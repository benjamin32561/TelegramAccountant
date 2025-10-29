"""
Input validation utilities.
"""

from datetime import datetime
import re


def is_valid_amount(amount: str) -> bool:
    """Check if amount string is valid."""
    try:
        float(amount)
        return True
    except ValueError:
        return False


def parse_amount(amount_str: str) -> float:
    """Parse amount string to float."""
    # Remove currency symbols and whitespace
    cleaned = re.sub(r"[₪$,\s]", "", amount_str)
    return float(cleaned)


def is_valid_month(month: int) -> bool:
    """Check if month is valid (1-12)."""
    return 1 <= month <= 12


def is_valid_year(year: int) -> bool:
    """Check if year is reasonable."""
    current_year = datetime.now().year
    return 2020 <= year <= current_year + 1


def parse_update_command(text: str) -> dict:
    """
    Parse /update command arguments.
    
    Format: /update income=1000 expenses=200 pension=300 study=100
    
    Returns:
        Dictionary with parsed values
    """
    result = {}
    
    # Remove command prefix
    text = text.lower().replace("/update", "").strip()
    
    # Parse key=value pairs
    pattern = r"(\w+)=(\d+(?:\.\d+)?)"
    matches = re.findall(pattern, text)
    
    for key, value in matches:
        if key in ["income", "expenses", "pension", "study"]:
            result[key] = float(value)
    
    return result


def parse_deposit_command(text: str) -> dict:
    """
    Parse /deposit command arguments.
    
    Format: /deposit pension=2000 study=500
    
    Returns:
        Dictionary with parsed values
    """
    result = {}
    
    text = text.lower().replace("/deposit", "").strip()
    
    pattern = r"(pension|study)=(\d+(?:\.\d+)?)"
    matches = re.findall(pattern, text)
    
    for key, value in matches:
        result[key] = float(value)
    
    return result


def validate_invoice_data(data: dict) -> tuple[bool, str]:
    """
    Validate invoice/receipt data.
    
    Returns:
        (is_valid, error_message)
    """
    required_fields = ["amount", "client", "description"]
    
    for field in required_fields:
        if field not in data:
            return False, f"Missing required field: {field}"
    
    try:
        amount = float(data["amount"])
        if amount <= 0:
            return False, "Amount must be positive"
    except (ValueError, TypeError):
        return False, "Invalid amount format"
    
    if not data["client"].strip():
        return False, "Client name cannot be empty"
    
    if not data["description"].strip():
        return False, "Description cannot be empty"
    
    return True, ""


if __name__ == "__main__":
    # Test validators
    print("=== Validator Tests ===")
    print(f"Is valid amount '1000': {is_valid_amount('1000')}")
    print(f"Is valid amount '1,000.50': {is_valid_amount('1,000.50')}")
    print(f"Parse amount '₪1,234.56': {parse_amount('₪1,234.56')}")
    
    update_cmd = "income=15000 expenses=400 pension=2000 study=500"
    print(f"Parse update: {parse_update_command(update_cmd)}")
    
    deposit_cmd = "pension=2000 study=500"
    print(f"Parse deposit: {parse_deposit_command(deposit_cmd)}")

