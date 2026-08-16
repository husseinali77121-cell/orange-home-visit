# tests_import.py — اختبارات قواعد الاستيراد
# التشغيل:  python3 tests_import.py
#
# المنطق ده كان مدفون جوّه import_from_excel وسط نداءات st.* — مستحيل يتختبر.
# دلوقتي كل قاعدة ليها اختبار، ومعاها اختبار **الانحدار العكسي**: يعني نتأكد
# إن السلوك القديم الغلط مابقاش موجود، مش بس إن الجديد شغّال.

from import_rules import (
    validate_row, fill_insert_defaults, parse_date,
    coerce_numbers, restrict_categoricals, ImportOptions,
)

_FAILS = []
OPTS = ImportOptions()


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


def row(**kw):
    base = {"name": "حسين علي", "phone": "01016872801", "visit_date": "2026-08-12"}
    base.update(kw)
    return base


# ══════════════════════════════════════════════════════════════════════════════
print("\n📅 parse_date — ممنوع اختراع تواريخ")
for raw, ok in [("2026-08-12", True), ("12/08/2026", True), ("2026/08/12", True),
                ("2026-08-12 09:30", True),
                ("2026/99/99", False), ("2026-02-30", False), ("", False),
                (None, False), ("كلام", False), ("1899-01-01", False),
                ("2200-01-01", False), ("   ", False)]:
    iso, err = parse_date(raw)
    check(f"«{raw}» {'يُقبل' if ok else 'يُرفض'}", (err is None), ok)
check("الناتج ISO",              parse_date("12/08/2026")[0], "2026-08-12")

print("\n🗓️ ترتيب اليوم/الشهر — pandas افتراضيًا أمريكي")
check("12/08 = 12 أغسطس",       parse_date("12/08/2026")[0], "2026-08-12")
check("05/03 = 5 مارس",         parse_date("05/03/2026")[0], "2026-03-05")
check("12/03 = 12 مارس",        parse_date("12/03/2026")[0], "2026-03-12")
check("25/03 = 25 مارس",        parse_date("25/03/2026")[0], "2026-03-25")
check("31/12 = 31 ديسمبر",      parse_date("31/12/2026")[0], "2026-12-31")
check("12-08-2026 بشرطة",       parse_date("12-08-2026")[0], "2026-08-12")
check("ISO مش بيتأثر",           parse_date("2026-08-12")[0], "2026-08-12")
check("ISO بوقت",                parse_date("2026-08-12 09:30")[0], "2026-08-12")
check("مفيش تفسير مختلط",
      [parse_date(f"{d:02d}/03/2026")[0] for d in (5, 12, 25)],
      ["2026-03-05", "2026-03-12", "2026-03-25"])
check("سبب الرفض واضح",          "غير صالح" in (parse_date("كلام")[1] or ""), True)
check("سبب الفراغ واضح",         parse_date("")[1], "التاريخ فاضي")

print("\n🚫 الانحدار العكسي — البق القديم مابقاش موجود")
_r, _f, _w = validate_row(row(visit_date="2026/99/99"), OPTS)
check("تاريخ فاسد يرفض الصف",     bool(_f), True)
check("مابقاش يتحوّل لتاريخ النهاردة",
      _r.get("visit_date") == "2026/99/99", True)   # القيمة الخام زي ما هي، مش today
_r2, _f2, _ = validate_row(row(visit_date=""), OPTS)
check("تاريخ فاضي يرفض الصف",     "التاريخ فاضي" in " ".join(_f2), True)

print("\n🔢 coerce_numbers — الأرقام الفاسدة مش بتعدّي في صمت")
r = {"total_price": "1,200"}
n = coerce_numbers(r)
check("الفاصلة تتقرا",            r["total_price"], 1200.0)
check("مفيش ملاحظة للسليم",       n, [])
r = {"total_price": "خمسمية"}
n = coerce_numbers(r)
check("نص في خانة فلوس → 0",     r["total_price"], 0)
check("مع ملاحظة",                len(n) > 0, True)
r = {"transport_fee": -50}
n = coerce_numbers(r)
check("سعر سالب → 0",            r["transport_fee"], 0)
check("مع ملاحظة",                "سالب" in " ".join(n), True)
r = {"age": 900, "age_unit": "سنة"}
n = coerce_numbers(r)
check("سن 900 يرفع ملاحظة",       "سن غير منطقي" in " ".join(n), True)
r = {"age": 6, "age_unit": "شهر"}
check("6 شهور مفيش ملاحظة",       coerce_numbers(r), [])
r = {}
coerce_numbers(r)
check("الحقول الناقصة = 0",       r["total_price"], 0)

print("\n🏷️ restrict_categoricals — القيم الغريبة مابتدخلش الداتابيز")
r = {"status": "Done"}
n = restrict_categoricals(r, OPTS)
check("«Done» → مجدولة",          r["status"], "مجدولة")
check("مع ملاحظة",                len(n) > 0, True)
r = {"status": "<img onerror=x>"}
restrict_categoricals(r, OPTS)
check("وسم HTML → مجدولة",        r["status"], "مجدولة")
r = {"status": "تمت"}
check("القيمة السليمة تعدّي",      (restrict_categoricals(r, OPTS), r["status"]), ([], "تمت"))
r = {"payment_status": "مدفوع جزئيا"}   # من غير ألف مقصورة
n = restrict_categoricals(r, OPTS)
check("فرق إملائي يتصلّح بهدوء",   (r["payment_status"], n), ("مدفوع جزئياً", []))
r = {"branch": "la cite"}
restrict_categoricals(r, OPTS)
check("فرع بحالة أحرف مختلفة",     r["branch"] in ("La Cite",), True)
r = {"status": ""}
restrict_categoricals(r, OPTS)
check("الفاضي → الافتراضي",        r["status"], "مجدولة")

