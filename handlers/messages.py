"""
Telegram bot message handlers for file uploads (expenses).
"""

from telegram import Update
from telegram.ext import ContextTypes
import config
from config import DATA_FOLDER_PATH
from services import ledger_service
from utils import formatters
import os
from datetime import datetime


async def handle_expense_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle expense document upload (photo or file)."""
    
    # Check if user is in expense upload flow
    user_data = context.user_data
    if 'pending_expense' not in user_data:
        # Not in expense flow, ignore
        return
    
    expense_data = user_data['pending_expense']
    
    # Get the file
    file = None
    file_ext = None
    
    if update.message.photo:
        # Photo uploaded
        file = await update.message.photo[-1].get_file()  # Get highest resolution
        file_ext = "jpg"
    elif update.message.document:
        # Document uploaded (PDF, etc.)
        file = await update.message.document.get_file()
        file_name = update.message.document.file_name
        file_ext = file_name.split('.')[-1] if '.' in file_name else "pdf"
    else:
        await update.message.reply_text("❌ Please upload a photo or PDF document.")
        return
    
    # Generate expense ID
    state = config.load_state()
    expense_info = state['settings']['invoice_numbering']
    expense_id = formatters.format_invoice_id(
        "E", expense_info['year'], expense_info['next_expense']
    )
    
    # Create organized folder structure: DATA_FOLDER_PATH/expenses/YYYY/MM/
    current_year = config.get_current_year()
    current_month = config.get_current_month()
    expense_folder = os.path.join(DATA_FOLDER_PATH, "expenses", str(current_year), f"{current_month:02d}")
    os.makedirs(expense_folder, exist_ok=True)
    
    # Save file
    file_path = os.path.join(expense_folder, f"{expense_id}.{file_ext}")
    await file.download_to_drive(file_path)
    
    # Extract data
    amount = expense_data['amount']
    vendor = expense_data['vendor']
    description = expense_data['description']
    include_vat = expense_data.get('include_vat', False)
    vat_rate = state['settings']['rates']['vat_rate']
    
    # Calculate amount excluding VAT if needed
    if include_vat and vat_rate > 0:
        amount_excl_vat = amount / (1 + vat_rate)
        vat_amount = amount - amount_excl_vat
    else:
        amount_excl_vat = amount
        vat_amount = 0
    
    # Add to ledger
    ledger = ledger_service.LedgerService()
    ledger.add_entry(
        entry_id=expense_id,
        entry_type="Expense",
        amount=amount,
        party=vendor,
        description=description,
        payment_method="Expense",
        local_path=file_path,
        drive_file_id="",
        drive_folder_id="",
        notes=f"VAT: ₪{vat_amount:.2f}" if vat_amount > 0 else "No VAT"
    )
    
    # Auto-update monthly expenses (with VAT-exclusive amount)
    month_key = str(current_month)
    state["months"][month_key]["expenses"] += amount_excl_vat
    
    # Increment expense counter
    state['settings']['invoice_numbering']['next_expense'] += 1
    
    config.save_state(state)
    
    # Clear pending expense
    del user_data['pending_expense']
    
    # Confirmation message
    message = f"✅ Expense recorded!\n\n"
    message += f"ID: {expense_id}\n"
    message += f"Vendor: {vendor}\n"
    message += f"Amount: ₪{amount:,.2f}\n"
    if vat_amount > 0:
        vat_percentage = int(vat_rate * 100)
        message += f"VAT ({vat_percentage}%): ₪{vat_amount:.2f}\n"
        message += f"Excl. VAT: ₪{amount_excl_vat:,.2f}\n"
    message += f"📁 Saved to: {file_path}\n\n"
    message += f"💰 Expenses updated for {current_month}/{current_year}\n"
    message += f"Use /summary to see updated totals."
    
    await update.message.reply_text(message)

