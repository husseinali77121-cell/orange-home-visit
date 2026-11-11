# -*- coding: utf-8 -*-
"""
pdf_export.py — تصدير الزيارات المنزلية PDF
═══════════════════════════════════════════════════════════════════════════════
• A4 بالعرض، **ملء كامل للصفحة من غير أي حواف** (أول بلوك لازق في الحافة العليا
  وآخر بلوك لازق في الحافة السفلى، والجداول من الحافة اليمين للشمال).
• نفس محتوى ملف Excel ونفس أرقامه: نفس الأعمدة، صف «الإجمالي الكلي» (مجموع كل
  الصفوف زي SUM في إكسيل)، ملخص الأطباء (من غير الملغية، بدل 5%)، والتوقيع.
• حجم الخط بيتظبط لوحده: أكبر خط يدخّل الزيارات في أقل عدد صفحات، والصفوف
  بتتمط عشان تملا الصفحة لآخرها. لو أكتر من صفحة: الصفوف بتتوزّع بالتساوي،
  والعنوان وصف رؤوس الأعمدة بيتكرروا في كل صفحة.

مفيش أي اعتماد على Streamlit هنا — دالة نقية: list of dicts → bytes.

العربي: reportlab مابيعملش تشكيل حروف ولا اتجاه نص، فالموديول ده فيه:
  ① shape_ar  — توصيل الحروف (أشكال الحرف أول/وسط/آخر/منفصل + لام ألف)
  ② _visual   — ترتيب العرض من اليمين للشمال (نسخة مختصرة من خوارزمية Unicode
                Bidi) عشان الأرقام والإنجليزي جوّه الكلام العربي يتعرضوا صح.
من غير أي مكتبة إضافية غير reportlab.

الخط: fonts/DejaVuSansCondensed*.ttf (مرفق مع البرنامج، رخصة حرّة — LICENSE-DejaVu.txt).
لو حطيت Cairo-Regular.ttf + Cairo-Bold.ttf في فولدر fonts/ هيتستخدموا بدله
بشرط إنهم فيهم أشكال الحروف العربية (Presentation Forms) — غير كده بيتجاهلوا.
"""
import io
import os
import re
import unicodedata as _ud

# ══════════════════════════════════════════════════════════════════════════════
# ① تشكيل الحروف العربية
# ══════════════════════════════════════════════════════════════════════════════
# الحرف: (منفصل, آخر, أول, وسط) — None = الشكل ده مش موجود للحرف
_FORMS = {
    "ء": (0xFE80, None, None, None),       # ء
    "آ": (0xFE81, 0xFE82, None, None),     # آ
    "أ": (0xFE83, 0xFE84, None, None),     # أ
    "ؤ": (0xFE85, 0xFE86, None, None),     # ؤ
    "إ": (0xFE87, 0xFE88, None, None),     # إ
    "ئ": (0xFE89, 0xFE8A, 0xFE8B, 0xFE8C), # ئ
    "ا": (0xFE8D, 0xFE8E, None, None),     # ا
    "ب": (0xFE8F, 0xFE90, 0xFE91, 0xFE92), # ب
    "ة": (0xFE93, 0xFE94, None, None),     # ة
    "ت": (0xFE95, 0xFE96, 0xFE97, 0xFE98), # ت
    "ث": (0xFE99, 0xFE9A, 0xFE9B, 0xFE9C), # ث
    "ج": (0xFE9D, 0xFE9E, 0xFE9F, 0xFEA0), # ج
    "ح": (0xFEA1, 0xFEA2, 0xFEA3, 0xFEA4), # ح
    "خ": (0xFEA5, 0xFEA6, 0xFEA7, 0xFEA8), # خ
    "د": (0xFEA9, 0xFEAA, None, None),     # د
    "ذ": (0xFEAB, 0xFEAC, None, None),     # ذ
    "ر": (0xFEAD, 0xFEAE, None, None),     # ر
    "ز": (0xFEAF, 0xFEB0, None, None),     # ز
    "س": (0xFEB1, 0xFEB2, 0xFEB3, 0xFEB4), # س
    "ش": (0xFEB5, 0xFEB6, 0xFEB7, 0xFEB8), # ش
    "ص": (0xFEB9, 0xFEBA, 0xFEBB, 0xFEBC), # ص
    "ض": (0xFEBD, 0xFEBE, 0xFEBF, 0xFEC0), # ض
    "ط": (0xFEC1, 0xFEC2, 0xFEC3, 0xFEC4), # ط
    "ظ": (0xFEC5, 0xFEC6, 0xFEC7, 0xFEC8), # ظ
    "ع": (0xFEC9, 0xFECA, 0xFECB, 0xFECC), # ع
    "غ": (0xFECD, 0xFECE, 0xFECF, 0xFED0), # غ
    "ف": (0xFED1, 0xFED2, 0xFED3, 0xFED4), # ف
    "ق": (0xFED5, 0xFED6, 0xFED7, 0xFED8), # ق
    "ك": (0xFED9, 0xFEDA, 0xFEDB, 0xFEDC), # ك
    "ل": (0xFEDD, 0xFEDE, 0xFEDF, 0xFEE0), # ل
    "م": (0xFEE1, 0xFEE2, 0xFEE3, 0xFEE4), # م
    "ن": (0xFEE5, 0xFEE6, 0xFEE7, 0xFEE8), # ن
    "ه": (0xFEE9, 0xFEEA, 0xFEEB, 0xFEEC), # ه
    "و": (0xFEED, 0xFEEE, None, None),     # و
    "ى": (0xFEEF, 0xFEF0, None, None),     # ى
    "ي": (0xFEF1, 0xFEF2, 0xFEF3, 0xFEF4), # ي
    "پ": (0xFB56, 0xFB57, 0xFB58, 0xFB59), # پ
    "چ": (0xFB7A, 0xFB7B, 0xFB7C, 0xFB7D), # چ
    "ژ": (0xFB8A, 0xFB8B, None, None),     # ژ
    "ک": (0xFB8E, 0xFB8F, 0xFB90, 0xFB91), # ک
    "گ": (0xFB92, 0xFB93, 0xFB94, 0xFB95), # گ
    "ی": (0xFBFC, 0xFBFD, 0xFBFE, 0xFBFF), # ی
}
# لام + ألف → حرف واحد (منفصل, آخر)
_LAM_ALEF = {"آ": (0xFEF5, 0xFEF6), "أ": (0xFEF7, 0xFEF8),
             "إ": (0xFEF9, 0xFEFA), "ا": (0xFEFB, 0xFEFC)}
