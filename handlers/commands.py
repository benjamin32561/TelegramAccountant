import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
import config
from config import DATA_FOLDER_PATH
from utils import formatters, validators
from core import calculator
from services import ledger_service, pdf_service
import os



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message."""
    help_text = """
<b>📚 Commands Cheat Sheet</b>

<b>💰 Core Workflow:</b>
1. /receipt AMOUNT CLIENT "description" → Auto-updates income
2. /expense AMOUNT VENDOR "description" vat → Uploads file, auto-updates expenses
3. /recommend → Get deposit suggestions
4. /deposit pension=X study=Y → Record deposits
5. /summary → Full analysis with "what's left"

<b>📊 Financial Analysis:</b>
/summary — Full YTD analysis + what's left to do
/monthly — This month's tax/NI projection
/projection — Year-end forecast
/recommend — Deposit recommendations
/setni AMOUNT — Set manual NI payment

<b>📄 Document Management:</b>
/receipt AMOUNT CLIENT "description" — Generate receipt (auto-updates income)
/invoice AMOUNT CLIENT "description" — Generate invoice (auto-updates income)
/expense AMOUNT VENDOR "desc" vat — Upload expense with photo (auto-updates expenses)
/excel — Download complete ledger
/last NUMBER — Show last N entries

<b>⚙️ Advanced:</b>
/optimizer — December top-up optimizer
/settings key=value — Update settings
/setmonth M YEAR — Time travel for testing
/nextmonth — Advance one month

<b>💡 Key Features:</b>
• /expense accepts photos/PDFs and extracts VAT
• Add "vat" to expense if amount includes VAT
• Income auto-updates when approving receipts/invoices
• Expenses auto-update when uploading files
• /monthly shows this month's tax estimate
• /summary shows what's left to deposit
"""
    
    await update.message.reply_text(help_text, parse_mode='HTML')


async def update_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update monthly values (cumulative - adds to existing values)."""
    state = config.load_state()
    current_month = config.get_current_month()
    user_id = update.effective_user.id
    
    # Parse command arguments
    args = update.message.text.replace("/update", "").strip()
    updates = validators.parse_update_command(args)
    
    if not updates:
        await update.message.reply_text(
            "❌ Invalid format. Use: /update income=1000 expenses=200\n"
            "💡 Tip: You can update just one field at a time!"
        )
        return
    
    # Update state (ADD to existing values, don't overwrite)
    month_key = str(current_month)
    previous_values = {}
    new_values = {}
    
    for key, value in updates.items():
        previous_values[key] = state["months"][month_key][key]
        state["months"][month_key][key] += value  # ADD instead of overwrite
        new_values[key] = state["months"][month_key][key]
    
    config.save_state(state)
    
    # Create detailed summary message
    summary_lines = []
    for key, added_value in updates.items():
        prev = previous_values[key]
        new = new_values[key]
        summary_lines.append(f"  {key.capitalize()}: ₪{prev:,.0f} + ₪{added_value:,.0f} = ₪{new:,.0f}")
    
    summary = "\n".join(summary_lines)
    
    await update.message.reply_text(
        f"✅ Updated {current_month}/{state['year']}:\n{summary}\n\n"
        f"💡 Use /recommend to see deposit suggestions"
    )


async def recommend_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Quick deposit recommendations based on current income."""
    state = config.load_state()
    analysis = calculator.calculate_full_analysis(state)
    
    totals = analysis['totals']
    remaining = analysis['remaining']
    suggestions = analysis['suggestions']
    
    # Get current forecast mode
    forecast_mode = state['settings'].get('forecast', {}).get('mode', 'balanced')
    current_suggestion = suggestions[forecast_mode]
    
    message = f"<b>💡 Deposit Recommendations</b>\n\n"
    message += f"<b>📊 Current Status:</b>\n"
    message += f"  Net Income: {formatters.format_currency(totals['net_income_ytd'])}\n"
    message += f"  Months Left: {totals['months_left']}\n\n"
    
    message += f"<b>💰 Recommended Monthly Deposits ({forecast_mode.capitalize()}):</b>\n"
    message += f"  Pension: {formatters.format_currency(current_suggestion['pension'])}\n"
    message += f"  Study: {formatters.format_currency(current_suggestion['study'])}\n"
    message += f"  Total: {formatters.format_currency(current_suggestion['total'])}\n\n"
    
    message += f"<b>📈 Remaining Room:</b>\n"
    message += f"  Pension: {formatters.format_currency(remaining['pension_remaining'])}\n"
    message += f"  Study: {formatters.format_currency(remaining['study_remaining'])}\n\n"
    
    message += f"💡 <i>Use /deposit pension=X study=Y to record your deposits</i>\n"
    message += f"📊 <i>Use /summary for detailed analysis</i>"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def deposit_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Record pension/study fund deposits."""
    state = config.load_state()
    current_month = config.get_current_month()
    
    # Parse command
    args = update.message.text.replace("/deposit", "").strip()
    deposits = validators.parse_deposit_command(args)
    
    if not deposits:
        await update.message.reply_text(
            "❌ Invalid format. Use: /deposit pension=2000 study=500"
        )
        return
    
    # Add to current month
    month_key = str(current_month)
    for key, value in deposits.items():
        state["months"][month_key][key] += value
    
    config.save_state(state)
    
    # Summary
    summary = "\n".join([f"  {k}: +₪{v:,.2f}" for k, v in deposits.items()])
    await update.message.reply_text(
        f"✅ Recorded deposits for {current_month}/{state['year']}:\n{summary}"
    )


