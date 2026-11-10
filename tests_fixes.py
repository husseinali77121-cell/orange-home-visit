# -*- coding: utf-8 -*-
"""
tests_fixes.py — إصلاحات نوفمبر 2026

  ① متتبّع نتيجة الحفظ: فشل الرفع بيفضل ظاهر بعد الـ rerun، والنجاح بيصفّره
  ② مانع التكرار: نفس التليفون في نفس اليوم (زيارة جديدة بس، مع خانة تأكيد)
  ③ تاريخ الدفع مايتغيّرش لما تتعدّل زيارة مدفوعة
  ④ تنظيف البيانات القديمة من جوّه البرنامج
  ⑤ الفرع والدكتور الافتراضيين حسب الحساب
  ⑥ فحص GitHub دوري مش مع كل ضغطة — والحفظ لسه بيقرا قبل ما يكتب
  ⑦ الزيارات اللي عدّى ميعادها: سؤال بدل التحويل الآلي
  ⑧ خانة البحث: المسح/الكتابة بيتطبّق من أول مرة
  ⑨ زرار تصدير PDF (الرئيسية + التقارير)

التشغيل:  python3 tests_fixes.py
"""
import os
import sys
import shutil
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


SECRETS = {"admin_password": "x", "branch_password": "y", "device_secret": "z",
           "allowed_emails": ["Hussein.ali77121@gmail.com", "Orangelab511@gmail.com",
                              "Huossein721@gmail.com"],
           "github_token": "", "github_repo": "", "use_monthly_sync": False}
USERS = {"admin": "Hussein.ali77121@gmail.com", "diamond": "Orangelab511@gmail.com",
         "lacite": "Huossein721@gmail.com"}
MODS = ("app", "core", "import_rules", "phone_utils", "lab_picker", "quick_panels",
        "doctors_sync", "email_backup", "login_theme", "easter_eggs", "device_auth",
        "labs_price_list", "repair_data")

# ── ودجت قابلة للتحكم: زر الحفظ (مالوش key) وخانات التأكيد ──
PRESS_LABELS, CHECK_KEYS, PICKED = set(), set(), {}
_orig_button, _orig_checkbox, _orig_selectbox = stub.button, stub.checkbox, stub.selectbox


def _button(label="", *a, **k):
    r = _orig_button(label, *a, **k)
    return r or any(p in str(label) for p in PRESS_LABELS)


def _checkbox(label="", value=False, *a, **k):
    r = _orig_checkbox(label, value, *a, **k)
    return True if k.get("key") in CHECK_KEYS else r


def _selectbox(label="", options=(), index=0, *a, **k):
    r = _orig_selectbox(label, options, index, *a, **k)
    PICKED[str(label)] = r
    return r


_orig_text_input = stub.text_input


def _text_input(label="", value="", *a, **k):
    """زي Streamlit: خانة ليها key بترجّع قيمتها من session_state."""
    r = _orig_text_input(label, value, *a, **k)
    key = k.get("key")
    if key and key in stub.session_state:
        return str(stub.session_state[key])
    return r


stub.button, stub.checkbox, stub.selectbox = _button, _checkbox, _selectbox
stub.text_input = _text_input


def run(page, utype, extra=None, press=(), checks=(), keys=()):
    """rerun كامل لـ app.py في المجلد الحالي (الـ DB بتفضل بين النداءات)."""
    stub.reset()
    st = stub.install(SECRETS)
    PRESS_LABELS.clear(); PRESS_LABELS.update(press)
    CHECK_KEYS.clear(); CHECK_KEYS.update(checks)
    PICKED.clear()
    stub.BUTTON_TRUE.update(keys)
    st.session_state.update({
        "authenticated": True, "user_type": utype, "user_email": USERS[utype],
        "page": page, "need_password": False, "_skip_auto_login": True,
        "current_page": 1, "page_size": 20, "total_visits": 0,
        "prefill": {}, "selected_id": None, "selected_client_phone": "", "search_q": "",
    })
    if extra:
        st.session_state.update(extra)
    for m in MODS:
        sys.modules.pop(m, None)
    how = "ok"
    try:
        importlib.import_module("app")
    except stub._Rerun:
        how = "rerun"
    except stub._Stop:
        how = "stop"
    return how


