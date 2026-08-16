# -*- coding: utf-8 -*-
"""
core.py — الطبقة النقية لـ Orange Lab HVMS

دوال تحقّق وتنسيق **من غير أي اعتماد على Streamlit أو قاعدة البيانات أو الشبكة**.
مدخلات ← مخرجات. مفيش حالة، مفيش آثار جانبية (ما عدا كاش داخلي واحد).

ليه ملف منفصل:
  ① الاختبارات بقت تختبر **الكود الحقيقي** مش نسخة منه. قبل كده tests_pure.py
     كان بينسخ الدوال، يعني app.py يتغيّر والاختبارات تفضل خضرا.
  ② repair_data.py و app.py بيقروا من نفس المصدر — مافيش انحراف بينهم.
  ③ أول شريحة من تفكيك app.py، وأقلها مخاطرة (صفر اعتماديات).

الاستيراد:  from core import _esc, format_money, canonicalize_geo, ...
الاختبار :  python3 tests_pure.py
"""
import re as re_module
import hashlib
import json
import uuid as uuid_lib
from datetime import date, datetime


# ══════════════════════════════════════════════════════════════════════════════
# دوال مساعدة للتنسيق
# ══════════════════════════════════════════════════════════════════════════════
def _esc(txt):
    """
    تهريب HTML لأي نص جاي من المستخدم قبل ما يتحط في markdown بـ
    unsafe_allow_html. سطر تحليل مكتوب يدوي فيه < أو > كان بيبوّظ التنسيق.
    """
    return (str(txt or "").strip().replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))

def format_money(value):
    try:
        val = float(value or 0)
        return f"{val:,.0f} جنيه"
    except (ValueError, TypeError):
        return "0 جنيه"

def _safe_url(url):
    """
    رابط آمن للحقن في href. رابط الموقع بيتكتب بإيد المستخدم، ولو حد كتب
    `javascript:...` كان هيتنفّذ كود لما أي حد يضغط على «فتح الموقع».
    بنسمح بـ http/https بس، وأي حاجة تانية بترجع فاضية (الرابط مايتعرضش).
    """
    u = str(url or "").strip()
    return _esc(u) if u.lower().startswith(("http://", "https://")) else ""

# ══════════════════════════════════════════════════════════════════════════════
# 🔤 تطبيع النص العربي
# ══════════════════════════════════════════════════════════════════════════════
_AR_MAP = str.maketrans({"ى": "ي", "أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا",
                         "ة": "ه", "ؤ": "و", "ئ": "ي",
                         "\u064B": "", "\u064C": "", "\u064D": "", "\u064E": "",
                         "\u064F": "", "\u0650": "", "\u0651": "", "\u0652": "",
                         "\u0640": ""})

def normalize_ar(s):
    """
    مفتاح **مطابقة** للنص العربي — مش شكل للتخزين.

    بيوحّد الاختلافات الإملائية عشان «الحي الثامن» و«الحى الثامن» يبقى ليهم
    نفس المفتاح فيتجمّعوا صح في التقارير والتجميع الجغرافي.

    ⚠️ الناتج **مشوّه بقصد** (ة→ه ، ئ→ي): «حدائق» بيطلع «حدايق».
       عشان كده ممنوع يتخزّن. للتخزين استخدم `canonicalize_geo()`.
    """
    s = str(s or "").strip().translate(_AR_MAP)
    s = re_module.sub(r"[\u200f\u200e\u00a0]", " ", s)      # محارف اتجاه/مسافة خفية
    # ★ الفصل في **الاتجاهين**. الإصدار القديم كان بيفصل رقم←حرف بس
    #   («6اكتوبر» → «6 اكتوبر») ومايفصلش حرف←رقم، فـ«الحى11» كان بيفضل
    #   ملزوق ومايطابقش «الحي 11» — وده خلّى تصنيفين وهميين يعيشوا بعد التنظيف.
    s = re_module.sub(r"(\d)\s*([\u0600-\u06FF])", r"\1 \2", s)   # «6اكتوبر» → «6 اكتوبر»
    s = re_module.sub(r"([\u0600-\u06FF])\s*(\d)", r"\1 \2", s)   # «الحي11»  → «الحي 11»
    return re_module.sub(r"\s+", " ", s).strip()

