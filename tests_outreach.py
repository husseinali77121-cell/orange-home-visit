# -*- coding: utf-8 -*-
"""
tests_outreach.py — إضافات نوفمبر 2026 (الجزء التاني)

  ① records_sync: دمج المتابعات وسجل النشاط (عمره ما يقل)
  ② outreach: تذكير بكرة · كشف الدكتور والنقدية · عملاء مرجعوش
  ③ المتابعات + السجل على GitHub (GitHub وهمي في الذاكرة)
  ④ الصفحات: اليوم (تذكير + كشف) · المتابعات (عملاء مرجعوش)
  ⑤ بدل الانتقال بالأحمر (PDF + Excel)

التشغيل:  python3 tests_outreach.py
"""
import io
import os
import sys
import shutil
import tempfile
import importlib
import urllib.parse
from datetime import date, timedelta

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _stub_streamlit as stub
import records_sync as rs
import outreach as oc

_FAILS = []


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


TODAY = date.today()
T = TODAY.isoformat()
TOM = (TODAY + timedelta(days=1)).isoformat()

# ══════════════════════════════════════════════════════════════════════════════
print("\n① records_sync")
fa = {"id": "a", "follow_up_date": "2026-11-01", "client_name": "س", "done": 0}
fb = {"id": "b", "follow_up_date": "2026-11-02", "client_name": "ص", "done": 0}
m = rs.merge_followups([fa, {**fb, "done": 1}], [{**fa, "done": 1}, fb,
                                                 {"id": "c", "follow_up_date": "2026-11-03"}])
check("اتحاد بالـ id", [r["id"] for r in m], ["a", "b", "c"])
check("«تمت» بتكسب من الناحيتين", [r["done"] for r in m], [1, 1, 0])
check("صف من غير تاريخ بيتشال", rs.merge_followups([{"id": "x"}], []), [])
ins, done = rs.plan_fu_pull([fa], [{**fa, "done": 1}, fb])
check("الإقلاع: ضيف الناقص واقفل اللي اتقفل", ([r["id"] for r in ins], done), (["b"], ["a"]))
check("الإقلاع: مابيفتحش متابعة مقفولة", rs.plan_fu_pull([{**fa, "done": 1}], [fa]), ([], []))
check("مفيش جديد = مفيش رفع", rs.fu_differs([fa, fb], rs.merge_followups([fa, fb], [fa])), False)
check("متابعة جديدة = رفع", rs.fu_differs([fa], rs.merge_followups([fa], [fb])), True)
a1 = {"user_email": "u", "action": "update", "table_name": "visits", "record_id": "1",
      "timestamp": "2026-11-10T10:00:00"}
a2 = {**a1, "timestamp": "2026-11-10T09:00:00"}
ma = rs.merge_audit([a1], [a1, a2, {"timestamp": ""}])
check("السجل: من غير تكرار ومرتّب بالوقت", [r["timestamp"] for r in ma],
      ["2026-11-10T09:00:00", "2026-11-10T10:00:00"])
check("السجل: الناقص محليًا", len(rs.audit_missing_locally([a1], [a1, a2])), 1)
check("الشهر اللي قبله", (rs.prev_month("2026-01"), rs.prev_month("2026-11")), ("2025-12", "2026-10"))

# ══════════════════════════════════════════════════════════════════════════════
print("\n② outreach")


def V(i, **o):
    v = {"id": f"v{i}", "name": f"عميل {i}", "phone": f"0100000000{i}", "visit_date": TOM,
         "visit_time": "10:00 AM", "doctor_name": "حسين علي", "branch": "La Cite",
         "city": "6 أكتوبر", "district": "الحي الأول", "address": "شارع 1",
         "selected_labs_text": "CBC — 400 جنيه\nFerritin — 400 جنيه",
         "total_price": 900, "paid_amount": 0, "payment_status": "غير مدفوع",
         "payment_method": "", "status": "مجدولة"}
    v.update(o)
    return v


msg = oc.reminder_message(V(1, visit_time="11:30 AM"))
check("التذكير: الاسم والميعاد والدكتور والمنطقة", all(x in msg for x in
      ("عميل 1", "11:30 AM", "حسين علي", "الحي الأول", oc.day_label(TOM))), True)
