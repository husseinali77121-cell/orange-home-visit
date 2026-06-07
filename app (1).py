import streamlit as st
import json
import os
import urllib.parse
from datetime import date, datetime

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Orange Home Visit",
    page_icon="🟠",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── Constants ─────────────────────────────────────────────────────────────────
DATA_FILE = "visits.json"
VISIT_PRICE = 100

LABS = [
    {"name": "CBC - صورة دم كاملة",        "price": 50},
    {"name": "Blood Sugar - سكر صائم",      "price": 30},
    {"name": "HbA1c - سكر تراكمي",          "price": 120},
    {"name": "Lipid Profile - دهون",        "price": 150},
    {"name": "Liver Function - وظائف كبد", "price": 180},
    {"name": "Kidney Function - وظائف كلى","price": 180},
    {"name": "Thyroid TSH - هرمون غدة",    "price": 100},
    {"name": "Vitamin D",                   "price": 200},
    {"name": "Vitamin B12",                 "price": 150},
    {"name": "Urine Analysis - تحليل بول", "price": 40},
    {"name": "CRP - بروتين التهابي",        "price": 80},
    {"name": "PT/INR - تجلط",               "price": 100},
    {"name": "Ferritin - حديد",             "price": 120},
    {"name": "Calcium - كالسيوم",           "price": 60},
    {"name": "COVID PCR",                   "price": 350},
]

# ─── CSS ───────────────────────────────────────────────────────────────────────
st.markdown("""
<link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
<style>
  html, body, [class*="css"] {
    font-family: 'Cairo', sans-serif !important;
    direction: rtl;
  }
  .main { background: #fff8f0; }
  .block-container { padding-top: 1rem !important; max-width: 680px; }

  /* Header */
  .ohv-header {
    background: linear-gradient(90deg, #FF6B00, #FF9A3C);
    border-radius: 16px;
    padding: 18px 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
    box-shadow: 0 4px 20px rgba(255,107,0,0.3);
  }
  .ohv-header h1 { color:#fff; margin:0; font-size:22px; font-weight:800; }
  .ohv-header span { color:rgba(255,255,255,0.85); font-size:13px; }

  /* Cards */
  .ohv-card {
    background: #fff;
    border-radius: 16px;
    padding: 18px 20px;
    margin-bottom: 16px;
    border: 1px solid #ffe8d1;
    box-shadow: 0 2px 14px rgba(0,0,0,0.06);
  }
  .ohv-section-title {
    font-size: 15px; font-weight: 700;
    color: #FF6B00; margin-bottom: 12px;
    border-right: 4px solid #FF6B00;
    padding-right: 10px;
  }

  /* Stats */
  .stat-grid { display:flex; gap:12px; margin-bottom:20px; }
  .stat-box {
    flex:1; background:#fff; border-radius:14px;
    padding:14px; text-align:center;
    border:1px solid #ffe8d1;
    box-shadow:0 2px 10px rgba(0,0,0,0.05);
  }
  .stat-num { font-size:26px; font-weight:800; color:#FF6B00; }
  .stat-label { font-size:11px; color:#aaa; margin-top:2px; }

  /* Visit Cards in list */
  .visit-card {
    background:#fff; border-radius:14px;
    padding:16px; margin-bottom:12px;
    border:1px solid #ffe8d1;
    box-shadow:0 2px 12px rgba(0,0,0,0.06);
    cursor:pointer; transition:all 0.2s;
  }
  .visit-card:hover { box-shadow:0 6px 20px rgba(255,107,0,0.15); }
  .visit-name { font-size:16px; font-weight:700; color:#222; }
  .visit-meta { font-size:13px; color:#888; margin-top:4px; }
  .visit-badge {
    background:#fff3e6; color:#FF6B00;
    border-radius:8px; padding:4px 10px;
    font-size:13px; font-weight:700;
    float:left;
  }

  /* Price box */
  .price-box {
    background: linear-gradient(135deg, #FF6B00, #FF9A3C);
    border-radius:16px; padding:18px 20px;
    color:#fff; margin-bottom:16px;
  }
  .price-row {
    display:flex; justify-content:space-between;
    font-size:15px; margin-bottom:8px;
  }
  .price-total {
    display:flex; justify-content:space-between;
    font-size:20px; font-weight:800;
    border-top:2px solid rgba(255,255,255,0.3);
    padding-top:10px; margin-top:6px;
  }

  /* WhatsApp buttons */
  .wa-btn {
    display:inline-block; padding:12px 20px;
    border-radius:12px; color:#fff !important;
    font-weight:700; font-size:14px;
    text-decoration:none; text-align:center;
    font-family:'Cairo',sans-serif;
    transition:all 0.2s;
  }
  .wa-client { background:#25D366; box-shadow:0 4px 12px rgba(37,211,102,0.3); }
  .wa-share  { background:#128C7E; }

  /* Detail rows */
  .detail-row {
    display:flex; justify-content:space-between;
    padding:9px 0; border-bottom:1px solid #f5f5f5;
    font-size:14px;
  }
  .detail-label { color:#888; }
  .detail-value { font-weight:600; color:#222; max-width:58%; text-align:left; }

  /* Lab badge */
  .lab-badge {
    display:inline-block; margin:3px;
    background:#fff3e6; color:#FF6B00;
    border-radius:8px; padding:4px 10px;
    font-size:12px; font-weight:600;
    border:1px solid #ffd4a8;
  }

  /* Repeat visit banner */
  .repeat-banner {
    background:#fff8f0;
    border:2px dashed #FF9A3C;
    border-radius:14px; padding:14px;
    text-align:center; margin-top:14px;
    color:#FF6B00; font-weight:700;
  }

  /* Streamlit overrides */
  div[data-testid="stButton"] button {
    font-family:'Cairo',sans-serif !important;
    font-weight:700 !important;
    border-radius:12px !important;
    width:100%;
  }
  div[data-testid="stSelectbox"] label,
  div[data-testid="stTextInput"] label,
  div[data-testid="stNumberInput"] label,
  div[data-testid="stDateInput"] label,
  div[data-testid="stTextArea"] label,
  div[data-testid="stMultiSelect"] label {
    font-family:'Cairo',sans-serif !important;
    font-weight:600 !important;
    color:#555 !important;
  }
  .stAlert { border-radius:12px !important; }
  div[data-testid="stCheckbox"] label { font-family:'Cairo',sans-serif !important; }
</style>
""", unsafe_allow_html=True)

