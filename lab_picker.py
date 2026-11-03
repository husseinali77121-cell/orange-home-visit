# lab_picker.py
# ══════════════════════════════════════════════════════════════════════════════
#  🔎 محرك اختيار التحاليل الذكي — Orange Lab HVMS
#  الهدف: نفس فكرة برنامج الـ Price List — بحث ذكي بالعربي والإنجليزي،
#         اختيار متعدد، حماية من الازدواج، وملخص الأنابيب المطلوبة.
#
#  ⚠️ صيغة السطر المخزّن **لم تتغير**: "Test Name — 400 جنيه"
#     عشان كل الدوال القديمة (WhatsApp / PDF / _lab_price / التقارير) تشتغل زي ما هي.
# ══════════════════════════════════════════════════════════════════════════════

import re
import difflib
import hashlib

SEP = " — "                       # نفس الفاصل المستخدم في البرنامج الأصلي
PRICE_RE = re.compile(r'(\d+)\s*جنيه')

# ──────────────────────────────────────────────────────────────────────────────
# 1) تطبيع النص (عربي + إنجليزي)
# ──────────────────────────────────────────────────────────────────────────────
_DIAC = re.compile(r'[\u064B-\u0652\u0670\u0640]')
_NONWORD = re.compile(r'[^\w\u0600-\u06FF]+')


def norm(s):
    """تطبيع: تشكيل، همزات، ة/ه، ى/ي، أرقام عربية، علامات ترقيم."""
    s = str(s or "").lower()
    s = _DIAC.sub("", s)
    for a, b in (("أ", "ا"), ("إ", "ا"), ("آ", "ا"), ("ٱ", "ا"),
                 ("ة", "ه"), ("ى", "ي"), ("ؤ", "و"), ("ئ", "ي")):
        s = s.replace(a, b)
    s = s.translate(str.maketrans("٠١٢٣٤٥٦٧٨٩", "0123456789"))
    s = _NONWORD.sub(" ", s)
    return re.sub(r"\s+", " ", s).strip()


