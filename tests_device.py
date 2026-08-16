# -*- coding: utf-8 -*-
"""
tests_device.py — اختبار توكن الجهاز (P2 و P4)

بينفّذ app.py الحقيقي في كل سيناريو + بيختبر device_auth مباشرة.
التشغيل:  python3 tests_device.py
"""
import sys, os, time, tempfile, shutil, importlib

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import _stub_streamlit as stub
import device_auth as dev

ADMIN   = "Hussein.ali77121@gmail.com"
DIAMOND = "Orangelab511@gmail.com"

BASE = {
    "admin_password": "AdminPass!2026",
    "branch_password": "1234567",
    "device_secret": "S3cretSigningKey",
    "allowed_emails": [ADMIN, DIAMOND],
    "github_token": "", "github_repo": "",
}

_FAILS = []


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


class FakeSt:
    """st مبسّط لاختبار device_auth لوحده."""
    def __init__(self, secrets=None, cookies=None, params=None):
        self.secrets = dict(secrets or BASE)
        self.session_state = {}
        self.query_params = dict(params or {})
        class _C:
            pass
        self.context = _C()
        self.context.cookies = dict(cookies or {})
        self.context.headers = {}
        self.context.ip_address = "197.45.12.9"


def run_app(secrets=None, cookies=None, params=None):
    """بينفّذ app.py ويرجّع حالة الجلسة + الـ query params بعد التنفيذ."""
    wd = tempfile.mkdtemp(prefix="dev_")
    cwd = os.getcwd()
    os.chdir(wd)
    stub.reset()
    st = stub.install(secrets or BASE)
    st.context.cookies = dict(cookies or {})
    st.query_params.update(params or {})
    for m in ("app", "core", "import_rules", "device_auth", "phone_utils",
              "lab_picker", "login_theme", "easter_eggs", "labs_price_list"):
        sys.modules.pop(m, None)
    err = None
    try:
        importlib.import_module("app")
    except (stub._Rerun, stub._Stop):
        pass
    except Exception as e:
        err = f"{type(e).__name__}: {e}"
    out = {
        "auth": bool(stub.session_state.get("authenticated")),
        "ut": stub.session_state.get("user_type"),
        "url_token": stub.query_params.get(dev.TOKEN_PARAM),
        "pending_cookie": stub.session_state.get("_pending_cookie"),
        "err": err,
    }
    os.chdir(cwd)
    shutil.rmtree(wd, ignore_errors=True)
    return out


CK = dev.COOKIE_NAME

# ══════════════════════════════════════════════════════════════════════════════
print("═" * 62)
print("  اختبار توكن الجهاز — P2 (الـURL) و P4 (الإلغاء)")
print("═" * 62)

print("\n🔑 صحة التوكن الأساسية")
s = FakeSt()
tok = dev.make_token(s, DIAMOND)
check("التوكن بيتولّد",        bool(tok), True)
check("بيتقرا صح",             dev.read_token(s, tok)["e"], DIAMOND.lower())
check("فيه رقم إصدار",         dev.read_token(s, tok)["v"], 1)
check("توقيع معدّل → مرفوض",   dev.read_token(s, tok[:-4] + "AAAA"), None)
check("نص عشوائي → مرفوض",     dev.read_token(s, "كلام.فاضي"), None)
check("فاضي → مرفوض",          dev.read_token(s, ""), None)
_expired = dev.make_token(s, DIAMOND, days=-1)
check("منتهي → مرفوض",         dev.read_token(s, _expired), None)
_no_secret = FakeSt(secrets={k: v for k, v in BASE.items()
                             if k not in ("device_secret", "admin_password")})
check("من غير سر → مايتولّدش", dev.make_token(_no_secret, DIAMOND), "")

print("\n🔄 P4 — إلغاء الأجهزة بـ token_version")
s1 = FakeSt(secrets={**BASE, "token_version": 1})
t1 = dev.make_token(s1, DIAMOND)
check("الإصدار 1 شغّال",        bool(dev.read_token(s1, t1)), True)
s2 = FakeSt(secrets={**BASE, "token_version": 2})
check("نفس التوكن بعد الترقية → ملغي", dev.read_token(s2, t1), None)
t2 = dev.make_token(s2, DIAMOND)
check("التوكن الجديد شغّال",     bool(dev.read_token(s2, t2)), True)
check("والقديم فضل ملغي",        dev.read_token(s2, t1), None)
check("الرجوع للإصدار 1 يرجّع القديم", bool(dev.read_token(s1, t1)), True)
# توافق رجعي: توكن من غير "v"
import json as _json, base64 as _b64, hmac as _hmac, hashlib as _hash
_raw = _json.dumps({"e": DIAMOND.lower(), "a": 0, "d": "x", "x": int(time.time()) + 9999},
                   separators=(",", ":"), sort_keys=True).encode()
