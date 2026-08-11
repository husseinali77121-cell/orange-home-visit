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
    "سكر": ["glucose", "fbg", "rbg", "hba1c"],
    "سكر صايم": ["fbg"], "صائم": ["fbg"], "صايم": ["fbg"],
    "سكر فاطر": ["ppbg"], "فاطر": ["ppbg"],
    "تراكمي": ["hba1c"], "سكر تراكمي": ["hba1c"], "a1c": ["hba1c"], "sugar": ["glucose", "fbg"],
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
    "بول": ["urine"], "تحليل بول": ["urine examination"],
    "صديد": ["urine examination"], "املاح بول": ["urine electrolytes"],
    "براز": ["stool"], "تحليل براز": ["stool examination"],
    "سائل منوي": ["semen"], "منوي": ["semen"],
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
        line = format_entry(lab["name"], lab["price"])
        if norm(lab["name"]) not in existing:
            target.append(line)
            existing.add(norm(lab["name"]))
            n += 1
    return n


def render_lab_picker(st, all_labs, categories, key_prefix,
                      ss_key=None, target_list=None, compact=False):
    """
    البحث الذكي + الاختيار المتعدد.
    - ss_key      : مفتاح session_state فيه list (للحالة الأساسية)
    - target_list : list مباشرة (للحالات الإضافية)
    بيرجّع عدد التحاليل اللي اتضافت في الرن ده.
    """
    if not all_labs:
        st.warning("قائمة الأسعار غير متاحة حالياً")
        return 0

    nonce_key = f"{key_prefix}__nonce"
    if nonce_key not in st.session_state:
        st.session_state[nonce_key] = 0
    n = st.session_state[nonce_key]

    # 🔑 مفتاحا البحث/القسم **ثابتين** — عشان الكلمة متضيعش بعد كل إضافة.
    c1, c2 = st.columns([3, 2])
    with c1:
        q = st.text_input(
            "🔎 ابحث", key=f"{key_prefix}_q",
            placeholder="سكر • صورة دم • فيتامين د • CBC • مزرعة بول",
            label_visibility="collapsed" if compact else "visible",
        )
    with c2:
        cat = st.selectbox("القسم", ["الكل"] + categories, key=f"{key_prefix}_cat",
                           label_visibility="collapsed" if compact else "visible")

    results, suggestions = search_labs(all_labs, q, cat)

    # ⚠️ مفتاح الـ multiselect لازم يتغيّر مع تغيّر البحث/القسم.
    #    لو فضل ثابت، اختيار قديم مش موجود في النتائج الجديدة بيرمي
    #    StreamlitAPIException ويقفل الصفحة كلها. الـ sig ده هو اللي بيمنع ده.
    sig = hashlib.md5(f"{q}||{cat}".encode("utf-8")).hexdigest()[:8]
    wk = f"{sig}_{n}"

    if not results:
        if suggestions:
            st.caption("مفيش نتيجة مطابقة — هل تقصد؟")
            for i, s in enumerate(suggestions):
                if st.button(f"↩️ {s['name']} — {s['price']} جنيه",
                             key=f"{key_prefix}_sg_{wk}_{i}", use_container_width=True):
                    _add_many(st, ss_key, [s], target_list)
                    st.session_state[nonce_key] += 1
                    return 1
        else:
            st.caption("مفيش نتائج — جرّب كلمة أقصر، أو اكتبه يدوياً تحت.")
        return 0

    # ⚡ أضف أسرع نتيجة بضغطة واحدة (مفيد جداً على الموبايل)
    if q.strip():
        top = results[0]
        if st.button(f"⚡ أضف: {top['name']} — {top['price']} جنيه",
                     key=f"{key_prefix}_top_{wk}", use_container_width=True):
            added = _add_many(st, ss_key, [top], target_list)
            st.session_state[nonce_key] += 1
            return added

    # أسماء متكررة بين الأقسام → عناوين مكررة في الـ multiselect. بنوحّدها.
    lab_by_label, labels = {}, []
    for l in results:
        lbl = f"{l['name']}{SEP}{l['price']} جنيه"
        if lbl not in lab_by_label:
            lab_by_label[lbl] = l
            labels.append(lbl)

    st.caption(f"{len(results)} نتيجة" + (f" في «{cat}»" if cat != "الكل" else ""))
    picked = st.multiselect("اختر تحليل أو أكتر", labels, key=f"{key_prefix}_ms_{wk}",
                            label_visibility="collapsed" if compact else "visible")

    if picked:
        st.caption(f"المحدد: {len(picked)} تحليل — "
                   f"{sum(lab_by_label[p]['price'] for p in picked):,} جنيه")

    if st.button(f"➕ أضف المحدد ({len(picked)})" if picked else "➕ أضف المحدد",
                 key=f"{key_prefix}_add_{wk}", use_container_width=True,
                 disabled=not picked):
        added = _add_many(st, ss_key, [lab_by_label[p] for p in picked], target_list)
        st.session_state[nonce_key] += 1
        if added < len(picked):
            st.toast(f"⚠️ {len(picked)-added} تحليل كان مضاف قبل كده")
        return added
    return 0


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