# ──────────────────────────────────────────────────────────────────────────────
# 2) المرادفات — الاسم اللي بيقوله العميل/الدكتور → كلمات البحث الحقيقية
#    زوّدها براحتك، مفيش حد أقصى.
# ──────────────────────────────────────────────────────────────────────────────
ALIASES = {
    # سكر
    "سكر": ["fbg", "rbg", "hba1c"],
    "سكر صايم": ["fbg"], "صائم": ["fbg"], "صايم": ["fbg"],
    "سكر فاطر": ["ppbg"], "فاطر": ["ppbg"],
    "تراكمي": ["hba1c"], "سكر تراكمي": ["hba1c"], "a1c": ["hba1c"], "sugar": ["fbg", "rbg"],
    "منحني السكر": ["glucose tolerance"],
    # دم
    "صوره دم": ["cbc"], "صوره دم كامله": ["cbc"], "سي بي سي": ["cbc"],
    "هيموجلوبين": ["hb hemoglobin"], "نسبه الدم": ["hb hemoglobin", "cbc"],
    "صفايح": ["platelets"], "صفائح": ["platelets"],
    "سرعه ترسيب": ["esr"], "esr": ["esr"], "ترسيب": ["esr"],
    "فصيله": ["abo", "blood rh"], "فصيله دم": ["abo", "blood rh"],
    "كومبس": ["coombs"], "ار اتش": ["blood rh"],
    "انيميا": ["cbc", "ferritin", "iron"], "فقر دم": ["cbc", "ferritin"],
    # كلى
    "وظائف كلي": ["urea", "creatinine", "uric acid"],
    "كليه": ["urea", "creatinine"], "كرياتينين": ["creatinine"], "يوريا": ["urea"],
    "نقرس": ["uric acid"], "حمض بوليك": ["uric acid"],
    "املاح": ["na sodium", "k potassium"], "صوديوم": ["na sodium"], "بوتاسيوم": ["k potassium"],
    "كالسيوم": ["calcium"], "ماغنسيوم": ["magnesium"], "فوسفور": ["po4 phosphorus"],
    # كبد
    "وظائف كبد": ["alt sgpt", "ast sgot", "bilirubin", "albumin"],
    "كبد": ["alt sgpt", "ast sgot"], "صفرا": ["bilirubin"], "صفراء": ["bilirubin"],
    "البيومين": ["albumin"], "زلال": ["albumin", "protein in urine"],
    # دهون
    "دهون": ["cholesterol", "hdl", "ldl", "triglycerides"],
    "دهنيات": ["cholesterol", "hdl", "ldl", "triglycerides"],
    "كوليسترول": ["cholesterol"], "تراي": ["triglycerides"], "دهون ثلاثيه": ["triglycerides"],
    # غدة
    "غده": ["tsh", "ft3", "ft4"], "غده درقيه": ["tsh", "ft3", "ft4"],
    "free t4": ["ft4"], "free t3": ["ft3"], "t4 حر": ["ft4"], "t3 حر": ["ft3"],
    "درقيه": ["tsh", "ft3", "ft4"], "thyroid": ["tsh", "ft3", "ft4"],
    # فيتامينات ومعادن
    "فيتامين د": ["vitamin d3"], "vit d": ["vitamin d3"], "vitd": ["vitamin d3"],
    "فيتامين ب12": ["vitamin b12"], "b12": ["vitamin b12"], "ب12": ["vitamin b12"],
    "حديد": ["ferritin", "iron", "tibc"], "مخزون الحديد": ["ferritin"],
    "زنك": ["zinc"], "فوليك": ["folic"],
    # هرمونات
    "هرمون الحليب": ["prolactin"], "لبن": ["prolactin"], "برولاكتين": ["prolactin"],
    "هرمونات انثويه": ["fsh", "lh", "estradiol", "prolactin"],
    "هرمونات ذكوره": ["testosterone"], "تستوستيرون": ["testosterone"],
    "خصوبه": ["fsh", "lh", "amh", "prolactin"], "تبويض": ["lh", "progesterone"],
    "كورتيزون": ["cortisol"], "كورتيزول": ["cortisol"],
    # حمل
    "حمل": ["pregnancy", "bhcg"], "تحليل حمل": ["pregnancy", "bhcg"], "hcg": ["bhcg"],
    # بول / براز / سوائل
    "بول": ["urine examination", "urine culture"],
    "تحليل بول": ["urine examination"], "بول كامل": ["urine examination"],
    "صديد": ["urine examination"], "املاح بول": ["urine electrolytes"],
    "زرع بول": ["urine culture"], "مزرعه بول": ["urine culture"],
    "مزرعه دم": ["blood culture"], "مزرعه براز": ["stool culture"],
    "مزرعه حلق": ["throat culture"], "مزرعه بلغم": ["sputum culture"],
    "براز": ["stool examination", "stool culture"],
    "تحليل براز": ["stool examination"],
    "سائل منوي": ["semen examination", "semen culture"],
    "منوي": ["semen examination", "semen culture"],
    "تحليل منوي": ["semen examination"], "سيمن": ["semen examination"],
    # مزارع + نوع العيّنة (كلمات قصيرة — مطابقة تامة)
    "دم": ["blood"], "بلغم": ["sputum"], "زور": ["throat"], "حلق": ["throat"],
    "اذن": ["ear"], "انف": ["nasal"], "عين": ["conjuntival"], "جرح": ["wound"],
    "صديد اذن": ["ear discharge"],
    "مزرعه": ["culture"], "مزرعة": ["culture"], "زرع": ["culture"],
    "حساسيه مضادات": ["culture and sensitivity"],
    # سيولة
    "سيوله": ["pt", "ptt", "bleeding time", "clotting time"],
    "تجلط": ["pt", "ptt", "fibrinogen"],
    "دي دايمر": ["d dimer"],
    # التهاب / مناعة
    "التهاب": ["crp"], "crp": ["crp"], "روماتويد": ["rheumatoid"], "روماتيزم": ["aso", "rheumatoid"],
    "اسو": ["asot", "streptolysin"], "aso": ["asot"],
    # فيروسات
    "فيروس سي": ["hcv"], "كبد وبائي سي": ["hcv"], "فيروس بي": ["hbs"], "كبد وبائي بي": ["hbs"],
    "ايدز": ["hiv"], "درن": ["tb"], "سل": ["tb"],
    # أورام
    "بروستاتا": ["psa"], "دلالات اورام": ["tumor", "marker"],
    # قلب
    "قلب": ["troponin", "ck mb"], "تروبونين": ["troponin"],
}