def clean_text(s):
    """تنظيف بلا خسارة: مسافات زيادة ومحارف اتجاه خفية بس. الحروف زي ما هي."""
    s = re_module.sub(r"[\u200f\u200e\u00a0]", " ", str(s or ""))
    return re_module.sub(r"\s+", " ", s).strip()

# الأشكال القانونية للمناطق والمدن. مبنية من بيانات المعمل الفعلية باختيار
# **أصحّ** إملاء مش الأكتر تكرارًا — عشان كده «6 أكتوبر» (281 مرة) كسبت
# «6اكتوبر» (542 مرة).
_GEO_CANON_LIST = [
    "6 أكتوبر", "الشيخ زايد", "القاهرة", "الجيزة", "الإسكندرية", "طريق الواحات",
    "الطريق الصحراوي", "المتميز", "غرب سوميد", "حدائق الأهرام", "حدائق أكتوبر",
    "حدائق المهندسين", "بيفرلي هيلز", "مينا جاردن سيتي", "هرم سيتي", "سيتي فيو",
    "رويال سيتي", "فاملي لاند", "هاي لاند", "وادي الربيع", "مدينة الخمائل",
    "جنة أكتوبر", "كمبوند الروضة", "التوسعات الشمالية", "السياحية الأولى",
    "المحور الخدمي", "حي الأشجار", "حي الورود", "حي الندى", "حي الأندلس", "الدقي",
    "الحي الأول", "الحي الثاني", "الحي الثالث", "الحي الرابع", "الحي الخامس",
    "الحي السادس", "الحي السابع", "الحي الثامن", "الحي التاسع", "الحي العاشر",
    "الحي الحادي عشر", "الحي الثاني عشر", "الحي الثالث عشر", "الحي الرابع عشر",
    "الحي الخامس عشر", "الحي السادس عشر", "الحي المتميز",
]

_GEO_CANON = {}   # كسول — normalize_ar لازم تكون متعرّفة الأول

# مرادفات: صيغة رقمية → الشكل القانوني المكتوب. «الحي 11» و«الحى2» موجودين
# فعلاً في البيانات وكانوا بيعملوا مجموعات منفصلة عن «الحي الحادي عشر»
# و«الحي الثاني». ده مرادف **دلالي** مش إملائي، فمحتاج جدول صريح.
_GEO_ALIASES = {}
for _i, _w in enumerate(["الأول","الثاني","الثالث","الرابع","الخامس","السادس","السابع",
                         "الثامن","التاسع","العاشر","الحادي عشر","الثاني عشر",
                         "الثالث عشر","الرابع عشر","الخامس عشر","السادس عشر"], 1):
    # «الحي 3» و«حي 3» و«الحى3» كلهم بيوصلوا لـ«الحي الثالث».
    # normalize_ar بتفصل الرقم عن الحرف، فالشكل الملزوق بيطابق تلقائيًا.
    _GEO_ALIASES[f"الحي {_i}"] = f"الحي {_w}"
    _GEO_ALIASES[f"حي {_i}"]   = f"الحي {_w}"
_GEO_ALIASES_OLD = {
    "الحي 1": "الحي الأول",        "الحي 2": "الحي الثاني",
    "الحي 3": "الحي الثالث",       "الحي 4": "الحي الرابع",
    "الحي 5": "الحي الخامس",       "الحي 6": "الحي السادس",
    "الحي 7": "الحي السابع",       "الحي 8": "الحي الثامن",
    "الحي 9": "الحي التاسع",       "الحي 10": "الحي العاشر",
    "الحي 11": "الحي الحادي عشر",  "الحي 12": "الحي الثاني عشر",
    "الحي 13": "الحي الثالث عشر",  "الحي 14": "الحي الرابع عشر",
    "الحي 15": "الحي الخامس عشر",  "الحي 16": "الحي السادس عشر",
}
_GEO_ALIASES.update(_GEO_ALIASES_OLD)

