"""
Core financial calculation engine.
Calculates YTD aggregations, caps, remaining room, and recommendations.
"""

from datetime import datetime
from typing import Dict, Any
from core import tax_calculator


def calculate_ytd_totals(state: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate year-to-date totals.
    
    Returns:
        {
            "income_ytd": float,
            "expenses_ytd": float,
            "net_income_ytd": float,
            "pension_total": float,
            "study_total": float,
            "months_left": int
        }
    """
    months_data = state.get("months", {})
    # Use simulation month if set, otherwise use current month
    sim_month = state.get("simulation", {}).get("current_month")
    current_month = sim_month if sim_month is not None else datetime.now().month
    
    totals = {
        "income_ytd": 0,
        "expenses_ytd": 0,
        "pension_total": 0,
        "study_total": 0,
        "months_left": 12 - current_month + 1,  # Including current month
    }
    
    for month_num, month_data in months_data.items():
        totals["income_ytd"] += month_data.get("income", 0)
        totals["expenses_ytd"] += month_data.get("expenses", 0)
        totals["pension_total"] += month_data.get("pension", 0)
        totals["study_total"] += month_data.get("study", 0)
    
    totals["net_income_ytd"] = totals["income_ytd"] - totals["expenses_ytd"]
    
    return totals


def calculate_caps(net_income_ytd: float, settings: Dict[str, Any]) -> Dict[str, float]:
    """
    Calculate deductible caps based on net income.
    
    Returns:
        {
            "pension_cap": float,
            "study_deductible_cap": float,
            "study_total_cap": float
        }
    """
    rates = settings.get("rates", {})
    
    pension_rate = rates.get("pension_rate", 0.165)
    study_rate_deductible = rates.get("study_rate_deductible", 0.045)
    study_cap_total = rates.get("study_cap_total", 20520)
    
    return {
        "pension_cap": net_income_ytd * pension_rate,
        "study_deductible_cap": net_income_ytd * study_rate_deductible,
        "study_total_cap": study_cap_total,
    }


def calculate_remaining_room(
    caps: Dict[str, float], pension_total: float, study_total: float
) -> Dict[str, float]:
    """
    Calculate remaining deductible room.
    
    Returns:
        {
            "pension_remaining": float,
            "study_deductible_remaining": float,
            "study_total_remaining": float
        }
    """
    pension_deductible_deposited = min(pension_total, caps["pension_cap"])
    
    # Study fund: what's deductible vs non-deductible
    study_deductible_deposited = min(study_total, caps["study_deductible_cap"])
    
    return {
        "pension_remaining": max(0, caps["pension_cap"] - pension_total),
        "study_deductible_remaining": max(
            0, caps["study_deductible_cap"] - study_total
        ),
        "study_total_remaining": max(0, caps["study_total_cap"] - study_total),
    }


def calculate_monthly_suggestions(
    remaining: Dict[str, float], months_left: int, mode: str = "balanced"
) -> Dict[str, float]:
    """
    Calculate monthly deposit suggestions.
    
    Args:
        remaining: Remaining room calculations
        months_left: Number of months remaining in year
        mode: 'balanced', 'aggressive', or 'conservative'
    
    Returns:
        {
            "pension": float,
            "study_deductible": float,
            "study_total": float
        }
    """
    if months_left <= 0:
        return {"pension": 0, "study_deductible": 0, "study_total": 0}
    
    pension_next = remaining["pension_remaining"] / months_left
    study_deductible_next = remaining["study_deductible_remaining"] / months_left
    study_total_next = remaining["study_total_remaining"] / months_left
    
    if mode == "aggressive":
        # Front-load everything
        return {
            "pension": remaining["pension_remaining"],
            "study_deductible": remaining["study_deductible_remaining"],
            "study_total": remaining["study_total_remaining"],
        }
    elif mode == "conservative":
        # Half the balanced amount
        return {
            "pension": pension_next / 2,
            "study_deductible": study_deductible_next / 2,
            "study_total": study_total_next / 2,
        }
    else:  # balanced
        return {
            "pension": pension_next,
            "study_deductible": study_deductible_next,
            "study_total": study_total_next,
        }


def calculate_deductible_analysis(
    pension_total: float,
    study_total: float,
    caps: Dict[str, float],
) -> Dict[str, Any]:
    """
    Analyze what portion of deposits is deductible.
    
    Returns:
        {
            "pension": {
                "total": float,
                "deductible": float,
                "non_deductible": float
            },
            "study": {
                "total": float,
                "deductible": float,
                "non_deductible_tax_free": float
            }
        }
    """
    pension_deductible = min(pension_total, caps["pension_cap"])
    pension_non_deductible = max(0, pension_total - caps["pension_cap"])
    
    study_deductible = min(study_total, caps["study_deductible_cap"])
    study_non_deductible_portion = max(0, study_total - caps["study_deductible_cap"])
    # Tax-free portion: up to the total cap minus deductible cap (₪20,520 - deductible_cap)
    max_tax_free_allowed = max(0, caps["study_total_cap"] - caps["study_deductible_cap"])
    study_non_deductible_tax_free = min(study_non_deductible_portion, max_tax_free_allowed)
    
    return {
        "pension": {
            "total": pension_total,
            "deductible": pension_deductible,
            "non_deductible": pension_non_deductible,
        },
        "study": {
            "total": study_total,
            "deductible": study_deductible,
            "non_deductible_tax_free": study_non_deductible_tax_free,
        },
    }


def calculate_full_analysis(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Complete analysis calculation pipeline.
    
    Returns a comprehensive dictionary with all calculations.
    """
    totals = calculate_ytd_totals(state)
    caps = calculate_caps(totals["net_income_ytd"], state["settings"])
    remaining = calculate_remaining_room(caps, totals["pension_total"], totals["study_total"])
    
    forecast_mode = state["settings"].get("forecast", {}).get("mode", "balanced")
    suggestions_balanced = calculate_monthly_suggestions(remaining, totals["months_left"], "balanced")
    suggestions_aggressive = calculate_monthly_suggestions(remaining, totals["months_left"], "aggressive")
    suggestions_conservative = calculate_monthly_suggestions(remaining, totals["months_left"], "conservative")
    
    deductible_analysis = calculate_deductible_analysis(
        totals["pension_total"], totals["study_total"], caps
    )
    
    # Calculate comprehensive tax analysis
    tax_settings = state["settings"]["rates"]["tax"]
    ni_settings = state["settings"]["rates"]["ni"]
    ni_paid_manually = state.get("totals", {}).get("ni_paid_manually", 0)
    
    tax_analysis = tax_calculator.calculate_comprehensive_tax_analysis(
        totals["net_income_ytd"], tax_settings, ni_settings, ni_paid_manually
    )
    
    return {
        "totals": totals,
        "caps": caps,
        "remaining": remaining,
        "suggestions": {
            "balanced": suggestions_balanced,
            "aggressive": suggestions_aggressive,
            "conservative": suggestions_conservative,
        },
        "deductible_analysis": deductible_analysis,
        "tax_analysis": tax_analysis,
    }


if __name__ == "__main__":
    # Test calculations
    from config import load_state
    
    state = load_state()
    analysis = calculate_full_analysis(state)
    
    print("=== Financial Analysis ===")
    print(f"Net Income YTD: ₪{analysis['totals']['net_income_ytd']:,.2f}")
    print(f"Pension Cap: ₪{analysis['caps']['pension_cap']:,.2f}")
    print(f"Pension Remaining: ₪{analysis['remaining']['pension_remaining']:,.2f}")
    print(f"\nBalanced Monthly Suggestions:")
    print(f"  Pension: ₪{analysis['suggestions']['balanced']['pension']:,.2f}")
    print(f"  Study (deductible): ₪{analysis['suggestions']['balanced']['study_deductible']:,.2f}")

