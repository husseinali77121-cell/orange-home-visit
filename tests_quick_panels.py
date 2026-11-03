# -*- coding: utf-8 -*-
"""
tests_quick_panels.py — اختبارات الإضافات الجديدة:
  ① رسائل الواتساب من غير سعر بجوار كل تحليل (والإجمالي/بعد الخصم زي ما هم)
  ② Quick Panels بأسعارها + حماية الدفع مرتين
  ③ خانة اللصق (parse + resolve + add)
  ④ تنفيذ فعلي لصفحة «زيارة جديدة» مع ضغط زرار panel وزرار «أضف المختار»

التشغيل:  python3 tests_quick_panels.py
"""
import os
import sys
import shutil
import tempfile
import importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import lab_picker as lp
import quick_panels as qp
from core import _lab_price
from labs_price_list import LABS_DB

ALL = [{"name": t["name"], "price": t["price"], "category": c,
        "result_days": t.get("result_days"), "collection_notes": t.get("collection_notes")}
       for c, ts in LABS_DB.items() for t in ts]
IDX = qp.build_index(ALL)
_FAILS = []


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


# ── ① اسم التحليل من غير سعر (للعرض في الرسائل بس) — بيتنفذ بعد تحميل app.py تحت ──
DISPLAY_CASES = [
    ("CBC — 400 جنيه", "CBC"),
    ("HbA1C — 350 جنيه", "HbA1C"),
    ("CBC - 1,200 جنيه", "CBC"),
    ("Hba1c- 400", "Hba1c"),
    ("CBC", "CBC"),
    ("CA 15-3 — 600 جنيه", "CA 15-3"),
    ("17-OH progesterone — 700 جنيه", "17-OH progesterone"),
    ("Vitamin D3(25 Hydroxy Cholecal.) — 1000 جنيه", "Vitamin D3(25 Hydroxy Cholecal.)"),
    ("Test — Special — 300 جنيه", "Test — Special"),
    ("", ""),
]
check("السطر المخزّن لسه بيتحسب", _lab_price("CBC — 400 جنيه"), 400)

# ── ② Panels ────────────────────────────────────────────────────────────────
print("\n② Quick Panels")
check("كل الـ panels أسماؤها مطابقة لقايمة الأسعار", qp.validate_panels(IDX), {})
check("عدد الـ panels", len(qp.QUICK_PANELS) >= 27, True)

tgt = []
res = qp.add_labs(tgt, qp.panel_labs(IDX, "🔥 CRP + ESR"))
check("panel بيضيف بالسعر وبالصيغة المخزّنة", all(" — " in e and e.endswith(" جنيه") for e in tgt), True)
check("الإجمالي = مجموع أسعار القايمة الرسمية",
      sum(_lab_price(e) for e in tgt),
      sum(IDX[lp.norm(n)][0]["price"] for n in ("CRP", "ESR")))
check("المضاف", res["added"], ["CRP", "ESR"])

res = qp.add_labs(tgt, qp.panel_labs(IDX, "🔥 CRP + ESR"))
check("المكرر مابيتضافش", (res["added"], len(tgt)), ([], 2))

tgt = []
qp.add_labs(tgt, [qp.find_lab(IDX, "Lipid Profile")])
res = qp.add_labs(tgt, qp.panel_labs(IDX, "💉 Lipid Profile"))
check("مفرّق داخل باقة موجودة بيتخطى (مفيش دفع مرتين)", (res["added"], len(tgt), len(res["covered"])), ([], 1, 5))

tgt = []
qp.add_labs(tgt, qp.panel_labs(IDX, "💉 Lipid Profile"))
res = qp.add_labs(tgt, [qp.find_lab(IDX, "Lipid Profile")])
check("باقة بتغطي مفرّق موجود بتتأجل (مابتتضافش لوحدها)", (res["added"], res["deferred"], len(tgt)),
      ([], ["Lipid profile"], 5))
check("بوابة الازدواج الموجودة في الفورم لسه بتشوفها بعد إضافة الاتنين يدوي",
      bool(lp.find_conflicts(tgt + ["Lipid profile — 700 جنيه"])[0]), True)

lipid = qp.panel_bundle(IDX, "💉 Lipid Profile")
check("باقة الـ panel بتتلاقي", lipid["name"], "Lipid profile")
check("panel من غير باقة", qp.panel_bundle(IDX, "🩸 CBC"), None)

# ── ③ خانة اللصق ────────────────────────────────────────────────────────────
print("\n③ خانة اللصق")
check("أسماء + أسعار بشرطة", qp.parse_paste("CBC - 400\nHba1c- 400", ALL), ["CBC", "Hba1c"])
check("ترقيم وفواصل", qp.parse_paste("1- صورة دم كاملة\n2) سكر صائم\nفيتامين د، كرياتينين\nTSH + Ferritin", ALL),
      ["صورة دم كاملة", "سكر صائم", "فيتامين د", "كرياتينين", "TSH", "Ferritin"])