_ALIAS_NORM = {norm(k): v for k, v in ALIASES.items()}


# ──────────────────────────────────────────────────────────────────────────────
# 3) صيغة السطر
# ──────────────────────────────────────────────────────────────────────────────
def format_entry(name, price):
    return f"{str(name).strip()}{SEP}{int(price or 0)} جنيه"


def entry_name(entry):
    """
    اسم التحليل من سطر مخزّن (يشيل جزء السعر).
    بيتعامل كمان مع السطور القديمة اللي اتكتبت يدوي بشرطة عادية:
    "CBC - 400 جنيه" → "CBC" (من غير الشرطة الزايدة).
    """
    s = str(entry or "")
    s = s.split(SEP)[0] if SEP in s else re.sub(r'\s*\d+\s*جنيه\s*$', '', s)
    return s.strip().rstrip("-–—:،,").strip()


def entry_price(entry):
    m = PRICE_RE.search(str(entry or ""))
    return int(m.group(1)) if m else 0


def entries_total(entries):
    return sum(entry_price(e) for e in (entries or []))


# ──────────────────────────────────────────────────────────────────────────────
# 4) البحث الذكي
# ──────────────────────────────────────────────────────────────────────────────
_TERM_CACHE = {}


def _has_term(nname, term):
    """مطابقة على حدود الكلمة — تمنع 'pt' إنها تلزق جوّه 'receptor'."""
    if not term:
        return False
    key = (nname, term)
    v = _TERM_CACHE.get(key)
    if v is None:
        if len(_TERM_CACHE) > 50000:
            _TERM_CACHE.clear()
        v = re.search(r'(?<![\w\u0600-\u06FF])' + re.escape(term) +
                      r'(?![\w\u0600-\u06FF])', nname) is not None
        _TERM_CACHE[key] = v
    return v


def _direct_score(nq, tokens, nname, loose=True):
    """تطابق مباشر. loose=False للمرادفات — لازم كل الكلمات تتحقق."""
    if not nq:
        return 0
    if nq == nname:
        return 1000
    if nname.startswith(nq):
        return 850 - min(len(nname), 100)
    if nq in nname:
        return 700 - min(len(nname), 100)
    if len(tokens) > 1:
        # الكلمة القصيرة (حرف/حرفين) لازم تكون كلمة مستقلة — مش أي "d" جوّه اسم
        def _hit(t):
            return (t in nname) if len(t) >= 3 else _has_term(nname, t)
        if all(_hit(t) for t in tokens):
            return 620 - min(len(nname), 100)
        # "كل الكلمات إلا واحدة" — من ٣ كلمات فأكتر بس، عشان ميبقاش فضفاض
        if loose and len(tokens) >= 3 and \
                sum(1 for t in tokens if _hit(t)) >= len(tokens) - 1:
            return 470
    return 0


def _phrase_aliases(nq):
    """مرادفات الجملة كاملة: [(term, order_index), ...]"""
    if nq in _ALIAS_NORM:
        return [(norm(t), i) for i, t in enumerate(_ALIAS_NORM[nq])]
    out = []
    for k, v in _ALIAS_NORM.items():
        if len(k) >= 4 and k in nq:
            out.extend((norm(t), i) for i, t in enumerate(v))
    return out


def _token_options(tok):
    """
    بدائل الكلمة الواحدة (عربي ↔ إنجليزي) — للبحث المركّب زي «مزرعة بول».
    ⚠️ الهدف المركّب (زي "vitamin b12") بيتساب **جملة واحدة**؛ لو قسّمناه
       كلمة كلمة، كلمة عامة زي "vitamin" هتخلي «فيتامين ب12» تجيب فيتامين A.
    """
    opts = {tok}
    if len(tok) < 2:
        return opts
    for k, v in _ALIAS_NORM.items():
        hit = (k == tok) or (len(k) >= 3 and len(tok) >= 3 and (k in tok or tok in k))
        if not hit:
            continue
        for t in v:
            nt = norm(t)
            opts.add(nt)                       # الجملة كاملة (بحدود الكلمة)
    return opts


