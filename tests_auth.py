# -*- coding: utf-8 -*-
"""
tests_auth.py — اختبار مسار الدخول بالتنفيذ الفعلي

بينفّذ app.py الحقيقي في كل سيناريو دخول. مش تحليل ثابت — تشغيل.
التشغيل:  python3 tests_auth.py
"""
import sys, os, importlib, tempfile, shutil, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _stub_streamlit as stub

ADMIN   = "Hussein.ali77121@gmail.com"
DIAMOND = "Orangelab511@gmail.com"
LACITE  = "Huossein721@gmail.com"

SECRETS = {
    "admin_password":  "AdminPass!2026",
    "branch_password": "1234567",
    "allowed_emails":  [ADMIN, DIAMOND, LACITE],
    "github_token": "", "github_repo": "",
}

_FAILS = []


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


def attempt(email, password, secrets=None, extra_state=None, remember=True):
    """
    بيشغّل app.py مرتين: مرة لضغط «دخول»، ومرة لضغط «تأكيد كلمة المرور».
    بيرجّع dict فيه حالة الجلسة بعد المحاولة.
    """
    workdir = tempfile.mkdtemp(prefix="auth_")
    cwd = os.getcwd()
    os.chdir(workdir)
    stub.reset()
    st = stub.install(secrets or SECRETS)
    st.session_state["_skip_auto_login"] = True
    if extra_state:
        st.session_state.update(extra_state)

    for m in ("app", "core", "import_rules", "phone_utils", "lab_picker",
              "login_theme", "easter_eggs", "device_auth", "labs_price_list"):
        sys.modules.pop(m, None)

    # ── الرن الأول: املا الإيميل واضغط «دخول» ──
    _orig_ti, _orig_cb = stub.text_input, stub.checkbox
    stub.text_input = lambda label="", value="", *a, **k: (
        email if "بريدك" in str(label) else ("" if "مرور" in str(label) else value))
    stub.checkbox = lambda label="", value=False, *a, **k: remember
    sys.modules["streamlit"].text_input = stub.text_input
    sys.modules["streamlit"].checkbox = stub.checkbox
    stub.BUTTON_TRUE.clear()
    _orig_button = stub.button
    def btn(label="", *a, **k):
        stub.CALLS.append(("button", (label,), k))
        return label == "دخول"
    stub.button = btn; sys.modules["streamlit"].button = btn

    state = {}
    try:
        importlib.import_module("app")
    except (stub._Rerun, stub._Stop):
        pass
    except Exception as e:
        state["error"] = f"{type(e).__name__}: {e}"
        state["tb"] = traceback.format_exc()[-400:]

    # ── الرن الثاني: املا الباسورد واضغط «تأكيد» ──
    if not state.get("error"):
        stub.text_input = lambda label="", value="", *a, **k: (
            password if "مرور" in str(label) else (email if "بريدك" in str(label) else value))
        sys.modules["streamlit"].text_input = stub.text_input
        def btn2(label="", *a, **k):
            stub.CALLS.append(("button", (label,), k))
            return label == "تأكيد كلمة المرور"
        stub.button = btn2; sys.modules["streamlit"].button = btn2
        for m in ("app",):
            sys.modules.pop(m, None)
        try:
            importlib.import_module("app")
        except (stub._Rerun, stub._Stop):
            pass
        except Exception as e:
            state["error"] = f"{type(e).__name__}: {e}"
            state["tb"] = traceback.format_exc()[-400:]

    state.update({
        "authenticated": bool(stub.session_state.get("authenticated")),
        "user_type": stub.session_state.get("user_type"),
        "user_email": stub.session_state.get("user_email"),
        "need_password": bool(stub.session_state.get("need_password")),
        "pw_fails": stub.session_state.get("_pw_fails", 0),
        "locked": stub.session_state.get("_pw_locked_until") is not None,
        "errors": [a[0] for n, a, k in stub.CALLS if n == "error"],
    })
    stub.text_input, stub.checkbox, stub.button = _orig_ti, _orig_cb, _orig_button
    os.chdir(cwd)
    shutil.rmtree(workdir, ignore_errors=True)
    return state


