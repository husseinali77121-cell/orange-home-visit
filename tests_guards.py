# -*- coding: utf-8 -*-
"""
tests_guards.py — اختبار حُرّاس المزامنة

الحُرّاس دول اللي بيمنعوا ضياع 1,030 سجل. قبل الاستخراج كانوا مالهمش
ولا اختبار مباشر — دلوقتي 40 حالة.

التشغيل:  python3 tests_guards.py
"""
import sys, os, hashlib, json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sync_guards import check_save_allowed, months_to_write, verify_before_prune
from core import _hash_records

_FAILS = []


def check(name, got, want):
    if got == want:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}\n       المتوقع: {want!r}\n       الفعلي : {got!r}")
        _FAILS.append(name)


# ══════════════════════════════════════════════════════════════════════════════
print("═" * 60)
print("  حُرّاس المزامنة — منع ضياع البيانات")
print("═" * 60)

print("\n① الحارس: قاعدة محلية فاضية")
d = check_save_allowed(0, 156)
check("محلي 0 / بعيد 156 → ممنوع",  (bool(d), d.guard), (False, "empty_db"))
check("والسبب واضح",                "فاضية" in d.reason, True)
d = check_save_allowed(0, 0)
check("محلي 0 / بعيد 0 → ممنوع",    bool(d), False)
d = check_save_allowed(0, None)
check("محلي 0 حتى بلا تحقق → ممنوع", d.guard, "empty_db")
d = check_save_allowed(0, 156, allow_shrink_once=True)
check("الإذن مايكسرش حارس الفراغ",  bool(d), False)

print("\n② الحارس: الانكماش")
check("155 < 156 → ممنوع",          bool(check_save_allowed(155, 156)), False)
check("والحارس = shrink",           check_save_allowed(155, 156).guard, "shrink")
check("1 < 156 → ممنوع",            bool(check_save_allowed(1, 156)), False)
check("156 = 156 → مسموح",          bool(check_save_allowed(156, 156)), True)
check("157 > 156 → مسموح",          bool(check_save_allowed(157, 156)), True)
check("الرقم في الرسالة",
      "155" in check_save_allowed(155, 156).reason and "156" in check_save_allowed(155, 156).reason, True)

print("\n③ استثناء allow_shrink_once (من الأرشفة)")
check("120 < 156 بالإذن → مسموح",   bool(check_save_allowed(120, 156, allow_shrink_once=True)), True)
check("من غير الإذن → ممنوع",       bool(check_save_allowed(120, 156)), False)
check("الإذن مايأثرش على السليم",   bool(check_save_allowed(200, 156, allow_shrink_once=True)), True)

print("\n④ الحارس: تعذّر التحقق")
d = check_save_allowed(156, None)
check("بعيد=None → ممنوع",          (bool(d), d.guard), (False, "unverified"))
check("حتى لو المحلي كبير",         bool(check_save_allowed(9999, None)), False)
check("الإذن مايكسرش حارس التحقق",  bool(check_save_allowed(156, None, allow_shrink_once=True)), False)

print("\n⑤ بيانات الدخول")
d = check_save_allowed(156, 156, has_credentials=False)
check("بلا توكن → ممنوع",           (bool(d), d.guard), (False, "credentials"))
check("وده قبل أي فحص تاني",        "Secrets" in d.reason, True)

print("\n⑥ ترتيب الأولوية بين الحُرّاس")
check("الفراغ قبل الانكماش",        check_save_allowed(0, 156).guard, "empty_db")
check("الفراغ قبل التحقق",          check_save_allowed(0, None).guard, "empty_db")
check("التحقق قبل الانكماش",        check_save_allowed(10, None).guard, "unverified")
check("بيانات الدخول أول حاجة",
      check_save_allowed(0, None, has_credentials=False).guard, "credentials")

