# tests_pure.py — اختبارات الطبقة النقية
# التشغيل:  python3 tests_pure.py
#
# ★ الاختبارات دي بتستورد من core.py مباشرة — يعني بتختبر **الكود الحقيقي**
#   اللي بيشتغل في التطبيق. قبل كده كانت بتنسخ الدوال جواها، وده كان معناه
#   إن app.py يتغيّر والاختبارات تفضل خضرا وهي بتختبر نسخة قديمة.

import re as re_module
import phone_utils as phu
import lab_picker as lp
from core import (
    _esc, format_money, _safe_url, revenue, labs_revenue, transport_revenue,
    normalize_ar, clean_text, canonicalize_geo,
    _payment_problems, _lab_price,
    _month_of, _time_key, format_date_ar,
    parse_extra_persons, dump_extra_persons,
    extra_persons_total, extra_persons_labs_count,
    get_client_tag_color, _hash_records,
)

_FAILS = []


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


def import_date_check(raw):
    """نفس منطق قبول/رفض التاريخ في import_from_excel."""
    import pandas as pd
    from datetime import date as _date
    if raw is None or str(raw).strip() == "":
        return "التاريخ فاضي"
    try:
        parsed = pd.to_datetime(raw, errors="raise")
        if pd.isna(parsed):
            raise ValueError("NaT")
        d = parsed.strftime("%Y-%m-%d")
        return None if "2000-01-01" <= d <= "2100-12-31" else f"خارج المدى ({d})"
    except Exception:
        return f"غير صالح ({str(raw)[:24]})"


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

print("\n🔤 normalize_ar — مفتاح المطابقة (مشوّه بقصد)")
check("الحى → الحي",        normalize_ar("الحى الثامن"), "الحي الثامن")
check("6اكتوبر يتفصل",     normalize_ar("6اكتوبر"), "6 اكتوبر")
check("6 أكتوبر يتوحّد",    normalize_ar("6 أكتوبر"), "6 اكتوبر")
check("الشكلين بيتساووا",  normalize_ar("الحى الثامن") == normalize_ar("الحي الثامن"), True)
check("التشكيل بيتشال",     normalize_ar("الحَيّ الثَانِي"), "الحي الثاني")
check("مسافات زيادة",      normalize_ar("  الحي   الأول  "), "الحي الاول")
check("إنجليزي مايتأثرش",  normalize_ar("Sheikh Zayed"), "Sheikh Zayed")
check("فاضي",              normalize_ar(""), "")
check("None",              normalize_ar(None), "")

print("\n🗺️ canonicalize_geo — شكل التخزين (لازم يحافظ على الإملاء)")
check("الحى → الحي (قانوني)",   canonicalize_geo("الحى الثامن"), "الحي الثامن")
check("6اكتوبر → 6 أكتوبر",     canonicalize_geo("6اكتوبر"), "6 أكتوبر")
check("حدايق → حدائق (مايشوّهش)", canonicalize_geo("حدايق الاهرام"), "حدائق الأهرام")
check("الشماليه → الشمالية",     canonicalize_geo("التوسعات الشماليه"), "التوسعات الشمالية")
check("الروضه → الروضة",         canonicalize_geo("كمبوند الروضه"), "كمبوند الروضة")
check("الشكل القانوني ثابت",     canonicalize_geo("الحي الأول"), "الحي الأول")
check("منطقة جديدة تفضل زي ما هي", canonicalize_geo("كمبوند بالم هيلز"), "كمبوند بالم هيلز")
check("منطقة جديدة بهمزة محفوظة", canonicalize_geo("حدائق النخيل"), "حدائق النخيل")
check("مسافات زيادة بس",        canonicalize_geo("  كمبوند   جديد  "), "كمبوند جديد")
check("فاضي",                   canonicalize_geo(""), "")
check("None",                   canonicalize_geo(None), "")
check("كل الأشكال بتلمّ على واحد",
      canonicalize_geo("الحى الثامن") == canonicalize_geo("الحي الثامن") == "الحي الثامن", True)
check("الحى11 ملزوق → الحادي عشر", canonicalize_geo("الحى11"), "الحي الحادي عشر")
check("الحى2 ملزوق → الثاني",       canonicalize_geo("الحى2"), "الحي الثاني")
check("الحي3 ملزوق → الثالث",       canonicalize_geo("الحي3"), "الحي الثالث")
check("حى 5 من غير ال → الخامس",    canonicalize_geo("حى 5"), "الحي الخامس")
check("حي5 ملزوق بلا ال",           canonicalize_geo("حي5"), "الحي الخامس")
check("الملزوق = المفصول",
      canonicalize_geo("الحى11") == canonicalize_geo("الحي 11"), True)
