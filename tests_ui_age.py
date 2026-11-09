# -*- coding: utf-8 -*-
"""
tests_ui_age.py — المرحلة الأولى من الواجهة + تحديث العمر

  ① home_kpis (SQL) = _home_kpis_slow (الطريقة القديمة بالظبط) على بيانات عشوائية فيها كل الحالات الشاذة
  ② فشل SQL → رجوع تلقائي للطريقة القديمة (مفيش كراش)
  ③ كروت الأرقام (HTML) + الهيدر + شريحة المزامنة (حقيقية مش ثابتة)
  ④ refresh_age: سنة / شهر / حالات مش مفهومة / حدود
  ⑤ استدعاء بيانات عميل قديم (حي + أرشيف) بيحدّث العمر في الزيارة الجديدة، والقديمة ما بتتغيّرش

التشغيل:  python3 tests_ui_age.py
"""
import os
import sys
import json
import random
import sqlite3
import tempfile
import importlib
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _stub_streamlit as stub

_FAILS = []


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


NOGH = {"admin_password": "x", "allowed_emails": ["Hussein.ali77121@gmail.com", "Orangelab511@gmail.com"]}
USERS = {"admin": "Hussein.ali77121@gmail.com", "diamond": "Orangelab511@gmail.com", "lacite": "Hussein.ali77121@gmail.com"}


def run_app(page="home", user_type="admin", state=None, workdir=None, buttons=()):
    workdir = workdir or tempfile.mkdtemp(prefix="hvms_ui_")
    cwd = os.getcwd()
    os.chdir(workdir)
    stub.reset()
    st = stub.install(NOGH)
    st.session_state.update({
        "authenticated": True, "user_type": user_type, "user_email": USERS[user_type],
        "page": page, "need_password": False, "_skip_auto_login": True,
        "current_page": 1, "page_size": 20, "total_visits": 0,
        "prefill": {}, "selected_id": None, "selected_client_phone": "", "search_q": "",
    })
    st.session_state.update(state or {})
    stub.BUTTON_TRUE.update(buttons)
    for m in ("app", "core", "import_rules", "phone_utils", "lab_picker", "quick_panels", "doctors_sync",
              "email_backup", "login_theme", "easter_eggs", "device_auth", "labs_price_list"):
        sys.modules.pop(m, None)
    app, err = None, None
    try:
        app = importlib.import_module("app")
    except (stub._Rerun, stub._Stop) as e:
        err = e
        app = sys.modules.get("app")
    finally:
        os.chdir(cwd)
    return app, st.session_state, err, workdir


def md_all(kinds=("markdown",)):
    return " ".join(str(c[1][0]) for c in stub.CALLS if c[0] in kinds and c[1])


def rec(i, **kw):
    d = (date.today() - timedelta(days=random.randint(0, 200))).isoformat()
    r = {"id": f"k{i}", "created_at": d + "T10:00:00", "name": f"عميل {i}", "age": "30", "phone": f"0101000{i:04d}",
         "visit_date": d, "visit_time": "10:00 AM", "branch": "Diamond", "status": "تمت", "doctor_name": "حسين علي",
         "address": "x", "location_link": "", "selected_labs_text": "CBC — 400 جنيه", "notes": "",
         "labs_price_before": 400, "labs_price_after": 400, "transport_fee": 0, "total_price": 400,
         "payment_status": "غير مدفوع", "paid_amount": 0}
    r.update(kw)
    return r


# ── ① SQL = الطريقة القديمة ─────────────────────────────────────────────────
print("① home_kpis (SQL) مقابل الطريقة القديمة")
random.seed(7)
app, ss, err, wd = run_app("home")
conn = app.get_connection()
TODAY = date.today().isoformat()
STAT = ["مجدولة", "في الطريق", "تمت", "ملغية", None, "", "ملغيه", " ملغية ", "ملغي", "مُلغية", "cancelled", "ملغاة", "تم الإلغاء"]
PAY = ["غير مدفوع", "مدفوع جزئياً", "مدفوع", None, ""]
TOT = [0, 100, 450, 1250.5, None, "700", "abc", 0.0]
for i in range(1500):
    r = rec(i, branch=random.choice(["Diamond", "La Cite", "Diamond", ""]),
            status=random.choice(STAT), payment_status=random.choice(PAY),
            total_price=random.choice(TOT), paid_amount=random.choice([0, None, 50, 100, 450, 9999]),
            visit_date=random.choice([TODAY, TODAY, "2026-01-05", "2025-12-30", ""]))
    app._load_insert_visit(conn, r, upsert=False, archived=1 if i % 11 == 0 else 0)
    if i % 17 == 0:
        conn.execute("UPDATE visits SET deleted_at='2026-01-01' WHERE id=?", (r["id"],))