_TATWEEL = "ـ"
_HARAKAT = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭ]")


def _joins_next(ch):
    """الحرف ده بيتوصّل باللي بعده؟"""
    return ch == _TATWEEL or (ch in _FORMS and _FORMS[ch][2] is not None)


def _joins_prev(ch):
    """الحرف ده بيقبل يتوصّل باللي قبله؟"""
    return ch == _TATWEEL or (ch in _FORMS and _FORMS[ch][1] is not None)


def shape_ar(text):
    """نص منطقي → نفس الترتيب بس بأشكال الحروف الموصّلة (التشكيل بيتشال)."""
    s = _HARAKAT.sub("", str(text or ""))
    out, i, n = [], 0, len(s)
    while i < n:
        c = s[i]
        if c not in _FORMS:
            out.append(c); i += 1
            continue
        prev = s[i - 1] if i > 0 else ""
        jp = bool(prev) and _joins_next(prev) and _joins_prev(c)
        nxt = s[i + 1] if i + 1 < n else ""
        if c == "ل" and nxt in _LAM_ALEF:
            iso, fin = _LAM_ALEF[nxt]
            out.append(chr(fin if jp else iso)); i += 2
            continue
        jn = bool(nxt) and _joins_next(c) and _joins_prev(nxt)
        iso, fin, ini, med = _FORMS[c]
        out.append(chr(med if (jp and jn) else fin if jp else ini if jn else iso))
        i += 1
    return "".join(out)


# ══════════════════════════════════════════════════════════════════════════════
# ② ترتيب العرض (اتجاه الفقرة من أول حرف قوي، من غير تضمينات صريحة)
# ══════════════════════════════════════════════════════════════════════════════
_MIRROR = {"(": ")", ")": "(", "[": "]", "]": "[", "{": "}", "}": "{",
           "<": ">", ">": "<", "«": "»", "»": "«"}
_NEUTRAL_IN = {"B", "S", "WS", "ON", "BN", "LRE", "RLE", "PDF", "LRO", "RLO",
               "LRI", "RLI", "FSI", "PDI"}


_LEVEL_CACHE = {}


def _levels(text):
    """
    مستويات الاتجاه لفقرة كاملة (خوارزمية Unicode Bidi مختصرة: P2–P3, W1–W7, N1–N2, I1–I2).
    اتجاه الفقرة من أول حرف قوي فيها (زي «تلقائي» في Word/Excel): سطر تحاليل بيبدأ
    بإنجليزي = شمال→يمين، عنوان بيبدأ بعربي = يمين→شمال. من غير حروف خالص
    (تليفون/تاريخ) = شمال→يمين. Returns (base_level, [level per char]).
    """
    hit = _LEVEL_CACHE.get(text)
    if hit is not None:
        return hit
    n = len(text)
    t = [(_ud.bidirectional(c) or "ON") for c in text]
    t = ["ON" if x in _NEUTRAL_IN else x for x in t]
    base = 0
    for x in t:                                              # P2 / P3
        if x == "L":
            base = 0; break
        if x in ("R", "AL"):
            base = 1; break
    e = "L" if base == 0 else "R"
    prev = e                                                 # W1
    for i in range(n):
        if t[i] == "NSM":
            t[i] = prev
        prev = t[i]
    last = e                                                 # W2
    for i in range(n):
        if t[i] in ("L", "R", "AL"):
            last = t[i]
        elif t[i] == "EN" and last == "AL":
            t[i] = "AN"
    t = ["R" if x == "AL" else x for x in t]                 # W3
    for i in range(1, n - 1):                                # W4
        if t[i] == "ES" and t[i - 1] == "EN" and t[i + 1] == "EN":
            t[i] = "EN"
        elif t[i] == "CS" and t[i - 1] == t[i + 1] and t[i - 1] in ("EN", "AN"):
            t[i] = t[i - 1]
    i = 0                                                    # W5
    while i < n:
        if t[i] == "ET":
            j = i
            while j < n and t[j] == "ET":
                j += 1
            if (i > 0 and t[i - 1] == "EN") or (j < n and t[j] == "EN"):
                for k in range(i, j):
                    t[k] = "EN"
            i = j
        else:
            i += 1
    t = ["ON" if x in ("ES", "ET", "CS") else x for x in t]  # W6
    last = e                                                 # W7
    for i in range(n):
        if t[i] in ("L", "R"):
            last = t[i]
        elif t[i] == "EN" and last == "L":
            t[i] = "L"

    def _strong(x):
        return "L" if x == "L" else ("R" if x in ("R", "EN", "AN") else None)

    i = 0                                                    # N1 / N2
    while i < n:
        if _strong(t[i]) is None:
            j = i
            while j < n and _strong(t[j]) is None:
                j += 1
            before = _strong(t[i - 1]) if i > 0 else e
            after = _strong(t[j]) if j < n else e
            d = before if before == after else e
            for k in range(i, j):
                t[k] = d
            i = j
        else:
            i += 1
    if base == 0:                                            # I1
        lv = [0 if x == "L" else (1 if x == "R" else 2) for x in t]
    else:                                                    # I2
        lv = [1 if x == "R" else 2 for x in t]
    out = (base, lv)
    if len(_LEVEL_CACHE) < 50000:
        _LEVEL_CACHE[text] = out
    return out