check("normalize بيفصل الاتجاهين",
      (normalize_ar("الحي11"), normalize_ar("6اكتوبر")), ("الحي 11", "6 اكتوبر"))
check("التخزين ≠ المطابقة",
      canonicalize_geo("حدايق الاهرام") != normalize_ar("حدايق الاهرام"), True)

print("\n💳 _payment_problems — منع التناقض المالي")
check("مدفوع + صفر يترفض",       bool(_payment_problems({"payment_status":"مدفوع","paid_amount":0,"total_price":450})), True)
check("مدفوع سليم يعدّي",         _payment_problems({"payment_status":"مدفوع","paid_amount":450,"total_price":450}), [])
check("جزئي + صفر يترفض",        bool(_payment_problems({"payment_status":"مدفوع جزئياً","paid_amount":0,"total_price":450})), True)
check("جزئي سليم يعدّي",          _payment_problems({"payment_status":"مدفوع جزئياً","paid_amount":200,"total_price":450}), [])
check("غير مدفوع + مبلغ يترفض",  bool(_payment_problems({"payment_status":"غير مدفوع","paid_amount":100,"total_price":450})), True)
check("مدفوع > الإجمالي يترفض",   bool(_payment_problems({"payment_status":"مدفوع","paid_amount":900,"total_price":450})), True)
check("إجمالي صفر مايشتكيش",      _payment_problems({"payment_status":"مدفوع","paid_amount":0,"total_price":0}), [])
check("غير مدفوع سليم",           _payment_problems({"payment_status":"غير مدفوع","paid_amount":0,"total_price":450}), [])

print("\n📅 التحقق من التاريخ في الاستيراد — ممنوع اختراع تواريخ")
check("تاريخ سليم يعدّي",     import_date_check("2026-08-12") is None, True)
check("2026/99/99 يترفض",    import_date_check("2026/99/99") is not None, True)
check("30 فبراير يترفض",     import_date_check("2026-02-30") is not None, True)
check("نص عربي يترفض",       import_date_check("كلام") is not None, True)
check("فاضي يترفض",          import_date_check("") is not None, True)
check("None يترفض",          import_date_check(None) is not None, True)
check("1899 خارج المدى",     import_date_check("1899-01-01") is not None, True)
check("صيغة يوم/شهر/سنة",    import_date_check("12/08/2026") is None, True)


print("\n📆 format_date_ar — دالة عرض ماينفعش توقّع صفحة")
check("تاريخ ISO",        format_date_ar("2026-08-12"), "12 أغسطس 2026")
check("ISO بوقت",        format_date_ar("2026-08-12T09:00:00"), "12 أغسطس 2026")
check("نص مش تاريخ",     format_date_ar("كلام"), "كلام")
check("فاضي",            format_date_ar(""), "")
check("None",            format_date_ar(None), "")
check("رقم (كان بيرمي)",  format_date_ar(999999999), "999999999")
check("dict (كان بيرمي)", format_date_ar({"a": 1}), "{'a': 1}")
check("list (كان بيرمي)", format_date_ar([1, 2]), "[1, 2]")

print("\n🧱 تحصين الدوال المجمِّعة — مدخل بايظ يتخطّى بدل ما يوقّع")
_ok_persons = [{"name": "أحمد", "labs": ["CBC — 400 جنيه", "D3 — 900 جنيه"]},
               {"name": "سارة", "labs": ["TSH — 300 جنيه"]}]
check("إجمالي سليم",       extra_persons_total(_ok_persons), 1600)
check("عدد التحاليل",      extra_persons_labs_count(_ok_persons), 3)
check("None في القائمة",   extra_persons_total([None] + _ok_persons), 1600)
check("labs=None",         extra_persons_total([{"name": "x", "labs": None}]), 0)
check("مش list خالص",      extra_persons_total("نص"), 0)
check("عدّاد مع None",      extra_persons_labs_count([None, {"labs": ["a"]}]), 1)
check("dump بيتخطّى None",  dump_extra_persons([None, {"name": "أحمد", "labs": []}]) != "", True)
check("لون مع dict",       isinstance(get_client_tag_color({"a": 1}), str), True)
check("لون مع نص معروف",   get_client_tag_color("🆕 عميل جديد"), "#3498DB")
check("_hash_records بلا list", _hash_records("نص") == _hash_records([]), True)
check("_hash_records مع None داخل", _hash_records([None]) == _hash_records([]), True)
check("_hash_records ثابت مع الترتيب",
      _hash_records([{"id": "a"}, {"id": "b"}]) == _hash_records([{"id": "b"}, {"id": "a"}]), True)
check("_hash_records حسّاس للمحتوى",
      _hash_records([{"id": "a"}]) != _hash_records([{"id": "a", "x": 1}]), True)

