# -*- coding: utf-8 -*-
"""
tests_permissions.py — اختبار الصلاحيات على مستوى البيانات

القاعدة: admin → الكل · diamond → Diamond · lacite → La Cite · غيرهم → ممنوع

الطبقة دي defense in depth: الواجهة بتفلتر بالفعل، بس لو نسي حد حارس في
صفحة جديدة، البيانات نفسها بترفض.

التشغيل:  python3 tests_permissions.py
"""
import sys, os, ast, sqlite3, re, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from permissions import (allowed_branch, can_access, enforce, filter_visible,
                         scope_filters, PermissionDenied)

_FAILS = []


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


D = {"id": "d1", "branch": "Diamond", "name": "أحمد"}
L = {"id": "l1", "branch": "La Cite", "name": "سارة"}
N = {"id": "n1", "branch": "",        "name": "بلا فرع"}

print("═" * 60)
print("  الصلاحيات على مستوى البيانات")
print("═" * 60)

print("\n① نطاق كل دور")
check("admin → كل الفروع",   allowed_branch("admin"), None)
check("diamond → Diamond",   allowed_branch("diamond"), "Diamond")
check("lacite → La Cite",    allowed_branch("lacite"), "La Cite")
check("other → ممنوع",       allowed_branch("other"), False)
check("None → ممنوع",        allowed_branch(None), False)
check("فاضي → ممنوع",        allowed_branch(""), False)
check("قيمة مخترعة → ممنوع", allowed_branch("branch"), False)
check("حالة أحرف مختلفة",    allowed_branch("ADMIN"), None)

print("\n② can_access — الوصول للسجل")
check("admin يشوف Diamond",     can_access(D, "admin"), True)
check("admin يشوف La Cite",     can_access(L, "admin"), True)
check("admin يشوف بلا فرع",     can_access(N, "admin"), True)
check("diamond يشوف Diamond",   can_access(D, "diamond"), True)
check("diamond مايشوفش La Cite", can_access(L, "diamond"), False)
check("lacite يشوف La Cite",    can_access(L, "lacite"), True)
check("lacite مايشوفش Diamond", can_access(D, "lacite"), False)
check("other مايشوفش حاجة",     can_access(D, "other"), False)
check("سجل بلا فرع → أدمن بس",  can_access(N, "diamond"), False)
check("مدخل مش dict",           can_access("نص", "diamond"), False)
check("None",                   can_access(None, "diamond"), False)

print("\n③ filter_visible — تصفية القوائم")
ALL = [D, L, N]
check("admin يشوف الكل",      len(filter_visible(ALL, "admin")), 3)
check("diamond يشوف واحد",    [r["id"] for r in filter_visible(ALL, "diamond")], ["d1"])
check("lacite يشوف واحد",     [r["id"] for r in filter_visible(ALL, "lacite")], ["l1"])
check("other مايشوفش حاجة",   filter_visible(ALL, "other"), [])
check("قائمة فاضية",          filter_visible([], "admin"), [])
check("None",                 filter_visible(None, "admin"), [])

print("\n④ scope_filters — فرض الفرع في الاستعلام")
check("admin بلا قيد",        scope_filters({}, "admin"), {})
check("admin بيحتفظ بفلتره",  scope_filters({"branch": "Diamond"}, "admin"), {"branch": "Diamond"})
check("diamond يتفرض عليه",   scope_filters({}, "diamond"), {"branch": "Diamond"})
check("lacite يتفرض عليه",    scope_filters({}, "lacite"), {"branch": "La Cite"})
check("🔴 الفرع مايقدرش يتخطّى",
      scope_filters({"branch": "La Cite"}, "diamond"), {"branch": "Diamond"})
check("other → فرع مستحيل",   scope_filters({}, "other")["branch"], "__DENY__")
check("باقي الفلاتر محفوظة",
      scope_filters({"status": "تمت"}, "diamond"),
      {"status": "تمت", "branch": "Diamond"})
check("المدخل الأصلي ماتغيّرش",
      (lambda f: (scope_filters(f, "diamond"), f))({"x": 1})[1], {"x": 1})

print("\n⑤ enforce — الرمي عند المنع")
check("المسموح بيعدّي",  enforce(D, "diamond")["id"], "d1")
check("None بيعدّي",     enforce(None, "diamond"), None)
try:
    enforce(L, "diamond")
    check("الممنوع بيرمي", False, True)
except PermissionDenied:
    check("الممنوع بيرمي", True, True)

print("\n⑥ التوصيل في app.py")
_APP = open(os.path.join(HERE, "app.py"), encoding="utf-8").read()
check("permissions مستوردة",        "from permissions import" in _APP, True)
check("fetch_visits فيها user_type",
      "def fetch_visits(filters=None, page=None, page_size=None, user_type=None)" in _APP, True)
