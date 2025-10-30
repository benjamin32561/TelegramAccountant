"""
Conversational receipt generation handler.
Uses multi-step conversation to avoid parsing issues with Hebrew/English.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import os
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import config
from config import DATA_FOLDER_PATH
from utils import formatters, validators
from services import pdf_service

# Conversation states
AMOUNT, CLIENT, DESCRIPTION, PAYMENT_METHOD = range(4)


async def start_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the receipt creation conversation."""
    await update.message.reply_text(
        "📝 <b>Create New Receipt</b>\n\n"
        "Let's create a receipt step by step.\n\n"
        "💵 <b>Step 1/4:</b> Enter the amount (e.g., 3500 or ₪3,500)",
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove()
    )
    return AMOUNT


async def receipt_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input."""
    try:
        amount = validators.parse_amount(update.message.text)
        context.user_data['receipt_data'] = {'amount': amount}
        
        await update.message.reply_text(
            f"✅ Amount: {formatters.format_currency(amount)}\n\n"
            f"👤 <b>Step 2/4:</b> Enter client/customer name\n"
            f"(Hebrew or English)",
            parse_mode='HTML'
        )
        return CLIENT
        
    except:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a number (e.g., 3500 or 3,500.00)"
        )
        return AMOUNT


async def receipt_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle client name input."""
    client = update.message.text.strip()
    
    if not client:
        await update.message.reply_text("❌ Client name cannot be empty. Please try again.")
        return CLIENT
    
    context.user_data['receipt_data']['client'] = client
    
    await update.message.reply_text(
        f"✅ Client: {client}\n\n"
        f"📄 <b>Step 3/4:</b> Enter service description\n"
        f"(Hebrew or English, can be multi-line)",
        parse_mode='HTML'
    )
    return DESCRIPTION


async def receipt_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle description input."""
    description = update.message.text.strip()
    
    if not description:
        await update.message.reply_text("❌ Description cannot be empty. Please try again.")
        return DESCRIPTION
    
    context.user_data['receipt_data']['description'] = description
    
    # Create inline keyboard with payment method options
    payment_keyboard = [
        [
            InlineKeyboardButton("🏦 Bank Transfer", callback_data="payment_bank"),
            InlineKeyboardButton("💳 Credit Card", callback_data="payment_credit"),
        ],
        [
            InlineKeyboardButton("💵 Cash", callback_data="payment_cash"),
            InlineKeyboardButton("📝 Check", callback_data="payment_check"),
        ],
        [
            InlineKeyboardButton("⏭️ Skip (no payment method)", callback_data="payment_skip"),
        ]
    ]
    
    await update.message.reply_text(
        f"✅ Description: {description}\n\n"
        f"💳 <b>Step 4/4:</b> Select payment method (optional)\n\n"
        f"Choose how the client paid:",
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(payment_keyboard)
    )
    return PAYMENT_METHOD


async def receipt_payment_method(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle payment method selection via inline keyboard."""
    query = update.callback_query
    await query.answer()
    
    # Map callback data to payment method names
    payment_methods = {
        'payment_bank': 'Bank Transfer',
        'payment_credit': 'Credit Card',
        'payment_cash': 'Cash',
        'payment_check': 'Check',
        'payment_skip': None,
    }
    
    payment_method = payment_methods.get(query.data, None)
    
    receipt_data = context.user_data['receipt_data']
    receipt_data['payment_method'] = payment_method
    
    # Edit the message to show selection
    if payment_method:
        await query.edit_message_text(
            f"✅ Payment method selected: <b>{payment_method}</b>\n\n"
            f"🔄 Generating receipt...",
            parse_mode='HTML'
        )
    else:
        await query.edit_message_text(
            f"⏭️ Skipped payment method\n\n"
            f"🔄 Generating receipt...",
            parse_mode='HTML'
        )
    
    # Generate receipt (need to pass the effective message/chat)
    await generate_receipt_pdf(query, context, receipt_data)
    
    # Clear conversation data
    context.user_data.pop('receipt_data', None)
    
    return ConversationHandler.END


async def generate_receipt_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE, receipt_data: dict):
    """Generate the receipt PDF and send for approval."""
    
    # Handle both message and callback query updates
    if hasattr(update, 'callback_query') and update.callback_query:
        # Already edited the message in receipt_payment_method, no need to send another message
        chat_id = update.effective_chat.id
    else:
        await update.message.reply_text(
            "🔄 Generating receipt...",
            reply_markup=ReplyKeyboardRemove()
        )
        chat_id = update.message.chat_id
    
    # Generate receipt ID
    state = config.load_state()
    invoice_info = state['settings']['invoice_numbering']
    receipt_id = formatters.format_invoice_id(
        "K", invoice_info['year'], invoice_info['next_receipt']
    )
    
    # Get current month and year for organizing files
    current_month = config.get_current_month()
    current_year = config.get_current_year()
    
    # Use new organized folder structure
    pdf_path = config.get_receipt_path(receipt_id, current_year, current_month)
    
    # Generate PDF
    pdf = pdf_service.PDFService()
    success = pdf.generate_receipt(
        output_path=pdf_path,
        receipt_id=receipt_id,
        client=receipt_data['client'],
        amount=receipt_data['amount'],
        description=receipt_data['description'],
        business_info=state['settings']['business'],
        vat_rate=state['settings']['rates']['vat_rate'],
        payment_method=receipt_data.get('payment_method'),
        payment_ref=None,
    )
    
    if not success:
        await context.bot.send_message(chat_id=chat_id, text="❌ Failed to generate receipt")
        return
    
    # Create summary
    summary = f"📄 <b>Receipt Preview</b>\n\n"
    summary += f"<b>ID:</b> {receipt_id}\n"
    summary += f"<b>Client:</b> {receipt_data['client']}\n"
    summary += f"<b>Amount:</b> {formatters.format_currency(receipt_data['amount'])}\n"
    summary += f"<b>Description:</b> {receipt_data['description']}\n"
    if receipt_data.get('payment_method'):
        summary += f"<b>Payment:</b> {receipt_data['payment_method']}\n"
    
    # Send PDF for approval
    with open(pdf_path, 'rb') as f:
        await context.bot.send_document(
            chat_id=chat_id,
            document=f,
            caption=summary,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve & Save", callback_data=f"approve_{receipt_id}_{receipt_data['amount']}_{receipt_data['client']}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            ]])
        )


async def cancel_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the receipt creation conversation."""
    context.user_data.pop('receipt_data', None)
    
    await update.message.reply_text(
        "❌ Receipt creation cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

