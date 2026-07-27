# -*- coding: utf-8 -*-
"""
easter_eggs.py — Orange Lab HVMS
تعليقات ومزاح ورسائل تنبيه ذكية داخل برنامج الزيارات المنزلية

للاستخدام الداخلي في Orange Lab فقط (مش للنسخة التجارية).

طريقة الاستخدام:
    import easter_eggs as egg
    msg = egg.tests_comment(len(selected_tests))
    if msg: st.caption(msg)

كل الدوال بترجّع:
    - None            → مفيش تعليق
    - str             → نص جاهز للعرض (فيه الإيموجي جواه)
    - dict            → للحالات اللي محتاجة قرار من المستخدم
"""

from __future__ import annotations
import random
from datetime import datetime, date, time, timedelta

# ════════════════════════════════════════════════════════════════
#  التوقيت المحلي
#  Streamlit Cloud بيشتغل بتوقيت UTC — يعني متأخر عن القاهرة ساعتين
#  أو 3 ساعات. من غير التصحيح ده فحص «التاريخ/الوقت فات» بيفشل.
# ════════════════════════════════════════════════════════════════
TZ_NAME = "Africa/Cairo"
try:
    from zoneinfo import ZoneInfo
    _TZ = ZoneInfo(TZ_NAME)
except Exception:
    _TZ = None


def now_local() -> datetime:
    """الوقت الحالي بتوقيت القاهرة، مهما كان توقيت السيرفر."""
    if _TZ is not None:
        return datetime.now(_TZ).replace(tzinfo=None)
    # احتياطي لو zoneinfo/tzdata مش متوفرين: UTC+3 (توقيت مصر الصيفي)
    return datetime.utcnow() + timedelta(hours=3)


def today_local() -> date:
    return now_local().date()

# ════════════════════════════════════════════════════════════════
#  مفتاح التشغيل العام
# ════════════════════════════════════════════════════════════════
EGG_VERSION = "1.5"      # للتأكد إن النسخة الجديدة هي اللي شغالة فعلاً
FUN_MODE = True          # خليها False لو حبيت تقفل كل التعليقات مرة واحدة
SERIOUS_WARNINGS = True  # تنبيهات التاريخ والسعر — يفضّل تفضل True دايماً


def _pick(seed, options):
    """اختيار ثابت (مش بيتغير مع كل rerun) بس متنوع حسب المدخل."""
    if not options:
        return None
    return random.Random(str(seed)).choice(options)


# ════════════════════════════════════════════════════════════════
#  1) عدّاد التحاليل
# ════════════════════════════════════════════════════════════════
TEST_TIERS = {
    0: [
        "زيارة من غير تحاليل؟ يعني قعدة وشاي وكلام حلو ☕",
        "التحاليل فين؟ ولا الزيارة دي مجاملة 😄",
    ],
    1: [
        "تحليل واحد بس؟ العميل ده بخيل شوية 😅",
    ],
    3: [
        "حلو كده 👌",
        "تمام، ماشي في السكة الصح 👌",
    ],
    5: [
        "كفاية كده بقى 🙂",
        "خمسة؟ الحمد لله، كفاية ✋",
    ],
    10: [
        "حرام عليك يا مفتري 😂",
        "عشرة؟! الراجل جاي يعمل زيارة ولا صيانة شاملة 😂",
    ],
    15: [
        "اتق الله وكفاية عليه كده!! 😳",
        "خمستاشر تحليل؟ سيبله دم يمشي بيه 😳",
    ],
    20: [
        "هو انت عايز تحقق التارجيت في زيارة واحدة؟ 🎯",
        "عشرين؟ ده مش عميل ده مشروع قومي 🎯",
    ],
    30: [
        "يا عم ده احنا كده بنعمل Full Body Scan 🧬",
        "تلاتين تحليل... ابعتله المعمل كله وخلاص 🧬",
    ],
}


def tests_comment(count: int, key: str = "") -> str | None:
    """تعليق حسب عدد التحاليل المختارة. يتحط تحت مربع اختيار التحاليل مباشرة."""
    if not FUN_MODE:
        return None
    tier = None
    for t in sorted(TEST_TIERS.keys(), reverse=True):
        if count >= t:
            tier = t
            break
    if tier is None:
        return None
    # 1 و 3 و 5 بس عند الرقم بالظبط، الباقي عند الوصول أو أكتر
    if tier in (0, 1) and count != tier:
        return None
    return _pick(f"{key}|{tier}|{count}", TEST_TIERS[tier])