# ─── Data helpers ───────────────────────────────────────────────────────────────
def load_visits():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_visits(visits):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(visits, f, ensure_ascii=False, indent=2)

def calc_labs_total(selected_labs):
    total = 0
    for lab_name in selected_labs:
        for lab in LABS:
            if lab["name"] == lab_name:
                total += lab["price"]
    return total

def calc_total(selected_labs):
    return calc_labs_total(selected_labs) + VISIT_PRICE

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

def make_whatsapp_msg(v, for_client=False):
    labs_total = calc_labs_total(v.get("selected_labs", []))
    total      = calc_total(v.get("selected_labs", []))
    labs_list  = ""
    for l in v.get("selected_labs", []):
        for lab in LABS:
            if lab["name"] == l:
                labs_list += f"• {l} - {lab['price']} جنيه\n"
    if not labs_list:
        labs_list = "لا توجد تحاليل\n"

    visit_date = format_date_ar(v.get("visit_date", ""))

    if for_client:
        msg = (
            f"🟠 *Orange Home Visit*\n"
            f"أهلاً {v['name']} 👋\n"
            f"━━━━━━━━━━━━━━\n"
            f"📅 *موعد الزيارة:* {visit_date}\n"
            f"🧪 *التحاليل المطلوبة:*\n{labs_list}"
            f"━━━━━━━━━━━━━━\n"
            f"💰 *الإجمالي:* {total} جنيه\n"
            f"شكراً لثقتكم 🙏"
        )
    else:
        location_line = f"🗺️ *الموقع:* {v.get('location_link','')}\n" if v.get("location_link") else ""
        notes_line    = f"📌 *ملاحظات:* {v.get('notes','')}\n" if v.get("notes") else ""
        custom_line   = f"📝 *تحاليل إضافية:*\n{v.get('custom_labs','')}\n" if v.get("custom_labs") else ""
        msg = (
            f"🟠 *Orange Home Visit*\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 *الاسم:* {v['name']}\n"
            f"🎂 *السن:* {v.get('age','')} سنة\n"
            f"📞 *التليفون:* {v.get('phone','')}\n"
            f"📅 *تاريخ الزيارة:* {visit_date}\n"
            f"📍 *العنوان:* {v.get('address','')}\n"
            f"{location_line}"
            f"━━━━━━━━━━━━━━\n"
            f"🧪 *التحاليل المطلوبة:*\n{labs_list}"
            f"{custom_line}"
            f"━━━━━━━━━━━━━━\n"
            f"💉 *سعر التحاليل:* {labs_total} جنيه\n"
            f"🚗 *سعر الزيارة:* {VISIT_PRICE} جنيه\n"
            f"💰 *الإجمالي:* {total} جنيه\n"
            f"━━━━━━━━━━━━━━\n"
            f"{notes_line}"
        )
    return msg

