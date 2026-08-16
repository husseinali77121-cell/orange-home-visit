# -*- coding: utf-8 -*-
"""
tests_pages.py — تنفيذ app.py فعليًا لكل صفحة

ده الفحص اللي كان ناقص طول المراجعة: كل اللي فات كان تحليل ثابت أو اختبار
دوال معزولة. هنا بننفّذ **الكود الحقيقي** بتاع كل صفحة سطر بسطر، فأي
NameError أو TypeError أو مفتاح ناقص أو توقيع دالة غلط بيظهر.

التشغيل:  python3 tests_pages.py
"""
import sys, os, io, importlib, traceback, sqlite3, json, shutil, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import _stub_streamlit as stub

SECRETS = {
    "admin_password": "TestPass123",
    "allowed_emails": ["Hussein.ali77121@gmail.com", "Orangelab511@gmail.com",
                       "Huossein721@gmail.com", "stranger@example.com"],
    "github_token": "", "github_repo": "", "github_branch": "main",
    "use_monthly_sync": False,
}

PAGES = ["home", "today", "new", "detail", "reports", "dashboard",
         "client_profile", "manage_doctors", "follow_ups", "audit",
         "صفحة_مش_موجودة"]

# ★ القيم دي لازم تطابق _user_type_for() في app.py: admin/diamond/lacite/other
#   أول محاولة استخدمت "branch" — قيمة مخترعة — فكل صفحات الفرع طلعت "فشل"
#   وهي في الحقيقة بوابة صلاحيات شغالة صح.
USERS = [("admin",   "Hussein.ali77121@gmail.com"),
         ("diamond", "Orangelab511@gmail.com"),
         ("lacite",  "Huossein721@gmail.com"),
         ("other",   "stranger@example.com")]

results = []


def seed_db(workdir):
    """بيانات حقيقية في DB — عشان الصفحات تلاقي حاجة ترسمها."""
    src = os.path.join(HERE, "Visits.json")
    with open(src, encoding="utf-8") as f:
        visits = json.load(f)["visits"][:40]
    return visits


def run_page(page, user_type, email, seed_visits, extra_state=None):
    """بيستورد app.py من الأول لكل حالة — أقرب حاجة لـ rerun حقيقي."""
    workdir = tempfile.mkdtemp(prefix=f"hvms_{page}_")
    cwd = os.getcwd()
    os.chdir(workdir)
    stub.reset()
    st = stub.install(SECRETS)

    # حالة ما بعد الدخول
    # ★ أسماء المفاتيح دي لازم تطابق app.py بالظبط. أول محاولة استخدمت
    #   logged_in و selected_visit_id — أسماء مخترعة — فالتنفيذ كان بيقف عند
    #   شاشة الدخول وكل الصفحات بتطلع "خضرا" وهي ماتفحصتش أصلاً.
    st.session_state.update({
        "authenticated": True, "user_type": user_type, "user_email": email,
        "page": page, "need_password": False, "_skip_auto_login": True,
        "current_page": 1, "page_size": 20, "total_visits": 0,
        "prefill": {}, "selected_id": None, "selected_client_phone": "",
        "search_q": "",
    })
    if extra_state:
        st.session_state.update(extra_state)

    for m in ("app", "core", "import_rules", "phone_utils", "lab_picker",
              "login_theme", "easter_eggs", "device_auth", "labs_price_list"):
        sys.modules.pop(m, None)

    status, detail = "✅", ""
    try:
        app = importlib.import_module("app")
        # ازرع بيانات لو الصفحة محتاجة
        if seed_visits and hasattr(app, "insert_visit"):
            conn = app.get_connection()
            for v in seed_visits:
                try:
                    app._load_insert_visit(conn, v, upsert=True)
                except Exception:
                    pass
            conn.commit()
    except stub._Rerun:
        status, detail = "↻", "st.rerun()"
    except stub._Stop:
        # ★ st.stop() من بوابة الدخول = الصفحة ماتنفّذتش. ده فشل مش نجاح.
        ADMIN_ONLY = {"dashboard", "manage_doctors", "audit"}
        if user_type == "other":
            status, detail = "🔒", "اتمنع (متوقع)"
        elif page in ADMIN_ONLY and user_type != "admin":
            status, detail = "🔒", "أدمن فقط (متوقع)"
        elif len(stub.CALLS) > 40:
            status, detail = "⏹", "st.stop() — التنفيذ وصل للآخر"
        else:
            status, detail = "❌", f"وقف بدري ({len(stub.CALLS)} نداء) — الصفحة ماتنفّذتش"
    except Exception as e:
        status = "❌"
        tb = traceback.extract_tb(sys.exc_info()[2])
        frames = [f for f in tb if "app.py" in f.filename or "core.py" in f.filename
                  or "import_rules" in f.filename or "lab_picker" in f.filename]
        loc = frames[-1] if frames else tb[-1]
        detail = (f"{type(e).__name__}: {str(e)[:70]}\n"
                  f"        {os.path.basename(loc.filename)}:{loc.lineno} — {(loc.line or '')[:80]}")
    finally:
        os.chdir(cwd)
        shutil.rmtree(workdir, ignore_errors=True)
    return status, detail, len(stub.CALLS)


