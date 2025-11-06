import io
import json
import os
import textwrap
from datetime import datetime, date
from decimal import Decimal
from pathlib import Path
from typing import Any, Dict, List, Optional

import requests
from flask import Flask, jsonify, request, send_from_directory, has_request_context
from flask_cors import CORS
import mysql.connector
from mysql.connector import pooling
from werkzeug.security import check_password_hash, generate_password_hash
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Table, TableStyle
from zoneinfo import ZoneInfo


class Database:
    def __init__(self) -> None:
        self.pool: Optional[pooling.MySQLConnectionPool] = None

    def init_app(self, app: Flask) -> None:
        config = {
            "pool_name": "servicemate_pool",
            "pool_size": int(os.getenv("DB_POOL_SIZE", "5")),
            "host": os.getenv("DB_HOST", "127.0.0.1"),
            "port": int(os.getenv("DB_PORT", "3306")),
            "user": os.getenv("DB_USER", "root"),
            "password": os.getenv("DB_PASSWORD", ""),
            "database": os.getenv("DB_NAME", "servicemate"),
            "charset": "utf8mb4",
            "collation": "utf8mb4_unicode_ci",
        }

        try:
            self.pool = pooling.MySQLConnectionPool(**config)
        except mysql.connector.Error as exc:
            app.logger.error("Failed to initialise DB pool: %s", exc)
            raise

    def get_connection(self):
        if not self.pool:
            raise RuntimeError("Database pool not initialised")
        return self.pool.get_connection()


db = Database()

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
INVOICE_PDF_DIR = os.getenv("INVOICE_PDF_DIR", os.path.join(BASE_DIR, "static", "invoices"))
NEIGHSHOP_LOGO_PATH = Path(BASE_DIR) / "logo.png"
NEIGHSHOP_LOGO_URL = os.getenv(
    "NEIGHSHOP_LOGO_URL",
    os.getenv("INVOICE_LOGO_URL", "https://github.com/AKM-dv/servicemate/blob/main/logo-details%202.png?raw=true"),
)
SERVICEMATE_LOGO_URL = os.getenv(
    "SERVICEMATE_LOGO_URL",
    "https://github.com/AKM-dv/servicemate/blob/main/Group%2064.png?raw=true",
)
DEFAULT_CONTACT_NUMBER = os.getenv("CONTACT_PHONE", "+91 8307802643")
DEFAULT_UPI_ID = os.getenv("UPI_ID", "8307802643@axl")
DEFAULT_BANK_NAME = os.getenv("BANK_NAME", "Suman Kumari")
DEFAULT_BANK_ACCOUNT = os.getenv("BANK_ACCOUNT", "STATE BANK OF INDIA")
DEFAULT_ACCOUNT_NUMBER = os.getenv("BANK_ACCOUNT_NO", "42213259870")
DEFAULT_UPI_LABEL = os.getenv("UPI_LABEL", DEFAULT_UPI_ID)
DEFAULT_SETUP_FEE = Decimal(os.getenv("SETUP_FEE_AMOUNT", "3000"))
IST = ZoneInfo(os.getenv("TIMEZONE", "Asia/Kolkata"))
FEEDBACK_CATEGORIES = {"Bug", "Suggestion", "Improvement", "Other"}
FEEDBACK_STATUSES = {"Open", "In Review", "Resolved"}
PIN_LENGTH = 6
LOGO_CACHE: Dict[str, Optional[ImageReader]] = {}


def as_decimal(value: Any) -> Decimal:
    if isinstance(value, Decimal):
        return value
    if value is None:
        return Decimal("0")
    return Decimal(str(value))


def dict_factory(cursor, row) -> Dict[str, Any]:
    return {desc[0]: row[idx] for idx, desc in enumerate(cursor.description)}


def execute(query: str, params: Optional[tuple] = None, *, fetchone: bool = False, fetchall: bool = False) -> Any:
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        if fetchone:
            result = cursor.fetchone()
        elif fetchall:
            result = cursor.fetchall()
        else:
            result = None
        conn.commit()
        return result
    finally:
        conn.close()


def execute_dict(query: str, params: Optional[tuple] = None, *, fetchone: bool = False, fetchall: bool = False) -> Any:
    conn = db.get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(query, params or ())
        columns = [col[0] for col in cursor.description]
        if fetchone:
            row = cursor.fetchone()
            result = dict(zip(columns, row)) if row else None
        elif fetchall:
            result = [dict(zip(columns, row)) for row in cursor.fetchall()]
        else:
            result = None
        conn.commit()
        return result
    finally:
        conn.close()


