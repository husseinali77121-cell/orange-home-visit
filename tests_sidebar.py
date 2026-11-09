# -*- coding: utf-8 -*-
"""
tests_sidebar.py — المرحلة 2 من الواجهة: السايدبار الداكن

  ① نفس صفحات الشريط العلوي بالظبط لكل دور (AST) — السايدبار مايفتحش صفحة ممنوعة ولا ينقص صفحة
  ② الرسم الفعلي: الأزرار/المفاتيح/تمييز الصفحة الحالية/الأدوار/الفلاج
  ③ الضغط على الأزرار بيودّي للصفحة الصح (نفس go()) والخروج شغال
  ④ الـCSS: الشريط العلوي بيتخفي بس لما السايدبار مفتوح (شبكة الأمان) والسايدبار مخفي على الموبايل
  ⑤ الفلاج ui_sidebar = "0" بيرجّع الشكل القديم، وset_page_config

التشغيل:  python3 tests_sidebar.py
"""
import os
import sys
import ast
import tempfile
import importlib

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


USERS = {"admin": "Hussein.ali77121@gmail.com", "diamond": "Orangelab511@gmail.com",
         "lacite": "Huossein721@gmail.com", "other": "stranger@example.com"}
BASE_SECRETS = {"admin_password": "x", "allowed_emails": list(USERS.values())}


def run_app(page="home", user_type="admin", buttons=(), secrets=None, state=None):
    workdir = tempfile.mkdtemp(prefix="hvms_sb_")
    cwd = os.getcwd()
    os.chdir(workdir)
    stub.reset()
    sec = dict(BASE_SECRETS)
    sec.update(secrets or {})
    st = stub.install(sec)
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
    return app, st.session_state, err


def sb_buttons():
    """أزرار السايدبار المسجّلة: [(key, label, type)]"""
    return [(c[2].get("key"), c[1][0], c[2].get("type"))
            for c in stub.CALLS if c[0] == "button" and str(c[2].get("key", "")).startswith("sb_")]


# ── ① مطابقة الشريط العلوي (AST) ────────────────────────────────────────────
print("① السايدبار = الشريط العلوي (نفس الصفحات لكل دور)")
src = open(os.path.join(HERE, "app.py"), encoding="utf-8").read()
tree = ast.parse(src)


def go_pages(stmts):
    out = set()
    for s_ in stmts:
        for n in ast.walk(s_):
            if (isinstance(n, ast.Call) and isinstance(n.func, ast.Name) and n.func.id == "go"
                    and n.args and isinstance(n.args[0], ast.Constant)):
                out.add(n.args[0].value)
    return out


topnav = [n for n in ast.walk(tree) if isinstance(n, ast.With)
          and any(isinstance(i.context_expr, ast.Call) and getattr(i.context_expr.func, "attr", "") == "container"
                  and any(k.arg == "key" and getattr(k.value, "value", None) == "topnav" for k in i.context_expr.keywords)
                  for i in n.items)]
check("الشريط العلوي متلفّف في container(key='topnav') (مرة واحدة)", len(topnav), 1)
chain = [n for n in topnav[0].body if isinstance(n, ast.If)][0]
top_admin = go_pages(chain.body)
top_branch = go_pages(chain.orelse[0].body)
top_other = go_pages(chain.orelse[0].orelse)

app, ss, err = run_app("home")
for role, top in (("admin", top_admin), ("diamond", top_branch), ("lacite", top_branch)):
    side = {it[2] for it in app._sidebar_items(role, "📅 اليوم", 0)}
    check(f"{role}: صفحات السايدبار = صفحات الشريط العلوي {sorted(top)}", side, top)
check("مستخدم بلا دور: مفيش سايدبار (بيفضل على الشريط العلوي)", app._sidebar_items("other", "x", 0), [])
check("الفرعين مايشوفوش Dashboard/الأطباء/السجل",
      {it[2] for it in app._sidebar_items("diamond", "x", 0)} & {"dashboard", "manage_doctors", "audit"}, set())
check("عدّاد المتابعات في الاسم", [it[1] for it in app._sidebar_items("admin", "x", 3) if it[0] == "follow_ups"], ["⏰ متابعات (3)"])
check("من غير متابعات: من غير رقم", [it[1] for it in app._sidebar_items("admin", "x", 0) if it[0] == "follow_ups"], ["⏰ متابعات"])
check("اليوم بيستخدم نفس اللابل", [it[1] for it in app._sidebar_items("admin", "📅 اليوم (5)", 0) if it[0] == "today"], ["📅 اليوم (5)"])
check("كل المفاتيح فريدة", len({it[0] for it in app._sidebar_items("admin", "x", 0)}), 8)

# ── ② الرسم الفعلي ──────────────────────────────────────────────────────────
print("\n② الرسم الفعلي")
for role, n_items in (("admin", 8), ("diamond", 5), ("lacite", 5)):
    app, ss, err = run_app("home", role)
    b = sb_buttons()
    check(f"{role}: {n_items} زر + خروج", len(b), n_items + 1)
    check(f"{role}: مفاتيح sb_* فريدة", len({x[0] for x in b}), n_items + 1)
    check(f"{role}: الرئيسية primary والباقي secondary",
          ([x[0] for x in b if x[2] == "primary"], {x[2] for x in b[:-1] if x[2] != "primary"}), (["sb_home"], {"secondary"}))
    check(f"{role}: زر الخروج آخر زر", b[-1][0], "sb_logout")

app, ss, err = run_app("reports", "admin")
check("صفحة التقارير → زر التقارير هو الـprimary", [x[0] for x in sb_buttons() if x[2] == "primary"], ["sb_reports"])
app, ss, err = run_app("detail", "admin", state={"selected_visit_id": "x"})
check("صفحة التفاصيل → بتتعلّم تحت «الرئيسية»", [x[0] for x in sb_buttons() if x[2] == "primary"], ["sb_home"])