check("fetch_visits بتفرض النطاق",
      "filters = scope_filters(filters, user_type)" in _APP, True)
check("fetch_visit_by_id بتفحص",
      "not can_access(rec, user_type)" in _APP, True)
check("صفحة التفاصيل بتمرّر user_type",
      "fetch_visit_by_id(vid, user_type=st.session_state.user_type)" in _APP, True)
check("تاريخ العميل بيتصفّى",
      "out = filter_visible(out, user_type)" in _APP, True)
check("التصفية قبل الـlimit",
      _APP.index("out = filter_visible(out, user_type)")
      < _APP.index("if limit and len(out) > limit"), True)
_ui_calls = _APP.count("user_type=st.session_state.user_type")
check(f"نقاط الواجهة المقصورة ({_ui_calls})", _ui_calls >= 9, True)

print("\n⑦ سيناريو حقيقي — الفرع يحاول يفتح زيارة فرع تاني")
schema = re.search(r'CREATE TABLE IF NOT EXISTS visits \((.*?)\)\s*"""', _APP, re.S).group(1)
con = sqlite3.connect(":memory:")
con.row_factory = sqlite3.Row
con.execute(f"CREATE TABLE visits ({schema})")
# نقرا أسماء الأعمدة من الجدول نفسه بدل ما نحلل نص الـDDL
_cols = [r[1] for r in con.execute("PRAGMA table_info(visits)").fetchall()]
_numeric = {"age", "labs_price_before", "labs_price_after", "transport_fee",
            "total_price", "paid_amount", "archived", "rating"}
for vid, br in (("v_d", "Diamond"), ("v_l", "La Cite")):
    vals = {c: (0 if c in _numeric else "") for c in _cols}
    vals.update(id=vid, name="مريض", phone="01000000000",
                visit_date="2026-08-15", branch=br)
    vals["deleted_at"] = None
    con.execute(f"INSERT INTO visits ({','.join(_cols)}) VALUES ({','.join('?'*len(_cols))})",
                tuple(vals[c] for c in _cols))
con.commit()


def fetch_by_id(vid, user_type=None):
    row = con.execute("SELECT * FROM visits WHERE id=? AND deleted_at IS NULL", (vid,)).fetchone()
    rec = dict(row) if row else None
    if rec is not None and user_type is not None and not can_access(rec, user_type):
        return None
    return rec


check("diamond يفتح زيارته",        fetch_by_id("v_d", "diamond")["id"], "v_d")
check("🔴 diamond مايفتحش زيارة La Cite", fetch_by_id("v_l", "diamond"), None)
check("lacite مايفتحش زيارة Diamond",     fetch_by_id("v_d", "lacite"), None)
check("admin يفتح الاتنين",
      (fetch_by_id("v_d", "admin")["id"], fetch_by_id("v_l", "admin")["id"]), ("v_d", "v_l"))
check("other مايفتحش حاجة",
      (fetch_by_id("v_d", "other"), fetch_by_id("v_l", "other")), (None, None))
check("بلا user_type = السلوك القديم", fetch_by_id("v_l")["id"], "v_l")

print("\n⑧ device_secret إجباري (#6)")
import device_auth as dev


class _S:
    def __init__(self, sec):
        self.secrets = sec


check("مع device_secret يشتغل",
      bool(dev.make_token(_S({"device_secret": "K"}), "a@b.com")), True)
check("🔴 admin_password مابقاش fallback",
      bool(dev.make_token(_S({"admin_password": "P"}), "a@b.com")), False)
check("من غير الاتنين → مقفول",
      bool(dev.make_token(_S({}), "a@b.com")), False)
check("secret_configured بيميّز",
      (dev.secret_configured(_S({"device_secret": "K"})),
       dev.secret_configured(_S({"admin_password": "P"}))), (True, False))

print("\n⑨ باسورد لكل فرع (#5)")
check("ترتيب Diamond",  "'diamond_password', 'branch_password'" in _APP.replace('"', "'"), True)
check("ترتيب La Cite",  "'lacite_password', 'branch_password'" in _APP.replace('"', "'"), True)
check("الأدمن منفصل",   '_keys = ["admin_password"]' in _APP, True)
check("الرجوع للمشترك موجود", '"branch_password"' in _APP, True)

print("\n" + "═" * 60)
if _FAILS:
    print(f"❌ فشل {len(_FAILS)} اختبار: {', '.join(_FAILS[:5])}")
    raise SystemExit(1)
print("✅ كل اختبارات الصلاحيات نجحت")