def initialize_schema(app: Flask) -> None:
    statements = [
        """
        CREATE TABLE IF NOT EXISTS users (
            id INT AUTO_INCREMENT PRIMARY KEY,
            email VARCHAR(191) NOT NULL UNIQUE,
            password_hash VARCHAR(255) NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS plans (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(120) NOT NULL,
            price DECIMAL(10,2) NOT NULL,
            features JSON NOT NULL,
            is_active TINYINT(1) DEFAULT 1,
            sort_order INT DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS leads (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(120) DEFAULT NULL,
            email VARCHAR(191) DEFAULT NULL,
            phone VARCHAR(20) DEFAULT NULL,
            address VARCHAR(255) DEFAULT NULL,
            brand_name VARCHAR(191) DEFAULT NULL,
            status ENUM('New','In Progress','Converted','Lost','Custom') DEFAULT 'New',
            preferred_plan_id INT DEFAULT NULL,
            converted_on DATE DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (preferred_plan_id) REFERENCES plans(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS lead_followups (
            id INT AUTO_INCREMENT PRIMARY KEY,
            lead_id INT NOT NULL,
            status ENUM('New','Contacted','Meeting Scheduled','Negotiation','Closed Won','Closed Lost','Custom') DEFAULT 'New',
            follow_up_date DATE DEFAULT NULL,
            objective VARCHAR(255) DEFAULT NULL,
            next_follow_up DATE DEFAULT NULL,
            future_follow_up_note TEXT,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS invoices (
            id INT AUTO_INCREMENT PRIMARY KEY,
            lead_id INT NOT NULL,
            plan_id INT NOT NULL,
            invoice_number VARCHAR(64) NOT NULL UNIQUE,
            subtotal DECIMAL(10,2) NOT NULL,
            tax DECIMAL(10,2) NOT NULL,
            total DECIMAL(10,2) NOT NULL,
            setup_fee_amount DECIMAL(10,2) NOT NULL DEFAULT 3000.00,
            setup_fee_discount DECIMAL(10,2) NOT NULL DEFAULT 0.00,
            setup_fee_net DECIMAL(10,2) NOT NULL DEFAULT 3000.00,
            generated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            notes TEXT,
            pdf_url VARCHAR(255) DEFAULT NULL,
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
            FOREIGN KEY (plan_id) REFERENCES plans(id)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS invoice_items (
            id INT AUTO_INCREMENT PRIMARY KEY,
            invoice_id INT NOT NULL,
            description VARCHAR(255) NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS lead_payments (
            id INT AUTO_INCREMENT PRIMARY KEY,
            lead_id INT NOT NULL,
            invoice_id INT DEFAULT NULL,
            billing_month DATE NOT NULL,
            amount DECIMAL(10,2) NOT NULL,
            paid_on DATE DEFAULT NULL,
            payment_method VARCHAR(64) DEFAULT NULL,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
            FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE SET NULL,
            UNIQUE KEY lead_month_unique (lead_id, billing_month)
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """,
        """
        CREATE TABLE IF NOT EXISTS admin_feedback (
            id INT AUTO_INCREMENT PRIMARY KEY,
            title VARCHAR(191) NOT NULL,
            body TEXT NOT NULL,
            category ENUM('Bug','Suggestion','Improvement','Other') DEFAULT 'Suggestion',
            status ENUM('Open','In Review','Resolved') DEFAULT 'Open',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
        """
    ]

    for statement in statements:
        execute(statement)

    ensure_lead_phone_column()
    ensure_lead_optional_columns()
    ensure_user_pin_column()
    ensure_lead_status_enum()
    ensure_followup_columns()
    ensure_followup_status_enum()
    ensure_invoice_columns()

    seed_admin(app)
    ensure_admin_pin()
    seed_plans()


def seed_admin(app: Flask) -> None:
    admin_email = os.getenv("ADMIN_EMAIL", "admin@servicemate.com")
    existing = execute("SELECT id FROM users WHERE email = %s", (admin_email,), fetchone=True)
    if existing:
        return

    password = os.getenv("ADMIN_PASSWORD", "changeme")
    pin_code = os.getenv("ADMIN_PIN", "130323")
    if not pin_code.isdigit() or len(pin_code) != PIN_LENGTH:
        pin_code = "130323"
    execute(
        "INSERT INTO users (email, password_hash, pin_hash) VALUES (%s, %s, %s)",
        (
            admin_email,
            generate_password_hash(password),
            generate_password_hash(pin_code),
        ),
    )
    app.logger.info("Seeded default admin user")


def seed_plans() -> None:
    basic_features = [
        "Website",
        "Android App",
        "iOS App",
        "Elementary SEO",
        "Lead Management",
    ]
    basic_price = Decimal("1999.00")

    plans = execute_dict("SELECT id, name FROM plans", fetchall=True)
    basic_plan = next((plan for plan in plans if plan["name"].lower() == "basic"), None) if plans else None

    if basic_plan:
        execute(
            "UPDATE plans SET price=%s, features=CAST(%s AS JSON), is_active=1, sort_order=1 WHERE id=%s",
            (
                basic_price,
                json_dumps(basic_features),
                basic_plan["id"],
            ),
        )
        execute("UPDATE plans SET is_active = 0 WHERE id <> %s", (basic_plan["id"],))
    else:
        execute("DELETE FROM plans")
        execute(
            "INSERT INTO plans (name, price, features, is_active, sort_order) VALUES (%s, %s, CAST(%s AS JSON), 1, 1)",
            (
                "Basic",
                basic_price,
                json_dumps(basic_features),
            ),
        )


def ensure_lead_phone_column() -> None:
    exists = execute(
        """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'leads' AND COLUMN_NAME = 'phone'
        """,
        (os.getenv("DB_NAME", "servicemate"),),
        fetchone=True,
    )
    if not exists:
        execute("ALTER TABLE leads ADD COLUMN phone VARCHAR(20) DEFAULT NULL")


def ensure_lead_optional_columns() -> None:
    execute(
        """
        ALTER TABLE leads MODIFY name VARCHAR(120) NULL
        """
    )
    execute(
        """
        ALTER TABLE leads MODIFY email VARCHAR(191) NULL
        """
    )


def ensure_user_pin_column() -> None:
    exists = execute(
        """
        SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'users' AND COLUMN_NAME = 'pin_hash'
        """,
        (os.getenv("DB_NAME", "servicemate"),),
        fetchone=True,
    )
    if not exists:
        execute(
            """
            ALTER TABLE users ADD COLUMN pin_hash VARCHAR(255) DEFAULT NULL
            """
        )


def ensure_lead_status_enum() -> None:
    execute(
        """
        ALTER TABLE leads
        MODIFY status ENUM('New','In Progress','Converted','Lost','Custom') DEFAULT 'New'
        """
    )


