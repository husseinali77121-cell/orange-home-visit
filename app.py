import streamlit as st
import sqlite3
import json
import os
import urllib.parse
from datetime import date, datetime
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
# نظام تسجيل الدخول - فقط الإيميلات المصرح بها في secrets
# ══════════════════════════════════════════════════════════════════════════════
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "user_type" not in st.session_state:
    st.session_state.user_type = None   # admin, diamond

# جلب القوائم من secrets (يجب تعريفها في .streamlit/secrets.toml)
ALLOWED_EMAILS = st.secrets.get("allowed_emails", [])
ADMIN_EMAIL = "Hussein.ali77121@gmail.com"   # الأدمن الثابت (يطلب كلمة مرور)
DIAMOND_EMAIL = "Orangelab511@gmail.com"     # حساب فرع دايموند (ضمن المسموحين)

if not st.session_state.authenticated:
    st.title("🔒 تسجيل الدخول")
    email = st.text_input("📧 أدخل بريدك الإلكتروني للدخول")

    if st.button("دخول"):
        email_clean = email.strip()
        if email_clean not in ALLOWED_EMAILS:
            st.error("هذا البريد غير مصرح له بالدخول. راجع الأدمن.")
        else:
            # إذا كان الأدمن يحتاج كلمة مرور
            if email_clean.lower() == ADMIN_EMAIL.lower():
                # نطلب كلمة المرور في واجهة منفصلة أو ننتقل لحقل كلمة المرور
                # لتبسيط التجربة: يمكننا طلب كلمة المرور قبل الضغط على دخول (كما في النسخة السابقة)
                # لكن هنا نعيد تصميم صغير: نعرض حقل كلمة المرور عند الحاجة
                # سنضيف حقل كلمة المرور في صفحة جديدة صغيرة
                st.session_state.login_email = email_clean
                st.session_state.need_password = True
                st.rerun()
            else:
                # باقي الإيميلات تدخل مباشرة
                st.session_state.authenticated = True
                st.session_state.user_email = email_clean
                # نحدد نوع المستخدم (دايموند إذا كان مطابقًا)
                if email_clean.lower() == DIAMOND_EMAIL.lower():
                    st.session_state.user_type = "diamond"
                else:
                    st.session_state.user_type = "other"
                st.rerun()

    # إذا طلب كلمة المرور للأدمن نعرض حقل الإدخال
    if st.session_state.get("need_password"):
        # إخفاء حقل البريد الأصلي وعرض حقل كلمة المرور
        st.markdown("---")
        st.markdown(f"البريد: **{st.session_state.login_email}**")
        password = st.text_input("🔑 كلمة المرور", type="password")
        if st.button("تأكيد كلمة المرور"):
            correct_password = st.secrets.get("admin_password", "123456")
            if password == correct_password:
                st.success("صلِّ على رسول الله ﷺ - أهلاً بالأدمن")
                st.session_state.authenticated = True
                st.session_state.user_email = st.session_state.login_email
                st.session_state.user_type = "admin"
                st.session_state.need_password = False
                st.rerun()
            else:
                st.error("كلمة مرور خاطئة")
        if st.button("رجوع"):
            st.session_state.need_password = False
            st.rerun()

    # تذييل صفحة الدخول
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
# إخفاء عناصر Streamlit و GitHub
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
# إعداد قاعدة البيانات (بدون عمود الصورة)
# ══════════════════════════════════════════════════════════════════════════════
DB_FILE = "visits.db"
BACKUP_EXCEL = "visits_export.xlsx"

@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def init_db():
    conn = get_connection()
    # إضافة عمود age_unit إذا لم يكن موجوداً (تمت إضافته في التعديل السابق)
    try:
        conn.execute("ALTER TABLE visits ADD COLUMN age_unit TEXT DEFAULT 'سنة'")
    except sqlite3.OperationalError:
        pass

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
            total_price REAL DEFAULT 0
        )
    """)
    conn.commit()

init_db()

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
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]

def fetch_visit_by_id(visit_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM visits WHERE id = ?", (visit_id,)).fetchone()
    return dict(row) if row else None

def insert_visit(record):
    conn = get_connection()
    conn.execute("""
        INSERT INTO visits (
            id, created_at, name, age, age_unit, phone, visit_date, visit_time,
            doctor_name, branch, address, location_link,
            selected_labs_text, notes, labs_price_before,
            labs_price_after, transport_fee, total_price
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        record["id"], record["created_at"], record["name"], record["age"],
        record.get("age_unit", "سنة"),
        record["phone"], record["visit_date"], record["visit_time"],
        record["doctor_name"], record.get("branch", "La Cite"),
        record["address"], record["location_link"],
        record["selected_labs_text"], record["notes"],
        record["labs_price_before"], record["labs_price_after"],
        record["transport_fee"], record["total_price"]
    ))
    conn.commit()

def update_visit(record):
    conn = get_connection()
    conn.execute("""
        UPDATE visits SET
            name = ?, age = ?, age_unit = ?, phone = ?, visit_date = ?, visit_time = ?,
            doctor_name = ?, branch = ?, address = ?, location_link = ?,
            selected_labs_text = ?, notes = ?, labs_price_before = ?,
            labs_price_after = ?, transport_fee = ?, total_price = ?
        WHERE id = ?
    """, (
        record["name"], record["age"], record.get("age_unit", "سنة"),
        record["phone"], record["visit_date"], record["visit_time"],
        record["doctor_name"], record.get("branch", "La Cite"),
        record["address"], record["location_link"], record["selected_labs_text"],
        record["notes"], record["labs_price_before"], record["labs_price_after"],
        record["transport_fee"], record["total_price"],
        record["id"]
    ))
    conn.commit()