def _reorder(chars, lv, base):
    """L1 (مسافات آخر السطر = مستوى الفقرة) + L2 (عكس الكتل) + L4 (عكس الأقواس)."""
    chars, lv = list(chars), list(lv)
    k = len(chars) - 1
    while k >= 0 and chars[k] in (" ", _NBSP):
        lv[k] = base; k -= 1
    if not chars:
        return ""
    for i, c in enumerate(chars):
        if lv[i] % 2 == 1 and c in _MIRROR:
            chars[i] = _MIRROR[c]
    top = max(lv)
    low = min([x for x in lv if x % 2 == 1] or [top + 1])
    for level in range(top, low - 1, -1):
        i, n = 0, len(chars)
        while i < n:
            if lv[i] >= level:
                j = i
                while j < n and lv[j] >= level:
                    j += 1
                chars[i:j] = chars[i:j][::-1]
                lv[i:j] = lv[i:j][::-1]
                i = j
            else:
                i += 1
    return "".join(chars)


def _visual_span(para, start, end):
    """سطر = جزء من فقرة: المستويات محسوبة على الفقرة كلها (عشان قوس أو فاصل في آخر
    السطر ياخد اتجاه الكلام اللي بعده مش اتجاه نهاية السطر)."""
    base, lv = _levels(para)
    return _reorder(para[start:end].replace(_NBSP, " "), lv[start:end], base)


def _visual(line):
    """سطر لوحده → ترتيب الرسم من الشمال لليمين."""
    return _visual_span(line, 0, len(line))


# ══════════════════════════════════════════════════════════════════════════════
# ③ الخطوط
# ══════════════════════════════════════════════════════════════════════════════
_HERE = os.path.dirname(os.path.abspath(__file__))
_FONT_DIRS = [os.path.join(_HERE, "fonts"), "/usr/share/fonts/truetype/dejavu",
              "/usr/share/fonts/dejavu", "/usr/share/fonts/TTF"]
_FONT_CANDIDATES = [
    ("Cairo-Regular.ttf", "Cairo-Bold.ttf"),
    ("DejaVuSansCondensed.ttf", "DejaVuSansCondensed-Bold.ttf"),
    ("DejaVuSans.ttf", "DejaVuSans-Bold.ttf"),
]
_NEEDED_GLYPHS = (0xFEFB, 0xFE8E, 0xFEDF, 0xFEE4, 0x0661, 0x0031)
_FONTS = {}
LAST_INFO = {}          # آخر تصدير: حجم الخط وعدد الصفحات (للاختبارات)


def _find(fname):
    for d in _FONT_DIRS:
        p = os.path.join(d, fname)
        if os.path.exists(p):
            return p
    return None


def _fonts():
    """(regular, bold, cmap) — بيتسجّلوا في reportlab مرة واحدة."""
    if _FONTS:
        return _FONTS["r"], _FONTS["b"], _FONTS["cmap"]
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    for reg, bold in _FONT_CANDIDATES:
        pr, pb = _find(reg), _find(bold)
        if not pr:
            continue
        try:
            fr = TTFont("HV-R", pr)
            cmap = set(fr.face.charToGlyph.keys())
            if not all(g in cmap for g in _NEEDED_GLYPHS):
                continue
            fb = TTFont("HV-B", pb) if pb else TTFont("HV-B", pr)
            pdfmetrics.registerFont(fr)
            pdfmetrics.registerFont(fb)
            _FONTS.update(r="HV-R", b="HV-B", cmap=cmap, path=pr)
            return _FONTS["r"], _FONTS["b"], _FONTS["cmap"]
        except Exception:
            continue
    raise RuntimeError("مفيش خط عربي — حط DejaVuSansCondensed.ttf في فولدر fonts/")


# ══════════════════════════════════════════════════════════════════════════════
# ④ النص داخل الخلية: تشكيل → لفّ سطور → ترتيب عرض
# ══════════════════════════════════════════════════════════════════════════════
_W_CACHE = {}


def _sw(s, font, size):
    from reportlab.pdfbase.pdfmetrics import stringWidth
    k = (s, font, size)
    w = _W_CACHE.get(k)
    if w is None:
        w = stringWidth(s, font, size)
        if len(_W_CACHE) < 200000:
            _W_CACHE[k] = w
    return w


