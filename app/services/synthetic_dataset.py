import csv
import io
import json
import random
import uuid
import zipfile
from datetime import datetime, timezone, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import List, Dict, Any, Optional

import pandas as pd
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

from app.config import settings
from app.services.privacy_redaction import VERHOEFF_D, VERHOEFF_P, validate_verhoeff

# Verhoeff Multiplicative Inversion table
VERHOEFF_INV = [0, 4, 3, 2, 1, 5, 6, 7, 8, 9]

SAMPLE_FIRST_NAMES_MALE = [
    "Rajesh", "Vikram", "Aditya", "Amit", "Rahul", "Siddharth", "Arjun", "Karan", "Rohan", "Sanjay",
    "Deepak", "Manoj", "Pranav", "Gaurav", "Naveen", "Abhishek", "Harish", "Suresh", "Vishal", "Alok",
    "Varun", "Sunil", "Manish", "Ankit", "Tarun", "Kartik", "Sachin", "Dinesh", "Ashwin", "Hemant"
]
SAMPLE_FIRST_NAMES_FEMALE = [
    "Pooja", "Ananya", "Priyanka", "Sneha", "Kavita", "Sunita", "Deepika", "Neha", "Meera", "Swati",
    "Divya", "Ritu", "Shreya", "Aditi", "Pallavi", "Nandini", "Aarti", "Tanvi", "Preeti", "Suman",
    "Rupali", "Komal", "Isha", "Bhavna", "Gayatri", "Sangeeta", "Archana", "Rashmi", "Shalini", "Jyoti"
]
SAMPLE_LAST_NAMES = [
    "Sharma", "Patel", "Verma", "Deshmukh", "Iyer", "Reddy", "Nair", "Malhotra", "Joshi", "Sundaram",
    "Chopra", "Gupta", "Bose", "Menon", "Kulkarni", "Mehta", "Bhat", "Rao", "Saxena", "Choudhury",
    "Sen", "Hegde", "Mishra", "Pandey", "Chatterjee", "Banerjee", "Agarwal", "Bhattacharya", "Pillai", "Nambiar"
]
BLOOD_GROUPS = ["O+", "A+", "B+", "AB+", "O-", "A-", "B-", "AB-"]
GENDERS = ["Male", "Female", "Non-binary"]

CITIES_STATES = [
    ("Bengaluru", "Karnataka", 560001, 560099),
    ("Mumbai", "Maharashtra", 400001, 400099),
    ("Hyderabad", "Telangana", 500001, 500099),
    ("New Delhi", "Delhi NCR", 110001, 110099),
    ("Pune", "Maharashtra", 411001, 411099),
    ("Chennai", "Tamil Nadu", 600001, 600099),
    ("Kolkata", "West Bengal", 700001, 700099),
    ("Ahmedabad", "Gujarat", 380001, 380099),
    ("Kochi", "Kerala", 682001, 682099),
    ("Jaipur", "Rajasthan", 302001, 302099)
]

EMPLOYERS = [
    "Tata Consultancy Services", "Infosys Technologies", "Wipro Limited", "HDFC Bank",
    "ICICI Bank", "Larsen & Toubro", "Reliance Industries", "Cognizant India",
    "State Bank of India", "Bharat Electronics Ltd", "Persistent Systems", "Zoho Corporation"
]

DEPARTMENTS = [
    "Information Security & Cryptography", "Financial Crime & AML", "Biometric Identity Governance",
    "Cloud Platform Engineering", "SOC Incident Response", "Data Protection & Legal Compliance",
    "Core Banking Systems", "Artificial Intelligence & Threat Intelligence"
]

DESIGNATIONS = [
    "Chief Risk Officer", "Lead ML Research Engineer", "Senior Threat Forensic Analyst",
    "Principal Cybersecurity Architect", "Data Protection Compliance Officer", "SOC Incident Commander",
    "Cloud Security Lead", "Digital Forensics Specialist", "Identity & Access Manager"
]

BANKS = [
    ("State Bank of India", "SBIN000"),
    ("HDFC Bank", "HDFC000"),
    ("ICICI Bank", "ICIC000"),
    ("Axis Bank", "UTIB000"),
    ("Kotak Mahindra Bank", "KKBK000"),
    ("Punjab National Bank", "PUNB000")
]


