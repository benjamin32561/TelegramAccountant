"""
PDF generation service for invoices and receipts using WeasyPrint.
"""

from weasyprint import HTML, CSS
from weasyprint.text.fonts import FontConfiguration
from datetime import datetime
from typing import Dict, Any, Optional
from jinja2 import Template
import os


INVOICE_TEMPLATE = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
    <meta charset="UTF-8">
    <style>
        @page {
            size: A4;
            margin: 20mm;
        }
        
        body {
            font-family: 'Arial', 'Helvetica', sans-serif;
            direction: rtl;
            text-align: right;
            margin: 0;
            padding: 0;
            color: #333;
        }
        
        .container {
            max-width: 100%;
            margin: 0 auto;
        }
        
        .header {
            border-bottom: 3px solid #2c3e50;
            padding-bottom: 15px;
            margin-bottom: 30px;
        }
        
        .header h1 {
            color: #2c3e50;
            margin: 0;
            font-size: 28px;
            font-weight: bold;
        }
        
        .business-info {
            display: inline-block;
            vertical-align: top;
            width: 48%;
            margin-left: 2%;
        }
        
        .invoice-info {
            display: inline-block;
            vertical-align: top;
            width: 48%;
            margin-right: 2%;
        }
        
        .info-box {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            margin-bottom: 20px;
        }
        
        .info-box h3 {
            margin: 0 0 10px 0;
            color: #2c3e50;
            font-size: 16px;
            border-bottom: 2px solid #3498db;
            padding-bottom: 5px;
        }
        
        .info-row {
            margin: 8px 0;
            font-size: 13px;
        }
        
        .info-label {
            font-weight: bold;
            color: #555;
            display: inline-block;
            width: 80px;
        }
        
        .info-value {
            color: #222;
        }
        
        .items-table {
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 13px;
        }
        
        .items-table th {
            background: #2c3e50;
            color: white;
            padding: 12px;
            text-align: right;
            font-weight: bold;
        }
        
        .items-table td {
            padding: 10px;
            border-bottom: 1px solid #ddd;
        }
        
        .items-table tr:hover {
            background: #f5f5f5;
        }
        
        .amount-cell {
            text-align: left;
            font-weight: bold;
        }
        
        .description-cell {
            text-align: right;
            max-width: 300px;
        }
        
        .totals-section {
            margin-top: 30px;
            text-align: left;
            float: left;
            width: 300px;
        }
        
        .total-row {
            padding: 8px 15px;
            font-size: 14px;
        }
        
        .total-row.total-final {
            background: #2c3e50;
            color: white;
            font-size: 18px;
            font-weight: bold;
            border-radius: 5px;
            margin-top: 5px;
        }
        
        .total-label {
            display: inline-block;
            width: 150px;
        }
        
        .total-value {
            text-align: left;
            font-weight: bold;
        }
        
        .footer {
            margin-top: 80px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            text-align: center;
            color: #888;
            font-size: 12px;
        }
        
        .vat-note {
            background: #fff3cd;
            border: 1px solid #ffc107;
            border-radius: 5px;
            padding: 10px;
            margin-top: 15px;
            text-align: right;
            font-size: 12px;
            color: #856404;
        }
        
        .bilingual-label {
            font-size: 11px;
            color: #666;
            margin-top: 5px;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>חשבונית / INVOICE</h1>
        </div>
        
        <div class="business-info">
            <div class="info-box">
                <h3>פרטי העסק / Business Details</h3>
                <div class="info-row">
                    <span class="info-label">שם:</span>
                    <span class="info-value">{{ business_name }}</span>
                    <div class="bilingual-label">{{ business_name_en }}</div>
                </div>
                <div class="info-row">
                    <span class="info-label">ח.פ.:</span>
                    <span class="info-value">{{ business_id }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">כתובת:</span>
                    <span class="info-value">{{ business_address }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">טלפון:</span>
                    <span class="info-value">{{ business_contact }}</span>
                </div>
            </div>
        </div>
        
        <div class="invoice-info">
            <div class="info-box">
                <h3>פרטי החשבונית / Invoice Details</h3>
                <div class="info-row">
                    <span class="info-label">מספר:</span>
                    <span class="info-value" style="font-size: 16px; font-weight: bold; color: #2c3e50;">{{ invoice_id }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">תאריך:</span>
                    <span class="info-value">{{ invoice_date }}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">לקוח:</span>
                    <span class="info-value">{{ client_name }}</span>
                </div>
            </div>
        </div>
        
        <div style="clear: both;"></div>
        
        <table class="items-table">
            <thead>
                <tr>
                    <th style="text-align: center;">#</th>
                    <th>תיאור / Description</th>
                    {% if vat_rate > 0 %}
                    <th style="text-align: left;">מחיר לפני מע״מ</th>
                    <th style="text-align: left;">מע״מ</th>
                    {% endif %}
                    <th style="text-align: left;">סכום / Amount</th>
                </tr>
            </thead>
            <tbody>
                <tr>
                    <td style="text-align: center;">1</td>
                    <td class="description-cell">
                        {{ description }}
                        <div class="bilingual-label">{{ description_en }}</div>
                    </td>
                    {% if vat_rate > 0 %}
                    <td class="amount-cell">₪{{ "{:,.2f}".format(subtotal) }}</td>
                    <td class="amount-cell">₪{{ "{:,.2f}".format(vat_amount) }}</td>
                    {% endif %}
                    <td class="amount-cell" style="font-size: 15px; color: #2c3e50;">₪{{ "{:,.2f}".format(total) }}</td>
                </tr>
            </tbody>
        </table>
        
        <div style="clear: both;"></div>
        
        <div class="totals-section" dir="ltr">
            {% if vat_rate > 0 %}
            <div class="total-row">
                <span class="total-label">Subtotal:</span>
                <span class="total-value">₪{{ "{:,.2f}".format(subtotal) }}</span>
            </div>
            <div class="total-row">
                <span class="total-label">VAT ({{ vat_percent }}%):</span>
                <span class="total-value">₪{{ "{:,.2f}".format(vat_amount) }}</span>
            </div>
            {% endif %}
            <div class="total-row total-final">
                <span class="total-label">Total / סה״כ:</span>
                <span class="total-value">₪{{ "{:,.2f}".format(total) }}</span>
            </div>
        </div>
        
        {% if vat_rate == 0 %}
        <div class="vat-note">
            פטור ממע״מ על פי פקודת המסים | VAT Exempt under Section 34
        </div>
        {% endif %}
        
        <div class="footer">
            <p>תודה על עסקתכם | Thank you for your business</p>
            <p>נוצר באמצעות Exempt/Morasha Pro | Generated by Exempt/Morasha Pro</p>
        </div>
    </div>
</body>
</html>
"""

RECEIPT_TEMPLATE = """
<!DOCTYPE html>
<html lang="he" dir="rtl">
<head>
  <meta charset="UTF-8">
  <style>
    @page { size: A4; margin: 18mm; }
    /* Embed Hebrew-friendly fonts (falls back cleanly if unavailable) */
    body {
      font-family: 'Rubik', 'Noto Sans Hebrew', 'Arial', 'Helvetica', sans-serif;
      direction: rtl; text-align: right; margin: 0; color: #222;
      line-height: 1.45;
    }
    .container { max-width: 100%; }
    .header { border-bottom: 2px solid #2c3e50; padding-bottom: 12px; margin-bottom: 20px; display: flex; align-items: center; justify-content: space-between; gap: 12px; }
    .title-block { display: flex; flex-direction: column; }
    .title { font-size: 26px; margin: 0; color: #2c3e50; font-weight: 700; }
    .subtitle { font-size: 12px; color: #666; margin-top: 2px; }

    .info-wrap { display: flex; gap: 16px; margin-top: 10px; }
    .box { flex: 1; background: #f7f8fa; border-radius: 6px; padding: 12px 14px; }
    .box h3 { margin: 0 0 8px 0; font-size: 15px; color: #2c3e50; border-bottom: 1.5px solid #e0e6eb; padding-bottom: 6px; }
    .row { margin: 6px 0; font-size: 13px; }
    .label { font-weight: 600; color: #555; display: inline-block; min-width: 92px; }
    .value { color: #222; }

    .section { margin-top: 18px; }
    .desc { background: #fff; border: 1px solid #e9ecef; border-radius: 6px; padding: 12px; font-size: 13px; }
    .desc .bilingual { font-size: 11px; color: #666; margin-top: 4px; }

    .amount { margin-top: 18px; display: flex; justify-content: flex-start; }
    .card { border-radius: 8px; padding: 12px 16px; background: #2c3e50; color: #fff; font-weight: 700; font-size: 18px; }
    .card .label { color: #cfd8dc; min-width: auto; }
    .ltr { direction: ltr; unicode-bidi: plaintext; }

    .note { margin-top: 12px; font-size: 12px; color: #6c757d; }
    .paid { margin-top: 8px; display: inline-block; font-size: 12px; background: #e6f4ea; color: #0f5132; border: 1px solid #badbcc; border-radius: 4px; padding: 6px 8px; }

    .footer { margin-top: 60px; padding-top: 14px; border-top: 1.5px solid #e0e0e0; text-align: center; color: #777; font-size: 11px; }
    .logo { max-height: 38px; object-fit: contain; }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div class="title-block">
        <h1 class="title">קבלה / RECEIPT</h1>
        <div class="subtitle">מסמך המאשר קבלת תשלום / Payment confirmation</div>
      </div>
      {% if business_logo %}
        <img class="logo" src="{{ business_logo }}" alt="logo" />
      {% endif %}
    </div>

    <div class="info-wrap">
      <div class="box">
        <h3>פרטי העסק / Business</h3>
        <div class="row"><span class="label">שם:</span><span class="value">{{ business_name }}</span></div>
        <div class="row"><span class="label">ח.פ.:</span><span class="value">{{ business_id }}</span></div>
        <div class="row"><span class="label">כתובת:</span><span class="value">{{ business_address }}</span></div>
        <div class="row"><span class="label">טלפון:</span><span class="value">{{ business_contact }}</span></div>
      </div>
      <div class="box">
        <h3>פרטי קבלה / Receipt</h3>
        <div class="row"><span class="label">מס׳ קבלה:</span><span class="value" style="font-weight:700">{{ receipt_id }}</span></div>
        <div class="row"><span class="label">תאריך:</span><span class="value">{{ receipt_date }}</span></div>
        <div class="row"><span class="label">התקבל מ:</span><span class="value">{{ client_name }}</span></div>
        {% if payment_method %}
        <div class="row"><span class="label">אמצעי תשלום:</span><span class="value">{{ payment_method }}</span></div>
        {% endif %}
        {% if payment_ref %}
        <div class="row"><span class="label">אסמכתא:</span><span class="value">{{ payment_ref }}</span></div>
        {% endif %}
      </div>
    </div>

    <div class="section desc">
      <div>{{ description }}</div>
      {% if description_en %}<div class="bilingual">{{ description_en }}</div>{% endif %}
    </div>

    <div class="amount">
      <div class="card">
        <span class="label">סכום שהתקבל / Amount received:&nbsp;</span>
        <span class="ltr">₪{{ "{:,.2f}".format(total) }}</span>
      </div>
    </div>

    {% if vat_rate > 0 %}
      <div class="note">הסכום כולל מע״מ {{ vat_percent }}% / Amount includes VAT {{ vat_percent }}%.</div>
    {% else %}
      <div class="note">פטור ממע״מ על פי פקודת המסים (ס׳ 34) / VAT exempt (Section 34).</div>
    {% endif %}
    <span class="paid">שולם במלואו / Paid in full</span>

    <div class="footer">
      תודה על העסקה | Thank you for your business · נוצר באמצעות Exempt/Morasha Pro | Generated by Exempt/Morasha Pro
    </div>
  </div>
</body>
</html>
"""


class PDFService:
    """Service for generating PDF invoices and receipts using WeasyPrint."""
    
    def __init__(self):
        """Initialize PDF service."""
        pass
    
    def generate_invoice(
        self,
        output_path: str,
        invoice_id: str,
        client: str,
        amount: float,
        description: str,
        business_info: Dict[str, str],
        vat_rate: float = 0.0,
        date: Optional[datetime] = None,
        description_en: Optional[str] = None,
    ) -> bool:
        """
        Generate professional invoice/receipt PDF using WeasyPrint.
        
        Args:
            output_path: Output file path
            invoice_id: Invoice ID (e.g., R-2025-0001)
            client: Client name
            amount: Invoice amount
            description: Item description (Hebrew)
            business_info: Business details dict
            vat_rate: VAT rate (0.0 for exempt)
            date: Invoice date (defaults to today)
            description_en: English description (optional)
        
        Returns:
            True if successful
        """
        try:
            if date is None:
                date = datetime.now()
            
            # Ensure output directory exists
            os.makedirs(os.path.dirname(output_path) if os.path.dirname(output_path) else ".", exist_ok=True)
            
            # Calculate VAT
            if vat_rate > 0:
                subtotal = amount / (1 + vat_rate)
                vat_amount = amount - subtotal
                vat_percent = int(vat_rate * 100)
            else:
                subtotal = amount
                vat_amount = 0
                vat_percent = 0
            
            # Format date
            date_str = date.strftime("%d/%m/%Y")
            
            # Render HTML from template
            template = Template(INVOICE_TEMPLATE)
            
            html_content = template.render(
                invoice_id=invoice_id,
                invoice_date=date_str,
                client_name=client,
                description=description,
                description_en=description_en or description,
                business_name=business_info.get('name', ''),
                business_name_en=business_info.get('name', ''),  # You can add separate EN name if needed
                business_id=business_info.get('dealer_id', ''),
                business_address=business_info.get('address', ''),
                business_contact=business_info.get('contact', ''),
                total=amount,
                subtotal=subtotal,
                vat_amount=vat_amount,
                vat_rate=vat_rate,
                vat_percent=vat_percent,
            )
            
            # Generate PDF with font configuration
            font_config = FontConfiguration()
            HTML(string=html_content).write_pdf(output_path, font_config=font_config)
            
            print(f"✅ Generated professional invoice: {output_path}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to generate invoice: {e}")
            import traceback
            traceback.print_exc()
            return False

    def generate_receipt(
        self,
        output_path: str,
        receipt_id: str,
        client: str,
        amount: float,
        description: str,
        business_info: Dict[str, str],
        date: Optional[datetime] = None,
        description_en: Optional[str] = None,
        payment_method: Optional[str] = None,   # e.g., "Bank transfer"
        payment_ref: Optional[str] = None,      # e.g., last 4 digits / tx id
        vat_rate: float = 0.0,
        logo_path: Optional[str] = None,        # optional logo image path or data URI
    ) -> bool:
        """Generate a clean receipt PDF."""
        try:
            date = date or datetime.now()
            os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

            subtotal = amount / (1 + vat_rate) if vat_rate > 0 else amount
            vat_amount = amount - subtotal if vat_rate > 0 else 0.0
            vat_percent = int(vat_rate * 100)

            tpl = Template(RECEIPT_TEMPLATE)
            html_content = tpl.render(
                receipt_id=receipt_id,
                receipt_date=date.strftime("%d/%m/%Y"),
                client_name=client,
                description=description,
                description_en=description_en,
                business_name=business_info.get("name", ""),
                business_id=business_info.get("dealer_id", ""),
                business_address=business_info.get("address", ""),
                business_contact=business_info.get("contact", ""),
                business_logo=logo_path,
                total=amount,
                subtotal=subtotal,
                vat_amount=vat_amount,
                vat_rate=vat_rate,
                vat_percent=vat_percent,
                payment_method=payment_method,
                payment_ref=payment_ref,
            )

            font_config = FontConfiguration()
            HTML(string=html_content).write_pdf(
                output_path,
                font_config=font_config  # ensures proper font embedding
            )
            print(f"✅ Generated receipt: {output_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to generate receipt: {e}")
            import traceback; traceback.print_exc()
            return False


if __name__ == "__main__":
    # Test PDF generation
    service = PDFService()
    
    business_info = {
        "name": "Ben Akhovan",
        "dealer_id": "213531254",
        "address": "Kfar Yehezkel, Israel",
        "contact": "ben32561@gmail.com | 053-5292405",
    }
    
    service.generate_invoice(
        output_path="test_invoice.pdf",
        invoice_id="R-2025-0001",
        client="Algolight Ltd. / אלגולייט בע״מ",
        amount=2016.00,
        description="שירותים חודש ספטמבר 2025",
        description_en="September 2025 Services",
        business_info=business_info,
        vat_rate=0.0,
    )
    
    print("\n✅ Test invoice generated: test_invoice.pdf")
    print("   Open it to see the professional formatting!")