def _prep(text, cmap):
    """تشكيل + شيل أي رمز مش موجود في الخط (إيموجي مثلًا) + توحيد المسافات."""
    s = shape_ar(str(text if text is not None else ""))
    s = "".join(ch for ch in s if ch == "\n" or ord(ch) in cmap)
    return [re.sub(r"[ \t]+", " ", p).strip() for p in s.split("\n")]


def _wrap(paragraphs, font, size, max_w):
    """
    لفّ كلمات بالترتيب المنطقي. Returns [(فقرة, بداية, نهاية)] — كل سطر حتة من
    فقرته (عشان الاتجاه يتحسب على الفقرة كلها). وحدة non-breaking أعرض من الخلية
    بتتفك كلمات، وكلمة أعرض من الخلية بتتكسر حروف.
    """
    out = []
    sp = _sw(" ", font, size)
    for para in paragraphs:
        if not para:
            continue
        toks = []                                # (start, end)
        for m in re.finditer(r"[^ ]+", para):
            a, b = m.start(), m.end()
            if _NBSP in para[a:b] and _sw(para[a:b], font, size) > max_w:
                for m2 in re.finditer("[^" + _NBSP + "]+", para[a:b]):
                    toks.append((a + m2.start(), a + m2.end()))
            else:
                toks.append((a, b))
        cur_s = cur_e = None
        cur_w = 0.0
        for a, b in toks:
            ww = _sw(para[a:b], font, size)
            if ww > max_w:                       # كلمة مستحيل تدخل → كسر حروف
                if cur_s is not None:
                    out.append((para, cur_s, cur_e)); cur_s = None
                ps = a
                for k in range(a + 1, b + 1):
                    if _sw(para[ps:k], font, size) > max_w and k - 1 > ps:
                        out.append((para, ps, k - 1)); ps = k - 1
                cur_s, cur_e, cur_w = ps, b, _sw(para[ps:b], font, size)
                continue
            if cur_s is None:
                cur_s, cur_e, cur_w = a, b, ww
            elif cur_w + sp + ww > max_w:
                out.append((para, cur_s, cur_e))
                cur_s, cur_e, cur_w = a, b, ww
            else:
                cur_e, cur_w = b, cur_w + sp + ww
        if cur_s is not None:
            out.append((para, cur_s, cur_e))
    return out


# ══════════════════════════════════════════════════════════════════════════════
# ⑤ التنسيق
# ══════════════════════════════════════════════════════════════════════════════
ORANGE, ORANGE_LIGHT, DARK, WHITE = "#FF6B00", "#FFF3E8", "#2C3E50", "#FFFFFF"
BORDER_C = "#FFBB80"
STATUS_FILL = {"تمت": "#D5F5E3", "ملغية": "#FADBD8", "في الطريق": "#FEF9E7", "مجدولة": "#D6EAF8"}

# أعمدة الجدول الأساسي بترتيب العرض من **اليمين** للشمال (زي ملف إكسيل المطبوع).
# الرقم = وزن العرض للأعمدة النصية. الأعمدة الثابتة (FIXED_KEYS) عرضها = أطول قيمة
# فيها بالظبط (تليفون/تاريخ/سعر مايتكسروش على سطرين) والباقي بيتوزّع بالأوزان.
MAIN_COLS = [
    ("name", "الاسم", 16), ("phone", "التليفون", 0), ("visit_date", "تاريخ الزيارة", 0),
    ("doctor_name", "الدكتور", 9), ("address", "العنوان", 26),
    ("extra_persons_text", "حالات إضافية", 19), ("selected_labs_text", "التحاليل", 32),
    ("labs_price_before", "السعر قبل الخصم", 0), ("labs_price_after", "السعر بعد الخصم", 0),
    ("transport_fee", "بدل الانتقال", 0), ("total_price", "الإجمالي", 0), ("status", "الحالة", 0),
]
PRICE_KEYS = {"labs_price_before", "labs_price_after", "transport_fee", "total_price"}
FIXED_KEYS = PRICE_KEYS | {"phone", "visit_date", "status"}
LEFT_TEXT = {"name", "address", "extra_persons_text", "selected_labs_text", "doctor_name"}
DOC_COLS = [("م", 4), ("اسم الدكتور", 20), ("عدد الزيارات", 12), ("إجمالي بعد الخصم", 17),
            ("بدل الزيارة (5%)", 16), ("بدل الانتقال", 15), ("الإجمالي", 16)]


_LH, _PAD = 1.17, 0.28       # ارتفاع السطر ÷ حجم الخط · الهامش جوّه الخلية ÷ حجم الخط


def _num(v):
    try:
        if v is None or v == "":
            return 0.0
        f = float(v)
        return 0.0 if f != f else f            # NaN → 0
    except Exception:
        return 0.0


def money(v, decimals=False):
    """53630 → «53,630 ج» · 5236.5 → «5,236.5 ج» (نفس شكل إكسيل)."""
    f = _num(v)
    if decimals and abs(f - round(f)) > 1e-9:
        s = f"{f:,.2f}".rstrip("0").rstrip(".")
    else:
        s = f"{round(f):,.0f}"
    return f"{s} ج"


def _txt(v):
    if v is None:
        return ""
    try:
        if isinstance(v, float) and v != v:
            return ""
    except Exception:
        pass
    return str(v)