def generate_verhoeff_aadhaar() -> str:
    """Generates a 12-digit Aadhaar number that strictly passes Verhoeff checksum validation."""
    first_digit = str(random.randint(2, 9))
    body = "".join([str(random.randint(0, 9)) for _ in range(10)])
    num11 = first_digit + body
    c = 0
    for i, item in enumerate(reversed(num11)):
        c = VERHOEFF_D[c][VERHOEFF_P[(i + 1) % 8][int(item)]]
    checksum = VERHOEFF_INV[c]
    num12 = num11 + str(checksum)
    return f"{num12[:4]} {num12[4:8]} {num12[8:12]}"


def generate_pan_card() -> str:
    """Generates a standard Indian Income Tax PAN card number."""
    letters = "ABCDEFGHJKLMNPQRSTUVWXYZ"
    first4 = "".join(random.choices(letters, k=4))
    status = "P"  # Individual
    digits = f"{random.randint(1000, 9999)}"
    last = random.choice(letters)
    return f"{first4}{status}{digits}{last}"


def generate_passport_no() -> str:
    letter = random.choice("JTKMNPRST")
    digits = f"{random.randint(1000000, 9999999)}"
    return f"{letter}{digits}"


def generate_voter_id() -> str:
    letters = "".join(random.choices("ABCDEFGHIJKLMNOPQRSTUVWXYZ", k=3))
    digits = f"{random.randint(1000000, 9999999)}"
    return f"{letters}{digits}"


