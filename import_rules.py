# -*- coding: utf-8 -*-
"""
import_rules.py — قواعد التحقق من صفوف الاستيراد

الطبقة دي كانت مدفونة جوّه لوب في `import_from_excel` وسط نداءات `st.*`،
يعني **مستحيل تتختبر** — رغم إنها بتحمل كل إصلاحات جولات التقوية التلاتة
(التاريخ الفاسد، التحقق المالي، الأرقام السالبة، قصر القيم التصنيفية).

دلوقتي: دالة واحدة `validate_row()` — دخل صف، اطلع بصف منظّف + قائمة أسباب
رفض + قائمة ملاحظات. مفيش Streamlit، مفيش داتابيز، مفيش آثار جانبية.

الفلسفة الحاكمة:
    البرنامج **مايخترعش بيانات** عشان الاستيراد «ينجح».
    الصف اللي ماينفعش يتقرا بيترفض، والأدمن بيشوف السبب ورقم الصف.

الاستخدام:
    from import_rules import validate_row, ImportOptions
    rec, fatal, warns = validate_row(raw_record, ImportOptions(...))
    if fatal:  ...  # الصف مرفوض
"""
from dataclasses import dataclass
from datetime import datetime

from core import normalize_ar, canonicalize_geo, _payment_problems


# ── الحقول الرقمية ومدياتها المعقولة ────────────────────────────────────────
NUMERIC_FIELDS = ["labs_price_before", "labs_price_after", "transport_fee",
                  "total_price", "paid_amount", "age"]

TEXT_DEFAULTS = {"status": "مجدولة", "branch": "La Cite",
                 "payment_status": "غير مدفوع", "payment_method": "نقدي",
                 "age_unit": "سنة", "doctor_name": ""}

OPTIONAL_TEXT = ("address", "location_link", "selected_labs_text",
                 "notes", "city", "district")

MAX_AGE_YEARS = 130
DATE_MIN, DATE_MAX = "2000-01-01", "2100-12-31"


@dataclass
class ImportOptions:
    """القيم المسموحة للحقول التصنيفية — بتيجي من app.py عشان تفضل مصدر واحد."""
    status_options: tuple = ("مجدولة", "في الطريق", "تمت", "ملغية")
    payment_options: tuple = ("غير مدفوع", "مدفوع جزئياً", "مدفوع")
    age_units: tuple = ("سنة", "شهر")
    branches: tuple = ("La Cite", "Diamond")

    def categorical(self):
        return (
            ("status",         self.status_options,  "مجدولة"),
            ("payment_status", self.payment_options, "غير مدفوع"),
            ("age_unit",       self.age_units,       "سنة"),
            ("branch",         self.branches,        "La Cite"),
        )


def parse_date(raw):
    """
    بيرجّع (التاريخ بصيغة ISO، رسالة الخطأ). واحد منهم بس بيبقى مليان.

    ★★ بقّين اتصلّحوا هنا:

    ① اختراع التواريخ — الكود القديم كان بيعمل:
           except: record["visit_date"] = date.today().isoformat()
       يعني تاريخ فاسد («2026/99/99» أو خلية فاضية) مابيتـرفضش — بيتحوّل
       لتاريخ النهاردة. النتيجة: زيارة **مخترعة** بتدخل الملف الشهري الغلط،
       وتظهر في تقرير الشهر ده، وتتحسب في إيراده.

    ② ترتيب اليوم/الشهر — `pd.to_datetime` افتراضيًا **أمريكي** (شهر/يوم).
       إحنا بنكتب يوم/شهر. يعني «12/08/2026» كان بيتخزّن 8 ديسمبر بدل
       12 أغسطس. والأسوأ إن pandas بيرجع لـ dayfirst تلقائيًا لما اليوم > 12،
       فنفس العمود كان بيطلع بشهور مختلطة:
           05/03/2026 → 5 مايو    ❌
           25/03/2026 → 25 مارس   ✅
       `dayfirst=True` بيوحّد التفسير. الصيغة ISO مالهاش لبس فمابتتأثرش.
    """
    if raw is None or str(raw).strip() == "":
        return None, "التاريخ فاضي"
    txt = str(raw).strip()
    # ISO أولاً — مالهاش لبس ولا محتاجة تخمين
    try:
        iso = datetime.strptime(txt[:10], "%Y-%m-%d").strftime("%Y-%m-%d")
    except Exception:
        try:
            import pandas as pd
            parsed = pd.to_datetime(raw, errors="raise", dayfirst=True)
            if pd.isna(parsed):
                raise ValueError("NaT")
            iso = parsed.strftime("%Y-%m-%d")
        except Exception:
            # احتياطي بلا pandas — عشان الوحدة تفضل قابلة للاختبار لوحدها
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
                try:
                    iso = datetime.strptime(txt[:10], fmt).strftime("%Y-%m-%d")
                    break
                except Exception:
                    continue
            else:
                return None, f"تاريخ غير صالح ({txt[:24]})"
    # حارس المدى: تاريخ برّه النطاق ده خطأ إدخال مش زيارة
    if not (DATE_MIN <= iso <= DATE_MAX):
        return None, f"تاريخ خارج المدى ({iso})"
    return iso, None


