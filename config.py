"""
Configuration management and default settings.
"""

import json
import os
from pathlib import Path
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def get_env_value(key: str, default: str = None, type_func=str):
    """Get environment variable with type conversion and default."""
    value = os.getenv(key, default)
    if value is None:
        return default
    try:
        return type_func(value)
    except (ValueError, TypeError):
        return default


# File paths
ENV_FILE = ".env"
DATA_FOLDER_PATH = get_env_value("DATA_FOLDER_PATH", "0outputs")
os.makedirs(DATA_FOLDER_PATH, exist_ok=True)
STATE_FILE = os.path.join(DATA_FOLDER_PATH, "state.json")
# Legacy ledger file path (kept for backward compatibility)
LEDGER_FILE = os.path.join(DATA_FOLDER_PATH, "ledger.xlsx")

# Default state structure with environment variable overrides
DEFAULT_STATE = {
    "year": get_env_value("INVOICE_YEAR", datetime.now().year, int),
    "months": {
        str(i): {
            "income": 0,
            "expenses": 0,
            "pension": 0,
            "study": 0,
            "ni_paid": 0,
            "tax_paid": 0,
        }
        for i in range(1, 13)
    },
    "totals": {
        "income_ytd": 0,
        "expenses_ytd": 0,
        "net_income_ytd": 0,
        "pension_total": 0,
        "study_total": 0,
    },
    "simulation": {
        "current_month": None,  # None = use real date, or set 1-12 for simulation
        "current_year": None,   # None = use real date, or set year for simulation
    },
    "settings": {
        "locale": get_env_value("LOCALE", "he-IL"),
        "timezone": get_env_value("TIMEZONE", "Asia/Jerusalem"),
        "currency": get_env_value("CURRENCY", "ILS"),
        "business": {
            "name": get_env_value("BUSINESS_NAME", "Ben Akhovan Engineering"),
            "name_en": get_env_value("BUSINESS_NAME_EN", "Ben Akhovan Engineering"),
            "dealer_id": get_env_value("BUSINESS_ID", "XXXXXXXXX"),
            "address": get_env_value("BUSINESS_ADDRESS", "Address, City"),
            "contact": get_env_value("BUSINESS_CONTACT", "email@example.com | +972-50-XXXXXXX"),
        },
        "rates": {
            "vat_rate": get_env_value("VAT_RATE", 0.0, float),
            "pension_rate": get_env_value("PENSION_RATE", 0.165, float),
            "study_rate_deductible": get_env_value("STUDY_RATE_DEDUCTIBLE", 0.045, float),
            "study_cap_total": get_env_value("STUDY_CAP_TOTAL", 20520, float),
            "ni": {
                "monthly_thresholds": {
                    "low": get_env_value("NI_MONTHLY_THRESHOLD_LOW", 7522, float),  # ₪7,522
                    "high": get_env_value("NI_MONTHLY_THRESHOLD_HIGH", 50695, float),  # ₪50,695
                },
                "rates": {
                    # Self-employed only pay employee portion (no employer contributions)
                    "ni_low": get_env_value("NI_RATE_LOW", 0.0104, float),  # 1.04%
                    "health_low": get_env_value("HEALTH_RATE_LOW", 0.0323, float),  # 3.23%
                    "ni_high": get_env_value("NI_RATE_HIGH", 0.07, float),  # 7%
                    "health_high": get_env_value("HEALTH_RATE_HIGH", 0.0516, float),  # 5.16%
                },
            },
            "tax": {
                "brackets": [
                    {"min": 0, "max": 84120, "rate": 0.10},
                    {"min": 84120, "max": 120720, "rate": 0.14},
                    {"min": 120720, "max": 193800, "rate": 0.20},
                    {"min": 193800, "max": 269280, "rate": 0.31},
                    {"min": 269280, "max": 560280, "rate": 0.35},
                    {"min": 560280, "max": 721560, "rate": 0.47},
                    {"min": 721560, "max": float("inf"), "rate": 0.50},  # 50% with surtax
                ],
                "surtax_threshold": 721560,  # Surtax applies above this amount
                "surtax_rate": 0.03,  # 3% surtax
                "credit_points": get_env_value("TAX_CREDIT_POINTS", 2.25, float),
                "credit_point_value": get_env_value("TAX_CREDIT_POINT_VALUE", 2800, float),
            },
        },
        "drive": {
            "root_folder_id": get_env_value("GOOGLE_DRIVE_ROOT_FOLDER_ID"),
            "folders": {
                "invoices": None,
                "receipts": None,
                "expenses": None,
            },
        },
        "invoice_numbering": {
            "year": get_env_value("INVOICE_YEAR", 2025, int),
            "next_receipt": get_env_value("NEXT_RECEIPT_NUMBER", 1, int),
            "next_invoice": get_env_value("NEXT_INVOICE_NUMBER", 1, int),
            "next_expense": get_env_value("NEXT_EXPENSE_NUMBER", 1, int),
        },
        "forecast": {
            "mode": get_env_value("FORECAST_MODE", "balanced"),
            "assumed_monthly_income": None,
        },
    },
}