class SyntheticDatasetService:
    def __init__(self):
        self.output_dir = Path("data/synthetic_datasets")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.datasets_dir = Path("data/datasets")
        self.datasets_dir.mkdir(parents=True, exist_ok=True)

    def generate_records(self, count: int = 25, extended: bool = True) -> List[Dict[str, Any]]:
        """
        Generates realistic large-scale synthetic KYC, PII, financial, and cybersecurity records.
        Strictly guarantees the presence of all 6 required fields:
          1. name
          2. phone no.
          3. blood group
          4. gender
          5. aadhar no. (Verhoeff checksum validated)
          6. income
        plus 35+ rich professional, demographic, financial, and cyber threat indicators.
        """
        records = []
        base_date = datetime.now(timezone.utc)

        for i in range(1, count + 1):
            gender = random.choice(GENDERS)
            if gender == "Female":
                first = random.choice(SAMPLE_FIRST_NAMES_FEMALE)
            elif gender == "Male":
                first = random.choice(SAMPLE_FIRST_NAMES_MALE)
            else:
                first = random.choice(SAMPLE_FIRST_NAMES_FEMALE + SAMPLE_FIRST_NAMES_MALE)
            last = random.choice(SAMPLE_LAST_NAMES)
            full_name = f"{first} {last}"

            phone_digits = random.randint(6000000000, 9999999999)
            phone_no = f"+91 {str(phone_digits)[:5]} {str(phone_digits)[5:]}"
            alt_phone_digits = random.randint(6000000000, 9999999999)
            alt_phone = f"+91 {str(alt_phone_digits)[:5]} {str(alt_phone_digits)[5:]}"

            blood_group = random.choice(BLOOD_GROUPS)
            aadhar_no = generate_verhoeff_aadhaar()
            pan_no = generate_pan_card()
            passport_no = generate_passport_no()
            voter_id = generate_voter_id()

            # Realistic financial compensation
            raw_annual_income = random.randint(450000, 4800000)
            income_bracket = f"INR {raw_annual_income:,} per annum"

            if raw_annual_income > 3000000:
                tax_bracket = "30% (High Surcharge)"
            elif raw_annual_income > 1500000:
                tax_bracket = "30% Standard"
            elif raw_annual_income > 1000000:
                tax_bracket = "20% Standard"
            elif raw_annual_income > 600000:
                tax_bracket = "10% Standard"
            else:
                tax_bracket = "5% Basic"

            # Age and DOB
            age = random.randint(22, 65)
            birth_year = base_date.year - age
            dob_str = f"{birth_year}-{random.randint(1, 12):02d}-{random.randint(1, 28):02d}"

            # Location
            city, state, pin_min, pin_max = random.choice(CITIES_STATES)
            pincode = random.randint(pin_min, pin_max)
            tower = random.choice(["Tower A", "Tower B", "Tower C", "Tower D", "Block 4", "Sector 14"])
            residential_address = f"Flat {random.randint(101, 999)}, {tower}, Green Glen Layout, {city}, {state} - {pincode}"

            # Banking
            bank_name, ifsc_prefix = random.choice(BANKS)
            ifsc_code = f"{ifsc_prefix}{random.randint(1000, 9999)}"
            bank_account_no = f"{random.randint(10000000000000, 99999999999999)}"
            credit_score = random.randint(580, 850)

            # Corporate & Cyber Risk
            employer = random.choice(EMPLOYERS)
            dept = random.choice(DEPARTMENTS)
            designation = random.choice(DESIGNATIONS)
            emp_id = f"EMP-{random.randint(10000, 99999)}"

            email_domain = employer.lower().replace(" ", "").replace("&", "")[:10] + ".in"
            official_email = f"{first.lower()}.{last.lower()}{random.randint(10, 99)}@{email_domain}"
            personal_email = f"{first.lower()}.{last.lower()}{random.randint(100, 999)}@gmail.com"

            ip_address = f"{random.randint(14, 182)}.{random.randint(10, 240)}.{random.randint(1, 254)}.{random.randint(1, 254)}"
            dev_fp = f"DEV-{uuid.uuid4().hex[:16].upper()}"
            mfa = random.choice(["TRUE", "TRUE", "TRUE", "FALSE"])

            # Cyber risk scoring
            cyber_risk = round(random.uniform(0.04, 0.96), 3)
            if cyber_risk > 0.75:
                fraud_flag = "SUSPICIOUS"
                phish_tier = "CRITICAL"
            elif cyber_risk > 0.45:
                fraud_flag = "REVIEW_NEEDED"
                phish_tier = "ELEVATED"
            else:
                fraud_flag = "CLEAN"
                phish_tier = "LOW"

            rec = {
                "record_id": f"PHG-REC-{i:06d}",
                # 6 Mandatory Fields:
                "name": full_name,
                "phone_no": phone_no,
                "blood_group": blood_group,
                "gender": gender,
                "aadhar_no": aadhar_no,
                "income": income_bracket,
                # Extended Fields:
                "first_name": first,
                "last_name": last,
                "dob": dob_str,
                "age": age,
                "nationality": "Indian",
                "pan_no": pan_no,
                "passport_no": passport_no,
                "voter_id": voter_id,
                "alt_phone_no": alt_phone,
                "official_email": official_email,
                "personal_email": personal_email,
                "annual_income_inr": raw_annual_income,
                "tax_bracket": tax_bracket,
                "bank_name": bank_name,
                "bank_account_no": bank_account_no,
                "bank_ifsc": ifsc_code,
                "credit_score": credit_score,
                "residential_address": residential_address,
                "city": city,
                "state": state,
                "pincode": pincode,
                "employer_name": employer,
                "department": dept,
                "designation": designation,
                "employee_id": emp_id,
                "ip_address": ip_address,
                "device_fingerprint": dev_fp,
                "mfa_enabled": mfa,
                "cyber_risk_score": cyber_risk,
                "fraud_flag": fraud_flag,
                "phishing_susceptibility_tier": phish_tier,
                "data_classification": "RESTRICTED_PII",
                "dpdp_consent_status": "CONSENT_ACTIVE_VERIFIED"
            }
            records.append(rec)

        return records

    # 1. CSV Format
    def export_csv(self, records: List[Dict[str, Any]]) -> bytes:
        if not records:
            return b""
        output = io.StringIO()
        fieldnames = list(records[0].keys())
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for r in records:
            writer.writerow(r)
        return output.getvalue().encode("utf-8")

    # 2. JSON Format
    def export_json(self, records: List[Dict[str, Any]]) -> bytes:
        payload = {
            "metadata": {
                "platform": "AI PhishGuard Dataset Hub",
                "specification": "Synthetic KYC, Identity & Cyber Threat Risk Benchmark",
                "generated_at": datetime.now(timezone.utc).isoformat(),
                "total_records": len(records),
                "total_columns": len(records[0]) if records else 0,
                "columns": list(records[0].keys()) if records else [],
                "regulatory_framework": "Indian Digital Personal Data Protection (DPDP) Act 2023 Compliant"
            },
            "records": records
        }
        return json.dumps(payload, indent=2, ensure_ascii=False).encode("utf-8")

    # 3. Excel Spreadsheet (XLSX)
    def export_xlsx(self, records: List[Dict[str, Any]]) -> bytes:
        if not records:
            return b""
        df = pd.DataFrame(records)
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine="openpyxl") as writer:
            df.to_excel(writer, index=False, sheet_name="Synthetic_KYC_Dossier")
        return output.getvalue()

    # 4. Text Format
    def export_txt(self, records: List[Dict[str, Any]]) -> bytes:
        lines = [
            "=" * 90,
            "AI PHISHGUARD — LARGE-SCALE SYNTHETIC KYC & IDENTITY DOSSIER",
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | Total Records: {len(records)}",
            "=" * 90,
            ""
        ]
        for r in records:
            lines.append(f"RECORD ID:    {r.get('record_id', '--')}")
            lines.append(f"Full Name:    {r.get('name', '--')}")
            lines.append(f"Phone No.:    {r.get('phone_no', '--')} | Alt: {r.get('alt_phone_no', '--')}")
            lines.append(f"Blood Group:  {r.get('blood_group', '--')} | Gender: {r.get('gender', '--')}")
            lines.append(f"Aadhar No.:   {r.get('aadhar_no', '--')} (Verhoeff Checksum Validated)")
            lines.append(f"PAN NUMBER:   {r.get('pan_no', '--')} | Passport: {r.get('passport_no', '--')}")
            lines.append(f"INCOME:       {r.get('income', '--')} | Bracket: {r.get('tax_bracket', '--')}")
            lines.append(f"EMPLOYER:     {r.get('employer_name', '--')} - {r.get('designation', '--')}")
            lines.append(f"BANK:         {r.get('bank_name', '--')} | Acct: {r.get('bank_account_no', '--')} | IFSC: {r.get('bank_ifsc', '--')}")
            lines.append(f"RESIDENCE:    {r.get('residential_address', '--')}")
            lines.append(f"CYBER RISK:   Score {r.get('cyber_risk_score', '--')} | Status: {r.get('fraud_flag', '--')} | MFA: {r.get('mfa_enabled', '--')}")
            lines.append("-" * 90)
        return "\n".join(lines).encode("utf-8")

    # 5. PDF Document
    def export_pdf(self, records: List[Dict[str, Any]]) -> bytes:
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=24, leftMargin=24, topMargin=24, bottomMargin=24)
        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'DocTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#0d1527'),
            spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'DocSub',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.HexColor('#475569'),
            spaceAfter=12
        )

        elements = [
            Paragraph("AI PhishGuard — Synthetic KYC & Identity Protection Dossier", title_style),
            Paragraph(f"Synthetic Records Catalog // Formatted PII Dataset // Generated {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}", subtitle_style),
            HRFlowable(width="100%", thickness=1, color=colors.HexColor('#2563eb'), spaceAfter=10)
        ]

        table_data = [["ID", "Name", "Phone", "Blood", "Gender", "Aadhaar", "Income", "PAN", "City"]]
        for r in records[:50]:  # Limit PDF rendering to 50 rows for clean page budget
            table_data.append([
                r.get("record_id", "")[:10],
                r.get("name", "")[:18],
                r.get("phone_no", ""),
                r.get("blood_group", ""),
                r.get("gender", "")[:6],
                r.get("aadhar_no", ""),
                r.get("income", "")[:15],
                r.get("pan_no", ""),
                r.get("city", "")[:12]
            ])

        col_widths = [60, 95, 80, 42, 45, 95, 95, 65, 80]
        t = Table(table_data, colWidths=col_widths)
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#111c35')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 5),
            ('TOPPADDING', (0, 0), (-1, 0), 5),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#f8fafc')]),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e1')),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t)
        doc.build(elements)
        return buffer.getvalue()

    # 6. DOCX Format
    def export_docx(self, records: List[Dict[str, Any]]) -> bytes:
        doc_rows_xml = ""
        for r in records[:100]:
            doc_rows_xml += f"""
            <w:tr>
                <w:tc><w:p><w:r><w:t>{r.get('record_id', '')}</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:t>{r.get('name', '')}</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:t>{r.get('phone_no', '')}</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:t>{r.get('blood_group', '')}</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:t>{r.get('gender', '')}</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:t>{r.get('aadhar_no', '')}</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:t>{r.get('income', '')}</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:t>{r.get('pan_no', '')}</w:t></w:r></w:p></w:tc>
            </w:tr>
            """

        doc_xml = f"""<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">
          <w:body>
            <w:p><w:r><w:rPr><w:b/><w:sz w:val="32"/></w:rPr><w:t>AI PhishGuard — Synthetic KYC Dataset</w:t></w:r></w:p>
            <w:tbl>
              <w:tr>
                <w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>ID</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Name</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Phone</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Blood</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Gender</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Aadhaar</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>Income</w:t></w:r></w:p></w:tc>
                <w:tc><w:p><w:r><w:rPr><w:b/></w:rPr><w:t>PAN</w:t></w:r></w:p></w:tc>
              </w:tr>
              {doc_rows_xml}
            </w:tbl>
          </w:body>
        </w:document>"""

        content_types = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
          <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
          <Default Extension="xml" ContentType="application/xml"/>
          <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
        </Types>"""

        rels = """<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
        <Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
          <Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>
        </Relationships>"""

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("[Content_Types].xml", content_types)
            zf.writestr("_rels/.rels", rels)
            zf.writestr("word/document.xml", doc_xml)
        return buffer.getvalue()

    # 7. EML Email Format
    def export_eml(self, records: List[Dict[str, Any]]) -> bytes:
        r = records[0] if records else {}
        msg = EmailMessage()
        msg["Subject"] = f"CONFIDENTIAL KYC DOSSIER // {r.get('name', 'Applicant')} // Verification Request"
        msg["From"] = "compliance-audit@securephishguard.gov.in"
        msg["To"] = r.get("official_email", "applicant@enterprise.in")
        msg["Date"] = datetime.now(timezone.utc).strftime("%a, %d %b %Y %H:%M:%S +0000")

        body = f"""CONFIDENTIAL IDENTITY AUDIT & KYC VERIFICATION NOTICE

