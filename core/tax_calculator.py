"""
Tax and National Insurance calculation engine for self-employed (osek patur).
Self-employed individuals only pay employee NI + Health (no employer contributions).
"""

from typing import Dict, Any, List


def calculate_national_insurance(
    monthly_income: float, ni_settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate National Insurance and Health Tax for self-employed (osek patur).
    Self-employed individuals only pay the employee portion (no employer contributions).
    
    Args:
        monthly_income: Monthly income (not annual)
        ni_settings: NI configuration from settings
    
    Returns:
        {
            "ni_amount": float,
            "health_amount": float,
            "total_amount": float,
            "effective_rate": float,
            "breakdown": List[Dict]
        }
    """
    thresholds = ni_settings.get("monthly_thresholds", {})
    rates = ni_settings.get("rates", {})
    
    low_threshold = thresholds.get("low", 7522)
    high_threshold = thresholds.get("high", 50695)
    
    # Self-employed rates (employee portion only)
    ni_low_rate = rates.get("ni_low", 0.0104)  # 1.04%
    health_low_rate = rates.get("health_low", 0.0323)  # 3.23%
    ni_high_rate = rates.get("ni_high", 0.07)  # 7%
    health_high_rate = rates.get("health_high", 0.0516)  # 5.16%
    
    # Initialize calculations
    ni_amount = 0
    health_amount = 0
    breakdown = []
    
    # Calculate for income up to low threshold
    if monthly_income > 0:
        income_in_low_bracket = min(monthly_income, low_threshold)
        
        # Self-employed contributions (low bracket)
        ni_low_amount = income_in_low_bracket * ni_low_rate
        health_low_amount = income_in_low_bracket * health_low_rate
        
        ni_amount += ni_low_amount
        health_amount += health_low_amount
        
        if ni_low_amount > 0 or health_low_amount > 0:
            breakdown.append({
                "bracket": f"₪0 - ₪{low_threshold:,.0f}",
                "ni_rate": f"{ni_low_rate*100:.2f}%",
                "health_rate": f"{health_low_rate*100:.2f}%",
                "ni_amount": ni_low_amount,
                "health_amount": health_low_amount,
                "total_amount": ni_low_amount + health_low_amount,
            })
    
    # Calculate for income between low and high thresholds
    if monthly_income > low_threshold:
        income_in_high_bracket = min(monthly_income, high_threshold) - low_threshold
        
        # Self-employed contributions (high bracket)
        ni_high_amount = income_in_high_bracket * ni_high_rate
        health_high_amount = income_in_high_bracket * health_high_rate
        
        ni_amount += ni_high_amount
        health_amount += health_high_amount
        
        if ni_high_amount > 0 or health_high_amount > 0:
            breakdown.append({
                "bracket": f"₪{low_threshold:,.0f} - ₪{high_threshold:,.0f}",
                "ni_rate": f"{ni_high_rate*100:.1f}%",
                "health_rate": f"{health_high_rate*100:.2f}%",
                "ni_amount": ni_high_amount,
                "health_amount": health_high_amount,
                "total_amount": ni_high_amount + health_high_amount,
            })
    
    # Income above high threshold (no additional contributions)
    if monthly_income > high_threshold:
        breakdown.append({
            "bracket": f"₪{high_threshold:,.0f}+",
            "ni_rate": "0.00%",
            "health_rate": "0.00%",
            "ni_amount": 0,
            "health_amount": 0,
            "total_amount": 0,
        })
    
    # Calculate totals (self-employed only pay NI + Health, no employer portion)
    total_amount = ni_amount + health_amount
    effective_rate = total_amount / monthly_income if monthly_income > 0 else 0
    
    return {
        "ni_amount": ni_amount,
        "health_amount": health_amount,
        "total_amount": total_amount,
        "effective_rate": effective_rate,
        "breakdown": breakdown,
    }


def calculate_income_tax(
    income: float, tax_settings: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Calculate income tax with progressive brackets and surtax.
    
    Args:
        income: Taxable income
        tax_settings: Tax configuration from settings
    
    Returns:
        {
            "amount": float,
            "marginal_rate": float,
            "effective_rate": float,
            "credit_points_value": float,
            "net_tax": float,
            "surtax": float,
            "breakdown": List[Dict]
        }
    """
    brackets = tax_settings.get("brackets", [])
    credit_points = tax_settings.get("credit_points", 2.25)
    credit_point_value = tax_settings.get("credit_point_value", 2800)
    surtax_threshold = tax_settings.get("surtax_threshold", 721560)
    surtax_rate = tax_settings.get("surtax_rate", 0.03)
    
    total_tax = 0
    breakdown = []
    
    for bracket in brackets:
        bracket_min = bracket["min"]
        bracket_max = bracket["max"]
        bracket_rate = bracket["rate"]
        
        if income <= bracket_min:
            break
        
        taxable_in_bracket = min(income, bracket_max) - bracket_min
        tax_in_bracket = taxable_in_bracket * bracket_rate
        total_tax += tax_in_bracket
        
        if tax_in_bracket > 0:
            breakdown.append({
                "bracket": f"₪{bracket_min:,.0f} - ₪{bracket_max:,.0f}",
                "rate": f"{bracket_rate*100:.1f}%",
                "amount": tax_in_bracket,
            })
    
    # Calculate surtax (3% on income above 721,560 ILS)
    surtax = 0
    if income > surtax_threshold:
        surtax = (income - surtax_threshold) * surtax_rate
        breakdown.append({
            "bracket": f"₪{surtax_threshold:,.0f}+ (Surtax)",
            "rate": f"{surtax_rate*100:.1f}%",
            "amount": surtax,
        })
    
    total_tax_with_surtax = total_tax + surtax
    
    credit_points_value_calc = credit_points * credit_point_value
    net_tax = max(0, total_tax_with_surtax - credit_points_value_calc)
    
    # Determine marginal rate (highest bracket reached)
    marginal_rate = 0
    for bracket in brackets:
        if income > bracket["min"]:
            marginal_rate = bracket["rate"]
    if income > surtax_threshold:
        marginal_rate += surtax_rate
    
    effective_rate = net_tax / income if income > 0 else 0
    
    return {
        "amount": total_tax_with_surtax,
        "marginal_rate": marginal_rate,
        "effective_rate": effective_rate,
        "credit_points_value": credit_points_value_calc,
        "net_tax": net_tax,
        "surtax": surtax,
        "breakdown": breakdown,
    }


def calculate_comprehensive_tax_analysis(
    net_income: float, 
    tax_settings: Dict[str, Any], 
    ni_settings: Dict[str, Any],
    ni_paid_manually: float = 0
) -> Dict[str, Any]:
    """
    Calculate comprehensive tax analysis for self-employed (osek patur).
    
    Args:
        net_income: Annual net income for tax calculation
        tax_settings: Tax configuration
        ni_settings: National Insurance configuration
        ni_paid_manually: Amount of NI already paid manually (annual)
    
    Returns:
        Comprehensive tax analysis with all calculations
    """
    # Calculate taxes (annual)
    tax_calc = calculate_income_tax(net_income, tax_settings)
    
    # Calculate NI (monthly, then convert to annual) - self-employed only
    monthly_income = net_income / 12
    ni_calc_monthly = calculate_national_insurance(monthly_income, ni_settings)
    
    # Convert monthly NI to annual
    ni_annual = ni_calc_monthly["ni_amount"] * 12
    health_annual = ni_calc_monthly["health_amount"] * 12
    ni_total_annual = ni_calc_monthly["total_amount"] * 12
    
    # Calculate total tax burden (self-employed: income tax + NI + health)
    total_tax_burden = tax_calc["net_tax"] + ni_total_annual
    total_effective_rate = total_tax_burden / net_income if net_income > 0 else 0
    
    # Calculate take-home pay
    take_home_pay = net_income - total_tax_burden
    
    # NI payment analysis
    ni_remaining = max(0, ni_total_annual - ni_paid_manually)
    ni_overpaid = max(0, ni_paid_manually - ni_total_annual)
    
    # Calculate monthly equivalents
    monthly_income_calc = net_income / 12
    monthly_tax = tax_calc["net_tax"] / 12
    monthly_ni_total = ni_total_annual / 12
    monthly_tax_burden = total_tax_burden / 12
    monthly_take_home = take_home_pay / 12
    monthly_ni_paid = ni_paid_manually / 12
    monthly_ni_remaining = ni_remaining / 12
    
    # Create summary comparison
    summary_comparison = {
        "yearly": {
            "income": net_income,
            "tax": tax_calc["net_tax"],
            "ni_employee": ni_total_annual,  # Self-employed pay this (no employer portion)
            "total_burden": total_tax_burden,
            "take_home": take_home_pay,
            "effective_rate": total_effective_rate,
        },
        "monthly": {
            "income": monthly_income_calc,
            "tax": monthly_tax,
            "ni_employee": monthly_ni_total,
            "total_burden": monthly_tax_burden,
            "take_home": monthly_take_home,
            "effective_rate": total_effective_rate,
        },
        "ni_status": {
            "yearly_paid": ni_paid_manually,
            "yearly_due": ni_total_annual,
            "yearly_remaining": ni_remaining,
            "yearly_overpaid": ni_overpaid,
            "monthly_paid": monthly_ni_paid,
            "monthly_due": monthly_ni_total,
            "monthly_remaining": monthly_ni_remaining,
        },
    }
    
    # Calculate percentages for summary
    tax_percentage = (tax_calc["net_tax"] / net_income * 100) if net_income > 0 else 0
    ni_percentage = (ni_total_annual / net_income * 100) if net_income > 0 else 0
    health_percentage = (health_annual / net_income * 100) if net_income > 0 else 0
    
    return {
        "income": {
            "net_income": net_income,
            "take_home_pay": take_home_pay,
            "monthly_income": monthly_income_calc,
            "monthly_take_home": monthly_take_home,
        },
        "tax": {
            "gross_tax": tax_calc["amount"],
            "credit_points_value": tax_calc["credit_points_value"],
            "net_tax": tax_calc["net_tax"],
            "monthly_tax": monthly_tax,
            "surtax": tax_calc["surtax"],
            "marginal_rate": tax_calc["marginal_rate"],
            "effective_rate": tax_calc["effective_rate"],
            "breakdown": tax_calc["breakdown"],
        },
        "national_insurance": {
            "ni_amount": ni_annual,
            "health_amount": health_annual,
            "total_amount": ni_total_annual,
            "monthly_total": monthly_ni_total,
            "effective_rate": ni_calc_monthly["effective_rate"],
            "breakdown": ni_calc_monthly["breakdown"],
            "paid_manually": ni_paid_manually,
            "monthly_paid": monthly_ni_paid,
            "remaining": ni_remaining,
            "monthly_remaining": monthly_ni_remaining,
            "overpaid": ni_overpaid,
        },
        "summary": {
            "total_tax_burden": total_tax_burden,
            "monthly_tax_burden": monthly_tax_burden,
            "total_effective_rate": total_effective_rate,
            "tax_percentage": tax_percentage,
            "ni_percentage": ni_percentage,
            "health_percentage": health_percentage,
            "take_home_pay": take_home_pay,
            "monthly_take_home": monthly_take_home,
        },
        "comparison": summary_comparison,
    }

