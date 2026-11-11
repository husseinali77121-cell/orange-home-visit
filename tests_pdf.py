# -*- coding: utf-8 -*-
"""
tests_pdf.py — تصدير PDF (pdf_export.py)

  ① تشكيل الحروف العربية (أول/وسط/آخر/منفصل + لام ألف)
  ② ترتيب العرض (أرقام وإنجليزي جوّه الكلام العربي)
  ③ الملف: A4 بالعرض، ملء كامل من غير حواف، الأرقام والإجماليات صح
  ④ توزيع الصفحات: شهر عادي في صفحة، تصدير كبير على صفحات متوازنة

التشغيل:  python3 tests_pdf.py
"""
import io
import os
import sys
import unicodedata

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import pdf_export as pe

_FAILS = []


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


# ══════════════════════════════════════════════════════════════════════════════
print("\n① تشكيل الحروف")
check("لا → حرف واحد", pe.shape_ar("لا"), "ﻻ")
check("كلا → لام ألف موصولة من قبلها", pe.shape_ar("كلا"), "ﻛﻼ")
check("سلام: أول / وسط-لام ألف / آخر", pe.shape_ar("سلام"), "ﺳﻼﻡ")
check("بيت: أول / وسط / آخر", pe.shape_ar("بيت"), "ﺑﻴﺖ")
check("دار: د وا مابيتوصلوش باللي بعدهم", pe.shape_ar("دار"), "ﺩﺍﺭ")
check("مسافة بتقطع التوصيل", pe.shape_ar("ب ب"), "ﺏ ﺏ")
check("التشكيل بيتشال", pe.shape_ar("مَحمّد"), pe.shape_ar("محمد"))
check("إنجليزي وأرقام زي ما هم", pe.shape_ar("CBC 400"), "CBC 400")


def vis(s):
    """ترتيب العرض بعد فك أشكال الحروف — عشان المقارنة تبقى مقروءة."""
    return unicodedata.normalize("NFKC", pe._visual(pe.shape_ar(s)))


print("\n② ترتيب العرض")
check("عربي بس → معكوس للرسم", vis("جنيه"), "هينج")
check("إنجليزي بس → زي ما هو", vis("Developed by Dr. Hussein Ali"), "Developed by Dr. Hussein Ali")
check("سطر بيبدأ بإنجليزي → اتجاهه شمال→يمين", vis("TSH — 330 جنيه"), "TSH — 330 هينج")
check("سطر بيبدأ بعربي → يمين→شمال", vis("جنيه 330"), "330 هينج")
check("تليفون دولي: + في مكانها", vis("+96590888806"), "+96590888806")
check("سعر بفاصلة آلاف", vis("53,630 ج"), "ج 53,630")
check("تاريخ ISO سليم", vis("2026-10-04"), "2026-10-04")
check("رقم تليفون سليم", vis("01156644842"), "01156644842")
check("الأقواس بتتعكس في العربي", vis("(الزوج)"), "(جوزلا)")
check("رقم جوّه كلام عربي", vis("عمارة 74"), "74 ةرامع")


def wrapped(text, width):
    from reportlab.pdfbase.pdfmetrics import stringWidth  # noqa: F401
    fr, _fb, cmap = pe._fonts()
    ls = pe._wrap(pe._prep(text, cmap), fr, 7, width)
    return [unicodedata.normalize("NFKC", pe._visual_span(*x)) for x in ls]


print("\n②ب السطور الملفوفة")
labs = " • ".join(pe._keep(x) for x in ["CBC", "Urine Examination", "Urea", "Creatinine (Serum)",
                                        "Uric Acid", "Vitamin D3(25 Hydroxy Cholecal.)"])
L = wrapped(labs, 120)
check("التحاليل اتلفّت على أكتر من سطر", len(L) > 1, True)
check("القوس في آخر السطر مابيتعكسش ولا بيتنقل", all(x.count("(") == x.count(")") for x in L), True)
check("كل سطر بيبدأ بتحليل مش بفاصل", all(not x.strip().startswith("•") for x in L), True)
check("مفيش تحليل اتقسم على سطرين", any("Creatinine (Serum)" in x for x in L), True)
L2 = wrapped("مريم احمد — 20 سنة (الابنة): " + labs, 140)
check("حالة إضافية: اسمها العربي يمين أول سطر", L2[0].rstrip().endswith(
      unicodedata.normalize("NFKC", pe._visual(pe.shape_ar("مريم")))), True)