def texts(kind):
    return " ".join(str(c[1][0]) for c in stub.CALLS if c[0] == kind and c[1])


def db():
    import sqlite3
    c = sqlite3.connect("visits.db")
    c.row_factory = sqlite3.Row
    return c


def base_visit(**over):
    v = {"id": "v1", "created_at": "2026-11-01T10:00:00", "name": "عميل تجربة", "age": 30,
         "age_unit": "سنة", "phone": "01012345678", "visit_date": TOMORROW,
         "visit_time": "10:00 AM", "doctor_name": "حسين علي", "branch": "La Cite",
         "city": "6 أكتوبر", "district": "الحي الأول", "address": "شارع 1",
         "location_link": "", "selected_labs_text": "", "notes": "", "extra_persons": "",
         "labs_price_before": 500, "labs_price_after": 500, "transport_fee": 100,
         "total_price": 600, "status": "مجدولة", "payment_status": "غير مدفوع",
         "payment_method": "", "paid_amount": 0, "payment_date": ""}
    v.update(over)
    return v


TOMORROW = (date.today() + timedelta(days=1)).isoformat()
workdir = tempfile.mkdtemp(prefix="hvms_fixes_")
os.chdir(workdir)
try:
    # ══════════════════════════════════════════════════════════════════════
    print("\n⑤ الفرع والدكتور الافتراضيين")
    run("new", "lacite")
    check("La Cite ← الفرع La Cite", PICKED.get("🏥 الفرع"), "La Cite")
    check("La Cite ← حسين علي", PICKED.get("👨‍⚕️ الدكتور القائم بالزيارة"), "حسين علي")
    run("new", "diamond")
    check("Diamond ← الفرع Diamond", PICKED.get("🏥 الفرع"), "Diamond")
    check("Diamond ← محمد شفيق", PICKED.get("👨‍⚕️ الدكتور القائم بالزيارة"), "محمد شفيق")
    run("new", "diamond", {"prefill": {"doctor_name": "ايه جمال", "branch": "La Cite"}})
    check("بيانات منقولة بتكسب الافتراضي",
          (PICKED.get("🏥 الفرع"), PICKED.get("👨‍⚕️ الدكتور القائم بالزيارة")),
          ("La Cite", "ايه جمال"))

    # ══════════════════════════════════════════════════════════════════════
    print("\n① متتبّع نتيجة الحفظ")
    run("home", "admin")
    app = sys.modules["app"]
    check("الدالة الأصلية لسه موجودة باسمها", app._save_to_github_json_core.__name__,
          "save_to_github_json")
    al = app._save_alert_state()
    app._save_to_github_json_core = lambda: False
    check("من غير أسرار: الفشل مابيتسجّلش (محلي فقط)", (app.save_to_github_json(), al["unsaved"]),
          (False, 0))
    app.GITHUB_TOKEN, app.GITHUB_REPO = "t", "o/r"
    app._GH_STATE["last_error"] = "HTTP 500"
    check("الفشل بيرجّع False زي الأصل", app.save_to_github_json(), False)
    app.save_to_github_json()
    check("عدّاد الفشل = 2 والسبب محفوظ", (al["unsaved"], al["why"]), (2, "HTTP 500"))
    # محاكاة rerun: _GH_STATE بيتبني من جديد
    app._GH_STATE["unsaved"] = 0
    app._GH_STATE["last_error"] = ""
    app._GH_STATE["connected"] = True
    check("المؤشر أحمر بعد الـ rerun", app._sync_chip()[1:], ("🔴", "2 تعديل غير مرفوع"))
    stub.CALLS.clear()
    app.render_sync_banner()
    check("البانر الأحمر ظاهر بعد الـ rerun", "2 تعديل محفوظ محليًا" in texts("markdown"), True)
    check("زر إعادة المحاولة موجود", "حاول الرفع على GitHub" in texts("button"), True)
    app._save_to_github_json_core = lambda: True
    check("النجاح بيرجّع True", app.save_to_github_json(), True)
    check("النجاح بيصفّر العدّاد", (al["unsaved"], al["why"]), (0, ""))
    stub.CALLS.clear()
    app.render_sync_banner()
    check("البانر اختفى بعد النجاح", "محفوظ محليًا" in texts("markdown"), False)
    app.GITHUB_TOKEN, app.GITHUB_REPO = "", ""

    # ══════════════════════════════════════════════════════════════════════
    print("\n② مانع التكرار")
    app.insert_visit(base_visit(), sync=False)
    new_pf = {"name": "عميل تجربة", "phone": "01012345678", "address": "شارع 1",
              "visit_date": TOMORROW, "age": 30, "doctor_name": "حسين علي", "branch": "La Cite"}
    count = lambda: db().execute("SELECT COUNT(*) FROM visits").fetchone()[0]
    run("new", "lacite", {"prefill": dict(new_pf)}, press=("حفظ الزيارة",))
    check("التكرار اتمنع (مفيش صف جديد)", count(), 1)
    check("رسالة المنع ظهرت", "زيارة مكررة" in texts("error"), True)
    check("الزيارة الموجودة معروضة", "عنده زيارة مسجّلة في نفس اليوم" in texts("markdown"), True)
    how = run("new", "lacite", {"prefill": dict(new_pf)}, press=("حفظ الزيارة",),
              checks=("dup_same_day_ok",))
    check("بخانة التأكيد الحفظ بيعدّي", (count(), how), (2, "rerun"))
    other_day = (date.today() + timedelta(days=2)).isoformat()
    run("new", "lacite", {"prefill": {**new_pf, "visit_date": other_day}}, press=("حفظ الزيارة",))
    check("يوم تاني = مفيش منع", count(), 3)
    c = db(); c.execute("UPDATE visits SET status='ملغية' WHERE visit_date=?", (other_day,)); c.commit()
    run("new", "lacite", {"prefill": {**new_pf, "visit_date": other_day}}, press=("حفظ الزيارة",))
    check("الزيارة الملغية مش بتمنع", count(), 4)
    run("new", "lacite", {"prefill": {**base_visit(), "_edit": True, "name": "اسم مصحّح"}},
        press=("حفظ التعديلات",))
    check("التعديل مش بيتمنع", db().execute("SELECT name FROM visits WHERE id='v1'").fetchone()[0],
          "اسم مصحّح")
    run("home", "lacite")
    check("مفتاح التأكيد بيتمسح مع كل فتحة فورم", "dup_same_day_ok" in sys.modules["app"]._VISIT_FORM_KEYS, True)

    # ══════════════════════════════════════════════════════════════════════
    print("\n③ تاريخ الدفع")
    app = sys.modules["app"]
    app.insert_visit(base_visit(id="p1", phone="01099999999", payment_status="مدفوع",
                                payment_method="نقدي", paid_amount=600,
                                payment_date="2026-10-01"), sync=False)
    v = dict(db().execute("SELECT * FROM visits WHERE id='p1'").fetchone())
    run("new", "lacite", {"prefill": {**v, "_edit": True, "name": "اسم جديد"}},
        press=("حفظ التعديلات",))
    r = db().execute("SELECT name, payment_date FROM visits WHERE id='p1'").fetchone()
    check("تعديل زيارة مدفوعة: التاريخ الأصلي باقي", (r[0], r[1]), ("اسم جديد", "2026-10-01"))
    run("new", "lacite", {"prefill": {**new_pf, "phone": "01088888888", "payment_status": "مدفوع",
                                      "labs_price_after": 500, "labs_price_before": 500}},
        press=("حفظ الزيارة",))
    r = db().execute("SELECT payment_date FROM visits WHERE phone='01088888888'").fetchone()
    check("زيارة جديدة مدفوعة: التاريخ = النهاردة", r and r[0], date.today().isoformat())

    # ══════════════════════════════════════════════════════════════════════
    print("\n④ تنظيف البيانات")
    run("home", "admin")
    app = sys.modules["app"]
    c = app.get_connection()
    c.execute("DELETE FROM visits"); c.commit()
    app.insert_visit(base_visit(id="c1", district="الحي الاول"), sync=False)
    app.insert_visit(base_visit(id="c2", phone="01011111111", district="الحى الثانى",
                                doctor_name="عبدالله "), sync=False)
    app.insert_visit(base_visit(id="c3", phone="01022222222", payment_status="مدفوع",
                                payment_method="", paid_amount=0), sync=False)
    app.insert_visit(base_visit(id="c4", phone="01033333333", district="الحي الاول"), sync=False)
    c.execute("UPDATE visits SET archived=1 WHERE id='c4'"); c.commit()
    plan = app.data_cleanup_plan()
    check("الخطة: إملاء/دكتور/مدفوع صفر/بدون طريقة",
          (len(plan["geo"]), len(plan["doctor"]), len(plan["paid0"]), len(plan["no_method"])),
          (2, 1, 1, 1))
    check("المعاينة مابتكتبش", c.execute("SELECT district FROM visits WHERE id='c1'").fetchone()[0],
          "الحي الاول")
    n, saved = app.apply_data_cleanup(plan, fix_paid0=True, user_email="t")
    check("عدد التغييرات", n, 4)
    row = lambda i, f: c.execute(f"SELECT {f} FROM visits WHERE id=?", (i,)).fetchone()[0]
    check("الإملاء اتوحّد", (row("c1", "district"), row("c2", "district")),
          ("الحي الأول", "الحي الثاني"))
    check("اسم الدكتور اتنضّف", row("c2", "doctor_name"), "عبدالله")
    check("المدفوع بصفر = الإجمالي", row("c3", "paid_amount"), 600.0)
    check("الأرشيف ماتلمسش", row("c4", "district"), "الحي الاول")
    check("updated_at اتحدّث", row("c1", "updated_at") > "2026-11-01", True)
    check("التغييرات في سجل التدقيق",
          c.execute("SELECT COUNT(*) FROM audit_log WHERE action='cleanup'").fetchone()[0], 4)
    plan2 = app.data_cleanup_plan()
    check("تشغيل تاني = مفيش حاجة",
          len(plan2["geo"]) + len(plan2["doctor"]) + len(plan2["paid0"]), 0)
    how = run("dashboard", "admin")
    check("Dashboard نضيف: رسالة «مفيش حاجة»", (how, "مفيش حاجة محتاجة تنظيف" in texts("success")),
          ("ok", True))
    c = db(); c.execute("UPDATE visits SET district='الحى العاشر' WHERE id='c1'"); c.commit()
    run("dashboard", "admin")
    check("Dashboard: المعاينة وزر التطبيق ظاهرين",
          ("توحيد الإملاء — 1" in texts("markdown"), "طبّق التنظيف (1)" in texts("button")),
          (True, True))
    check("من غير ضغط مفيش كتابة",
          db().execute("SELECT district FROM visits WHERE id='c1'").fetchone()[0], "الحى العاشر")
    how = run("dashboard", "admin", press=("طبّق التنظيف",), checks=("cleanup_confirm",))
    check("الضغط بيطبّق ويعمل rerun",
          (how, db().execute("SELECT district FROM visits WHERE id='c1'").fetchone()[0]),
          ("rerun", "الحي العاشر"))

    # ══════════════════════════════════════════════════════════════════════
    print("\n⑥ فحص GitHub الدوري")
    from datetime import datetime as _dt
    run("home", "admin")
    app = sys.modules["app"]
    seen = app._gh_seen()
    check("بعد أول رن: اللقطة اتسجّلت", seen["at"] is not None, True)
    seen["snap"] = {"connected": True, "remote_total": 325, "month_totals": {"2026-11": 17},
                    "monthly_ready": True, "legacy_total": 325, "last_error": ""}
    seen["at"] = _dt.now()
    check("متصل ولسه فاحص: مفيش قراءة جديدة", app._gh_check_due(), False)
    seen["at"] = _dt.now() - timedelta(minutes=app.GH_RECHECK_MIN, seconds=5)
    check("بعد مهلة إعادة الفحص: يقرا تاني", app._gh_check_due(), True)
    seen["snap"]["connected"] = False
    seen["at"] = _dt.now() - timedelta(seconds=5)
    check("الاتصال واقع من 5 ث: يستنى", app._gh_check_due(), False)
    seen["at"] = _dt.now() - timedelta(seconds=25)
    check("الاتصال واقع من 25 ث: يحاول تاني", app._gh_check_due(), True)
    seen["snap"]["connected"] = True
    app._GH_STATE.update(remote_total=None, month_totals={}, monthly_ready=None)
    check("العرض بياخد من اللقطة لما الحالة فاضية",
          (app._gh_view("remote_total"), app._gh_view("month_totals"), app._gh_view("monthly_ready")),
          (325, {"2026-11": 17}, True))
    app._GH_STATE["remote_total"] = 400
    check("القيمة الطازة بتكسب اللقطة", app._gh_view("remote_total"), 400)
    # الحفظ لسه بيقرا GitHub بنفسه قبل الكتابة (اللقطة مابتدخلش في قرار الحفظ)
    _n_local = app.get_connection().execute(
        "SELECT COUNT(*) FROM visits WHERE COALESCE(archived,0)=0").fetchone()[0]
    reads, puts = [], []
    def _fake_download():
        reads.append(1)
        app._GH_STATE["remote_total"] = _n_local
        return [], 200, ""
    app._gh_download_visits = _fake_download
    app._gh_put_json = lambda path, payload, message, expected_sha=None: (puts.append(path) or True)
    app.GITHUB_TOKEN, app.GITHUB_REPO = "t", "o/r"
    app._GH_STATE.update(remote_total=None, conflict="")
    ok = app.save_to_github_json()
    check("الحفظ: قراءة طازة ثم كتابة", (ok, len(reads) >= 1, len(puts) >= 1), (True, True, True))
    check("الحفظ الناجح حدّث اللقطة", app._gh_seen()["snap"].get("remote_total"), _n_local)
    app.GITHUB_TOKEN, app.GITHUB_REPO = "", ""

    # ══════════════════════════════════════════════════════════════════════
    print("\n⑦ زيارات عدّى ميعادها")
    c = app.get_connection()
    c.execute("DELETE FROM visits"); c.commit()
    YEST = (date.today() - timedelta(days=1)).isoformat()
    app.insert_visit(base_visit(id="o1", visit_date=YEST, phone="01000000001"), sync=False)
    app.insert_visit(base_visit(id="o2", visit_date=YEST, phone="01000000002", status="في الطريق"), sync=False)
    app.insert_visit(base_visit(id="o3", visit_date=YEST, phone="01000000003", status="تمت"), sync=False)
    app.insert_visit(base_visit(id="o4", visit_date=YEST, phone="01000000004", branch="Diamond"), sync=False)
    app.insert_visit(base_visit(id="o5", visit_date=TOMORROW, phone="01000000005"), sync=False)
    app.insert_visit(base_visit(id="o6", visit_date=YEST, phone="01000000006"), sync=False)
    check("الوضع الافتراضي = سؤال", app.OVERDUE_MODE, "ask")
    check("المستحق لفرع La Cite", [v["id"] for v in app.fetch_overdue_visits("La Cite")], ["o1", "o2", "o6"])
    check("المستحق للأدمن (كل الفروع)", len(app.fetch_overdue_visits(None)), 4)
    stat = lambda i: db().execute("SELECT status FROM visits WHERE id=?", (i,)).fetchone()[0]
    run("home", "lacite")
    check("القائمة ظاهرة بالعدد", "عدّى ميعادها — حصل إيه؟ (3)" in texts("markdown"), True)
    check("مفيش تحويل آلي", (stat("o1"), stat("o2")), ("مجدولة", "في الطريق"))
    run("home", "diamond")
    check("Diamond بيشوف زياراته بس", "حصل إيه؟ (1)" in texts("markdown"), True)
    how = run("home", "lacite", keys=("od_done_o1",))
    check("✅ تمت", (how, stat("o1")), ("rerun", "تمت"))
    how = run("today", "lacite", keys=("od_cancel_o2",))
    check("❌ ملغية (من صفحة اليوم)", (how, stat("o2")), ("rerun", "ملغية"))
    how = run("home", "lacite", keys=("od_post_o6",))
    ss = stub.session_state
    check("⏰ تأجيل بيفتح التعديل", (how, ss.get("page"), (ss.get("prefill") or {}).get("id"),
                                    (ss.get("prefill") or {}).get("_edit"), stat("o6")),
          ("rerun", "new", "o6", True, "مجدولة"))
    run("home", "lacite")
    check("الباقي في القائمة = 1", "حصل إيه؟ (1)" in texts("markdown"), True)
    SECRETS["overdue_mode"] = "auto"
    run("home", "lacite")
    check("overdue_mode=auto بيرجّع القديم", (stat("o6"), "حصل إيه؟" in texts("markdown")), ("تمت", False))
    SECRETS.pop("overdue_mode")

    # ══════════════════════════════════════════════════════════════════════
    print("\n⑧ خانة البحث")
    def _search_call():
        return [c for c in stub.CALLS if c[0] == "text_input" and c[1] and "بحث" in str(c[1][0])]
    run("home", "lacite")
    sc = _search_call()
    check("الخانة ليها key ثابت ومن غير value متغيّر",
          (len(sc), sc[0][2].get("key"), "value" in sc[0][2]), (1, "search_box", False))
    check("أول فتح: الخانة فاضية", stub.session_state.get("search_q"), "")
    run("home", "lacite", {"search_box": "رئيفة"})
    check("كتابة اسم → البحث اتطبّق", stub.session_state.get("search_q"), "رئيفة")
    run("home", "lacite", {"search_q": "رئيفة", "search_box": ""})
    check("مسح الاسم مرة واحدة → البحث اتلغى", stub.session_state.get("search_q"), "")
    run("home", "lacite", {"search_q": "رئيفة", "search_box": "خالد"})
    check("كتابة اسم جديد مرة واحدة → اتطبّق", stub.session_state.get("search_q"), "خالد")
    run("home", "lacite", {"search_q": "خالد"})          # رجوع من صفحة تانية (Streamlit مسح search_box)
    check("بعد الرجوع للرئيسية البحث لسه موجود",
          (stub.session_state.get("search_box"), stub.session_state.get("search_q")), ("خالد", "خالد"))

    # ══════════════════════════════════════════════════════════════════════
    print("\n⑨ تصدير PDF")
    app = sys.modules["app"]
    c = app.get_connection()
    c.execute("DELETE FROM visits"); c.commit()
    TODAY = date.today().isoformat()
    for k_ in range(4):
        app.insert_visit(base_visit(id=f"x{k_}", visit_date=TODAY, phone=f"0101000000{k_}",
                                    status="تمت"), sync=False)
    app.insert_visit(base_visit(id="xd", visit_date=TODAY, phone="01010000009", branch="Diamond"), sync=False)
    n, pdf, fname, err = app.export_to_pdf(branch_filter="La Cite", date_from=TODAY, date_to=TODAY)
    check("export_to_pdf: فرع La Cite بس", (n, err, fname, pdf[:4]),
          (4, "", f"lacite_{TODAY}_{TODAY}.pdf", b"%PDF"))
    n, pdf, fname, err = app.export_to_pdf(date_from="2001-01-01", date_to="2001-01-02")
    check("فترة فاضية → مفيش ملف", (n, pdf), (0, None))
    run("home", "lacite")
    check("زرار PDF ظاهر في الرئيسية", "— PDF" in texts("button"), True)
    stub.CALLS.clear()
    run("home", "lacite", keys=("btn_export_home_pdf",))
    dl = [c_ for c_ in stub.CALLS if c_[0] == "download_button" and c_[2].get("key") == "dl_home_pdf"]
    check("ضغط PDF في الرئيسية → زرار تحميل PDF",
          (len(dl), dl and dl[0][2].get("mime"), dl and str(dl[0][2].get("file_name", "")).endswith(".pdf")),
          (1, "application/pdf", True))
    run("home", "lacite", keys=("btn_export_home",))
    dlx = [c_ for c_ in stub.CALLS if c_[0] == "download_button" and c_[2].get("key") == "dl_home_final"]
    check("زرار Excel لسه شغال زي الأول", len(dlx), 1)
    run("reports", "admin", keys=("export_rep_pdf",))
    dl = [c_ for c_ in stub.CALLS if c_[0] == "download_button" and c_[2].get("key") == "dl_rep_pdf"]
    check("ضغط PDF في التقارير → زرار تحميل PDF", (len(dl), dl and dl[0][2].get("mime")),
          (1, "application/pdf"))
finally:
    os.chdir(HERE)
    shutil.rmtree(workdir, ignore_errors=True)

print()
if _FAILS:
    print(f"❌ فشل {len(_FAILS)}: {_FAILS}")
    sys.exit(1)
print("✅ كل اختبارات الإصلاحات نجحت")
