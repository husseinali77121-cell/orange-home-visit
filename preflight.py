#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
preflight.py — فحص ما قبل الرفع

شغّله **قبل** git push. بيتأكد إن كل حاجة مظبوطة عشان مايحصلش موقف
البرنامج يقع بعد النشر وانت مش عارف السبب.

    python3 preflight.py

بيرجّع 0 لو كله تمام، و1 لو فيه حاجة هتقع.
"""
import os, sys, json, ast, importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))
os.chdir(HERE)

OK, WARN, FAIL = "✅", "⚠️ ", "❌"
problems, warnings = [], []


def check(label, ok, detail="", fatal=True):
    mark = OK if ok else (FAIL if fatal else WARN)
    print(f"  {mark} {label}" + (f"\n       {detail}" if detail and not ok else ""))
    if not ok:
        (problems if fatal else warnings).append(label)
    return ok


print("═" * 62)
print("  فحص ما قبل الرفع — Orange Lab HVMS")
print("═" * 62)

# ── ① الملفات الإجبارية ──────────────────────────────────────────────────────
print("\n① الملفات الإجبارية")
REQUIRED = ["app.py", "core.py", "import_rules.py", "sync_guards.py",
            "device_auth.py", "phone_utils.py", "lab_picker.py",
            "labs_price_list.py", "login_theme.py", "easter_eggs.py",
            "requirements.txt"]
missing = [f for f in REQUIRED if not os.path.exists(f)]
check("كل الملفات موجودة", not missing,
      f"ناقص: {missing}\n       ← البرنامج هيقع بـ ModuleNotFoundError")

NEW = ["core.py", "import_rules.py", "sync_guards.py"]
print(f"       ℹ️ ملفات جديدة لازم تترفع مع app.py: {', '.join(NEW)}")

# ── ② الصياغة ────────────────────────────────────────────────────────────────
print("\n② الصياغة")
bad = []
for f in REQUIRED:
    if not f.endswith(".py") or not os.path.exists(f):
        continue
    try:
        ast.parse(open(f, encoding="utf-8").read())
    except SyntaxError as e:
        bad.append(f"{f}:{e.lineno} — {e.msg}")
check("كل الملفات syntax سليم", not bad, "\n       ".join(bad))

# ── ③ الاستيرادات بتشتغل فعلاً ───────────────────────────────────────────────
print("\n③ الاستيرادات (بلا Streamlit)")
for mod in ["core", "import_rules", "sync_guards", "phone_utils", "lab_picker"]:
    try:
        spec = importlib.util.spec_from_file_location(mod, f"{mod}.py")
        m = importlib.util.module_from_spec(spec)
        sys.modules[mod] = m
        spec.loader.exec_module(m)
        check(f"{mod}.py", True)
    except Exception as e:
        check(f"{mod}.py", False, f"{type(e).__name__}: {e}")

# ── ④ الأسرار المطلوبة ───────────────────────────────────────────────────────
print("\n④ الأسرار المطلوبة")
secrets_path = ".streamlit/secrets.toml"
if os.path.exists(secrets_path):
    txt = open(secrets_path, encoding="utf-8").read()
    for key, why in [
        ("admin_password",  "من غيره دخول الأدمن مقفول"),
        ("branch_password", "من غيره **الفروع مش هتقدر تدخل خالص**"),
        ("github_token",    "من غيره مفيش مزامنة"),
        ("github_repo",     "من غيره مفيش مزامنة"),
    ]:
        check(f"{key} موجود", f"{key}" in txt and f'{key} = ""' not in txt, why)
    check("device_secret موجود",
          "device_secret" in txt and 'device_secret = ""' not in txt,
          "من غيره الكود بيوقّع بـ admin_password — تغيير الباسورد بيفصل كل الأجهزة",
          fatal=False)
else:
    print(f"  {WARN} مفيش {secrets_path} محليًا")
    print("       ← عادي لو بتظبّط الأسرار من Streamlit Cloud → Settings → Secrets")
    print("       ⚠️ بس **اتأكد** إن دول موجودين هناك:")
    print("          admin_password · branch_password · device_secret")
    print("          github_token · github_repo")
    warnings.append("الأسرار مش متحققة محليًا")

# ── ⑤ الأسرار مش داخلة git ───────────────────────────────────────────────────
print("\n⑤ حماية الأسرار")
gi = open(".gitignore", encoding="utf-8").read() if os.path.exists(".gitignore") else ""
check(".gitignore بيغطي secrets.toml", "secrets.toml" in gi,
      "← خطر تسريب التوكن والباسورد")
leaked = []
for f in REQUIRED:
    if f.endswith(".py") and os.path.exists(f):
        src = open(f, encoding="utf-8").read()
        if "ghp_" in src or "github_pat_" in src:
            leaked.append(f)
check("مفيش توكن في الكود", not leaked, f"في: {leaked}")

# ── ⑥ سلامة البيانات ────────────────────────────────────────────────────────
print("\n⑥ سلامة ملفات البيانات")
try:
    live = json.load(open("Visits.json", encoding="utf-8"))
    nlive = len(live.get("visits", []))
    check(f"Visits.json ({nlive} زيارة)", live.get("total") == nlive,
          f"total={live.get('total')} لكن الفعلي={nlive}")
    if os.path.isdir("visits"):
        tot, ids = 0, set()
        for f in os.listdir("visits"):
            v = json.load(open(f"visits/{f}", encoding="utf-8"))["visits"]
            tot += len(v)
            ids |= {r["id"] for r in v}
        check(f"الملفات الشهرية ({tot})", tot == nlive,
              f"المجموع الشهري {tot} ≠ الملف الحي {nlive}")
        check("نفس الـIDs", ids == {r["id"] for r in live["visits"]})
    arc = "archive/Visits_upto_2026-05-31.json"
    if os.path.exists(arc):
        a = json.load(open(arc, encoding="utf-8"))["visits"]
        overlap = {r["id"] for r in a} & {r["id"] for r in live["visits"]}
        check(f"صفر تداخل مع الأرشيف ({len(a)})", not overlap, f"{len(overlap)} متداخل")
except Exception as e:
    check("قراءة ملفات البيانات", False, f"{type(e).__name__}: {e}")

# ── ⑦ الاختبارات ─────────────────────────────────────────────────────────────
print("\n⑦ الاختبارات")
import subprocess
for suite in ["tests_pure.py", "tests_guards.py", "tests_import.py",
              "tests_auth.py", "tests_device.py", "tests_pages.py"]:
    if not os.path.exists(suite):
        check(suite, False, "الملف مش موجود", fatal=False)
        continue
    r = subprocess.run([sys.executable, suite], capture_output=True, text=True)
    n = r.stdout.count("✅")
    check(f"{suite} ({n} اختبار)", r.returncode == 0,
          "\n       ".join(l for l in r.stdout.splitlines() if "❌" in l)[:300])

# ── الخلاصة ─────────────────────────────────────────────────────────────────
print("\n" + "═" * 62)
if problems:
    print(f"  {FAIL} {len(problems)} مشكلة هتوقّع البرنامج:")
    for p in problems:
        print(f"     • {p}")
    print("\n  ⛔ **متعملش push قبل ما تتصلّح**")
    sys.exit(1)

if warnings:
    print(f"  {WARN} {len(warnings)} تنبيه (مش مانع):")
    for w in warnings:
        print(f"     • {w}")
    print()

print("  ✅ جاهز للرفع")
print("""
  الخطوات:
    1. اتأكد إن الأسرار متظبّطة في Streamlit Cloud
    2. git add -A && git commit -m "..." && git push
    3. بعد إعادة التشغيل، افتح البرنامج واتأكد من:
       • شاشة الدخول بتطلب باسورد للفرع
       • بانر المزامنة أخضر
       • عدد الزيارات صح (مش صفر)
    4. لو المزامنة اتصرّفت غلط → Secrets: use_cas = false
    5. للرجوع الكامل: git revert HEAD && git push
""")
sys.exit(0)