conn.commit()
ok_all = True
for br in (None, "Diamond", "La Cite"):
    fast, slow = app.home_kpis(br), app._home_kpis_slow(br)
    same = all(abs(fast[k] - slow[k]) < 1e-6 for k in slow)
    ok_all &= same
    check(f"فرع={br}: كل الأرقام متطابقة {fast['total']} زيارة", same, True)
    if not same:
        print("       fast:", fast, "\n       slow:", slow)
check("الأرقام مش كلها أصفار (البيانات فعلًا بتختبر حاجة)", app.home_kpis()["remaining"] > 0 and app.home_kpis()["unpaid"] > 0, True)
# مرجع يدوي صغير
conn.execute("DELETE FROM visits"); conn.commit()
for r in (rec(1, payment_status="غير مدفوع", total_price=500),
          rec(2, payment_status="مدفوع جزئياً", total_price=800, paid_amount=300),
          rec(3, payment_status="مدفوع", total_price=999, paid_amount=999),
          rec(4, payment_status="غير مدفوع", total_price=1000, status="ملغية"),
          rec(5, payment_status="مدفوع جزئياً", total_price=100, paid_amount=500, visit_date=TODAY, branch="La Cite")):
    app._load_insert_visit(conn, r, upsert=False)
conn.commit()
k = app.home_kpis()
check("متبقي = 500 + (800-300) + 0 + (ملغية:0) + (زيادة دفع:0)", k["remaining"], 1000.0)
check("غير المدفوع (بدون الملغية) = 1", k["unpaid"], 1)
check("الإيراد (بدون الملغية) = 500+800+999+100", k["revenue"], 2399.0)
check("اليوم / تمت / الإجمالي", (k["today"], k["done"], k["total"]), (1, 4, 5))
check("فلتر الفرع", (app.home_kpis("La Cite")["total"], app.home_kpis("Diamond")["total"]), (1, 4))

# ── ①ب الملغية بأي إملاء (المشكلة اللي اتبلّغ عنها: متبقي الملغية بيتحسب) ──────────
print("\n①ب الملغية بإملاء مختلف مابتتحسبش في المتبقي")
for r in (rec(11, payment_status="مدفوع جزئياً", total_price=1500, paid_amount=300, status="ملغيه"),     # ← 1200 متبقي لو اتحسبت غلط
          rec(12, payment_status="مدفوع جزئياً", total_price=700, paid_amount=100, status=" ملغية  "),
          rec(13, payment_status="غير مدفوع", total_price=400, status="ملغاة"),
          rec(14, payment_status="غير مدفوع", total_price=400, status="مُلغية"),
          rec(15, payment_status="غير مدفوع", total_price=400, status="Cancelled"),
          rec(16, payment_status="غير مدفوع", total_price=400, status="تم الالغاء")):
    app._load_insert_visit(conn, r, upsert=False)
conn.commit()
k2 = app.home_kpis()
check("المتبقي ماتغيّرش (1000) رغم 6 زيارات ملغية بإملاءات مختلفة", k2["remaining"], 1000.0)
check("غير المدفوع ماتغيّرش (1)", k2["unpaid"], 1)
check("الإيراد ماتغيّرش (2399)", k2["revenue"], 2399.0)
check("الطريقة القديمة (slow) نفس الرقم", app._home_kpis_slow()["remaining"], 1000.0)
for sv, want in (("ملغية", True), ("ملغيه", True), ("ملغي", True), ("ملغاة", True), (" ملغية ", True), ("مُلغيّة", True),
                 ("تم الإلغاء", True), ("الغاء", True), ("CANCELLED", True), ("ملغى", True),
                 ("تمت", False), ("مجدولة", False), ("في الطريق", False), ("", False), (None, False), ("مدفوع", False), (123, False)):
    check(f"_is_cancelled_status({sv!r}) = {want}", app._is_cancelled_status(sv), want)