print("\n②ج أسعار التحاليل جوّه المربعات")
check("سعر التحليل بيتشال", pe._item("Vitamin D3(25 Hydroxy Cholecal.) — 1000 جنيه"),
      "Vitamin D3(25 Hydroxy Cholecal.)")
check("اسم فيه شرطة مابيتأثرش", pe._item("HOMA1-IR — 550 جنيه"), "HOMA1-IR")
check("روشتة بشرطة عادية", pe._item("روشتة - 6000"), "روشتة")
check("من غير سعر = زي ما هو", pe._item("Lipid profile"), "Lipid profile")
check("الحالات الإضافية: السن بيفضل والأسعار تتشال",
      pe._cell_text({"extra_persons_text": "هدى — 35 سنة: HbA1C — 400 جنيه • CBC — 400 جنيه"},
                    "extra_persons_text").replace(pe._NBSP, " "), "هدى — 35 سنة:\nHbA1C • CBC")

# ══════════════════════════════════════════════════════════════════════════════
import pdfplumber


def visit(i, **over):
    v = {"id": f"v{i}", "name": f"عميل رقم {i}", "phone": f"0100000{i:04d}",
         "visit_date": f"2026-10-{(i % 28) + 1:02d}", "visit_time": "10:00 AM",
         "doctor_name": "حسين علي" if i % 3 else "محمد شفيق", "branch": "La Cite",
         "address": "الحي الثامن - مجاورة 2 - عمارة 74 - الدور 2 - شقة 6",
         "selected_labs_text": "CBC — 400 جنيه\nFerritin — 400 جنيه\nTSH — 330 جنيه",
         "extra_persons_text": "", "labs_price_before": 1130, "labs_price_after": 1000,
         "transport_fee": 100, "total_price": 1100, "status": "تمت"}
    v.update(over)
    return v


def pages_of(b):
    with pdfplumber.open(io.BytesIO(b)) as pdf:
        out = []
        for pg in pdf.pages:
            r = pg.rects
            out.append({
                "w": round(pg.width, 1), "h": round(pg.height, 1),
                "W": round(pg.width, 2), "H": round(pg.height, 2),
                "edges": (round(min(x["x0"] for x in r), 2), round(max(x["x1"] for x in r), 2),
                          round(min(x["top"] for x in r), 2), round(max(x["bottom"] for x in r), 2)),
                "text": unicodedata.normalize("NFKC", pg.extract_text() or ""),
            })
        return out


print("\n③ الملف")
vs = [visit(i) for i in range(22)]
vs[5]["status"] = "ملغية"
vs[7]["extra_persons_text"] = "نجوي احمد — 74 سنة: HbA1C — 400 جنيه • Lipid profile — 700 جنيه"
b = pe.build_visits_pdf(vs, "فرع La Cite", "2026-10-01 → 2026-10-27", "2026-10-27")
P = pages_of(b)
check("بيبدأ بـ %PDF", b[:4], b"%PDF")
check("صفحة واحدة لشهر عادي (22 زيارة)", len(P), 1)
check("A4 بالعرض", (P[0]["w"], P[0]["h"]), (841.9, 595.3))
check("19 زيارة تقيلة في صفحة واحدة", len(pages_of(pe.build_visits_pdf(
    [visit(i, selected_labs_text="\n".join(f"Test number {k} — {100 + k} جنيه" for k in range(9)),
           extra_persons_text=("حالة — 30 سنة: " + " • ".join(f"Lab {k} — 200 جنيه" for k in range(8)))
           if i % 6 == 0 else "") for i in range(19)], "x", "y", "z"))), 1)
check("ملء كامل: البلوكات لازقة في الحواف الأربعة",
      P[0]["edges"], (0.0, P[0]["W"], 0.0, P[0]["H"]))