def search_labs(all_labs, query, category=None, limit=60):
    """يرجّع (results, suggestions). results = list من dicts زي ALL_LABS."""
    pool = [l for l in all_labs
            if not category or category == "الكل" or l.get("category") == category]
    nq = norm(query)
    if not nq:
        # ⚠️ من غير بحث بنرجّع **القسم كامل** مش أول 60.
        #    قبل كده، «Separate» (99 تحليل) و«Autoimmune» (68) كانوا بيتقصّوا،
        #    و«الكل» كان بيوري 60 من 836 — يعني الاستعراض اليدوي مكنش بيوصل
        #    لكل التحاليل لو البحث فشل لأي سبب.
        return list(pool), []

    tokens = [t for t in nq.split() if t]
    phrase = _phrase_aliases(nq)
    groups = [_token_options(t) for t in tokens] if len(tokens) > 1 else []

    scored = []
    for lab in pool:
        nname = norm(lab["name"])
        sc = _direct_score(nq, tokens, nname)          # 470 – 1000

        # بحث مركّب: كل كلمة لازم تتحقق (هي أو أحد بدائلها)
        if sc == 0 and groups:
            ok = all(
                any((o == g_tok and len(o) >= 3 and o in nname) or _has_term(nname, o)
                    for o in g)
                for g, g_tok in zip(groups, tokens)
            )
            if ok:
                sc = 480 - min(len(nname), 60) * 0.5   # 450 – 480

        # مرادف الجملة كاملة
        if sc == 0 and phrase:
            best = 0
            for term, idx in phrase:
                t_tokens = term.split()
                if len(t_tokens) == 1 and not _has_term(nname, term):
                    continue
                s2 = _direct_score(term, t_tokens, nname, loose=False)
                if s2:
                    best = max(best, s2 * 0.25 + max(0, 6 - idx))
            if best:
                sc = 250 + best                        # ~300 – 510

        if sc:
            scored.append((sc, len(lab["name"]), lab.get("price", 0), lab["name"], lab))

    scored.sort(key=lambda x: (-x[0], x[1], x[2], x[3]))
    results = [x[4] for x in scored][:limit]

    # شبكة أمان: مرادف موجود بس التطابق الصارم فشل (اسم التحليل مختصر في القائمة)
    if not results and phrase:
        loose = []
        for lab in pool:
            nname = norm(lab["name"])
            best = 0
            for term, idx in phrase:
                for w in term.split():
                    if (w in nname) if len(w) >= 4 else _has_term(nname, w):
                        best = max(best, 300 - min(len(nname), 100) + max(0, 6 - idx))
            if best:
                loose.append((best, len(lab["name"]), lab["name"], lab))
        loose.sort(key=lambda x: (-x[0], x[1], x[2]))
        results = [x[3] for x in loose][:limit]

    # اقتراحات "هل تقصد؟" لو مفيش أي نتيجة (أخطاء إملائية)
    suggestions = []
    if not results:
        names = {}
        for l in pool:
            names.setdefault(norm(l["name"]), l)
        keys = list(names.keys())
        hits = difflib.get_close_matches(nq, keys, n=5, cutoff=0.5)
        if not hits:
            firsts = {}
            for k in keys:
                firsts.setdefault(k.split()[0] if k.split() else k, k)
            hits = [firsts[m] for m in
                    difflib.get_close_matches(nq, list(firsts.keys()), n=5, cutoff=0.6)]
        suggestions = [names[h] for h in hits if h in names]
    return results, suggestions


