"""
Main Telegram bot entry point.
"""

import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes, ConversationHandler
import config
from handlers import commands, callbacks, messages, receipt_conversation, invoice_conversation


# Load environment variables
load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    await update.message.reply_text(
        "👋 Welcome to Exempt/Morasha Pro!\n\n"
        "Your unified finance management bot.\n\n"
        "Use /help to see all commands."
    )


async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle errors."""
    print(f"Update {update} caused error {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An error occurred. Please try again or use /help."
        )


def main():
    """Start the bot."""
    if not BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN not found in .env file")
        return
    
    # Ensure state exists
    config.ensure_state_exists()
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", commands.help_command))
    application.add_handler(CommandHandler("update", commands.update_command))
    application.add_handler(CommandHandler("recommend", commands.recommend_command))
    application.add_handler(CommandHandler("deposit", commands.deposit_command))
    application.add_handler(CommandHandler("summary", commands.summary_command))
    application.add_handler(CommandHandler("monthly", commands.monthly_command))
    application.add_handler(CommandHandler("projection", commands.projection_command))
    application.add_handler(CommandHandler("optimizer", commands.optimizer_command))
    
    # Conversational receipt handler (new improved version)
    receipt_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("receipt", receipt_conversation.start_receipt)],
        states={
            receipt_conversation.AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receipt_conversation.receipt_amount)],
            receipt_conversation.CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, receipt_conversation.receipt_client)],
            receipt_conversation.DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, receipt_conversation.receipt_description)],
            receipt_conversation.PAYMENT_METHOD: [MessageHandler(filters.TEXT & ~filters.COMMAND, receipt_conversation.receipt_payment_method)],
        },
        fallbacks=[CommandHandler("cancel", receipt_conversation.cancel_receipt)],
    )
    application.add_handler(receipt_conv_handler)
    
    # Conversational invoice handler (new improved version)
    invoice_conv_handler = ConversationHandler(
        entry_points=[CommandHandler("invoice", invoice_conversation.start_invoice)],
        states={
            invoice_conversation.AMOUNT: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_conversation.invoice_amount)],
            invoice_conversation.CLIENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_conversation.invoice_client)],
            invoice_conversation.DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, invoice_conversation.invoice_description)],
        },
        fallbacks=[CommandHandler("cancel", invoice_conversation.cancel_invoice)],
    )
    application.add_handler(invoice_conv_handler)
    application.add_handler(CommandHandler("expense", commands.expense_command))
    application.add_handler(CommandHandler("excel", commands.excel_command))
    application.add_handler(CommandHandler("last", commands.last_entries_command))
    application.add_handler(CommandHandler("settings", commands.settings_command))
    application.add_handler(CommandHandler("setmonth", commands.setmonth_command))
    application.add_handler(CommandHandler("nextmonth", commands.nextmonth_command))
    
    # Register message handlers for file uploads
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.ALL, messages.handle_expense_document))
    
    # Register callbacks
    application.add_handler(CallbackQueryHandler(callbacks.handle_callback))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start bot
    print("🤖 Bot starting...")
    print("✅ Bot is running. Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

