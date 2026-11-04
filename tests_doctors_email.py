# -*- coding: utf-8 -*-
"""
tests_doctors_email.py — اختبارات:
  ① doctors_sync: دمج/خطة سحب الأطباء (منطق بحت)
  ② email_backup: بناء الرسالة والإرسال (بسيرفر SMTP وهمي — مفيش شبكة)
  ③ تنفيذ فعلي في app.py: حفظ الدكتور على GitHub (دوال الشبكة متبدّلة بوهمية)،
     عزل حالة مزامنة الزيارات، زرار إرسال الملخص للدكتور، وإرسال النسخة للأدمن فقط

التشغيل:  python3 tests_doctors_email.py
"""
import os
import sys
import json
import shutil
import smtplib
import tempfile
import importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import doctors_sync as ds
import email_backup as eb

_FAILS = []


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


def D(i, name, phone="", active=1, branch="", comm=5.0, tr=0):
    return {"id": i, "name": name, "phone": phone, "branch": branch, "commission_pct": comm,
            "transport_eligible": tr, "active": active, "created_at": "2026-01-01"}


# ── ① doctors_sync ──────────────────────────────────────────────────────────
print("① doctors_sync")
remote = [D("r1", "حسين علي"), D("r2", "ضي", active=0), D("r3", "دكتور جديد", phone="01012345678")]
local = [D("x1", "حسين علي"), D("x2", "ضي"), D("x9", "ايه جمال")]
ops = ds.plan_pull(local, remote)
kinds = sorted((k, lid, r["id"]) for k, lid, r in ops)
check("المطابقة بالاسم بتاخد id بتاع GitHub (مفيش تكرار)",
      kinds, [("insert", None, "r3"), ("update", "x1", "r1"), ("update", "x2", "r2")])
check("المحلي بس بيتساب (ايه جمال ما اتمسّش)", all(lid != "x9" for _, lid, _ in ops), True)
check("الإيقاف اللي على GitHub بيتطبّق", [r["active"] for k, lid, r in ops if lid == "x2"], [0])
check("نفس البيانات → مفيش عمليات", ds.plan_pull(remote, remote), [])
check("مطابقة الاسم تتجاهل الهمزة والمسافات", ds.norm_name("  أحمد   علي ") == ds.norm_name("احمد علي"), True)

new = D("n1", "طبيب جديد", phone="01099999999")
edited = D("r1", "حسين علي", phone="01011112222")
stale = D("r3", "دكتور جديد", phone="000")          # نسخة قديمة عند سيرفر تاني — ماينفعش تدوس
merged = ds.merge_for_push(remote, [new, edited, stale], ["n1", "r1"])
by = {r["id"]: r for r in merged}
check("الجديد اتضاف", "n1" in by, True)
check("التعديل اتطبّق", by["r1"]["phone"], "01011112222")
check("تعديل سيرفر تاني ماتدوّسش (r3 مش في المتغيّرين)", by["r3"]["phone"], "01012345678")
check("الملف عمره ما يقل (3 قديم + 1 جديد)", len(merged), 4)
check("أول رفع (مفيش ملف) = كل المحلي", len(ds.merge_for_push([], [new, edited], None)), 2)
check("نفس الدكتور بـ id مختلف مايتكررش", len(ds.merge_for_push(remote, [D("zz", "حسين علي", phone="1")], ["zz"])), 3)
check("صف بلا اسم/id بيتشال", ds.clean_rows([{"id": "", "name": "x"}, {"id": "1", "name": ""}, D("2", "ok")]), [ds.clean_row(D("2", "ok"))])

# ── ② email_backup ──────────────────────────────────────────────────────────
print("\n② email_backup")
secrets = {"smtp_user": "sender@gmail.com", "smtp_password": "abcd efgh ijkl mnop"}
cfg = eb.smtp_config(lambda k, d=None: secrets.get(k, d))
check("الباسورد بيتنضّف من المسافات", cfg["password"], "abcdefghijklmnop")
check("الافتراضي جيميل SSL", (cfg["host"], cfg["port"]), ("smtp.gmail.com", 465))
check("إعداد ناقص → None", eb.smtp_config(lambda k, d=None: {"smtp_user": "a@b.c"}.get(k, d)), None)