async def summary_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate comprehensive financial summary with detailed tax analysis."""
    state = config.load_state()
    analysis = calculator.calculate_full_analysis(state)
    
    totals = analysis['totals']
    caps = analysis['caps']
    remaining = analysis['remaining']
    suggestions = analysis['suggestions']
    tax_analysis = analysis['tax_analysis']
    
    # Table 1: Current State
    state_rows = [
        ("Gross Income", formatters.format_currency(totals['income_ytd'])),
        ("Expenses", formatters.format_currency(totals['expenses_ytd'])),
        ("Net Income", formatters.format_currency(totals['net_income_ytd'])),
        ("", ""),
        ("Pension Deposited", formatters.format_currency(totals['pension_total'])),
        ("Pension Cap (16.5%)", formatters.format_currency(caps['pension_cap'])),
        ("Pension Remaining", formatters.format_currency(remaining['pension_remaining'])),
        ("", ""),
        ("Study Deposited", formatters.format_currency(totals['study_total'])),
        ("Study Ded. Cap (4.5%)", formatters.format_currency(caps['study_deductible_cap'])),
        ("Study Ded. Remaining", formatters.format_currency(remaining['study_deductible_remaining'])),
        ("Study Total Cap (₪20,520)", formatters.format_currency(caps['study_total_cap'])),
        ("Study Total Remaining", formatters.format_currency(remaining['study_total_remaining'])),
        ("", ""),
        ("Months Left", str(totals['months_left'])),
    ]
    
    state_table = formatters.format_two_column_table(("Metric", "Amount"), state_rows)
    
    # Table 2: Tax Analysis - Monthly vs Yearly Comparison
    comparison = tax_analysis['comparison']
    
    tax_rows = [
        ("", "Monthly", "Yearly"),
        ("─" * 20, "─" * 12, "─" * 12),
        ("Net Income", 
         formatters.format_currency(comparison['monthly']['income']),
         formatters.format_currency(comparison['yearly']['income'])),
        ("", "", ""),
        ("Income Tax", 
         formatters.format_currency(comparison['monthly']['tax']),
         formatters.format_currency(comparison['yearly']['tax'])),
        ("Tax Rate", f"{tax_analysis['summary']['tax_percentage']:.1f}%", f"{tax_analysis['summary']['tax_percentage']:.1f}%"),
        ("Marginal Rate", f"{tax_analysis['tax']['marginal_rate']*100:.1f}%", f"{tax_analysis['tax']['marginal_rate']*100:.1f}%"),
        ("", "", ""),
        ("National Insurance (Employee)", 
         formatters.format_currency(comparison['monthly']['ni_employee']),
         formatters.format_currency(comparison['yearly']['ni_employee'])),
        ("Health Tax (Employee)", 
         formatters.format_currency(tax_analysis['national_insurance']['health_amount'] / 12),
         formatters.format_currency(tax_analysis['national_insurance']['health_amount'])),
        ("NI + Health Rate", f"{tax_analysis['summary']['ni_percentage']:.1f}%", f"{tax_analysis['summary']['ni_percentage']:.1f}%"),
        ("", "", ""),
        ("NI Paid Manually", 
         formatters.format_currency(comparison['ni_status']['monthly_paid']),
         formatters.format_currency(comparison['ni_status']['yearly_paid'])),
        ("NI Remaining", 
         formatters.format_currency(comparison['ni_status']['monthly_remaining']),
         formatters.format_currency(comparison['ni_status']['yearly_remaining'])),
        ("", "", ""),
        ("Total Tax Burden", 
         formatters.format_currency(comparison['monthly']['total_burden']),
         formatters.format_currency(comparison['yearly']['total_burden'])),
        ("Effective Rate", f"{comparison['monthly']['effective_rate']*100:.1f}%", f"{comparison['yearly']['effective_rate']*100:.1f}%"),
        ("Take-Home Pay", 
         formatters.format_currency(comparison['monthly']['take_home']),
         formatters.format_currency(comparison['yearly']['take_home'])),
    ]
    
    # Format as simple list (fixed-width fails in Telegram)
    tax_table = "<b>💰 Tax Analysis (Self-Employed):</b>\n\n"
    tax_table += "<b>Monthly Breakdown:</b>\n"
    tax_table += f"• Net Income: {formatters.format_currency(comparison['monthly']['income'])}\n"
    tax_table += f"• Income Tax: {formatters.format_currency(comparison['monthly']['tax'])} ({tax_analysis['summary']['tax_percentage']:.1f}%)\n"
    tax_table += f"• NI + Health: {formatters.format_currency(comparison['monthly']['ni_employee'])}\n"
    tax_table += f"• Total Burden: {formatters.format_currency(comparison['monthly']['total_burden'])}\n"
    tax_table += f"• Take-Home: {formatters.format_currency(comparison['monthly']['take_home'])}\n"
    tax_table += f"• Effective Rate: {comparison['monthly']['effective_rate']*100:.1f}%\n\n"
    
    tax_table += "<b>Yearly Breakdown:</b>\n"
    tax_table += f"• Net Income: {formatters.format_currency(comparison['yearly']['income'])}\n"
    tax_table += f"• Income Tax: {formatters.format_currency(comparison['yearly']['tax'])} ({tax_analysis['summary']['tax_percentage']:.1f}%)\n"
    tax_table += f"• NI + Health: {formatters.format_currency(comparison['yearly']['ni_employee'])}\n"
    tax_table += f"• NI Paid Manually: {formatters.format_currency(comparison['ni_status']['yearly_paid'])}\n"
    tax_table += f"• NI Remaining: {formatters.format_currency(comparison['ni_status']['yearly_remaining'])}\n"
    tax_table += f"• Total Burden: {formatters.format_currency(comparison['yearly']['total_burden'])}\n"
    tax_table += f"• Take-Home: {formatters.format_currency(comparison['yearly']['take_home'])}\n"
    tax_table += f"• Effective Rate: {comparison['yearly']['effective_rate']*100:.1f}%\n"
    tax_table += f"• Marginal Rate: {tax_analysis['tax']['marginal_rate']*100:.1f}%\n\n"
    tax_table += f"<i>Note: Self-employed (osek patur) - no employer contributions</i>\n"
    
    # Table 3: Recommendations
    rec_table = "<b>📋 Deposit Recommendations:</b>\n\n"
    
    rec_table += "<b>Balanced:</b>\n"
    rec_table += f"• Pension: {formatters.format_currency(suggestions['balanced']['pension'])}\n"
    rec_table += f"• Study (Deductible): {formatters.format_currency(suggestions['balanced']['study_deductible'])}\n"
    rec_table += f"• Study (Total): {formatters.format_currency(suggestions['balanced']['study_total'])}\n\n"
    
    rec_table += "<b>Aggressive (Front-load):</b>\n"
    rec_table += f"• Pension: {formatters.format_currency(suggestions['aggressive']['pension'])}\n"
    rec_table += f"• Study (Deductible): {formatters.format_currency(suggestions['aggressive']['study_deductible'])}\n"
    rec_table += f"• Study (Total): {formatters.format_currency(suggestions['aggressive']['study_total'])}\n\n"
    
    rec_table += "<b>Conservative:</b>\n"
    rec_table += f"• Pension: {formatters.format_currency(suggestions['conservative']['pension'])}\n"
    rec_table += f"• Study (Deductible): {formatters.format_currency(suggestions['conservative']['study_deductible'])}\n"
    rec_table += f"• Study (Total): {formatters.format_currency(suggestions['conservative']['study_total'])}\n"
    
    # Add "What's Left" section
    whats_left = f"""