items, odd, n_total = app.home_remaining_breakdown()
check("التفاصيل: الزيارات الداخلة في المتبقي (500 + 500 + زيادة الدفع مستبعدة)", (n_total, sorted(i["المتبقي"] for i in items)), (2, [500.0, 500.0]))
check("التفاصيل: مجموعها = رقم الكرت", sum(i["المتبقي"] for i in items), k2["remaining"])
check("التفاصيل: الحالات الشاذة اتكشفت وعليها علامة ملغية", odd.get("ملغيه"), (1, True))
check("التفاصيل: الحالات القياسية مش في قائمة الشاذ", any(x in odd for x in ("تمت", "ملغية", "مجدولة")), False)
check("التفاصيل بتحترم فلتر الفرع", app.home_remaining_breakdown("La Cite")[2], 0)

# ── ② فشل SQL ───────────────────────────────────────────────────────────────
print("\n② فشل الاستعلام → الطريقة القديمة")
real_get = app.get_connection


class Proxy:
    def __init__(self, c):
        self.c = c

    def execute(self, sql, *a):
        if "COALESCE(SUM" in sql:
            raise sqlite3.OperationalError("boom")
        return self.c.execute(sql, *a)

    def __getattr__(self, n):
        return getattr(self.c, n)


app.get_connection = lambda: Proxy(real_get())
check("بيرجع نفس الأرقام من غير كراش", app.home_kpis(), app._home_kpis_slow())
app.get_connection = real_get

# ── ③ الكروت والهيدر ────────────────────────────────────────────────────────
print("\n③ الكروت والهيدر وشريحة المزامنة")
html = app.home_kpi_cards_html({"remaining": 4500.0, "unpaid": 3, "done": 8, "today": 12, "total": 320, "revenue": 99000.0})
check("4 كروت بالعناوين", all(t in html for t in ("متبقي التحصيل", "زيارات مكتملة", "زيارات اليوم", "إجمالي الزيارات")), True)
check("الأرقام منسّقة", all(t in html for t in ("4,500", "320", "12", "99,000")), True)
check("شبكة موبايل عمودين / ديسكتوب 4", ("repeat(2,1fr)" in html, "min-width:640px" in html and "repeat(4,1fr)" in html), (True, True))
check("مفيش widgets ولا صور (HTML بس)", ("<img" in html, "<script" in html), (False, False))
check("حجم الكروت صغير", len(html.encode()) < 3000, True)

app.GITHUB_TOKEN, app.GITHUB_REPO = "", ""
check("من غير GitHub → محلي فقط", app._sync_chip()[2], "محلي فقط")
app.GITHUB_TOKEN, app.GITHUB_REPO = "t", "o/r"
app._BOOT = {"ok": True}
for g in ("conflict", "unsaved", "connected"):
    app._GH_STATE.pop(g, None)
check("كله تمام → متزامن", app._sync_chip()[:3:2], ("#27AE60", "متزامن مع GitHub"))
app._BOOT = {"ok": False}
check("الإقلاع فشل → مش أخضر", app._sync_chip()[1], "🟠")
app._BOOT = {"ok": True}
app._GH_STATE["connected"] = False
check("غير متصل → أحمر", app._sync_chip()[1], "🔴")
app._GH_STATE["connected"] = True
app._GH_STATE["unsaved"] = 2
check("تعديلات غير مرفوعة → أحمر بالعدد", ("2" in app._sync_chip()[2], app._sync_chip()[1]), (True, "🔴"))
app._GH_STATE["conflict"] = "visits/2026-11.json"
check("تعارض → برتقالي (له الأولوية)", app._sync_chip()[1], "🟠")

for ut, role in (("admin", "مدير النظام"), ("diamond", "فرع Diamond"), ("lacite", "فرع La Cite")):
    run_app("home", user_type=ut)
    m = md_all()
    check(f"{ut}: الهيدر + الدور + الكروت", ("oh-head" in m, role in m, "kpi-grid" in m), (True, True, True))
run_app("manage_doctors")
check("الهيدر ظاهر في باقي الصفحات", "oh-head" in md_all(), True)

