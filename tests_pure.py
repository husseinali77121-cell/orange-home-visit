# tests_pure.py — اختبارات الطبقة النقية (مالهاش أي علاقة بـ Streamlit)
# التشغيل:  python3 tests_pure.py     أو     pytest tests_pure.py
#
# الدوال دي هي اللي كانت فيها البقّ الصامت (أسعار وتواريخ وأرقام تليفون).
# أي تعديل مستقبلي فيها لازم يعدّي من هنا الأول.

import re as re_module
from datetime import date
import phone_utils as phu
import lab_picker as lp

_FAILS = []


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


# ── نسخ طبق الأصل من app.py (الدوال النقية) ──────────────────────────────────
def _lab_price(entry):
    m = re_module.findall(r'(\d[\d,]*)\s*جنيه', str(entry or ""))
    if not m:
        return 0
    try:
        return int(m[-1].replace(",", ""))
    except ValueError:
        return 0


def _month_of(rec):
    d = str(rec.get("visit_date") or "").strip()
    try:
        date.fromisoformat(d[:10])
        return d[:7]
    except Exception:
        return "0000-00"


def _time_key(t):
    m = re_module.match(r'\s*(\d{1,2}):(\d{2})\s*(AM|PM|ص|م)?', str(t or ""), re_module.IGNORECASE)
    if not m:
        return -1
    h, mi, ap = int(m.group(1)), int(m.group(2)), (m.group(3) or "").upper()
    if ap in ("PM", "م") and h != 12: h += 12
    if ap in ("AM", "ص") and h == 12: h = 0
    return h * 60 + mi


def _esc(txt):
    return (str(txt or "").strip().replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))


def _safe_url(url):
    u = str(url or "").strip()
    return _esc(u) if u.lower().startswith(("http://", "https://")) else ""


# ══════════════════════════════════════════════════════════════════════════════
print("\n💰 _lab_price — استخراج السعر")
check("سطر عادي",            _lab_price("CBC — 400 جنيه"), 400)
check("سعر بفاصلة (كان 200)", _lab_price("Test — 1,200 جنيه"), 1200)
check("فاصلتين",             _lab_price("PCR — 12,500 جنيه"), 12500)
check("رقم في الاسم (كان 25)", _lab_price("تحليل 25 جنيه شامل — 300 جنيه"), 300)
check("Vit D3 (25)",         _lab_price("Vitamin D3(25 Hydroxy Cholecal.) — 900 جنيه"), 900)
check("من غير سعر",          _lab_price("CBC - 400 EGP"), 0)
check("فاضي",                _lab_price(""), 0)
check("None",                _lab_price(None), 0)
check("صفر",                 _lab_price("Free test — 0 جنيه"), 0)

print("\n📅 _month_of — تقسيم الشهور")
check("تاريخ سليم",       _month_of({"visit_date": "2026-06-14"}), "2026-06")
check("وقت مش تاريخ",     _month_of({"visit_date": "19:00:00"}), "0000-00")
check("شهر بخانة واحدة",  _month_of({"visit_date": "2026-8-1"}), "0000-00")
check("فاضي",             _month_of({"visit_date": ""}), "0000-00")
check("None",             _month_of({"visit_date": None}), "0000-00")
check("مفتاح ناقص",       _month_of({}), "0000-00")
check("تاريخ + وقت",      _month_of({"visit_date": "2026-06-14T09:00:00"}), "2026-06")
check("29 فبراير مش كبيسة", _month_of({"visit_date": "2026-02-29"}), "0000-00")

print("\n🕐 _time_key — ترتيب المواعيد")
check("9:05 PM",  _time_key("9:05 PM"), 1265)
check("12:00 AM", _time_key("12:00 AM"), 0)
check("12:30 PM", _time_key("12:30 PM"), 750)
check("عربي م",   _time_key("9:05 م"), 1265)
check("فاضي",     _time_key(""), -1)
check("ترتيب صح", _time_key("9:00 AM") < _time_key("9:00 PM"), True)

print("\n☎️ wa_digits — لينك واتساب")
check("مصري عادي",   phu.wa_digits("01016872801"), "201016872801")
check("أرقام عربية", phu.wa_digits("٠١٠١٦٨٧٢٨٠١"), "201016872801")
check("دولي بمسافات", phu.wa_digits("+20 11 15644483"), "201115644483")
check("سوداني",      phu.wa_digits("+249122077443"), "249122077443")
check("بشرط",        phu.wa_digits("010-1687-2801"), "201016872801")
check("فاضي",        phu.wa_digits(""), "")
check("None",        phu.wa_digits(None), "")
check("مبدوء بـ20",  phu.wa_digits("201016872801"), "201016872801")

print("\n🔗 _safe_url — منع javascript:")
check("https عادي",  _safe_url("https://maps.app.goo.gl/x"), "https://maps.app.goo.gl/x")
check("http عادي",   _safe_url("http://example.com"), "http://example.com")
check("javascript:", _safe_url("javascript:alert(1)"), "")
check("data:",       _safe_url("data:text/html,<script>"), "")
check("فاضي",        _safe_url(""), "")
check("نص عادي",     _safe_url("الحي الأول بجوار المسجد"), "")

print("\n🛡️ _esc — منع حقن HTML")
check("اسم فيه وسم", _esc('<img src=x onerror=alert(1)>'),
      "&lt;img src=x onerror=alert(1)&gt;")
check("أمبرساند",    _esc("محمد & أحمد"), "محمد &amp; أحمد")
check("اسم عادي",    _esc("حسين علي"), "حسين علي")
check("None",        _esc(None), "")

print("\n🔎 lab_picker — الصيغة المخزّنة ما اتغيرتش")
check("format_entry", lp.format_entry("CBC", 400), "CBC — 400 جنيه")
check("entry_name",   lp.entry_name("CBC — 400 جنيه"), "CBC")
check("entry_name شرطة عادية", lp.entry_name("CBC - 400 جنيه"), "CBC")
check("entry_price",  lp.entry_price("CBC — 400 جنيه"), 400)
check("توافق _lab_price مع format_entry",
      _lab_price(lp.format_entry("Ferritin", 1200)), 1200)

print("\n📞 split/join — التوافق الرجعي للأرقام المصرية")
check("مصري يفضل زي ما هو", phu.join_phone("+20", "01016872801"), "01016872801")
check("دولي بصيغة +",       phu.join_phone("+249", "0122077443"), "+249122077443")
check("split مصري",         phu.split_phone("01016872801"), ("+20", "01016872801"))
check("same_number",        phu.same_number("01016872801", "+201016872801"), True)

print("\n" + "═" * 60)
if _FAILS:
    print(f"❌ فشل {len(_FAILS)} اختبار: {', '.join(_FAILS)}")
    raise SystemExit(1)
print("✅ كل الاختبارات نجحت")