def delete_visit(visit_id):
    conn = get_connection()
    conn.execute("DELETE FROM visits WHERE id = ?", (visit_id,))
    conn.commit()

# ══════════════════════════════════════════════════════════════════════════════
# دوال التصدير والاستيراد
# ══════════════════════════════════════════════════════════════════════════════
def export_to_excel():
    visits = fetch_visits()
    df = pd.DataFrame(visits)
    cols = ["id", "created_at", "name", "age", "age_unit", "phone", "visit_date", "visit_time",
            "doctor_name", "branch", "address", "location_link",
            "selected_labs_text", "notes", "labs_price_before",
            "labs_price_after", "transport_fee", "total_price"]
    df = df[cols]
    df.to_excel(BACKUP_EXCEL, index=False, engine="openpyxl")
    return df, BACKUP_EXCEL

def import_from_excel(uploaded_file):
    df = pd.read_excel(uploaded_file, engine="openpyxl")
    required_cols = {"id", "name", "phone", "visit_date", "address"}
    if not required_cols.issubset(df.columns):
        st.error("ملف Excel غير صالح: ينقصه أعمدة أساسية (id, name, phone, visit_date, address)")
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
        if "age" not in record or pd.isna(record["age"]):
            record["age"] = 0
        existing = fetch_visit_by_id(record["id"])
        if existing:
            update_visit(record)
        else:
            insert_visit(record)
        count += 1
    return count