# ── ④ refresh_age ───────────────────────────────────────────────────────────
print("\n④ refresh_age")
T = date(2026, 11, 9)
R = lambda a, u, d: app.refresh_age(a, u, d, T)
check("32 سنة قبل سنة بالظبط → 33", R("32", "سنة", "2025-11-09"), ("33", "سنة", True))
check("قبل 355 يوم → 33", R("32", "سنة", "2025-11-20")[:2], ("33", "سنة"))
check("قبل شهرين → لسه 32 (مالسّه ماعدّاش نص سنة)", R("32", "سنة", "2026-09-01"), ("32", "سنة", False))
check("قبل 298 يوم → 33 (الأرجح إن عيد الميلاد عدّى)", R("32", "سنة", "2026-01-15")[:2], ("33", "سنة"))
check("قبل سنتين → 34", R("32", "سنة", "2024-11-09")[0], "34")
check("أرقام عربية ٣٢ → 33", R("٣٢", "سنة", "2025-11-09")[0], "33")
check("عمر int مش نص", R(32, "سنة", "2025-11-09")[0], "33")
check("وحدة فاضية = سنة", R("32", "", "2025-11-09")[:2], ("33", "سنة"))
check("8 شهور قبل سنة → 20 شهر", R("8", "شهر", "2025-11-09"), ("20", "شهر", True))
check("20 شهر قبل سنة → 32 شهر = سنتين", R("20", "شهر", "2025-11-09")[:2], ("2", "سنة"))
check("شهور: اليوم أصغر من يوم الزيارة → شهر أقل", R("10", "شهر", "2026-09-20")[0], "11")
check("شهور: لسه ماكملش شهر → من غير تغيير", R("10", "شهر", "2026-10-20")[2], False)
for bad_age in ("", None, "abc", "32.5", "-3", " ", "inf", "nan", "1e999"):
    check(f"عمر غير صالح {bad_age!r} → زي ما هو", R(bad_age, "سنة", "2025-11-09"), (bad_age, "سنة", False))
for bad_date in ("", None, "bad", "2026-13-45", "2027-01-01"):
    check(f"تاريخ غير صالح/مستقبل {bad_date!r} → زي ما هو", R("32", "سنة", bad_date), ("32", "سنة", False))
check("وحدة غريبة → زي ما هي", R("32", "يوم", "2025-11-09"), ("32", "يوم", False))
check("حد 120: ماتتخطّاش", R("119", "سنة", "2021-11-09")[2], False)
check("تاريخ بصيغة datetime كامل", R("32", "سنة", "2025-11-09T10:00:00")[0], "33")
check("نفس اليوم → من غير تغيير", R("32", "سنة", "2026-11-09")[2], False)

pf = app.prefilled_age_fields({"age": "32", "age_unit": "سنة", "visit_date": "2025-11-09"})
check("prefilled_age_fields: العمر والملاحظة", (pf["age"], "32 سنة" in pf["age_note"], "33 سنة" in pf["age_note"], "راجعه" in pf["age_note"]), ("33", True, True, True))
pf0 = app.prefilled_age_fields({"age": "7", "age_unit": "سنة", "visit_date": "2026-11-01"})
check("من غير تغيير → نفس القيم بالظبط وبدون ملاحظة", pf0, {"age": "7", "age_unit": "سنة"})
check("زيارة من غير تاريخ → زي ما هي", app.prefilled_age_fields({"age": "9"}), {"age": "9", "age_unit": "سنة"})

ex = json.dumps([{"uid": "a", "name": "سارة", "age": "5", "age_unit": "سنة", "relation": "", "labs": ["TSH — 300 جنيه"]},
                 {"uid": "b", "name": "ليلى", "age": "10", "age_unit": "شهر", "relation": "", "labs": []},
                 {"uid": "c", "name": "بدون عمر", "age": "", "age_unit": "سنة", "labs": []}], ensure_ascii=False)
out = json.loads(app.refresh_extra_persons_ages(ex, "2025-11-09"))
check("الحالات الإضافية: الأعمار اتحدّثت", [(p["age"], p["age_unit"]) for p in out], [("6", "سنة"), ("22", "شهر"), ("", "سنة")])
check("الباقي ما اتلمسش (تحاليل/أسماء)", (out[0]["labs"], out[0]["name"], out[1]["uid"]), (["TSH — 300 جنيه"], "سارة", "b"))
check("الأسماء العربي مش متحوّلة لـ \\u", "سارة" in app.refresh_extra_persons_ages(ex, "2025-11-09"), True)
check("JSON بايظ → زي ما هو", app.refresh_extra_persons_ages("{bad", "2025-11-09"), "{bad")
check("مش list → زي ما هو", app.refresh_extra_persons_ages('{"a":1}', "2025-11-09"), '{"a":1}')
check("فاضي → فاضي", app.refresh_extra_persons_ages("", "2025-11-09"), "")