# ══════════════════════════════════════════════════════════════════════════════
# ⑥ البلوكات (صفوف) — كل بلوك: خلايا بتمتد على أعمدة شبكة
# ══════════════════════════════════════════════════════════════════════════════
class _Row:
    __slots__ = ("grid", "cells", "fill", "kind", "h", "stretch", "lines", "size")

    def __init__(self, grid, cells, fill, kind, stretch=False):
        self.grid = grid          # "main" | "doc" | "full"
        self.cells = cells        # [(c0, c1, text, style)] — c0..c1 شاملين
        self.fill = fill
        self.kind = kind
        self.stretch = stretch
        self.h = 0.0
        self.lines = []
        self.size = 0.0


def _style(size, bold=False, color="#222222", align="c", fill=None):
    return {"size": size, "bold": bold, "color": color, "align": align, "fill": fill}


# سعر كل تحليل جوّه مربع التحاليل والحالات الإضافية: False = أسماء التحاليل بس
# (زي رسايل الواتساب) — الأسعار موجودة في أعمدة الحسابات. True يرجّع «CBC — 400 جنيه».
SHOW_ITEM_PRICES = False
_ITEM_PRICE = re.compile(r"\s*[—–-]\s*\d[\d,٬\.]{1,}\s*(?:جنيه|ج\.?م?|EGP|LE)?\s*$")


def _item(x):
    x = x.strip()
    return x if SHOW_ITEM_PRICES else (_ITEM_PRICE.sub("", x).strip() or x)


def _cell_text(v, k):
    """قيمة الخلية زي إكسيل — بس التحاليل ورا بعض بفاصل « • » بدل سطر لكل تحليل،
    ومن غير سعر كل تحليل (SHOW_ITEM_PRICES) عشان الفترة تدخل في أقل صفحات."""
    if k in PRICE_KEYS:
        return money(v.get(k))
    s = _txt(v.get(k))
    if k == "selected_labs_text":
        s = " • ".join(_keep(_item(x)) for x in s.splitlines() if x.strip())
    elif k == "extra_persons_text":
        out = []
        for ln in s.splitlines():
            if not ln.strip():
                continue
            title, sep, labs = ln.partition(": ")
            if sep:
                # الاسم (عربي) في سطر والتحاليل (إنجليزي) في سطر لوحدها — كل فقرة
                # بتاخد اتجاهها الطبيعي، فالأقواس والفواصل مابتتلخبطش على الأطراف.
                items = [_keep(_item(it)) for it in labs.split(" • ") if it.strip()]
                out.append(title.strip() + ":")
                out.append(" • ".join(items))
            else:
                out.append(ln.strip())
        s = "\n".join(out)
    return s


_NBSP = "\u00a0"


def _keep(item):
    """تحليل واحد «Uric Acid — 200 جنيه» مايتقسمش على سطرين لو داخل في الخلية
    (مسافاته بتبقى non-breaking). لو أعرض من الخلية، _wrap بيقسّمه عادي."""
    return re.sub(r"\s+", _NBSP, item.strip())


def _main_cols(visits):
    """عمود «حالات إضافية» بيتشال لو مفيش ولا زيارة فيها حالات إضافية في الفترة."""
    has_xp = any(_txt(v.get("extra_persons_text")).strip() for v in visits)
    return [c for c in MAIN_COLS if has_xp or c[0] != "extra_persons_text"]


def _flex_demand(cols, visits, fonts, cmap):
    """لكل عمود نصي: عرض كل فقرة في كل خلية بحجم خط 1 + أعرض كلمة (للحد الأدنى)."""
    fr, _fb = fonts
    dem, minw = {}, {}
    for k, _l, _w in cols:
        if k in FIXED_KEYS:
            continue
        rows, mw = [], 0.0
        for v in visits:
            paras = [p for p in _prep(_cell_text(v, k), cmap) if p]
            rows.append([_sw(p.replace(_NBSP, " "), fr, 1.0) for p in paras])
            for p in paras:
                for w_ in re.split("[ " + _NBSP + "]", p):
                    if w_:
                        mw = max(mw, _sw(w_, fr, 1.0))
        dem[k], minw[k] = rows, mw
    return dem, minw


def _opt_flex(keys, dem, minw, R, f):
    """
    بيوزّع العرض الباقي R على الأعمدة النصية بحيث مجموع ارتفاع الصفوف يبقى أقل ما
    يمكن (الصف ارتفاعه = أطول خلية فيه). نزول إحداثي: ينقل حتة عرض من عمود لعمود
    طول ما المجموع بيقل. Returns: {key: width}
    """
    import math
    pad = 2 * max(1.4, f * _PAD) + 0.5
    n = len(next(iter(dem.values()))) if dem else 0
    floor_ = {k: min(max(minw[k] * f + pad, R * 0.045), R * 0.32) for k in keys}

    def total(ws):
        tot = 0
        for r in range(n):
            m = 1
            for k in keys:
                cw = ws[k] - pad
                if cw <= 1:
                    return 1e18
                ln = 0
                for pw in dem[k][r]:
                    ln += max(1, math.ceil(pw * f * 1.04 / cw))
                if ln > m:
                    m = ln
            tot += m
        return tot

    area = {k: sum(sum(x) for x in dem[k]) * f + 1.0 for k in keys}
    a_sum = sum(area.values())
    ws = {k: max(floor_[k], R * area[k] / a_sum) for k in keys}
    scale = R / sum(ws.values())
    ws = {k: w * scale for k, w in ws.items()}
    best = total(ws)
    for step_frac in (0.08, 0.04, 0.02, 0.01, 0.005):
        step = R * step_frac
        for _it in range(40):
            improved = False
            for i in keys:
                for j in keys:
                    if i == j or ws[j] - step < floor_[j]:
                        continue
                    ws[i] += step; ws[j] -= step
                    t = total(ws)
                    if t < best:
                        best, improved = t, True
                    else:
                        ws[i] -= step; ws[j] += step
            if not improved:
                break
    return ws