# ════════════════════════════════════════════════════════════════
#  2) فحص التاريخ والوقت
# ════════════════════════════════════════════════════════════════
PAST_MSGS = [
    "🍺 انت شارب حاجة؟ التاريخ ده عدّى خلاص!",
    "⏰ التاريخ ده فات... راجع نفسك",
    "🕰️ الزيارة دي في الماضي — آلة الزمن مش ضمن الباقة",
]

FAR_FUTURE_MSGS = [
    "🔮 بتحجز من دلوقتي؟ ده بعد {days} يوم!",
    "🔮 التاريخ ده بعيد قوي — {days} يوم من النهاردة. متأكد؟",
]

LATE_NIGHT_MSGS = [
    "🌙 الساعة {h} بالليل؟ ربنا يقوّي الدكتور 💪",
    "🦉 معاد آخر الليل... الدكتور هيشتغل بومة",
]

VERY_EARLY_MSGS = [
    "🌅 قبل الفجر؟ ده مش معمل ده مأذنة",
    "☀️ بدري أوي كده... متأكد من الوقت؟",
]


def date_sanity(visit_date, visit_time=None, now: datetime | None = None,
                far_future_days: int = 60) -> dict | None:
    """
    فحص منطقية تاريخ/وقت الزيارة.

    بيرجّع dict فيه:
        level   : "blocker" (محتاج قرار) أو "info" (تنبيه بس)
        message : نص الرسالة
        choices : قائمة اختيارات (للـ blocker بس)
        code    : past / far_future / late_night / very_early

    مثال:
        r = egg.date_sanity(d, t)
        if r and r["level"] == "blocker":
            st.warning(r["message"])
            ans = st.radio("", r["choices"], key="past_fix")
            ...
    """
    if not SERIOUS_WARNINGS:
        return None
    now = now or now_local()

    if isinstance(visit_date, datetime):
        visit_date = visit_date.date()
    if visit_date is None:
        return None

    dt = datetime.combine(visit_date, visit_time or time(12, 0))

    # ─ تاريخ فات ─
    if dt < now - timedelta(minutes=30):
        return {
            "code": "past",
            "level": "blocker",
            "message": _pick(str(visit_date), PAST_MSGS)
                       + "\n\nدي زيارة نسيت تسجّلها ولا التاريخ غلط؟",
            "choices": [
                "🔧 هعدّل التاريخ/الوقت",
                "🙏 نسيت أسجّلها... متأسف جداً",
            ],
        }

    # ─ تاريخ بعيد أوي ─
    days = (visit_date - now.date()).days
    if days > far_future_days:
        return {
            "code": "far_future",
            "level": "info",
            "message": _pick(str(visit_date), FAR_FUTURE_MSGS).format(days=days),
        }

    # ─ وقت غريب ─
    if visit_time:
        h = visit_time.hour
        if h >= 23 or h <= 3:
            disp = h if h <= 12 else h - 12
            return {
                "code": "late_night",
                "level": "info",
                "message": _pick(str(visit_time), LATE_NIGHT_MSGS).format(h=disp),
            }
        if 4 <= h < 6:
            return {
                "code": "very_early",
                "level": "info",
                "message": _pick(str(visit_time), VERY_EARLY_MSGS),
            }
    return None


# ════════════════════════════════════════════════════════════════
#  3) إنجازات اليوم (فرع / دكتور)
# ════════════════════════════════════════════════════════════════
MASHALLAH = [
    "بسم الله ما شاء الله... اللهم لا حسد 🧿",
    "ما شاء الله تبارك الله 🧿 اللهم لا حسد",
]

# كل رقم = قائمة اختيارات، والبرنامج بيختار واحد ثابت لكل (دكتور/فرع + رقم)
BRANCH_MILESTONES = {
    1:  ["🌅 فاتحة خير — أول زيارة النهاردة"],
    2:  ["😎 شغال ما شاء الله",
         "💪 التانية... شغال ما شاء الله"],
    3:  MASHALLAH,
    4:  ["🧿 بسم الله ما شاء الله... اللهم لا حسد",
         "🧿 رابع زيارة — اللهم لا حسد ولا عين تصيب"],
    5:  ["🙈 أنا مش هعلّق لحسن تفتكر إني بحسد",
         "🔥 خمس زيارات! اليوم ماشي حلو"],
    7:  ["😮 سبعة؟ الفرع ده مولّع"],
    10: ["🏆 عشر زيارات — يوم أسطوري!"],
    15: ["🚀 خمستاشر زيارة... احنا فتحنا فرع تاني ولا إيه؟"],
}