def ensure_followup_columns() -> None:
    db_name = os.getenv("DB_NAME", "servicemate")
    definitions = {
        "follow_up_date": "ADD COLUMN follow_up_date DATE",
        "objective": "ADD COLUMN objective VARCHAR(255) DEFAULT NULL",
        "future_follow_up_note": "ADD COLUMN future_follow_up_note TEXT",
    }

    for column, ddl in definitions.items():
        exists = execute(
            """
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'lead_followups' AND COLUMN_NAME = %s
            """,
            (db_name, column),
            fetchone=True,
        )
        if not exists:
            execute(f"ALTER TABLE lead_followups {ddl}")


def ensure_followup_status_enum() -> None:
    execute(
        """
        ALTER TABLE lead_followups
        MODIFY status ENUM('New','Contacted','Meeting Scheduled','Negotiation','Closed Won','Closed Lost','Custom') DEFAULT 'New'
        """
    )


def ensure_invoice_columns() -> None:
    db_name = os.getenv("DB_NAME", "servicemate")
    definitions = {
        "setup_fee_amount": "ADD COLUMN setup_fee_amount DECIMAL(10,2) NOT NULL DEFAULT 3000.00",
        "setup_fee_discount": "ADD COLUMN setup_fee_discount DECIMAL(10,2) NOT NULL DEFAULT 0.00",
        "setup_fee_net": "ADD COLUMN setup_fee_net DECIMAL(10,2) NOT NULL DEFAULT 3000.00",
    }

    for column, ddl in definitions.items():
        exists = execute(
            """
            SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'invoices' AND COLUMN_NAME = %s
            """,
            (db_name, column),
            fetchone=True,
        )
        if not exists:
            execute(f"ALTER TABLE invoices {ddl}")


def json_dumps(data: Any) -> str:
    return json.dumps(data, default=str)


def json_loads(raw: Any) -> Any:
    if raw is None:
        return None
    if isinstance(raw, (dict, list)):
        return raw
    try:
        return json.loads(raw)
    except (TypeError, ValueError):
        return raw


def parse_decimal(value: Any) -> float:
    return float(as_decimal(value))


def sanitize_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    result = str(value).strip()
    return result or None


def ensure_invoice_pdf_dir() -> None:
    os.makedirs(INVOICE_PDF_DIR, exist_ok=True)


def format_invoice_date(value: Any) -> str:
    dt_value = to_ist_datetime(value) or datetime.now(IST)
    return dt_value.strftime("%d %b %Y")


def wrap_text(text: Optional[str], width: int = 70) -> List[str]:
    if not text:
        return ["NA"]
    return textwrap.wrap(text, width) or ["NA"]


def absolute_invoice_url(path: Optional[str]) -> Optional[str]:
    if not path:
        return None
    if path.startswith("http://") or path.startswith("https://"):
        return path
    if has_request_context():
        base = request.host_url.rstrip("/")
        return f"{base}{path}"
    return path


def get_logo_image(url: Optional[str]) -> Optional[ImageReader]:
    if url == "local_neighshop" and NEIGHSHOP_LOGO_PATH.exists():
        cache_key = str(NEIGHSHOP_LOGO_PATH.resolve())
        cached = LOGO_CACHE.get(cache_key)
        if cached is not None:
            return cached
        try:
            with NEIGHSHOP_LOGO_PATH.open("rb") as file_handler:
                cached = ImageReader(file_handler)
        except Exception as exc:
            if app.logger:
                app.logger.warning("Failed to load local logo %s: %s", NEIGHSHOP_LOGO_PATH, exc)
            cached = None
        LOGO_CACHE[cache_key] = cached
        return cached

    if not url:
        return None
    cached = LOGO_CACHE.get(url)
    if cached is not None:
        return cached
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        cached = ImageReader(io.BytesIO(response.content))
    except Exception as exc:
        if app.logger:
            app.logger.warning("Failed to load logo %s: %s", url, exc)
        cached = None
    LOGO_CACHE[url] = cached
    return cached


def to_ist_datetime(value: Any) -> Optional[datetime]:
    if value is None or value == "":
        return None
    if isinstance(value, datetime):
        dt_value = value
    else:
        raw = str(value)
        dt_value = None
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f"):
            try:
                dt_value = datetime.strptime(raw, fmt)
                break
            except ValueError:
                continue
        if dt_value is None:
            try:
                dt_value = datetime.fromisoformat(raw.replace("Z", "+00:00"))
            except ValueError:
                return None
    if dt_value.tzinfo is None:
        dt_value = dt_value.replace(tzinfo=IST)
    else:
        dt_value = dt_value.astimezone(IST)
    return dt_value


def fetch_invoice_details(invoice_number: str) -> Optional[Dict[str, Any]]:
    return execute_dict(
        """
        SELECT i.*, l.name AS lead_name, l.email AS lead_email, l.phone AS lead_phone,
               l.address AS lead_address, l.brand_name AS brand_name,
               p.name AS plan_name, p.price AS plan_price
        FROM invoices i
        JOIN leads l ON l.id = i.lead_id
        JOIN plans p ON p.id = i.plan_id
        WHERE i.invoice_number = %s
        """,
        (invoice_number,),
        fetchone=True,
    )


def serialize_invoice_record(invoice: Dict[str, Any]) -> Dict[str, Any]:
    record = dict(invoice)
    numeric_fields = [
        "subtotal",
        "tax",
        "total",
        "setup_fee_amount",
        "setup_fee_discount",
        "setup_fee_net",
        "plan_price",
    ]
    for field in numeric_fields:
        if field in record:
            record[field] = parse_decimal(record[field])

    generated_dt = to_ist_datetime(record.get("generated_at"))
    record["generated_at"] = generated_dt.isoformat() if generated_dt else None

    created_dt = to_ist_datetime(record.get("created_at"))
    record["created_at"] = created_dt.isoformat() if created_dt else None

    updated_dt = to_ist_datetime(record.get("updated_at"))
    record["updated_at"] = updated_dt.isoformat() if updated_dt else None

    record["pdf_url"] = absolute_invoice_url(record.get("pdf_url"))

    return record