_sig = _hmac.new(BASE["device_secret"].encode(), _raw, _hash.sha256).digest()[:16]
_legacy = dev._b64e(_raw) + "." + dev._b64e(_sig)
check("توكن قديم بلا v → يتعامل كإصدار 1", bool(dev.read_token(s1, _legacy)), True)

print("\n🔗 P2 — التوكن مابقاش يتحط في الـURL")
s = FakeSt()
tok = dev.remember_device(s, DIAMOND)
check("remember_device بيرجّع توكن",   bool(tok), True)
check("والـURL فاضي",                  s.query_params.get(dev.TOKEN_PARAM), None)
s_opt = FakeSt(secrets={**BASE, "allow_url_token": True})
dev.remember_device(s_opt, DIAMOND)
check("الاحتياطي الصريح بيحطه",        bool(s_opt.query_params.get(dev.TOKEN_PARAM)), True)

print("\n🧹 P2 — التوكن الموجود في URL بينتقل للكوكي ويتشال")
s = FakeSt(params={dev.TOKEN_PARAM: dev.make_token(FakeSt(), DIAMOND)})
res = dev.try_auto_login(s, [ADMIN, DIAMOND])
check("الدخول نجح",                    bool(res), True)
check("والمصدر = link",                res["via"], "link")
check("اتشال من الـURL",               s.query_params.get(dev.TOKEN_PARAM), None)
check("واتحط في طابور الكوكي",         bool(s.session_state.get("_pending_cookie")), True)
s2 = FakeSt(secrets={**BASE, "allow_url_token": True},
            params={dev.TOKEN_PARAM: dev.make_token(FakeSt(), DIAMOND)})
dev.try_auto_login(s2, [ADMIN, DIAMOND])
check("مع الاحتياطي بيفضل في الـURL",   bool(s2.query_params.get(dev.TOKEN_PARAM)), True)

print("\n⏱️ مدة توكن الأدمن أقصر")
s = FakeSt()
ta = dev.make_token(s, ADMIN, is_admin=True, days=dev.admin_days(s))
tb = dev.make_token(s, DIAMOND, days=dev.DEFAULT_DAYS)
check("الافتراضي للأدمن 30 يوم",  dev.admin_days(s), 30)
check("والفرع 90",                dev.DEFAULT_DAYS, 90)
check("توكن الأدمن أقصر فعلاً",
      dev.read_token(s, ta)["x"] < dev.read_token(s, tb)["x"], True)
s_cfg = FakeSt(secrets={**BASE, "admin_days": 90})
check("قابل للتغيير من Secrets",  dev.admin_days(s_cfg), 90)

print("\n▶️ تنفيذ app.py — الدخول التلقائي")
r = run_app(cookies={CK: dev.make_token(FakeSt(), DIAMOND)})
check("كوكي فرع صالحة → دخول",   (r["err"], r["auth"], r["ut"]), (None, True, "diamond"))
r = run_app(cookies={CK: dev.make_token(FakeSt(), ADMIN, is_admin=True)})
check("كوكي أدمن صالحة → دخول",  (r["err"], r["auth"], r["ut"]), (None, True, "admin"))
r = run_app(params={dev.TOKEN_PARAM: dev.make_token(FakeSt(), DIAMOND)})
check("توكن URL → دخول",         (r["err"], r["auth"]), (None, True))
check("واتشال من الـURL",         r["url_token"], None)
check("واتحط في طابور الكوكي",    bool(r["pending_cookie"]), True)
r = run_app(cookies={CK: "توكن.مزوّر"})
check("كوكي مزوّرة → شاشة دخول", (r["err"], r["auth"]), (None, False))
_old = dev.make_token(FakeSt(secrets={**BASE, "token_version": 1}), DIAMOND)
r = run_app(secrets={**BASE, "token_version": 2}, cookies={CK: _old})
check("توكن ملغي بالإصدار → مرفوض", (r["err"], r["auth"]), (None, False))
r = run_app(secrets={**BASE, "allowed_emails": [ADMIN]},
            cookies={CK: dev.make_token(FakeSt(), DIAMOND)})
check("إيميل اتشال من القايمة → مرفوض", (r["err"], r["auth"]), (None, False))
r = run_app()
check("من غير كوكي → شاشة دخول", (r["err"], r["auth"]), (None, False))

print("\n🔐 التوكن مش بيتخطّى بوابة الإيميل")
_alien = dev.make_token(FakeSt(secrets={**BASE, "allowed_emails": ["ghost@x.com"]}),
                        "ghost@x.com")
r = run_app(cookies={CK: _alien})
check("توكن لإيميل بره القايمة", (r["err"], r["auth"]), (None, False))

print("\n" + "═" * 62)
if _FAILS:
    print(f"❌ فشل {len(_FAILS)} اختبار: {', '.join(_FAILS[:6])}")
    raise SystemExit(1)
print("✅ كل اختبارات توكن الجهاز نجحت")