DOCTOR_MILESTONES = {
    1:  ["🌅 أول زيارة للدكتور النهاردة — بالتوفيق"],
    2:  ["😌 تاني زيارة للدكتور... ابسط يا عم",
         "🙂 التانية على طول؟ ابسط يا عم"],
    3:  ["🧿 تالت زيارة... اللهم لا حسد",
         "🧿 تالت زيارة للدكتور — اللهم لا حسد"],
    4:  ["😅 رابع زيارة... كده كتير يا دكتور والله",
         "😅 الرابعة؟ كده كتير يا دكتور والله"],
    5:  ["💪 الدكتور ده مكنة — خمس زيارات",
         "🏅 هو مفيش إلا انت يا دكتور؟ ما شاء الله",
         "🚗 خمسة! الدكتور ده مكنة والله"],
    7:  ["😅 سيبوا للدكتور وقت ياكل"],
    10: ["🥇 عشر زيارات لدكتور واحد! يستاهل مكافأة"],
}


def _visits_ar(n: int) -> str:
    """صياغة عربية سليمة لعدد الزيارات."""
    if n == 1:  return "زيارة واحدة"
    if n == 2:  return "زيارتين"
    if 3 <= n <= 10: return f"{n} زيارات"
    return f"{n} زيارة"


def daily_milestone(count: int, kind: str = "branch", name: str = "") -> str | None:
    """
    تعليق لما الفرع أو الدكتور يوصل عدد معين من الزيارات في اليوم.
    kind: "branch" أو "doctor"
    count: عدد زيارات اليوم *بعد* إضافة الزيارة الحالية
    """
    if not FUN_MODE:
        return None
    table = BRANCH_MILESTONES if kind == "branch" else DOCTOR_MILESTONES
    options = table.get(count)
    if not options:
        return None
    msg   = _pick(f"{kind}|{name}|{count}", options)
    label = f"فرع {name}" if kind == "branch" else f"د. {name}"
    return f"{msg}  \n({label} — {_visits_ar(count)} النهاردة)"


# ════════════════════════════════════════════════════════════════
#  4) الفلوس
# ════════════════════════════════════════════════════════════════
def price_comment(total: float, discount_pct: float = 0.0) -> str | None:
    """تعليق على السعر والخصم."""
    if not SERIOUS_WARNINGS:
        return None
    if total is None:
        return None
    if total <= 0:
        return _pick(str(total), [
            "💸 الفلوس فين؟ السعر صفر!",
            "🎁 زيارة ببلاش؟ ربنا يكرمك بس راجع السعر",
        ])
    # ── خصم بالسالب = السعر بعد الخصم أعلى من قبل الخصم ──
    if discount_pct < 0:
        return _pick(str(total), [
            "🕵️ بعد الخصم أعلى من قبله! لو الرقم ده صح يبقى انت حرامي 😂 "
            "— أغلب الظن إنك استدعيت عميل سابق وسعره القديم لسه واقف",
            "😂 خصم بالسالب؟ لو الرقم مظبوط يبقى انت حرامي "
            "— راجع «السعر بعد الخصم»، ده على الأرجح سعر الزيارة القديمة",
            "🚨 بعد الخصم أغلى من قبله — سعر قديم من استدعاء عميل سابق؟ "
            "أو انت حرامي فعلاً 😂",
        ])
    if discount_pct >= 50:
        return f"😱 خصم {discount_pct:.0f}%؟ ده احنا بندفع للعميل!"
    if discount_pct >= 40:
        return f"😅 خصم {discount_pct:.0f}% — الخصم ده هيوصلنا الحسينية"
    if discount_pct >= 25:
        return f"🤏 خصم {discount_pct:.0f}%... راجع مع الإدارة"
    if FUN_MODE and total >= 3000:
        return "🤑 فاتورة محترمة — ما شاء الله"
    return None