def generate_invoice_pdf(invoice: Dict[str, Any]) -> str:
    storage_path = Path(INVOICE_PDF_DIR)
    storage_path.mkdir(parents=True, exist_ok=True)

    generated_dt = to_ist_datetime(invoice.get("generated_at")) or datetime.now(IST)
    timestamp_str = generated_dt.strftime("%Y%m%dT%H%M%S")
    pdf_filename = f"INV_{timestamp_str}_{invoice.get('lead_id')}.pdf"
    pdf_path = storage_path / pdf_filename

    pdf_canvas = canvas.Canvas(str(pdf_path), pagesize=A4)
    width, height = A4
    margin = 20 * mm

    neigh_logo = get_logo_image("local_neighshop" if NEIGHSHOP_LOGO_PATH.exists() else NEIGHSHOP_LOGO_URL)

    header_height = 50
    header_top = height - margin
    current_y = header_top

    text_x = margin
    if neigh_logo:
        logo_size = 32 * mm
        pdf_canvas.drawImage(
            neigh_logo,
            margin,
            header_top - logo_size + 35,
            width=logo_size,
            height=logo_size,
            preserveAspectRatio=True,
            mask="auto",
        )
        text_x = margin + logo_size + 10
        current_y = header_top - 8
    else:
        current_y = header_top - 12

    pdf_canvas.setFillColor(colors.HexColor("#0F172A"))
    pdf_canvas.setFont("Helvetica-Bold", 18)
    pdf_canvas.drawString(text_x, current_y, "Neighshop Global")
    current_y -= 18

    pdf_canvas.setFont("Helvetica", 9)
    address_lines = wrap_text(
        "Shri Ram Nagar, 8-B, opp. Dhanwantri Hospital & Research Centre, near New Sanganer Road, Mansarovar, Jaipur, Rajasthan 302020",
        width=80,
    )
    address_lines.append("+91 8307802643")
    for line in address_lines:
        pdf_canvas.drawString(text_x, current_y, line)
        current_y -= 11

    y_position = current_y - 6
    pdf_canvas.setStrokeColor(colors.HexColor("#CBD5F5"))
    pdf_canvas.line(margin, y_position, width - margin, y_position)
    y_position -= 16

    left_column_x = margin
    right_column_x = width / 2 + 16 * mm
    row_height = 16

    pdf_canvas.setFillColor(colors.black)

    def draw_field(label: str, value: Optional[str], start_x: float, start_y: float) -> float:
        pdf_canvas.setFont("Helvetica-Bold", 10)
        pdf_canvas.drawString(start_x, start_y, f"{label}:")
        pdf_canvas.setFont("Helvetica", 10)
        current_y = start_y
        for idx, line in enumerate(wrap_text(value)):
            if idx == 0:
                pdf_canvas.drawString(start_x + 60, current_y, line)
            else:
                current_y -= row_height
                pdf_canvas.drawString(start_x + 60, current_y, line)
        return current_y - row_height

    left_y = y_position
    left_fields = [
        ("Client", invoice.get("lead_name") or invoice.get("lead_phone")),
        ("Brand", invoice.get("brand_name")),
        ("Email", invoice.get("lead_email")),
        ("Phone", invoice.get("lead_phone")),
        ("Address", invoice.get("lead_address")),
    ]
    for label, value in left_fields:
        left_y = draw_field(label, value or "NA", left_column_x, left_y)

    right_y = y_position
    right_fields = [
        ("Invoice #", invoice["invoice_number"]),
        ("Invoice Date", format_invoice_date(generated_dt)),
        ("Plan", invoice.get("plan_name")),
    ]
    for label, value in right_fields:
        pdf_canvas.setFont("Helvetica-Bold", 10)
        pdf_canvas.drawString(right_column_x, right_y, f"{label}:")
        pdf_canvas.setFont("Helvetica", 10)
        pdf_canvas.drawString(right_column_x + 80, right_y, str(value or "NA"))
        right_y -= row_height

    y_position = min(left_y, right_y) - 20

    plan_price = as_decimal(invoice.get("plan_price"))
    setup_fee_amount = as_decimal(invoice.get("setup_fee_amount"))
    setup_discount = as_decimal(invoice.get("setup_fee_discount"))
    subtotal = as_decimal(invoice.get("subtotal"))
    tax_amount = as_decimal(invoice.get("tax"))
    total_due = as_decimal(invoice.get("total"))

    cost_rows: List[List[str]] = [
        ["Description", "Amount (INR)"],
        [f"Plan - {invoice.get('plan_name')}", f"{plan_price:,.2f}"],
        ["One-time Setup Fee", f"{setup_fee_amount:,.2f}"],
    ]
    if setup_discount > 0:
        cost_rows.append(["One-time Discount", f"-{setup_discount:,.2f}"])
    cost_rows.extend(
        [
            ["Subtotal", f"{subtotal:,.2f}"],
            ["Grand Total", f"{total_due:,.2f}"],
        ]
    )

    table = Table(cost_rows, colWidths=[120 * mm, 40 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F172A")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 11),
                ("ALIGN", (0, 0), (-1, 0), "LEFT"),
                ("ALIGN", (0, 1), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
                ("FONTSIZE", (0, 1), (-1, -1), 10),
                ("LINEABOVE", (0, 1), (-1, -1), 0.25, colors.HexColor("#CBD5F5")),
                ("LINEBELOW", (0, -1), (-1, -1), 0.8, colors.HexColor("#0F172A")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.whitesmoke, colors.white]),
            ]
        )
    )
    table_width, table_height = table.wrap(0, 0)
    table.drawOn(pdf_canvas, margin, y_position - table_height)
    y_position = y_position - table_height - 36

    default_payment_lines = [
        f"Bank Name: {DEFAULT_BANK_ACCOUNT}",
        f"Account Holder: {DEFAULT_BANK_NAME}",
        f"Account Number: {DEFAULT_ACCOUNT_NUMBER}",
        f"UPI: {DEFAULT_UPI_LABEL}",
    ]

    payment_lines_raw = os.getenv("INVOICE_PAYMENT_LINES")
    if payment_lines_raw:
        payment_lines = [line.strip() for line in payment_lines_raw.split("|") if line.strip()]
    else:
        payment_lines = default_payment_lines

    pdf_canvas.setFont("Helvetica-Bold", 12)
    pdf_canvas.drawString(margin, y_position, "Payment Details")
    pdf_canvas.setFont("Helvetica", 10)
    y_position -= 16
    for line in payment_lines:
        pdf_canvas.drawString(margin, y_position, line)
        y_position -= 14

    qr_image = get_logo_image("https://github.com/AKM-dv/servicemate/blob/main/WhatsApp%20Image%202025-11-07%20at%2001.24.34.jpeg?raw=true")
    if qr_image:
        qr_size = 100
        qr_x = margin
        qr_y = y_position - qr_size - 8
        pdf_canvas.drawImage(
            qr_image,
            qr_x,
            qr_y,
            width=qr_size,
            height=qr_size,
            preserveAspectRatio=True,
            mask="auto",
        )
        pdf_canvas.setFont("Helvetica", 9)
        pdf_canvas.drawString(qr_x, qr_y - 6, "Scan UPI: 8307802643@axl")
        y_position = qr_y - 20

    y_position -= 8
    pdf_canvas.setFont("Helvetica", 10)
    pdf_canvas.drawString(margin, y_position, "Thank you for choosing Neighshop Global.")

    pdf_canvas.showPage()
    pdf_canvas.save()

    invoice["generated_at"] = generated_dt

    return f"/files/invoices/{pdf_filename}"