check("التذكير: من غير تحاليل ولا أسعار", ("CBC" in msg, "جنيه" in msg, "900" in msg), (False, False, False))
check("التذكير قصير (≤ 7 سطور)", len(msg.splitlines()) <= 7, True)
cand = oc.reminder_candidates([V(1, visit_time="1:00 PM"), V(2, visit_time="9:00 AM"),
                               V(3, status="ملغية"), V(4, status="تمت"), V(5, visit_date=T)], TOM)
check("مرشحين التذكير: بكرة + لسه + بالترتيب", [v["id"] for v in cand], ["v2", "v1"])

day = [V(1, visit_date=T, visit_time="1:00 PM", district="الحي الثاني"),
       V(2, visit_date=T, visit_time="9:00 AM"),
       V(3, visit_date=T, visit_time="", district="الحي العاشر"),
       V(4, visit_date=T, visit_time="", district="الحي الأول"),
       V(5, visit_date=T, status="ملغية"),
       V(6, visit_date=T, doctor_name="محمد شفيق"),
       V(7, visit_date=T, visit_time="11:00 AM", payment_status="مدفوع", payment_method="نقدي",
         paid_amount=900),
       V(8, visit_date=T, visit_time="12:00 PM", payment_status="مدفوع", payment_method="محفظة إلكترونية",
         paid_amount=900),
       V(9, visit_date=T, visit_time="12:30 PM", payment_status="مدفوع جزئياً", payment_method="نقدي",
         paid_amount=300)]
txt, sm = oc.doctor_day_sheet(day, "حسين علي", T, lambda l: l.split(" — ")[0])
check("الكشف: الدكتور بس ومن غير الملغية", sm["visits"], 7)
check("الترتيب: من غير وقت (بالمنطقة) ثم بالوقت", sm["ids"], ["v4", "v3", "v2", "v7", "v8", "v9", "v1"])
check("المتبقي = غير مدفوع كامل + باقي الجزئي", sm["remaining"], 900 * 4 + 600)
check("النقدي المتحصّل = المدفوع كاش بس (مش المحفظة)", sm["cash"], 900 + 300)
check("المطلوب تسليمه = المتبقي + النقدي", sm["to_hand_over"], 4200 + 1200)
check("الكشف فيه أسماء التحاليل من غير أسعار", ("CBC • Ferritin" in txt, "400 جنيه" in txt), (True, False))
check("المدفوع بالمحفظة بيبان", "✅ مدفوع (محفظة إلكترونية)" in txt, True)
check("دكاترة اليوم", oc.doctors_on_day(day, T), [("حسين علي", 7), ("محمد شفيق", 1)])


def ago(n):
    return (TODAY - timedelta(days=n)).isoformat()


hist = [V(1, visit_date=ago(100), name="قديم"), V(1, visit_date=ago(200), name="قديم"),
        V(2, visit_date=ago(95), branch="Diamond"),
        V(3, visit_date=ago(120)), V(3, visit_date=(TODAY + timedelta(days=3)).isoformat()),
        V(4, visit_date=ago(30)),
        V(5, visit_date=ago(150), status="ملغية"),
        {**V(6, visit_date=ago(400)), "deleted_at": "x"}]
lap = oc.lapsed_clients(hist, TODAY, 90)
check("مرجعوش من 90+: من غير اللي عنده زيارة جاية والقريب والملغي والمحذوف",
      [c["phone"] for c in lap], ["01000000002", "01000000001"])
check("عدد الزيارات وآخر تاريخ", (lap[1]["visits"], lap[1]["days"], lap[1]["name"]), (2, 100, "قديم"))
check("فلتر الفرع (فرع آخر زيارة)", [c["phone"] for c in oc.lapsed_clients(hist, TODAY, 90, "Diamond")],
      ["01000000002"])
lm = oc.lapsed_message({"name": "قديم", "days": 100})
check("رسالة وحشتنا: الاسم والمدة", ("قديم" in lm, "3 شهور" in lm), (True, True))

# ══════════════════════════════════════════════════════════════════════════════
SECRETS = {"admin_password": "x", "branch_password": "y", "device_secret": "z",
           "allowed_emails": ["Hussein.ali77121@gmail.com", "Orangelab511@gmail.com",
                              "Huossein721@gmail.com"],
           "github_token": "", "github_repo": "", "use_monthly_sync": False}
USERS = {"admin": "Hussein.ali77121@gmail.com", "diamond": "Orangelab511@gmail.com",
         "lacite": "Huossein721@gmail.com"}