msg = eb.build_message("sender@gmail.com", "Orangelab511@gmail.com", "نسخة", "نص",
                       [("a.json", b'{"x":1}', "application/json"),
                        ("b.xlsx", b"PK", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")])
check("المستلم", msg["To"], "Orangelab511@gmail.com")
check("المرفقات", [p.get_filename() for p in msg.iter_attachments()], ["a.json", "b.xlsx"])
try:
    eb.build_message("a", "b", "s", "t", [])
    check("مفيش مرفقات → خطأ", False, True)
except ValueError:
    check("مفيش مرفقات → خطأ", True, True)
try:
    eb.build_message("a", "b", "s", "t", [("big.bin", b"x" * (21 * 1024 * 1024), "application/octet-stream")])
    check("حجم كبير → خطأ", False, True)
except ValueError:
    check("حجم كبير → خطأ", True, True)


class FakeSMTP:
    sent, logins, fail = [], [], None

    def __init__(self, host, port, timeout=None, context=None):
        self.host, self.port = host, port

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def login(self, u, p):
        if FakeSMTP.fail == "auth":
            raise smtplib.SMTPAuthenticationError(535, b"bad")
        FakeSMTP.logins.append((u, p))

    def send_message(self, m):
        if FakeSMTP.fail == "net":
            raise OSError("network down")
        FakeSMTP.sent.append(m)


ok, err = eb.send_message(cfg, msg, smtp_ssl_cls=FakeSMTP)
check("إرسال ناجح", (ok, err, len(FakeSMTP.sent)), (True, "", 1))
FakeSMTP.fail = "auth"
ok, err = eb.send_message(cfg, msg, smtp_ssl_cls=FakeSMTP)
check("باسورد غلط → رسالة App Password", (ok, "App Password" in err), (False, True))
check("الباسورد ماظهرش في رسالة الخطأ", "abcdefgh" in err, False)
FakeSMTP.fail = "net"
ok, err = eb.send_message(cfg, msg, smtp_ssl_cls=FakeSMTP)
check("انقطاع شبكة → خطأ مفهوم من غير استثناء", (ok, "network down" in err), (False, True))
FakeSMTP.fail = None

# ── ③ تنفيذ app.py ──────────────────────────────────────────────────────────
print("\n③ app.py")
import _stub_streamlit as stub

SECRETS = {"admin_password": "TestPass123",
           "allowed_emails": ["Hussein.ali77121@gmail.com", "Orangelab511@gmail.com"],
           "github_token": "tok", "github_repo": "o/r", "github_branch": "main",
           "use_monthly_sync": False,
           "smtp_user": "sender@gmail.com", "smtp_password": "abcd efgh ijkl mnop"}


def run_app(page, user_type="admin", buttons=(), state=None, secrets=None, workdir=None):
    workdir = workdir or tempfile.mkdtemp(prefix="hvms_de_")
    cwd = os.getcwd()
    os.chdir(workdir)
    stub.reset()
    st = stub.install(secrets if secrets is not None else SECRETS)
    email = {"admin": "Hussein.ali77121@gmail.com", "diamond": "Orangelab511@gmail.com"}[user_type]
    st.session_state.update({
        "authenticated": True, "user_type": user_type, "user_email": email,
        "page": page, "need_password": False, "_skip_auto_login": True,
        "current_page": 1, "page_size": 20, "total_visits": 0,
        "prefill": {}, "selected_id": None, "selected_client_phone": "", "search_q": "",
    })
    st.session_state.update(state or {})
    stub.BUTTON_TRUE.update(buttons)
    for m in ("app", "core", "import_rules", "phone_utils", "lab_picker", "quick_panels",
              "doctors_sync", "email_backup", "login_theme", "easter_eggs", "device_auth",
              "labs_price_list"):
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


class FakeGH:
    """GitHub وهمي لملف واحد (doctors.json) — بيسجّل كل PUT."""
    def __init__(self, content=None):
        self.content, self.puts, self.fail_put = content, [], False

    def get_json(self, path):
        if self.content is None:
            return None, 404, "HTTP 404"
        return json.loads(json.dumps(self.content)), 200, ""

    def put_json(self, path, payload, message, expected_sha=None):
        if self.fail_put:
            return False
        self.puts.append((path, payload, message, expected_sha))
        self.content = json.loads(json.dumps(payload))
        return True


# 1) إضافة دكتور → بيترفع على GitHub (الملف اتعمل أول مرة = كل الأطباء + الجديد)
app, ss, err, wd = run_app("manage_doctors")
check("صفحة الأطباء اتنفذت", err is None, True)
gh = FakeGH(content=None)
app._gh_get_json, app._gh_put_json = gh.get_json, gh.put_json
app._get_github_file_sha = lambda p: ""
app.st.session_state.user_email = "Hussein.ali77121@gmail.com"
doc_id = app.insert_doctor("د. تجربة", 7.5, 1, "01012345678", "Diamond")
names = [d["name"] for d in gh.content["doctors"]]
check("الدكتور الجديد اتحفظ على GitHub", "د. تجربة" in names, True)
check("ومعاه الأطباء الافتراضيين (أول رفع)", len(names) >= 9, True)
check("نتيجة الحفظ متخزّنة للصفحة", app.st.session_state.get("_doctors_sync_msg"), (True, ""))
check("الـ PUT بدون SHA قديم لملف جديد", gh.puts[0][3], "")

# 2) تعديل → بيتحفظ، وباقي الأطباء مايتأثروش
other_before = {d["id"]: d for d in gh.content["doctors"] if d["id"] != doc_id}
app.update_doctor(doc_id, "01099998888", "La Cite", 10.0, 0)
saved = {d["id"]: d for d in gh.content["doctors"]}
check("التعديل اتحفظ", (saved[doc_id]["phone"], saved[doc_id]["branch"], saved[doc_id]["commission_pct"]),
      ("01099998888", "La Cite", 10.0))
check("باقي الأطباء زي ما هم", {i: d for i, d in saved.items() if i != doc_id}, other_before)
check("get_doctor_phone بالاسم", app.get_doctor_phone("د.  تجربة"), "01099998888")

# 3) إيقاف
app.toggle_doctor_active(doc_id)
check("الإيقاف اتحفظ", {d["id"]: d for d in gh.content["doctors"]}[doc_id]["active"], 0)

# 4) كونتينر جديد: الأطباء الافتراضيين بـ id عشوائي → السحب بيطابق بالاسم ومايتكررّوش
app2, ss2, err2, wd2 = run_app("manage_doctors")
remote_doc = json.loads(json.dumps(gh.content))
gh2 = FakeGH(content=remote_doc)
app2._gh_get_json, app2._gh_put_json = gh2.get_json, gh2.put_json
before = len(app2._doctor_rows())
r = app2.pull_doctors_from_github()
rows = app2._doctor_rows()
check("السحب نجح", r["ok"] and r["found"], True)
check("الدكتور المضاف رجع بعد إعادة التشغيل", any(d["name"] == "د. تجربة" and d["phone"] == "01099998888" for d in rows), True)
check("مفيش أسماء مكررة", len({ds.norm_name(d["name"]) for d in rows}), len(rows))
check("الـ id بقى بتاع GitHub", {d["id"] for d in rows} >= {d["id"] for d in remote_doc["doctors"]}, True)

# 5) فشل GitHub مايوقفش الحفظ المحلي ومايلمّسش حالة مزامنة الزيارات
app3, ss3, err3, wd3 = run_app("manage_doctors")
gh3 = FakeGH(content=None)
gh3.fail_put = True
app3._gh_get_json, app3._gh_put_json = gh3.get_json, gh3.put_json
app3._get_github_file_sha = lambda p: ""
app3._GH_STATE["conflict"] = ""
app3._GH_STATE["connected"] = True
app3._GH_STATE["last_error"] = "قديم"
app3.st.session_state.user_email = "Hussein.ali77121@gmail.com"
did = app3.insert_doctor("د. فشل", 5.0, 0, "", "")
check("الدكتور اتحفظ محليًا برضه", any(d["id"] == did for d in app3._doctor_rows()), True)
check("رسالة فشل الحفظ على GitHub", app3.st.session_state["_doctors_sync_msg"][0], False)
check("حالة مزامنة الزيارات ماتأثرتش",
      (app3._GH_STATE["conflict"], app3._GH_STATE["connected"], app3._GH_STATE["last_error"]),
      ("", True, "قديم"))

# 6) قراءة GitHub فشلت (مش 404) → مانكتبش على أعمى
app4, _, _, _ = run_app("manage_doctors")
app4._gh_get_json = lambda p: (None, 500, "HTTP 500")
app4._get_github_file_sha = lambda p: "abc"
puts = []
app4._gh_put_json = lambda *a, **k: puts.append(a) or True
ok4, err4 = app4.push_doctors_to_github(["x"], "t")
check("قراءة فاشلة → مفيش كتابة", (ok4, puts), (False, []))
app4._gh_get_json = lambda p: ([1, 2], 200, "")          # شكل غير معروف
ok4, err4 = app4.push_doctors_to_github(["x"], "t")
check("ملف بشكل غريب → مفيش كتابة", (ok4, puts), (False, []))

# 7) من غير Secrets → رسالة واضحة، والحفظ المحلي شغال
app5, _, _, _ = run_app("manage_doctors", secrets={"admin_password": "x", "allowed_emails": ["Hussein.ali77121@gmail.com"]})
ok5, err5 = app5.push_doctors_to_github(None, "t")
check("من غير github secrets", (ok5, "هيضيعوا" in err5), (False, True))

# 8) صفحة الأطباء: إضافة عبر الواجهة + منع التكرار
app6, ss6, err6, _ = run_app("manage_doctors", buttons={"save_new_doc_0"},
                             state={"new_doc_name_0": "ح"})   # الـ stub بيرجّع value الافتراضي، فبنختبر المنطق مباشرة تحت
check("صفحة الأطباء مع ضغط «حفظ» اتنفذت", err6 is None or type(err6).__name__ in ("_Rerun", "_Stop"), True)
labels = [c[1][0] for c in stub.CALLS if c[0] == "button"]
check("أزرار الأطباء ظاهرة (إيقاف/تعديل/حفظ الدائم)",
      ("🚫 إيقاف" in labels, "☁️ احفظ الحاليين على GitHub" in labels, "🔄 تحديث من GitHub" in labels), (True, True, True))

# 9) زرار إرسال الملخص للدكتور في صفحة الزيارة
app7, _, _, _ = run_app("home")
v = {"id": "v1", "name": "أحمد", "phone": "01000000000", "visit_date": "2026-11-05", "visit_time": "10:00 AM",
     "doctor_name": "حسين علي", "branch": "Diamond", "address": "x", "status": "مجدولة",
     "selected_labs_text": "CBC — 400 جنيه", "extra_persons": "[]", "labs_price_before": 400,
     "labs_price_after": 400, "transport_fee": 0, "total_price": 400}
app7.st.session_state.user_email = "Hussein.ali77121@gmail.com"
conn = app7.get_connection()
conn.execute("UPDATE doctors SET phone='01234567890' WHERE name='حسين علي'")
conn.commit()
check("رقم الدكتور بيتجاب بالاسم", app7.get_doctor_phone("حسين علي"), "01234567890")
link = app7.whatsapp_link("hi", app7.get_doctor_phone("حسين علي"))
check("لينك واتساب مباشر لرقم الدكتور", link.startswith("https://wa.me/201234567890?text="), True)

# 10) إرسال النسخة: أدمن فقط + بيبعت لإيميل الفرع الرئيسي
FakeSMTP.sent.clear()
FakeSMTP.fail = None
orig = eb.smtplib.SMTP_SSL
eb.smtplib.SMTP_SSL = FakeSMTP
_cwd0 = os.getcwd()
try:
    app8, _, _, wd8 = run_app("home")
    os.chdir(wd8)          # backup_to_json / export_to_excel بيكتبوا ملفات في مجلد الشغل — مش في الريبو
    app8.st.session_state.user_email = "Hussein.ali77121@gmail.com"
    # قاعدة فاضية → مش هيبعت نسخة فاضية
    ok8, m8 = app8.send_backup_email()
    check("قاعدة فاضية → مابيبعتش", (ok8, len(FakeSMTP.sent)), (False, 0))
    # نضيف زيارة (نفس صيغة الاستيراد)
    app8.insert_visit({"id": "t-1", "created_at": "2026-11-04T10:00:00", "name": "عميل", "age": "30",
                       "phone": "01000000000", "visit_date": "2026-11-05", "visit_time": "10:00 AM",
                       "branch": "Diamond", "status": "مجدولة", "doctor_name": "حسين علي",
                       "address": "x", "location_link": "", "selected_labs_text": "CBC — 400 جنيه",
                       "notes": "", "labs_price_before": 400, "labs_price_after": 400,
                       "transport_fee": 0, "total_price": 400, "_user": "test"}, sync=False)
    ok8, m8 = app8.send_backup_email()
    check("أدمن + قاعدة فيها زيارات → اتبعتت", (ok8, len(FakeSMTP.sent)), (True, 1))
    sent = FakeSMTP.sent[-1]
    check("المستلم = إيميل الفرع الرئيسي", sent["To"], "Orangelab511@gmail.com")
    names = [p.get_filename() for p in sent.iter_attachments()]
    check("المرفقات: JSON + الأطباء", (any(n.startswith("visits_backup") and n.endswith(".json") for n in names),
                                       any(n.startswith("doctors_backup") for n in names)), (True, True))
    # مش أدمن → مرفوض على مستوى الدالة
    app8.st.session_state.user_type = "diamond"
    ok8, m8 = app8.send_backup_email()
    check("غير الأدمن مرفوض (حتى لو استدعى الدالة مباشرة)", (ok8, len(FakeSMTP.sent)), (False, 1))
    # بدون إعدادات smtp
    app8.st.session_state.user_type = "admin"
    app9, _, _, _ = run_app("home", secrets={"admin_password": "x", "allowed_emails": ["Hussein.ali77121@gmail.com"]})
    app9.st.session_state.user_type = "admin"
    ok9, m9 = app9.send_backup_email()
    check("من غير smtp secrets → رسالة واضحة", (ok9, "smtp_user" in m9), (False, True))
finally:
    os.chdir(_cwd0)
    eb.smtplib.SMTP_SSL = orig

# 11) صفحة الزيارة: زرار «إرسال الملخص للدكتور مباشرة» (بيتنفذ فعليًا على داتابيز فيها زيارة)
NOGH = {"admin_password": "x", "allowed_emails": ["Hussein.ali77121@gmail.com"]}
appA, _, _, wdA = run_app("home", secrets=NOGH)
appA.st.session_state.user_email = "Hussein.ali77121@gmail.com"
appA.insert_visit({"id": "t-9", "created_at": "2026-11-04T10:00:00", "name": "عميل", "age": "30",
                   "phone": "01000000000", "visit_date": "2026-11-05", "visit_time": "10:00 AM",
                   "branch": "Diamond", "status": "تمت", "doctor_name": "حسين علي",
                   "address": "x", "location_link": "", "selected_labs_text": "CBC — 400 جنيه",
                   "notes": "", "labs_price_before": 400, "labs_price_after": 400,
                   "transport_fee": 0, "total_price": 400, "_user": "test"}, sync=False)
cA = appA.get_connection()
cA.execute("UPDATE doctors SET phone='01234567890' WHERE name='حسين علي'")
cA.commit()
run_app("detail", secrets=NOGH, workdir=wdA, state={"selected_id": "t-9"})
md = " ".join(str(c[1][0]) for c in stub.CALLS if c[0] == "markdown" and c[1])
check("صفحة الزيارة: زرار الدكتور المباشر ظاهر", "إرسال الملخص للدكتور حسين علي مباشرة" in md, True)
check("ولينكه على رقم الدكتور", "wa.me/201234567890" in md, True)
cA.execute("UPDATE doctors SET phone='' WHERE name='حسين علي'"); cA.commit()
run_app("detail", secrets=NOGH, workdir=wdA, state={"selected_id": "t-9"})
md = " ".join(str(c[1][0]) for c in stub.CALLS if c[0] == "markdown" and c[1])
check("من غير رقم: مفيش زرار (بس تلميح)", "إرسال الملخص للدكتور حسين علي مباشرة" in md, False)

# الزرار في الواجهة: ظاهر للأدمن بس
app10, _, _, _ = run_app("home")
labs_admin = [c[1][0] for c in stub.CALLS if c[0] == "button"]
check("زرار الإرسال ظاهر للأدمن", "📧 ابعت النسخة دلوقتي" in labs_admin, True)
app11, _, _, _ = run_app("home", user_type="diamond")
labs_dia = [c[1][0] for c in stub.CALLS if c[0] == "button"]
check("زرار الإرسال مش ظاهر لغير الأدمن", "📧 ابعت النسخة دلوقتي" in labs_dia, False)

print()
if _FAILS:
    print(f"❌ {len(_FAILS)} اختبار فشل:")
    for f in _FAILS:
        print("   -", f)
    sys.exit(1)
print("✅ كل اختبارات الأطباء والإيميل نجحت")