# ── ⑤ استدعاء عميل قديم (حي + أرشيف) ────────────────────────────────────────
print("\n⑤ استدعاء بيانات عميل قديم")
appA, _, _, wdA = run_app("home")
cA = appA.get_connection()
PH = "01012345678"
last_year = (date.today().replace(year=date.today().year - 1) - timedelta(days=3)).isoformat()   # قبل سنة وكام يوم
appA._ensure_archive_index_table(cA)
arch = rec(901, id="arch-1", phone=PH, age="32", age_unit="سنة", visit_date=last_year, name="مريض أرشيف",
           extra_persons=json.dumps([{"uid": "x", "name": "ابنه", "age": "5", "age_unit": "سنة", "labs": []}], ensure_ascii=False))
cA.execute("INSERT OR REPLACE INTO visits_archive (id,phone,visit_date,status,rec) VALUES (?,?,?,?,?)",
           (arch["id"], PH, last_year, "تمت", json.dumps(arch, ensure_ascii=False)))
cA.commit()
check("مفيش زيارة حية للعميل (الأرشيف بس)", cA.execute("SELECT COUNT(*) FROM visits WHERE phone=?", (PH,)).fetchone()[0], 0)

_, ss, err, _ = run_app("new", workdir=wdA, state={"prefill": {"phone": PH}}, buttons={"use_prev_data"})
pfx = ss.get("prefill") or {}
check("«استخدم بياناته السابقة»: العمر 33 مش 32", (pfx.get("age"), pfx.get("age_unit")), ("33", "سنة"))
check("الملاحظة موجودة", "32 سنة" in (pfx.get("age_note") or "") and "33 سنة" in (pfx.get("age_note") or ""), True)
check("باقي البيانات اتنقلت", (pfx.get("name"), pfx.get("phone")), ("مريض أرشيف", PH))
ep = json.loads(pfx.get("extra_persons") or "[]")
check("عمر الحالة الإضافية 5 → 6", ep and ep[0]["age"], "6")
check("زيارة الأرشيف الأصلية ما اتغيّرتش (عمره وقتها)", json.loads(cA.execute("SELECT rec FROM visits_archive WHERE id='arch-1'").fetchone()[0])["age"], "32")

# زيارة حية قديمة + صفحة العميل
live = rec(902, id="live-1", phone="01099887766", age="40", visit_date=last_year, name="مريض حي")
appA.st.session_state.user_email = "Hussein.ali77121@gmail.com"
appA.insert_visit({**live, "age_unit": "سنة", "_user": "t"}, sync=False)
cA.commit()
_, ss2, err2, _ = run_app("client_profile", workdir=wdA, state={"selected_client_phone": "01099887766"}, buttons={"cp_new"})
pf2 = ss2.get("prefill") or {}
check("صفحة العميل: «زيارة جديدة» بعمر محدّث (40 → 41)", (pf2.get("age"), pf2.get("age_unit")), ("41", "سنة"))

# الفورم بيعرض الملاحظة، وفتح زيارة للتعديل ما فيهوش ملاحظة
run_app("new", workdir=wdA, state={"prefill": {"name": "س", "age": "33", "age_unit": "سنة", "age_note": "NOTE-XYZ-🎂", "phone": ""}})
check("الفورم بيعرض سطر تحديث العمر", "NOTE-XYZ-🎂" in md_all(("caption", "markdown")), True)
run_app("new", workdir=wdA, state={"prefill": {"name": "س", "age": "33", "age_unit": "سنة", "phone": ""}})
check("من غير ملاحظة → مفيش سطر", "العمر اتحدّث" in md_all(("caption", "markdown")), False)

print()
if _FAILS:
    print(f"❌ {len(_FAILS)} اختبار فشل:")
    for f in _FAILS:
        print("   -", f)
    sys.exit(1)
print("✅ كل اختبارات الواجهة وتحديث العمر نجحت")