# ════════════════════════════════════════════════════════════════
#  5) بيانات العميل
# ════════════════════════════════════════════════════════════════
def client_comment(name: str = "", phone: str = "", tag: str = "",
                   age_years: int | None = None, age_unit: str = "سنة") -> list[str]:
    """
    تعليقات على بيانات العميل. بيرجّع list — ممكن تكون فاضية.
    كل عنصر يتعرض في st.caption منفصل.
    """
    out = []

    # ─ التليفون ─
    digits = "".join(ch for ch in str(phone or "") if ch.isdigit())
    if digits:
        if len(digits) < 11:
            out.append(f"📵 الرقم ناقص ({len(digits)} رقم) — جربت تتصل بيه؟")
        elif len(digits) > 11:
            out.append(f"📵 الرقم زيادة ({len(digits)} رقم) — متأكد؟")
        elif not digits.startswith("01"):
            out.append("📵 الرقم مش بادئ بـ 01 — راجعه")
        elif len(set(digits[2:])) <= 2:
            out.append("🤨 الرقم ده شكله وهمي... راجعه")

    # ─ الاسم ─
    #   ملاحظة: تنبيه «الاسم فاضي» بيظهر بس لو المستخدم بدأ يملا حاجة تانية،
    #   عشان الفورم ماتفتحش وهي مليانة تحذيرات.
    clean   = (name or "").strip()
    started = bool(digits)
    if not clean:
        if started:
            out.append(_pick(phone, [
                "✍️ الاسم فين؟ الزيارة هتتسجل باسم مين — «العميل»؟ 😅",
                "😅 نسيت الاسم... مش هينفع نكتب «واحد صاحبنا»",
                "📝 اكتب الاسم بقى، الرقم لوحده مش كفاية",
            ]))
    elif len(clean) <= 2:
        out.append("😅 ده اسم ولا اختصار؟")
    elif len(clean.split()) == 1 and FUN_MODE:
        out.append("📝 اسم واحد بس؟ حاول تكتب الاسم بالكامل")

    # ─ السن ─
    if age_years is not None:
        if not age_years:
            if clean:
                out.append(_pick(clean, [
                    "🎂 السن فاضي — العميل لسه ماتولدش؟",
                    "🍼 صفر سنة؟ لو مولود جديد حط السن بالشهر، وإلا اكتب سنه",
                    "😄 السن صفر... اكتبه بجد بقى",
                ]))
        elif age_unit == "سنة" and age_years > 120:
            out.append("🤔 السن ده غريب... راجعه")
        elif age_unit == "سنة" and age_years >= 90 and FUN_MODE:
            out.append("👴 ربنا يطول في عمره — خد بالك من العينة")

    # ─ التصنيف ─
    if FUN_MODE and tag:
        t = str(tag).upper()
        if "VIP" in t:
            out.append("🎩 دخل الباشا — عميل VIP، خد بالك")
        elif "FREQUENT" in t or "متكرر" in tag:
            out.append("🔁 عميل دائم — يستاهل معاملة خاصة")
        elif "NEW" in t or "جديد" in tag:
            out.append("🌱 عميل جديد — الانطباع الأول مهم")

    return [m for m in out if m]


def transport_comment(fee) -> str | None:
    """تعليق لما بدل الانتقال يبقى صفر."""
    if not FUN_MODE:
        return None
    try:
        fee = float(fee or 0)
    except Exception:
        return None
    if fee > 0:
        return None
    return _pick("transport", [
        "🚗 الزيارة ببلاش ليه؟ العميل تبع أمن الدولة ولا مجاملة؟ 😄",
        "🛵 بدل انتقال صفر... الدكتور هيروح مشي؟",
        "😅 مفيش بدل انتقال؟ يا إما مجاملة يا إما نسيته",
        "⛽ صفر انتقال؟ البنزين بقى ببلاش وماحدش قالنا",
    ])


def address_comment(address: str = "", started: bool = True) -> str | None:
    """تعليق لما العنوان يبقى فاضي أو ناقص."""
    clean = (address or "").strip()
    if not clean:
        if not started:
            return None
        return _pick("addr", [
            "😴 انت تعبان يا دكتور — زيارة من غير عنوان؟",
            "🏠 العنوان فين؟ الدكتور هيلف البلد يدوّر؟",
            "🗺️ من غير عنوان الزيارة دي مش هتتسجل — اكتبه",
        ])
    if len(clean) < 10 and FUN_MODE:
        return "🤏 العنوان ده مختصر قوي — الدكتور هيلاقي البيت إزاي؟"
    return None


# ════════════════════════════════════════════════════════════════
#  6) تكرار
# ════════════════════════════════════════════════════════════════
def duplicate_comment(hours_ago: float | None) -> str | None:
    """لو نفس العميل مسجّل زيارة قريّب."""
    if hours_ago is None:
        return None
    if hours_ago < 3:
        return f"🤔 العميل ده اتسجل من {int(hours_ago*60)} دقيقة... متأكد إنها زيارة تانية؟"
    if hours_ago < 24:
        return f"🤔 ده اتسجل من {int(hours_ago)} ساعة — زيارة جديدة فعلاً؟"
    if hours_ago < 24 * 7:
        return f"🔁 العميل ده عنده زيارة من {int(hours_ago/24)} يوم"
    return None


