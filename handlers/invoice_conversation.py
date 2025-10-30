"""
Conversational invoice generation handler.
Uses multi-step conversation to avoid parsing issues with Hebrew/English.
"""

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import os
from telegram import Update, ReplyKeyboardRemove, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, ConversationHandler
import config
from config import DATA_FOLDER_PATH
from utils import formatters, validators
from services import pdf_service

# Conversation states
AMOUNT, CLIENT, DESCRIPTION = range(3)


async def start_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start the invoice creation conversation."""
    await update.message.reply_text(
        "📄 <b>Create New Invoice</b>\n\n"
        "Let's create an invoice step by step.\n\n"
        "💵 <b>Step 1/3:</b> Enter the amount (e.g., 3500 or ₪3,500)",
        parse_mode='HTML',
        reply_markup=ReplyKeyboardRemove()
    )
    return AMOUNT


async def invoice_amount(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle amount input."""
    try:
        amount = validators.parse_amount(update.message.text)
        context.user_data['invoice_data'] = {'amount': amount}
        
        await update.message.reply_text(
            f"✅ Amount: {formatters.format_currency(amount)}\n\n"
            f"👤 <b>Step 2/3:</b> Enter client/customer name\n"
            f"(Hebrew or English)",
            parse_mode='HTML'
        )
        return CLIENT
        
    except:
        await update.message.reply_text(
            "❌ Invalid amount. Please enter a number (e.g., 3500 or 3,500.00)"
        )
        return AMOUNT


async def invoice_client(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle client name input."""
    client = update.message.text.strip()
    
    if not client:
        await update.message.reply_text("❌ Client name cannot be empty. Please try again.")
        return CLIENT
    
    context.user_data['invoice_data']['client'] = client
    
    await update.message.reply_text(
        f"✅ Client: {client}\n\n"
        f"📄 <b>Step 3/3:</b> Enter service/product description\n"
        f"(Hebrew or English, can be multi-line)",
        parse_mode='HTML'
    )
    return DESCRIPTION


async def invoice_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle description input and generate invoice."""
    description = update.message.text.strip()
    
    if not description:
        await update.message.reply_text("❌ Description cannot be empty. Please try again.")
        return DESCRIPTION
    
    invoice_data = context.user_data['invoice_data']
    invoice_data['description'] = description
    
    # Generate invoice
    await generate_invoice_pdf(update, context, invoice_data)
    
    # Clear conversation data
    context.user_data.pop('invoice_data', None)
    
    return ConversationHandler.END


async def generate_invoice_pdf(update: Update, context: ContextTypes.DEFAULT_TYPE, invoice_data: dict):
    """Generate the invoice PDF and send for approval."""
    
    await update.message.reply_text(
        "🔄 Generating invoice...",
        reply_markup=ReplyKeyboardRemove()
    )
    
    # Generate invoice ID
    state = config.load_state()
    invoice_info = state['settings']['invoice_numbering']
    invoice_id = formatters.format_invoice_id(
        "R", invoice_info['year'], invoice_info['next_invoice']
    )
    
    # Get current month and year for organizing files
    current_month = config.get_current_month()
    current_year = config.get_current_year()
    
    # Use new organized folder structure
    pdf_path = config.get_invoice_path(invoice_id, current_year, current_month)
    
    # Generate PDF
    pdf = pdf_service.PDFService()
    success = pdf.generate_invoice(
        output_path=pdf_path,
        invoice_id=invoice_id,
        client=invoice_data['client'],
        amount=invoice_data['amount'],
        description=invoice_data['description'],
        business_info=state['settings']['business'],
        vat_rate=state['settings']['rates']['vat_rate'],
    )
    
    if not success:
        await update.message.reply_text("❌ Failed to generate invoice")
        return
    
    # Create summary
    summary = f"📄 <b>Invoice Preview</b>\n\n"
    summary += f"<b>ID:</b> {invoice_id}\n"
    summary += f"<b>Client:</b> {invoice_data['client']}\n"
    summary += f"<b>Amount:</b> {formatters.format_currency(invoice_data['amount'])}\n"
    summary += f"<b>Description:</b> {invoice_data['description']}\n"
    
    # Send PDF for approval
    with open(pdf_path, 'rb') as f:
        await update.message.reply_document(
            document=f,
            caption=summary,
            parse_mode='HTML',
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve & Save", callback_data=f"approve_{invoice_id}_{invoice_data['amount']}_{invoice_data['client']}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            ]])
        )


async def cancel_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancel the invoice creation conversation."""
    context.user_data.pop('invoice_data', None)
    
    await update.message.reply_text(
        "❌ Invoice creation cancelled.",
        reply_markup=ReplyKeyboardRemove()
    )
    
    return ConversationHandler.END

