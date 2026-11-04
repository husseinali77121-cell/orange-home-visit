# -*- coding: utf-8 -*-
"""
tests_archive_index.py — فهرس الأرشيف: تاريخ العميل يفضل ظاهر حتى لو زياراته اتأرشفت

  ① load_archive_index: بيملي جدول visits_archive **المنفصل** ومابيلمسش visits
  ② fetch_client_history / get_client_tag / get_churn_risk بيشوفوا الأرشيف (بدون تكرار)
  ③ مفيش أي رقم في التقارير/النسخ الاحتياطي/الإقلاع بيتغيّر
  ④ فشل جزئي / من غير secrets → مفيش كراش
  ⑤ صفحة «زيارة جديدة»: كارت «هذا العميل موجود في النظام» لعميل زياراته كلها في الأرشيف

التشغيل:  python3 tests_archive_index.py
"""
import os
import sys
import json
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


GH = {"admin_password": "TestPass123", "allowed_emails": ["Hussein.ali77121@gmail.com"],
      "github_token": "tok", "github_repo": "o/r", "github_branch": "main", "use_monthly_sync": False}
NOGH = {"admin_password": "x", "allowed_emails": ["Hussein.ali77121@gmail.com"]}


def run_app(page="home", secrets=None, state=None, workdir=None, buttons=()):
    workdir = workdir or tempfile.mkdtemp(prefix="hvms_ar_")
    cwd = os.getcwd()
    os.chdir(workdir)
    stub.reset()
    st = stub.install(secrets if secrets is not None else GH)
    st.session_state.update({
        "authenticated": True, "user_type": "admin", "user_email": "Hussein.ali77121@gmail.com",
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


def V(i, phone, d, status="تمت", **kw):
    rec = {"id": i, "created_at": f"{d}T10:00:00", "name": "عميل أرشيف", "age": "35", "age_unit": "سنة",
           "phone": phone, "visit_date": d, "visit_time": "10:00 AM", "branch": "Diamond", "status": status,
           "doctor_name": "حسين علي", "address": "الشيخ زايد", "location_link": "",
           "selected_labs_text": "CBC — 400 جنيه", "notes": "", "labs_price_before": 400,
           "labs_price_after": 400, "transport_fee": 0, "total_price": 400, "deleted_at": None}
    rec.update(kw)
    return rec


PH = "01011112222"
ARCH1 = {"visits": [V("a1", PH, "2026-05-03"), V("a2", PH, "2026-05-20"),
                    V("a3", "01099990000", "2026-05-10"), V("a4", PH, "2026-05-25", deleted_at="2026-06-01")]}
ARCH2 = {"visits": [V("b1", PH, "2026-04-02", status="ملغية"), V("b2", PH, "2026-04-15")]}
FILES = {"archive/Visits_upto_2026-05-31.json": ARCH1, "archive/Visits_upto_2026-04-30.json": ARCH2}


def patch_gh(app, files=FILES, broken=()):
    app._list_archive_files_strict = lambda: (sorted(files.keys(), reverse=True), "")

    def fake_get(path):
        if path in broken or path not in files:
            return None, 500, "HTTP 500"
        return json.loads(json.dumps(files[path])), 200, ""
    app._gh_get_json = fake_get


def n(conn, sql, *a):
    return conn.execute(sql, a).fetchone()[0]


# ── ① التحميل ───────────────────────────────────────────────────────────────
print("① load_archive_index")
app, ss, err, wd = run_app("home")
patch_gh(app)
conn = app.get_connection()
visits_before = n(conn, "SELECT COUNT(*) FROM visits")
r = app.load_archive_index()
check("نجح وحمّل ملفين", (r["ok"], r["files"]), (True, 2))
check("اتحمّل 5 زيارات (المحذوفة اتخطّت)", r["visits"], 5)
check("الجدول المنفصل فيه 5", n(conn, "SELECT COUNT(*) FROM visits_archive"), 5)
check("جدول visits ماتلمسش", n(conn, "SELECT COUNT(*) FROM visits"), visits_before)
r2 = app.load_archive_index()
check("التكرار آمن (نفس العدد)", n(conn, "SELECT COUNT(*) FROM visits_archive"), 5)

# ── ② البحث ─────────────────────────────────────────────────────────────────
print("\n② تاريخ العميل / التصنيف / النشاط")
h = app.fetch_client_history(PH)
check("زيارات العميل من الأرشيف (من الملفين)", sorted(x["id"] for x in h), ["a1", "a2", "b1", "b2"])
check("مرتّبة من الأحدث", [x["visit_date"] for x in h], ["2026-05-20", "2026-05-03", "2026-04-15", "2026-04-02"])
check("limit", [x["id"] for x in app.fetch_client_history(PH, limit=2)], ["a2", "a1"])
check("exclude_id", "a2" in [x["id"] for x in app.fetch_client_history(PH, exclude_id="a2")], False)
check("بيانات كاملة للـ autofill", (h[0]["name"], h[0]["address"], h[0]["doctor_name"]),
      ("عميل أرشيف", "الشيخ زايد", "حسين علي"))
check("عميل مالوش تاريخ", app.fetch_client_history("01000000001"), [])

# زيارة حية جديدة لنفس العميل + نسخة محمّلة يدويًا بنفس id (من «حمّل الأرشيف للعرض») → مفيش تكرار
app.st.session_state.user_email = "Hussein.ali77121@gmail.com"
today = date.today()
live = V("L1", PH, (today - timedelta(days=3)).isoformat(), status="تمت", created_at=today.isoformat() + "T09:00:00")
app.insert_visit(live, sync=False)
app._load_insert_visit(conn, V("a2", PH, "2026-05-20"), upsert=True, archived=1)
conn.commit()
h = app.fetch_client_history(PH)
ids = [x["id"] for x in h]
check("الحية + الأرشيف مرتّبين من غير تكرار", (ids[0], ids.count("a2"), len(ids)), ("L1", 1, 5))

# التصنيف: تمت = L1 + a1 + a2 + b2 = 4 (b1 ملغية) → «متكرر»
app.st.session_state.pop(f"_ctag_{PH}", None)
check("التصنيف بيعدّ الأرشيف (4 زيارات تمت)", app.get_client_tag(PH), "🌟 عميل متكرر")
check("عميل أرشيف بس (زيارة واحدة تمت) → منتظم", (app.st.session_state.pop("_ctag_01099990000", None), app.get_client_tag("01099990000"))[1], "⭐ عميل منتظم")
check("عميل جديد فعلًا", app.get_client_tag("01000000002"), "🆕 عميل جديد")

# النشاط: الأحدث بين الحي والأرشيف
check("النشاط من الزيارة الحية (3 أيام)", "🟢 نشط (3 يوم)", app.get_churn_risk(PH))
conn.execute("UPDATE visits SET deleted_at='x' WHERE id='L1'"); conn.commit()
res = app.get_churn_risk(PH)
check("من غير حية: النشاط من الأرشيف (خطر عالي)", res.startswith("🔴 خطر عالي"), True)
check("عميل أرشيف بس بيظهر نشاطه", app.get_churn_risk("01099990000").startswith("🔴"), True)
check("من غير أي تاريخ", app.get_churn_risk("01000000003"), "⚪ لا يوجد تاريخ")

# ── ③ مفيش رقم بيتغيّر ──────────────────────────────────────────────────────
print("\n③ التقارير والنسخ الاحتياطي والإقلاع")
conn.execute("UPDATE visits SET deleted_at=NULL WHERE id='L1'"); conn.commit()
live_rows = app.fetch_visits()
live_rows = live_rows[0] if isinstance(live_rows, tuple) else live_rows
check("قايمة الزيارات: الحية بس", sorted(v["id"] for v in live_rows), ["L1"])
check("عدّ الإقلاع (جدول visits) ماتأثرش", n(conn, "SELECT COUNT(*) FROM visits"), visits_before + 2)
_cwd0 = os.getcwd(); os.chdir(wd)          # backup_to_json بيكتب ملف في مجلد الشغل — مش في الريبو
bk, _name = app.backup_to_json()
os.chdir(_cwd0)
check("النسخة الاحتياطية مفيهاش زيارات الأرشيف", {x["id"] for x in json.loads(bk)["visits"]} & {"a1", "b1", "b2", "a3"}, set())
check("تقرير السنة (استعلام visits) مفيهوش الأرشيف",
      n(conn, "SELECT COUNT(*) FROM visits WHERE visit_date LIKE '2026-04%'"), 0)

# ── ④ فشل جزئي / من غير secrets ─────────────────────────────────────────────
print("\n④ الفشل")
app2, _, _, _ = run_app("home")
patch_gh(app2, broken={"archive/Visits_upto_2026-04-30.json"})
r = app2.load_archive_index()
check("ملف فاشل → ok False والتاني اتحمّل", (r["ok"], r["files"], r["visits"], len(r["failed"])), (False, 1, 3, 1))
check("رسالة الخطأ بتسمّي الملف", "2026-04-30" in r["err"], True)
patch_gh(app2)
r = app2.load_archive_index()
check("إعادة المحاولة بتكمّل", (r["ok"], app2.get_connection().execute("SELECT COUNT(*) FROM visits_archive").fetchone()[0]), (True, 5))

app3, _, _, _ = run_app("home", secrets=NOGH)
r = app3.load_archive_index()
check("من غير secrets → رسالة من غير كراش", (r["ok"], "github_token" in r["err"]), (False, True))
check("البحث من غير فهرس بيشتغل", app3.fetch_client_history(PH), [])
check("التصنيف من غير فهرس", app3.get_client_tag(PH), "🆕 عميل جديد")

app4, _, _, _ = run_app("home")
app4._list_archive_files_strict = lambda: ([], "")
r = app4.load_archive_index()
check("مفيش ملفات أرشيف → ok من غير خطأ", (r["ok"], r["files"], r["visits"]), (True, 0, 0))
app4._list_archive_files_strict = lambda: (None, "URLError: انقطاع")
r = app4.load_archive_index()
check("فشل قراءة قايمة الأرشيف ≠ «مفيش أرشيف» (مايتعلّمش ok)", (r["ok"], "انقطاع" in r["err"]), (False, True))

# ── ⑤ صفحة «زيارة جديدة» ────────────────────────────────────────────────────
print("\n⑤ صفحة زيارة جديدة — عميل زياراته في الأرشيف بس")
appA, _, _, wdA = run_app("home", secrets=NOGH)
connA = appA.get_connection()
appA._ensure_archive_index_table(connA)
for fobj in FILES.values():
    for rec in fobj["visits"]:
        if not rec.get("deleted_at"):
            connA.execute("INSERT OR REPLACE INTO visits_archive (id,phone,visit_date,status,rec) VALUES (?,?,?,?,?)",
                          (rec["id"], rec["phone"], rec["visit_date"], rec["status"], json.dumps(rec, ensure_ascii=False)))
connA.commit()
check("مفيش أي زيارة حية للعميل ده", n(connA, "SELECT COUNT(*) FROM visits WHERE phone=?", PH), 0)
run_app("new", secrets=NOGH, workdir=wdA, state={"prefill": {"phone": PH}})
md = " ".join(str(c[1][0]) for c in stub.CALLS if c[0] == "markdown" and c[1])
check("كارت «هذا العميل موجود في النظام»", "هذا العميل موجود في النظام" in md, True)
check("اسم العميل وآخر زيارة من الأرشيف", ("عميل أرشيف" in md, "حسين علي" in md), (True, True))
labels = [c[1][0] for c in stub.CALLS if c[0] == "button"]
check("زرار «استخدم بياناته السابقة» ظاهر", "✅ استخدم بياناته السابقة" in labels, True)
run_app("new", secrets=NOGH, workdir=wdA, state={"prefill": {"phone": "01055550000"}})
md = " ".join(str(c[1][0]) for c in stub.CALLS if c[0] == "markdown" and c[1])
check("عميل جديد فعلًا: مفيش كارت", "هذا العميل موجود في النظام" in md, False)

# صفحة الأدمن: فهرس الأرشيف ظاهر
run_app("home", secrets=NOGH, workdir=wdA)
md = " ".join(str(c[1][0]) for c in stub.CALLS if c[0] in ("caption", "markdown") and c[1])
labels = [c[1][0] for c in stub.CALLS if c[0] == "button"]
check("زرار «تحديث فهرس الأرشيف» للأدمن", "🔄 تحديث فهرس الأرشيف" in labels, True)
check("سطر حالة الفهرس بيعرض عدد الزيارات والعملاء", "فهرس الأرشيف: 5 زيارة لـ 2 عميل" in md, True)

print()
if _FAILS:
    print(f"❌ {len(_FAILS)} اختبار فشل:")
    for f in _FAILS:
        print("   -", f)
    sys.exit(1)
print("✅ كل اختبارات فهرس الأرشيف نجحت")