print("\n⑦ months_to_write — الشهر اللي ماتغيرش مايترفعش")
r1 = [{"id": "a", "visit_date": "2026-06-01"}]
r2 = [{"id": "b", "visit_date": "2026-07-01"}]
buckets = {"2026-06": r1, "2026-07": r2}
prev_hash = {"2026-06": _hash_records(r1), "2026-07": _hash_records(r2)}
prev_tot = {"2026-06": 1, "2026-07": 1}
ch, em = months_to_write(buckets, prev_hash, prev_tot, _hash_records)
check("مفيش تغيير → مفيش رفع",      (ch, em), ([], []))

buckets2 = {"2026-06": r1 + [{"id": "c", "visit_date": "2026-06-02"}], "2026-07": r2}
ch, em = months_to_write(buckets2, prev_hash, prev_tot, _hash_records)
check("شهر اتغيّر → يترفع لوحده",   (ch, em), (["2026-06"], []))

ch, em = months_to_write({"2026-07": r2}, prev_hash, prev_tot, _hash_records)
check("شهر اتفضّى → يترفع فاضي",     (ch, em), (["2026-06"], ["2026-06"]))

ch, em = months_to_write({"2026-08": [{"id": "z"}]}, {}, {}, _hash_records)
check("شهر جديد → يترفع",           ch, ["2026-08"])
ch, em = months_to_write({}, {}, {}, _hash_records)
check("مفيش حاجة → مفيش رفع",       (ch, em), ([], []))

# الترتيب ثابت
b3 = {"2026-08": [{"id": "x"}], "2026-06": [{"id": "y"}], "2026-07": [{"id": "z"}]}
check("الترتيب زمني",               months_to_write(b3, {}, {}, _hash_records)[0],
      ["2026-06", "2026-07", "2026-08"])

print("\n⑧ verify_before_prune — التحقق قبل التقليم")
d = verify_before_prune(["a", "b", "c"], ["a", "b", "c"])
check("كله موجود → مسموح",          bool(d), True)
d = verify_before_prune(["a", "b", "c"], ["a", "b"])
check("سجل ناقص → ممنوع",           (bool(d), d.guard), (False, "prune_verify"))
check("والعدد في الرسالة",          "1" in d.reason, True)
check("ملف أرشيف فاضي → ممنوع",     bool(verify_before_prune(["a"], [])), False)
check("مفيش حاجة للأرشفة → مسموح",  bool(verify_before_prune([], [])), True)
check("الأرشيف فيه زيادة → مسموح",  bool(verify_before_prune(["a"], ["a", "b"])), True)

print("\n⑨ السيناريو الكارثي — DB اتصفّرت")
# ده اللي الحُرّاس اتعملوا عشانه: container اتعمله restart والـ DB فاضية
d = check_save_allowed(0, 1030)
check("DB فاضية / GitHub 1030 → ممنوع", bool(d), False)
check("مفيش إذن بيكسره",
      bool(check_save_allowed(0, 1030, allow_shrink_once=True)), False)
# وبعد استرجاع جزئي
check("استرجاع جزئي (500) → برضه ممنوع", bool(check_save_allowed(500, 1030)), False)
check("استرجاع كامل (1030) → مسموح",     bool(check_save_allowed(1030, 1030)), True)

print("\n⑩ SaveDecision كـ boolean")
check("القرار المسموح truthy",      bool(check_save_allowed(10, 5)), True)
check("القرار المرفوض falsy",       bool(check_save_allowed(0, 5)), False)
check("if not d بتشتغل",            (not check_save_allowed(0, 5)), True)


# ══════════════════════════════════════════════════════════════════════════════
# ⑪ الكتابة المتزامنة بين الفروع (Compare-and-Swap)
# ══════════════════════════════════════════════════════════════════════════════
# حارس العدد لوحده **مش** كافي. السيناريو اللي بيهرب منه:
#     الفرعين عندهم 1000، وGitHub عليه 1000
#     La Cité يضيف X → 1001 → رفع ✅
#     Diamond لسه شايف remote=1000، يضيف Y → 1001 → رفع ✅
#     ⇒ العدد سليم (1001) بس زيارة X ضاعت
# الحل: نبعت الـSHA اللي قرينا عنده؛ GitHub بيرفض بـ409 لو حد كتب بعدنا.