<b>🎯 What's Left to Do This Year:</b>

<b>Deposit Room Remaining:</b>
• Pension: {formatters.format_currency(remaining['pension_remaining'])} (out of {formatters.format_currency(caps['pension_cap'])})
• Study (Deductible): {formatters.format_currency(remaining['study_deductible_remaining'])} (out of {formatters.format_currency(caps['study_deductible_cap'])})
• Study (Tax-Free): {formatters.format_currency(remaining['study_total_remaining'])} (out of ₪20,520)

<b>If You Max Out Caps:</b>
• Total Additional Deposits: {formatters.format_currency(remaining['pension_remaining'] + remaining['study_total_remaining'])}
• Tax Saved: ~{formatters.format_currency((remaining['pension_remaining'] + remaining['study_deductible_remaining']) * tax_analysis['tax']['marginal_rate'])}
• Months Left: {totals['months_left']} months

<b>Quick Actions:</b>
• /monthly — See this month's projection
• /projection — See year-end forecast
• /optimizer — Optimize December deposits
"""
    
    # Add concise summary
    summary_text = f"""
<b>📋 Quick Summary:</b>
• Monthly Take-Home: {formatters.format_currency(comparison['monthly']['take_home'])}
• Tax Burden: {tax_analysis['summary']['tax_percentage']:.1f}% income + {tax_analysis['summary']['ni_percentage']:.1f}% NI+Health = {tax_analysis['summary']['total_effective_rate']*100:.1f}% total
• NI Status: {formatters.format_currency(comparison['ni_status']['yearly_remaining'])} remaining to pay
• Marginal Rate: {tax_analysis['tax']['marginal_rate']*100:.1f}% (next ₪1 taxed at this rate)
• Health Tax: {tax_analysis['summary']['health_percentage']:.1f}% of income
"""
    
    # Combine and send
    message = f"<b>📊 Financial Summary - {state['year']}</b>\n\n"
    message += "<b>📈 Current State:</b>\n" + state_table + "\n\n"
    message += tax_table + "\n\n"
    message += rec_table + "\n\n"
    message += whats_left + "\n"
    message += summary_text
    
    await update.message.reply_text(message, parse_mode='HTML')


async def setni_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set manual National Insurance payment amount."""
    args = context.args
    if len(args) != 1:
        await update.message.reply_text(
            "❌ Usage: /setni <amount>\n"
            "Example: /setni 5000"
        )
        return
    
    try:
        amount = validators.parse_amount(args[0])
    except:
        await update.message.reply_text("❌ Invalid amount format")
        return
    
    state = config.load_state()
    state['totals']['ni_paid_manually'] = amount
    config.save_state(state)
    
    await update.message.reply_text(
        f"✅ Set manual NI payment to ₪{amount:,.2f}\n\n"
        f"Run /summary to see updated tax analysis"
    )


