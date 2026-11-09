# -*- coding: utf-8 -*-
"""
tests_table.py — المرحلة 3 من الواجهة: جدول الزيارات العريض

  ① visit_table_html: الأعمدة / pills الحالة والفرع والتحصيل / الإلغاء بأي إملاء / الهروب من HTML
  ② صفوف بايظة وقيم غريبة (من غير كراش) + حجم الناتج
  ③ التكامل في الرئيسية: خيار «🧾 جدول» + اختيار الزيارة وفتحها + الكروت والقائمة المدمجة زي ما هم

التشغيل:  python3 tests_table.py
"""
import os
import sys
import time
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


SECRETS = {"admin_password": "x", "allowed_emails": ["Hussein.ali77121@gmail.com", "Orangelab511@gmail.com"]}
MODS = ("app", "core", "import_rules", "phone_utils", "lab_picker", "quick_panels", "doctors_sync",
        "email_backup", "login_theme", "easter_eggs", "device_auth", "labs_price_list")


def run_app(workdir, mode=None, user_type="admin", buttons=()):
    """mode = القيمة اللي الـradio «طريقة العرض» هيرجّعها (الـstub بيرجّع أول خيار دايمًا)."""
    cwd = os.getcwd()
    os.chdir(workdir)
    stub.reset()
    st = stub.install(SECRETS)
    orig_radio = stub.radio
    if mode:
        st.radio = lambda label="", options=(), *a, **k: mode if k.get("key") == "main_view_mode" else orig_radio(label, options, *a, **k)
    em = {"admin": "Hussein.ali77121@gmail.com", "diamond": "Orangelab511@gmail.com"}[user_type]
    st.session_state.update({
        "authenticated": True, "user_type": user_type, "user_email": em, "page": "home", "need_password": False,
        "_skip_auto_login": True, "current_page": 1, "page_size": 20, "total_visits": 0, "prefill": {},
        "selected_id": None, "selected_client_phone": "", "search_q": "",
    })
    stub.BUTTON_TRUE.update(buttons)
    for m in MODS:
        sys.modules.pop(m, None)
    app, err = None, None
    try:
        app = importlib.import_module("app")
    except (stub._Rerun, stub._Stop) as e:
        err = e
        app = sys.modules.get("app")
    finally:
        os.chdir(cwd)
        st.radio = orig_radio
    return app, st.session_state, err


def md_all():
    return " ".join(str(c[1][0]) for c in stub.CALLS if c[0] == "markdown" and c[1])


T = date.today().isoformat()
Y = (date.today() - timedelta(days=3)).isoformat()


def V(i, **kw):
    d = dict(id=f"t{i}", visit_time="10:00 AM", visit_date=T, name=f"عميل {i}", phone=f"0101000{i:04d}", address="الحصري",
             district="", branch="La Cite", status="مجدولة", total_price=400, payment_status="غير مدفوع", paid_amount=0)
    d.update(kw)
    return d


wd = tempfile.mkdtemp(prefix="hvms_tbl_")
app, ss, err = run_app(wd)

# ── ① الجدول ────────────────────────────────────────────────────────────────
print("① visit_table_html")
h = app.visit_table_html([V(1, status="تمت", payment_status="مدفوع", total_price=1200, paid_amount=1200)], title="🧾 الزيارات (1)")
check("8 أعمدة بالعناوين", all(t in h for t in ("الوقت", "العميل", "الهاتف", "العنوان", "الفرع", "الحالة", "الإجمالي", "التحصيل")), True)
check("العنوان (title) ظاهر", "🧾 الزيارات (1)" in h, True)
check("pill «تمت» أخضر", 'background:#E6F6EC;color:#1E8449">تمت' in h, True)
check("pill الفرع La Cite", "#FDEBDD" in h and "La Cite" in h, True)
check("الإجمالي منسّق", "1,200 ج.م" in h, True)
check("pill «مدفوع»", "✓ مدفوع" in h, True)
check("علامة التوسيع للصفحة", 'class="vt-wide"' in h and ":has(.vt-wide)" in h, True)
check("اليوم بدل التاريخ", ("اليوم" in h, T in h), (True, False))
h2 = app.visit_table_html([V(2, visit_date=Y)])
check("زيارة قديمة: التاريخ كامل", (Y in h2, "اليوم" in h2), (True, False))