def _main_widths(cols, visits, f, W, fonts, cmap, flex=None):
    """عرض كل عمود: الثابت = أطول قيمة + هامش، والنصي من flex (نسب من الباقي)."""
    fr, fb = fonts
    pad = max(1.4, f * _PAD) * 2 + 1.0
    fixed = {}
    for k, lbl, _w in cols:
        if k not in FIXED_KEYS:
            continue
        need = max([_sw(w_, fb, f) for w_ in _prep(lbl, cmap)[0].split(" ")] + [0])
        for v in visits:
            need = max(need, _sw(_prep(_cell_text(v, k), cmap)[0], fr, f))
        if k in PRICE_KEYS:     # صف الإجمالي (أكبر رقم وبخط أعرض)
            tot = money(sum(_num(v.get(k)) for v in visits))
            need = max(need, _sw(_prep(tot, cmap)[0], fb, f * 1.08))
        if k == "status":
            need = max(need, _sw(_prep(f"{len(visits)} زيارة", cmap)[0], fb, f * 1.08))
        fixed[k] = need + pad
    fsum = sum(fixed.values())
    if fsum > W * 0.62:                       # خط كبير جدًا → الأعمدة الثابتة تتقاسم
        fixed = {k: w * W * 0.62 / fsum for k, w in fixed.items()}
        fsum = W * 0.62
    rest = W - fsum
    if flex:                                  # نسب محسوبة بـ _opt_flex
        fs = sum(flex.values())
        return [fixed[k] if k in FIXED_KEYS else rest * flex[k] / fs for k, _l, _w in cols]
    flex_w = sum(w for k, _l, w in cols if k not in FIXED_KEYS)
    return [fixed[k] if k in FIXED_KEYS else rest * w / flex_w for k, _l, w in cols]


def _fixed_sum(cols, visits, f, W, fonts, cmap):
    ws = _main_widths(cols, visits, f, W, fonts, cmap)
    return sum(w for (k, _l, _w), w in zip(cols, ws) if k in FIXED_KEYS)


def _build_rows(visits, branch_label, period_label, export_date, f, cols):
    """كل الصفوف بحجم خط أساسي f (من غير قياس)."""
    title_s = _style(f * 1.55, True, WHITE)
    sub_s = _style(f * 1.05, True, ORANGE)
    hdr_s = _style(f * 1.0, True, WHITE)
    body = f
    tot_s = _style(f * 1.08, True, WHITE)
    n_main = len(MAIN_COLS)

    statuses = ["تمت", "مجدولة", "في الطريق", "ملغية"]
    parts = "  |  ".join(f"{s}: {sum(1 for v in visits if v.get('status') == s)}"
                         for s in statuses if any(v.get("status") == s for v in visits))
    head = [
        _Row("full", [(0, 0, f"Orange Lab HVMS — {branch_label} — {period_label}", title_s)],
             ORANGE, "title"),
        _Row("full", [(0, 0, f"إجمالي: {len(visits)} زيارة  |  {parts}  |  تاريخ التصدير: {export_date}",
                       sub_s)], ORANGE_LIGHT, "sub"),
    ]
    col_hdr = _Row("main", [(i, i, lbl, hdr_s) for i, (_k, lbl, _w) in enumerate(cols)],
                   ORANGE, "colhdr")

    data = []
    for v in visits:
        fill = STATUS_FILL.get(_txt(v.get("status")), WHITE)
        cells = []
        for i, (k, _lbl, _w) in enumerate(cols):
            s = _cell_text(v, k)
            cells.append((i, i, s, _style(body, align=("r" if k in LEFT_TEXT else "c"))))
        data.append(_Row("main", cells, fill, "data", stretch=True))

    # صف الإجمالي الكلي — مجموع كل الصفوف (زي SUM في إكسيل)
    idx = {k: i for i, (k, _l, _w) in enumerate(cols)}
    tcells = [(0, idx["selected_labs_text"], "الإجمالي الكلي", tot_s)]
    for k in ("labs_price_before", "labs_price_after", "transport_fee", "total_price"):
        tcells.append((idx[k], idx[k], money(sum(_num(v.get(k)) for v in visits)), tot_s))
    tcells.append((idx["status"], idx["status"], f"{len(visits)} زيارة", tot_s))
    total = _Row("main", tcells, ORANGE, "total")

    # ملخص الأطباء — من غير الملغية (زي إكسيل)
    docs = {}
    for v in visits:
        if _txt(v.get("status")) == "ملغية":
            continue
        d = _txt(v.get("doctor_name")) or "غير محدد"
        e = docs.setdefault(d, {"count": 0, "after": 0.0, "transport": 0.0})
        e["count"] += 1
        e["after"] += _num(v.get("labs_price_after"))
        e["transport"] += _num(v.get("transport_fee"))
    docs_sorted = sorted(docs.items(), key=lambda x: x[1]["count"], reverse=True)
    tail = [
        _Row("full", [(0, 0, "", _style(f))], WHITE, "gap"),
        _Row("full", [(0, 0, "ملخص الأطباء — بدل الزيارات", _style(f * 1.15, True, WHITE))],
             DARK, "doctitle"),
        _Row("doc", [(i, i, lbl, hdr_s) for i, (lbl, _w) in enumerate(DOC_COLS)], DARK, "dochdr"),
    ]
    for n_, (dname, d) in enumerate(docs_sorted):
        allow = d["after"] * 0.05
        vals = [str(n_ + 1), dname, str(d["count"]), money(d["after"], True),
                money(allow, True), money(d["transport"], True), money(allow + d["transport"], True)]
        tail.append(_Row("doc", [(i, i, s, _style(f * 1.05, align=("r" if i == 1 else "c")))
                                 for i, s in enumerate(vals)],
                         WHITE if n_ % 2 == 0 else "#F5F5F5", "docrow"))
    t_after = sum(d["after"] for _n, d in docs_sorted)
    t_trans = sum(d["transport"] for _n, d in docs_sorted)
    t_allow = t_after * 0.05
    tail.append(_Row("doc", [(0, 1, "الإجمالي", tot_s),
                             (2, 2, str(sum(d["count"] for _n, d in docs_sorted)), tot_s),
                             (3, 3, money(t_after, True), tot_s), (4, 4, money(t_allow, True), tot_s),
                             (5, 5, money(t_trans, True), tot_s),
                             (6, 6, money(t_allow + t_trans, True), tot_s)], ORANGE, "doctotal"))
    tail.append(_Row("full", [(0, 0, "Developed by Dr. Hussein Ali\nFor Orange Lab © 2026",
                               _style(f * 0.95, True, ORANGE))], ORANGE_LIGHT, "sig"))
    return head, col_hdr, data, total, tail