# ──────────────────────────────────────────────────────────────────────────────
# 5) بوابة الازدواج (Double-charge gate) — نفس فكرة برنامج الفواتير
# ──────────────────────────────────────────────────────────────────────────────
PROFILE_COMPONENTS = {
    "Lipid profile":   ["Cholesterol", "HDL", "LDL", "Triglycerides", "VLDL"],
    "Kidney profile":  ["Urea", "BUN", "Creatinine (Serum)", "Uric Acid", "Na (Sodium)",
                        "K (Potassium)", "Calcium (Total)", "PO4 (Phosphorus)",
                        "eGFR (Glomerular filtration"],
    "Liver profile":   ["ALT (SGPT)", "AST (SGOT)", "Albumin (ALB)", "Total Protein",
                        "Bilirubin Total", "Bilirubin Direct", "Bilirubin Indirect",
                        "Alkaline Phosphatase (ALP)", "GGT (Gamma-glutamyl transferase)",
                        "A/G Ratio", "Globulin"],
    "Thyroid profile": ["TSH", "FT3", "FT4", "T3 (Total)", "T4 (Total)"],
}
_PROF_NORM = {norm(k): [norm(c) for c in v] for k, v in PROFILE_COMPONENTS.items()}


def find_conflicts(entries):
    """يرجّع list من dicts: {'profile','overlap','wasted'} لكل ازدواج باقة + مفرداتها."""
    names = [entry_name(e) for e in (entries or [])]
    nmap = {norm(n): (n, entry_price(e)) for n, e in zip(names, entries or [])}
    out = []
    for prof_n, comps in _PROF_NORM.items():
        if prof_n not in nmap:
            continue
        overlap = [nmap[c] for c in comps if c in nmap]
        if overlap:
            out.append({
                "profile": nmap[prof_n][0],
                "overlap": [o[0] for o in overlap],
                "wasted":  sum(o[1] for o in overlap),
            })
    # تكرار حرفي لنفس الاسم
    seen, dups = set(), []
    for n in names:
        k = norm(n)
        if k in seen and n not in dups:
            dups.append(n)
        seen.add(k)
    return out, dups


def drop_components(entries, profile_name):
    """يشيل مفردات باقة معيّنة ويسيب الباقة."""
    comps = _PROF_NORM.get(norm(profile_name), [])
    return [e for e in entries if norm(entry_name(e)) not in comps]


# ──────────────────────────────────────────────────────────────────────────────
# 6) ملخص العيّنات — الدكتور يعرف ياخد معاه إيه قبل ما يخرج
# ──────────────────────────────────────────────────────────────────────────────
TUBE_RULES = [
    ("edta",                       "🟣 EDTA (بنفسجي)"),
    ("floride",                    "⚪ Fluoride (رمادي)"),
    ("fluoride",                   "⚪ Fluoride (رمادي)"),
    ("citrat",                     "🔵 Citrate (أزرق)"),
    ("heparin",                    "🟢 Heparin (أخضر)"),
    ("urine",                      "🥤 برطمان بول"),
    ("stool",                      "🥤 برطمان براز"),
    ("semen",                      "🥤 برطمان سائل منوي"),
    ("csf",                        "🧫 CSF"),
    ("fluid",                      "🧫 Body fluid"),
    ("swab",                       "🧫 Swab"),
    ("serum",                      "🔴 Serum (أحمر / جل)"),
    ("plasma",                     "🔴 أنبوبة بلازما"),
]


def sample_summary(entries, lab_index):
    """
    lab_index: dict اسم-مطبّع → dict فيه collection_notes / result_days.
    يرجّع dict: tubes(list), fasting(bool), frozen(bool), max_days(int), notes(list)
    """
    tubes, notes = [], []
    fasting = frozen = False
    max_days = 0
    for e in (entries or []):
        info = lab_index.get(norm(entry_name(e)))
        if not info:
            continue
        cn = str(info.get("collection_notes") or "").lower()
        rd = info.get("result_days")
        try:
            max_days = max(max_days, int(rd or 0))
        except Exception:
            pass
        if "fasting" in cn or "صيام" in cn:
            fasting = True
        if "frozen" in cn or "froz" in cn:
            frozen = True
        matched = False
        for kw, label in TUBE_RULES:
            if kw in cn:
                if label not in tubes:
                    tubes.append(label)
                matched = True
                break
        if not matched and cn and cn != "none":
            if cn not in notes:
                notes.append(cn)
    return {"tubes": tubes, "fasting": fasting, "frozen": frozen,
            "max_days": max_days, "notes": notes[:4]}