async def monthly_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show current month's tax and NI projections."""
    state = config.load_state()
    current_month = config.get_current_month()
    current_year = config.get_current_year()
    
    # Get current month's data
    month_key = str(current_month)
    month_data = state['months'][month_key]
    
    # Calculate monthly figures
    monthly_income = month_data['income']
    monthly_expenses = month_data['expenses']
    monthly_net = monthly_income - monthly_expenses
    monthly_pension = month_data['pension']
    monthly_study = month_data['study']
    
    # Get tax and NI settings
    tax_settings = state['settings']['rates']['tax']
    ni_settings = state['settings']['rates']['ni']
    
    # Calculate monthly NI (self-employed only - no employer contributions)
    from core import tax_calculator
    ni_calc = tax_calculator.calculate_national_insurance(monthly_net / 12 if monthly_net > 0 else 0, ni_settings)
    monthly_ni_total = ni_calc['total_amount']
    
    # Estimate monthly tax (simplified - based on monthly income only)
    # For accurate tax, need YTD, but this gives monthly estimate
    taxable_income = monthly_net - monthly_pension - monthly_study
    if taxable_income > 0:
        tax_calc = tax_calculator.calculate_income_tax(taxable_income, tax_settings)
        monthly_tax = tax_calc['net_tax'] / 12  # Spread over year
    else:
        monthly_tax = 0
    
    # Build message
    message = f"📅 <b>Monthly Projection - {current_month}/{current_year}</b>\n\n"
    
    message += f"<b>💰 This Month's Income:</b>\n"
    message += f"  Gross: {formatters.format_currency(monthly_income)}\n"
    message += f"  Expenses: {formatters.format_currency(monthly_expenses)}\n"
    message += f"  Net: {formatters.format_currency(monthly_net)}\n\n"
    
    message += f"<b>🏦 This Month's Deposits:</b>\n"
    message += f"  Pension: {formatters.format_currency(monthly_pension)}\n"
    message += f"  Study: {formatters.format_currency(monthly_study)}\n"
    message += f"  Total: {formatters.format_currency(monthly_pension + monthly_study)}\n\n"
    
    message += f"<b>📊 Estimated Monthly Payments:</b>\n"
    message += f"  Income Tax: ~{formatters.format_currency(monthly_tax)}\n"
    message += f"  NI + Health: ~{formatters.format_currency(monthly_ni_total)}\n"
    message += f"  <b>Total Burden:</b> ~{formatters.format_currency(monthly_tax + monthly_ni_total)}\n"
    message += f"  <i>(Self-employed: no employer contributions)</i>\n\n"
    
    # Get recommendations for this month
    analysis = calculator.calculate_full_analysis(state)
    suggestions = analysis['suggestions']['balanced']
    
    message += f"<b>💡 Recommended Deposits (Rest of Year):</b>\n"
    message += f"  Pension: {formatters.format_currency(suggestions['pension'])} /month\n"
    message += f"  Study: {formatters.format_currency(suggestions['study_total'])} /month\n\n"
    
    message += f"💼 Use /summary for full YTD analysis\n"
    message += f"📈 Use /projection for year-end forecast"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def projection_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show comprehensive year-end projection."""
    state = config.load_state()
    current_month = config.get_current_month()
    current_year = config.get_current_year()
    
    # Get current analysis
    analysis = calculator.calculate_full_analysis(state)
    totals = analysis['totals']
    caps = analysis['caps']
    remaining = analysis['remaining']
    tax_analysis = analysis['tax_analysis']
    
    months_left = totals['months_left']
    
    # Project year-end income (assume current average continues)
    if current_month > 0:
        avg_monthly_income = totals['income_ytd'] / current_month
        avg_monthly_expenses = totals['expenses_ytd'] / current_month
    else:
        avg_monthly_income = 0
        avg_monthly_expenses = 0
    
    projected_income = totals['income_ytd'] + (avg_monthly_income * months_left)
    projected_expenses = totals['expenses_ytd'] + (avg_monthly_expenses * months_left)
    projected_net = projected_income - projected_expenses
    
    # Project deposits (assume recommendations followed)
    suggestions = analysis['suggestions']['balanced']
    projected_pension = totals['pension_total'] + (suggestions['pension'] * months_left)
    projected_study = totals['study_total'] + (suggestions['study_total'] * months_left)
    
    # Cap projections
    projected_pension_capped = min(projected_pension, projected_net * 0.165)
    projected_study_capped = min(projected_study, 20520)
    
    # Calculate projected tax
    projected_taxable = projected_net - projected_pension_capped - min(projected_study_capped, projected_net * 0.045)
    tax_settings = state['settings']['rates']['tax']
    from core import tax_calculator
    projected_tax_calc = tax_calculator.calculate_income_tax(projected_taxable, tax_settings)
    
    # Build message
    message = f"📈 <b>Year-End Projection - {current_year}</b>\n\n"
    
    message += f"<b>💰 Projected Year-End:</b>\n"
    message += f"  Income: {formatters.format_currency(projected_income)}\n"
    message += f"  Expenses: {formatters.format_currency(projected_expenses)}\n"
    message += f"  <b>Net Income:</b> {formatters.format_currency(projected_net)}\n\n"
    
    message += f"<b>🏦 Projected Deposits:</b>\n"
    message += f"  Pension: {formatters.format_currency(projected_pension_capped)}\n"
    message += f"  Study: {formatters.format_currency(projected_study_capped)}\n"
    message += f"  Total: {formatters.format_currency(projected_pension_capped + projected_study_capped)}\n\n"
    
    message += f"<b>📊 Projected Tax:</b>\n"
    message += f"  Taxable Income: {formatters.format_currency(projected_taxable)}\n"
    message += f"  Income Tax: {formatters.format_currency(projected_tax_calc['net_tax'])}\n"
    message += f"  Effective Rate: {projected_tax_calc['effective_rate']*100:.1f}%\n\n"
    
    message += f"<b>📅 Current Progress:</b>\n"
    message += f"  Months completed: {current_month}/12\n"
    message += f"  Months remaining: {months_left}\n"
    message += f"  % of year: {(current_month/12)*100:.0f}%\n\n"
    
    message += f"<b>🎯 To Reach Projections:</b>\n"
    if months_left > 0:
        needed_monthly_income = (projected_income - totals['income_ytd']) / months_left
        needed_monthly_pension = max(0, (projected_pension_capped - totals['pension_total']) / months_left)
        needed_monthly_study = max(0, (projected_study_capped - totals['study_total']) / months_left)
        
        message += f"  Income: {formatters.format_currency(needed_monthly_income)}/month\n"
        message += f"  Pension: {formatters.format_currency(needed_monthly_pension)}/month\n"
        message += f"  Study: {formatters.format_currency(needed_monthly_study)}/month\n"
    else:
        message += f"  No months remaining!\n"
    
    message += f"\n💡 Use /optimizer for December top-up strategy"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def optimizer_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """December top-up optimizer."""
    state = config.load_state()
    current_month = config.get_current_month()
    analysis = calculator.calculate_full_analysis(state)
    
    if current_month != 12:
        await update.message.reply_text(
            f"⏰ December optimizer will be available in December.\n"
            f"Currently in month {current_month}/12"
        )
        return
    
    remaining = analysis['remaining']
    
    message = "🎯 <b>December Top-Up Optimizer</b>\n\n"
    message += "<b>Exact amounts to max out:</b>\n"
    message += f"Pension: {formatters.format_currency(remaining['pension_remaining'])}\n"
    message += f"Study Fund: {formatters.format_currency(remaining['study_total_remaining'])}\n\n"
    message += "💡 Use /deposit to record these amounts."
    
    await update.message.reply_text(message, parse_mode='HTML')


async def receipt_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate receipt PDF."""
    # Parse command: /receipt <amount> <client> [description] [payment_method] [payment_ref]
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Usage: /receipt <amount> <client> [description] [payment_method] [payment_ref]\n"
            "Example: /receipt 2016 Algolight September services Bank transfer Ref1234"
        )
        return
    
    try:
        amount = validators.parse_amount(args[0])
        client = args[1]
        description = args[2] if len(args) > 2 else "Services"
        payment_method = args[3] if len(args) > 3 else "Cash"
        payment_ref = args[4] if len(args) > 4 else None
    except:
        await update.message.reply_text("❌ Invalid amount format")
        return
    
    # Generate receipt ID (K- prefix for receipts)
    state = config.load_state()
    invoice_info = state['settings']['invoice_numbering']
    receipt_id = formatters.format_invoice_id(
        "K", invoice_info['year'], invoice_info['next_receipt']
    )
    
    # Generate PDF
    receipts_folder = os.path.join(DATA_FOLDER_PATH, "receipts")
    os.makedirs(receipts_folder, exist_ok=True)
    pdf_path = os.path.join(receipts_folder, f"{receipt_id}.pdf")
    
    pdf = pdf_service.PDFService()
    success = pdf.generate_receipt(
        output_path=pdf_path,
        receipt_id=receipt_id,
        client=client,
        amount=amount,
        description=description,
        business_info=state['settings']['business'],
        vat_rate=state['settings']['rates']['vat_rate'],
        payment_method=payment_method,
        payment_ref=payment_ref,
    )
    
    if not success:
        await update.message.reply_text("❌ Failed to generate receipt")
        return
    
    # Send PDF for approval
    with open(pdf_path, 'rb') as f:
        await update.message.reply_document(
            document=f,
            caption=f"📄 Receipt {receipt_id}\n\nApprove & upload to Drive?",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve & Upload", callback_data=f"approve_{receipt_id}_{amount}_{client}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            ]])
        )