Dear {r.get('name', 'Candidate')},

Please verify the following sensitive personal data registered in the AI PhishGuard compliance registry:

Personal Identifiers:
- Full Legal Name:       {r.get('name', '--')}
- Primary Mobile:        {r.get('phone_no', '--')}
- Blood Group:          {r.get('blood_group', '--')}
- Gender Designation:    {r.get('gender', '--')}
- UIDAI Aadhaar No:      {r.get('aadhar_no', '--')} [Verhoeff Checksum Validated]
- Income Tax PAN:        {r.get('pan_no', '--')}
- Declared Income:       {r.get('income', '--')}
- Bank Account Number:   {r.get('bank_account_no', '--')} ({r.get('bank_name', '--')})
- Current Address:       {r.get('residential_address', '--')}

Security & Cyber Posture:
- Employee ID:           {r.get('employee_id', '--')} ({r.get('employer_name', '--')})
- Device IP Address:     {r.get('ip_address', '--')}
- Threat Risk Score:     {r.get('cyber_risk_score', '--')} ({r.get('fraud_flag', 'CLEAN')})

NOTICE: This transmission contains restricted personal data governed by Section 8 of the Indian DPDP Act 2023. Unauthorized distribution is prohibited.
"""
        msg.set_content(body)
        return msg.as_bytes()

    def generate_all_sample_files(self):
        """Pre-populates sample files across all 7 formats."""
        records = self.generate_records(50)
        (self.output_dir / "synthetic_dataset.csv").write_bytes(self.export_csv(records))
        (self.output_dir / "synthetic_dataset.json").write_bytes(self.export_json(records))
        (self.output_dir / "synthetic_dataset.xlsx").write_bytes(self.export_xlsx(records))
        (self.output_dir / "synthetic_dataset.txt").write_bytes(self.export_txt(records))
        (self.output_dir / "synthetic_dataset.pdf").write_bytes(self.export_pdf(records))
        (self.output_dir / "synthetic_dataset.docx").write_bytes(self.export_docx(records))
        (self.output_dir / "synthetic_dataset.eml").write_bytes(self.export_eml(records))


synthetic_dataset_service = SyntheticDatasetService()
