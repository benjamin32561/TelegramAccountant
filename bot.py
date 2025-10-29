"""
Main Telegram bot entry point.
"""

import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import config
from handlers import commands, callbacks, messages


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
    application.add_handler(CommandHandler("setni", commands.setni_command))
    application.add_handler(CommandHandler("monthly", commands.monthly_command))
    application.add_handler(CommandHandler("projection", commands.projection_command))
    application.add_handler(CommandHandler("optimizer", commands.optimizer_command))
    application.add_handler(CommandHandler("receipt", commands.receipt_command))
    application.add_handler(CommandHandler("invoice", commands.invoice_command))
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