def main():
    seed = seed_db(None)
    print("═" * 66)
    print("  تنفيذ app.py فعليًا — كل صفحة × كل نوع مستخدم")
    print("═" * 66)
    fails = 0
    for user_type, email in USERS:
        print(f"\n▸ المستخدم: {user_type} ({email.split('@')[0]})")
        for page in PAGES:
            extra = {}
            if page == "detail":
                extra = {"selected_visit_id": seed[0]["id"]}
            if page == "client_profile":
                extra = {"selected_client_phone": seed[0]["phone"]}
            status, detail, ncalls = run_page(page, user_type, email, seed, extra)
            label = f"{page:<22}"
            print(f"   {status} {label} ({ncalls} نداء واجهة)"
                  + (f"\n        {detail}" if detail and status == "❌" else ""))
            if status == "❌":
                fails += 1
                results.append((user_type, page, detail))
    # ── فحص صريح لحراس الصلاحيات ─────────────────────────────────────────
    # ★ عدّ نداءات الواجهة لوحده مابيكفيش: صفحة من غير حارس ممكن ترسم قليل
    #   وتعدّي. الفحص ده بيقرا الكود ويتأكد إن **كل** صفحة فيها حارس صريح،
    #   ويشغّل مستخدم بلا دور على كل الصفحات ويتأكد إنه مايشوفش بيانات.
    import ast as _ast
    print("\n▸ حراس الصلاحيات — فحص صريح (AST)")
    _src = open(os.path.join(HERE, "app.py"), encoding="utf-8").read()
    _tree = _ast.parse(_src)

    # ★ الفحص كان بـ regex على نص الكتلة — وده بيلاقي `user_type` في
    #   **التعليقات** كمان. يعني حارس متشال والتعليق فاضل = أخضر كاذب.
    #   (اتكشف لما شيلت الحارس فعليًا والاختبار عدّى.)
    #   AST بيشوف الكود المنفَّذ بس — التعليقات مش موجودة فيه أصلاً.
    def _page_blocks(tree):
        """بيرجّع {اسم الصفحة: [عقد الجسم]} من سلسلة if/elif بتاعة الـrouting."""
        out = {}
        for node in _ast.walk(tree):
            if not isinstance(node, _ast.If):
                continue
            t = node.test
            if not (isinstance(t, _ast.Compare) and isinstance(t.left, _ast.Attribute)
                    and t.left.attr == "page"
                    and isinstance(t.comparators[0], _ast.Constant)):
                continue
            out[t.comparators[0].value] = node.body
        return out

    def _has_guard(body):
        """
        الحارس لازم يكون `if` على **المستوى الأول** من جسم الصفحة، شرطه
        بيفحص user_type، وجسمه فيه st.stop().

        ★ ما ينفعش نستخدم ast.walk هنا: بيدخل جوّه أي عمق، فحارس ملفوف
          في `if False:` كان بيتحسب موجود. والفحص القديم بـ regex كان
          بيلاقي user_type في **التعليقات** كمان.
        """
        for st_ in body:
            if not isinstance(st_, _ast.If):
                continue
            try:
                cond = _ast.unparse(st_.test)
            except Exception:
                continue
            if "user_type" not in cond:
                continue
            # الشرط لازم يكون فحص حقيقي مش ثابت (if False)
            if isinstance(st_.test, _ast.Constant):
                continue
            body_src = " ".join(_ast.unparse(x) for x in st_.body)
            if "st.stop()" in body_src or "st.error" in body_src:
                return True
        return False

    _blocks = _page_blocks(_tree)
    _pages = list(_blocks.items())
    _nog = [n for n, b in _pages if not _has_guard(b)]
    if _nog:
        print(f"   ❌ صفحات من غير حارس: {_nog}")
        fails += len(_nog)
        results.append(("—", ", ".join(_nog), "مفيش حارس صلاحية في الكود"))
    else:
        print(f"   ✅ كل الصفحات ({len(_pages)}) فيها حارس صريح")

    # مستخدم بلا دور: كل الصفحات لازم تمنعه
    _leaked = []
    for _p in PAGES:
        _st, _d, _n = run_page(_p, "other", "stranger@example.com", seed, None)
        if _n > 25 and _p not in ("صفحة_مش_موجودة",):
            _leaked.append((_p, _n))
    if _leaked:
        print(f"   ❌ صفحات اتفتحت لمستخدم بلا دور: {_leaked}")
        fails += len(_leaked)
        results.append(("other", str(_leaked), "الصفحة رسمت محتوى لمستخدم مالوش صلاحية"))
    else:
        print("   ✅ مستخدم بلا دور اتمنع من كل الصفحات")

    print("\n" + "═" * 66)
    if fails:
        print(f"❌ {fails} صفحة فشلت")
        for u, p, d in results:
            print(f"\n  [{u}] {p}\n    {d}")
        return 1
    print("✅ كل الصفحات اتنفّذت من غير استثناء")
    return 0


if __name__ == "__main__":
    sys.exit(main())