check("أسماء بتبدأ بأرقام/شرطة ماتتقصّش", qp.parse_paste("17-OH progesterone\nCA 15-3", ALL),
      ["17-OH progesterone", "CA 15-3"])
check("A/G Ratio ماتتقسمش", qp.parse_paste("A/G Ratio", ALL), ["A/G Ratio"])
check("CRP / ESR بتتقسم", qp.parse_paste("CRP / ESR", ALL), ["CRP", "ESR"])
check("تكرار", qp.parse_paste("CBC\ncbc\nCBC — 400 جنيه", ALL), ["CBC"])
check("أرقام بس", qp.parse_paste("400\n٣٠٠ جنيه\n---", ALL), [])
check("سعر بفاصلة آلاف", qp.parse_paste("CBC — 1,200 جنيه, ESR — 100 جنيه", ALL), ["CBC", "ESR"])

price_msg = """🍊 *معمل أورانج للتحاليل الطبية*
━━━━━━━━━━━━━━━
الاسم: *أحمد*
الطبيب: د. ماجد
التاريخ: 03-11-2026

1. CBC —
2. HbA1C —
3. Vitamin D3(25 Hydroxy Cholecal.) —
━━━━━━━━━━━━━━━
الإجمالي: 1,500 ج.م
*المطلوب: 1,200 ج.م*
⏱️ النتيجة خلال 1 يوم

*تعليمات العينة:*
• 1.0 ml Serum
شكراً لثقتكم 🍊"""
check("رسالة أسعار كاملة — التحاليل بس", qp.parse_paste(price_msg, ALL),
      ["CBC", "HbA1C", "Vitamin D3(25 Hydroxy Cholecal.)"])

conf, choose, missing = qp.resolve_tokens(ALL, ["CBC", "Hba1c", "سكر صائم", "دهون", "xyzabc"])
check("مؤكد", [(t, l["name"]) for t, l in conf],
      [("CBC", "CBC"), ("Hba1c", "HbA1C"), ("سكر صائم", "FBG")])
check("محتاج اختيار", [t for t, _, _ in choose], ["دهون"])
check("مش موجود", missing, ["xyzabc"])

# ── ④ تنفيذ فعلي للصفحة ─────────────────────────────────────────────────────
print("\n④ تنفيذ صفحة «زيارة جديدة» فعليًا")
import _stub_streamlit as stub

SECRETS = {"admin_password": "TestPass123",
           "allowed_emails": ["Hussein.ali77121@gmail.com"],
           "github_token": "", "github_repo": "", "github_branch": "main",
           "use_monthly_sync": False}


def run_app(page, buttons=(), state=None):
    """يستورد app.py بنفس طريقة tests_pages. يرجّع (app أو None, session_state, الاستثناء)."""
    workdir = tempfile.mkdtemp(prefix="hvms_qp_")
    cwd = os.getcwd()
    os.chdir(workdir)
    stub.reset()
    st = stub.install(SECRETS)
    st.session_state.update({
        "authenticated": True, "user_type": "admin", "user_email": "Hussein.ali77121@gmail.com",
        "page": page, "need_password": False, "_skip_auto_login": True,
        "current_page": 1, "page_size": 20, "total_visits": 0,
        "prefill": {}, "selected_id": None, "selected_client_phone": "", "search_q": "",
    })
    st.session_state.update(state or {})
    stub.BUTTON_TRUE.update(buttons)
    for m in ("app", "core", "import_rules", "phone_utils", "lab_picker", "quick_panels",
              "login_theme", "easter_eggs", "device_auth", "labs_price_list"):
        sys.modules.pop(m, None)
    app, err = None, None
    try:
        app = importlib.import_module("app")
    except (stub._Rerun, stub._Stop) as e:
        err = e
    finally:
        os.chdir(cwd)
        shutil.rmtree(workdir, ignore_errors=True)
    return app, st.session_state, err


# ضغط أول panel (CBC)
_, ss, err = run_app("new", buttons={"qp_new_visit__pnl_0"})
check("ضغطة panel → rerun", type(err).__name__, "_Rerun")
check("CBC اتضاف بسعره", ss.get("added_labs_new_visit"), ["CBC — 400 جنيه"])
check("رسالة النجاح متخزّنة للرن الجاي", [k for k, _ in ss.get("qp_new_visit__pnl_flash", [])], ["success"])

# باقة أوفر؟ (Lipid Profile: 700 مقابل 950) → بيسأل مش بيضيف
names = list(qp.QUICK_PANELS)
i_lipid = names.index("💉 Lipid Profile")
_, ss, err = run_app("new", buttons={f"qp_new_visit__pnl_{i_lipid}"})
check("panel ليه باقة أوفر → بيسأل الأول", (ss.get("qp_new_visit__pnl_pending"), ss.get("added_labs_new_visit")),
      ("💉 Lipid Profile", []))