def build_lab_index(labs_db):
    """من LABS_DB → dict مطبّع للبحث السريع عن تفاصيل العيّنة."""
    idx = {}
    for cat, tests in (labs_db or {}).items():
        for t in tests:
            idx.setdefault(norm(t.get("name", "")), {
                "name": t.get("name", ""), "price": t.get("price", 0), "category": cat,
                "result_days": t.get("result_days"),
                "collection_notes": t.get("collection_notes"),
            })
    return idx


# ══════════════════════════════════════════════════════════════════════════════
# 7) واجهة Streamlit — قابلة لإعادة الاستخدام (الحالة الأساسية + الحالات الإضافية)
# ══════════════════════════════════════════════════════════════════════════════
def _add_many(st, ss_key, labs, container_list=None):
    """يضيف تحاليل من غير تكرار. يرجّع عدد اللي اتضاف فعلاً."""
    target = container_list if container_list is not None else st.session_state[ss_key]
    existing = {norm(entry_name(x)) for x in target}
    n = 0
    for lab in labs:
        if norm(lab["name"]) not in existing:
            target.append(format_entry(lab["name"], lab["price"]))
            existing.add(norm(lab["name"]))
            n += 1
    return n


# ══════════════════════════════════════════════════════════════════════════════
# 🎯 المُحلِّل — نفس منطق برنامج التسعير: اكتب واضغط Enter
# ══════════════════════════════════════════════════════════════════════════════
#   exact / alias  → يتضاف على طول
#   ambiguous      → أكتر من احتمال، اختار الصح
#   suggest        → قريب بس مش مؤكد، أكّده
#   not_found      → مش موجود
# البرنامج **مابيخمّنش ويضيف من نفسه** في أي حالة غير المؤكدة.
EXACT, ALIAS, AMBIGUOUS, SUGGEST, NOT_FOUND = (
    "exact", "alias", "ambiguous", "suggest", "not_found")


def _dedupe(labs):
    out, seen = [], set()
    for l in labs:
        k = norm(l["name"])
        if k not in seen:
            seen.add(k)
            out.append(l)
    return out


def resolve_lab(all_labs, query, max_cands=8):
    """يرجّع dict: status / query / cands / reason."""
    nq = norm(query)
    if not nq:
        return {"status": NOT_FOUND, "query": query, "cands": [], "reason": "الاسم فاضي"}

    # ── المستوى ١: مطابقة تامة للاسم ──
    # ⚠️ ممنوع _dedupe هنا: هي بتوحّد بالاسم المطبّع، وده كان بيخفي الأسماء
    #    المكررة اللي **بأسعار مختلفة** ويخلّيها تتضاف فوراً بأول سعر يقابله.
    #    في القائمة ٤ أسماء كده، أكبرها فرق ٣٤٠٠ جنيه.
    exact = [l for l in all_labs if norm(l["name"]) == nq]
    if exact:
        prices = {int(l.get("price") or 0) for l in exact}
        if len(prices) == 1:
            return {"status": EXACT, "query": query, "cands": exact[:1],
                    "reason": "مطابقة تامة"}
        return {"status": AMBIGUOUS, "query": query, "cands": exact[:max_cands],
                "reason": "الاسم ده مكرر في قائمة الأسعار بأسعار مختلفة — اختار الصح"}

    # ── المستوى ٢: اختصار معروف (سكر / صورة دم / فيتامين د …) ──
    targets = _ALIAS_NORM.get(nq)
    if targets:
        cands = []
        for t in targets:
            hits, _ = search_labs(all_labs, t)
            if hits:
                cands.append(hits[0])
        cands = _dedupe(cands)
        if len(cands) == 1:
            # لو الاسم اللي وصلنا له مكرر بأسعار مختلفة، لازم تأكيد برضه
            twins = [l for l in all_labs if norm(l["name"]) == norm(cands[0]["name"])]
            if len({int(l.get("price") or 0) for l in twins}) > 1:
                return {"status": AMBIGUOUS, "query": query, "cands": twins[:max_cands],
                        "reason": "الاسم مكرر بأسعار مختلفة — اختار الصح"}
            return {"status": ALIAS, "query": query, "cands": cands,
                    "reason": f"اختصار معروف ← {cands[0]['name']}"}
        if cands:
            return {"status": AMBIGUOUS, "query": query, "cands": cands[:max_cands],
                    "reason": f"«{query}» ليها {len(cands)} احتمالات"}

    # ── المستوى ٣: نتائج البحث ──
    hits, sugg = search_labs(all_labs, query)
    if hits:
        return {"status": SUGGEST, "query": query, "cands": hits[:max_cands],
                "reason": ("نتيجة واحدة قريبة — أكّدها" if len(hits) == 1
                           else f"{len(hits)} نتيجة محتملة — اختار الصح")}
    if sugg:
        return {"status": SUGGEST, "query": query, "cands": sugg[:max_cands],
                "reason": "مفيش مطابقة تامة — دي أقرب أسماء"}
    return {"status": NOT_FOUND, "query": query, "cands": [],
            "reason": "مش موجود في قائمة الأسعار"}