def serialize_feedback_record(entry: Dict[str, Any]) -> Dict[str, Any]:
    record = dict(entry)
    for key in ("created_at", "updated_at"):
        value = to_ist_datetime(record.get(key))
        record[key] = value.isoformat() if value else None
    return record


def serialize_lead_record(lead: Dict[str, Any]) -> Dict[str, Any]:
    record = dict(lead)
    for field in ("created_at", "updated_at", "converted_on"):
        datetime_value = to_ist_datetime(record.get(field))
        record[field] = datetime_value.isoformat() if datetime_value else None
    return record


def serialize_followup_record(entry: Dict[str, Any]) -> Dict[str, Any]:
    record = dict(entry)
    created_dt = to_ist_datetime(record.get("created_at"))
    record["created_at"] = created_dt.isoformat() if created_dt else None

    for field in ("follow_up_date", "next_follow_up"):
        dt_value = to_ist_datetime(record.get(field))
        record[field] = dt_value.date().isoformat() if dt_value else None

    return record

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False
CORS(app, resources={r"/*": {"origins": os.getenv("FRONTEND_URL", "http://localhost:5173")}})

db.init_app(app)


def ensure_admin_pin() -> None:
    admin_pin = os.getenv("ADMIN_PIN", "130323")
    if not admin_pin.isdigit() or len(admin_pin) != PIN_LENGTH:
        if app.logger:
            app.logger.warning("ADMIN_PIN must be a 6-digit number; using default 130323")
        admin_pin = "130323"

    user = execute_dict("SELECT id, pin_hash FROM users LIMIT 1", fetchone=True)
    if not user:
        return

    pin_hash = user.get("pin_hash")
    if not pin_hash or not check_password_hash(pin_hash, admin_pin):
        execute(
            "UPDATE users SET pin_hash = %s WHERE id = %s",
            (generate_password_hash(admin_pin), user["id"]),
        )


initialize_schema(app)
ensure_invoice_pdf_dir()


def authenticate_pin(pin: str) -> bool:
    user = execute_dict("SELECT id, pin_hash FROM users LIMIT 1", fetchone=True)
    if not user or not user.get("pin_hash"):
        return False
    return check_password_hash(user["pin_hash"], pin)


@app.route("/auth/login", methods=["POST"])
def login():
    payload = request.get_json() or {}
    pin = (payload.get("pin") or "").strip()
    if not pin.isdigit() or len(pin) != PIN_LENGTH:
        return jsonify({"error": "Valid 6-digit pin required"}), 400

    if not authenticate_pin(pin):
        return jsonify({"error": "Invalid pin"}), 401

    session_token = generate_password_hash(f"{pin}{datetime.utcnow().isoformat()}" )
    return jsonify({"message": "Login successful", "session": session_token})


@app.route("/plans", methods=["GET"])
def list_plans():
    rows = execute_dict("SELECT id, name, price, features, is_active, sort_order FROM plans WHERE is_active = 1 ORDER BY sort_order ASC", fetchall=True)
    if not rows:
        seed_plans()
        rows = execute_dict(
            "SELECT id, name, price, features, is_active, sort_order FROM plans WHERE is_active = 1 ORDER BY sort_order ASC",
            fetchall=True,
        )
    for row in rows:
        row["price"] = parse_decimal(row["price"])
        row["features"] = json_loads(row.get("features")) or []
    return jsonify(rows)