def load_state(filepath=STATE_FILE):
    """Load state from JSON file."""
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return DEFAULT_STATE.copy()


def save_state(state, filepath=STATE_FILE):
    """Save state to JSON file."""
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def ensure_state_exists():
    """Ensure state file exists, create if not."""
    if not os.path.exists(STATE_FILE):
        save_state(DEFAULT_STATE)
        print(f"Created new state file: {STATE_FILE}")


def get_current_month():
    """Get current month number (1-12), respecting simulation mode."""
    state = load_state()
    sim_month = state.get("simulation", {}).get("current_month")
    if sim_month is not None:
        return int(sim_month)
    return datetime.now().month


def get_current_year():
    """Get current year, respecting simulation mode."""
    state = load_state()
    sim_year = state.get("simulation", {}).get("current_year")
    if sim_year is not None:
        return int(sim_year)
    return datetime.now().year


def get_currency_symbol():
    """Get currency symbol based on locale."""
    return "₪"


def get_tz():
    """Get timezone object."""
    return pytz.timezone("Asia/Jerusalem")


def get_current_year():
    """Get current year."""
    return datetime.now().year


# ============================================================================
# NEW: Organized folder structure helpers
# ============================================================================

def get_year_folder(year: int = None) -> str:
    """Get the folder path for a specific year."""
    if year is None:
        year = get_current_year()
    path = os.path.join(DATA_FOLDER_PATH, str(year))
    os.makedirs(path, exist_ok=True)
    return path


def get_month_folder(year: int = None, month: int = None) -> str:
    """Get the folder path for a specific month."""
    if year is None:
        year = get_current_year()
    if month is None:
        month = get_current_month()
    
    year_path = get_year_folder(year)
    month_str = f"{month:02d}"  # Format as 01, 02, ..., 12
    path = os.path.join(year_path, month_str)
    os.makedirs(path, exist_ok=True)
    return path


def get_receipts_folder(year: int = None, month: int = None) -> str:
    """Get the receipts folder for a specific month."""
    month_path = get_month_folder(year, month)
    path = os.path.join(month_path, "receipts")
    os.makedirs(path, exist_ok=True)
    return path


def get_expenses_folder(year: int = None, month: int = None) -> str:
    """Get the expenses folder for a specific month."""
    month_path = get_month_folder(year, month)
    path = os.path.join(month_path, "expenses")
    os.makedirs(path, exist_ok=True)
    return path


def get_yearly_ledger_path(year: int = None) -> str:
    """Get the yearly ledger file path."""
    if year is None:
        year = get_current_year()
    year_path = get_year_folder(year)
    return os.path.join(year_path, f"ledger_{year}.xlsx")


def get_monthly_ledger_path(year: int = None, month: int = None) -> str:
    """Get the monthly ledger file path."""
    if year is None:
        year = get_current_year()
    if month is None:
        month = get_current_month()
    
    month_path = get_month_folder(year, month)
    month_str = f"{month:02d}"
    return os.path.join(month_path, f"ledger_{year}_{month_str}.xlsx")


def get_receipt_path(receipt_id: str, year: int = None, month: int = None) -> str:
    """Get the full path for a receipt PDF."""
    receipts_folder = get_receipts_folder(year, month)
    return os.path.join(receipts_folder, f"{receipt_id}.pdf")


def get_expense_path(expense_id: str, year: int = None, month: int = None) -> str:
    """Get the full path for an expense PDF."""
    expenses_folder = get_expenses_folder(year, month)
    return os.path.join(expenses_folder, f"{expense_id}.pdf")


def get_invoices_folder(year: int = None, month: int = None) -> str:
    """Get the invoices folder for a specific month (receipts are income, invoices are for billing)."""
    month_path = get_month_folder(year, month)
    path = os.path.join(month_path, "invoices")
    os.makedirs(path, exist_ok=True)
    return path


def get_invoice_path(invoice_id: str, year: int = None, month: int = None) -> str:
    """Get the full path for an invoice PDF."""
    invoices_folder = get_invoices_folder(year, month)
    return os.path.join(invoices_folder, f"{invoice_id}.pdf")


if __name__ == "__main__":
    # Test creating default state
    ensure_state_exists()
    state = load_state()
    print("State loaded successfully!")
    print(f"Year: {state['year']}")
    print(f"Business: {state['settings']['business']['name']}")

