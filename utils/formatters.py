"""
Number, date, and currency formatting utilities.
"""

import locale
from datetime import datetime
from typing import Optional


def format_currency(amount: float, with_symbol: bool = True) -> str:
    """
    Format amount as currency.
    
    Args:
        amount: Amount to format
        with_symbol: Include currency symbol (₪)
    
    Returns:
        Formatted string (e.g., "1,234.56" or "₪1,234.56")
    """
    if with_symbol:
        return f"₪{amount:,.2f}"
    else:
        return f"{amount:,.2f}"


def format_amount_simple(amount: float) -> str:
    """Simple amount formatting."""
    return f"{amount:,.2f}"


def format_date(date: Optional[datetime] = None) -> str:
    """
    Format date as YYYY-MM-DD.
    
    Args:
        date: Date to format (defaults to now)
    
    Returns:
        Formatted date string
    """
    if date is None:
        date = datetime.now()
    return date.strftime("%Y-%m-%d")


def format_date_hebrew(date: Optional[datetime] = None) -> str:
    """
    Format date in Hebrew format (DD/MM/YYYY).
    
    Args:
        date: Date to format (defaults to now)
    
    Returns:
        Formatted date string
    """
    if date is None:
        date = datetime.now()
    return date.strftime("%d/%m/%Y")


def format_number_with_k(n: float) -> str:
    """Format large numbers with K abbreviation."""
    if n >= 1000000:
        return f"{n/1000000:.1f}M"
    elif n >= 1000:
        return f"{n/1000:.1f}K"
    else:
        return f"{n:.0f}"


def create_table_row(key: str, value: str, separator: str = " | ") -> str:
    """
    Create a table row for Telegram messages.
    
    Args:
        key: Column key
        value: Column value
        separator: Column separator
    
    Returns:
        Formatted table row
    """
    return f"<code>{key.ljust(30)}{separator}{value}</code>"


def format_two_column_table(headers: tuple, rows: list) -> str:
    """
    Format a two-column table for Telegram.
    
    Args:
        headers: (header1, header2)
        rows: List of (key, value) tuples
    
    Returns:
        Formatted table as HTML
    """
    table = []
    table.append(f"<b>{headers[0]:<30} | {headers[1]}</b>")
    table.append("-" * 60)
    
    for key, value in rows:
        table.append(f"{key:<30} | {value}")
    
    return "\n".join(table)


def format_percentage(value: float, decimals: int = 1) -> str:
    """Format as percentage."""
    return f"{value * 100:.{decimals}f}%"


def format_invoice_id(prefix: str, year: int, number: int) -> str:
    """Format invoice ID (e.g., R-2025-0001)."""
    return f"{prefix}-{year}-{number:04d}"


if __name__ == "__main__":
    # Test formatters
    print("=== Formatter Tests ===")
    print(f"Currency: {format_currency(1234.56)}")
    print(f"Date: {format_date()}")
    print(f"Date (Hebrew): {format_date_hebrew()}")
    print(f"Number with K: {format_number_with_k(15000)}")
    print(f"Percentage: {format_percentage(0.165)}")
    print(f"Invoice ID: {format_invoice_id('R', 2025, 1)}")

