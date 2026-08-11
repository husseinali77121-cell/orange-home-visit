# phone_utils.py
# ══════════════════════════════════════════════════════════════════════════════
#  ☎️ رقم تليفون دولي — مفتاح الدولة + باقي الرقم
#
#  ⚠️ قاعدة التوافق الرجعي:
#     الأرقام المصرية بتتخزّن **زي ما هي بالظبط** (01xxxxxxxxx) عشان الـ 1129
#     رقم المخزّن حالياً وكشف التكرار وسجل العميل (fetch_client_history) يفضلوا
#     شغالين حرف بحرف. الأرقام الأجنبية بس هي اللي بتتخزّن بصيغة +CC.
# ══════════════════════════════════════════════════════════════════════════════

import re

DEFAULT_CODE = "+20"

# (المفتاح، الاسم بالعربي، العلم) — مصر الأول، وبعدها الأكثر استخدامًا
COUNTRIES = [
    ("+20",  "مصر",            "🇪🇬"),
    ("+966", "السعودية",       "🇸🇦"),
    ("+971", "الإمارات",       "🇦🇪"),
    ("+965", "الكويت",         "🇰🇼"),
    ("+974", "قطر",            "🇶🇦"),
    ("+973", "البحرين",        "🇧🇭"),
    ("+968", "عُمان",           "🇴🇲"),
    ("+962", "الأردن",         "🇯🇴"),
    ("+961", "لبنان",          "🇱🇧"),
    ("+963", "سوريا",          "🇸🇾"),
    ("+964", "العراق",         "🇮🇶"),
    ("+970", "فلسطين",         "🇵🇸"),
    ("+249", "السودان",        "🇸🇩"),
    ("+218", "ليبيا",          "🇱🇾"),
    ("+216", "تونس",           "🇹🇳"),
    ("+213", "الجزائر",        "🇩🇿"),
    ("+212", "المغرب",         "🇲🇦"),
    ("+967", "اليمن",          "🇾🇪"),
    ("+252", "الصومال",        "🇸🇴"),
    ("+253", "جيبوتي",         "🇩🇯"),
    ("+90",  "تركيا",          "🇹🇷"),
    ("+1",   "أمريكا/كندا",    "🇺🇸"),
    ("+44",  "بريطانيا",       "🇬🇧"),
    ("+49",  "ألمانيا",        "🇩🇪"),
    ("+33",  "فرنسا",          "🇫🇷"),
    ("+39",  "إيطاليا",        "🇮🇹"),
    ("+34",  "إسبانيا",        "🇪🇸"),
    ("+31",  "هولندا",         "🇳🇱"),
    ("+7",   "روسيا",          "🇷🇺"),
    ("+91",  "الهند",          "🇮🇳"),
    ("+92",  "باكستان",        "🇵🇰"),
    ("+86",  "الصين",          "🇨🇳"),
    ("+27",  "جنوب أفريقيا",   "🇿🇦"),
    ("+234", "نيجيريا",        "🇳🇬"),
    ("+254", "كينيا",          "🇰🇪"),
    ("+251", "إثيوبيا",        "🇪🇹"),
]

CODES = [c for c, _, _ in COUNTRIES]
# الأطول الأول عشان "+971" ما يتلخبطش مع "+97"
_CODES_SORTED = sorted(CODES, key=len, reverse=True)
_LABELS = {c: f"{flag} {c}" for c, name, flag in COUNTRIES}
_NAMES = {c: name for c, name, _ in COUNTRIES}


def label_for(code):
    return _LABELS.get(code, code)


def country_name(code):
    return _NAMES.get(code, "")


def clean_digits(s):
    """يسيب الأرقام بس (بيشيل مسافات وشرط وأقواس والأرقام العربية بتتحوّل)."""
    s = str(s or "").translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    return re.sub(r"\D", "", s)


