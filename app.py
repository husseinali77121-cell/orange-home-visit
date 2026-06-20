import streamlit as st
import sqlite3
import os
import urllib.parse
from datetime import date, datetime, timedelta
import pandas as pd
import re as re_module

# ══════════════════════════════════════════════════════════════════════════════
# إعدادات الصفحة
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="Orange Lab Home Visit",
    page_icon="🟠",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ══════════════════════════════════════════════════════════════════════════════
# نظام تسجيل الدخول
# ══════════════════════════════════════════════════════════════════════════════
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_type" not in st.session_state:
    st.session_state.user_type = None

ALLOWED_EMAILS = st.secrets.get("allowed_emails", [])
ADMIN_EMAIL    = "Hussein.ali77121@gmail.com"
DIAMOND_EMAIL  = "Orangelab511@gmail.com"

if not st.session_state.authenticated:
    st.title("🔒 تسجيل الدخول")

    # ── استرجاع الإيميل المحفوظ من query params ──
    params     = st.query_params
    saved_mail = params.get("remember", "")

    email = st.text_input("📧 أدخل بريدك الإلكتروني للدخول", value=saved_mail)
    remember_me = st.checkbox("تذكرني في هذا الجهاز", value=bool(saved_mail))

    if st.button("دخول"):
        email_clean = email.strip()
        if email_clean not in ALLOWED_EMAILS:
            st.error("هذا البريد غير مصرح له بالدخول. راجع الأدمن.")
        else:
            # حفظ الإيميل في URL إذا اختار المستخدم "تذكرني"
            if remember_me:
                st.query_params["remember"] = email_clean
            else:
                st.query_params.clear()

            if email_clean.lower() == ADMIN_EMAIL.lower():
                st.session_state.login_email  = email_clean
                st.session_state.need_password = True
                st.rerun()
            else:
                st.session_state.authenticated = True
                st.session_state.user_email    = email_clean
                st.session_state.user_type     = "diamond" if email_clean.lower() == DIAMOND_EMAIL.lower() else "other"
                st.rerun()

    if st.session_state.get("need_password"):
        st.markdown("---")
        st.markdown(f"البريد: **{st.session_state.login_email}**")
        password = st.text_input("🔑 كلمة المرور", type="password")
        if st.button("تأكيد كلمة المرور"):
            correct_password = st.secrets.get("admin_password", "123456")
            if password == correct_password:
                st.success("صلِّ على رسول الله ﷺ - أهلاً بالأدمن")
                st.session_state.authenticated  = True
                st.session_state.user_email     = st.session_state.login_email
                st.session_state.user_type      = "admin"
                st.session_state.need_password  = False
                st.rerun()
            else:
                st.error("كلمة مرور خاطئة")
        if st.button("رجوع"):
            st.session_state.need_password = False
            st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="text-align:center; margin-top:40px; color:#333; font-size:13px; line-height:1.8;">
      <div style="color:#FF6B00; font-weight:800; font-size:15px; margin-bottom:6px;">📞 للتواصل Contact</div>
      <div><b>Dr / Hussein Ali</b></div>
      <div style="direction: ltr; unicode-bidi: embed;">📱 T: 01016872801</div>
      <div style="direction: ltr; unicode-bidi: embed;">📧 Email: hussein.ali77121@gmail.com</div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# إخفاء عناصر Streamlit
# ══════════════════════════════════════════════════════════════════════════════
st.markdown("""
    <style>
    .stActionButton {display: none !important;}
    #MainMenu {visibility: hidden !important;}
    footer {visibility: hidden !important;}
    header[data-testid="stHeader"] {display: none !important;}
    </style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# قاعدة البيانات
# ══════════════════════════════════════════════════════════════════════════════
DB_FILE      = "visits.db"
BACKUP_EXCEL = "visits_export.xlsx"

@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_connection()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            name TEXT NOT NULL,
            age INTEGER,
            age_unit TEXT DEFAULT 'سنة',
            phone TEXT NOT NULL,
            visit_date TEXT NOT NULL,
            visit_time TEXT,
            doctor_name TEXT,
            branch TEXT DEFAULT 'La Cite',
            address TEXT NOT NULL,
            location_link TEXT,
            selected_labs_text TEXT,
            notes TEXT,
            labs_price_before REAL DEFAULT 0,
            labs_price_after REAL DEFAULT 0,
            transport_fee REAL DEFAULT 0,
            total_price REAL DEFAULT 0,
            status TEXT DEFAULT 'مجدولة'
        )
    """)
    safe_cols = [
        ("age_unit",  "TEXT DEFAULT 'سنة'"),
        ("status",    "TEXT DEFAULT 'مجدولة'"),
        ("rating",    "INTEGER DEFAULT 0"),
        ("tag",       "TEXT DEFAULT ''"),
    ]
    for col, definition in safe_cols:
        try:
            conn.execute(f"ALTER TABLE visits ADD COLUMN {col} {definition}")
        except sqlite3.OperationalError:
            pass
    conn.commit()

init_db()

# ══════════════════════════════════════════════════════════════════════════════
# ثوابت الحالة
# ══════════════════════════════════════════════════════════════════════════════
STATUS_OPTIONS = ["مجدولة", "في الطريق", "تمت", "ملغية"]
STATUS_COLORS  = {
    "مجدولة":    "#3498DB",
    "في الطريق": "#F39C12",
    "تمت":       "#27AE60",
    "ملغية":     "#E74C3C",
}
STATUS_ICONS = {
    "مجدولة":    "📅",
    "في الطريق": "🚗",
    "تمت":       "✅",
    "ملغية":     "❌",
}