print("\n🔁 parse/dump — استقرار الذهاب والعودة")
_p1 = parse_extra_persons(dump_extra_persons(_ok_persons))
_p2 = parse_extra_persons(dump_extra_persons(_p1))
check("مستقر من التكرار الثاني", _p1 == _p2, True)
check("الأسماء محفوظة",         [p["name"] for p in _p1], ["أحمد", "سارة"])
check("التحاليل محفوظة",        _p1[0]["labs"], ["CBC — 400 جنيه", "D3 — 900 جنيه"])
check("الإجمالي بعد العودة",     extra_persons_total(_p1), 1600)


print("\n💵 format_money — الفلوس بلا كسور")
check("عدد صحيح كـ float",  format_money(450.0), "450 جنيه")
check("مفيش .0",            ".0" in format_money(450.0), False)
check("فاصلة الآلاف",       format_money(12500.0), "12,500 جنيه")
check("كسر بيتقرّب",         format_money(450.7), "451 جنيه")
check("صفر",                format_money(0), "0 جنيه")
check("نص مش رقم",          format_money("abc"), "0 جنيه")
check("None",               format_money(None), "0 جنيه")
check("سالب",               format_money(-100.0), "-100 جنيه")

print("\n📊 revenue — الملغية مستبعدة")
_vs = [{"status": "تمت", "total_price": 500, "labs_price_after": 400, "transport_fee": 100},
       {"status": "ملغية", "total_price": 900, "labs_price_after": 800, "transport_fee": 100},
       {"status": "مجدولة", "total_price": 300, "labs_price_after": 300, "transport_fee": 0}]
check("الملغية مستبعدة من revenue",       revenue(_vs), 800)
check("الملغية مستبعدة من labs_revenue",  labs_revenue(_vs), 700)
check("الملغية مستبعدة من transport",     transport_revenue(_vs), 100)
check("revenue = labs + transport",       revenue(_vs) == labs_revenue(_vs) + transport_revenue(_vs), True)
check("الملغية لوحدها = صفر",             revenue([_vs[1]]), 0)
check("قائمة فاضية",                      revenue([]), 0)
check("None في القائمة",                  revenue([None] + _vs), 800)
check("قيمة نصية بايظة",                  revenue([{"status": "تمت", "total_price": "x"}]), 0)


print("\n🧬 سلامة الاستخراج — مفيش تعريف محلي بيدوس على المستورد")
# ★ طفرة M35 كشفت الثغرة دي: لو حد عرّف دالة في app.py بنفس اسم واحدة
#   مستوردة من core، التعريف المحلي بيدوس عليها في صمت — والاختبارات
#   كلها تفضل خضرا لأنها بتختبر core مباشرة.
#   ده مش افتراضي: حصل فعلًا — جسم _payment_problems فضل ملزوق في app.py
#   بعد استخراج سابق (من غير سطر def) وعاش ككود ميت بعد return.
import ast as _ast2, os as _os2

_ROOT = _os2.path.dirname(_os2.path.abspath(__file__))
_app_src = open(_os2.path.join(_ROOT, "app.py"), encoding="utf-8").read()
_app_tree = _ast2.parse(_app_src)

_imported = set()
for _n in _app_tree.body:
    if isinstance(_n, _ast2.ImportFrom) and _n.module in ("core", "import_rules", "sync_guards"):
        _imported |= {a.asname or a.name for a in _n.names}
_defined = {n.name for n in _app_tree.body if isinstance(n, _ast2.FunctionDef)}

check("مفيش دالة مستوردة معرّفة محليًا كمان", sorted(_imported & _defined), [])
check("عدد المستورد من الوحدات > 20", len(_imported) > 20, True)

# كود ميت بعد return/continue/break
_dead = []
for _n in _ast2.walk(_app_tree):
    _b = getattr(_n, "body", None)
    if isinstance(_b, list):
        for _i, _s in enumerate(_b[:-1]):
            if isinstance(_s, (_ast2.Return, _ast2.Continue, _ast2.Break, _ast2.Raise)):
                _dead.append(_b[_i + 1].lineno)
                break
check("مفيش كود ميت بعد return", _dead, [])

# نفس الفحص على الوحدات
for _m in ("core.py", "import_rules.py", "sync_guards.py"):
    _t = _ast2.parse(open(_os2.path.join(_ROOT, _m), encoding="utf-8").read())
    _names = [n.name for n in _t.body if isinstance(n, _ast2.FunctionDef)]
    check(f"{_m}: مفيش دالة معرّفة مرتين", len(_names), len(set(_names)))

print("\n" + "═" * 60)
if _FAILS:
    print(f"❌ فشل {len(_FAILS)} اختبار: {', '.join(_FAILS)}")
    raise SystemExit(1)
print("✅ كل الاختبارات نجحت")