def coerce_numbers(record):
    """
    بيحوّل الحقول الرقمية لأرقام ويرجّع قائمة الملاحظات.

    ★ الكود القديم كان بيحوّل أي قيمة فاسدة لـ 0 **في صمت** — يعني سعر سالب
      أو نص في خانة الفلوس كان بيعدّي من غير ما حد ياخد باله.
    """
    notes = []
    for key in NUMERIC_FIELDS:
        if key in record and record[key] is not None:
            raw = record[key]
            try:
                record[key] = float(str(raw).replace(",", "").strip()) if isinstance(raw, str) else float(raw)
            except Exception:
                notes.append(f"{key}={raw!r} مش رقم")
                record[key] = 0
            else:
                if record[key] < 0:
                    notes.append(f"{key} سالب ({record[key]:g})")
                    record[key] = 0
        elif key not in record:
            record[key] = 0
    # السن: 0 مقبول (مش مسجّل)، لكن قيمة خيالية ملاحظة
    if record.get("age_unit", "سنة") == "سنة" and record.get("age", 0) > MAX_AGE_YEARS:
        notes.append(f"سن غير منطقي ({record['age']:g} سنة)")
    return notes


def restrict_categoricals(record, opts):
    """
    بيقصر الحقول التصنيفية على القيم المسموحة.

    ★ قبل كده الاستيراد كان بيقبل **أي نص** في status و payment_status.
      عمود إكسيل فيه «Done» أو وسم HTML كان بيدخل الداتابيز كما هو، والفلاتر
      والـ KPIs بتفوّت السجل لأنها بتقارن بالقيم العربية بالظبط.

    فرق إملائي → يتصلّح بهدوء. قيمة غريبة → ترجع للافتراضي **مع ملاحظة**.
    """
    notes = []
    for fld, allowed, default in opts.categorical():
        val = str(record.get(fld) or "").strip()
        if not val:
            record[fld] = default
            continue
        if val in allowed:
            continue
        match = next((o for o in allowed if normalize_ar(o) == normalize_ar(val)), None)
        if match:
            record[fld] = match
        else:
            notes.append(f"{fld}=«{val[:20]}» مش من القيم المسموحة → {default}")
            record[fld] = default
    return notes


def fill_insert_defaults(record):
    """
    بيملا الحقول النصية الاختيارية بـ "" — **للإدراج بس**.

    ⚠️ ممنوع تتنادى قبل ما تتأكد إن الصف جديد فعلاً. الصف الموجود لازم
    الحقول الغايبة تفضل **غايبة**، عشان `_keep()` في `update_visit` يحافظ
    على القيمة المحفوظة. لو ملّيناها "" هنمسح عنوان/ملاحظات زيارة قديمة
    لمجرد إن ملف الإكسيل مافيهوش العمود ده.
    """
    record = dict(record)
    for key in OPTIONAL_TEXT:
        if record.get(key) is None:
            record[key] = ""
    return record


def validate_row(record, opts=None):
    """
    بيرجّع (record, fatal, warnings).

    • fatal مليان   → الصف **مايتحفظش**، والسبب بيتعرض للأدمن برقم الصف.
    • warnings مليان → الصف بيتحفظ، بس بملاحظة ظاهرة.

    ملحوظة: الدالة دي **مابتملاش** الحقول النصية الاختيارية. ده مقصود —
    قرار الإدراج مقابل التحديث بيتاخد بعد كشف التكرار (اللي محتاج التاريخ
    منظّف الأول)، فالملء بيحصل بعده عبر `fill_insert_defaults()`.
    """
    opts = opts or ImportOptions()
    record = dict(record or {})
    warnings = []

    warnings += coerce_numbers(record)

    for key, default in TEXT_DEFAULTS.items():
        if record.get(key) is None:
            record[key] = default

    warnings += restrict_categoricals(record, opts)

    iso, date_err = parse_date(record.get("visit_date"))
    if iso:
        record["visit_date"] = iso

    if record.get("visit_time") is None:
        record["visit_time"] = ""

    # تطبيع جغرافي — يمنع «الحي/الحى» من تكوين تصنيفات وهمية
    for geo in ("city", "district"):
        if record.get(geo):
            record[geo] = canonicalize_geo(record[geo])

    if not record.get("total_price"):
        record["total_price"] = record.get("labs_price_after", 0) + record.get("transport_fee", 0)

    warnings += _payment_problems(record)

    fatal = []
    if not str(record.get("name") or "").strip():
        fatal.append("الاسم فاضي")
    if not str(record.get("phone") or "").strip():
        fatal.append("التليفون فاضي")
    if date_err:
        fatal.append(date_err)

    return record, fatal, warnings