class FakeGitHub:
    """محاكاة سلوك GitHub Contents API في موضوع الـSHA."""
    def __init__(self):
        self.files = {}          # path → (sha, content)
        self._n = 0

    def read(self, path):
        return self.files.get(path, (None, None))

    def put(self, path, content, expected_sha):
        cur_sha = self.files.get(path, (None, None))[0]
        if cur_sha is not None and expected_sha != cur_sha:
            return 409, None      # Conflict — حد تاني كتب
        self._n += 1
        new_sha = f"sha{self._n}"
        self.files[path] = (new_sha, content)
        return 200, new_sha


print("\n⑪ الكتابة المتزامنة — Compare-and-Swap")
gh = FakeGitHub()
gh.put("Visits.json", ["v1"] * 1000, None)          # الحالة الابتدائية
base_sha = gh.files["Visits.json"][0]

# الفرعين قروا في نفس الوقت
lacite_sha, lacite_data = gh.read("Visits.json")
diamond_sha, diamond_data = gh.read("Visits.json")
check("الفرعين قروا نفس النسخة", lacite_sha == diamond_sha, True)

# La Cité يضيف زيارة ويرفع
code, new_sha = gh.put("Visits.json", list(lacite_data) + ["X"], lacite_sha)
check("La Cité رفع بنجاح", code, 200)
check("GitHub بقى 1001", len(gh.files["Visits.json"][1]), 1001)
check("وفيه X", "X" in gh.files["Visits.json"][1], True)

# Diamond يضيف زيارة تانية ويرفع بالـSHA القديم
code2, _ = gh.put("Visits.json", list(diamond_data) + ["Y"], diamond_sha)
check("Diamond اترفض (409)", code2, 409)
check("زيارة X لسه موجودة", "X" in gh.files["Visits.json"][1], True)
check("والعدد لسه 1001", len(gh.files["Visits.json"][1]), 1001)

# بعد إعادة القراءة والدمج
fresh_sha, fresh = gh.read("Visits.json")
code3, _ = gh.put("Visits.json", list(fresh) + ["Y"], fresh_sha)
check("بعد إعادة القراءة الرفع نجح", code3, 200)
check("الاتنين موجودين",
      ("X" in gh.files["Visits.json"][1], "Y" in gh.files["Visits.json"][1]), (True, True))
check("والعدد 1002", len(gh.files["Visits.json"][1]), 1002)

# من غير CAS (السلوك القديم) البيانات بتضيع
gh2 = FakeGitHub()
gh2.put("Visits.json", ["v1"] * 1000, None)
a_sha, a = gh2.read("Visits.json")
b_sha, b = gh2.read("Visits.json")
gh2.put("Visits.json", list(a) + ["X"], a_sha)
# السلوك القديم: يجيب SHA جديد قبل الـPUT مباشرة → دايمًا بينجح
gh2.put("Visits.json", list(b) + ["Y"], gh2.files["Visits.json"][0])
check("بلا CAS: X بتضيع",   "X" in gh2.files["Visits.json"][1], False)
check("بلا CAS: العدد سليم فمفيش إنذار", len(gh2.files["Visits.json"][1]), 1001)

# ملف جديد (مفيش SHA) مسموح
code4, _ = gh.put("visits/2026-09.json", ["new"], None)
check("ملف جديد بلا SHA → مسموح", code4, 200)

# ── التحقق من الكود الحقيقي مش المحاكاة ──────────────────────────────────────
# ★ الاختبارات فوق بتثبت **المبدأ** بمحاكاة GitHub. لكن الطفرة M32 عدّت منها،
#   لأنها مابتلمسش app.py. الفحص ده بيقرا الكود الفعلي ويتأكد إن CAS متوصّل.
import ast as _ast, os as _os