async def invoice_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Generate invoice PDF (separate from receipts)."""
    # Parse command: /invoice <amount> <client> [description]
    args = context.args
    if len(args) < 2:
        await update.message.reply_text(
            "❌ Usage: /invoice <amount> <client> [description]\n"
            "Example: /invoice 2016 Algolight September services"
        )
        return
    
    try:
        amount = validators.parse_amount(args[0])
        client = args[1]
        description = " ".join(args[2:]) if len(args) > 2 else "Services"
    except:
        await update.message.reply_text("❌ Invalid amount format")
        return
    
    # Generate invoice ID (R- prefix for invoices)
    state = config.load_state()
    invoice_info = state['settings']['invoice_numbering']
    invoice_id = formatters.format_invoice_id(
        "R", invoice_info['year'], invoice_info['next_invoice']
    )
    
    # Generate PDF
    invoices_folder = os.path.join(DATA_FOLDER_PATH, "invoices")
    os.makedirs(invoices_folder, exist_ok=True)
    pdf_path = os.path.join(invoices_folder, f"{invoice_id}.pdf")
    
    pdf = pdf_service.PDFService()
    success = pdf.generate_invoice(
        output_path=pdf_path,
        invoice_id=invoice_id,
        client=client,
        amount=amount,
        description=description,
        business_info=state['settings']['business'],
        vat_rate=state['settings']['rates']['vat_rate'],
    )
    
    if not success:
        await update.message.reply_text("❌ Failed to generate invoice")
        return
    
    # Send PDF for approval
    with open(pdf_path, 'rb') as f:
        await update.message.reply_document(
            document=f,
            caption=f"📄 Invoice {invoice_id}\n\nApprove & upload to Drive?",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("✅ Approve & Upload", callback_data=f"approve_{invoice_id}_{amount}_{client}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel")
            ]])
        )


async def excel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send current ledger Excel file."""
    if not os.path.exists(config.LEDGER_FILE):
        await update.message.reply_text("❌ Ledger not found")
        return
    
    with open(config.LEDGER_FILE, 'rb') as f:
        await update.message.reply_document(
            document=f,
            caption="📊 Current ledger"
        )