def whatsapp_link(msg, phone=None):
    encoded = urllib.parse.quote(msg)
    if phone:
        p = phone.replace(" ", "").replace("-", "")
        if p.startswith("0"):
            p = "2" + p
        return f"https://wa.me/{p}?text={encoded}"
    return f"https://wa.me/?text={encoded}"

# ─── Session State ──────────────────────────────────────────────────────────────
if "page" not in st.session_state:
    st.session_state.page = "home"
if "visits" not in st.session_state:
    st.session_state.visits = load_visits()
if "selected_id" not in st.session_state:
    st.session_state.selected_id = None
if "prefill" not in st.session_state:
    st.session_state.prefill = {}
if "search_q" not in st.session_state:
    st.session_state.search_q = ""

def go(page, prefill=None, visit_id=None):
    st.session_state.page = page
    if prefill is not None:
        st.session_state.prefill = prefill
    if visit_id is not None:
        st.session_state.selected_id = visit_id
    st.rerun()

def refresh_visits():
    st.session_state.visits = load_visits()

# ─── Header ────────────────────────────────────────────────────────────────────
today_str = format_date_ar(date.today())
st.markdown(f"""
<div class="ohv-header">
  <h1>🟠 Orange Home Visit</h1>
  <span>📅 {today_str}</span>
</div>
""", unsafe_allow_html=True)

# ─── Navigation ────────────────────────────────────────────────────────────────
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("🏠 الرئيسية", use_container_width=True):
        go("home")
with col2:
    if st.button("➕ زيارة جديدة", use_container_width=True):
        go("new", prefill={})