def canonicalize_geo(value):
    """
    شكل **التخزين** لحقل المدينة/المنطقة.

    • بيطابق شكل قانوني معروف (بعد التطبيع) → نرجّع الشكل القانوني بإملائه
      الصحيح. «الحى الثامن» → «الحي الثامن» · «6اكتوبر» → «6 أكتوبر»
    • بيطابق مرادف رقمي → نرجّع الشكل المكتوب. «الحى2» → «الحي الثاني»
    • مش معروف (منطقة جديدة)؟ → نرجّعه بتنظيف مسافات بس، **بلا أي تشويه**.
      البرنامج مايفرضش إملاء على حاجة مايعرفهاش — «حدائق النخيل» بتفضل بهمزتها.
    """
    v = clean_text(value)
    if not v:
        return ""
    if not _GEO_CANON:
        for c in _GEO_CANON_LIST:
            _GEO_CANON[normalize_ar(c)] = c
        for a, c in _GEO_ALIASES.items():
            _GEO_CANON[normalize_ar(a)] = c
    return _GEO_CANON.get(normalize_ar(v), v)

def _payment_problems(rec):
    """
    بيرجّع قائمة تناقضات مالية في السجل (فاضية = سليم).
    الحالات دي مش أخطاء برمجية — دي بيانات بتقول حاجة مستحيلة، ولو عدّت
    بتخرّب التقارير المالية والتحصيل من غير ما حد ياخد باله.
    """
    def _n(x):
        try: return float(x or 0)
        except (TypeError, ValueError): return 0.0
    st_pay = str(rec.get("payment_status") or "").strip()
    paid   = _n(rec.get("paid_amount"))
    total  = _n(rec.get("total_price"))
    out = []
    if st_pay == "مدفوع" and total > 0 and paid <= 0:
        out.append(f"«مدفوع» والمبلغ المدفوع صفر (الإجمالي {total:,.0f})")
    if st_pay == "مدفوع جزئياً" and paid <= 0:
        out.append("«مدفوع جزئياً» والمبلغ المدفوع صفر")
    if st_pay == "غير مدفوع" and paid > 0:
        out.append(f"«غير مدفوع» ومسجّل مدفوع {paid:,.0f}")
    if paid > total + 0.01 and total > 0:
        out.append(f"المدفوع ({paid:,.0f}) أكبر من الإجمالي ({total:,.0f})")
    return out

def _lab_price(entry):
    """
    يستخرج السعر من سطر تحليل بصيغة 'CBC — 400 جنيه'. يرجّع 0 لو مفيش سعر.

    ★ اتصلّح بقّين كانوا بيضيّعوا فلوس في صمت — الاتنين بيتفعّلوا من خانة
      «أضف تحليل يدوياً» اللي بتقبل أي نص:
        ١) الفاصلة: "Test — 1,200 جنيه" كانت بترجّع 200 (السعر اتقص عند الفاصلة).
        ٢) أول تطابق: "تحليل 25 جنيه شامل — 300 جنيه" كانت بترجّع 25.
      الحل: نقبل الفواصل جوّه الرقم، وناخد **آخر** تطابق (السعر دايمًا في آخر السطر).
    """
    m = re_module.findall(r'(\d[\d,]*)\s*جنيه', str(entry or ""))
    if not m:
        return 0
    try:
        return int(m[-1].replace(",", ""))
    except ValueError:
        return 0

