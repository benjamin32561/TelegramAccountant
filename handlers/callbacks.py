import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import os
import re

from telegram import Update
from telegram.ext import ContextTypes
from config import DATA_FOLDER_PATH, get_current_month
import config
from services import ledger_service
from core.calculator import calculate_ytd_totals


async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries."""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "cancel":
        # Extract document ID from the approve button data if available
        # The document should be in the same message
        if query.message.caption:
            # Extract ID from caption like "📄 Receipt K-2025-0001"
            match = re.search(r'(K-\d{4}-\d{4}|R-\d{4}-\d{4}|E-\d{4}-\d{4})', query.message.caption)
            if match:
                doc_id = match.group(1)
                # Determine folder based on prefix
                if doc_id.startswith('K-'):
                    folder = os.path.join(DATA_FOLDER_PATH, "receipts")
                elif doc_id.startswith('R-'):
                    folder = os.path.join(DATA_FOLDER_PATH, "invoices")
                elif doc_id.startswith('E-'):
                    folder = os.path.join(DATA_FOLDER_PATH, "expenses")
                else:
                    folder = None
                
                # Delete the file
                if folder:
                    file_path = os.path.join(folder, f"{doc_id}.pdf")
                    if os.path.exists(file_path):
                        os.remove(file_path)
        
        await query.edit_message_caption(caption="❌ Cancelled and deleted")
        return
    
    if data.startswith("approve_"):
        # Parse approval data: approve_{invoice_id}_{amount}_{client}_{description}
        parts = data.replace("approve_", "").split("_")
        if len(parts) >= 3:
            invoice_id = parts[0]
            amount = float(parts[1])
            client = parts[2]
            description = "_".join(parts[3:]) if len(parts) > 3 else "Services"
            
            await handle_invoice_approval(query, invoice_id, amount, client, description)
    
    # Add more callback handlers as needed


async def handle_invoice_approval(query, document_id: str, amount: float, client: str, description: str):
    """Handle invoice/receipt approval and Drive upload."""
    state = config.load_state()
    
    # Determine if this is a receipt (K-) or invoice (R-)
    is_receipt = document_id.startswith('K-')
    counter_field = "next_receipt" if is_receipt else "next_invoice"
    
    # Get current year and month
    current_year = config.get_current_year()
    current_month = config.get_current_month()
    
    # Get PDF path using new organized structure
    if is_receipt:
        pdf_path = config.get_receipt_path(document_id, current_year, current_month)
    else:
        pdf_path = config.get_invoice_path(document_id, current_year, current_month)
    
    # Add to both monthly and yearly ledgers
    ledger = ledger_service.LedgerService()
    ledger.add_entry_to_all_ledgers(
        entry_id=document_id,
        entry_type="Income",
        amount=amount,
        party=client,
        description=description,
        payment_method="Receipt" if is_receipt else "Invoice",
        local_path=pdf_path,
        drive_file_id="",
        drive_folder_id="",
        notes=f"{'Receipt' if is_receipt else 'Invoice'} generated via bot",
        year=current_year,
        month=current_month,
    )
    
    # Increment appropriate counter
    state['settings']['invoice_numbering'][counter_field] += 1
    config.save_state(state)
    
    # Update income for current month
    current_month = get_current_month()
    month_key = str(current_month)
    state['months'][month_key]['income'] += amount
    
    # Recalculate totals
    state['totals'] = calculate_ytd_totals(state)
    
    config.save_state(state)
    
    # Send confirmation
    doc_type = "Receipt" if is_receipt else "Invoice"
    message = f"✅ {doc_type} approved and saved!\n\n"
    message += f"ID: {document_id}\n"
    message += f"Amount: ₪{amount:,.2f}\n"
    message += f"Client: {client}\n"
    message += f"📁 Saved to: {pdf_path}\n\n"
    message += "💰 Income recorded. Use /summary to see updated totals."
    
    # Try to edit caption if document, otherwise edit text
    await query.edit_message_caption(caption=message)