MODS = ("app", "core", "import_rules", "phone_utils", "lab_picker", "quick_panels",
        "doctors_sync", "email_backup", "login_theme", "easter_eggs", "device_auth",
        "labs_price_list", "repair_data", "records_sync", "outreach", "pdf_export")
PRESS = set()
_ob = stub.button


def _button(label="", *a, **k):
    return _ob(label, *a, **k) or any(p in str(label) for p in PRESS)


stub.button = _button
_oe = stub.expander


def _expander(label="", *a, **k):
    stub.CALLS.append(("expander", (label,), k))
    return _oe(label, *a, **k)


stub.expander = _expander


def run(page, utype, extra=None, keys=(), press=()):
    stub.reset()
    st = stub.install(SECRETS)
    stub.BUTTON_TRUE.update(keys)
    PRESS.clear(); PRESS.update(press)
    st.session_state.update({
        "authenticated": True, "user_type": utype, "user_email": USERS[utype],
        "page": page, "need_password": False, "_skip_auto_login": True,
        "current_page": 1, "page_size": 20, "total_visits": 0,
        "prefill": {}, "selected_id": None, "selected_client_phone": "", "search_q": "",
    })
    if extra:
        st.session_state.update(extra)
    for m_ in MODS:
        sys.modules.pop(m_, None)
    how = "ok"
    try:
        importlib.import_module("app")
    except stub._Rerun:
        how = "rerun"
    except stub._Stop:
        how = "stop"
    return how


def md():
    return " ".join(str(c[1][0]) for c in stub.CALLS if c[0] == "markdown" and c[1])


def calls(kind):
    return [c for c in stub.CALLS if c[0] == kind]


class FakeGH:
    """GitHub وهمي: path → (payload, sha)."""
    def __init__(self):
        self.files, self.puts, self.n = {}, [], 0
        self.fail_put = False

    def get(self, path):
        if path not in self.files:
            return None, 404, "HTTP 404"
        return self.files[path][0], 200, ""

    def sha(self, path):
        return self.files.get(path, (None, ""))[1]

    def put(self, path, payload, message, expected_sha=None):
        if self.fail_put:
            return False
        if expected_sha is not None and expected_sha != self.sha(path):
            return False
        self.n += 1
        import json
        self.files[path] = (json.loads(json.dumps(payload)), f"sha{self.n}")
        self.puts.append(path)
        return True


def wire(app, gh):
    app.GITHUB_TOKEN, app.GITHUB_REPO = "t", "o/r"
    app._gh_get_json = gh.get
    app._get_github_file_sha = gh.sha
    app._gh_put_json = gh.put