# ════════════════════════════════════════════════════════════════
#  7) التقييم
# ════════════════════════════════════════════════════════════════
RATING_MSGS = {
    5: ["🌟 كده كده! خمس نجوم", "🌟 ما شاء الله — العميل مبسوط"],
    4: ["👍 كويس، بس في مساحة للأحسن"],
    3: ["😐 متوسط... نشوف إيه اللي ناقص"],
    2: ["😕 التقييم ضعيف — لازم متابعة"],
    1: ["😔 نجمة واحدة؟ لازم نعرف المشكلة فين — كلّم العميل"],
}


def rating_comment(stars: int | None) -> str | None:
    if not stars:
        return None
    opts = RATING_MSGS.get(int(stars))
    return _pick(str(stars), opts) if opts else None


# ════════════════════════════════════════════════════════════════
#  8) رسائل موسمية  (عدّل التواريخ كل سنة)
# ════════════════════════════════════════════════════════════════
SEASONS = [
    # (شهر_بداية, يوم, شهر_نهاية, يوم, الرسالة)
    (1,  1,  1,  2,  "🎉 كل سنة وانتوا طيبين — سنة جديدة سعيدة"),
    (1,  7,  1,  7,  "🎄 كل سنة وانتوا طيبين"),
    (2, 17,  3, 19,  "🌙 رمضان كريم — الزيارات بعد الفطار أفضل"),   # رمضان 1448 تقريبي
    (3, 20,  3, 23,  "🌙 عيد فطر مبارك 🎊"),
    (5, 27,  5, 30,  "🐑 عيد أضحى مبارك 🎊"),
    (4, 13,  4, 13,  "🥚 شم النسيم — خد بالك من الفسيخ 🐟"),
    (12, 31, 12, 31, "🎊 آخر يوم في السنة — كل سنة وانتوا طيبين"),
]


def seasonal_greeting(today: date | None = None) -> str | None:
    """رسالة موسمية تتعرض مرة واحدة في أول الصفحة."""
    if not FUN_MODE:
        return None
    today = today or today_local()
    for m1, d1, m2, d2, msg in SEASONS:
        start = date(today.year, m1, d1)
        end = date(today.year, m2, d2)
        if start <= today <= end:
            return msg
    return None


# ════════════════════════════════════════════════════════════════
#  9) رسالة عشوائية عند حفظ الزيارة
# ════════════════════════════════════════════════════════════════
SAVE_MSGS = [
    "✅ اتسجلت — ربنا يبارك",
    "✅ تمام، الزيارة اتحفظت 👍",
    "✅ خلاص، اطمن",
    "✅ اتسجلت بنجاح 🍊",
    "✅ ماشي — الزيارة في السيستم",
]


def save_message() -> str:
    if not FUN_MODE:
        return "✅ تم الحفظ"
    return random.choice(SAVE_MSGS)


# ════════════════════════════════════════════════════════════════
#  10) دوال مساعدة للعرض في Streamlit
# ════════════════════════════════════════════════════════════════
def render_caption(st, msg):
    """يعرض تعليق (أو أكتر) تحت الحقل مباشرة."""
    if not msg:
        return
    if isinstance(msg, str):
        msg = [msg]
    for m in msg:
        if m:
            st.caption(m)


def render_toast(st, msg, icon="🍊"):
    """يعرض toast بعد الحفظ."""
    if msg:
        try:
            st.toast(msg, icon=icon)
        except Exception:
            st.success(msg)


# ════════════════════════════════════════════════════════════════
#  اختبار سريع من الترمنال:  python easter_eggs.py
# ════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("── التحاليل ──")
    for n in (0, 1, 3, 5, 10, 15, 20, 30):
        print(f"  {n:>2} → {tests_comment(n)}")

    print("\n── التاريخ ──")
    print(" ", date_sanity(date.today() - timedelta(days=3)))
    print(" ", date_sanity(date.today() + timedelta(days=90)))
    print(" ", date_sanity(date.today(), time(1, 30)))

    print("\n── الإنجازات ──")
    for n in (1, 3, 5, 10):
        print(f"  branch {n} → {daily_milestone(n, 'branch', 'La Cite')}")
    print(f"  doctor 3 → {daily_milestone(3, 'doctor', 'محمد شفيق')}")

    print("\n── الفلوس ──")
    print(" ", price_comment(0))
    print(" ", price_comment(1000, 45))

    print("\n── العميل ──")
    print(" ", client_comment("أ", "0123", "VIP", 95))

    print("\n── متفرقات ──")
    print(" ", duplicate_comment(1.5))
    print(" ", rating_comment(1))
    print(" ", seasonal_greeting())
    print(" ", save_message())