txt = P[0]["text"]
check("إجمالي الأسعار قبل الخصم (كل الصفوف زي إكسيل)", "24,860" in txt, True)
check("إجمالي بعد الخصم", "22,000" in txt, True)
check("إجمالي بدل الانتقال", "2,200" in txt, True)
check("الإجمالي الكلي", "24,200" in txt, True)
check("ملخص الأطباء: بدل 5% من غير الملغية (21 × 1000 × 5%)", "1,050" in txt, True)
check("التليفون في سطر واحد", "01000000003" in txt, True)
check("التوقيع", "Developed by Dr. Hussein Ali" in txt, True)
check("عمود حالات إضافية موجود لما فيه بيانات", "HbA1C" in txt, True)

vs2 = [visit(i) for i in range(5)]
P2 = pages_of(pe.build_visits_pdf(vs2, "فرع La Cite", "x", "y"))
check("مفيش حالات إضافية → العمود بيتشال", unicodedata.normalize("NFKC", pe.shape_ar("إضافية"))
      in P2[0]["text"], False)
check("عدد قليل: لسه ملء كامل للصفحة", P2[0]["edges"][1:], (P2[0]["W"], 0.0, P2[0]["H"]))
check("عدد قليل: الخط بيكبر", pe.LAST_INFO["font"] > 9, True)

check("إيموجي في البيانات مابيكسرش الملف",
      pages_of(pe.build_visits_pdf([visit(1, name="أحمد 🟠😀")], "x", "y", "z"))[0]["w"], 841.9)
check("قيم فاضية / None", len(pages_of(pe.build_visits_pdf(
    [visit(1, address=None, selected_labs_text=None, total_price=None, status=None)], "x", "y", "z"))), 1)

print("\n③ب ملخص الأطباء مابيتمطّش")
few = [visit(i) for i in range(3)]
pe.build_visits_pdf(few, "x", "y", "z")
with pdfplumber.open(io.BytesIO(pe.build_visits_pdf(few, "x", "y", "z"))) as pdf:
    pg = pdf.pages[0]
    words = pg.extract_words()
    # صفوف ملخص الأطباء = المستطيلات البيضا/الرمادي بعرض الصفحة تحت عنوان الملخص
    rects = sorted({(round(r["top"], 1), round(r["bottom"], 1)) for r in pg.rects
                    if r.get("non_stroking_color") in ((1, 1, 1), [1, 1, 1], (0.96, 0.96, 0.96))
                    and r["width"] > pg.width * 0.9})
    hs = [b_ - a_ for a_, b_ in rects]
check("صفوف الأطباء بارتفاع طبيعي (مش متمطّة)", bool(hs) and max(hs) < 30, True)

print("\n④ الصفحات")
big = [visit(i) for i in range(160)]
b3 = pe.build_visits_pdf(big, "كل الفروع", "x", "y")
P3 = pages_of(b3)
check("تصدير كبير على أكتر من صفحة", len(P3) > 1, True)
check("كل الصفحات A4 ملء كامل", all(p["edges"] == (0.0, p["W"], 0.0, p["H"])
                                     for p in P3), True)
check("رقم الصفحة في العنوان", unicodedata.normalize("NFKC", pe._visual(pe.shape_ar(f"صفحة 1 من {len(P3)}")))
      .replace(" ", "") in P3[0]["text"].replace(" ", ""), True)
n_rows = [p["text"].count("0100000") for p in P3]
check("كل الزيارات موجودة", sum(n_rows), 160)
check("توزيع متوازن (الفرق بين الصفحات صغير)", max(n_rows) - min(n_rows) <= max(6, max(n_rows) // 3), True)
check("ملخص الأطباء في آخر صفحة بس",
      [unicodedata.normalize("NFKC", pe._visual(pe.shape_ar("ملخص الأطباء"))) in p["text"] for p in P3][-1], True)

print()
if _FAILS:
    print(f"❌ فشل {len(_FAILS)}: {_FAILS}")
    sys.exit(1)
print("✅ كل اختبارات الـ PDF نجحت")