@app.route("/plans", methods=["PUT"])
def update_plans():
    payload = request.get_json() or {}
    plans = payload.get("plans", [])
    plan_payload = plans[0] if plans else {}

    name = plan_payload.get("name") or "Basic"
    price = as_decimal(plan_payload.get("price") or Decimal("1999.00"))
    features = plan_payload.get("features") or [
        "Website",
        "Android App",
        "iOS App",
        "Elementary SEO",
        "Lead Management",
    ]

    basic = execute_dict("SELECT id FROM plans WHERE name = %s LIMIT 1", ("Basic",), fetchone=True)
    if not basic:
        seed_plans()
        basic = execute_dict("SELECT id FROM plans WHERE name = %s LIMIT 1", ("Basic",), fetchone=True)

    execute(
        "UPDATE plans SET name=%s, price=%s, features=CAST(%s AS JSON), is_active=1, sort_order=1 WHERE id=%s",
        (
            name,
            price,
            json_dumps(features),
            basic["id"],
        ),
    )
    execute("UPDATE plans SET is_active = 0 WHERE id <> %s", (basic["id"],))

    return jsonify({"message": "Plan updated"})


@app.route("/leads", methods=["GET"])
def list_leads():
    status_param = request.args.get("status")
    search_param = sanitize_string(request.args.get("search"))
    created_from = request.args.get("created_from")
    created_to = request.args.get("created_to")

    conditions: List[str] = []
    params: List[Any] = []

    if status_param:
        statuses = [value.strip() for value in status_param.split(",") if value.strip()]
        if statuses:
            placeholders = ", ".join(["%s"] * len(statuses))
            conditions.append(f"l.status IN ({placeholders})")
            params.extend(statuses)

    if search_param:
        like_pattern = f"%{search_param}%"
        conditions.append(
            "(l.name LIKE %s OR l.email LIKE %s OR l.phone LIKE %s OR l.brand_name LIKE %s)"
        )
        params.extend([like_pattern, like_pattern, like_pattern, like_pattern])

    if created_from:
        conditions.append("DATE(l.created_at) >= %s")
        params.append(created_from)

    if created_to:
        conditions.append("DATE(l.created_at) <= %s")
        params.append(created_to)

    query = (
        """
        SELECT l.id, l.name, l.email, l.phone, l.address, l.brand_name, l.status, l.preferred_plan_id,
               l.converted_on, l.created_at, l.updated_at, p.name AS preferred_plan_name
        FROM leads l
        LEFT JOIN plans p ON p.id = l.preferred_plan_id
        """
    )

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY l.created_at DESC"

    param_tuple = tuple(params)
    rows = execute_dict(
        query,
        param_tuple if param_tuple else None,
        fetchall=True,
    )
    return jsonify([serialize_lead_record(row) for row in rows])