def _meta_line(lab):
    bits = []
    if lab.get("result_days"):
        bits.append(f"⏱️ النتيجة خلال {lab['result_days']} يوم")
    cn = lab.get("collection_notes")
    if cn and str(cn).lower() != "none":
        bits.append(f"🧪 {cn}")
    return "  ·  ".join(bits)


def render_lab_picker(st, all_labs, key_prefix, ss_key=None, target_list=None,
                      compact=False):
    """
    خانة واحدة: اكتب اسم التحليل واضغط Enter.
    • اسم مؤكد → يتضاف فوراً.
    • غير مؤكد → قايمة قصيرة تختار منها وتأكّد.
    بيرجّع عدد التحاليل اللي اتضافت في الرن ده.
    """
    if not all_labs:
        st.warning("قائمة الأسعار غير متاحة حالياً")
        return 0

    pend_key = f"{key_prefix}__pending"
    added = 0

    # ⚠️ st.form: الضغط على Enter جوّه الخانة بيبعت مباشرة، و clear_on_submit
    #    بيفضّيها لوحدها — فتقدر تكتب تحليل ورا التاني من غير أي ضغطات زيادة.
    with st.form(f"{key_prefix}__form", clear_on_submit=True):
        c1, c2 = st.columns([4, 1])
        with c1:
            q = st.text_input(
                "اسم التحليل", key=f"{key_prefix}_q",
                placeholder="cbc • سكر • فيتامين د • مزرعة بول",
                label_visibility="collapsed",
            )
        with c2:
            submitted = st.form_submit_button("➕ أضف", use_container_width=True)

    if submitted:
        if not q.strip():
            st.session_state[pend_key] = None
        else:
            r = resolve_lab(all_labs, q)
            if r["status"] in (EXACT, ALIAS):
                lab = r["cands"][0]
                n = _add_many(st, ss_key, [lab], target_list)
                if n:
                    st.success(f"✅ {lab['name']} — {lab['price']:,} جنيه"
                               + (f"  ({r['reason']})" if r["status"] == ALIAS else ""))
                    added += n
                else:
                    st.warning(f"⚠️ {lab['name']} مضاف بالفعل")
                st.session_state[pend_key] = None
            else:
                st.session_state[pend_key] = r

    # ── بوابة التأكيد ──
    pend = st.session_state.get(pend_key)
    if pend:
        cands = pend.get("cands") or []
        if pend["status"] == AMBIGUOUS:
            st.warning(f"🔎 «{pend['query']}» — {pend['reason']}. اختار التحليل الصح:")
        elif pend["status"] == SUGGEST:
            st.warning(f"🔎 «{pend['query']}» — {pend['reason']}:")
        else:
            st.error(f"⛔ «{pend['query']}» — {pend['reason']}")

        if cands:
            # ⚠️ مفتاح الراديو لازم يتغيّر مع تغيّر البحث، وإلا اختيار قديم
            #    مش موجود في القايمة الجديدة بيرمي استثناء ويقفل الصفحة.
            sig = hashlib.md5(str(pend["query"]).encode("utf-8")).hexdigest()[:8]
            _names = [c["name"] for c in cands]
            _clash = len(set(_names)) != len(_names)   # أسماء متطابقة → وضّح القسم
            opts = [f"{c['name']}  ·  {c['price']:,} جنيه"
                    + (f"  ·  {c.get('category','')}" if _clash else "")
                    for c in cands]
            # لو لسه فيه تكرار حرفي (نفس الاسم والسعر والقسم) نرقّمهم عشان
            # st.radio ما ياخدش خيارين بنفس النص
            if len(set(opts)) != len(opts):
                opts = [f"{i+1}. {o}" for i, o in enumerate(opts)]
            pick = st.radio("الاختيارات المتاحة", opts,
                            key=f"{key_prefix}_pick_{sig}",
                            label_visibility="collapsed")
            rec = cands[opts.index(pick)] if pick in opts else cands[0]
            meta = _meta_line(rec)
            if meta:
                st.caption(meta)

            a1, a2 = st.columns(2)
            with a1:
                if st.button("✅ أكّد وأضف", key=f"{key_prefix}_ok_{sig}",
                             use_container_width=True):
                    if _add_many(st, ss_key, [rec], target_list):
                        st.toast(f"✅ {rec['name']}")
                    else:
                        st.toast(f"⚠️ {rec['name']} مضاف بالفعل")
                    st.session_state[pend_key] = None
                    st.rerun()
            with a2:
                if st.button("❌ إلغاء", key=f"{key_prefix}_no_{sig}",
                             use_container_width=True):
                    st.session_state[pend_key] = None
                    st.rerun()
        else:
            if st.button("حسناً", key=f"{key_prefix}_okay", use_container_width=True):
                st.session_state[pend_key] = None
                st.rerun()

    return added