workdir = tempfile.mkdtemp(prefix="hvms_outreach_")
os.chdir(workdir)
try:
    print("\n③ المتابعات + السجل على GitHub")
    run("home", "admin")
    app = sys.modules["app"]
    gh = FakeGH()
    wire(app, gh)
    stt = app._records_state()
    stt.update(audit_pushed_id=0, audit_last_try=0.0, fu_dirty=False)
    gh.files["followups.json"] = ({"follow_ups": [
        {"id": "remote1", "follow_up_date": T, "client_name": "من جهاز تاني", "done": 0}]}, "sha0")
    app._GH_STATE["last_error"] = "قبل"
    fid = app.insert_follow_up("", "عميل جديد", "01011112222", T, "سبب", created_by="t")
    fus = {r["id"]: r for r in gh.files["followups.json"][0]["follow_ups"]}
    check("إضافة متابعة → اترفعت فورًا ومن غير ما تمسح بتاعة الجهاز التاني",
          (fid in fus, "remote1" in fus), (True, True))
    check("_GH_STATE مااتلمسش (معزول عن الزيارات)", app._GH_STATE["last_error"], "قبل")
    app.complete_follow_up(fid)
    check("إقفال متابعة → done=1 على GitHub",
          {r["id"]: r["done"] for r in gh.files["followups.json"][0]["follow_ups"]}[fid], 1)
    n0 = len(gh.puts)
    app._followups_after_change("noop")
    check("مفيش تغيير → مفيش commit", len(gh.puts), n0)
    gh.fail_put = True
    app.insert_follow_up("", "تاني", "01033334444", T, "سبب")
    check("فشل الرفع → متعلّم ويتعاد", (stt["fu_dirty"], app._records_status("fu")[0]), (True, "err"))
    gh.fail_put = False
    stt["audit_last_try"] = 0
    app._records_tick()
    check("الإعادة في الـ tick نجحت", (stt["fu_dirty"],
          len(gh.files["followups.json"][0]["follow_ups"])), (False, 3))

    ym = TODAY.strftime("%Y-%m")
    apath = f"audit/{ym}.json"
    check("السجل اترفع في الـ tick", apath in gh.files, True)
    n_aud = len(gh.files[apath][0]["entries"])
    check("سطور السجل = اللي محليًا", n_aud, app.get_connection().execute(
        "SELECT COUNT(*) FROM audit_log WHERE substr(timestamp,1,7)=?", (ym,)).fetchone()[0])
    n1 = len(gh.puts)
    stt["audit_last_try"] = 0
    app._records_tick()
    check("مفيش سطور جديدة → مفيش commit", len(gh.puts), n1)
    import time as _t
    stt["audit_last_try"] = _t.time()            # لسه رافع من ثانية
    app._log_audit("u", "update", "visits", "x1", details="جديد")
    app._records_tick()
    check("سطر جديد قبل مهلة الـ tick → لسه مارتفعش", len(gh.puts), n1)
    stt["audit_last_try"] = 0
    app._records_tick()
    check("بعد المهلة → اترفع", len(gh.files[apath][0]["entries"]), n_aud + 1)

    # الإقلاع على كونتينر جديد: الجداول فاضية → بتترجع من GitHub
    c = app.get_connection()
    c.execute("DELETE FROM follow_ups"); c.execute("DELETE FROM audit_log"); c.commit()
    prev = rs.prev_month(ym)
    gh.files[f"audit/{prev}.json"] = ({"entries": [{**a1, "timestamp": f"{prev}-15T10:00:00"}]}, "shaP")
    app._boot_pull_records.clear()
    r = app._boot_pull_records()
    check("الإقلاع رجّع المتابعات", c.execute("SELECT COUNT(*) FROM follow_ups").fetchone()[0], 3)
    check("الإقلاع رجّع المقفول مقفول", c.execute("SELECT done FROM follow_ups WHERE id=?", (fid,)).fetchone()[0], 1)
    check("الإقلاع رجّع سجل الشهرين", c.execute("SELECT COUNT(*) FROM audit_log").fetchone()[0], n_aud + 2)
    check("نتيجة الإقلاع ok", r.get("ok"), True)
    n2 = len(gh.puts)
    stt.update(audit_pushed_id=0, audit_last_try=0)
    app._records_tick()
    check("بعد الإقلاع: الرفع مابيعملش commit فاضي", len(gh.puts), n2)

    # ══════════════════════════════════════════════════════════════════════
    print("\n④ الصفحات")
    run("home", "admin")
    app = sys.modules["app"]
    c = app.get_connection()
    c.execute("DELETE FROM visits"); c.commit()

    def ins(**o):
        v = V(0)
        v.update({"age": 30, "age_unit": "سنة", "location_link": "", "notes": "", "extra_persons": "",
                  "labs_price_before": 900, "labs_price_after": 800, "transport_fee": 100,
                  "created_at": "2026-01-01T00:00:00"})
        v.update(o)
        app.insert_visit(v, sync=False)

    ins(id="t1", name="بكرة واحد", phone="01022220001", visit_date=TOM, visit_time="9:00 AM")
    ins(id="t2", name="بكرة دايموند", phone="01022220002", visit_date=TOM, branch="Diamond")
    ins(id="d1", name="النهاردة", phone="01022220003", visit_date=T, visit_time="10:00 AM")
    ins(id="o1", name="قديمة", phone="01022220009", visit_date=ago(120))
    run("today", "lacite")
    exps = [str(c_[1][0]) for c_ in calls("expander")]
    check("صفحة اليوم: تذكير بكرة (La Cite بس)", any("تذكير عملاء بكرة" in e and "(1)" in e for e in exps), True)
    links = [x for x in md().split('href="')[1:] if x.startswith("https://wa.me/")]
    rem = [urllib.parse.unquote(x.split('"')[0]) for x in links if "201022220001" in x]
    check("زرار تذكير للعميل برسالة التذكير", bool(rem) and "تذكير بالزيارة المنزلية" in rem[0], True)
    check("كشف الدكتور ظاهر", any("كشف اليوم للدكتور" in e for e in exps), True)
    codes = [str(c_[1][0]) for c_ in calls("code")]
    check("نص الكشف فيه زيارة النهاردة والحساب", bool(codes) and "النهاردة" in codes[0]
          and "المطلوب تسليمه للمعمل آخر اليوم" in codes[0], True)
    phone_hussein = app.get_doctor_phone("حسين علي")
    check("الكشف بيتبعت على رقم الدكتور", (not phone_hussein) or any(
          phone_hussein[-9:] in x.split('"')[0] for x in links), True)

    run("follow_ups", "lacite")
    check("المتابعات: عملاء مرجعوش", "قديمة" in md() and "من 120 يوم" in md(), True)
    how = run("follow_ups", "lacite", keys=("lap_fu_01022220009",))
    run("follow_ups", "lacite")
    app = sys.modules["app"]
    fus = app.fetch_follow_ups({"phone": "01022220009"})
    check("⏰ متابعة من القائمة → اتعملت متابعة", (how, len(fus), "مرجعش" in (fus[0]["reason"] if fus else "")),
          ("rerun", 1, True))
    check("بعد المتابعة: «عليه متابعة» ومن غير زرار تاني", ("عليه متابعة" in md(),
          any(c_[2].get("key") == "lap_fu_01022220009" for c_ in calls("button"))), (True, False))
    run("audit", "admin")
    check("سجل النشاط: سطر حالة الحفظ", any("GitHub" in str(c_[1][0]) for c_ in calls("caption") + calls("warning")), True)

    # ══════════════════════════════════════════════════════════════════════
    print("\n⑤ بدل الانتقال بالأحمر")
    import pdf_export as pe
    import pdfplumber
    vs = [V(i, visit_date=T, doctor_name=d, transport_fee=100, labs_price_after=800, status="تمت",
            extra_persons_text="") for i, d in enumerate(["حسين علي", "حسين علي", "محمد شفيق", "عبدالله"])]

    def red_cells(b):
        with pdfplumber.open(io.BytesIO(b)) as pdf:
            return sum(1 for r in pdf.pages[0].rects if r.get("fill")
                       and tuple(round(x, 2) for x in (r.get("non_stroking_color") or ())) == (0.99, 0.93, 0.93))
    from doctors_sync import norm_name
    b_red = pe.build_visits_pdf(vs, "x", "y", "z", transport_paid={norm_name("محمد شفيق")})
    check("PDF: خانة الانتقال حمرا لحسين وعبدالله بس", red_cells(b_red), 2)
    check("PDF: الملاحظة في عنوان الملخص", "مابيتصرفش" in (pe.TRANSPORT_NOTE), True)
    check("PDF من غير قائمة → مفيش أحمر", red_cells(pe.build_visits_pdf(vs, "x", "y", "z")), 0)
    run("home", "admin")
    app = sys.modules["app"]
    check("القائمة من إدارة الأطباء = محمد شفيق", app.transport_paid_names(), {norm_name("محمد شفيق")})
    c = app.get_connection()
    c.execute("DELETE FROM visits"); c.commit()
    for i, v in enumerate(vs):
        app.insert_visit({**V(0), **v, "id": f"r{i}", "phone": f"0103000000{i}", "age": 30, "age_unit": "سنة",
                          "location_link": "", "notes": "", "extra_persons": "", "labs_price_before": 900,
                          "total_price": 900, "created_at": "2026-01-01T00:00:00"}, sync=False)
    df, path = app.export_to_excel(date_from=T, date_to=T)
    from openpyxl import load_workbook
    ws = load_workbook(path).active
    reds = {}
    for row in ws.iter_rows():
        for cell in row:
            if cell.column == 6 and cell.font and cell.font.color is not None and \
                    str(cell.font.color.rgb or "").upper().endswith("C0392B"):
                reds[ws.cell(cell.row, 2).value] = cell.value
    check("Excel: الانتقال أحمر لحسين وعبدالله بس", sorted(reds), sorted(["حسين علي", "عبدالله"]))
    check("Excel: الأرقام زي ما هي", reds.get("حسين علي"), 200)
    n_, pdf_b, _fn, err = app.export_to_pdf(date_from=T, date_to=T)
    check("export_to_pdf بيلوّن من إدارة الأطباء", (err, red_cells(pdf_b)), ("", 2))
finally:
    os.chdir(HERE)
    shutil.rmtree(workdir, ignore_errors=True)

print()
if _FAILS:
    print(f"❌ فشل {len(_FAILS)}: {_FAILS}")
    sys.exit(1)
print("✅ كل اختبارات الإضافات نجحت")