for stt, label, color in (("في الطريق", "في الطريق 🚗", "#C86400"), ("مجدولة", "مجدولة 🕒", "#1F6FB5"),
                          ("ملغية", "ملغية ✕", "#C0392B"), ("تمت", "تمت ✓", "#1E8449")):
    check(f"pill الحالة {stt}", (label in app.visit_table_html([V(3, status=stt)]), color in app.visit_table_html([V(3, status=stt)])), (True, True))
for variant in ("ملغيه", " ملغية ", "ملغي", "ملغاة", "Cancelled", "تم الإلغاء"):
    hv = app.visit_table_html([V(4, status=variant, payment_status="غير مدفوع", total_price=900)])
    check(f"إلغاء بإملاء {variant!r} → pill «ملغية» وتحصيل «—»", ("ملغية ✕" in hv, "غير مدفوع" in hv), (True, False))
hs = app.visit_table_html([V(5, status="حالة غريبة")])
check("حالة غريبة → pill رمادي بنفس النص", ("حالة غريبة" in hs, "#EEF0F2" in hs), (True, True))
hp = app.visit_table_html([V(6, payment_status="مدفوع جزئياً", total_price=800, paid_amount=300)])
check("دفع جزئي: «جزئي» + المتبقي 500", ("جزئي" in hp, "متبقي 500" in hp), (True, True))
hp2 = app.visit_table_html([V(6, payment_status="مدفوع جزئياً", total_price=100, paid_amount=500)])
check("دفع جزئي بزيادة: المتبقي 0 مش سالب", "متبقي 0" in hp2, True)
hu = app.visit_table_html([V(7, payment_status="غير مدفوع")])
check("غير مدفوع", ("غير مدفوع" in hu, "#FDECEA" in hu), (True, True))
hb = app.visit_table_html([V(8, branch="Diamond"), V(9, branch="La Cité"), V(10, branch="")])
check("فرع Diamond أزرق", "#E3EEFB" in hb, True)
check("La Cité بحرف é بيتعرف", hb.count("#FDEBDD"), 1)
check("فرع فاضي → شرطة", 'class="vt-br"><span class="vt-empty">—' in hb, True)
check("AM → ص / PM → م", (app._vt_time("10:00 AM"), app._vt_time("2:30 pm"), app._vt_time("14:00"), app._vt_time(None), app._vt_time("")),
      ("10:00 ص", "2:30 م", "14:00", "", ""))
hd = app.visit_table_html([V(11, district="الحي 8", address="عمارة 5")])
check("العنوان = الحي — العنوان", "الحي 8 — عمارة 5" in hd, True)

# الهروب من HTML (أمان)
hx = app.visit_table_html([V(12, name='<img src=x onerror=alert(1)>', address='<script>alert(1)</script>" onmouseover="alert(2)', phone='"><b>', branch="<i>x</i>")])
from html.parser import HTMLParser


class _P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.tags, self.attrs = set(), set()

    def handle_starttag(self, tag, attrs):
        self.tags.add(tag)
        self.attrs.update(a for a, _ in attrs)


_p = _P()
_p.feed(hx)
check("مفيش img/script/i في الـDOM الناتج", _p.tags & {"img", "script", "i"}, set())
check("مفيش أي attribute حدث (onerror/onmouseover…) — حتى جوّه title", {a for a in _p.attrs if a.startswith("on")}, set())
check("الـattributes المستخدمة بس class/style/title", _p.attrs <= {"class", "style", "title"}, True)
check("علامة الاقتباس في العنوان اتهرّبت", "&quot; onmouseover=&quot;alert(2)" in hx, True)
check("الاسم ظاهر كنص مهروب", "&lt;img" in hx, True)

# ── ② صفوف بايظة وحجم ───────────────────────────────────────────────────────
print("\n② صفوف بايظة وقيم غريبة")
hbad = app.visit_table_html([V(13), None, "نص", 123, V(14)])
check("صفوف مش dict اتخطّت + تحذير بالعدد", (hbad.count("<tr><td"), "اتخطّينا 3" in hbad), (2, True))
check("قائمة فاضية/None من غير كراش", ("<tbody></tbody>" in app.visit_table_html([]), "<tbody></tbody>" in app.visit_table_html(None)), (True, True))
hw = app.visit_table_html([V(15, total_price="abc", paid_amount=None, visit_time=None, visit_date=None, name=None, phone=None,
                             address=None, status=None, payment_status=None, branch=None)])