# ══════════════════════════════════════════════════════════════════════════════
print("═" * 62)
print("  اختبار المصادقة — تنفيذ app.py فعليًا")
print("═" * 62)

print("\n🔑 الأدمن")
r = attempt(ADMIN, "AdminPass!2026")
check("باسورد صح → دخول",        (r.get("error"), r["authenticated"], r["user_type"]),
      (None, True, "admin"))
r = attempt(ADMIN, "غلط")
check("باسورد غلط → مرفوض",      r["authenticated"], False)
r = attempt(ADMIN, "1234567")
check("باسورد الفرع مايفتحش الأدمن", r["authenticated"], False)
r = attempt(ADMIN, "")
check("باسورد فاضي → مرفوض",     r["authenticated"], False)

print("\n🏥 الفروع — الباسورد المشترك")
for label, em, ut in [("Diamond", DIAMOND, "diamond"), ("La Cité", LACITE, "lacite")]:
    r = attempt(em, "1234567")
    check(f"{label}: باسورد صح → دخول", (r.get("error"), r["authenticated"], r["user_type"]),
          (None, True, ut))
    r = attempt(em, "غلط")
    check(f"{label}: باسورد غلط → مرفوض", r["authenticated"], False)
r = attempt(DIAMOND, "AdminPass!2026")
check("باسورد الأدمن مايفتحش الفرع", r["authenticated"], False)

print("\n🚫 الانحدار العكسي — البق القديم مابقاش موجود")
r = attempt(DIAMOND, "")
check("الفرع مايدخلش بإيميل لوحده", r["authenticated"], False)
check("وبيتطلب منه باسورد",         r["need_password"], True)
r = attempt("stranger@example.com", "1234567")
check("إيميل بره القايمة مرفوض",    r["authenticated"], False)

print("\n⛔ السر الناقص = دخول مقفول (مش مفتوح)")
r = attempt(DIAMOND, "1234567", secrets={**SECRETS, "branch_password": ""})
check("branch_password فاضي → مقفول", r["authenticated"], False)
check("والرسالة بتوضّح السبب",
      any("branch_password" in e for e in r["errors"]), True)
r = attempt(ADMIN, "AdminPass!2026", secrets={**SECRETS, "admin_password": ""})
check("admin_password فاضي → مقفول", r["authenticated"], False)

print("\n🔒 تحديد المحاولات")
r = attempt(DIAMOND, "غلط", extra_state={"_pw_fails": 4})
check("المحاولة الخامسة تقفل",     r["locked"], True)
check("والعدّاد بيتصفّر",           r["pw_fails"], 0)
r = attempt(DIAMOND, "غلط", extra_state={"_pw_fails": 1})
check("المحاولة التانية مابتقفلش",  r["locked"], False)
check("والعدّاد بيزيد",             r["pw_fails"], 2)
r = attempt(DIAMOND, "1234567", extra_state={"_pw_fails": 3})
check("النجاح بيصفّر العدّاد",       (r["authenticated"], r["pw_fails"]), (True, 0))

print("\n🌍 باسوردات غير إنجليزية")
for pw in ["كلمة السر ١٢٣", "🟠orange", "P@ss wörd"]:
    r = attempt(DIAMOND, pw, secrets={**SECRETS, "branch_password": pw})
    check(f"«{pw[:14]}» يشتغل", (r.get("error"), r["authenticated"]), (None, True))

print("\n" + "═" * 62)
if _FAILS:
    print(f"❌ فشل {len(_FAILS)} اختبار: {', '.join(_FAILS[:6])}")
    raise SystemExit(1)
print("✅ كل اختبارات المصادقة نجحت")