def split_phone(stored):
    """
    رقم مخزّن → (مفتاح الدولة، باقي الرقم).
    أي رقم مش مبدوء بـ + بيتعتبر مصري ويرجع زي ما هو (01xxxxxxxxx).
    """
    s = str(stored or "").strip().replace(" ", "").replace("-", "")
    if s.startswith("+"):
        for c in _CODES_SORTED:
            if s.startswith(c):
                return c, s[len(c):]
        # مفتاح مش في القايمة → سيبه كامل في الخانة عشان ما يضيعش
        return DEFAULT_CODE, s
    return DEFAULT_CODE, s


def join_phone(code, rest):
    """
    (مفتاح، باقي الرقم) → الصيغة اللي بتتخزّن.
    مصر (+20): بيرجع الرقم زي ما هو — نفس صيغة الـ 1129 رقم المخزّنين.
    غير كده: +CC + الرقم.
    """
    rest = str(rest or "").strip().replace(" ", "").replace("-", "")
    rest = rest.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    if not rest:
        return ""
    if str(code or DEFAULT_CODE) == DEFAULT_CODE:
        return rest                      # ← التوافق الرجعي
    return f"{code}{rest.lstrip('0')}"   # الدولي: الصفر البادئ بيتشال


def wa_digits(phone):
    """
    رقم مخزّن → الأرقام اللي بتتحط في wa.me
    • الأرقام الدولية (+): بتتاخد زي ما هي.
    • أي حاجة تانية: نفس منطق البرنامج الأصلي بالظبط (مصر).
    """
    p = str(phone or "").strip().replace(" ", "").replace("-", "")
    if p.startswith("+"):
        return clean_digits(p)           # مفيش لزوم نضيف 20
    p = p.replace("+", "")
    if p.startswith("0"):
        return "20" + p[1:]
    if not p.startswith("20"):
        return "20" + p
    return p


def display(phone):
    """عرض مقروء من اليسار لليمين."""
    code, rest = split_phone(phone)
    if str(phone or "").startswith("+"):
        return f"{code} {rest}"
    return str(phone or "")


def same_number(a, b):
    """هل الرقمين بيوصّلوا لنفس الشخص؟ (مقارنة بأرقام الواتس مش بالنص)."""
    if not a or not b:
        return False
    return wa_digits(a) == wa_digits(b)


# ── واجهة Streamlit ───────────────────────────────────────────────────────────
def render_phone_input(st, label, value="", key_prefix="ph", placeholder="1xxxxxxxxx",
                       required=True):
    """
    خانتين جنب بعض: مفتاح الدولة + باقي الرقم. بترجّع الرقم بالصيغة المخزّنة.

    ⚠️ لو المستخدم ما غيّرش الرقم فعلياً، بنرجّع **النص المخزّن الأصلي زي ما هو**.
       ليه؟ سجل العميل وكشف التكرار بيقارنوا نص الرقم حرف بحرف، فلو أعدنا
       كتابة رقم قديم متخزّن بصيغة "+2010..." لصيغة "010..." كان هيتفصل عن
       تاريخ زياراته السابقة. الرقم بيتغيّر بس لما المستخدم يغيّره بجد.
    """
    code0, rest0 = split_phone(value)
    if code0 not in CODES:
        CODES.insert(0, code0)
        _LABELS[code0] = code0
    c1, c2 = st.columns([1, 2.4])
    with c1:
        code = st.selectbox(
            "المفتاح", CODES, index=CODES.index(code0),
            format_func=label_for, key=f"{key_prefix}_code",
        )
    with c2:
        rest = st.text_input(
            label + (" *" if required else ""), value=rest0,
            placeholder="01xxxxxxxxx" if code == DEFAULT_CODE else placeholder,
            key=f"{key_prefix}_num",
        )
    out = join_phone(code, rest)
    if value and same_number(out, value):
        return str(value).strip()        # ← ما اتغيرش: سيبه زي ما هو
    if code != DEFAULT_CODE and rest.strip():
        st.caption(f"📱 {country_name(code)} — هيتخزّن: {out}")
    return out
