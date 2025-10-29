# Unified Telegram Finance Bot — "Exempt/Morasha Pro"

A comprehensive Telegram bot for self-employed individuals in Israel to manage finances, generate invoices, archive documents, and optimize tax deductions.

## Features

- 📊 **Financial Tracking**: Log income, expenses, pension, and study fund deposits
- 🧾 **Invoice Generation**: Create PDF invoices/receipts with VAT support
- 📁 **Google Drive Integration**: Auto-archive documents with structured folders
- 💰 **Tax Optimization**: Calculate deductible limits and monthly recommendations
- 📈 **Projections**: Forecast year-end positions and December top-up strategies
- 🌍 **Bilingual**: Hebrew and English support

## Project Structure

```
TelegramAccountant/
├── bot.py                    # Main bot entry point
├── config.py                 # Configuration management
├── state.json                # State persistence (auto-created)
├── .env                      # Environment variables (create this)
├── requirements.txt          # Python dependencies
├── pdf_tester.py            # PDF format testing tool
├── core/
│   ├── calculator.py        # Financial calculations
│   ├── tax_calculator.py    # Tax and NI calculations
│   └── optimizer.py         # Deduction optimizer
├── handlers/
│   ├── commands.py          # Bot command handlers
│   ├── callbacks.py         # Button/callback handlers
│   └── document_handler.py  # Document upload workflows
├── services/
│   ├── drive_service.py     # Google Drive integration
│   ├── ledger_service.py    # Excel ledger management
│   └── pdf_service.py       # PDF generation service
├── utils/
│   ├── formatters.py        # Number/date formatting
│   └── validators.py        # Input validation
└── credentials/
    └── service_account.json  # Google Service Account (add manually)
```

## Setup

### 1. Environment Setup

```bash
# Activate conda environment
conda activate ta_env

# Install dependencies
pip install -r requirements.txt
```

### 2. Environment Configuration

1. Copy the environment template:
```bash
cp env_template.txt .env
```

2. Edit `.env` file with your actual values:

3. Get your Telegram Bot Token:
   - Create a bot via [@BotFather](https://t.me/botfather)
   - Get your bot token and add it to `.env`

### 3. Initialize State

Run the bot once to auto-create `state.json` with defaults from your `.env` file.

## Usage

### Core Commands

- `/update income=15000 expenses=400` - Update monthly values
- `/deposit pension=2000 study=500` - Record deposits
- `/summary` - View YTD state and recommendations
- `/projection` - Forecast year-end position
- `/optimizer` - December top-up recommendations
- `/receipt 2016 ClientName Service description` - Generate receipt
- `/expense 150 vendor description` - Upload expense document

See `/help` for full command list.

## Development

### Testing PDF Generation

```bash
python pdf_tester.py
```

This will generate sample invoices in both Hebrew and English for format comparison.

### Running the Bot

```bash
python bot.py
```

## Configuration

Edit `state.json` to customize:
- Business details
- Tax rates and brackets
- Pension/study fund rates
- Drive folder structure

## Roadmap

- [ ] OCR for expense receipts
- [ ] Bank CSV/OFX import
- [ ] Multi-user support
- [ ] Charts and visualizations
- [ ] Google Sheets live ledger