_, ss, err = run_app("new", buttons={"qp_new_visit__pnl_bundle"},
                     state={"qp_new_visit__pnl_pending": "💉 Lipid Profile", "added_labs_new_visit": []})
check("اختيار الباقة", (ss.get("added_labs_new_visit"), ss.get("qp_new_visit__pnl_pending")),
      (["Lipid profile — 700 جنيه"], None))
_, ss, err = run_app("new", buttons={"qp_new_visit__pnl_split"},
                     state={"qp_new_visit__pnl_pending": "💉 Lipid Profile", "added_labs_new_visit": []})
check("اختيار المفرّق", (len(ss.get("added_labs_new_visit")), sum(_lab_price(e) for e in ss.get("added_labs_new_visit"))),
      (5, 950))

# خانة اللصق: إضافة المختار
cbc = IDX[lp.norm("CBC")][0]
a1c = IDX[lp.norm("HbA1C")][0]
bulk = {"confident": [("cbc", cbc), ("Hba1c", a1c)], "choose": [], "missing": [], "n": 1}
_, ss, err = run_app("new", buttons={"qpaste_new_visit__bk_add_1"},
                     state={"qpaste_new_visit__bulk": bulk, "added_labs_new_visit": []})
check("«أضف المختار» → التحاليل بأسعارها", ss.get("added_labs_new_visit"),
      ["CBC — 400 جنيه", f"HbA1C — {a1c['price']} جنيه"])
check("القايمة الملزوقة اتمسحت بعد الإضافة", ss.get("qpaste_new_visit__bulk"), None)

# الصفحة بتترسم من غير أخطاء (من غير ضغط أي زرار) — وبيظهر البانلز
app, ss, err = run_app("new")
check("صفحة «زيارة جديدة» اتنفذت للآخر", err is None or type(err).__name__ == "_Stop", True)
labels = [c[1][0] for c in stub.CALLS if c[0] == "button"]
check("أزرار الـ panels ظاهرة", "🩸 CBC" in labels and "💉 Lipid Profile" in labels, True)
css = " ".join(c[1][0] for c in stub.CALLS if c[0] == "markdown" and c[1] and "st-key-qpgrid" in str(c[1][0]))
check("مربعات الـ panels: 3 في الصف وما بتلفّش على الموبايل",
      ("flex-wrap:nowrap" in css, "min-width:0" in css), (True, True))
check("الـ panels في حاوية متعلّمة بـ key (CSS مش بيلمس باقي الصفحة)",
      any(c[0] == "container" and "qpgrid_qp_new_visit" in str(c[2].get("key", "")) for c in stub.CALLS)
      or "st-key-qpgrid_qp_new_visit" in css, True)

# ① الرسائل — من غير سعر بجوار كل تحليل
app, ss, err = run_app("home")
if app is None:
    check("استيراد app.py لاختبار الرسائل", repr(err), "None")
else:
    print("① اسم التحليل من غير سعر (_wa_lab_name)")
    for entry, want in DISPLAY_CASES:
        check(f"_wa_lab_name({entry!r})", app._wa_lab_name(entry), want)
    v = {"name": "أحمد", "phone": "01000000000", "visit_date": "2026-11-05", "visit_time": "10:00 AM",
         "doctor_name": "د. ماجد", "branch": "Diamond", "address": "الشيخ زايد", "status": "مجدولة",
         "selected_labs_text": "CBC — 400 جنيه\nHbA1C — 350 جنيه",
         "extra_persons": '[{"uid":"a1","name":"سارة","age":"30","age_unit":"سنة","relation":"","labs":["TSH — 300 جنيه"]}]',
         "labs_price_before": 1050, "labs_price_after": 900, "transport_fee": 100, "total_price": 1000}
    for target in ("client", "internal"):
        msg = app.make_whatsapp_msg(v, target)
        lines = msg.splitlines()
        check(f"[{target}] أسماء التحاليل من غير سعر",
              ("🧪 CBC" in lines, "🧪 HbA1C" in lines, "🧪 TSH" in lines), (True, True, True))
        check(f"[{target}] مفيش سعر تحليل جنب الاسم",
              any(("400 جنيه" in l or "350 جنيه" in l or "300 جنيه" in l) and l.startswith("🧪") for l in lines), False)
        check(f"[{target}] السعر قبل/بعد الخصم والإجمالي موجودين",
              ("السعر قبل الخصم:* 1050 جنيه" in msg, "السعر بعد الخصم:* 900 جنيه" in msg, "1000 جنيه" in msg),
              (True, True, True))

print()
if _FAILS:
    print(f"❌ {len(_FAILS)} اختبار فشل:")
    for f in _FAILS:
        print("   -", f)
    sys.exit(1)
print("✅ كل اختبارات الإضافات الجديدة نجحت")