app, ss, err = run_app("home", "other")
check("بلا دور: مفيش أزرار سايدبار", sb_buttons(), [])
check("بلا دور: ولا CSS سايدبار", "stSidebar" in " ".join(str(c[1][0]) for c in stub.CALLS if c[0] == "markdown" and c[1]), False)

# محتوى السايدبار: الاسم + حالة المزامنة الحقيقية
app, ss, err = run_app("home", "admin")
md = " ".join(str(c[1][0]) for c in stub.CALLS if c[0] == "markdown" and c[1])
check("بطاقة العلامة + الدور", "sb-brand" in md and "مدير النظام" in md, True)
check("حالة المزامنة في السايدبار (من _sync_chip مش نص ثابت)", app._sync_chip()[2] in md, True)
check("الشريط العلوي لسه موجود في الكود (أزرار بدون مفاتيح sb_)",
      any(c[0] == "button" and c[1][0] == "🏠 الرئيسية" and not c[2].get("key") for c in stub.CALLS), True)

# ── ③ الضغط ─────────────────────────────────────────────────────────────────
print("\n③ الضغط على أزرار السايدبار")
for key, page in (("sb_reports", "reports"), ("sb_today", "today"), ("sb_follow_ups", "follow_ups"),
                  ("sb_dashboard", "dashboard"), ("sb_manage_doctors", "manage_doctors"), ("sb_audit", "audit"), ("sb_home", "home")):
    app, ss, err = run_app("new", "admin", buttons={key})
    check(f"{key} → صفحة {page} (+ st.rerun)", (ss.get("page"), isinstance(err, stub._Rerun)), (page, True))
app, ss, err = run_app("home", "admin", buttons={"sb_new"}, state={"prefill": {"x": 1}})
check("sb_new → فورم جديد بـ prefill فاضي", (ss.get("page"), ss.get("prefill")), ("new", {}))
app, ss, err = run_app("home", "diamond", buttons={"sb_reports"})
check("فرع: sb_reports شغال", ss.get("page"), "reports")
app, ss, err = run_app("home", "diamond", buttons={"sb_dashboard"})
check("فرع: مفيش زر sb_dashboard أصلاً (الضغط ما بيغيّرش الصفحة)", ss.get("page"), "home")
app, ss, err = run_app("home", "admin", buttons={"sb_logout"})
check("خروج: authenticated=False + rerun", (ss.get("authenticated"), isinstance(err, stub._Rerun)), (False, True))

# ── ④ الـCSS ────────────────────────────────────────────────────────────────
print("\n④ الـCSS")
app, ss, err = run_app("home", "admin")
css = app._SIDEBAR_CSS
i_wide, i_narrow = css.index("@media (min-width:992px)"), css.index("@media (max-width:991.98px)")
wide, narrow = css[i_wide:i_narrow], css[i_narrow:]
check("إخفاء الشريط العلوي بشرط السايدبار مفتوح فعلاً (aria-expanded=true) + شاشة عريضة",
      ".stApp:has([data-testid='stSidebar'][aria-expanded='true']) .st-key-topnav{display:none!important}" in wide, True)
check("مفيش إخفاء للشريط العلوي برّه شرط :has (لا بدون شرط ولا على الموبايل)",
      css.replace(".stApp:has([data-testid='stSidebar'][aria-expanded='true']) .st-key-topnav", "").count(".st-key-topnav"), 0)
check("السايدبار مخفي على <992px", "[data-testid='stSidebar']{display:none!important}" in narrow, True)
check("زر قفل السايدبار مخفي (الهيدر مخفي فمفيش طريق يرجّعه)", "stSidebarCollapseButton" in wide, True)
check("الـCSS صغير", len(css.encode()) < 4000, True)
md = " ".join(str(c[1][0]) for c in stub.CALLS if c[0] == "markdown" and c[1])
check("الـCSS بيتحقن مع الهيدر لما السايدبار شغال", "min-width:992px" in md, True)

# ── ⑤ الفلاج و set_page_config ──────────────────────────────────────────────
print("\n⑤ الفلاج ui_sidebar")


def cfg_state():
    for c in stub.CALLS:
        if c[0] == "set_page_config":
            return c[2].get("initial_sidebar_state")


app, ss, err = run_app("home", "admin")
check("افتراضي: السايدبار شغال + initial_sidebar_state=auto", (app.UI_SIDEBAR, cfg_state()), (True, "auto"))
for val in ("0", "false", "False", "off", "no", "", False):
    app, ss, err = run_app("home", "admin", secrets={"ui_sidebar": val})
    md = " ".join(str(c[1][0]) for c in stub.CALLS if c[0] == "markdown" and c[1])
    check(f"ui_sidebar={val!r} → مقفول: مفيش أزرار sb_ ومفيش CSS + collapsed",
          (app.UI_SIDEBAR, sb_buttons(), "min-width:992px" in md, cfg_state()), (False, [], False, "collapsed"))
    check(f"ui_sidebar={val!r} → الشريط العلوي كامل زي الأول",
          sum(1 for c in stub.CALLS if c[0] == "button" and c[1][0] in ("🏠 الرئيسية", "➕ جديدة", "📈 تقارير", "📊 Dashboard")), 4)
for val in ("1", "true", True, "yes", "on"):
    app, ss, err = run_app("home", "admin", secrets={"ui_sidebar": val})
    check(f"ui_sidebar={val!r} → شغال", app.UI_SIDEBAR, True)

print()
if _FAILS:
    print(f"❌ {len(_FAILS)} اختبار فشل")
    sys.exit(1)
print("✅ كل اختبارات السايدبار نجحت")