@app.route("/leads", methods=["POST"])
def create_lead():
    payload = request.get_json() or {}
    name = sanitize_string(payload.get("name"))
    email = sanitize_string(payload.get("email"))
    phone = sanitize_string(payload.get("phone"))
    if not phone:
        return jsonify({"error": "Phone number required"}), 400

    execute(
        """
        INSERT INTO leads (name, email, phone, address, brand_name, status, preferred_plan_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (
            name,
            email,
            phone,
            sanitize_string(payload.get("address")),
            sanitize_string(payload.get("brand_name")),
            payload.get("status", "New"),
            payload.get("preferred_plan_id"),
        ),
    )

    lead = execute_dict(
        "SELECT * FROM leads WHERE phone = %s ORDER BY id DESC LIMIT 1",
        (phone,),
        fetchone=True,
    )
    return jsonify(serialize_lead_record(lead)), 201


@app.route("/leads/<int:lead_id>", methods=["GET"])
def get_lead(lead_id: int):
    lead = execute_dict(
        """
        SELECT l.*, p.name AS preferred_plan_name
        FROM leads l
        LEFT JOIN plans p ON p.id = l.preferred_plan_id
        WHERE l.id = %s
        """,
        (lead_id,),
        fetchone=True,
    )
    if not lead:
        return jsonify({"error": "Lead not found"}), 404
    lead = serialize_lead_record(lead)
    followups = execute_dict(
        """
        SELECT id, status, follow_up_date, objective, next_follow_up, future_follow_up_note, note, created_at
        FROM lead_followups WHERE lead_id = %s ORDER BY created_at DESC
        """,
        (lead_id,),
        fetchall=True,
    )
    invoices = execute_dict(
        """
        SELECT id, invoice_number, total, generated_at, pdf_url
        FROM invoices WHERE lead_id = %s ORDER BY generated_at DESC
        """,
        (lead_id,),
        fetchall=True,
    )
    lead.update({
        "followups": [serialize_followup_record(item) for item in followups],
        "invoices": [serialize_invoice_record(item) for item in invoices],
    })
    return jsonify(lead)


@app.route("/leads/<int:lead_id>", methods=["PUT"])
def update_lead(lead_id: int):
    payload = request.get_json() or {}
    lead = execute_dict("SELECT id FROM leads WHERE id = %s", (lead_id,), fetchone=True)
    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    updates: List[str] = []
    values: List[Any] = []

    if "name" in payload:
        updates.append("name = %s")
        values.append(sanitize_string(payload.get("name")))

    if "email" in payload:
        updates.append("email = %s")
        values.append(sanitize_string(payload.get("email")))

    if "phone" in payload:
        phone_value = sanitize_string(payload.get("phone"))
        if not phone_value:
            return jsonify({"error": "Phone number cannot be empty"}), 400
        updates.append("phone = %s")
        values.append(phone_value)

    if "address" in payload:
        updates.append("address = %s")
        values.append(sanitize_string(payload.get("address")))

    if "brand_name" in payload:
        updates.append("brand_name = %s")
        values.append(sanitize_string(payload.get("brand_name")))

    status_value = payload.get("status")
    if status_value is not None:
        updates.append("status = %s")
        values.append(status_value)

    if "preferred_plan_id" in payload:
        plan_id = payload.get("preferred_plan_id") or None
        updates.append("preferred_plan_id = %s")
        values.append(plan_id)

    if status_value == "Converted":
        updates.append("converted_on = %s")
        values.append(payload.get("converted_on", date.today()))

    if not updates:
        return jsonify({"error": "Nothing to update"}), 400

    values.append(lead_id)
    execute(f"UPDATE leads SET {', '.join(updates)} WHERE id = %s", tuple(values))

    updated = execute_dict("SELECT * FROM leads WHERE id = %s", (lead_id,), fetchone=True)
    return jsonify(updated)


@app.route("/leads/<int:lead_id>/followups", methods=["POST"])
def add_followup(lead_id: int):
    payload = request.get_json() or {}
    status = payload.get("status", "New")
    note = sanitize_string(payload.get("note"))
    objective = sanitize_string(payload.get("objective"))
    future_follow_up_note = sanitize_string(payload.get("future_follow_up_note"))
    follow_up_date = payload.get("follow_up_date") or date.today().isoformat()
    next_follow_up = payload.get("next_follow_up")

    if status in {"Closed Won", "Closed Lost"}:
        next_follow_up = None
        future_follow_up_note = None
    else:
        next_follow_up = next_follow_up or None

    lead = execute_dict("SELECT id FROM leads WHERE id = %s", (lead_id,), fetchone=True)
    if not lead:
        return jsonify({"error": "Lead not found"}), 404

    execute(
        """
        INSERT INTO lead_followups (
            lead_id, status, follow_up_date, objective, next_follow_up, future_follow_up_note, note
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        """,
        (lead_id, status, follow_up_date, objective, next_follow_up, future_follow_up_note, note),
    )

    followup = execute_dict(
        """
        SELECT * FROM lead_followups WHERE lead_id = %s ORDER BY id DESC LIMIT 1
        """,
        (lead_id,),
        fetchone=True,
    )
    return jsonify(followup), 201


@app.route("/leads/<int:lead_id>/payments", methods=["POST"])
def record_payment(lead_id: int):
    payload = request.get_json() or {}
    billing_month = payload.get("billing_month")
    amount = payload.get("amount")
    if not billing_month or not amount:
        return jsonify({"error": "Billing month and amount required"}), 400

    execute(
        """
        INSERT INTO lead_payments (lead_id, billing_month, amount, paid_on, payment_method, note)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE amount=VALUES(amount), paid_on=VALUES(paid_on), payment_method=VALUES(payment_method), note=VALUES(note)
        """,
        (
            lead_id,
            billing_month,
            amount,
            payload.get("paid_on"),
            payload.get("payment_method"),
            payload.get("note"),
        ),
    )

    payment = execute_dict(
        "SELECT * FROM lead_payments WHERE lead_id = %s AND billing_month = %s",
        (lead_id, billing_month),
        fetchone=True,
    )
    return jsonify(payment)


@app.route("/analytics/summary", methods=["GET"])
def analytics_summary():
    lead_counts = execute_dict(
        """
        SELECT status, COUNT(*) AS total
        FROM leads
        GROUP BY status
        """,
        fetchall=True,
    )

    conversions_by_plan = execute_dict(
        """
        SELECT p.name AS plan_name, COUNT(*) AS total
        FROM leads l
        JOIN plans p ON p.id = l.preferred_plan_id
        WHERE l.status = 'Converted'
        GROUP BY p.name
        """,
        fetchall=True,
    )

    monthly_revenue = execute_dict(
        """
        SELECT DATE_FORMAT(paid_on, '%Y-%m') AS month, SUM(amount) AS total
        FROM lead_payments
        WHERE paid_on IS NOT NULL
        GROUP BY month
        ORDER BY month DESC
        LIMIT 12
        """,
        fetchall=True,
    )

    overdue = execute_dict(
        """
        SELECT COUNT(*) AS overdue_count
        FROM lead_payments
        WHERE paid_on IS NULL AND billing_month < CURDATE()
        """,
        fetchone=True,
    ) or {"overdue_count": 0}

    for entry in monthly_revenue:
        entry["total"] = parse_decimal(entry["total"])

    return jsonify(
        {
            "lead_counts": lead_counts,
            "conversions_by_plan": conversions_by_plan,
            "monthly_revenue": monthly_revenue,
            "overdue": overdue,
        }
    )


@app.route("/feedback", methods=["GET"])
def list_feedback():
    rows = execute_dict(
        """
        SELECT id, title, body, category, status, created_at, updated_at
        FROM admin_feedback
        ORDER BY created_at DESC
        """,
        fetchall=True,
    )
    return jsonify([serialize_feedback_record(row) for row in rows])


@app.route("/feedback", methods=["POST"])
def create_feedback():
    payload = request.get_json() or {}
    title = sanitize_string(payload.get("title"))
    body = sanitize_string(payload.get("body"))
    category = payload.get("category", "Suggestion")

    if not title or not body:
        return jsonify({"error": "Title and description required"}), 400

    if category not in FEEDBACK_CATEGORIES:
        category = "Suggestion"

    execute(
        """
        INSERT INTO admin_feedback (title, body, category)
        VALUES (%s, %s, %s)
        """,
        (title, body, category),
    )

    entry = execute_dict(
        "SELECT * FROM admin_feedback ORDER BY id DESC LIMIT 1",
        fetchone=True,
    )
    return jsonify(serialize_feedback_record(entry)), 201


@app.route("/feedback/<int:feedback_id>", methods=["PUT"])
def update_feedback(feedback_id: int):
    payload = request.get_json() or {}
    entry = execute_dict("SELECT id FROM admin_feedback WHERE id = %s", (feedback_id,), fetchone=True)
    if not entry:
        return jsonify({"error": "Feedback not found"}), 404

    updates: List[str] = []
    values: List[Any] = []

    if "title" in payload:
        title = sanitize_string(payload.get("title"))
        if not title:
            return jsonify({"error": "Title cannot be empty"}), 400
        updates.append("title = %s")
        values.append(title)

    if "body" in payload:
        body = sanitize_string(payload.get("body"))
        if not body:
            return jsonify({"error": "Description cannot be empty"}), 400
        updates.append("body = %s")
        values.append(body)

    if "category" in payload:
        category = payload.get("category")
        if category not in FEEDBACK_CATEGORIES:
            return jsonify({"error": "Invalid category"}), 400
        updates.append("category = %s")
        values.append(category)

    if "status" in payload:
        status = payload.get("status")
        if status not in FEEDBACK_STATUSES:
            return jsonify({"error": "Invalid status"}), 400
        updates.append("status = %s")
        values.append(status)

    if not updates:
        return jsonify({"error": "Nothing to update"}), 400

    values.append(feedback_id)
    execute(f"UPDATE admin_feedback SET {', '.join(updates)} WHERE id = %s", tuple(values))

    updated = execute_dict("SELECT * FROM admin_feedback WHERE id = %s", (feedback_id,), fetchone=True)
    return jsonify(serialize_feedback_record(updated))


@app.route("/invoices", methods=["POST"])
def create_invoice():
    payload = request.get_json() or {}
    lead_id = payload.get("lead_id")
    plan_id = payload.get("plan_id")
    if not lead_id or not plan_id:
        return jsonify({"error": "lead_id and plan_id required"}), 400

    plan = execute_dict("SELECT id, name, price FROM plans WHERE id = %s", (plan_id,), fetchone=True)
    lead = execute_dict("SELECT id, name, email, brand_name, phone, address FROM leads WHERE id = %s", (lead_id,), fetchone=True)
    if not plan or not lead:
        return jsonify({"error": "Invalid lead or plan"}), 400

    setup_discount_input = payload.get("setup_discount")
    setup_discount = as_decimal(setup_discount_input if setup_discount_input is not None else 0)
    if setup_discount < 0:
        setup_discount = Decimal("0")

    setup_fee_amount = DEFAULT_SETUP_FEE
    if setup_discount > setup_fee_amount:
        setup_discount = setup_fee_amount

    setup_fee_net = setup_fee_amount - setup_discount

    plan_price = as_decimal(plan["price"])
    subtotal = plan_price + setup_fee_net
    tax = Decimal("0")
    total = subtotal

    invoice_number = next_invoice_number()

    execute(
        """
        INSERT INTO invoices (
            lead_id,
            plan_id,
            invoice_number,
            subtotal,
            tax,
            total,
            notes,
            setup_fee_amount,
            setup_fee_discount,
            setup_fee_net
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (
            lead_id,
            plan_id,
            invoice_number,
            subtotal,
            tax,
            total,
            payload.get("notes"),
            setup_fee_amount,
            setup_discount,
            setup_fee_net,
        ),
    )

    invoice_details = fetch_invoice_details(invoice_number)
    if not invoice_details:
        return jsonify({"error": "Failed to create invoice"}), 500

    invoice_details["plan_price"] = plan_price
    pdf_url = generate_invoice_pdf(invoice_details)
    execute(
        "UPDATE invoices SET pdf_url = %s WHERE invoice_number = %s",
        (pdf_url, invoice_number),
    )
    invoice_details["pdf_url"] = pdf_url

    response_payload = serialize_invoice_record(invoice_details)
    return jsonify(response_payload), 201


def next_invoice_number() -> str:
    today = datetime.utcnow()
    prefix = today.strftime("INV%Y%m")
    seq_row = execute(
        "SELECT COUNT(*) FROM invoices WHERE invoice_number LIKE %s",
        (f"{prefix}%",),
        fetchone=True,
    )
    seq = (seq_row[0] if seq_row else 0) + 1
    return f"{prefix}{seq:04d}"


@app.route("/invoices", methods=["GET"])
def list_invoices():
    search_param = sanitize_string(request.args.get("search"))
    generated_from = request.args.get("generated_from")
    generated_to = request.args.get("generated_to")

    conditions: List[str] = []
    params: List[Any] = []

    if search_param:
        like_pattern = f"%{search_param}%"
        conditions.append(
            "(i.invoice_number LIKE %s OR l.name LIKE %s OR l.email LIKE %s OR l.phone LIKE %s)"
        )
        params.extend([like_pattern, like_pattern, like_pattern, like_pattern])

    if generated_from:
        conditions.append("DATE(i.generated_at) >= %s")
        params.append(generated_from)

    if generated_to:
        conditions.append("DATE(i.generated_at) <= %s")
        params.append(generated_to)

    query = (
        """
        SELECT i.id, i.invoice_number, i.total, i.generated_at, i.pdf_url,
               i.setup_fee_amount, i.setup_fee_discount, i.setup_fee_net,
               i.subtotal, i.tax,
               l.name AS lead_name, l.email AS lead_email, l.phone AS lead_phone,
               p.name AS plan_name, p.price AS plan_price
        FROM invoices i
        JOIN leads l ON l.id = i.lead_id
        JOIN plans p ON p.id = i.plan_id
        """
    )

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY i.generated_at DESC"

    param_tuple = tuple(params)
    invoices = execute_dict(
        query,
        param_tuple if param_tuple else None,
        fetchall=True,
    )
    serialized = [serialize_invoice_record(entry) for entry in invoices]
    return jsonify(serialized)


@app.route("/files/invoices/<path:filename>")
def serve_invoice_pdf(filename: str):
    download_flag = request.args.get("download", "0") == "1"
    return send_from_directory(INVOICE_PDF_DIR, filename, as_attachment=download_flag)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5700")), debug=True)