def render_conflicts(st, entries, key_prefix, ss_key=None, target_list=None):
    """تحذير الازدواج + زرار إصلاح بضغطة."""
    conflicts, dups = find_conflicts(entries)
    for i, c in enumerate(conflicts):
        st.warning(
            f"⚠️ **{c['profile']}** مضافة ومعاها مفرداتها: "
            f"{'، '.join(c['overlap'])} — العميل هيتحاسب مرتين "
            f"(زيادة ≈ {c['wasted']:,} جنيه)."
        )
        if st.button(f"🧹 شيل المفردات وسيب {c['profile']}",
                     key=f"{key_prefix}_fix_{i}", use_container_width=True):
            cleaned = drop_components(entries, c["profile"])
            if target_list is not None:
                target_list[:] = cleaned
            else:
                st.session_state[ss_key] = cleaned
            st.rerun()
    if dups:
        st.info(f"🔁 تحاليل مكررة: {'، '.join(dups)}")


def render_sample_box(st, entries, lab_index):
    """صندوق الأنابيب/الصيام — يظهر بس لو فيه تحاليل معروفة."""
    s = sample_summary(entries, lab_index)
    if not (s["tubes"] or s["fasting"] or s["frozen"]):
        return
    bits = []
    if s["tubes"]:
        bits.append("🧫 <b>العيّنات:</b> " + " • ".join(s["tubes"]))
    if s["fasting"]:
        bits.append("⏰ <b>صيام مطلوب</b> — نبّه العميل قبل الزيارة")
    if s["frozen"]:
        bits.append("❄️ <b>عيّنة مجمّدة</b> — جهّز الثلج/التجميد")
    if s["max_days"]:
        bits.append(f"📅 <b>أقصى مدة نتيجة:</b> {s['max_days']} يوم")
    st.markdown(
        '<div style="background:#FFF8F2;border:1px solid #FFD9BC;border-radius:10px;'
        'padding:10px 12px;margin:8px 0;font-size:12.5px;line-height:1.9;color:#5A3A22">'
        + "<br>".join(bits) + "</div>", unsafe_allow_html=True)