def parse_extra_persons(raw):
    """يقرأ عمود extra_persons ويرجّع list of dicts. أي داتا بايظة → [] بدل ما يكسر."""
    if not raw:
        return []
    data = raw if isinstance(raw, list) else None
    if data is None:
        try:
            data = json.loads(raw)
        except Exception:
            return []
    if not isinstance(data, list):
        return []
    out = []
    seen = set()
    for p in data:
        if not isinstance(p, dict):
            continue
        labs = p.get("labs") or []
        if isinstance(labs, str):
            labs = [l.strip() for l in labs.splitlines() if l.strip()]
        # uid مكرر = مفتاحين widget بنفس الاسم = Streamlit بيرمي DuplicateWidgetID
        # ويقفل الصفحة كلها. بنولّد واحد جديد بدل ما البرنامج يقع.
        uid = str(p.get("uid") or "")
        if not uid or uid in seen:
            uid = uuid_lib.uuid4().hex[:8]
            while uid in seen:
                uid = uuid_lib.uuid4().hex[:8]
        seen.add(uid)
        out.append({
            "uid":      uid,
            "name":     str(p.get("name") or "").strip(),
            "age":      str(p.get("age") or "").strip(),
            "age_unit": str(p.get("age_unit") or "سنة"),
            "relation": str(p.get("relation") or "").strip(),
            "labs":     [str(l).strip() for l in labs if str(l).strip()],
        })
    return out

def dump_extra_persons(persons):
    """يحوّل للـ JSON للتخزين — بيتجاهل أي صف من غير اسم (صفوف فاضية اتفتحت وماتملتش)."""
    clean = [p for p in _valid_persons(persons) if str(p.get("name", "")).strip()]
    return json.dumps(clean, ensure_ascii=False) if clean else ""

def _valid_persons(persons):
    """
    بيرجّع قائمة القواميس الصالحة بس. الدوال اللي تحت بتتنادى من الفورم
    وبتغذّي الإجمالي المالي — عنصر واحد بايظ (None مثلاً) كان بيرمي
    AttributeError ويوقّع شاشة إدخال الزيارة كلها.
    """
    if not isinstance(persons, (list, tuple)):
        return []
    return [p for p in persons if isinstance(p, dict)]


def extra_persons_total(persons):
    """إجمالي أسعار تحاليل كل الحالات الإضافية."""
    return sum(_lab_price(l) for p in _valid_persons(persons) for l in (p.get("labs") or []))

def extra_persons_labs_count(persons):
    return sum(len(p.get("labs") or []) for p in _valid_persons(persons))

def extra_person_title(p):
    """سطر تعريف الحالة: الاسم — العمر (الصلة)."""
    who = p.get("name", "") or "بدون اسم"
    if p.get("age"):
        who += f" — {p['age']} {p.get('age_unit','سنة')}"
    if p.get("relation"):
        who += f" ({p['relation']})"
    return who

# ══════════════════════════════════════════════════════════════════════════════
# ★ v5 — أدوات التقسيم الشهري
# ══════════════════════════════════════════════════════════════════════════════
def _month_of(rec):
    """
    '2026-06-14' → '2026-06'. أي تاريخ غلط/فاضي → '0000-00' (سلة مستقلة، مش بتضيع).

    ★ الفحص القديم (len>=7 and d[4]=='-') كان بيعدّي تواريخ بايظة وينتج أسماء
      ملفات مكسورة: "2026-8-1" → "2026-8-" → visits/2026-8-.json
      (وفعلًا فيه سجل في الأرشيف تاريخه "19:00:00"). التحقق الحقيقي بيقفل الباب ده.
    """
    d = str(rec.get("visit_date") or "").strip()
    try:
        date.fromisoformat(d[:10])
        return d[:7]
    except Exception:
        return "0000-00"

# ══════════════════════════════════════════════════════════════════════════════
# Excel Export/Import
# ══════════════════════════════════════════════════════════════════════════════
def _time_key(t):
    """'9:05 PM' → 1265 (دقائق من منتصف الليل). فاضي/غير معروف → -1 (أول اليوم)."""
    m = re_module.match(r'\s*(\d{1,2}):(\d{2})\s*(AM|PM|ص|م)?', str(t or ""), re_module.IGNORECASE)
    if not m: return -1
    h, mi, ap = int(m.group(1)), int(m.group(2)), (m.group(3) or "").upper()
    if ap in ("PM", "م") and h != 12: h += 12
    if ap in ("AM", "ص") and h == 12: h = 0
    return h * 60 + mi