print("\n💳 التحقق المالي داخل الاستيراد")
_r, _f, _w = validate_row(row(payment_status="مدفوع", paid_amount=0, total_price=500), OPTS)
check("«مدفوع» بصفر = ملاحظة",     len(_w) > 0, True)
check("لكن الصف بيتحفظ",           _f, [])
_r, _f, _w = validate_row(row(payment_status="مدفوع", paid_amount=500, total_price=500), OPTS)
check("الدفع السليم بلا ملاحظة",    _w, [])
_r, _f, _w = validate_row(row(payment_status="غير مدفوع", paid_amount=200, total_price=500), OPTS)
check("«غير مدفوع» بمبلغ = ملاحظة", len(_w) > 0, True)

print("\n🗺️ التطبيع الجغرافي")
_r, _, _ = validate_row(row(district="الحى الثامن"), OPTS)
check("الحى → الحي",              _r["district"], "الحي الثامن")
_r, _, _ = validate_row(row(city="6اكتوبر"), OPTS)
check("6اكتوبر → 6 أكتوبر",       _r["city"], "6 أكتوبر")
_r, _, _ = validate_row(row(district="حدايق الاهرام"), OPTS)
check("الإملاء مايتشوّهش",         _r["district"], "حدائق الأهرام")
_r, _, _ = validate_row(row(district="كمبوند جديد"), OPTS)
check("منطقة جديدة زي ما هي",      _r["district"], "كمبوند جديد")

print("\n⛔ أسباب الرفض")
check("الاسم فاضي",   validate_row(row(name=""), OPTS)[1], ["الاسم فاضي"])
check("التليفون فاضي", validate_row(row(phone=""), OPTS)[1], ["التليفون فاضي"])
check("الاتنين مع بعض",
      validate_row(row(name="", phone=""), OPTS)[1], ["الاسم فاضي", "التليفون فاضي"])
check("مسافات مش اسم", validate_row(row(name="   "), OPTS)[1], ["الاسم فاضي"])
check("الصف السليم يعدّي", validate_row(row(), OPTS)[1], [])

print("\n🛡️ fill_insert_defaults — الحماية من مسح البيانات")
r_upd, _, _ = validate_row(row(), OPTS)
check("التحديث: address تفضل غايبة", "address" in r_upd, False)
check("التحديث: notes تفضل غايبة",   "notes" in r_upd, False)
r_ins = fill_insert_defaults(r_upd)
check("الإدراج: address = ''",       r_ins["address"], "")
check("الإدراج: notes = ''",         r_ins["notes"], "")
check("مابتعدّلش الأصل",             "address" in r_upd, False)
r_has = fill_insert_defaults({"address": "عمارة 5"})
check("القيمة الموجودة ماتتغيّرش",    r_has["address"], "عمارة 5")

print("\n🧮 حساب الإجمالي")
_r, _, _ = validate_row(row(labs_price_after=400, transport_fee=100), OPTS)
check("الإجمالي الناقص يتحسب",     _r["total_price"], 500)
_r, _, _ = validate_row(row(labs_price_after=400, transport_fee=100, total_price=450), OPTS)
check("الإجمالي الموجود ما يتغيّرش", _r["total_price"], 450.0)

print("\n🧪 مدخلات عدائية — ماينفعش الوحدة تنهار")
hostile = [None, "", {}, {"name": None}, {"visit_date": ["x"]}, {"total_price": object()},
           {"name": "<script>", "phone": "'; DROP TABLE visits;--", "visit_date": "\x00"},
           {"age": float("inf")}, {"paid_amount": float("nan")},
           {"name": "😀" * 60, "phone": "0" * 200, "visit_date": "2026-08-12"}]
crashed = []
for h in hostile:
    try:
        validate_row(h, OPTS)
    except Exception as e:
        crashed.append((repr(h)[:34], type(e).__name__, str(e)[:40]))
check(f"{len(hostile)} مدخل عدائي بلا انهيار", crashed, [])

print("\n🔒 ثبات — الدالة مابتعدّلش المدخل")
orig = row(district="الحى الثامن", total_price="1,200")
snapshot = dict(orig)
validate_row(orig, OPTS)
check("المدخل الأصلي ماتغيّرش", orig, snapshot)

print("\n🔁 تكرار التشغيل يدّي نفس النتيجة")
a, fa, wa = validate_row(row(district="الحى الثامن", status="Done"), OPTS)
b, fb, wb = validate_row(a, OPTS)
check("idempotent (السجل)",    {k: v for k, v in b.items() if k in a}, a)
check("idempotent (الرفض)",    fb, fa)
check("الملاحظة مابتتكررش",     len(wb) <= len(wa), True)

print("\n" + "═" * 60)
if _FAILS:
    print(f"❌ فشل {len(_FAILS)} اختبار: {', '.join(_FAILS[:6])}")
    raise SystemExit(1)
print("✅ كل الاختبارات نجحت")