_APP = open(_os.path.join(_os.path.dirname(_os.path.abspath(__file__)), "app.py"),
            encoding="utf-8").read()
_T = _ast.parse(_APP)
_put = next((n for n in _ast.walk(_T)
             if isinstance(n, _ast.FunctionDef) and n.name == "_gh_put_json"), None)

print("\n⑫ CAS متوصّل في الكود الفعلي")
check("_gh_put_json فيها expected_sha",
      bool(_put) and "expected_sha" in [a.arg for a in _put.args.args], True)
_body = _ast.get_source_segment(_APP, _put) or ""
check("بتستخدم expected_sha مش SHA جديد دايمًا",
      "expected_sha if expected_sha is not None else" in _body, True)
check("بتتعامل مع 409",            "409" in _body, True)
check("وبتسجّل التعارض",           '_GH_STATE["conflict"]' in _body, True)
check("الملفات الشهرية بتمرّر SHA",  "expected_sha=_exp" in _APP, True)
check("الملف القديم بيمرّر SHA",
      'expected_sha=(_GH_STATE.get("file_sha") or {}).get(GITHUB_JSON_PATH)' in _APP, True)
check("SHA بيتخزّن وقت القراءة",   '_shas[f"{GITHUB_MONTHLY_DIR}/{e[\'name\']}"]' in _APP
      or "_remember_sha(GITHUB_JSON_PATH" in _APP, True)
check("بانر التعارض موجود",        'st.button("🔄 تحديث من GitHub ودمج"' in _APP, True)


print("\n⑬ ما بعد التعارض — ممنوع الدوس")
# ★ البق ده اتكشف في المراجعة الثلاثية: بعد 409 كان الـSHA بيتشال من الكاش،
#   فالمحاولة الجاية بتبعت expected_sha=None → الدالة تجيب SHA جديد →
#   GitHub يقبل → الدوسة تحصل. يعني التعارض كان بيتحوّل لفقد بيانات
#   بعد ضغطة واحدة زيادة.
check("SHA مابيتشالش بعد 409",
      'pop(path, None)\n            return False' not in _APP, True)
check("فيه حارس بيمنع الحفظ وقت التعارض",
      'if _GH_STATE.get("conflict"):' in _APP, True)
check("والحارس قبل أي كتابة",
      _APP.index('if _GH_STATE.get("conflict"):') < _APP.index('rows = conn.execute'), True)
check("التعارض بيتصفّر عند النجاح",
      '_GH_STATE["conflict"]          = ""' in _APP, True)
check("وبيتصفّر عند الدمج اليدوي",
      '_GH_STATE["conflict"] = ""\n            _GH_STATE["file_sha"] = {}' in _APP, True)

# محاكاة: الفرع بيحاول تاني بعد التعارض
gh3 = FakeGitHub()
gh3.put("Visits.json", ["v1"] * 100, None)
a_sha, a = gh3.read("Visits.json")
b_sha, b = gh3.read("Visits.json")
gh3.put("Visits.json", list(a) + ["X"], a_sha)          # الفرع الأول
code, _ = gh3.put("Visits.json", list(b) + ["Y"], b_sha)  # الفرع التاني → 409
check("المحاولة الأولى اترفضت", code, 409)
# المحاولة التانية بنفس الـSHA القديم (السلوك الصح)
code2, _ = gh3.put("Visits.json", list(b) + ["Y", "Z"], b_sha)
check("المحاولة التانية اترفضت برضه", code2, 409)
check("وX لسه موجودة", "X" in gh3.files["Visits.json"][1], True)

print("\n" + "═" * 60)
if _FAILS:
    print(f"❌ فشل {len(_FAILS)} اختبار: {', '.join(_FAILS[:5])}")
    raise SystemExit(1)
print("✅ كل اختبارات الحُرّاس نجحت")