def _grid_x(grid, W, widths):
    """حدود الأعمدة من اليمين: قائمة (x_left, x_right) لكل عمود."""
    ws = widths[grid]
    tot = float(sum(ws))
    xs, right = [], W
    for w in ws:
        cw = W * w / tot
        xs.append((right - cw, right))
        right -= cw
    xs[-1] = (0.0, xs[-1][1])          # آخر عمود لازق في الحافة الشمال بالظبط
    return xs


def _measure(row, W, cmap, fonts, widths):
    """يحسب السطور الملفوفة وارتفاع الصف (بالحجم الطبيعي من غير مطّ)."""
    fr, fb = fonts
    xs = _grid_x(row.grid, W, widths)
    row.lines, h = [], 0.0
    for c0, c1, text, st in row.cells:
        x_left, x_right = xs[c1][0], xs[c0][1]
        size = st["size"]
        pad = max(1.4, size * _PAD)
        font = fb if st["bold"] else fr
        lines = _wrap(_prep(text, cmap), font, size, max(4.0, x_right - x_left - 2 * pad))
        row.lines.append((x_left, x_right, lines, font, size, st, pad))
        h = max(h, len(lines) * size * _LH + 2 * pad * 0.85)
    row.h = h
    return h


# ══════════════════════════════════════════════════════════════════════════════
# ⑦ التقسيم على الصفحات + ضبط الخط
# ══════════════════════════════════════════════════════════════════════════════
def _paginate(head_h, cont_h, hdr_h, data_hs, tail_h, cap):
    """
    توزيع جشِع: صفحة 1 = عنوان + سطر ملخص + رؤوس أعمدة، والصفحات اللي بعدها =
    عنوان + رؤوس أعمدة. الإجمالي + ملخص الأطباء + التوقيع (tail) لازم يبقوا مع بعض
    في آخر صفحة. Returns: list of [indices of data rows] — آخر عنصر فيه الـ tail.
    """
    pages, cur, used = [], [], head_h + hdr_h
    for i, h in enumerate(data_hs):
        if used + h > cap and cur:
            pages.append(cur)
            cur, used = [], cont_h + hdr_h
        cur.append(i)
        used += h
    if used + tail_h > cap and cur:
        pages.append(cur)
        cur = []
    pages.append(cur)
    return pages