async def last_entries_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show last n entries from ledger."""
    n = 5
    if context.args and context.args[0].isdigit():
        n = int(context.args[0])
    
    ledger = ledger_service.LedgerService()
    entries = ledger.get_last_entries(n)
    
    if not entries:
        await update.message.reply_text("📝 No entries in ledger yet")
        return
    
    message = f"<b>📋 Last {n} Entries:</b>\n\n"
    for entry in reversed(entries):  # Show newest first
        msg = f"{entry['ID']} | {entry['Type']} | {entry['Party/Vendor']}\n"
        msg += f"{entry['Amount (₪)']}₪ | {entry['Date']}\n"
        message += msg + "\n"
    
    await update.message.reply_text(message, parse_mode='HTML')


async def expense_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Start expense upload workflow with VAT support."""
    args = context.args
    if not args or len(args) < 1:
        await update.message.reply_text(
            "❌ Usage: /expense AMOUNT VENDOR [description] [vat]\n\n"
            "Examples:\n"
            "• /expense 150 OfficeMax \"Office supplies\"\n"
            "• /expense 177 Restaurant \"Team lunch\" vat\n\n"
            "Add 'vat' at the end if amount INCLUDES VAT (will extract VAT automatically)"
        )
        return
    
    try:
        amount = validators.parse_amount(args[0])
    except:
        await update.message.reply_text("❌ Invalid amount format")
        return
    
    vendor = args[1] if len(args) > 1 else "Unknown"
    
    # Check if last arg is "vat"
    include_vat = False
    desc_args = args[2:]
    if desc_args and desc_args[-1].lower() == "vat":
        include_vat = True
        desc_args = desc_args[:-1]
    
    description = " ".join(desc_args) if desc_args else "Expense"
    
    # Store pending expense data in user context
    context.user_data['pending_expense'] = {
        'amount': amount,
        'vendor': vendor,
        'description': description,
        'include_vat': include_vat
    }
    
    # Build message
    message = f"📸 Please upload the expense document (photo or PDF)\n\n"
    message += f"Amount: ₪{amount:,.2f}"
    if include_vat:
        state = config.load_state()
        vat_rate = state['settings']['rates']['vat_rate']
        if vat_rate > 0:
            amount_excl_vat = amount / (1 + vat_rate)
            vat_amount = amount - amount_excl_vat
            message += f" (includes ₪{vat_amount:.2f} VAT)\n"
            message += f"Excl. VAT: ₪{amount_excl_vat:.2f}"
        else:
            message += " (VAT rate is 0%)"
    message += f"\nVendor: {vendor}\n"
    message += f"Description: {description}\n\n"
    message += f"📤 Upload the document now..."
    
    await update.message.reply_text(message)


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Update settings via command."""
    args = context.args
    if not args:
        # Show current settings
        state = config.load_state()
        business = state['settings']['business']
        
        message = "⚙️ <b>Current Business Settings:</b>\n\n"
        message += f"<b>Name:</b> {business['name']}\n"
        message += f"<b>Dealer ID:</b> {business['dealer_id']}\n"
        message += f"<b>Address:</b> {business['address']}\n"
        message += f"<b>Contact:</b> {business['contact']}\n\n"
        message += "<b>Usage:</b>\n"
        message += "/settings name=Your Business Name\n"
        message += "/settings dealer_id=123456789\n"
        message += "/settings address=Your Address\n"
        message += "/settings contact=email@example.com | +972-50-XXXXXXX\n"
        
        await update.message.reply_text(message, parse_mode='HTML')
        return
    
    # Parse settings update
    state = config.load_state()
    updated = []
    
    for arg in args:
        if '=' in arg:
            key, value = arg.split('=', 1)
            key = key.lower()
            
            if key in ['name', 'dealer_id', 'address', 'contact']:
                state['settings']['business'][key] = value
                updated.append(f"{key}: {value}")
            elif key in ['pension_rate', 'study_rate_deductible', 'study_cap_total']:
                try:
                    state['settings']['rates'][key] = float(value)
                    updated.append(f"{key}: {value}")
                except ValueError:
                    await update.message.reply_text(f"❌ Invalid value for {key}: {value}")
                    return
            elif key == 'vat_rate':
                try:
                    state['settings']['rates']['vat_rate'] = float(value)
                    updated.append(f"VAT rate: {float(value)*100:.1f}%")
                except ValueError:
                    await update.message.reply_text(f"❌ Invalid VAT rate: {value}")
                    return
            else:
                await update.message.reply_text(f"❌ Unknown setting: {key}")
                return
    
    if updated:
        config.save_state(state)
        message = "✅ <b>Settings Updated:</b>\n\n"
        for item in updated:
            message += f"• {item}\n"
        await update.message.reply_text(message, parse_mode='HTML')
    else:
        await update.message.reply_text("❌ No valid settings provided")


async def setmonth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set simulation month for testing (time travel)."""
    # Handle both new messages and edited messages
    message = update.message or update.edited_message
    if not message:
        return
        
    args = context.args
        
    if not args:
        state = config.load_state()
        sim_month = state.get("simulation", {}).get("current_month")
        sim_year = state.get("simulation", {}).get("current_year")
        
        if sim_month is None:
            reply = "📅 <b>Simulation Mode: OFF</b>\n\n"
            reply += f"Using real date: {config.get_current_month()}/{config.get_current_year()}\n\n"
        else:
            reply = f"📅 <b>Simulation Mode: ON</b>\n\n"
            reply += f"Simulated date: {sim_month}/{sim_year}\n\n"
        
        reply += "<b>Commands:</b>\n"
        reply += "/setmonth MONTH YEAR — Set specific month\n"
        reply += "/nextmonth — Advance one month\n"
        reply += "/setmonth off — Disable simulation\n\n"
        reply += "<b>Examples:</b>\n"
        reply += "/setmonth 1 2025 — Start at January 2025\n"
        reply += "/nextmonth — Move to next month\n"
        
        await message.reply_text(reply, parse_mode='HTML')
        return
    
    if args[0].lower() == "off":
        state = config.load_state()
        state["simulation"]["current_month"] = None
        state["simulation"]["current_year"] = None
        config.save_state(state)
        await message.reply_text("✅ Simulation mode disabled. Using real date now.")
        return
    
    if len(args) < 2:
        await message.reply_text("❌ Usage: /setmonth MONTH YEAR\nExample: /setmonth 1 2025")
        return
    
    month = int(args[0])
    year = int(args[1])
    
    if not (1 <= month <= 12):
        await message.reply_text("❌ Month must be between 1 and 12")
        return
    
    if not (2020 <= year <= 2030):
        await message.reply_text("❌ Year must be between 2020 and 2030")
        return
    
    state = config.load_state()
    if "simulation" not in state:
        state["simulation"] = {}
    state["simulation"]["current_month"] = month
    state["simulation"]["current_year"] = year
    state["year"] = year  # Update year in state too
    config.save_state(state)
    
    month_names = ["", "January", "February", "March", "April", "May", "June",
                    "July", "August", "September", "October", "November", "December"]
    
    await message.reply_text(
        f"✅ Time travel activated!\n\n"
        f"📅 Simulated date: {month_names[month]} {year}\n"
        f"🔢 Current month: {month}/{year}\n\n"
        f"All commands will now use this date.\n"
        f"Use /nextmonth to advance one month."
    )


async def nextmonth_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Advance to the next month in simulation."""
    state = config.load_state()
    
    if "simulation" not in state:
        state["simulation"] = {}
    
    current_month = state["simulation"].get("current_month")
    current_year = state["simulation"].get("current_year")
    
    if current_month is None:
        # Start simulation from current real month
        current_month = config.get_current_month()
        current_year = config.get_current_year()
    
    # Advance one month
    current_month += 1
    if current_month > 12:
        current_month = 1
        current_year += 1
    
    state["simulation"]["current_month"] = current_month
    state["simulation"]["current_year"] = current_year
    state["year"] = current_year
    config.save_state(state)
    
    month_names = ["", "January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
    
    await update.message.reply_text(
        f"⏭️ Advanced to next month!\n\n"
        f"📅 Current simulated date: {month_names[current_month]} {current_year}\n"
        f"🔢 Month: {current_month}/{current_year}\n\n"
        f"Use /nextmonth to continue, or /summary to see updated calculations."
    )