# ══════════════════════════════════════════════════════════════════════════════
# تنسيق CSS وخطوط
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
      .stat-grid { display:flex; gap:10px; margin-bottom:18px; }
      .stat-box { flex:1; background:#fff; border-radius:14px; padding:12px; text-align:center; border:1px solid #ffe8d1; box-shadow:0 2px 10px rgba(0,0,0,0.05); }
      .stat-num { font-size:24px; font-weight:800; color:#FF6B00; }
      .stat-label { font-size:10px; color:#aaa; margin-top:2px; }
      .visit-card { background:#fff; border-radius:14px; padding:14px; margin-bottom:10px; border:1px solid #ffe8d1; box-shadow:0 2px 10px rgba(0,0,0,0.05); }
      .visit-name { font-size:15px; font-weight:700; color:#222; }
      .visit-meta { font-size:12px; color:#888; margin-top:4px; }
      .visit-badge { background:#fff3e6; color:#FF6B00; border-radius:8px; padding:3px 10px; font-size:12px; font-weight:700; float:left; }
      .price-box { background: linear-gradient(135deg, #FF6B00, #FF9A3C); border-radius:16px; padding:16px 20px; color:#fff; margin-bottom:14px; }
      .price-row { display:flex; justify-content:space-between; font-size:14px; margin-bottom:7px; }
      .price-total { display:flex; justify-content:space-between; font-size:19px; font-weight:800; border-top:2px solid rgba(255,255,255,0.3); padding-top:9px; margin-top:5px; }
      .wa-btn { display:block; padding:11px 16px; border-radius:12px; color:#fff !important; font-weight:700; font-size:13px; text-decoration:none; text-align:center; font-family:'Cairo',sans-serif; margin-bottom: 8px; }
      .wa-client { background:#25D366; }
      .wa-share  { background:#128C7E; }
      .wa-group  { background:#075E54; }
      .detail-row { display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #f5f5f5; font-size:13px; }
      .detail-label { color:#888; }
      .detail-value { font-weight:600; color:#222; max-width:58%; text-align:left; }
      .repeat-banner { background:#fff8f0; border:2px dashed #FF9A3C; border-radius:14px; padding:12px; text-align:center; margin-top:12px; color:#FF6B00; font-weight:700; font-size:14px; }
      .section-title { font-size:14px; font-weight:700; color:#FF6B00; border-right:4px solid #FF6B00; padding-right:10px; margin-bottom:10px; }
      div[data-testid="stButton"] button { font-family:'Cairo',sans-serif !important; font-weight:700 !important; border-radius:12px !important; }
      div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label,
      div[data-testid="stDateInput"] label, div[data-testid="stTextArea"] label,
      div[data-testid="stMultiSelect"] label, div[data-testid="stSelectbox"] label {
        font-family:'Cairo',sans-serif !important; font-weight:600 !important; color:#555 !important;
      }
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
# الألواح السريعة
# ══════════════════════════════════════════════════════════════════════════════
QUICK_PANELS = [
    {"name": "🩸 CBC", "tests": ["CBC"]},
    {"name": "🍬 Diabetes", "tests": ["HbA1C", "Urea", "Creatinine (Serum)", "Uric Acid", "ALT (SGPT)", "AST (SGOT)", "Urine Examination"]},
    {"name": "❤️ Cardiac Risk", "tests": ["Cholesterol", "HDL", "LDL", "Triglycerides", "ALT (SGPT)", "AST (SGOT)", "Uric Acid"]},
    {"name": "🦋 Thyroid", "tests": ["TSH", "FT3", "FT4"]},
    {"name": "🔋 Fatigue", "tests": ["CBC", "Ferritin", "Vitamin D3(25 Hydroxy Cholecal.)", "TSH"]},
    {"name": "🧪 Kidney", "tests": ["Urea", "Creatinine (Serum)", "Uric Acid", "Urine Examination"]},
    {"name": "🫀 Liver", "tests": ["ALT (SGPT)", "AST (SGOT)", "Albumin (ALB)", "Bilirubin Total", "Alkaline Phosphatase (ALP)"]},
    {"name": "🌟 General", "tests": ["CBC", "Cholesterol", "HDL", "LDL", "Triglycerides", "HbA1C", "TSH",
                                   "ALT (SGPT)", "AST (SGOT)", "Urea", "Creatinine (Serum)", "Urine Examination"]},
]

# ══════════════════════════════════════════════════════════════════════════════
# استيراد قائمة الأسعار
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
    months = ["يناير","فبراير","مارس","أبريل","مايو","يونيو",
              "يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
    return f"{d.day} {months[d.month-1]} {d.year}"

def make_whatsapp_msg(v, target="internal"):
    labs_price_before = v.get("labs_price_before", 0)
    labs_price_after  = v.get("labs_price_after", 0)
    transport_fee     = v.get("transport_fee", 0)
    total             = v.get("total_price", 0)
    visit_date        = format_date_ar(v.get("visit_date", ""))
    visit_time        = v.get("visit_time", "")
    datetime_str      = f"{visit_date}" + (f" — {visit_time}" if visit_time else "")
    doc_name          = v.get("doctor_name", "غير محدد")
    address           = v.get("address", "")
    location          = v.get("location_link", "")
    branch            = v.get("branch", "")
    client_name       = v.get("name", "")
    age               = v.get("age", "")
    age_unit          = v.get("age_unit", "سنة")
    age_str           = f"🎂 *العمر:* {age} {age_unit}\n" if age else ""

    labs_text = v.get("selected_labs_text", "")
    if labs_text.strip():
        labs_lines = "\n".join(f"🧪 {l.strip()}" for l in labs_text.splitlines() if l.strip()) + "\n"
    else:
        labs_lines = "🚫 لا توجد تحاليل\n"

    loc_line = f"📍 *الموقع:* {location}\n" if location else ""
    branch_line = f"🏥 *الفرع:* {branch}\n" if branch else ""

    if target == "client":
        return (
            f"🟠 *Orange Lab Home Visit*\n"
            f"🏠 أهلاً بك {client_name}\n"
            f"━━━━━━━━━━━━━━\n"
            f"👨‍⚕️ *الدكتور القائم بالزيارة:* {doc_name}\n"
            f"📅 *موعد الزيارة:* {datetime_str}\n"
            f"━━━━━━━━━━━━━━\n"
            f"📍 *عنوان الزيارة:*\n{address}\n"
            f"{loc_line}"
            f"{branch_line}"
            f"━━━━━━━━━━━━━━\n"
            f"🧪 *التحاليل المطلوبة:*\n{labs_lines}"
            f"━━━━━━━━━━━━━━\n"
            f"💰 *السعر قبل الخصم:* {labs_price_before} جنيه\n"
            f"💰 *السعر بعد الخصم:* {labs_price_after} جنيه\n"
            f"🚗 *بدل الانتقال:* {transport_fee} جنيه\n"
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
            f"👨‍⚕️ *الدكتور القائم بالزيارة:* {doc_name}\n"
            f"📅 *الموعد:* {datetime_str}"
        )
    else:   # internal
        notes = f"📝 *ملاحظات:* {v.get('notes','')}\n" if v.get("notes") else ""
        return (
            f"🟠 *Orange Lab Home Visit*\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 *الاسم:* {v['name']}\n"
            f"{age_str}"
            f"📞 *التليفون:* {v.get('phone','')}\n"
            f"📅 *الموعد:* {datetime_str}\n"
            f"👨‍⚕️ *دكتور الزيارة:* {doc_name}\n"
            f"🏥 *الفرع:* {branch}\n"
            f"━━━━━━━━━━━━━━\n"
            f"📍 *العنوان:* {address}\n"
            f"{loc_line}"
            f"━━━━━━━━━━━━━━\n"
            f"🧪 *التحاليل المطلوبة:*\n{labs_lines}"
            f"━━━━━━━━━━━━━━\n"
            f"💰 *السعر قبل الخصم:* {labs_price_before} جنيه\n"
            f"💰 *السعر بعد الخصم:* {labs_price_after} جنيه\n"
            f"🚗 *بدل الانتقال:* {transport_fee} جنيه\n"
            f"💵 *الإجمالي:* {total} جنيه\n"
            f"━━━━━━━━━━━━━━\n"
            f"{notes}"
        )

def whatsapp_link(msg, phone=None):
    encoded = urllib.parse.quote(msg, encoding='utf-8')
    if phone:
        p = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
        if p.startswith("0"):
            p = "20" + p[1:]
        elif not p.startswith("20"):
            p = "20" + p
        return f"https://wa.me/{p}?text={encoded}"
    return f"https://wa.me/?text={encoded}"

# ══════════════════════════════════════════════════════════════════════════════
# إعداد حالة الجلسة
# ══════════════════════════════════════════════════════════════════════════════
for k, v in [("page", "home"), ("prefill", {}), ("selected_id", None), ("search_q", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

def go(page, prefill=None, visit_id=None):
    if page == "new" and (prefill is None or not prefill.get("_edit")):
        st.session_state.pop("added_labs_new_visit", None)
    st.session_state.page = page
    if prefill is not None:
        st.session_state.prefill = prefill
    if visit_id is not None:
        st.session_state.selected_id = visit_id
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

col1, col2, col3, col4, col5 = st.columns([2,2,2,2,1])
with col1:
    if st.button("🏠 الرئيسية", use_container_width=True): go("home")
with col2:
    if st.button("➕ زيارة جديدة", use_container_width=True): go("new", prefill={})
with col3:
    if st.button("🔍 بحث", use_container_width=True): go("search")
with col4:
    if st.button("📊 التقارير", use_container_width=True): go("reports")
with col5:
    if st.button("🚪", help="تسجيل الخروج", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# الصفحات
# ══════════════════════════════════════════════════════════════════════════════

# --- الصفحة الرئيسية ---
if st.session_state.page == "home":
    # السماح بالمشاهدة للأدمن وفرع دايموند فقط (أو أي نوع مصرح)
    # لكن عملياً: الأدمن يرى الكل، والدايموند يرى Diamond فقط
    if st.session_state.user_type not in ["admin", "diamond"]:
        st.info("ليس لديك صلاحية عرض بيانات الزيارات.")
        conn = get_connection()
        all_visits = fetch_visits()
        today = date.today().isoformat()
        t_today = sum(1 for v in all_visits if v.get("visit_date") == today)
        t_rev = sum(v.get("total_price", 0) for v in all_visits)
        st.markdown(f'''
        <div class="stat-grid">
          <div class="stat-box"><div class="stat-num">{len(all_visits)}</div><div class="stat-label">إجمالي الزيارات</div></div>
          <div class="stat-box"><div class="stat-num">{t_today}</div><div class="stat-label">زيارات اليوم</div></div>
          <div class="stat-box"><div class="stat-num" style="font-size:17px">{t_rev:,}</div><div class="stat-label">الإيراد (جنيه)</div></div>
        </div>''', unsafe_allow_html=True)
        st.stop()

    conn = get_connection()
    all_doctors = [row[0] for row in conn.execute("SELECT DISTINCT doctor_name FROM visits WHERE doctor_name != ''").fetchall()]
    all_branches = [row[0] for row in conn.execute("SELECT DISTINCT branch FROM visits").fetchall()]
    if "الكل" not in all_branches:
        all_branches.insert(0, "الكل")
    if "الكل" not in all_doctors:
        all_doctors.insert(0, "الكل")

    st.markdown("### تصفية الزيارات")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        if st.session_state.user_type == "diamond":
            selected_branch = "Diamond"
            st.selectbox("الفرع", options=["Diamond"], disabled=True)
        else:
            selected_branch = st.selectbox("الفرع", options=all_branches, index=0)
    with col_f2:
        selected_doctor = st.selectbox("الدكتور", options=all_doctors, index=0)
    with col_f3:
        search_query = st.text_input("بحث بالاسم أو التليفون", value=st.session_state.search_q, placeholder="ابحث...")
        st.session_state.search_q = search_query

    filters = {}
    if selected_branch != "الكل":
        filters["branch"] = selected_branch
    if selected_doctor != "الكل":
        filters["doctor"] = selected_doctor
    if search_query:
        filters["search"] = search_query

    visits = fetch_visits(filters)
    today = date.today().isoformat()
    if st.session_state.user_type == "diamond":
        all_visits = fetch_visits({"branch": "Diamond"})
    else:
        all_visits = fetch_visits()
    t_today = sum(1 for v in all_visits if v.get("visit_date") == today)
    t_rev = sum(v.get("total_price", 0) for v in all_visits)

    st.markdown(f'''
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-num">{len(all_visits)}</div><div class="stat-label">إجمالي الزيارات</div></div>
      <div class="stat-box"><div class="stat-num">{t_today}</div><div class="stat-label">زيارات اليوم</div></div>
      <div class="stat-box"><div class="stat-num" style="font-size:17px">{t_rev:,}</div><div class="stat-label">الإيراد (جنيه)</div></div>
    </div>''', unsafe_allow_html=True)

    if st.session_state.user_type == "admin":
        col_exp, col_imp = st.columns(2)
        with col_exp:
            if st.button("📤 تصدير إلى Excel", use_container_width=True):
                df, path = export_to_excel()
                with open(path, "rb") as f:
                    st.download_button(
                        label="📥 تحميل الملف",
                        data=f,
                        file_name="visits_export.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        with col_imp:
            uploaded_file = st.file_uploader("📥 استيراد من Excel", type=["xlsx"], key="import_excel")
            if uploaded_file is not None:
                count = import_from_excel(uploaded_file)
                st.success(f"تم استيراد {count} زيارة بنجاح!")
                st.rerun()

    st.markdown("---")

    if not visits:
        st.info("لا توجد زيارات تطابق التصفية.")
    else:
        for v in visits:
            total = v.get("total_price", 0)
            vdate = format_date_ar(v.get("visit_date", ""))
            addr = (v.get("address", "") or "")[:38] + ("..." if len(v.get("address", "") or "") > 38 else "")
            labs_count = len(v.get("selected_labs_text", "").splitlines()) if v.get("selected_labs_text") else 0
            doctor_show = f" | 👨‍⚕️ {v.get('doctor_name','')}" if v.get("doctor_name") else ""
            branch_show = f" | 🏥 {v.get('branch','')}" if v.get("branch") else ""
            age = v.get("age", "")
            age_unit = v.get("age_unit", "سنة")
            age_display = f"🎂 {age} {age_unit}" if age else ""
            st.markdown(f'''
            <div class="visit-card">
              <span class="visit-badge">{total:,} جنيه</span>
              <div class="visit-name">👤 {v["name"]}</div>
              <div class="visit-meta">📞 {v.get("phone","")} &nbsp;|&nbsp; 📅 {vdate} &nbsp; {age_display}</div>
              <div class="visit-meta">📍 {addr}</div>
              <div class="visit-meta" style="margin-top:5px">🧪 {labs_count} تحليل{doctor_show}{branch_show}</div>
            </div>''', unsafe_allow_html=True)
            if st.button(f"📂 فتح {v['name']}", key=f"o_{v['id']}", use_container_width=True):
                go("detail", visit_id=v["id"])

    st.markdown("""
    <div style="text-align:center; margin-top:50px; padding-top:20px; border-top:2px solid #FF6B00; color:#333; font-size:14px; font-weight:600;">
      Developed by <b>Dr / Hussein Ali</b> 2026 For <span style="color:#FF6B00;">Orange Lab 🍊</span>
    </div>
    """, unsafe_allow_html=True)

# --- صفحة زيارة جديدة / تعديل ---
elif st.session_state.page == "new":
    pf = st.session_state.prefill or {}
    is_edit = pf.get("_edit", False)
    st.markdown(f"### {'✏️ تعديل الزيارة' if is_edit else '➕ زيارة جديدة'}")

    st.markdown('<div class="section-title">👤 البيانات الشخصية</div>', unsafe_allow_html=True)
    name = st.text_input("الاسم الكامل *", value=pf.get("name", ""))
    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("العمر *", 0, 120, int(pf.get("age", 0) or 0))
    with c2:
        age_unit_options = ["سنة", "شهر"]
        current_age_unit = pf.get("age_unit", "سنة")
        if current_age_unit not in age_unit_options:
            current_age_unit = "سنة"
        age_unit = st.radio("الوحدة", age_unit_options, index=0 if current_age_unit == "سنة" else 1, horizontal=True)
    with st.columns(1)[0]:
        phone = st.text_input("رقم التليفون *", value=pf.get("phone", ""), placeholder="01xxxxxxxxx")

    doctor_name = st.text_input("👨‍⚕️ الدكتور القائم بالزيارة", value=pf.get("doctor_name", ""))
    branch = st.selectbox("🏥 الفرع", options=["La Cite", "Diamond"],
                          index=0 if pf.get("branch", "La Cite") == "La Cite" else 1)

    d1, d2 = st.columns(2)
    with d1:
        default_date = date.today()
        if pf.get("visit_date"):
            try:
                default_date = datetime.strptime(pf["visit_date"], "%Y-%m-%d").date()
            except:
                pass
        visit_date = st.date_input("📅 تاريخ الزيارة *", value=default_date)
    with d2:
        st.markdown("🕐 وقت الزيارة")
        t_col1, t_col2, t_col3 = st.columns([2,2,3])
        old_time = pf.get("visit_time", "")
        parsed_hour = 12
        parsed_minute = 0
        parsed_ampm = "PM"
        if old_time:
            match = re_module.match(r'(\d{1,2}):(\d{2})\s*(AM|PM)', old_time, re.IGNORECASE)
            if match:
                parsed_hour = int(match.group(1))
                parsed_minute = int(match.group(2))
                parsed_ampm = match.group(3).upper()
        with t_col1:
            hour = st.selectbox("ساعة", list(range(1,13)), index=parsed_hour-1 if 1<=parsed_hour<=12 else 11, key="hour_select")
        with t_col2:
            minute = st.selectbox("دقيقة", [0, 15, 30, 45], index=[0,15,30,45].index(parsed_minute) if parsed_minute in [0,15,30,45] else 0, key="minute_select")
        with t_col3:
            ampm = st.radio("", ["AM", "PM"], index=0 if parsed_ampm == "AM" else 1, horizontal=True, key="ampm_select")
        visit_time = f"{hour}:{minute:02d} {ampm}"
    st.markdown("---")

    st.markdown('<div class="section-title">📍 العنوان</div>', unsafe_allow_html=True)
    address = st.text_area("العنوان بالتفصيل *", value=pf.get("address", ""),
                           placeholder="المحافظة - المدينة - الشارع - رقم المبنى - الدور - الشقة...", height=90)
    location_link = st.text_input("🗺️ رابط الموقع (Google Maps)", value=pf.get("location_link", ""))
    st.markdown("---")

    # تم إلغاء خانة الصورة

    visit_id_key = pf.get("id", "new_visit")
    labs_ss_key = f"added_labs_{visit_id_key}"

    if labs_ss_key not in st.session_state:
        if pf.get("selected_labs_text", ""):
            st.session_state[labs_ss_key] = [l.strip() for l in pf["selected_labs_text"].splitlines() if l.strip()]
        else:
            st.session_state[labs_ss_key] = []

    # Quick Panels
    st.markdown('<div class="section-title">⚡ Quick Panels</div>', unsafe_allow_html=True)
    st.caption("اضغط على panel لإضافة تحاليله فوراً — التحاليل المكررة لن تُضاف مجدداً")
    cols = st.columns(4)
    for i, panel in enumerate(QUICK_PANELS):
        with cols[i % 4]:
            if st.button(panel["name"], key=f"panel_{visit_id_key}_{i}", use_container_width=True):
                for test_name in panel["tests"]:
                    existing_names = [e.split(" — ")[0].strip() for e in st.session_state[labs_ss_key]]
                    if test_name not in existing_names:
                        st.session_state[labs_ss_key].append(test_name)
                st.rerun()

    with st.expander("👁️ شاهد محتوى الـ Panels"):
        for panel in QUICK_PANELS:
            tests_str = " • ".join(panel["tests"])
            st.markdown(f'<div style="font-size:12px;margin-bottom:6px"><b style="color:#FF6B00">{panel["name"]}</b> — {tests_str}</div>', unsafe_allow_html=True)

    st.markdown("---")

    if ALL_LABS:
        st.markdown('<div class="section-title">📋 إضافة تحليل من قائمة الأسعار</div>', unsafe_allow_html=True)
        lab_options = [f"{lab['name']} — {lab['price']} جنيه" for lab in ALL_LABS]
        selected_lab_price = st.selectbox("اختر التحليل", options=lab_options, key=f"lab_price_select_{visit_id_key}")
        if st.button("➕ أضف من القائمة", key=f"add_lab_price_{visit_id_key}", use_container_width=True):
            if selected_lab_price not in st.session_state[labs_ss_key]:
                st.session_state[labs_ss_key].append(selected_lab_price)
            st.rerun()
    else:
        st.warning("قائمة الأسعار غير متاحة حالياً")

    st.markdown("---")

    st.markdown('<div class="section-title">🧪 التحاليل المضافة</div>', unsafe_allow_html=True)
    if st.session_state[labs_ss_key]:
        auto_total = sum(int(m.group(1)) for e in st.session_state[labs_ss_key] for m in [re_module.search(r'(\d+)\s*جنيه', e)] if m)
        st.markdown(f'<div style="font-size:12px;color:#FF6B00;font-weight:700;margin-bottom:8px">✅ {len(st.session_state[labs_ss_key])} تحليل{"  —  إجمالي: " + f"{auto_total:,} جنيه" if auto_total else ""}</div>', unsafe_allow_html=True)
        to_remove = None
        for i, entry in enumerate(st.session_state[labs_ss_key]):
            ca, cb = st.columns([10, 1])
            with ca:
                st.markdown(f'<div style="font-size:13px;padding:4px 0;border-bottom:1px solid #f5f5f5;color:#333">🔹 {entry}</div>', unsafe_allow_html=True)
            with cb:
                if st.button("✕", key=f"del_{visit_id_key}_{i}", help="احذف"):
                    to_remove = i
        if to_remove is not None:
            st.session_state[labs_ss_key].pop(to_remove)
            st.rerun()
        if st.button("🗑️ مسح الكل", key=f"clear_{visit_id_key}"):
            st.session_state[labs_ss_key] = []
            st.rerun()
    else:
        st.markdown('<div style="color:#aaa;font-size:13px;padding:8px 0">لا توجد تحاليل — اختر panel من فوق أو أضف يدوياً</div>', unsafe_allow_html=True)

    col_m1, col_m2 = st.columns([8, 2])
    with col_m1:
        manual_entry = st.text_input("أضف تحليل يدوياً", placeholder="CBC — 400 جنيه", key=f"manual_{visit_id_key}")
    with col_m2:
        st.markdown('<div style="margin-top:28px"></div>', unsafe_allow_html=True)
        if st.button("➕ أضف", key=f"manual_btn_{visit_id_key}", use_container_width=True):
            if manual_entry.strip():
                st.session_state[labs_ss_key].append(manual_entry.strip())
                st.rerun()

    selected_labs_text = "\n".join(st.session_state[labs_ss_key])
    selected_labs = st.session_state[labs_ss_key][:]
    st.markdown("---")

    st.markdown('<div class="section-title">📌 ملاحظات</div>', unsafe_allow_html=True)
    notes = st.text_area("ملاحظات خاصة", value=pf.get("notes", ""), height=75)
    st.markdown("---")

    st.markdown('<div class="section-title">💰 الأسعار</div>', unsafe_allow_html=True)
    auto_labs_total = sum(int(m.group(1)) for e in selected_labs for m in [re_module.search(r'(\d+)\s*جنيه', e)] if m)

    p1, p2, p3 = st.columns(3)
    with p1:
        labs_price_before = st.number_input("⭐ السعر قبل الخصم", min_value=0, step=10,
                                            value=auto_labs_total if auto_labs_total > 0 else int(pf.get("labs_price_before", 0) or 0))
    with p2:
        labs_price_after = st.number_input("⭐ السعر بعد الخصم", min_value=0, step=10,
                                           value=int(pf.get("labs_price_after", 0) or 0))
    with p3:
        transport_fee = st.number_input("⭐ بدل الانتقال", min_value=0, step=10,
                                        value=int(pf.get("transport_fee", 100) or 100))
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
                "id": pf.get("id", str(int(datetime.now().timestamp() * 1000))),
                "created_at": pf.get("created_at", datetime.now().isoformat()),
                "name": name,
                "age": age,
                "age_unit": age_unit,
                "phone": phone,
                "visit_date": visit_date.isoformat(),
                "visit_time": visit_time,
                "doctor_name": doctor_name,
                "branch": branch,
                "address": address,
                "location_link": location_link,
                "selected_labs_text": selected_labs_text,
                "notes": notes,
                "labs_price_before": labs_price_before,
                "labs_price_after": labs_price_after,
                "transport_fee": transport_fee,
                "total_price": total_price
            }
            if is_edit:
                update_visit(record)
                st.success("✅ تم تحديث الزيارة!")
            else:
                insert_visit(record)
                st.success("✅ تم حفظ الزيارة!")
            go("detail", visit_id=record["id"])

    if is_edit:
        if st.button("← رجوع بدون حفظ", use_container_width=True):
            go("detail", visit_id=pf.get("id"))

# --- صفحة التفاصيل ---
elif st.session_state.page == "detail":
    vid = st.session_state.selected_id
    v = fetch_visit_by_id(vid) if vid else None
    if not v:
        st.error("لم يتم العثور على الزيارة")
        go("home")
    else:
        labs_price_before = v.get("labs_price_before", 0)
        labs_price_after  = v.get("labs_price_after", 0)
        transport_fee     = v.get("transport_fee", 0)
        total_price       = v.get("total_price", 0)
        visit_time        = v.get("visit_time", "")
        datetime_display  = format_date_ar(v.get("visit_date", "")) + (f" — {visit_time}" if visit_time else "")
        age               = v.get("age", "")
        age_unit          = v.get("age_unit", "سنة")
        age_str           = f"🎂 {age} {age_unit}" if age else "🎂 غير محدد"

        st.markdown('<div class="section-title">👤 البيانات الشخصية</div>', unsafe_allow_html=True)
        st.markdown(f'''
        <div class="detail-row"><span class="detail-label">👤 الاسم</span><span class="detail-value">{v["name"]}</span></div>
        <div class="detail-row"><span class="detail-label">🎂 السن</span><span class="detail-value">{age_str}</span></div>
        <div class="detail-row"><span class="detail-label">📞 التليفون</span><span class="detail-value">{v.get("phone","")}</span></div>
        <div class="detail-row"><span class="detail-label">📅 الموعد</span><span class="detail-value">{datetime_display}</span></div>
        <div class="detail-row"><span class="detail-label">👨‍⚕️ الدكتور</span><span class="detail-value">{v.get("doctor_name","")}</span></div>
        <div class="detail-row"><span class="detail-label">🏥 الفرع</span><span class="detail-value">{v.get("branch","")}</span></div>
        ''', unsafe_allow_html=True)
        st.markdown("---")

        st.markdown('<div class="section-title">📍 العنوان</div>', unsafe_allow_html=True)
        st.write(v.get("address", ""))
        if v.get("location_link"):
            st.markdown(f'<a href="{v["location_link"]}" target="_blank" style="color:#FF6B00;font-weight:700;">🗺️ فتح الموقع على الخريطة</a>', unsafe_allow_html=True)
        st.markdown("---")

        labs_text = v.get("selected_labs_text", "")
        if labs_text.strip():
            st.markdown('<div class="section-title">🧪 التحاليل المطلوبة</div>', unsafe_allow_html=True)
            lines_html = "".join(f'<div class="detail-row"><span class="detail-label">🔹 {l.strip()}</span></div>' for l in labs_text.splitlines() if l.strip())
            st.markdown(f'<div style="background:#fffaf6;border-radius:12px;padding:8px 14px;border:1px solid #ffe8d1">{lines_html}</div>', unsafe_allow_html=True)
            st.markdown("---")

        st.markdown(f'''
        <div class="price-box">
          <div class="price-row"><span>⭐ السعر قبل الخصم</span><span>{labs_price_before} جنيه</span></div>
          <div class="price-row"><span>⭐ السعر بعد الخصم</span><span>{labs_price_after} جنيه</span></div>
          <div class="price-row"><span>⭐ بدل الانتقال</span><span>{transport_fee} جنيه</span></div>
          <div class="price-total"><span>⭐ الإجمالي</span><span>{total_price} جنيه</span></div>
        </div>''', unsafe_allow_html=True)

        if v.get("notes"):
            st.markdown('<div class="section-title">📌 ملاحظات</div>', unsafe_allow_html=True)
            st.write(v["notes"])
            st.markdown("---")

        st.markdown('<div class="section-title">📱 إرسال على واتساب</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<a href="{whatsapp_link(make_whatsapp_msg(v, "client"), v.get("phone"))}" target="_blank" class="wa-btn wa-client">📱 واتساب العميل</a>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<a href="{whatsapp_link(make_whatsapp_msg(v, "group"))}" target="_blank" class="wa-btn wa-group">👥 جروب العمل</a>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<a href="{whatsapp_link(make_whatsapp_msg(v, "internal"))}" target="_blank" class="wa-btn wa-share">📋 ملخص الزيارة</a>', unsafe_allow_html=True)
        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✏️ تعديل", use_container_width=True):
                go("new", prefill={**v, "_edit": True})
        with c2:
            if st.button("🗑️ حذف", use_container_width=True):
                st.session_state["confirm_delete"] = True

        if st.session_state.get("confirm_delete"):
            st.warning("⚠️ هل أنت متأكد من الحذف؟")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("✅ نعم، احذف", use_container_width=True):
                    delete_visit(vid)
                    st.session_state["confirm_delete"] = False
                    go("home")
            with cc2:
                if st.button("❌ إلغاء", use_container_width=True):
                    st.session_state["confirm_delete"] = False
                    st.rerun()

        st.markdown(f'<div class="repeat-banner">🔄 هتروح لـ {v["name"]} مرة تانية؟</div>', unsafe_allow_html=True)
        if st.button(f"➕ زيارة جديدة لـ {v['name']}", use_container_width=True):
            go("new", prefill={
                "name": v["name"], "age": v.get("age", ""), "age_unit": v.get("age_unit", "سنة"),
                "phone": v.get("phone", ""),
                "address": v.get("address", ""), "location_link": v.get("location_link", ""),
                "doctor_name": v.get("doctor_name", ""), "branch": v.get("branch", "La Cite"),
                "selected_labs": [], "selected_labs_text": "", "visit_time": "",
                "notes": "", "labs_price_before": 0, "labs_price_after": 0, "transport_fee": 100
            })
        if st.button("← رجوع للقائمة", use_container_width=True):
            go("home")

# --- صفحة البحث ---
elif st.session_state.page == "search":
    if st.session_state.user_type not in ["admin", "diamond"]:
        st.error("غير مصرح لك بالبحث.")
        st.stop()
    st.markdown("### 🔍 البحث عن عميل")
    query = st.text_input("اكتب الاسم أو التليفون", placeholder="مثال: محمد أو 01012345678")
    if query:
        if st.session_state.user_type == "diamond":
            visits = fetch_visits({"search": query, "branch": "Diamond"})
        else:
            visits = fetch_visits({"search": query})
        st.markdown(f"**{len(visits)} نتيجة**")
        for v in visits:
            total = v.get("total_price", 0)
            vdate = format_date_ar(v.get("visit_date", ""))
            age = v.get("age", "")
            age_unit = v.get("age_unit", "سنة")
            age_display = f"🎂 {age} {age_unit}" if age else ""
            st.markdown(f'''
            <div class="visit-card">
              <span class="visit-badge">{total:,} جنيه</span>
              <div class="visit-name">👤 {v["name"]}</div>
              <div class="visit-meta">📞 {v.get("phone","")} &nbsp;|&nbsp; 📅 {vdate} &nbsp; {age_display}</div>
            </div>''', unsafe_allow_html=True)
            if st.button(f"📂 فتح {v['name']}", key=f"s_{v['id']}", use_container_width=True):
                go("detail", visit_id=v["id"])

# --- صفحة التقارير ---
elif st.session_state.page == "reports":
    if st.session_state.user_type not in ["admin", "diamond"]:
        st.error("غير مصرح لك بعرض التقارير.")
        st.stop()
    st.markdown("### 📊 تقارير نهاية الشهر")
    col_y, col_m, col_b = st.columns(3)
    with col_y:
        year = st.selectbox("السنة", options=list(range(2023, 2031)), index=3)
    with col_m:
        month = st.selectbox("الشهر", options=list(range(1, 13)),
                             format_func=lambda m: ["يناير","فبراير","مارس","أبريل","مايو","يونيو",
                                                     "يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"][m-1],
                             index=date.today().month - 1)
    with col_b:
        if st.session_state.user_type == "diamond":
            branch_filter = "Diamond"
            st.selectbox("الفرع", options=["Diamond"], disabled=True)
        else:
            branch_filter = st.selectbox("الفرع", options=["الكل", "La Cite", "Diamond"])

    filters = {"year": year, "month": month}
    if branch_filter != "الكل":
        filters["branch"] = branch_filter

    visits = fetch_visits(filters)

    if not visits:
        st.info("لا توجد زيارات في هذا الشهر / الفرع.")
    else:
        summary = {}
        for v in visits:
            doc = v.get("doctor_name", "غير محدد")
            if doc not in summary:
                summary[doc] = {"count": 0, "before": 0, "after": 0, "transport": 0, "total": 0}
            summary[doc]["count"] += 1
            summary[doc]["before"] += v.get("labs_price_before", 0)
            summary[doc]["after"] += v.get("labs_price_after", 0)
            summary[doc]["transport"] += v.get("transport_fee", 0)
            summary[doc]["total"] += v.get("total_price", 0)

        df = pd.DataFrame(summary).T
        df["الطبيب"] = df.index
        df = df[["الطبيب", "count", "before", "after", "transport", "total"]]
        df.columns = ["الدكتور", "عدد الزيارات", "قبل الخصم", "بعد الخصم", "الانتقال", "الإجمالي"]
        df = df.sort_values("عدد الزيارات", ascending=False)

        total_count = df["عدد الزيارات"].sum()
        total_before = df["قبل الخصم"].sum()
        total_after = df["بعد الخصم"].sum()
        total_transport = df["الانتقال"].sum()
        total_total = df["الإجمالي"].sum()

        st.markdown("---")
        st.markdown(f"**إجمالي عدد الزيارات:** {total_count}  |  **الإجمالي العام:** {total_total:,} جنيه")
        st.dataframe(df.style.format({
            "قبل الخصم": "{:,} جنيه",
            "بعد الخصم": "{:,} جنيه",
            "الانتقال": "{:,} جنيه",
            "الإجمالي": "{:,} جنيه"
        }), use_container_width=True)

        st.markdown("---")
        month_name = ["يناير","فبراير","مارس","أبريل","مايو","يونيو",
                      "يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"][month-1]
        branch_title = f" - فرع {branch_filter}" if branch_filter != "الكل" else ""
        report_title = f"تقرير زيارات {month_name} {year}{branch_title}"

        printable_html = f"""
        <div id="printable-report" style="direction: rtl; font-family: 'Cairo', sans-serif; padding: 20px; background: white; color: black;">
            <h1 style="color:#FF6B00; text-align:center;">Orange Lab - تقرير الزيارات المنزلية</h1>
            <h2 style="text-align:center;">{report_title}</h2>
            <table border="1" cellpadding="8" cellspacing="0" style="width:100%; border-collapse:collapse; margin-top:20px;">
                <thead>
                    <tr style="background:#FF6B00; color:white;">
                        <th>الدكتور</th><th>عدد الزيارات</th><th>قبل الخصم</th><th>بعد الخصم</th><th>الانتقال</th><th>الإجمالي</th>
                    </tr>
                </thead>
                <tbody>
        """
        for _, row in df.iterrows():
            printable_html += f"""
                <tr>
                    <td>{row['الدكتور']}</td>
                    <td>{row['عدد الزيارات']}</td>
                    <td>{row['قبل الخصم']:,} ج</td>
                    <td>{row['بعد الخصم']:,} ج</td>
                    <td>{row['الانتقال']:,} ج</td>
                    <td><b>{row['الإجمالي']:,} ج</b></td>
                </tr>
            """
        printable_html += f"""
                <tr style="background:#f5f5f5; font-weight:bold;">
                    <td>الإجمالي الكلي</td>
                    <td>{total_count}</td>
                    <td>{total_before:,} ج</td>
                    <td>{total_after:,} ج</td>
                    <td>{total_transport:,} ج</td>
                    <td>{total_total:,} ج</td>
                </tr>
                </tbody>
            </table>
            <p style="text-align:center; margin-top:30px;">تم إنشاؤه بواسطة تطبيق Orange Lab Home Visit</p>
        </div>
        """
        st.components.v1.html(printable_html, height=600, scrolling=True)

        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 تحميل التقرير CSV",
            data=csv,
            file_name=f"تقرير_زيارات_{month_name}_{year}.csv",
            mime="text/csv",
    )