MONTHS_AR = ["يناير","فبراير","مارس","أبريل","مايو","يونيو",
             "يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]

# ══════════════════════════════════════════════════════════════════════════════
# دوال مساعدة
# ══════════════════════════════════════════════════════════════════════════════
def format_date_ar(d):
    """
    تاريخ → «12 أغسطس 2026». المدخل الغلط بيرجع كنص، مش استثناء.

    ★ الإصدار القديم كان بيروح على `d.day` مباشرة لأي مدخل مش نص — يعني رقم
      أو dict أو list كانوا بيرموا AttributeError ويوقّعوا الصفحة كلها.
      عمليًا كل النداءات بتبعت نص أو date، بس دالة تنسيق ماينفعش توقّع صفحة.
    """
    if not d:
        return ""
    if isinstance(d, str):
        try:
            d = datetime.strptime(d.strip()[:10], "%Y-%m-%d").date()
        except Exception:
            return d
    try:
        if not (1 <= d.month <= 12):
            return str(d)
        return f"{d.day} {MONTHS_AR[d.month - 1]} {d.year}"
    except Exception:
        return str(d)

def get_client_tag_color(tag):
    # ★ str() قبل البحث: dict/list بيرموا TypeError (unhashable). دالة ألوان
    #   ماينفعش توقّع صفحة.
    tag = str(tag) if not isinstance(tag, str) else tag
    return {"🆕 عميل جديد":"#3498DB","⭐ عميل منتظم":"#27AE60",
            "🌟 عميل متكرر":"#F39C12","👑 VIP":"#9B59B6",
            "🏢 Corporate":"#E74C3C"}.get(tag,"#888")

def _hash_records(recs):
    """بصمة محتوى ثابتة لمجموعة صفوف — بنقارن بيها بدل ما نرفع شهر ماتغيرش."""
    # ★ الفلترة مش زيادة: الدالة دي بتغذّي حارس «المحتوى ماتغيّرش» في المزامنة.
    #   لو رمت استثناء، save_to_github_json بتفشل والبيانات تفضل محلية بس.
    rows = [r for r in (recs or []) if isinstance(r, dict)] if isinstance(recs, (list, tuple)) else []
    canon = json.dumps(
        sorted(rows, key=lambda x: str(x.get("id") or "")),
        ensure_ascii=False, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()[:16]

# ══════════════════════════════════════════════════════════════════════════════
# 💰 تعريف الإيراد — مصدر حقيقة واحد
# ══════════════════════════════════════════════════════════════════════════════
# قبل كده كان في تعريفين شغالين في نفس الوقت، وفي **نفس صفحة التقارير**:
#   • total_price      → الرئيسية · Dashboard · «الإيراد اليومي» · ملخص الأطباء
#   • labs_price_after → KPI التقارير · الرسم الأسبوعي · «الزيارات بالدكتور»
# الفرق = بدل الانتقال. على الـ156 زيارة الحالية ده 19,730 ج تحت نفس اللافتة.
# القاعدة: «الإيراد» = المحصّل كامل (total_price). لو عايز التحاليل لوحدها
# استخدم labs_revenue() صراحة — الاسم بيقول الفرق.

def _num(x):
    try:
        return float(x or 0)
    except (TypeError, ValueError):
        return 0.0


def is_countable(v):
    """الزيارة بتتحسب في الإيراد؟ الملغية لأ."""
    return isinstance(v, dict) and str(v.get("status") or "") != "ملغية"


def revenue(visits):
    """إجمالي الإيراد = تحاليل بعد الخصم + بدل الانتقال. ده الرقم الرسمي."""
    return sum(_num(v.get("total_price")) for v in (visits or []) if is_countable(v))


def labs_revenue(visits):
    """إيراد التحاليل وحدها (من غير بدل الانتقال) — لحساب عمولة الأطباء."""
    return sum(_num(v.get("labs_price_after")) for v in (visits or []) if is_countable(v))


def transport_revenue(visits):
    """بدل الانتقال وحده."""
    return sum(_num(v.get("transport_fee")) for v in (visits or []) if is_countable(v))

