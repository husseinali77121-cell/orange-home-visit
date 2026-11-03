# quick_panels.py
# ══════════════════════════════════════════════════════════════════════════════
#  ⚡ Quick Panels + 📋 خانة اللصق — منقولين من برنامج الـ Price List
#
#  الملف ده **إضافة بس**: مابيلمسش الحفظ ولا المزامنة مع GitHub ولا أي دالة في app.py.
#  بيشتغل على نفس قايمة التحاليل (list of str) اللي الفورم بيحفظها:
#       "Test Name — 400 جنيه"        ← صيغة السطر المخزّن **ما اتغيّرتش**
#  فالإجمالي (_lab_price) والتقارير والحفظ بيشتغلوا زي ما هم.
#
#  قاعدة: كل اسم تحليل في QUICK_PANELS لازم يطابق اسم موجود **مرة واحدة** في
#  labs_price_list.py. الواجهة بتعمل self-check وبتخفي أي panel اتكسر بعد تحديث
#  قايمة الأسعار وبتبلّغ بيه (نفس فكرة برنامج الأسعار).
# ══════════════════════════════════════════════════════════════════════════════

import re
import html as _html

import lab_picker as lp

CURRENCY = "جنيه"

# panel -> {"tests": [أسماء بالظبط], "bundle": اسم باقة (اختياري)}
QUICK_PANELS = {
    # ---- الأكثر طلباً في الاستقبال ----
    "🩸 CBC": {"tests": ["CBC"]},
    "🧪 Urine Examination": {"tests": ["Urine Examination"]},
    "💩 Stool Examination": {"tests": ["Stool Examination"]},
    "🔥 CRP + ESR": {"tests": ["CRP", "ESR"]},
    "🤰 Pregnancy (Serum)": {"tests": ["Pregnancy in serum Qualit."]},

    # ---- مفرّق سريع ----
    "🫀 ALT + AST": {"tests": ["ALT (SGPT)", "AST (SGOT)"]},
    "🫘 Urea + Creat": {"tests": ["Urea", "Creatinine (Serum)"]},
    "💎 Uric Acid": {"tests": ["Uric Acid"]},
    "🍬 HbA1c only": {"tests": ["HbA1C"]},
    "🦠 HBs + HCV + HIV": {"tests": ["HBs Ag", "HCV IgG", "HIV (I,II) Abs"]},

    # ---- بروفايلات ليها سعر باقة ----
    "🫀 Liver Profile": {
        "bundle": "Liver Profile",
        "tests": ["ALT (SGPT)", "AST (SGOT)", "Bilirubin Total", "Bilirubin Direct",
                  "Albumin (ALB)", "Total Protein", "Alkaline Phosphatase (ALP)",
                  "GGT (Gamma-glutamyl transferase)"],
    },
    "🫘 Kidney Profile": {
        "bundle": "Kidney Profile",
        "tests": ["Urea", "Creatinine (Serum)", "Uric Acid", "Na (Sodium)",
                  "K (Potassium)", "Calcium (Total)", "PO4 (Phosphorus)"],
    },
    "💉 Lipid Profile": {
        "bundle": "Lipid Profile",
        "tests": ["Cholesterol", "Triglycerides", "HDL", "LDL", "VLDL"],
    },
    "🦋 Thyroid Profile": {
        "bundle": "Thyroid Profile",
        "tests": ["TSH", "FT3", "FT4"],
    },

    # ---- بروفايلات من غير باقة ----
    "🍬 Diabetes (FBG+PPBG+A1c)": {"tests": ["FBG", "PPBG", "HbA1C"]},
    "🦋 TSH Only": {"tests": ["TSH"]},
    "🔩 Anemia Workup": {"tests": ["CBC", "Ferritin", "Iron (Serum)", "TIBC"]},
    "🩹 PT + PTT": {"tests": ["PT", "PTT"]},
    "❤️ Cardiac": {"tests": ["Troponin (I)", "CK (MB)", "LDH"]},

    # ---- فيتامينات ----
    "☀️ Vitamin D3": {"tests": ["Vitamin D3(25 Hydroxy Cholecal.)"]},
    "💊 Vitamin B12": {"tests": ["Vitamin B12"]},

    # ---- باقات مركّبة ----
    "🧾 Check-up أساسي": {
        "tests": ["CBC", "FBG", "ALT (SGPT)", "AST (SGOT)", "Creatinine (Serum)",
                  "Urea", "Uric Acid", "Cholesterol", "Triglycerides",
                  "Urine Examination"],
    },
    "💍 قبل الزواج": {
        "tests": ["CBC", "ABO", "Blood Rh", "HBs Ag", "HCV IgG", "HIV (I,II) Abs"],
    },
    "🏥 قبل العملية": {
        "tests": ["CBC", "PT", "PTT", "FBG", "Creatinine (Serum)",
                  "HBs Ag", "HCV IgG", "ABO", "Blood Rh"],
    },
    "🤒 حمى / التهاب": {
        "tests": ["CBC", "CRP", "ESR", "Widal Test", "Urine Examination"],
    },
    "👶 متابعة حمل": {
        "tests": ["CBC", "ABO", "Blood Rh", "FBG", "Urine Examination", "TSH"],
    },
    "🧫 مزارع": {"tests": ["Urine Culture", "Stool Culture"]},

    # ---- بانلز برنامج الزيارات القديمة (كانت بتضيف الاسم من غير سعر — دلوقتي بسعره) ----
    "🍬 Diabetes شامل": {
        "tests": ["HbA1C", "Urea", "Creatinine (Serum)", "Uric Acid", "ALT (SGPT)",
                  "AST (SGOT)", "Urine Examination"],
    },
    "❤️ Cardiac (دهون+كبد)": {
        "tests": ["Cholesterol", "HDL", "LDL", "Triglycerides", "ALT (SGPT)",
                  "AST (SGOT)", "Uric Acid"],
    },
    "🔋 Fatigue": {
        "tests": ["CBC", "Ferritin", "Vitamin D3(25 Hydroxy Cholecal.)", "TSH"],
    },
    "🧪 Kidney + Urine": {
        "tests": ["Urea", "Creatinine (Serum)", "Uric Acid", "Urine Examination"],
    },
    "🫀 Liver (5)": {
        "tests": ["ALT (SGPT)", "AST (SGOT)", "Albumin (ALB)", "Bilirubin Total",
                  "Alkaline Phosphatase (ALP)"],
    },
    "🌟 General": {
        "tests": ["CBC", "Cholesterol", "HDL", "LDL", "Triglycerides", "HbA1C", "TSH",
                  "ALT (SGPT)", "AST (SGOT)", "Urea", "Creatinine (Serum)",
                  "Urine Examination"],
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# 1) فهرس بسيط على قايمة الأسعار (ALL_LABS)
# ══════════════════════════════════════════════════════════════════════════════
def build_index(all_labs):
    """اسم مطبّع -> list من التحاليل اللي بنفس الاسم."""
    idx = {}
    for lab in (all_labs or []):
        idx.setdefault(lp.norm(lab["name"]), []).append(lab)
    return idx


def find_lab(idx, name):
    """التحليل لو الاسم موجود **مرة واحدة** بس — غير كده None (مش بنخمّن سعر)."""
    hits = idx.get(lp.norm(name), [])
    return hits[0] if len(hits) == 1 else None


def validate_panels(idx):
    """يرجّع الـ panels المكسورة بس: {panel: [الأسماء اللي مالهاش مطابقة]}."""
    broken = {}
    for panel, cfg in QUICK_PANELS.items():
        bad = [t for t in cfg["tests"] if find_lab(idx, t) is None]
        if bad:
            broken[panel] = bad
    return broken


def panel_labs(idx, panel):
    return [find_lab(idx, t) for t in QUICK_PANELS[panel]["tests"]]


def panel_bundle(idx, panel):
    """سجل الباقة الخاصة بالـ panel (لو ليه باقة وموجودة في القايمة) وإلا None."""
    name = QUICK_PANELS.get(panel, {}).get("bundle")
    return find_lab(idx, name) if name else None


# ══════════════════════════════════════════════════════════════════════════════
# 2) إضافة آمنة — حماية الدفع مرتين (نفس منطق add_many في برنامج الأسعار)
#    • مكرر         → يتخطى
#    • داخل في باقة موجودة   → يتخطى (العميل دافع تمنه في الباقة)
#    • باقة بتغطي مفرّق موجود → ما يتضافش جماعي (فيه فلوس) — يتأجل للبحث اليدوي
#      ووقتها بوابة الازدواج الموجودة في الفورم بتعرض زرار «شيل المفردات»
# ══════════════════════════════════════════════════════════════════════════════
def _bundle_components():
    return {lp.norm(k): {lp.norm(c) for c in v}
            for k, v in lp.PROFILE_COMPONENTS.items()}


def add_labs(target, labs):
    """
    يضيف labs (list من dicts: name/price) على target (list من str) بالصيغة المخزّنة.
    يرجّع dict: added / dup / covered[(name, bundle, price)] / deferred
    """
    comps = _bundle_components()
    existing = {lp.norm(lp.entry_name(e)): lp.entry_name(e) for e in target}

    # الباقات الأول عن قصد: لو القايمة فيها باقة ومكوّن منها، المكوّن يتمسك كـ covered
    seen, uniq = set(), []
    for lab in sorted([l for l in labs if l], key=lambda l: lp.norm(l["name"]) not in comps):
        k = lp.norm(lab["name"])
        if k in seen:
            continue
        seen.add(k)
        uniq.append(lab)

    res = {"added": [], "dup": [], "covered": [], "deferred": []}
    for lab in uniq:
        k = lp.norm(lab["name"])
        if k in existing:
            res["dup"].append(lab["name"])
            continue
        if k in comps:                                   # باقة
            if any(c in existing for c in comps[k]):
                res["deferred"].append(lab["name"])
                continue
        else:                                            # مفرّق
            parent = next((b for b, cs in comps.items() if k in cs and b in existing), None)
            if parent:
                res["covered"].append((lab["name"], existing[parent], int(lab.get("price") or 0)))
                continue
        target.append(lp.format_entry(lab["name"], lab["price"]))
        existing[k] = lab["name"]
        res["added"].append(lab["name"])
    return res


def result_messages(label, res):
    """نتيجة add_labs -> list من (نوع الرسالة, النص)."""
    out = []
    if res["added"]:
        out.append(("success", f"تمت إضافة {len(res['added'])} تحليل من {label}"))
    if res["dup"]:
        out.append(("warning", f"موجودين قبل كده: {', '.join(res['dup'])}"))
    if res["covered"]:
        saved = sum(p for _, _, p in res["covered"])
        out.append(("warning",
                    f"⛔ اتخطّى {', '.join(n for n, _, _ in res['covered'])} — "
                    f"داخلين في باقة {res['covered'][0][1]} الموجودة. "
                    f"وفّرت على العميل {saved:,} {CURRENCY}"))
    if res["deferred"]:
        out.append(("warning",
                    f"📦 {', '.join(res['deferred'])} ما اتضافتش — بتغطي تحاليل مفرّقة "
                    f"موجودة. ضيفها من خانة «🔎 إضافة تحليل» وهيظهر زرار «شيل المفردات»"))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# 3) تحليل النص الملزوق (رسالة أسعار / قايمة تحاليل)
# ══════════════════════════════════════════════════════════════════════════════
MAX_LINES = 60

_CUR = r"(?:جنيه|جنية|ج\.?\s?م|ج|egp|le|l\.e\.?|pounds?)"
# سعر في آخر القطعة: بعد شرطة/نقطتين، أو متبوع بكلمة عملة.
# الشرطة لازم يكون جنبها مسافة (قبلها أو بعدها): "CBC - 400" و "Hba1c- 400" بيتقصّوا،
# لكن "CA 15-3" و "17-OH progesterone" ماتتقصّش.
_PRICE_TAIL = re.compile(
    rf"(?:\s+[—–-]\s*|[—–-]\s+|\s*[:=]\s*)\d[\d,\.]*(?:\s*{_CUR})?\s*$"
    rf"|\s+\d[\d,\.]*\s*{_CUR}\s*$",
    re.I)
# سطر كله رقم / رقم + عملة
_ONLY_NUMBER = re.compile(rf"^[\d٠-٩\s.,]+(?:{_CUR})?$", re.I)
# ترقيم أول السطر: "1." "1)" "1-" (بمسافة بعد الشرطة) "١:" — مش "17-OH"
_NUMBERING = re.compile(r"^[\d٠-٩]{1,3}(?:\s*[).:،]\s*|\s*[—–-]\s+)")
# أسطر الهيدر في رسالة أسعار — بتتخطى
_HEADER_LINE = re.compile(
    r"^(?:الاسم|اسم|الطبيب|الدكتور|دكتور|التاريخ|معمل|الموعد|التليفون|الهاتف|العنوان|الفرع|"
    r"patient|doctor|date|name)\b\s*[:：]?|^معمل\b|orange\b|^أهلا|^اهلا",
    re.I)
# أول سطر من «الفوتر» (إجماليات / تعليمات) — من هنا ورا مفيش تحاليل
_STOP_LINE = re.compile(
    r"^(?:الإجمالي|الاجمالي|إجمالي|اجمالي|المطلوب|السعر|بدل|الخصم|النتيجة خلال|تعليمات|"
    r"شكرا|شكراً|subtotal|discount|total\s*[:=]|ملاحظات)\b", re.I)


def _balance_trim(s):
    """يشيل علامات الترقيم من الأطراف، ويسيب الأقواس لو متزنة (Vitamin D3(25 ...))."""
    s = s.strip(" \t:-–—•*.،؛?؟\"'")
    while s.endswith(")") and s.count(")") > s.count("("):
        s = s[:-1].rstrip(" \t:-–—•*.،؛?؟\"'")
    while s.startswith("(") and s.count("(") > s.count(")"):
        s = s[1:].lstrip(" \t:-–—•*.،؛?؟\"'")
    return s.strip()


def _clean_piece(s):
    s = _PRICE_TAIL.sub("", s.strip())
    s = _balance_trim(s)
    if len(s) < 2 or _ONLY_NUMBER.match(s):
        return ""
    if not re.search(r"[a-zA-Z\u0600-\u06FF]", s):
        return ""
    return s


def parse_paste(raw, all_labs=None, limit=MAX_LINES):
    """
    نص ملزوق -> list أسماء مرشّحة (من غير ترقيم ولا أسعار ولا هيدر/فوتر رسالة).
    مش بيطابق ولا بيخمّن — ده شغل resolve_lab. all_labs اختياري: بيستخدمه بس
    علشان «A/G Ratio» ماتتقسمش على الشرطة المائلة.
    """
    if not raw or not str(raw).strip():
        return []
    out, seen = [], set()

    def _push(piece):
        """يرجّع True بس لما نوصل للحد الأقصى (عشان نوقف القراءة)."""
        c = _clean_piece(piece)
        k = lp.norm(c) if c else ""
        if not k or k in seen:
            return False
        seen.add(k)
        out.append(c)
        return len(out) >= limit

    for line in str(raw).splitlines():
        line = line.strip()
        if not line:
            continue
        line = re.sub(r"^[\W_]+", "", line)               # إيموجي / نجمة / شرطة / بولت
        line = _NUMBERING.sub("", line).strip()
        line = re.sub(r"^[\W_]+", "", line)
        if not line:
            continue
        if _STOP_LINE.match(line):
            break
        if _HEADER_LINE.match(line):
            continue
        line = re.sub(r"(?<=\d),(?=\d{3}\b)", "", line)   # 1,200 -> 1200 قبل التقسيم
        for chunk in re.split(r"[,،؛;|+]+|\s/\s", line):
            chunk = chunk.strip()
            if not chunk:
                continue
            parts = [chunk]
            if "/" in chunk:
                whole = _PRICE_TAIL.sub("", chunk).strip()
                keep_whole = False
                if all_labs:
                    r = lp.resolve_lab(all_labs, whole)
                    keep_whole = r["status"] in (lp.EXACT, lp.ALIAS)
                if not keep_whole:
                    parts = [p for p in chunk.split("/") if p.strip()]
            for p in parts:
                if _push(p):
                    return out
    return out


def resolve_tokens(all_labs, tokens):
    """
    confident: [(token, lab)]            ← مؤكدة (مطابقة تامة / اختصار معروف)
    choose:    [(token, cands, reason)]  ← محتاجة اختيار منك
    missing:   [token]                   ← مش موجودة
    """
    confident, choose, missing = [], [], []
    for t in tokens:
        r = lp.resolve_lab(all_labs, t)
        if r["status"] in (lp.EXACT, lp.ALIAS) and r["cands"]:
            confident.append((t, r["cands"][0]))
        elif r["cands"]:
            choose.append((t, r["cands"][:6], r["reason"]))
        else:
            missing.append(t)
    return confident, choose, missing


# ══════════════════════════════════════════════════════════════════════════════
# 4) واجهة Streamlit
# ══════════════════════════════════════════════════════════════════════════════
def _target(st, ss_key, target_list):
    return target_list if target_list is not None else st.session_state[ss_key]


def _flash(st, key, msgs):
    st.session_state.setdefault(key, []).extend(msgs)


def _show_flash(st, key):
    for kind, text in st.session_state.pop(key, []) or []:
        {"success": st.success, "warning": st.warning,
         "info": st.info, "error": st.error}.get(kind, st.info)(text)


def render_quick_panels(st, all_labs, key_prefix, ss_key=None, target_list=None, cols=2):
    """
    ⚡ الإدخال السريع — زرار لكل panel بيضيف تحاليله **بأسعارها** من قايمة الأسعار.
    لو الـ panel ليه باقة أرخص من المفرّق: بيسألك باقة ولا مفرّق (زي برنامج الأسعار).
    """
    if not all_labs:
        st.warning("قائمة الأسعار غير متاحة حالياً")
        return
    idx = build_index(all_labs)
    broken = validate_panels(idx)
    flash_key = f"{key_prefix}__pnl_flash"
    pend_key = f"{key_prefix}__pnl_pending"

    if broken:
        st.error(f"⛔ {len(broken)} panel مكسور — أسماء مش موجودة في قائمة الأسعار "
                 f"({'، '.join(broken)}) — اتخفوا لحد ما قايمة الأسعار تتظبط")

    _show_flash(st, flash_key)
    names = [p for p in QUICK_PANELS if p not in broken]
    for row in range(0, len(names), cols):
        cs = st.columns(cols)
        for j, p in enumerate(names[row:row + cols]):
            with cs[j]:
                if st.button(p, use_container_width=True, key=f"{key_prefix}__pnl_{row + j}"):
                    labs = panel_labs(idx, p)
                    bundle = panel_bundle(idx, p)
                    itemized = sum(int(l["price"] or 0) for l in labs)
                    if bundle and int(bundle["price"] or 0) <= itemized:
                        st.session_state[pend_key] = p
                    else:
                        _flash(st, flash_key,
                               result_messages(p, add_labs(_target(st, ss_key, target_list), labs)))
                    st.rerun()

    # ── باقة ولا مفرّق؟ ──
    pend = st.session_state.get(pend_key)
    if pend in QUICK_PANELS and pend not in broken:
        labs = panel_labs(idx, pend)
        bundle = panel_bundle(idx, pend)
        if bundle:
            itemized = sum(int(l["price"] or 0) for l in labs)
            saving = itemized - int(bundle["price"] or 0)
            st.info(f"**{pend}** — الباقة أوفر")
            b1, b2, b3 = st.columns([2, 2, 1])
            with b1:
                lbl = (f"📦 باقة: {int(bundle['price']):,} {CURRENCY}"
                       + (f"  (توفير {saving:,})" if saving > 0 else ""))
                if st.button(lbl, use_container_width=True, type="primary",
                             key=f"{key_prefix}__pnl_bundle"):
                    _flash(st, flash_key,
                           result_messages(pend, add_labs(_target(st, ss_key, target_list), [bundle])))
                    st.session_state[pend_key] = None
                    st.rerun()
            with b2:
                if st.button(f"🔬 مفرّق: {itemized:,} {CURRENCY}", use_container_width=True,
                             key=f"{key_prefix}__pnl_split"):
                    _flash(st, flash_key,
                           result_messages(pend, add_labs(_target(st, ss_key, target_list), labs)))
                    st.session_state[pend_key] = None
                    st.rerun()
            with b3:
                if st.button("إلغاء", use_container_width=True, key=f"{key_prefix}__pnl_cancel"):
                    st.session_state[pend_key] = None
                    st.rerun()

    with st.expander("👁️ شاهد محتوى الـ Panels"):
        for p in names:
            labs = panel_labs(idx, p)
            bundle = panel_bundle(idx, p)
            tail = f" — 📦 باقة {int(bundle['price']):,} {CURRENCY}" if bundle else ""
            st.markdown(
                f'<div style="font-size:12px;margin-bottom:6px"><b style="color:#FF6B00">'
                f'{_html.escape(p)}</b> — {_html.escape(" • ".join(l["name"] for l in labs))}'
                f'{_html.escape(tail)}</div>', unsafe_allow_html=True)


def render_paste_box(st, all_labs, key_prefix, ss_key=None, target_list=None):
    """
    📋 الصق قائمة تحاليل (رسالة أسعار / رسالة عميل) — البرنامج بيقراها ويضيفها تلقائياً
    بأسعارها. المؤكد بيتحدد لوحده (تقدر تشيل علامة أي حاجة)، وغير المؤكد بتختاره منك،
    ومش الموجود بيتعرض عشان تضيفه يدوي. مفيش حاجة بتتضاف من غير ما تدوس «أضف المختار».
    """
    if not all_labs:
        return
    state_key = f"{key_prefix}__bulk"
    flash_key = f"{key_prefix}__bulk_flash"
    BULK = st.session_state.get(state_key)

    with st.expander("📋 الصق قائمة تحاليل (رسالة أسعار / رسالة عميل)", expanded=bool(BULK)):
        _show_flash(st, flash_key)
        with st.form(f"{key_prefix}__bulk_form", clear_on_submit=True):
            raw = st.text_area(
                "الصق النص هنا", height=130, label_visibility="collapsed",
                key=f"{key_prefix}__bulk_raw",
                placeholder="الصق الرسالة زي ما هي — عربي أو إنجليزي:\n"
                            "CBC\nHba1c\nسكر صائم\nفيتامين د، كرياتينين\nTSH + Ferritin")
            go = st.form_submit_button("🔍 اقرأ القائمة", use_container_width=True)

        if go:
            toks = parse_paste(raw, all_labs)
            if not toks:
                _flash(st, flash_key, [("warning", "مفيش أي سطر صالح في النص ده")])
                st.session_state[state_key] = None
            else:
                conf, choose, missing = resolve_tokens(all_labs, toks)
                n = (BULK or {}).get("n", 0) + 1       # يفصل مفاتيح الـ widgets بين قراءة وأخرى
                st.session_state[state_key] = {"confident": conf, "choose": choose,
                                               "missing": missing, "n": n}
            st.rerun()

        if BULK:
            n = BULK.get("n", 0)
            st.caption(f"مؤكد {len(BULK['confident'])}  ·  محتاج اختيار {len(BULK['choose'])}"
                       f"  ·  مش متعرف عليه {len(BULK['missing'])}")
            chosen = []

            if BULK["confident"]:
                st.markdown("**✅ اتعرف عليها — شيل علامة أي حاجة مش عايزها**")
                for i, (t, lab) in enumerate(BULK["confident"]):
                    lbl = f"{lab['name']} — {int(lab['price']):,} {CURRENCY}"
                    if lp.norm(t) != lp.norm(lab["name"]):
                        lbl += f"   ‹ {t}"
                    if st.checkbox(lbl, value=True, key=f"{key_prefix}__bk_ok_{n}_{i}"):
                        chosen.append(lab)

            if BULK["choose"]:
                st.markdown("**🔎 محتاجة تحديد منك**")
                for i, (t, cands, why) in enumerate(BULK["choose"]):
                    opts = ["— تجاهل —"] + [f"{c['name']} · {int(c['price']):,}" for c in cands]
                    pick = st.selectbox(f"«{t}» — {why}", opts, key=f"{key_prefix}__bk_pick_{n}_{i}")
                    if pick != opts[0] and pick in opts:
                        chosen.append(cands[opts.index(pick) - 1])

            if BULK["missing"]:
                st.markdown("**⛔ مش لاقيلها مقابل — ضيفها يدوي من خانة «🔎 إضافة تحليل»**")
                st.code("\n".join(BULK["missing"]), language=None)

            g1, g2 = st.columns(2)
            with g1:
                if st.button(f"➕ أضف المختار ({len(chosen)})", use_container_width=True,
                             type="primary", disabled=not chosen, key=f"{key_prefix}__bk_add_{n}"):
                    res = add_labs(_target(st, ss_key, target_list), chosen)
                    _flash(st, flash_key, result_messages("القائمة الملزوقة", res))
                    st.session_state[state_key] = None
                    st.rerun()
            with g2:
                if st.button("🗑️ امسح القائمة", use_container_width=True,
                             key=f"{key_prefix}__bk_clr_{n}"):
                    st.session_state[state_key] = None
                    st.rerun()