check("قيم None وسعر نصي → صف شغال و0 ج.م", ("<tr><td" in hw, "0 ج.م" in hw), (True, True))
check("status=None → مجدولة", "مجدولة" in hw, True)
big = [V(i, name=f"عميل رقم {i}", address="شارع طويل " * 5) for i in range(300)]
t0 = time.time()
hb2 = app.visit_table_html(big)
check("300 صف: أقل من نص ثانية", time.time() - t0 < 0.5, True)
check("حجم الصف أقل من 1.2KB", len(hb2.encode()) / 300 < 1200, True)

# ── ③ التكامل في الرئيسية ───────────────────────────────────────────────────
print("\n③ التكامل في الرئيسية")
conn = app.get_connection()
seed = [V(i, status=("تمت" if i % 2 else "مجدولة"), name=f"زيارة {i}") for i in range(1, 6)]
for r in seed:
    r.update(created_at=T + "T10:00:00", age="30", age_unit="سنة", location_link="", selected_labs_text="CBC — 400 جنيه", notes="",
             labs_price_before=400, labs_price_after=400, transport_fee=0, doctor_name="حسين علي", branch="Diamond")
    app._load_insert_visit(conn, r, upsert=False)
conn.commit()

app, ss, err = run_app(wd)
md = md_all()
check("الوضع الافتراضي (كروت): مفيش جدول", ("vt-wrap" in md, '<div class="visit-card">' in md), (False, True))
radio = [c for c in stub.CALLS if c[2].get("key") == "main_view_mode"]
check("راديو «طريقة العرض» موجود مرة واحدة", len(radio), 1)
check("الخيارات التلاتة في الكود (الكروت والقائمة زي ما هم + جدول)",
      all(t in open(os.path.join(HERE, "app.py"), encoding="utf-8").read() for t in ('["🗂️ كروت","📋 قائمة مدمجة","🧾 جدول"]',)), True)
app, ss, err = run_app(wd, mode="📋 قائمة مدمجة")
md = md_all()
check("القائمة المدمجة زي ما هي", ('<div class="visit-row">' in md, "vt-wrap" in md), (True, False))
app, ss, err = run_app(wd, mode="🧾 جدول")
md = md_all()
check("وضع الجدول: جدول بـ5 صفوف", ("vt-wrap" in md, md.count("<tr><td")), (True, 5))
check("وضع الجدول: مفيش كروت ولا قائمة", ('<div class="visit-card">' in md, '<div class="visit-row">' in md), (False, False))
sel = [c for c in stub.CALLS if c[0] == "selectbox" and c[2].get("key") == "tbl_pick"]
check("اختيار الزيارة: selectbox واحد", len(sel), 1)
keys = [c[2].get("key") for c in stub.CALLS if c[0] == "button"]
check("زرّين بس للجدول (مش زرار لكل صف) ومفيش زراير الكروت", ("tbl_open" in keys, "tbl_profile" in keys, any(str(k).startswith(("o_", "cp_", "lo_")) for k in keys)), (True, True, False))
app, ss, err = run_app(wd, mode="🧾 جدول", buttons={"tbl_open"})
check("فتح → صفحة التفاصيل + rerun", (ss.get("page"), isinstance(err, stub._Rerun), bool(ss.get("selected_id"))), ("detail", True, True))
opened = ss.get("selected_id")
check("الـid المفتوح واحد من الزيارات المعروضة", opened in {f"t{i}" for i in range(1, 6)}, True)
app, ss, err = run_app(wd, mode="🧾 جدول", buttons={"tbl_profile"})
check("بروفايل → صفحة العميل + رقمه", (ss.get("page"), bool(ss.get("selected_client_phone"))), ("client_profile", True))
app, ss, err = run_app(wd, mode="🧾 جدول", user_type="diamond")
check("مستخدم فرع: الجدول شغال برضه", "vt-wrap" in md_all(), True)

print()
if _FAILS:
    print(f"❌ {len(_FAILS)} اختبار فشل")
    sys.exit(1)
print("✅ كل اختبارات جدول الزيارات نجحت")