# ══════════════════════════════════════════════════════════════════════════════
# 📖 قائمة الأسعار الكاملة — مرجع احتياطي لو البحث فشل لأي سبب
# ══════════════════════════════════════════════════════════════════════════════
def render_full_price_list(st, all_labs, categories, key_prefix,
                           ss_key=None, target_list=None):
    """
    كل الـ price list بالإنجليزي جوّه expander: تصفح بالقسم، إضافة مباشرة،
    وتنزيل CSV. ده الطريق البديل لو البحث بالعربي ماجابش المطلوب.
    """
    if not all_labs:
        return 0
    added = 0
    with st.expander(f"📖 قائمة الأسعار الكاملة ({len(all_labs)} تحليل) — "
                     f"لو البحث ما جابش اللي انت عايزه", expanded=False):
        nonce_key = f"{key_prefix}__fnonce"
        st.session_state.setdefault(nonce_key, 0)
        n = st.session_state[nonce_key]

        cat = st.selectbox("القسم", ["الكل"] + list(categories),
                           key=f"{key_prefix}_fcat")
        # ⚠️ نفس درس الـ picker: مفتاح الـmultiselect لازم يتغيّر مع تغيّر القسم.
        #    من غير كده، اختيار من قسم قديم مش موجود في القسم الجديد بيرمي
        #    StreamlitAPIException ويقفل الصفحة.
        fsig = hashlib.md5(str(cat).encode("utf-8")).hexdigest()[:8]
        rows = [l for l in all_labs
                if cat == "الكل" or l.get("category") == cat]
        rows = sorted(rows, key=lambda x: (x.get("category", ""), x["name"]))
        st.caption(f"{len(rows)} تحليل" + (f" في «{cat}»" if cat != "الكل" else ""))

        # إضافة مباشرة من القائمة
        labels, by_label = [], {}
        for l in rows:
            lbl = f"{l['name']}{SEP}{l['price']} جنيه"
            if lbl not in by_label:
                by_label[lbl] = l
                labels.append(lbl)
        picked = st.multiselect("اختر من القائمة", labels,
                                key=f"{key_prefix}_fms_{fsig}_{n}")
        if st.button(f"➕ أضف المحدد ({len(picked)})" if picked else "➕ أضف المحدد",
                     key=f"{key_prefix}_fadd_{fsig}_{n}", use_container_width=True,
                     disabled=not picked):
            added = _add_many(st, ss_key, [by_label[p] for p in picked], target_list)
            st.session_state[nonce_key] += 1

        # جدول للقراءة — أسماء إنجليزية وأسعار
        html = ['<div style="max-height:420px;overflow:auto;border:1px solid #FFD9BC;'
                'border-radius:10px">',
                '<table style="width:100%;border-collapse:collapse;font-size:12.5px;'
                'direction:ltr">']
        last = None
        for l in rows:
            if l.get("category") != last:
                last = l.get("category")
                html.append(
                    f'<tr><td colspan="2" style="background:#FFF1E4;color:#B4530A;'
                    f'font-weight:800;padding:6px 10px;position:sticky;top:0">'
                    f'{_esc_html(last)}</td></tr>')
            html.append(
                f'<tr><td style="padding:5px 10px;border-top:1px solid #F3E6DA">'
                f'{_esc_html(l["name"])}</td>'
                f'<td style="padding:5px 10px;border-top:1px solid #F3E6DA;'
                f'text-align:right;white-space:nowrap;color:#FF6B00;font-weight:700">'
                f'{int(l["price"] or 0):,}</td></tr>')
        html.append("</table></div>")
        st.markdown("".join(html), unsafe_allow_html=True)

        csv = "Category,Test,Price\n" + "\n".join(
            f'"{l.get("category","")}","{l["name"]}",{int(l["price"] or 0)}' for l in rows)
        st.download_button("⬇️ تحميل القائمة CSV", csv.encode("utf-8-sig"),
                           file_name="orange_lab_price_list.csv", mime="text/csv",
                           key=f"{key_prefix}_fdl", use_container_width=True)
    return added


def _esc_html(t):
    return (str(t or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))