def build_visits_pdf(visits, branch_label, period_label, export_date,
                     f_min=5.5, f_max=13.0):
    """
    visits: list of dicts (نفس مفاتيح جدول الزيارات + extra_persons_text مقروء)
    Returns: bytes (PDF)
    """
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.pdfgen import canvas
    from reportlab.lib.colors import HexColor

    W, H = landscape(A4)
    fr, fb, cmap = _fonts()
    fonts = (fr, fb)

    cols = _main_cols(visits)
    flex_keys = [k for k, _l, _w in cols if k not in FIXED_KEYS]
    dem, minw = _flex_demand(cols, visits, fonts, cmap)

    def flex_at(f):
        return _opt_flex(flex_keys, dem, minw, W - _fixed_sum(cols, visits, f, W, fonts, cmap), f)

    FLEX = {"ws": flex_at(6.5)}                 # نسب مرجعية — بتتعاد عند الخط النهائي

    def layout(f):
        head, col_hdr, data, total, tail = _build_rows(visits, branch_label, period_label,
                                                       export_date, f, cols)
        widths = {"main": _main_widths(cols, visits, f, W, fonts, cmap, FLEX["ws"]),
                  "doc": [w for _l, w in DOC_COLS], "full": [1]}
        for r in head + [col_hdr] + data + [total] + tail:
            _measure(r, W, cmap, fonts, widths)
        gap = tail[0]
        gap.h = f * 0.7
        head_h = sum(r.h for r in head)
        cont_h = head[0].h
        tail_h = total.h + sum(r.h for r in tail)
        return head, col_hdr, data, total, tail, head_h, cont_h, tail_h

    def n_pages(f, cap=H):
        L = layout(f)
        return len(_paginate(L[5], L[6], L[1].h, [r.h for r in L[2]], L[7], cap)), L

    # ① أقل عدد صفحات ممكن (بأصغر خط)، ② أكبر خط يدّي نفس العدد
    p_min, _ = n_pages(f_min)
    f_best = f_min
    f = f_max
    while f > f_min:
        p, _ = n_pages(f)
        if p <= p_min:
            f_best = f
            break
        f = round(f - 0.25, 2)
    _ref = FLEX["ws"]
    FLEX["ws"] = flex_at(f_best)                # نسب مظبوطة على الخط النهائي
    _p, L = n_pages(f_best)
    if _p > p_min:                              # لو زوّدت صفحات (نادر) → المرجعية
        FLEX["ws"] = _ref
        _p, L = n_pages(f_best)
    LAST_INFO.update(font=f_best, pages=p_min,
                     widths={k: round(v) for k, v in zip([c[0] for c in cols], L[1].lines and
                             [x[1] - x[0] for x in L[1].lines] or [])})
    head, col_hdr, data, total, tail, head_h, cont_h, tail_h = L
    data_hs = [r.h for r in data]

    # ③ توزيع متساوي: أقل سعة صفحة لسه بتدّي نفس عدد الصفحات
    lo, hi = H * 0.3, H
    for _ in range(30):
        mid = (lo + hi) / 2
        if len(_paginate(head_h, cont_h, col_hdr.h, data_hs, tail_h, mid)) <= p_min:
            hi = mid
        else:
            lo = mid
    pages = _paginate(head_h, cont_h, col_hdr.h, data_hs, tail_h, hi)
    if len(pages) > p_min:
        pages = _paginate(head_h, cont_h, col_hdr.h, data_hs, tail_h, H)
    n_total = len(pages)

    buf = io.BytesIO()
    cv = canvas.Canvas(buf, pagesize=(W, H))
    cv.setTitle(f"Orange Lab HVMS — {period_label}")
    cv.setAuthor("Orange Lab")

    def draw_row(r, y_top, h):
        y = y_top - h
        cv.setFillColor(HexColor(r.fill))
        cv.rect(0, y, W, h, stroke=0, fill=1)
        for (x_left, x_right, lines, font, size, st, pad) in r.lines:
            if st.get("fill"):
                cv.setFillColor(HexColor(st["fill"]))
                cv.rect(x_left, y, x_right - x_left, h, stroke=0, fill=1)
            if r.grid != "full":
                cv.setStrokeColor(HexColor(BORDER_C if r.kind in ("data", "docrow") else WHITE))
                cv.setLineWidth(0.5)
                cv.rect(x_left, y, x_right - x_left, h, stroke=1, fill=0)
            if not lines:
                continue
            lh = size * _LH
            block = len(lines) * lh
            base = y + h / 2 + block / 2 - size * 0.98        # أول سطر (توسيط رأسي)
            cv.setFillColor(HexColor(st["color"]))
            cv.setFont(font, size)
            for k, ln in enumerate(lines):
                vis = _visual_span(*ln)
                yy = base - k * lh
                if st["align"] == "r":
                    cv.drawRightString(x_right - pad, yy, vis)
                else:
                    cv.drawCentredString((x_left + x_right) / 2, yy, vis)
        return y

    for p_i, idxs in enumerate(pages):
        is_first, is_last = p_i == 0, p_i == n_total - 1
        rows = []
        if is_first:
            rows += head
        else:
            rows.append(head[0])
        rows.append(col_hdr)
        rows += [data[i] for i in idxs]
        if is_last:
            rows.append(total)
            rows += tail
        nat = [r.h for r in rows]
        slack = max(0.0, H - sum(nat))
        # المطّ لصفوف الزيارات بس — ملخص الأطباء والإجماليات بارتفاعهم الطبيعي.
        stretch_ix = [k for k, r in enumerate(rows) if r.stretch]
        if not stretch_ix:                      # صفحة من غير زيارات → المسافة قبل الملخص
            stretch_ix = [k for k, r in enumerate(rows) if r.kind == "gap"] or [len(rows) - 1]
        hs = list(nat)
        for k in stretch_ix:
            hs[k] += slack / len(stretch_ix)
        y = H
        for k, r in enumerate(rows):
            h = hs[k] if k < len(rows) - 1 else y      # آخر صف لازق في الحافة السفلى بالظبط
            y = draw_row(r, y, h)
        if n_total > 1:                         # رقم الصفحة في شريط العنوان (شمال)
            t = head[0]
            sz = t.lines[0][4] * 0.62
            cv.setFillColor(HexColor(WHITE))
            cv.setFont(fr, sz)
            cv.drawString(sz * 0.8, H - t.h / 2 - sz * 0.35,
                          _visual(shape_ar(f"صفحة {p_i + 1} من {n_total}")))
        cv.showPage()
    cv.save()
    return buf.getvalue()