MONTHS_AR = ["يناير","فبراير","مارس","أبريل","مايو","يونيو",
             "يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]

# ══════════════════════════════════════════════════════════════════════════════
# دوال CRUD
# ══════════════════════════════════════════════════════════════════════════════
def fetch_visits(filters=None):
    conn = get_connection()
    query = "SELECT * FROM visits"
    params = []
    conditions = []
    if filters:
        if filters.get("search"):
            s = f"%{filters['search']}%"
            conditions.append("(name LIKE ? OR phone LIKE ?)")
            params.extend([s, s])
        if filters.get("branch"):
            conditions.append("branch = ?")
            params.append(filters["branch"])
        if filters.get("doctor"):
            conditions.append("doctor_name = ?")
            params.append(filters["doctor"])
        if filters.get("month") and filters.get("year"):
            y, m = filters["year"], filters["month"]
            conditions.append("strftime('%Y', visit_date) = ? AND strftime('%m', visit_date) = ?")
            params.extend([str(y), f"{m:02d}"])
        if filters.get("date_exact"):
            conditions.append("visit_date = ?")
            params.append(filters["date_exact"])
        if filters.get("date_from"):
            conditions.append("visit_date >= ?")
            params.append(filters["date_from"])
        if filters.get("date_to"):
            conditions.append("visit_date <= ?")
            params.append(filters["date_to"])
        if filters.get("status"):
            conditions.append("status = ?")
            params.append(filters["status"])
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY visit_date ASC, visit_time ASC"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]

def fetch_visit_by_id(visit_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM visits WHERE id = ?", (visit_id,)).fetchone()
    return dict(row) if row else None

def fetch_client_history(phone, exclude_id=None):
    conn = get_connection()
    if exclude_id:
        rows = conn.execute(
            "SELECT * FROM visits WHERE phone = ? AND id != ? ORDER BY visit_date DESC",
            (phone, exclude_id)
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM visits WHERE phone = ? ORDER BY visit_date DESC", (phone,)
        ).fetchall()
    return [dict(r) for r in rows]

def insert_visit(record):
    conn = get_connection()
    conn.execute("""
        INSERT INTO visits (
            id, created_at, name, age, age_unit, phone, visit_date, visit_time,
            doctor_name, branch, address, location_link,
            selected_labs_text, notes, labs_price_before,
            labs_price_after, transport_fee, total_price, status
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        record["id"], record["created_at"], record["name"], record["age"],
        record.get("age_unit", "سنة"), record["phone"],
        record["visit_date"], record["visit_time"], record["doctor_name"],
        record.get("branch", "La Cite"), record["address"], record["location_link"],
        record["selected_labs_text"], record["notes"],
        record["labs_price_before"], record["labs_price_after"],
        record["transport_fee"], record["total_price"],
        record.get("status", "مجدولة")
    ))
    conn.commit()

def update_visit(record):
    conn = get_connection()
    conn.execute("""
        UPDATE visits SET
            name=?, age=?, age_unit=?, phone=?, visit_date=?, visit_time=?,
            doctor_name=?, branch=?, address=?, location_link=?,
            selected_labs_text=?, notes=?, labs_price_before=?,
            labs_price_after=?, transport_fee=?, total_price=?, status=?
        WHERE id=?
    """, (
        record["name"], record["age"], record.get("age_unit", "سنة"),
        record["phone"], record["visit_date"], record["visit_time"],
        record["doctor_name"], record.get("branch", "La Cite"),
        record["address"], record["location_link"], record["selected_labs_text"],
        record["notes"], record["labs_price_before"], record["labs_price_after"],
        record["transport_fee"], record["total_price"],
        record.get("status", "مجدولة"), record["id"]
    ))
    conn.commit()

def update_status_only(visit_id, new_status):
    conn = get_connection()
    conn.execute("UPDATE visits SET status=? WHERE id=?", (new_status, visit_id))
    conn.commit()

def delete_visit(visit_id):
    conn = get_connection()
    conn.execute("DELETE FROM visits WHERE id=?", (visit_id,))
    conn.commit()

def update_rating(visit_id, rating):
    conn = get_connection()
    conn.execute("UPDATE visits SET rating=? WHERE id=?", (rating, visit_id))
    conn.commit()

def update_tag(visit_id, tag):
    conn = get_connection()
    conn.execute("UPDATE visits SET tag=? WHERE id=?", (tag, visit_id))
    conn.commit()

def get_client_tag(phone):
    """تصنيف العميل تلقائياً بناءً على عدد زياراته المكتملة"""
    conn  = get_connection()
    count = conn.execute(
        "SELECT COUNT(*) FROM visits WHERE phone=? AND status='تمت'", (phone,)
    ).fetchone()[0]
    if count == 0:
        return "🆕 عميل جديد"
    elif count <= 2:
        return "⭐ عميل منتظم"
    elif count <= 5:
        return "🌟 عميل متكرر"
    else:
        return "👑 VIP"

def get_client_tag_color(tag):
    return {"🆕 عميل جديد":"#3498DB","⭐ عميل منتظم":"#27AE60",
            "🌟 عميل متكرر":"#F39C12","👑 VIP":"#9B59B6",
            "🏢 Corporate":"#E74C3C"}.get(tag,"#888")

# ══════════════════════════════════════════════════════════════════════════════
# تصدير / استيراد
# ══════════════════════════════════════════════════════════════════════════════
def export_to_excel(branch_filter=None, month=None, year=None, date_from=None, date_to=None):
    """تصدير الزيارات إلى Excel — جدول رئيسي + جدول الأطباء"""
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
    from openpyxl.utils import get_column_letter

    filters = {}
    if branch_filter:
        filters["branch"] = branch_filter
    if date_from and date_to:
        filters["date_from"] = str(date_from)
        filters["date_to"]   = str(date_to)
    elif month and year:
        filters["month"] = month
        filters["year"]  = year
    visits = fetch_visits(filters if filters else None)
    df = pd.DataFrame(visits)

    # ── ألوان وأنماط ──
    ORANGE       = "FF6B00"
    ORANGE_LIGHT = "FFF3E8"
    DOC_HDR_BG   = "2C3E50"
    WHITE        = "FFFFFF"
    STATUS_FILL  = {"تمت":"D5F5E3","ملغية":"FADBD8","في الطريق":"FEF9E7","مجدولة":"D6EAF8"}
    thin   = Side(style="thin", color="FFBB80")
    BORDER = Border(left=thin, right=thin, top=thin, bottom=thin)
    CENTER = Alignment(horizontal="center", vertical="center", wrap_text=True)
    RIGHT  = Alignment(horizontal="right",  vertical="center", wrap_text=True)

    # ── الأعمدة الرئيسية (RTL — من اليمين لليسار) ──
    MAIN_COLS = [
        ("status",            "الحالة"),
        ("total_price",       "الإجمالي"),
        ("transport_fee",     "بدل الانتقال"),
        ("labs_price_after",  "السعر بعد الخصم"),
        ("labs_price_before", "السعر قبل الخصم"),
        ("selected_labs_text","التحاليل"),
        ("address",           "العنوان"),
        ("doctor_name",       "الدكتور"),
        ("visit_date",        "تاريخ الزيارة"),
        ("phone",             "التليفون"),
        ("name",              "الاسم"),
    ]
    PRICE_KEYS = {"labs_price_before","labs_price_after","transport_fee","total_price"}
    col_keys   = [c[0] for c in MAIN_COLS]
    col_labels = [c[1] for c in MAIN_COLS]
    n_cols     = len(MAIN_COLS)
    WIDTHS_MAIN = {
        "status":10,"total_price":14,"transport_fee":14,
        "labs_price_after":16,"labs_price_before":16,
        "selected_labs_text":28,"address":32,
        "doctor_name":14,"visit_date":13,"phone":15,"name":20,
    }

    # ── اسم الملف ──
    if date_from and date_to:
        month_label = f"{date_from} → {date_to}"
    elif month and year:
        month_label = f"{MONTHS_AR[month-1]} {year}"
    else:
        month_label = str(date.today())
    branch_label = f"فرع {branch_filter}" if branch_filter else "كل الفروع"
    if date_from and date_to:
        period = f"{date_from}_to_{date_to}"
    elif month and year:
        period = f"{MONTHS_AR[month-1]}_{year}"
    else:
        period = str(date.today())
    if branch_filter == "Diamond":
        fname = f"diamond_{period}.xlsx"
    else:
        fname = f"visits_{period}.xlsx" if (date_from or month) else BACKUP_EXCEL

    if df.empty:
        pd.DataFrame().to_excel(fname, index=False, engine="openpyxl")
        return df, fname

    # فلتر للزيارات الصالحة (غير ملغية) لجدول الأطباء
    df_valid = df[df["status"] != "ملغية"]
    n_rows   = len(df)

    wb = Workbook()
    ws = wb.active
    ws.title = "الزيارات"
    ws.sheet_view.rightToLeft = True

    DATA_START = 4
    DATA_END   = DATA_START + n_rows - 1
    TOTAL_ROW  = DATA_END + 1

    # ── ROW 1: عنوان ──
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=n_cols)
    c = ws.cell(1, 1, f"🟠 Orange Lab Home Visit — {branch_label} — {month_label}")
    c.font = Font(name="Cairo", bold=True, color=WHITE, size=14)
    c.fill = PatternFill("solid", fgColor=ORANGE)
    c.alignment = CENTER
    ws.row_dimensions[1].height = 38

    # ── ROW 2: ملخص ──
    sl = ["تمت","مجدولة","في الطريق","ملغية"]
    parts = "  |  ".join(f"{s}: {(df['status']==s).sum()}" for s in sl if (df['status']==s).sum()>0)
    ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=n_cols)
    c = ws.cell(2, 1, f"إجمالي: {n_rows} زيارة  |  {parts}  |  تاريخ التصدير: {date.today()}")
    c.font = Font(name="Cairo", bold=True, color=ORANGE, size=10)
    c.fill = PatternFill("solid", fgColor=ORANGE_LIGHT)
    c.alignment = CENTER
    ws.row_dimensions[2].height = 22

    # ── ROW 3: رؤوس ──
    for ci, label in enumerate(col_labels, 1):
        c = ws.cell(3, ci, label)
        c.font = Font(name="Cairo", bold=True, color=WHITE, size=11)
        c.fill = PatternFill("solid", fgColor=ORANGE)
        c.alignment = CENTER
        c.border = BORDER
    ws.row_dimensions[3].height = 30

    # ── ROWS 4+: بيانات ──
    for ri, (_, row) in enumerate(df.iterrows(), start=DATA_START):
        st = str(row.get("status",""))
        fc = STATUS_FILL.get(st, WHITE)
        for ci, key in enumerate(col_keys, 1):
            val = row.get(key, "")
            if pd.isna(val): val = ""
            c = ws.cell(ri, ci, val)
            c.font   = Font(name="Cairo", size=10)
            c.fill   = PatternFill("solid", fgColor=fc)
            c.border = BORDER
            if key in PRICE_KEYS:
                c.number_format = '#,##0 "ج"'
                c.alignment = Alignment(horizontal="center", vertical="center")
            elif key == "selected_labs_text":
                c.alignment = Alignment(horizontal="right", vertical="top", wrap_text=True)
            else:
                c.alignment = RIGHT
        ws.row_dimensions[ri].height = 22

    # ── صف الإجمالي الكلي ──
    labs_ci = col_keys.index("selected_labs_text") + 1
    ws.merge_cells(start_row=TOTAL_ROW, start_column=labs_ci, end_row=TOTAL_ROW, end_column=n_cols)
    c = ws.cell(TOTAL_ROW, labs_ci, "الإجمالي الكلي")
    c.font = Font(name="Cairo", bold=True, color=WHITE, size=12)
    c.fill = PatternFill("solid", fgColor=ORANGE)
    c.alignment = CENTER; c.border = BORDER

    for ci, key in enumerate(col_keys, 1):
        if key in PRICE_KEYS:
            cl = get_column_letter(ci)
            c = ws.cell(TOTAL_ROW, ci, f"=SUM({cl}{DATA_START}:{cl}{DATA_END})")
            c.font = Font(name="Cairo", bold=True, color=WHITE, size=12)
            c.fill = PatternFill("solid", fgColor=ORANGE)
            c.alignment = Alignment(horizontal="center", vertical="center")
            c.border = BORDER
            c.number_format = '#,##0 "ج"'
        elif key == "status":
            c = ws.cell(TOTAL_ROW, ci, f"{n_rows} زيارة")
            c.font = Font(name="Cairo", bold=True, color=WHITE, size=12)
            c.fill = PatternFill("solid", fgColor=ORANGE)
            c.alignment = CENTER; c.border = BORDER
    ws.row_dimensions[TOTAL_ROW].height = 28

    # ════════════════════════════════════════
    # جدول الأطباء (تحت الجدول الرئيسي)
    # ════════════════════════════════════════
    DOC_COLS   = ["م","اسم الدكتور","عدد الزيارات","إجمالي بعد الخصم","بدل الزيارة (5%)","بدل الانتقال","الإجمالي"]
    n_doc_cols = len(DOC_COLS)
    DOC_TITLE  = TOTAL_ROW + 2
    DOC_HDR    = TOTAL_ROW + 3
    DOC_DATA   = TOTAL_ROW + 4

    ws.row_dimensions[TOTAL_ROW + 1].height = 16

    ws.merge_cells(start_row=DOC_TITLE, start_column=1, end_row=DOC_TITLE, end_column=n_doc_cols)
    c = ws.cell(DOC_TITLE, 1, "📊 ملخص الأطباء — بدل الزيارات")
    c.font = Font(name="Cairo", bold=True, color=WHITE, size=12)
    c.fill = PatternFill("solid", fgColor=DOC_HDR_BG)
    c.alignment = CENTER
    ws.row_dimensions[DOC_TITLE].height = 26

    for ci, label in enumerate(DOC_COLS, 1):
        c = ws.cell(DOC_HDR, ci, label)
        c.font = Font(name="Cairo", bold=True, color=WHITE, size=11)
        c.fill = PatternFill("solid", fgColor=DOC_HDR_BG)
        c.alignment = CENTER; c.border = BORDER
    ws.row_dimensions[DOC_HDR].height = 28

    # حساب كل دكتور
    doc_data = {}
    for _, row in df_valid.iterrows():
        doc = str(row.get("doctor_name","غير محدد") or "غير محدد")
        if doc not in doc_data:
            doc_data[doc] = {"count":0,"after":0,"transport":0}
        doc_data[doc]["count"]     += 1
        doc_data[doc]["after"]     += float(row.get("labs_price_after",0) or 0)
        doc_data[doc]["transport"] += float(row.get("transport_fee",0) or 0)

    docs_sorted = sorted(doc_data.items(), key=lambda x: x[1]["count"], reverse=True)

    for idx, (doc_name, d) in enumerate(docs_sorted):
        ri = DOC_DATA + idx
        allowance = d["after"] * 0.05
        total_doc = allowance + d["transport"]
        fc = WHITE if idx % 2 == 0 else "F5F5F5"
        for ci, val in enumerate([idx+1, doc_name, d["count"], d["after"], allowance, d["transport"], total_doc], 1):
            c = ws.cell(ri, ci, val)
            c.font   = Font(name="Cairo", size=11)
            c.fill   = PatternFill("solid", fgColor=fc)
            c.border = BORDER
            c.alignment = CENTER if ci != 2 else RIGHT
            if ci >= 4:
                c.number_format = '#,##0.## "ج"'
        ws.row_dimensions[ri].height = 22

    n_docs        = len(docs_sorted)
    DOC_TOTAL_ROW = DOC_DATA + n_docs
    tot_after = sum(d["after"]     for _,d in docs_sorted)
    tot_allow = tot_after * 0.05
    tot_trans = sum(d["transport"] for _,d in docs_sorted)
    tot_grand = tot_allow + tot_trans

    ws.merge_cells(start_row=DOC_TOTAL_ROW, start_column=1, end_row=DOC_TOTAL_ROW, end_column=2)
    c = ws.cell(DOC_TOTAL_ROW, 1, "الإجمالي")
    c.font = Font(name="Cairo", bold=True, color=WHITE, size=12)
    c.fill = PatternFill("solid", fgColor=ORANGE)
    c.alignment = CENTER; c.border = BORDER

    for ci, val in [(3, sum(d["count"] for _,d in docs_sorted)),
                    (4, tot_after),(5, tot_allow),(6, tot_trans),(7, tot_grand)]:
        c = ws.cell(DOC_TOTAL_ROW, ci, val)
        c.font = Font(name="Cairo", bold=True, color=WHITE, size=12)
        c.fill = PatternFill("solid", fgColor=ORANGE)
        c.alignment = Alignment(horizontal="center", vertical="center")
        c.border = BORDER
        if ci >= 4:
            c.number_format = '#,##0.## "ج"'
    ws.row_dimensions[DOC_TOTAL_ROW].height = 26

    # ── عرض الأعمدة ──
    for ci, key in enumerate(col_keys, 1):
        ws.column_dimensions[get_column_letter(ci)].width = WIDTHS_MAIN.get(key, 14)
    for ci, w in enumerate([5,18,14,18,16,14,14], 1):
        cur = ws.column_dimensions[get_column_letter(ci)].width
        ws.column_dimensions[get_column_letter(ci)].width = max(cur, w)

    ws.freeze_panes = "A4"
    wb.save(fname)
    return df, fname
def import_from_excel(uploaded_file):
    df = pd.read_excel(uploaded_file, engine="openpyxl")
    required_cols = {"id", "name", "phone", "visit_date", "address"}
    if not required_cols.issubset(df.columns):
        st.error("ملف Excel غير صالح: ينقصه أعمدة أساسية")
        return 0
    count = 0
    for _, row in df.iterrows():
        record = row.to_dict()
        record.setdefault("created_at", datetime.now().isoformat())
        record.setdefault("visit_time", "")
        record.setdefault("doctor_name", "")
        record.setdefault("branch", "La Cite")
        record.setdefault("location_link", "")
        record.setdefault("selected_labs_text", "")
        record.setdefault("notes", "")
        record.setdefault("labs_price_before", 0)
        record.setdefault("labs_price_after", 0)
        record.setdefault("transport_fee", 0)
        record.setdefault("total_price", 0)
        record.setdefault("age_unit", "سنة")
        record.setdefault("status", "مجدولة")
        if "age" not in record or pd.isna(record["age"]):
            record["age"] = 0
        if fetch_visit_by_id(record["id"]):
            update_visit(record)
        else:
            insert_visit(record)
        count += 1
    return count

# ══════════════════════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════════════════════
def inject_css():
    css = """
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
      html, body, [class*="css"] { font-family: 'Cairo', sans-serif !important; direction: rtl; }
      .main { background: #fff8f0; }
      .block-container { padding-top: 0.5rem !important; max-width: 680px; }
      .ohv-header {
        background: linear-gradient(90deg, #FF6B00, #FF9A3C);
        border-radius: 16px; padding: 16px 22px;
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 18px; box-shadow: 0 4px 20px rgba(255,107,0,0.3);
      }
      .ohv-header h1 { color:#fff; margin:0; font-size:20px; font-weight:800; }
      .ohv-header span { color:rgba(255,255,255,0.85); font-size:12px; }
      .stat-grid { display:flex; gap:10px; margin-bottom:18px; flex-wrap:wrap; }
      .stat-box { flex:1; min-width:80px; background:#fff; border-radius:14px; padding:12px;
                  text-align:center; border:1px solid #ffe8d1; box-shadow:0 2px 10px rgba(0,0,0,0.05); }
      .stat-num { font-size:24px; font-weight:800; color:#FF6B00; }
      .stat-label { font-size:10px; color:#aaa; margin-top:2px; }
      .visit-card { background:#fff; border-radius:14px; padding:14px; margin-bottom:10px;
                    border:1px solid #ffe8d1; box-shadow:0 2px 10px rgba(0,0,0,0.05); }
      .visit-name { font-size:15px; font-weight:700; color:#222; margin-top:6px; }
      .visit-meta { font-size:12px; color:#888; margin-top:4px; }
      .visit-badge { background:#fff3e6; color:#FF6B00; border-radius:8px;
                     padding:3px 10px; font-size:12px; font-weight:700; float:left; }
      .status-badge { display:inline-block; border-radius:20px; padding:3px 12px;
                      font-size:11px; font-weight:700; color:#fff; margin-right:4px; }
      .price-box { background: linear-gradient(135deg, #FF6B00, #FF9A3C);
                   border-radius:16px; padding:16px 20px; color:#fff; margin-bottom:14px; }
      .price-row { display:flex; justify-content:space-between; font-size:14px; margin-bottom:7px; }
      .price-total { display:flex; justify-content:space-between; font-size:19px; font-weight:800;
                     border-top:2px solid rgba(255,255,255,0.3); padding-top:9px; margin-top:5px; }
      .wa-btn { display:block; padding:11px 16px; border-radius:12px; color:#fff !important;
                font-weight:700; font-size:13px; text-decoration:none; text-align:center;
                font-family:'Cairo',sans-serif; margin-bottom:8px; }
      .wa-client { background:#25D366; }
      .wa-share  { background:#128C7E; }
      .wa-group  { background:#075E54; }
      .detail-row { display:flex; justify-content:space-between; padding:8px 0;
                    border-bottom:1px solid #f5f5f5; font-size:13px; }
      .detail-label { color:#888; }
      .detail-value { font-weight:600; color:#222; max-width:58%; text-align:left; }
      .repeat-banner { background:#fff8f0; border:2px dashed #FF9A3C; border-radius:14px;
                       padding:12px; text-align:center; margin-top:12px;
                       color:#FF6B00; font-weight:700; font-size:14px; }
      .section-title { font-size:14px; font-weight:700; color:#FF6B00;
                       border-right:4px solid #FF6B00; padding-right:10px; margin-bottom:10px; }
      .history-card { background:#f9f9f9; border-radius:10px; padding:10px 14px;
                      margin-bottom:8px; border-right:4px solid #FF9A3C; font-size:13px; }
      .today-header { background:linear-gradient(90deg,#27AE60,#2ECC71); border-radius:14px;
                      padding:12px 18px; color:#fff; font-weight:800; font-size:15px;
                      margin-bottom:14px; text-align:center; }
      div[data-testid="stButton"] button {
        font-family:'Cairo',sans-serif !important; font-weight:700 !important; border-radius:12px !important; }
      div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label,
      div[data-testid="stDateInput"] label, div[data-testid="stTextArea"] label,
      div[data-testid="stMultiSelect"] label, div[data-testid="stSelectbox"] label {
        font-family:'Cairo',sans-serif !important; font-weight:600 !important; color:#555 !important; }
      div[data-testid="stTextInput"] input,
      div[data-testid="stNumberInput"] input,
      div[data-testid="stTextArea"] textarea,
      div[data-testid="stDateInput"] input {
        background-color: #FFF3E8 !important; border: 1.5px solid #FFBB80 !important;
        border-radius: 8px !important; color: #222 !important; }
      div[data-testid="stTextInput"] input:focus,
      div[data-testid="stNumberInput"] input:focus,
      div[data-testid="stTextArea"] textarea:focus,
      div[data-testid="stDateInput"] input:focus {
        background-color: #FFE8CC !important; border: 2px solid #FF6B00 !important;
        box-shadow: 0 0 0 3px rgba(255,107,0,0.15) !important; outline: none !important; }
      div[data-testid="stSelectbox"] > div > div {
        background-color: #FFF3E8 !important; border: 1.5px solid #FFBB80 !important;
        border-radius: 8px !important; }
      #MainMenu { visibility: hidden; }
      footer { visibility: hidden; }
      header { visibility: hidden; }
      @media print {
        body * { visibility: hidden; }
        #printable-report, #printable-report * { visibility: visible; }
        #printable-report { position: absolute; left: 0; top: 0; width: 100%; }
        .no-print { display: none; }
      }
    </style>
    """
    st.components.v1.html(css, height=0)

inject_css()

# ══════════════════════════════════════════════════════════════════════════════
# Quick Panels
# ══════════════════════════════════════════════════════════════════════════════
QUICK_PANELS = [
    {"name": "🩸 CBC",         "tests": ["CBC"]},
    {"name": "🍬 Diabetes",    "tests": ["HbA1C","Urea","Creatinine (Serum)","Uric Acid","ALT (SGPT)","AST (SGOT)","Urine Examination"]},
    {"name": "❤️ Cardiac",    "tests": ["Cholesterol","HDL","LDL","Triglycerides","ALT (SGPT)","AST (SGOT)","Uric Acid"]},
    {"name": "🦋 Thyroid",     "tests": ["TSH","FT3","FT4"]},
    {"name": "🔋 Fatigue",     "tests": ["CBC","Ferritin","Vitamin D3(25 Hydroxy Cholecal.)","TSH"]},
    {"name": "🧪 Kidney",      "tests": ["Urea","Creatinine (Serum)","Uric Acid","Urine Examination"]},
    {"name": "🫀 Liver",       "tests": ["ALT (SGPT)","AST (SGOT)","Albumin (ALB)","Bilirubin Total","Alkaline Phosphatase (ALP)"]},
    {"name": "🌟 General",     "tests": ["CBC","Cholesterol","HDL","LDL","Triglycerides","HbA1C","TSH",
                                          "ALT (SGPT)","AST (SGOT)","Urea","Creatinine (Serum)","Urine Examination"]},
]

# ══════════════════════════════════════════════════════════════════════════════
# محرك الاقتراحات الذكي
# ══════════════════════════════════════════════════════════════════════════════

# ── قواعد الـ Bundles (عروض التوفير) ──
# لو العميل اختار واحد من القائمة → يُقترح البديل الأوفر
BUNDLE_RULES = [
    {
        "trigger":  ["Vitamin D3(25 Hydroxy Cholecal.)"],
        "bundle":   "Vitamin D3 Couple",          # الاسم في السيستم لو موجود
        "note":     "💡 عرض الفردين بسعر أوفر — وفّر فلوس!",
        "saving_fn": lambda price_lookup: (
            price_lookup.get("Vitamin D3(25 Hydroxy Cholecal.)", 400) * 2
            - price_lookup.get("Vitamin D3 Couple",
              price_lookup.get("Vitamin D3(25 Hydroxy Cholecal.)", 400) + 200)
        ),
        # لو مفيش bundle في السيستم، يقترح إضافة تحليل ثاني بخصم
        "fallback_add": "Vitamin D3(25 Hydroxy Cholecal.)",
        "fallback_note": "💡 إضافة فيتامين د ثاني للفردين بخصم خاص — راجع السعر مع الإدارة",
    },
]

# ── قواعد Panel Completion ──
# لو العميل اختار X% من panel معين → اقترح الباقي
PANEL_SUGGEST_RULES = [
    {
        "panel":       "🍬 Diabetes",
        "core":        ["HbA1C"],
        "suggest":     ["Urea","Creatinine (Serum)","ALT (SGPT)","Urine Examination","Uric Acid","AST (SGOT)"],
        "reason":      "متابعة مريض السكر — يُنصح بقياس وظائف الكلى والكبد",
    },
    {
        "panel":       "❤️ Cardiac",
        "core":        ["Cholesterol","Triglycerides"],
        "suggest":     ["HDL","LDL","ALT (SGPT)","Uric Acid"],
        "reason":      "تقييم القلب والأوعية الدموية الكامل",
    },
    {
        "panel":       "🦋 Thyroid",
        "core":        ["TSH"],
        "suggest":     ["FT3","FT4"],
        "reason":      "TSH وحده غير كافٍ — يُنصح بالثلاثي الكامل",
    },
    {
        "panel":       "🧪 Kidney",
        "core":        ["Urea","Creatinine (Serum)"],
        "suggest":     ["Uric Acid","Urine Examination"],
        "reason":      "تقييم وظائف الكلى الكامل",
    },
    {
        "panel":       "🫀 Liver",
        "core":        ["ALT (SGPT)","AST (SGOT)"],
        "suggest":     ["Albumin (ALB)","Bilirubin Total","Alkaline Phosphatase (ALP)","GGT"],
        "reason":      "تقييم وظائف الكبد الكامل",
    },
    {
        "panel":       "🔋 Fatigue",
        "core":        ["CBC","Ferritin"],
        "suggest":     ["Vitamin D3(25 Hydroxy Cholecal.)","TSH","B12"],
        "reason":      "الإجهاد المزمن — شيّك على الفيتامينات والغدة",
    },
    {
        "panel":       "🩸 Anemia",
        "core":        ["CBC"],
        "suggest":     ["Ferritin","Iron (Serum)","TIBC","B12","Folic Acid"],
        "reason":      "CBC وحده لا يكفي لتشخيص الأنيميا — أضف مؤشرات الحديد",
    },
    {
        "panel":       "🌟 General",
        "core":        ["CBC","Cholesterol","HbA1C"],
        "suggest":     ["TSH","Vitamin D3(25 Hydroxy Cholecal.)","Ferritin"],
        "reason":      "فحص شامل — أضف فيتامين د والغدة الدرقية لصورة أكتمل",
    },
]

# ── قواعد Clinical (علاقات طبية ثابتة) ──
CLINICAL_RULES = [
    {
        "if_present":  ["HbA1C","Cholesterol"],
        "suggest":     ["Creatinine (Serum)","ALT (SGPT)"],
        "reason":      "مريض سكر + دهون → وظائف كلى وكبد ضرورية",
    },
    {
        "if_present":  ["TSH"],
        "suggest":     ["Cholesterol","CBC"],
        "reason":      "اضطراب الغدة الدرقية يؤثر على الدهون والدم",
    },
    {
        "if_present":  ["Ferritin"],
        "suggest":     ["CBC","Iron (Serum)"],
        "reason":      "فيريتين بدون صورة دم ومخزون حديد غير مكتمل",
    },
    {
        "if_present":  ["Creatinine (Serum)","Urea"],
        "suggest":     ["Urine Examination","Uric Acid"],
        "reason":      "وظائف كلى — أضف تحليل بول وحمض يوريك",
    },
    {
        "if_present":  ["ALT (SGPT)","AST (SGOT)"],
        "suggest":     ["Albumin (ALB)","Bilirubin Total"],
        "reason":      "وظائف كبد جزئية — أضف الألبيومين والبيليروبين",
    },
    {
        "if_present":  ["Vitamin D3(25 Hydroxy Cholecal.)"],
        "suggest":     ["Calcium (Serum)","Phosphorus (Serum)"],
        "reason":      "فيتامين د مع الكالسيوم والفوسفور للتقييم الكامل",
    },
    {
        "if_present":  ["CBC","Ferritin","Vitamin D3(25 Hydroxy Cholecal.)"],
        "suggest":     ["B12","Folic Acid"],
        "reason":      "فحص إجهاد شامل — أضف ب12 وحمض الفوليك",
    },
]

def get_smart_suggestions(selected_labs_list, price_lookup):
    """
    يحلل التحاليل المختارة ويرجع:
    - panel_suggestions: اقتراحات إكمال Panels
    - clinical_suggestions: اقتراحات طبية
    - bundle_suggestions: عروض توفير
    كل اقتراح: {name, reason, price, type}
    """
    # استخراج أسماء التحاليل النظيفة (بدون السعر)
    clean_selected = set()
    for entry in selected_labs_list:
        name = entry.split(" — ")[0].strip()
        clean_selected.add(name)

    all_suggestions = {}

    def add_suggestion(name, reason, stype):
        if name not in clean_selected and name not in all_suggestions:
            price = price_lookup.get(name, 0)
            all_suggestions[name] = {
                "name":   name,
                "reason": reason,
                "price":  price,
                "type":   stype,
            }

    # ── Panel Completion ──
    for rule in PANEL_SUGGEST_RULES:
        matched_core = [t for t in rule["core"] if t in clean_selected]
        if not matched_core:
            continue
        missing = [t for t in rule["suggest"] if t not in clean_selected]
        if missing:
            for t in missing:
                add_suggestion(t, f"{rule['panel']} — {rule['reason']}", "panel")

    # ── Clinical Rules ──
    for rule in CLINICAL_RULES:
        if all(t in clean_selected for t in rule["if_present"]):
            for t in rule["suggest"]:
                add_suggestion(t, rule["reason"], "clinical")

    # ── Bundle Rules ──
    bundle_suggestions = []
    for rule in BUNDLE_RULES:
        if any(t in clean_selected for t in rule["trigger"]):
            # لو العميل اختار فيتامين د واحد بس
            vd_count = sum(1 for e in selected_labs_list
                           if "Vitamin D3(25 Hydroxy Cholecal.)" in e)
            if vd_count == 1:
                bundle_price = price_lookup.get("Vitamin D3 Couple", 0)
                single_price = price_lookup.get("Vitamin D3(25 Hydroxy Cholecal.)", 400)
                if bundle_price > 0:
                    saving = single_price * 2 - bundle_price
                    bundle_suggestions.append({
                        "name":    "Vitamin D3 Couple",
                        "note":    f"💡 استبدل بـ Couple وادفع {bundle_price} بدل {single_price*2} — توفير {saving} جنيه!",
                        "action":  "replace",
                        "remove":  "Vitamin D3(25 Hydroxy Cholecal.)",
                        "price":   bundle_price,
                        "saving":  saving,
                    })
                else:
                    # مفيش bundle في السيستم — اقترح إضافة تاني بخصم
                    bundle_suggestions.append({
                        "name":    "Vitamin D3(25 Hydroxy Cholecal.)",
                        "note":    f"💡 إضافة فيتامين د ثاني للفردين — السعر الإجمالي {single_price + 200} بدل {single_price * 2}",
                        "action":  "add_discounted",
                        "price":   200,
                        "saving":  single_price - 200,
                    })

    return all_suggestions, bundle_suggestions

# ══════════════════════════════════════════════════════════════════════════════
# قائمة الأسعار
# ══════════════════════════════════════════════════════════════════════════════
try:
    from labs_price_list import LABS_DB
    ALL_LABS = [{"name": t["name"], "price": t["price"], "category": cat}
                for cat, tests in LABS_DB.items() for t in tests]
    LABS_PRICE_LOOKUP = {t["name"]: t["price"] for t in ALL_LABS}
except Exception as e:
    st.error(f"خطأ في استيراد labs_price_list: {e}")
    ALL_LABS = []
    LABS_PRICE_LOOKUP = {}

# ══════════════════════════════════════════════════════════════════════════════
# دوال مساعدة
# ══════════════════════════════════════════════════════════════════════════════
def format_date_ar(d):
    if not d:
        return ""
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, "%Y-%m-%d").date()
        except:
            return d
    return f"{d.day} {MONTHS_AR[d.month-1]} {d.year}"

def make_whatsapp_msg(v, target="internal"):
    lpb   = v.get("labs_price_before", 0)
    lpa   = v.get("labs_price_after", 0)
    tf    = v.get("transport_fee", 0)
    total = v.get("total_price", 0)
    vdate = format_date_ar(v.get("visit_date", ""))
    vtime = v.get("visit_time", "")
    dt_str= vdate + (f" — {vtime}" if vtime else "")
    doc   = v.get("doctor_name", "غير محدد")
    addr  = v.get("address", "")
    loc   = v.get("location_link", "")
    br    = v.get("branch", "")
    cname = v.get("name", "")
    age   = v.get("age", "")
    au    = v.get("age_unit", "سنة")
    age_s = f"🎂 *العمر:* {age} {au}\n" if age else ""
    lt    = v.get("selected_labs_text", "")
    if lt.strip():
        labs_lines = "\n".join(f"🧪 {l.strip()}" for l in lt.splitlines() if l.strip()) + "\n"
    else:
        labs_lines = "🚫 لا توجد تحاليل\n"
    loc_line = f"📍 *الموقع:* {loc}\n" if loc else ""
    br_line  = f"🏥 *الفرع:* {br}\n"   if br  else ""
    status   = v.get("status", "مجدولة")

    if target == "client":
        return (
            f"🟠 *Orange Lab Home Visit*\n"
            f"🏠 أهلاً بك {cname}\n"
            f"━━━━━━━━━━━━━━\n"
            f"👨‍⚕️ *الدكتور القائم بالزيارة:* {doc}\n"
            f"📅 *موعد الزيارة:* {dt_str}\n"
            f"━━━━━━━━━━━━━━\n"
            f"📍 *عنوان الزيارة:*\n{addr}\n"
            f"{loc_line}{br_line}"
            f"━━━━━━━━━━━━━━\n"
            f"🧪 *التحاليل المطلوبة:*\n{labs_lines}"
            f"━━━━━━━━━━━━━━\n"
            f"💰 *السعر قبل الخصم:* {lpb} جنيه\n"
            f"💰 *السعر بعد الخصم:* {lpa} جنيه\n"
            f"🚗 *بدل الانتقال:* {tf} جنيه\n"
            f"💵 *الإجمالي المطلوب:* {total} جنيه\n"
            f"━━━━━━━━━━━━━━\n"
            f"✏️ *برجاء تأكيد حجزك بالرد برقم:*\n"
            f"  1 - تأكيد الزيارة\n"
            f"  2 - تأجيل الزيارة\n"
            f"  3 - إلغاء الزيارة\n\n"
            f"شكراً لثقتكم 🧡 *معمل أورانج لاب*"
        )
    elif target == "group":
        return (
            f"🟠 *زيارة منزلية*\n"
            f"━━━━━━━━━━━━━━\n"
            f"👨‍⚕️ *الدكتور القائم بالزيارة:* {doc}\n"
            f"📅 *الموعد:* {dt_str}"
        )
    else:  # internal
        notes_line = f"📝 *ملاحظات:* {v.get('notes','')}\n" if v.get("notes") else ""
        return (
            f"🟠 *Orange Lab Home Visit*\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 *الاسم:* {v['name']}\n"
            f"{age_s}"
            f"📞 *التليفون:* {v.get('phone','')}\n"
            f"📅 *الموعد:* {dt_str}\n"
            f"👨‍⚕️ *دكتور الزيارة:* {doc}\n"
            f"🏥 *الفرع:* {br}\n"
            f"🔖 *الحالة:* {STATUS_ICONS.get(status,'')} {status}\n"
            f"━━━━━━━━━━━━━━\n"
            f"📍 *العنوان:* {addr}\n"
            f"{loc_line}"
            f"━━━━━━━━━━━━━━\n"
            f"🧪 *التحاليل المطلوبة:*\n{labs_lines}"
            f"━━━━━━━━━━━━━━\n"
            f"💰 *السعر قبل الخصم:* {lpb} جنيه\n"
            f"💰 *السعر بعد الخصم:* {lpa} جنيه\n"
            f"🚗 *بدل الانتقال:* {tf} جنيه\n"
            f"💵 *الإجمالي:* {total} جنيه\n"
            f"━━━━━━━━━━━━━━\n"
            f"{notes_line}"
        )

def whatsapp_link(msg, phone=None):
    encoded = urllib.parse.quote(msg, encoding="utf-8")
    if phone:
        p = phone.strip().replace(" ","").replace("-","").replace("+","")
        if p.startswith("0"):
            p = "20" + p[1:]
        elif not p.startswith("20"):
            p = "20" + p
        return f"https://wa.me/{p}?text={encoded}"
    return f"https://wa.me/?text={encoded}"

def generate_visit_print_html(v):
    lt = v.get("selected_labs_text","")
    labs_rows = "".join(
        f"<tr><td style='padding:6px 10px;border-bottom:1px solid #eee;'>🔹 {l.strip()}</td></tr>"
        for l in lt.splitlines() if l.strip()
    ) if lt.strip() else "<tr><td>لا توجد تحاليل</td></tr>"
    status      = v.get("status","مجدولة")
    s_color     = STATUS_COLORS.get(status,"#888")
    s_icon      = STATUS_ICONS.get(status,"")
    loc_html    = f'<p style="font-size:12px;color:#FF6B00;">🗺️ {v.get("location_link","")}</p>' if v.get("location_link") else ""
    notes_html  = f'<div class="section"><div class="section-title">📌 ملاحظات</div><p style="font-size:13px;">{v.get("notes","")}</p></div>' if v.get("notes") else ""
    return f"""<!DOCTYPE html><html dir="rtl">
<head>
  <meta charset="UTF-8">
  <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;700;800&display=swap" rel="stylesheet">
  <style>
    body{{font-family:'Cairo',sans-serif;margin:30px;color:#222;background:#fff;}}
    .header{{background:linear-gradient(90deg,#FF6B00,#FF9A3C);color:#fff;border-radius:12px;
             padding:16px 22px;display:flex;justify-content:space-between;align-items:center;margin-bottom:20px;}}
    .header h2{{margin:0;font-size:20px;}}
    .header span{{font-size:13px;opacity:.85;}}
    .section{{margin-bottom:18px;}}
    .section-title{{color:#FF6B00;font-weight:800;font-size:14px;border-right:4px solid #FF6B00;
                    padding-right:10px;margin-bottom:10px;}}
    .row{{display:flex;justify-content:space-between;padding:7px 0;border-bottom:1px solid #f0f0f0;font-size:13px;}}
    .label{{color:#888;}} .value{{font-weight:700;}}
    .status-badge{{display:inline-block;background:{s_color};color:#fff;border-radius:20px;
                   padding:3px 14px;font-size:12px;font-weight:700;}}
    .price-box{{background:linear-gradient(135deg,#FF6B00,#FF9A3C);border-radius:12px;
                padding:14px 18px;color:#fff;margin-top:16px;}}
    .price-row{{display:flex;justify-content:space-between;font-size:13px;margin-bottom:6px;}}
    .price-total{{display:flex;justify-content:space-between;font-size:17px;font-weight:800;
                  border-top:2px solid rgba(255,255,255,.3);padding-top:8px;margin-top:4px;}}
    table{{width:100%;border-collapse:collapse;font-size:13px;}}
    .footer{{text-align:center;margin-top:30px;color:#aaa;font-size:11px;
             border-top:1px solid #eee;padding-top:12px;}}
  </style>
</head>
<body>
  <div class="header">
    <h2>🟠 Orange Lab Home Visit</h2>
    <span>📅 {format_date_ar(v.get('visit_date',''))}</span>
  </div>
  <div class="section">
    <div class="section-title">👤 بيانات العميل</div>
    <div class="row"><span class="label">الاسم</span><span class="value">{v['name']}</span></div>
    <div class="row"><span class="label">السن</span><span class="value">{v.get('age','')} {v.get('age_unit','سنة')}</span></div>
    <div class="row"><span class="label">التليفون</span><span class="value">{v.get('phone','')}</span></div>
    <div class="row"><span class="label">الموعد</span><span class="value">{format_date_ar(v.get('visit_date',''))} — {v.get('visit_time','')}</span></div>
    <div class="row"><span class="label">الدكتور</span><span class="value">{v.get('doctor_name','')}</span></div>
    <div class="row"><span class="label">الفرع</span><span class="value">{v.get('branch','')}</span></div>
    <div class="row"><span class="label">الحالة</span><span class="value"><span class="status-badge">{s_icon} {status}</span></span></div>
  </div>
  <div class="section">
    <div class="section-title">📍 العنوان</div>
    <p style="margin:6px 0;font-size:13px;">{v.get('address','')}</p>
    {loc_html}
  </div>
  <div class="section">
    <div class="section-title">🧪 التحاليل المطلوبة</div>
    <table><tbody>{labs_rows}</tbody></table>
  </div>
  {notes_html}
  <div class="price-box">
    <div class="price-row"><span>⭐ السعر قبل الخصم</span><span>{v.get('labs_price_before',0)} جنيه</span></div>
    <div class="price-row"><span>⭐ السعر بعد الخصم</span><span>{v.get('labs_price_after',0)} جنيه</span></div>
    <div class="price-row"><span>🚗 بدل الانتقال</span><span>{v.get('transport_fee',0)} جنيه</span></div>
    <div class="price-total"><span>💵 الإجمالي</span><span>{v.get('total_price',0)} جنيه</span></div>
  </div>
  <div class="footer">Orange Lab Home Visit — Developed by Dr / Hussein Ali 2026</div>
</body></html>"""

# ══════════════════════════════════════════════════════════════════════════════
# Session State
# ══════════════════════════════════════════════════════════════════════════════
for k, dv in [("page","home"),("prefill",{}),("selected_id",None),("search_q","")]:
    if k not in st.session_state:
        st.session_state[k] = dv

def go(page, prefill=None, visit_id=None):
    if page == "new" and (prefill is None or not prefill.get("_edit")):
        st.session_state.pop("added_labs_new_visit", None)
    st.session_state.page = page
    if prefill  is not None: st.session_state.prefill    = prefill
    if visit_id is not None: st.session_state.selected_id = visit_id
    st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# الشريط العلوي
# ══════════════════════════════════════════════════════════════════════════════
st.markdown(f'''
<div class="ohv-header">
  <h1>🟠 Orange Lab Home Visit</h1>
  <span>📅 {format_date_ar(date.today())}</span>
</div>
''', unsafe_allow_html=True)

if st.session_state.user_type == "admin":
    c1,c2,c3,c4,c5,c6 = st.columns([2,2,2,2,2,1])
    with c5:
        if st.button("📊 Dashboard", use_container_width=True): go("dashboard")
else:
    c1,c2,c3,c4,c6 = st.columns([2,2,2,2,1])

with c1:
    if st.button("🏠 الرئيسية",    use_container_width=True): go("home")
with c2:
    if st.button("➕ زيارة جديدة", use_container_width=True): go("new", prefill={})
with c3:
    if st.button("📅 اليوم",       use_container_width=True): go("today")
with c4:
    if st.button("📈 التقارير",    use_container_width=True): go("reports")
with c6:
    if st.button("🚪", help="تسجيل الخروج", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# visit card helper
# ══════════════════════════════════════════════════════════════════════════════
def visit_card_html(v):
    total      = v.get("total_price", 0)
    vdate      = format_date_ar(v.get("visit_date",""))
    vtime      = v.get("visit_time","")
    addr       = (v.get("address","") or "")
    addr_short = addr[:38] + ("..." if len(addr)>38 else "")
    lc         = len(v.get("selected_labs_text","").splitlines()) if v.get("selected_labs_text") else 0
    doc_show   = f" | 👨‍⚕️ {v.get('doctor_name','')}"  if v.get("doctor_name") else ""
    br_show    = f" | 🏥 {v.get('branch','')}"         if v.get("branch")      else ""
    age        = v.get("age","")
    au         = v.get("age_unit","سنة")
    age_disp   = f"🎂 {age} {au}" if age else ""
    status     = v.get("status","مجدولة")
    sc         = STATUS_COLORS.get(status,"#888")
    si         = STATUS_ICONS.get(status,"")
    tag_auto   = get_client_tag(v.get("phone",""))
    tag_color  = get_client_tag_color(tag_auto)
    rating     = int(v.get("rating", 0) or 0)
    stars      = "⭐" * rating if rating else ""
    return f'''
    <div class="visit-card">
      <span class="visit-badge">{total:,} جنيه</span>
      <span class="status-badge" style="background:{sc}">{si} {status}</span>
      <span style="background:{tag_color};color:#fff;border-radius:8px;padding:2px 8px;font-size:10px;font-weight:700;margin-right:4px;">{tag_auto}</span>
      <div class="visit-name">👤 {v['name']} {stars}</div>
      <div class="visit-meta">📞 {v.get('phone','')} &nbsp;|&nbsp; 📅 {vdate} {vtime} &nbsp; {age_disp}</div>
      <div class="visit-meta">📍 {addr_short}</div>
      <div class="visit-meta" style="margin-top:5px">🧪 {lc} تحليل{doc_show}{br_show}</div>
    </div>'''

# ══════════════════════════════════════════════════════════════════════════════
# صفحة الرئيسية
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "home":
    if st.session_state.user_type not in ["admin","diamond"]:
        st.info("ليس لديك صلاحية عرض بيانات الزيارات.")
        st.stop()

    conn        = get_connection()
    all_doctors = [r[0] for r in conn.execute("SELECT DISTINCT doctor_name FROM visits WHERE doctor_name != ''").fetchall()]
    all_branches= [r[0] for r in conn.execute("SELECT DISTINCT branch FROM visits").fetchall()]
    for lst in [all_branches, all_doctors]:
        if "الكل" not in lst: lst.insert(0, "الكل")

    st.markdown("### تصفية الزيارات")
    cf1,cf2,cf3,cf4 = st.columns(4)
    with cf1:
        if st.session_state.user_type == "diamond":
            selected_branch = "Diamond"
            st.selectbox("الفرع", ["Diamond"], disabled=True)
        else:
            selected_branch = st.selectbox("الفرع", all_branches, index=0)
    with cf2:
        selected_doctor = st.selectbox("الدكتور", all_doctors, index=0)
    with cf3:
        status_opts     = ["الكل"] + STATUS_OPTIONS
        selected_status = st.selectbox("الحالة", status_opts, index=0)
    with cf4:
        search_query = st.text_input("🔍 بحث", value=st.session_state.search_q, placeholder="اسم أو تليفون")
        st.session_state.search_q = search_query

    filters = {}
    if selected_branch != "الكل": filters["branch"] = selected_branch
    if selected_doctor != "الكل": filters["doctor"] = selected_doctor
    if selected_status != "الكل": filters["status"] = selected_status
    if search_query:               filters["search"] = search_query

    visits  = fetch_visits(filters)
    today_s = date.today().isoformat()
    all_vs  = fetch_visits({"branch":"Diamond"} if st.session_state.user_type=="diamond" else {})
    t_today = sum(1 for v in all_vs if v.get("visit_date")==today_s)
    t_rev   = sum(v.get("total_price",0) for v in all_vs if v.get("status")!="ملغية")
    t_done  = sum(1 for v in all_vs if v.get("status")=="تمت")

    st.markdown(f'''
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-num">{len(all_vs)}</div><div class="stat-label">إجمالي الزيارات</div></div>
      <div class="stat-box"><div class="stat-num">{t_today}</div><div class="stat-label">زيارات اليوم</div></div>
      <div class="stat-box"><div class="stat-num" style="color:#27AE60">{t_done}</div><div class="stat-label">تمت ✅</div></div>
      <div class="stat-box"><div class="stat-num" style="font-size:16px">{t_rev:,.0f}</div><div class="stat-label">الإيراد (جنيه)</div></div>
    </div>''', unsafe_allow_html=True)

    # ── أزرار التصدير / الاستيراد حسب نوع المستخدم ──
    if st.session_state.user_type in ["admin","diamond"]:
        with st.expander("📤 تصدير إلى Excel", expanded=False):
            st.markdown('<div style="font-size:13px;font-weight:700;color:#FF6B00;margin-bottom:8px">📅 اختر فترة التصدير</div>', unsafe_allow_html=True)
            exp_c1, exp_c2 = st.columns(2)
            with exp_c1:
                exp_from = st.date_input("من تاريخ", value=None, key="exp_from",
                                         help="اكتب أو اختر تاريخ البداية")
            with exp_c2:
                exp_to   = st.date_input("إلى تاريخ", value=date.today(), key="exp_to",
                                         help="اكتب أو اختر تاريخ النهاية")

            if st.session_state.user_type == "admin":
                exp_branch = st.selectbox("الفرع", ["كل الفروع","La Cite","Diamond"], key="exp_branch_sel")
                bf_exp = None if exp_branch == "كل الفروع" else exp_branch
                btn_label = f"📤 تصدير ({exp_branch})"
            else:
                bf_exp    = "Diamond"
                btn_label = "📤 تصدير زيارات Diamond"

            if st.button(btn_label, use_container_width=True, key="btn_export_home"):
                if not exp_from or not exp_to:
                    st.error("⚠️ من فضلك اختر تاريخ البداية والنهاية")
                elif exp_from > exp_to:
                    st.error("⚠️ تاريخ البداية أكبر من تاريخ النهاية!")
                else:
                    df_ex, path_ex = export_to_excel(
                        branch_filter=bf_exp,
                        date_from=exp_from.isoformat(),
                        date_to=exp_to.isoformat()
                    )
                    if df_ex.empty:
                        st.warning("لا توجد زيارات في هذه الفترة.")
                    else:
                        period_label = f"{exp_from} → {exp_to}"
                        fname_dl = f"{'diamond' if bf_exp=='Diamond' else 'visits'}_{exp_from}_{exp_to}.xlsx"
                        with open(path_ex,"rb") as fh:
                            st.download_button(
                                f"📥 تحميل ({period_label}) — {len(df_ex)} زيارة",
                                data=fh, file_name=fname_dl,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                key="dl_home_final"
                            )

    if st.session_state.user_type == "admin":
        uf = st.file_uploader("📥 استيراد من Excel", type=["xlsx"], key="import_excel")
        if uf:
            count = import_from_excel(uf)
            st.success(f"تم استيراد {count} زيارة!"); st.rerun()

    st.markdown("---")
    if not visits:
        st.info("لا توجد زيارات تطابق التصفية.")
    else:
        for v in visits:
            st.markdown(visit_card_html(v), unsafe_allow_html=True)
            if st.button(f"📂 فتح {v['name']}", key=f"o_{v['id']}", use_container_width=True):
                go("detail", visit_id=v["id"])

    st.markdown("""
    <div style="text-align:center;margin-top:50px;padding-top:20px;border-top:2px solid #FF6B00;
                color:#333;font-size:14px;font-weight:600;">
      Developed by <b>Dr / Hussein Ali</b> 2026 For <span style="color:#FF6B00;">Orange Lab 🍊</span>
    </div>""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# صفحة زيارات اليوم
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "today":
    if st.session_state.user_type not in ["admin","diamond"]:
        st.error("غير مصرح."); st.stop()

    f = {"date_exact": date.today().isoformat()}
    if st.session_state.user_type == "diamond":
        f["branch"] = "Diamond"
    today_visits = fetch_visits(f)

    st.markdown(
        f'<div class="today-header">📅 زيارات اليوم — {format_date_ar(date.today())} ({len(today_visits)} زيارة)</div>',
        unsafe_allow_html=True)

    done_t    = sum(1 for v in today_visits if v.get("status")=="تمت")
    pending_t = sum(1 for v in today_visits if v.get("status") in ["مجدولة","في الطريق"])
    rev_t     = sum(v.get("total_price",0) for v in today_visits if v.get("status")!="ملغية")

    st.markdown(f'''
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-num">{len(today_visits)}</div><div class="stat-label">إجمالي اليوم</div></div>
      <div class="stat-box"><div class="stat-num" style="color:#27AE60">{done_t}</div><div class="stat-label">تمت ✅</div></div>
      <div class="stat-box"><div class="stat-num" style="color:#F39C12">{pending_t}</div><div class="stat-label">متبقية 🕐</div></div>
      <div class="stat-box"><div class="stat-num" style="font-size:15px">{rev_t:,.0f}</div><div class="stat-label">إيراد اليوم</div></div>
    </div>''', unsafe_allow_html=True)

    if not today_visits:
        st.info("لا توجد زيارات مجدولة اليوم.")
    else:
        for v in today_visits:
            st.markdown(visit_card_html(v), unsafe_allow_html=True)
            tc1,tc2 = st.columns([3,1])
            with tc1:
                if st.button(f"📂 فتح {v['name']}", key=f"td_{v['id']}", use_container_width=True):
                    go("detail", visit_id=v["id"])
            with tc2:
                cur_idx  = STATUS_OPTIONS.index(v.get("status","مجدولة")) if v.get("status") in STATUS_OPTIONS else 0
                new_stat = st.selectbox("", STATUS_OPTIONS, index=cur_idx,
                                        key=f"st_{v['id']}", label_visibility="collapsed")
                if new_stat != v.get("status","مجدولة"):
                    update_status_only(v["id"], new_stat); st.rerun()

# ══════════════════════════════════════════════════════════════════════════════
# صفحة زيارة جديدة / تعديل
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "new":
    pf      = st.session_state.prefill or {}
    is_edit = pf.get("_edit", False)
    st.markdown(f"### {'✏️ تعديل الزيارة' if is_edit else '➕ زيارة جديدة'}")

    st.markdown('<div class="section-title">👤 البيانات الشخصية</div>', unsafe_allow_html=True)
    name  = st.text_input("الاسم الكامل *", value=pf.get("name",""))
    nc1,nc2 = st.columns(2)
    with nc1:
        age = st.number_input("العمر *", 0, 120, int(pf.get("age",0) or 0))
    with nc2:
        au_opts  = ["سنة","شهر"]
        cur_au   = pf.get("age_unit","سنة")
        if cur_au not in au_opts: cur_au = "سنة"
        age_unit = st.radio("الوحدة", au_opts, index=au_opts.index(cur_au), horizontal=True)
    phone = st.text_input("رقم التليفون *", value=pf.get("phone",""), placeholder="01xxxxxxxxx")

    # ── تحذير التكرار + تصنيف العميل (في الزيارات الجديدة فقط) ──
    if phone and len(phone) >= 10 and not is_edit:
        prev_visits = fetch_client_history(phone)
        if prev_visits:
            tag_auto  = get_client_tag(phone)
            tag_color = get_client_tag_color(tag_auto)
            last_v    = prev_visits[0]
            last_date = format_date_ar(last_v.get("visit_date",""))
            last_stat = last_v.get("status","")
            n_total   = len(prev_visits)
            st.markdown(f'''
            <div style="background:#FFF3CD;border:2px solid #F39C12;border-radius:12px;
                        padding:12px 16px;margin:8px 0;direction:rtl;">
              <div style="font-weight:800;color:#E67E22;font-size:14px;margin-bottom:6px;">
                ⚠️ هذا العميل موجود في النظام
              </div>
              <div style="font-size:13px;color:#333;line-height:1.8;">
                👤 <b>{last_v.get('name','')}</b> &nbsp;|&nbsp;
                <span style="background:{tag_color};color:#fff;border-radius:8px;
                             padding:2px 8px;font-size:11px;">{tag_auto}</span><br>
                📋 إجمالي الزيارات: <b>{n_total}</b><br>
                📅 آخر زيارة: <b>{last_date}</b> — {last_stat}
              </div>
            </div>''', unsafe_allow_html=True)

            col_use, col_ignore = st.columns(2)
            with col_use:
                if st.button("✅ استخدم بياناته السابقة", key="use_prev_data", use_container_width=True):
                    st.session_state.prefill = {
                        "name":        last_v.get("name",""),
                        "age":         last_v.get("age",""),
                        "age_unit":    last_v.get("age_unit","سنة"),
                        "phone":       last_v.get("phone",""),
                        "address":     last_v.get("address",""),
                        "location_link": last_v.get("location_link",""),
                        "doctor_name": last_v.get("doctor_name",""),
                        "branch":      last_v.get("branch","La Cite"),
                        "selected_labs_text": last_v.get("selected_labs_text",""),
                        "labs_price_before":  last_v.get("labs_price_before",0),
                        "labs_price_after":   last_v.get("labs_price_after",0),
                        "transport_fee":      last_v.get("transport_fee",100),
                        "visit_time":  "",
                        "notes":       "",
                    }
                    st.rerun()
            with col_ignore:
                if "ignore_dup_warning" not in st.session_state:
                    st.session_state.ignore_dup_warning = False
                if st.button("➕ متابعة كزيارة جديدة", key="ignore_dup", use_container_width=True):
                    st.session_state.ignore_dup_warning = True
                    st.rerun()
        else:
            # عميل جديد
            st.markdown('''<div style="background:#D5F5E3;border:1.5px solid #27AE60;border-radius:10px;
                          padding:8px 14px;margin:6px 0;font-size:13px;color:#1E8449;">
                          🆕 عميل جديد — لم يسبق له زيارة</div>''', unsafe_allow_html=True)
    DOCTOR_LIST = ["حسين علي","ايه جمال","محمد شفيق","شيرين احمد","محمد","عطيه","ضي","طارق الشافعي","أخرى..."]
    saved_doc   = pf.get("doctor_name","")
    doc_index   = DOCTOR_LIST.index(saved_doc) if saved_doc in DOCTOR_LIST else (len(DOCTOR_LIST)-1 if saved_doc else 0)
    doc_select  = st.selectbox("👨‍⚕️ الدكتور القائم بالزيارة", DOCTOR_LIST, index=doc_index)
    if doc_select == "أخرى...":
        doctor_name = st.text_input("اكتب اسم الدكتور", value=saved_doc if saved_doc not in DOCTOR_LIST else "", placeholder="اسم الدكتور...")
    else:
        doctor_name = doc_select
    branch      = st.selectbox("🏥 الفرع", ["La Cite","Diamond"],
                               index=0 if pf.get("branch","La Cite")=="La Cite" else 1)
    cur_status  = pf.get("status","مجدولة")
    if cur_status not in STATUS_OPTIONS: cur_status = "مجدولة"
    status = st.selectbox("🔖 حالة الزيارة", STATUS_OPTIONS, index=STATUS_OPTIONS.index(cur_status))

    dc1,dc2 = st.columns(2)
    with dc1:
        default_date = date.today()
        if pf.get("visit_date"):
            try: default_date = datetime.strptime(pf["visit_date"],"%Y-%m-%d").date()
            except: pass
        visit_date = st.date_input("📅 تاريخ الزيارة *", value=default_date)
    with dc2:
        st.markdown("🕐 وقت الزيارة")
        tc1,tc2,tc3 = st.columns([2,2,3])
        old_t = pf.get("visit_time","")
        ph,pm,pa = 12,0,"PM"
        if old_t:
            m = re_module.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', old_t, re_module.IGNORECASE)
            if m: ph,pm,pa = int(m.group(1)),int(m.group(2)),m.group(3).upper()
        with tc1: hour   = st.selectbox("ساعة", list(range(1,13)), index=ph-1 if 1<=ph<=12 else 11, key="hr_sel")
        with tc2: minute = st.selectbox("دقيقة", [0,15,30,45], index=[0,15,30,45].index(pm) if pm in [0,15,30,45] else 0, key="mn_sel")
        with tc3: ampm   = st.radio("", ["AM","PM"], index=0 if pa=="AM" else 1, horizontal=True, key="ap_sel")
    visit_time = f"{hour}:{minute:02d} {ampm}"
    st.markdown("---")

    st.markdown('<div class="section-title">📍 العنوان</div>', unsafe_allow_html=True)
    address       = st.text_area("العنوان بالتفصيل *", value=pf.get("address",""),
                                  placeholder="المحافظة - المدينة - الشارع - رقم المبنى - الدور - الشقة...", height=90)
    location_link = st.text_input("🗺️ رابط الموقع (Google Maps)", value=pf.get("location_link",""))
    st.markdown("---")

    vid_key     = pf.get("id","new_visit")
    labs_ss_key = f"added_labs_{vid_key}"
    if labs_ss_key not in st.session_state:
        if pf.get("selected_labs_text",""):
            st.session_state[labs_ss_key] = [l.strip() for l in pf["selected_labs_text"].splitlines() if l.strip()]
        else:
            st.session_state[labs_ss_key] = []

    st.markdown('<div class="section-title">⚡ Quick Panels</div>', unsafe_allow_html=True)
    st.caption("اضغط على panel لإضافة تحاليله فوراً — التحاليل المكررة لن تُضاف")
    pcols = st.columns(4)
    for i,panel in enumerate(QUICK_PANELS):
        with pcols[i%4]:
            if st.button(panel["name"], key=f"pnl_{vid_key}_{i}", use_container_width=True):
                existing = [e.split(" — ")[0].strip() for e in st.session_state[labs_ss_key]]
                for tn in panel["tests"]:
                    if tn not in existing:
                        st.session_state[labs_ss_key].append(tn)
                st.rerun()

    with st.expander("👁️ شاهد محتوى الـ Panels"):
        for panel in QUICK_PANELS:
            st.markdown(f'<div style="font-size:12px;margin-bottom:6px"><b style="color:#FF6B00">{panel["name"]}</b> — {" • ".join(panel["tests"])}</div>', unsafe_allow_html=True)

    st.markdown("---")
    if ALL_LABS:
        st.markdown('<div class="section-title">📋 إضافة تحليل من قائمة الأسعار</div>', unsafe_allow_html=True)
        lab_options = [f"{lab['name']} — {lab['price']} جنيه" for lab in ALL_LABS]
        sel_lab     = st.selectbox("اختر التحليل", lab_options, key=f"lps_{vid_key}")
        if st.button("➕ أضف من القائمة", key=f"alp_{vid_key}", use_container_width=True):
            if sel_lab not in st.session_state[labs_ss_key]:
                st.session_state[labs_ss_key].append(sel_lab)
            st.rerun()
    else:
        st.warning("قائمة الأسعار غير متاحة حالياً")

    st.markdown("---")
    st.markdown('<div class="section-title">🧪 التحاليل المضافة</div>', unsafe_allow_html=True)
    if st.session_state[labs_ss_key]:
        auto_total = sum(int(m.group(1)) for e in st.session_state[labs_ss_key]
                         for m in [re_module.search(r'(\d+)\s*جنيه', e)] if m)
        st.markdown(f'<div style="font-size:12px;color:#FF6B00;font-weight:700;margin-bottom:8px">'
                    f'✅ {len(st.session_state[labs_ss_key])} تحليل'
                    f'{"  —  إجمالي: "+f"{auto_total:,} جنيه" if auto_total else ""}</div>',
                    unsafe_allow_html=True)
        to_remove = None
        for i,entry in enumerate(st.session_state[labs_ss_key]):
            ca,cb = st.columns([10,1])
            with ca:
                st.markdown(f'<div style="font-size:13px;padding:4px 0;border-bottom:1px solid #f5f5f5;color:#333">🔹 {entry}</div>',
                            unsafe_allow_html=True)
            with cb:
                if st.button("✕", key=f"del_{vid_key}_{i}", help="احذف"): to_remove = i
        if to_remove is not None:
            st.session_state[labs_ss_key].pop(to_remove); st.rerun()
        if st.button("🗑️ مسح الكل", key=f"clr_{vid_key}"):
            st.session_state[labs_ss_key] = []; st.rerun()
    else:
        st.markdown('<div style="color:#aaa;font-size:13px;padding:8px 0">لا توجد تحاليل — اختر panel أو أضف يدوياً</div>',
                    unsafe_allow_html=True)

    cm1,cm2 = st.columns([8,2])
    with cm1:
        manual_entry = st.text_input("أضف تحليل يدوياً", placeholder="CBC — 400 جنيه", key=f"man_{vid_key}")
    with cm2:
        st.markdown('<div style="margin-top:28px"></div>', unsafe_allow_html=True)
        if st.button("➕ أضف", key=f"manb_{vid_key}", use_container_width=True):
            if manual_entry.strip():
                st.session_state[labs_ss_key].append(manual_entry.strip()); st.rerun()

    selected_labs_text = "\n".join(st.session_state[labs_ss_key])
    selected_labs      = st.session_state[labs_ss_key][:]

    # ─────────────────────────────────────────────────────────────────
    # 🤖 اقتراحات ذكية
    # ─────────────────────────────────────────────────────────────────
    if st.session_state[labs_ss_key] and LABS_PRICE_LOOKUP:
        sugg_all, bundle_sugg = get_smart_suggestions(
            st.session_state[labs_ss_key], LABS_PRICE_LOOKUP
        )
        if sugg_all or bundle_sugg:
            st.markdown(
                '<div style="background:linear-gradient(135deg,#1a1a2e,#16213e);border-radius:14px;'
                'padding:12px 16px;margin:12px 0;">'
                '<div style="color:#FF6B00;font-weight:800;font-size:14px;margin-bottom:4px;">'
                '🤖 اقتراحات ذكية</div></div>',
                unsafe_allow_html=True
            )

            # ── Bundle Offers أولاً ──
            for b in bundle_sugg:
                st.markdown(
                    f'<div style="background:#FFF9E6;border:2px solid #F39C12;border-radius:10px;'
                    f'padding:10px 14px;margin-bottom:8px;">'
                    f'<b style="color:#E67E22;">💰 عرض توفير</b><br>'
                    f'<span style="font-size:12px;color:#333;">{b["note"]}</span></div>',
                    unsafe_allow_html=True
                )
                if b["action"] == "replace":
                    bc1, bc2 = st.columns(2)
                    with bc1:
                        if st.button(f'🔄 استبدل بـ {b["name"]}', key=f'bundle_rep_{b["name"]}_{vid_key}', use_container_width=True):
                            st.session_state[labs_ss_key] = [
                                e for e in st.session_state[labs_ss_key]
                                if b["remove"] not in e
                            ]
                            price = LABS_PRICE_LOOKUP.get(b["name"], b["price"])
                            entry = f'{b["name"]} — {price} جنيه' if price else b["name"]
                            st.session_state[labs_ss_key].append(entry)
                            st.rerun()
                    with bc2:
                        st.button("❌ تجاهل العرض", key=f'bundle_ign_{b["name"]}_{vid_key}', use_container_width=True)
                elif b["action"] == "add_discounted":
                    if st.button(f'➕ أضف فيتامين د ثاني بـ {b["price"]} جنيه', key=f'bundle_add_{vid_key}', use_container_width=True):
                        st.session_state[labs_ss_key].append(
                            f'Vitamin D3(25 Hydroxy Cholecal.) — {b["price"]} جنيه (سعر خاص - الفردين)'
                        )
                        st.rerun()

            # ── Panel & Clinical Suggestions ──
            if sugg_all:
                shown_reasons = set()
                for lab_name, info in sugg_all.items():
                    if info["reason"] not in shown_reasons:
                        shown_reasons.add(info["reason"])
                        icon = "🔬" if info["type"] == "panel" else "⚕️"
                        st.markdown(
                            f'<div style="font-size:11px;color:#888;margin:8px 0 4px 0;'
                            f'border-right:3px solid #FF6B00;padding-right:8px;">{icon} {info["reason"]}</div>',
                            unsafe_allow_html=True
                        )
                    price_str = f' — {info["price"]} جنيه' if info["price"] else ""
                    sc1, sc2 = st.columns([7, 3])
                    with sc1:
                        st.markdown(
                            f'<div style="background:#F8F9FA;border-radius:8px;padding:7px 12px;'
                            f'font-size:12px;color:#222;border-right:3px solid #27AE60;">'
                            f'🧪 <b>{lab_name}</b>{price_str}</div>',
                            unsafe_allow_html=True
                        )
                    with sc2:
                        if st.button("➕ أضف", key=f'sugg_{lab_name}_{vid_key}', use_container_width=True):
                            existing_names = [e.split(" — ")[0].strip() for e in st.session_state[labs_ss_key]]
                            if lab_name not in existing_names:
                                entry = f'{lab_name} — {info["price"]} جنيه' if info["price"] else lab_name
                                st.session_state[labs_ss_key].append(entry)
                            st.rerun()

                st.markdown("---")
                if st.button("📋 أضف كل الاقتراحات لملاحظات الدكتور", key=f"add_all_notes_{vid_key}", use_container_width=True):
                    notes_text = "💡 اقتراحات النظام:\n"
                    for lab_name, info in sugg_all.items():
                        p = f' ({info["price"]} ج)' if info["price"] else ""
                        notes_text += f'• {lab_name}{p} — {info["reason"]}\n'
                    st.session_state[f"auto_notes_{vid_key}"] = notes_text
                    st.rerun()

    st.markdown("---")

    st.markdown('<div class="section-title">📌 ملاحظات</div>', unsafe_allow_html=True)
    auto_notes_val = st.session_state.get(f"auto_notes_{vid_key}", "")
    default_notes  = pf.get("notes","")
    if auto_notes_val and auto_notes_val not in default_notes:
        default_notes = (default_notes + "\n" + auto_notes_val).strip()
    notes = st.text_area("ملاحظات خاصة", value=default_notes, height=75)
    st.markdown("---")

    st.markdown('<div class="section-title">💰 الأسعار</div>', unsafe_allow_html=True)
    auto_labs_total = sum(int(m.group(1)) for e in selected_labs
                          for m in [re_module.search(r'(\d+)\s*جنيه', e)] if m)
    pp1,pp2,pp3 = st.columns(3)
    with pp1:
        labs_price_before = st.number_input("⭐ السعر قبل الخصم", min_value=0, step=10,
                                             value=auto_labs_total if auto_labs_total>0 else int(pf.get("labs_price_before",0) or 0))
    with pp2:
        labs_price_after  = st.number_input("⭐ السعر بعد الخصم", min_value=0, step=10,
                                             value=int(pf.get("labs_price_after",0) or 0))
    with pp3:
        transport_fee     = st.number_input("⭐ بدل الانتقال", min_value=0, step=10,
                                             value=int(pf.get("transport_fee",100) or 100))
    total_price = labs_price_after + transport_fee
    st.markdown(f'''
    <div class="price-box">
      <div class="price-row"><span>⭐ السعر قبل الخصم</span><span>{labs_price_before} جنيه</span></div>
      <div class="price-row"><span>⭐ السعر بعد الخصم</span><span>{labs_price_after} جنيه</span></div>
      <div class="price-row"><span>⭐ بدل الانتقال</span><span>{transport_fee} جنيه</span></div>
      <div class="price-total"><span>⭐ الإجمالي</span><span>{total_price} جنيه</span></div>
    </div>''', unsafe_allow_html=True)

    if st.button("💾 حفظ الزيارة" if not is_edit else "💾 حفظ التعديلات", use_container_width=True):
        if not name or not phone or not address:
            st.error("⚠️ من فضلك املأ الاسم والتليفون والعنوان")
        else:
            record = {
                "id": pf.get("id", str(int(datetime.now().timestamp()*1000))),
                "created_at": pf.get("created_at", datetime.now().isoformat()),
                "name": name, "age": age, "age_unit": age_unit,
                "phone": phone, "visit_date": visit_date.isoformat(),
                "visit_time": visit_time, "doctor_name": doctor_name,
                "branch": branch, "address": address, "location_link": location_link,
                "selected_labs_text": selected_labs_text, "notes": notes,
                "labs_price_before": labs_price_before, "labs_price_after": labs_price_after,
                "transport_fee": transport_fee, "total_price": total_price,
                "status": status,
            }
            if is_edit:
                update_visit(record); st.success("✅ تم تحديث الزيارة!")
            else:
                insert_visit(record); st.success("✅ تم حفظ الزيارة!")
            go("detail", visit_id=record["id"])

    if is_edit:
        if st.button("← رجوع بدون حفظ", use_container_width=True):
            go("detail", visit_id=pf.get("id"))

# ══════════════════════════════════════════════════════════════════════════════
# صفحة التفاصيل
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "detail":
    vid = st.session_state.selected_id
    v   = fetch_visit_by_id(vid) if vid else None
    if not v:
        st.error("لم يتم العثور على الزيارة"); go("home")
    else:
        lpb      = v.get("labs_price_before",0)
        lpa      = v.get("labs_price_after",0)
        tf       = v.get("transport_fee",0)
        tp       = v.get("total_price",0)
        vtime    = v.get("visit_time","")
        dt_disp  = format_date_ar(v.get("visit_date","")) + (f" — {vtime}" if vtime else "")
        age      = v.get("age","")
        au       = v.get("age_unit","سنة")
        age_str  = f"🎂 {age} {au}" if age else "🎂 غير محدد"
        status   = v.get("status","مجدولة")
        sc       = STATUS_COLORS.get(status,"#888")
        si       = STATUS_ICONS.get(status,"")

        st.markdown('<div class="section-title">👤 البيانات الشخصية</div>', unsafe_allow_html=True)
        st.markdown(f'''
        <div class="detail-row"><span class="detail-label">👤 الاسم</span><span class="detail-value">{v['name']}</span></div>
        <div class="detail-row"><span class="detail-label">🎂 السن</span><span class="detail-value">{age_str}</span></div>
        <div class="detail-row"><span class="detail-label">📞 التليفون</span><span class="detail-value">{v.get('phone','')}</span></div>
        <div class="detail-row"><span class="detail-label">📅 الموعد</span><span class="detail-value">{dt_disp}</span></div>
        <div class="detail-row"><span class="detail-label">👨‍⚕️ الدكتور</span><span class="detail-value">{v.get('doctor_name','')}</span></div>
        <div class="detail-row"><span class="detail-label">🏥 الفرع</span><span class="detail-value">{v.get('branch','')}</span></div>
        <div class="detail-row"><span class="detail-label">🔖 الحالة</span>
          <span class="detail-value"><span class="status-badge" style="background:{sc}">{si} {status}</span></span></div>
        ''', unsafe_allow_html=True)

        # تغيير الحالة السريع
        st.markdown("**⚡ تغيير الحالة السريع:**")
        qs_cols = st.columns(4)
        for col, sn in zip(qs_cols, STATUS_OPTIONS):
            with col:
                prefix = "✓ " if sn == status else ""
                if st.button(f"{prefix}{STATUS_ICONS[sn]} {sn}", key=f"qs_{v['id']}_{sn}", use_container_width=True):
                    update_status_only(v["id"], sn); st.rerun()
        st.markdown("---")

        st.markdown('<div class="section-title">📍 العنوان</div>', unsafe_allow_html=True)
        st.write(v.get("address",""))
        if v.get("location_link"):
            st.markdown(f'<a href="{v["location_link"]}" target="_blank" style="color:#FF6B00;font-weight:700;">🗺️ فتح الموقع على الخريطة</a>',
                        unsafe_allow_html=True)
        st.markdown("---")

        lt = v.get("selected_labs_text","")
        if lt.strip():
            st.markdown('<div class="section-title">🧪 التحاليل المطلوبة</div>', unsafe_allow_html=True)
            lines_html = "".join(f'<div class="detail-row"><span class="detail-label">🔹 {l.strip()}</span></div>'
                                 for l in lt.splitlines() if l.strip())
            st.markdown(f'<div style="background:#fffaf6;border-radius:12px;padding:8px 14px;border:1px solid #ffe8d1">{lines_html}</div>',
                        unsafe_allow_html=True)
            st.markdown("---")

        st.markdown(f'''
        <div class="price-box">
          <div class="price-row"><span>⭐ السعر قبل الخصم</span><span>{lpb} جنيه</span></div>
          <div class="price-row"><span>⭐ السعر بعد الخصم</span><span>{lpa} جنيه</span></div>
          <div class="price-row"><span>⭐ بدل الانتقال</span><span>{tf} جنيه</span></div>
          <div class="price-total"><span>⭐ الإجمالي</span><span>{tp} جنيه</span></div>
        </div>''', unsafe_allow_html=True)

        if v.get("notes"):
            st.markdown('<div class="section-title">📌 ملاحظات</div>', unsafe_allow_html=True)
            st.write(v["notes"]); st.markdown("---")

        # تاريخ العميل
        history = fetch_client_history(v.get("phone",""), exclude_id=v["id"])
        if history:
            with st.expander(f"📋 تاريخ العميل — {len(history)} زيارة سابقة"):
                for hv in history:
                    hs  = hv.get("status","مجدولة")
                    hsc = STATUS_COLORS.get(hs,"#888")
                    hsi = STATUS_ICONS.get(hs,"")
                    st.markdown(f'''
                    <div class="history-card">
                      <span class="status-badge" style="background:{hsc};font-size:10px">{hsi} {hs}</span>
                      <b>{format_date_ar(hv.get('visit_date',''))}</b> — {hv.get('visit_time','')}
                      <br>👨‍⚕️ {hv.get('doctor_name','')} &nbsp;|&nbsp; 💵 {hv.get('total_price',0):,} جنيه
                      <br>🧪 {len(hv.get('selected_labs_text','').splitlines()) if hv.get('selected_labs_text') else 0} تحليل
                    </div>''', unsafe_allow_html=True)
                    if st.button(f"📂 {format_date_ar(hv.get('visit_date',''))}", key=f"hv_{hv['id']}", use_container_width=True):
                        go("detail", visit_id=hv["id"])
            st.markdown("---")

        # ── تصنيف العميل ──
        client_tag   = get_client_tag(v.get("phone",""))
        tag_clr      = get_client_tag_color(client_tag)
        all_visits_c = fetch_client_history(v.get("phone",""))
        done_count   = sum(1 for hv in all_visits_c if hv.get("status")=="تمت")
        cur_rating   = int(v.get("rating", 0) or 0)

        stars_html = f'<span style="font-size:16px;">{"⭐"*cur_rating}</span>' if cur_rating else ""
        st.markdown(
            f'<div style="display:flex;gap:10px;align-items:center;margin-bottom:12px;flex-wrap:wrap;">'
            f'<span style="background:{tag_clr};color:#fff;border-radius:20px;padding:5px 14px;'
            f'font-weight:800;font-size:13px;">{client_tag}</span>'
            f'<span style="color:#888;font-size:12px;">زيارات مكتملة: <b style="color:#27AE60">{done_count}</b></span>'
            f'{stars_html}</div>',
            unsafe_allow_html=True
        )

        # ── تغيير Tag يدوي ──
        tag_options = ["🆕 عميل جديد","⭐ عميل منتظم","🌟 عميل متكرر","👑 VIP","🏢 Corporate"]
        saved_tag   = v.get("tag","") or client_tag
        if saved_tag not in tag_options: saved_tag = client_tag
        new_tag = st.selectbox("🏷️ تصنيف العميل", tag_options,
                               index=tag_options.index(saved_tag) if saved_tag in tag_options else 0,
                               key=f"tag_sel_{v['id']}")
        if new_tag != v.get("tag",""):
            update_tag(v["id"], new_tag)

        st.markdown("---")

        # ── تقييم الزيارة ──
        st.markdown('<div class="section-title">📊 تقييم الزيارة</div>', unsafe_allow_html=True)
        if status == "تمت":
            rating_cols = st.columns(6)
            with rating_cols[0]:
                st.markdown('<div style="font-size:13px;color:#888;padding-top:8px;">التقييم:</div>', unsafe_allow_html=True)
            for star_n in range(1,6):
                with rating_cols[star_n]:
                    star_icon = "⭐" if star_n <= cur_rating else "☆"
                    if st.button(f"{star_icon}{star_n}", key=f"star_{v['id']}_{star_n}", use_container_width=True):
                        update_rating(v["id"], star_n); st.rerun()
            if cur_rating:
                st.markdown(f'<div style="text-align:center;font-size:13px;color:#FF6B00;font-weight:700;margin-top:4px;">التقييم الحالي: {"⭐"*cur_rating} ({cur_rating}/5)</div>', unsafe_allow_html=True)

            # رسالة واتساب التقييم
            cname_r = v.get('name','')
            rating_msg = (
                f"🟠 *Orange Lab Home Visit*\n"
                f"━━━━━━━━━━━━━━\n"
                f"أهلاً {cname_r} 🌟\n"
                "شكراً لاختيارك معمل أورانج لاب للزيارة المنزلية!\n\n"
                "نتمنى أن الخدمة كانت على مستوى توقعاتك 🧡\n\n"
                "⭐ *قيّم خدمتنا من 1 إلى 5:*\n"
                "  1️⃣ - ضعيف\n"
                "  2️⃣ - مقبول\n"
                "  3️⃣ - جيد\n"
                "  4️⃣ - جيد جداً\n"
                "  5️⃣ - ممتاز\n\n"
                "رأيك يهمنا لتحسين خدماتنا 💛\n"
                "━━━━━━━━━━━━━━\n"
                "*معمل أورانج لاب*"
            )
            st.markdown(
                f'<a href="{whatsapp_link(rating_msg, v.get("phone"))}" target="_blank" '
                f'class="wa-btn" style="background:#9B59B6;margin-top:8px;">📊 إرسال طلب تقييم على واتساب</a>',
                unsafe_allow_html=True
            )
        else:
            st.info("التقييم متاح فقط بعد اكتمال الزيارة (حالة: تمت)")

        st.markdown("---")

        # واتساب
        st.markdown('<div class="section-title">📱 إرسال على واتساب</div>', unsafe_allow_html=True)
        wc1, wc2, wc3 = st.columns(3)
        with wc1:
            st.markdown(f'<a href="{whatsapp_link(make_whatsapp_msg(v,"client"),v.get("phone"))}" target="_blank" class="wa-btn wa-client">📱 للعميل</a>',
                        unsafe_allow_html=True)
        with wc2:
            st.markdown(f'<a href="{whatsapp_link(make_whatsapp_msg(v,"group"))}" target="_blank" class="wa-btn wa-group">👥 جروب</a>',
                        unsafe_allow_html=True)
        with wc3:
            st.markdown(f'<a href="{whatsapp_link(make_whatsapp_msg(v,"internal"))}" target="_blank" class="wa-btn wa-share">📋 ملخص</a>',
                        unsafe_allow_html=True)
        st.markdown("---")

        # طباعة
        st.markdown('<div class="section-title">🖨️ طباعة / تحميل</div>', unsafe_allow_html=True)
        print_html = generate_visit_print_html(v)
        st.download_button(
            label="⬇️ تحميل ورقة الزيارة (HTML للطباعة)",
            data=print_html.encode("utf-8"),
            file_name=f"زيارة_{v['name']}_{v.get('visit_date','')}.html",
            mime="text/html",
            use_container_width=True,
        )
        st.markdown("---")

        ec1,ec2 = st.columns(2)
        with ec1:
            if st.button("✏️ تعديل", use_container_width=True):
                go("new", prefill={**v, "_edit":True})
        with ec2:
            if st.button("🗑️ حذف", use_container_width=True):
                st.session_state["confirm_delete"] = True

        if st.session_state.get("confirm_delete"):
            st.warning("⚠️ هل أنت متأكد من الحذف؟")
            dc1,dc2 = st.columns(2)
            with dc1:
                if st.button("✅ نعم، احذف", use_container_width=True):
                    delete_visit(vid); st.session_state["confirm_delete"]=False; go("home")
            with dc2:
                if st.button("❌ إلغاء", use_container_width=True):
                    st.session_state["confirm_delete"]=False; st.rerun()

        st.markdown(f'<div class="repeat-banner">🔄 هتروح لـ {v["name"]} مرة تانية؟</div>', unsafe_allow_html=True)
        if st.button(f"➕ زيارة جديدة لـ {v['name']}", use_container_width=True):
            go("new", prefill={
                "name":v["name"],"age":v.get("age",""),"age_unit":v.get("age_unit","سنة"),
                "phone":v.get("phone",""),"address":v.get("address",""),
                "location_link":v.get("location_link",""),"doctor_name":v.get("doctor_name",""),
                "branch":v.get("branch","La Cite"),"selected_labs":[],"selected_labs_text":"",
                "visit_time":"","notes":"","labs_price_before":0,"labs_price_after":0,"transport_fee":100,
            })
        if st.button("← رجوع للقائمة", use_container_width=True):
            go("home")

# ══════════════════════════════════════════════════════════════════════════════
# صفحة التقارير
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "reports":
    if st.session_state.user_type not in ["admin","diamond"]:
        st.error("غير مصرح."); st.stop()

    st.markdown("### 📈 تقارير الزيارات")
    ry,rm,rb = st.columns(3)
    with ry: year  = st.selectbox("السنة", list(range(2023,2031)), index=3)
    with rm: month = st.selectbox("الشهر", list(range(1,13)),
                                   format_func=lambda m: MONTHS_AR[m-1],
                                   index=date.today().month-1)
    with rb:
        if st.session_state.user_type=="diamond":
            branch_filter="Diamond"; st.selectbox("الفرع",["Diamond"],disabled=True)
        else:
            branch_filter = st.selectbox("الفرع",["الكل","La Cite","Diamond"])

    filters = {"year":year,"month":month}
    if branch_filter!="الكل": filters["branch"]=branch_filter
    visits = fetch_visits(filters)

    # زر تصدير في صفحة التقارير
    st.markdown("---")
    with st.expander("📤 تصدير إلى Excel", expanded=False):
        st.markdown('<div style="font-size:13px;font-weight:700;color:#FF6B00;margin-bottom:8px">📅 اختر فترة التصدير</div>', unsafe_allow_html=True)
        rep_c1, rep_c2 = st.columns(2)
        with rep_c1:
            rep_from = st.date_input("من تاريخ", value=None, key="rep_from",
                                     help="اكتب أو اختر تاريخ البداية")
        with rep_c2:
            rep_to   = st.date_input("إلى تاريخ", value=date.today(), key="rep_to",
                                     help="اكتب أو اختر تاريخ النهاية")

        if st.session_state.user_type == "admin":
            bf_rep = None if branch_filter == "الكل" else branch_filter
            btn_rep_label = f"📤 تصدير ({branch_filter})"
        else:
            bf_rep = "Diamond"
            btn_rep_label = "📤 تصدير زيارات Diamond"

        if st.button(btn_rep_label, use_container_width=True, key="btn_export_reports"):
            if not rep_from or not rep_to:
                st.error("⚠️ من فضلك اختر تاريخ البداية والنهاية")
            elif rep_from > rep_to:
                st.error("⚠️ تاريخ البداية أكبر من تاريخ النهاية!")
            else:
                df_rep, path_rep = export_to_excel(
                    branch_filter=bf_rep,
                    date_from=rep_from.isoformat(),
                    date_to=rep_to.isoformat()
                )
                if df_rep.empty:
                    st.warning("لا توجد زيارات في هذه الفترة.")
                else:
                    period_rep  = f"{rep_from} → {rep_to}"
                    fname_rep   = f"{'diamond' if bf_rep=='Diamond' else 'visits'}_{rep_from}_{rep_to}.xlsx"
                    with open(path_rep,"rb") as fh:
                        st.download_button(
                            f"📥 تحميل ({period_rep}) — {len(df_rep)} زيارة",
                            data=fh, file_name=fname_rep,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            key="dl_reports_final"
                        )
    st.markdown("---")

    if not visits:
        st.info("لا توجد زيارات في هذا الشهر / الفرع.")
    else:
        t_rev  = sum(v.get("total_price",0) for v in visits if v.get("status")!="ملغية")
        t_done = sum(1 for v in visits if v.get("status")=="تمت")
        t_canc = sum(1 for v in visits if v.get("status")=="ملغية")

        st.markdown(f'''
        <div class="stat-grid">
          <div class="stat-box"><div class="stat-num">{len(visits)}</div><div class="stat-label">إجمالي الزيارات</div></div>
          <div class="stat-box"><div class="stat-num" style="color:#27AE60">{t_done}</div><div class="stat-label">تمت ✅</div></div>
          <div class="stat-box"><div class="stat-num" style="color:#E74C3C">{t_canc}</div><div class="stat-label">ملغية ❌</div></div>
          <div class="stat-box"><div class="stat-num" style="font-size:15px">{t_rev:,.0f}</div><div class="stat-label">الإيراد (جنيه)</div></div>
        </div>''', unsafe_allow_html=True)

        st.markdown("#### 📊 الإيراد اليومي")
        daily = {}
        for v in visits:
            if v.get("status")=="ملغية": continue
            d = v.get("visit_date","")
            daily[d] = daily.get(d,0) + v.get("total_price",0)
        if daily:
            df_daily = pd.DataFrame(sorted(daily.items()), columns=["التاريخ","الإيراد"])
            st.bar_chart(df_daily.set_index("التاريخ"))

        st.markdown("#### 👨‍⚕️ توزيع الزيارات على الأطباء")
        doc_counts = {}
        for v in visits:
            doc = v.get("doctor_name","غير محدد") or "غير محدد"
            doc_counts[doc] = doc_counts.get(doc,0)+1
        if doc_counts:
            df_dc = pd.DataFrame(doc_counts.items(), columns=["الدكتور","عدد الزيارات"])
            st.bar_chart(df_dc.set_index("الدكتور"))

        st.markdown("#### 📋 ملخص تفصيلي")
        summary = {}
        for v in visits:
            doc = v.get("doctor_name","غير محدد") or "غير محدد"
            if doc not in summary:
                summary[doc] = {"count":0,"before":0,"after":0,"transport":0,"total":0,"done":0,"cancelled":0}
            summary[doc]["count"]    += 1
            summary[doc]["before"]   += v.get("labs_price_before",0)
            summary[doc]["after"]    += v.get("labs_price_after",0)
            summary[doc]["transport"]+= v.get("transport_fee",0)
            if v.get("status")!="ملغية": summary[doc]["total"] += v.get("total_price",0)
            if v.get("status")=="تمت":   summary[doc]["done"]  += 1
            if v.get("status")=="ملغية": summary[doc]["cancelled"] += 1

        df = pd.DataFrame(summary).T
        df["الدكتور"] = df.index
        df = df[["الدكتور","count","done","cancelled","before","after","transport","total"]]
        df.columns = ["الدكتور","الزيارات","تمت","ملغية","قبل الخصم","بعد الخصم","الانتقال","الإجمالي"]
        df = df.sort_values("الزيارات",ascending=False)
        tc=df["الزيارات"].sum(); tb=df["قبل الخصم"].sum()
        ta=df["بعد الخصم"].sum(); ttr=df["الانتقال"].sum(); tt=df["الإجمالي"].sum()

        st.markdown(f"**إجمالي:** {tc} زيارة &nbsp;|&nbsp; **الإيراد الكلي:** {tt:,.0f} جنيه")
        st.dataframe(df.style.format({
            "قبل الخصم":"{:,.0f} ج","بعد الخصم":"{:,.0f} ج",
            "الانتقال":"{:,.0f} ج","الإجمالي":"{:,.0f} ج"
        }), use_container_width=True)

        month_name   = MONTHS_AR[month-1]
        branch_title = f" - فرع {branch_filter}" if branch_filter!="الكل" else ""
        report_title = f"تقرير زيارات {month_name} {year}{branch_title}"
        rows_html = ""
        for _,row in df.iterrows():
            rows_html += f"""<tr>
              <td>{row['الدكتور']}</td><td>{row['الزيارات']}</td>
              <td style="color:#27AE60;font-weight:700">{row['تمت']}</td>
              <td style="color:#E74C3C">{row['ملغية']}</td>
              <td>{row['قبل الخصم']:,.0f} ج</td><td>{row['بعد الخصم']:,.0f} ج</td>
              <td>{row['الانتقال']:,.0f} ج</td><td><b>{row['الإجمالي']:,.0f} ج</b></td>
            </tr>"""
        printable_html = f"""
        <div id="printable-report" style="direction:rtl;font-family:'Cairo',sans-serif;padding:20px;background:white;color:black;">
            <h1 style="color:#FF6B00;text-align:center;">Orange Lab — تقرير الزيارات المنزلية</h1>
            <h2 style="text-align:center;">{report_title}</h2>
            <table border="1" cellpadding="8" cellspacing="0" style="width:100%;border-collapse:collapse;margin-top:20px;">
                <thead><tr style="background:#FF6B00;color:white;">
                  <th>الدكتور</th><th>الزيارات</th><th>تمت</th><th>ملغية</th>
                  <th>قبل الخصم</th><th>بعد الخصم</th><th>الانتقال</th><th>الإجمالي</th>
                </tr></thead>
                <tbody>{rows_html}
                <tr style="background:#f5f5f5;font-weight:bold;">
                  <td>الإجمالي الكلي</td><td>{tc}</td>
                  <td style="color:#27AE60">{df['تمت'].sum()}</td>
                  <td style="color:#E74C3C">{df['ملغية'].sum()}</td>
                  <td>{tb:,.0f} ج</td><td>{ta:,.0f} ج</td><td>{ttr:,.0f} ج</td><td>{tt:,.0f} ج</td>
                </tr></tbody>
            </table>
            <p style="text-align:center;margin-top:30px;">تم إنشاؤه بواسطة Orange Lab Home Visit</p>
        </div>"""
        st.components.v1.html(printable_html, height=500, scrolling=True)

        # زر تصدير CSV للأدمن فقط
        if st.session_state.user_type == "admin":
            csv = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("📥 تحميل CSV", data=csv,
                               file_name=f"تقرير_زيارات_{month_name}_{year}.csv", mime="text/csv")

# ══════════════════════════════════════════════════════════════════════════════
# Dashboard (أدمن فقط)
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "dashboard":
    if st.session_state.user_type != "admin":
        st.error("هذه الصفحة للأدمن فقط."); st.stop()

    try:
        import plotly.graph_objects as go_plt
        import plotly.express as px
        HAS_PLOTLY = True
    except ImportError:
        HAS_PLOTLY = False

    st.markdown("## 📊 Dashboard — نظرة عامة")
    all_vs   = fetch_visits()
    today_s  = date.today().isoformat()
    week_ago = (date.today() - timedelta(days=6)).isoformat()

    total_all = len(all_vs)
    rev_all   = sum(v.get("total_price",0) for v in all_vs if v.get("status")!="ملغية")
    done_all  = sum(1 for v in all_vs if v.get("status")=="تمت")
    today_cnt = sum(1 for v in all_vs if v.get("visit_date")==today_s)
    week_vs   = [v for v in all_vs if v.get("visit_date","")>=week_ago]
    week_rev  = sum(v.get("total_price",0) for v in week_vs if v.get("status")!="ملغية")

    st.markdown(f'''
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-num">{total_all}</div><div class="stat-label">إجمالي كل الزيارات</div></div>
      <div class="stat-box"><div class="stat-num" style="color:#27AE60">{done_all}</div><div class="stat-label">تمت بنجاح ✅</div></div>
      <div class="stat-box"><div class="stat-num">{today_cnt}</div><div class="stat-la