with col3:
    if st.button("🔍 بحث", use_container_width=True):
        go("search")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: HOME
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "home":
    visits = st.session_state.visits
    today  = date.today().isoformat()

    total_visits   = len(visits)
    today_visits   = sum(1 for v in visits if v.get("visit_date") == today)
    total_revenue  = sum(calc_total(v.get("selected_labs", [])) for v in visits)

    st.markdown(f"""
    <div class="stat-grid">
      <div class="stat-box">
        <div class="stat-num">{total_visits}</div>
        <div class="stat-label">إجمالي الزيارات</div>
      </div>
      <div class="stat-box">
        <div class="stat-num">{today_visits}</div>
        <div class="stat-label">زيارات اليوم</div>
      </div>
      <div class="stat-box">
        <div class="stat-num" style="font-size:18px">{total_revenue:,}</div>
        <div class="stat-label">إجمالي الإيراد (جنيه)</div>
      </div>
    </div>
    """, unsafe_allow_html=True)

    # Search bar
    search_q = st.text_input("🔍 ابحث بالاسم أو رقم التليفون", value=st.session_state.search_q,
                              placeholder="اكتب هنا...")
    st.session_state.search_q = search_q

    filtered = [v for v in visits if
                search_q.lower() in v.get("name","").lower() or
                search_q in v.get("phone","")]

    if not filtered:
        st.info("لا توجد زيارات. اضغط ➕ زيارة جديدة للبدء.")
    else:
        for v in filtered:
            total = calc_total(v.get("selected_labs", []))
            labs_count = len(v.get("selected_labs", []))
            vdate = format_date_ar(v.get("visit_date", ""))
            addr  = v.get("address","")
            addr_short = addr[:40] + "..." if len(addr) > 40 else addr

            st.markdown(f"""
            <div class="visit-card">
              <span class="visit-badge">{total:,} جنيه</span>
              <div class="visit-name">👤 {v['name']}</div>
              <div class="visit-meta">📞 {v.get('phone','')} &nbsp;|&nbsp; 📅 {vdate}</div>
              <div class="visit-meta">📍 {addr_short}</div>
              <div class="visit-meta" style="margin-top:6px">🧪 {labs_count} تحليل</div>
            </div>
            """, unsafe_allow_html=True)

            if st.button(f"📂 فتح تفاصيل {v['name']}", key=f"open_{v['id']}",
                         use_container_width=True):
                go("detail", visit_id=v["id"])

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: NEW VISIT
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "new":
    pf = st.session_state.prefill or {}
    is_edit = pf.get("_edit", False)

    st.markdown(f"### {'✏️ تعديل الزيارة' if is_edit else '➕ زيارة جديدة'}")

    # ── Personal Info ──
    st.markdown('<div class="ohv-card"><div class="ohv-section-title">👤 البيانات الشخصية</div>', unsafe_allow_html=True)
    name  = st.text_input("الاسم الكامل *", value=pf.get("name",""), placeholder="اسم العميل")
    c1,c2 = st.columns(2)
    with c1:
        age = st.number_input("السن *", min_value=0, max_value=120, value=int(pf.get("age",0) or 0))
    with c2:
        phone = st.text_input("رقم التليفون *", value=pf.get("phone",""), placeholder="01xxxxxxxxx")

    default_date = date.today()
    if pf.get("visit_date"):
        try:
            default_date = datetime.strptime(pf["visit_date"], "%Y-%m-%d").date()
        except:
            pass
    visit_date = st.date_input("تاريخ الزيارة *", value=default_date)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Address ──
    st.markdown('<div class="ohv-card"><div class="ohv-section-title">📍 العنوان</div>', unsafe_allow_html=True)
    address = st.text_area("العنوان بالتفصيل *",
                            value=pf.get("address",""),
                            placeholder="المحافظة - المدينة - الشارع - رقم المبنى - الدور - الشقة...",
                            height=100)
    location_link = st.text_input("🗺️ رابط الموقع (Google Maps)",
                                   value=pf.get("location_link",""),
                                   placeholder="https://maps.google.com/...")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Labs ──
    st.markdown('<div class="ohv-card"><div class="ohv-section-title">🧪 التحاليل المطلوبة</div>', unsafe_allow_html=True)
    lab_names = [l["name"] for l in LABS]
    default_labs = pf.get("selected_labs", [])
    selected_labs = st.multiselect("اختر التحاليل", options=lab_names, default=default_labs)

    # Show prices inline
    if selected_labs:
        badges = " ".join([f'<span class="lab-badge">{l.split(" - ")[0]} — {next(x["price"] for x in LABS if x["name"]==l)} جنيه</span>' for l in selected_labs])
        st.markdown(badges, unsafe_allow_html=True)

    custom_labs = st.text_area("تحاليل إضافية (اكتبها هنا)",
                                value=pf.get("custom_labs",""),
                                placeholder="أي تحاليل غير موجودة في القائمة...",
                                height=70)
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Notes ──
    st.markdown('<div class="ohv-card"><div class="ohv-section-title">📌 ملاحظات</div>', unsafe_allow_html=True)
    notes = st.text_area("ملاحظات خاصة", value=pf.get("notes",""), height=80, placeholder="أي ملاحظات...")
    st.markdown('</div>', unsafe_allow_html=True)

    # ── Price Summary ──
    labs_total = calc_labs_total(selected_labs)
    total      = calc_total(selected_labs)
    st.markdown(f"""
    <div class="price-box">
      <div class="price-row"><span>🧪 سعر التحاليل</span><span>{labs_total} جنيه</span></div>
      <div class="price-row"><span>🚗 سعر الزيارة</span><span>{VISIT_PRICE} جنيه</span></div>
      <div class="price-total"><span>💰 الإجمالي</span><span>{total} جنيه</span></div>
    </div>
    """, unsafe_allow_html=True)

    # ── Save ──
    if st.button("💾 حفظ الزيارة" if not is_edit else "💾 حفظ التعديلات", use_container_width=True):
        if not name or not phone or not address:
            st.error("⚠️ من فضلك املأ الاسم والتليفون والعنوان")
        else:
            visits = load_visits()
            record = {
                "id":           pf.get("id", str(int(datetime.now().timestamp() * 1000))),
                "created_at":   pf.get("created_at", datetime.now().isoformat()),
                "name":         name,
                "age":          age,
                "phone":        phone,
                "visit_date":   visit_date.isoformat(),
                "address":      address,
                "location_link":location_link,
                "selected_labs":selected_labs,
                "custom_labs":  custom_labs,
                "notes":        notes,
            }
            if is_edit:
                visits = [record if v["id"] == record["id"] else v for v in visits]
                st.success("✅ تم تحديث الزيارة بنجاح!")
            else:
                visits.insert(0, record)
                st.success("✅ تم حفظ الزيارة بنجاح!")
            save_visits(visits)
            st.session_state.visits = visits
            go("detail", visit_id=record["id"])

    if is_edit:
        if st.button("← رجوع بدون حفظ", use_container_width=True):
            go("detail", visit_id=pf.get("id"))

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DETAIL
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "detail":
    visits = st.session_state.visits
    vid    = st.session_state.selected_id
    v      = next((x for x in visits if x["id"] == vid), None)

    if not v:
        st.error("لم يتم العثور على الزيارة")
        go("home")
    else:
        labs_total = calc_labs_total(v.get("selected_labs", []))
        total      = calc_total(v.get("selected_labs", []))

        # ── Personal ──
        st.markdown('<div class="ohv-card"><div class="ohv-section-title">👤 البيانات الشخصية</div>', unsafe_allow_html=True)
        st.markdown(f"""
        <div class="detail-row"><span class="detail-label">👤 الاسم</span><span class="detail-value">{v['name']}</span></div>
        <div class="detail-row"><span class="detail-label">🎂 السن</span><span class="detail-value">{v.get('age','')} سنة</span></div>
        <div class="detail-row"><span class="detail-label">📞 التليفون</span><span class="detail-value">{v.get('phone','')}</span></div>
        <div class="detail-row"><span class="detail-label">📅 تاريخ الزيارة</span><span class="detail-value">{format_date_ar(v.get('visit_date',''))}</span></div>
        """, unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Address ──
        st.markdown('<div class="ohv-card"><div class="ohv-section-title">📍 العنوان</div>', unsafe_allow_html=True)
        st.write(v.get("address",""))
        if v.get("location_link"):
            st.markdown(f'<a href="{v["location_link"]}" target="_blank" style="color:#FF6B00;font-weight:700;">🗺️ فتح الموقع على الخريطة</a>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

        # ── Labs ──
        if v.get("selected_labs") or v.get("custom_labs"):
            st.markdown('<div class="ohv-card"><div class="ohv-section-title">🧪 التحاليل</div>', unsafe_allow_html=True)
            for l in v.get("selected_labs", []):
                price = next((x["price"] for x in LABS if x["name"]==l), 0)
                st.markdown(f'<div class="detail-row"><span class="detail-label">• {l}</span><span class="lab-badge">{price} جنيه</span></div>', unsafe_allow_html=True)
            if v.get("custom_labs"):
                st.markdown(f"📝 **تحاليل إضافية:** {v['custom_labs']}")
            st.markdown('</div>', unsafe_allow_html=True)

        # ── Price ──
        st.markdown(f"""
        <div class="price-box">
          <div class="price-row"><span>🧪 سعر التحاليل</span><span>{labs_total} جنيه</span></div>
          <div class="price-row"><span>🚗 سعر الزيارة</span><span>{VISIT_PRICE} جنيه</span></div>
          <div class="price-total"><span>💰 الإجمالي</span><span>{total} جنيه</span></div>
        </div>
        """, unsafe_allow_html=True)

        # ── Notes ──
        if v.get("notes"):
            st.markdown('<div class="ohv-card"><div class="ohv-section-title">📌 ملاحظات</div>', unsafe_allow_html=True)
            st.write(v["notes"])
            st.markdown('</div>', unsafe_allow_html=True)

        # ── WhatsApp ──
        st.markdown("### 📱 إرسال على واتساب")
        wa_client_link = whatsapp_link(make_whatsapp_msg(v, for_client=True), phone=v.get("phone"))
        wa_share_link  = whatsapp_link(make_whatsapp_msg(v, for_client=False))

        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<a href="{wa_client_link}" target="_blank" class="wa-btn wa-client" style="display:block">📱 واتساب العميل</a>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<a href="{wa_share_link}" target="_blank" class="wa-btn wa-share" style="display:block">📋 مشاركة الملخص</a>', unsafe_allow_html=True)

        st.markdown("---")

        # ── Actions ──
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✏️ تعديل", use_container_width=True):
                go("new", prefill={**v, "_edit": True})
        with c2:
            if st.button("🗑️ حذف", use_container_width=True):
                st.session_state["confirm_delete"] = True

        if st.session_state.get("confirm_delete"):
            st.warning("⚠️ هل أنت متأكد من حذف هذه الزيارة؟")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("✅ نعم، احذف", use_container_width=True):
                    visits = [x for x in load_visits() if x["id"] != vid]
                    save_visits(visits)
                    st.session_state.visits = visits
                    st.session_state["confirm_delete"] = False
                    go("home")
            with cc2:
                if st.button("❌ إلغاء", use_container_width=True):
                    st.session_state["confirm_delete"] = False
                    st.rerun()

        # ── Repeat Visit ──
        st.markdown(f"""
        <div class="repeat-banner">
          🔄 هتروح لـ {v['name']} مرة تانية؟
        </div>
        """, unsafe_allow_html=True)
        if st.button(f"➕ زيارة جديدة لـ {v['name']}", use_container_width=True):
            go("new", prefill={
                "name":          v["name"],
                "age":           v.get("age",""),
                "phone":         v.get("phone",""),
                "address":       v.get("address",""),
                "location_link": v.get("location_link",""),
                "selected_labs": [],
                "custom_labs":   "",
                "notes":         "",
            })

        if st.button("← رجوع للقائمة", use_container_width=True):
            go("home")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SEARCH
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "search":
    st.markdown("### 🔍 البحث عن عميل")
    query = st.text_input("اكتب الاسم أو التليفون", placeholder="مثال: محمد أو 01012345678")

    if query:
        visits   = st.session_state.visits
        results  = [v for v in visits if
                    query.lower() in v.get("name","").lower() or
                    query in v.get("phone","")]

        st.markdown(f"**{len(results)} نتيجة**")

        for v in results:
            total  = calc_total(v.get("selected_labs", []))
            vdate  = format_date_ar(v.get("visit_date",""))
            st.markdown(f"""
            <div class="visit-card">
              <span class="visit-badge">{total:,} جنيه</span>
              <div class="visit-name">👤 {v['name']}</div>
              <div class="visit-meta">📞 {v.get('phone','')} &nbsp;|&nbsp; 📅 {vdate}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button(f"📂 فتح {v['name']}", key=f"s_{v['id']}", use_container_width=True):
                go("detail", visit_id=v["id"])
