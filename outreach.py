# -*- coding: utf-8 -*-
"""
outreach.py — التواصل اليومي (دوال نقية: مفيش Streamlit ولا داتابيز ولا شبكة)

  reminder_message(v)                 رسالة تذكير قصيرة للعميل بزيارة بكرة
  doctor_day_sheet(visits, doctor)    كشف يوم الدكتور: الزيارات بالوقت ثم المنطقة + حساب النقدية
  lapsed_clients(visits, today, days) عملاء آخر زيارة ليهم من days يوم أو أكتر ومالهمش زيارة جاية
  lapsed_message(c, today)            رسالة «وحشتنا» قصيرة
"""
from datetime import date, datetime

from core import _time_key, format_date_ar, parse_extra_persons, extra_person_title

PAID, PARTIAL, UNPAID = "مدفوع", "مدفوع جزئياً", "غير مدفوع"
CASH = "نقدي"
CANCELLED = "ملغية"
PENDING = ("مجدولة", "في الطريق")
WEEKDAYS_AR = ["الاثنين", "الثلاثاء", "الأربعاء", "الخميس", "الجمعة", "السبت", "الأحد"]


def _num(v):
    try:
        f = float(v or 0)
        return 0.0 if f != f else f
    except Exception:
        return 0.0


def money(v):
    f = _num(v)
    s = f"{f:,.2f}".rstrip("0").rstrip(".") if abs(f - round(f)) > 1e-9 else f"{round(f):,.0f}"
    return f"{s} ج"


def _d(x):
    if isinstance(x, date):
        return x
    try:
        return datetime.strptime(str(x)[:10], "%Y-%m-%d").date()
    except Exception:
        return None


def day_label(d):
    """2026-11-12 → «الخميس 12 نوفمبر 2026»"""
    dd = _d(d)
    return f"{WEEKDAYS_AR[dd.weekday()]} {format_date_ar(dd)}" if dd else str(d or "")


def _area(v):
    parts = [str(v.get(k) or "").strip() for k in ("city", "district")]
    return " / ".join(p for p in parts if p)


def lab_names(text, name_fn=None):
    """«CBC — 400 جنيه\\nFerritin — 400 جنيه» → ["CBC", "Ferritin"]"""
    out = []
    for ln in str(text or "").splitlines():
        if ln.strip():
            out.append(name_fn(ln) if name_fn else ln.strip())
    return out


# ══════════════════════════════════════════════════════════════════════════════
# ① تذكير زيارة بكرة
# ══════════════════════════════════════════════════════════════════════════════
def reminder_message(v):
    """رسالة قصيرة — من غير تحاليل ولا أسعار (التفاصيل وصلت في رسالة الحجز)."""
    name = str(v.get("name") or "").strip()
    when = day_label(v.get("visit_date"))
    t = str(v.get("visit_time") or "").strip()
    if t:
        when += f" — الساعة {t}"
    doc = str(v.get("doctor_name") or "").strip()
    area = _area(v)
    lines = [
        "🟠 *معمل أورانج لاب — تذكير بالزيارة المنزلية*",
        f"أهلاً {name} 🌸" if name else "أهلاً بك 🌸",
        f"📅 ميعاد زيارتك: {when}",
    ]
    if doc:
        lines.append(f"👨‍⚕️ الدكتور: {doc}")
    if area:
        lines.append(f"📍 {area}")
    lines.append("لو محتاج تغيّر الميعاد ابعتلنا هنا. شكراً لثقتكم 🧡")
    return "\n".join(lines)


def reminder_candidates(visits, day):
    """زيارات اليوم ده اللي لسه (مجدولة / في الطريق)، مرتّبة بالوقت."""
    ds = str(_d(day) or day)
    out = [v for v in visits if str(v.get("visit_date") or "")[:10] == ds
           and v.get("status", "مجدولة") in PENDING and not v.get("deleted_at")]
    return sorted(out, key=lambda v: (_time_key(v.get("visit_time")), _area(v), str(v.get("name") or "")))


# ══════════════════════════════════════════════════════════════════════════════
# ② كشف يوم الدكتور
# ══════════════════════════════════════════════════════════════════════════════
def visit_money(v):
    """
    (المتبقي تحصيله, النقدي اللي اتحصّل ومتسجّل)
      مدفوع              → متبقي 0
      غير مدفوع / جزئي   → متبقي = الإجمالي − المدفوع
      المدفوع بطريقة «نقدي» = نقدية مع الدكتور
    """
    total, paid = _num(v.get("total_price")), _num(v.get("paid_amount"))
    st = v.get("payment_status") or UNPAID
    remaining = 0.0 if st == PAID else max(0.0, total - paid)
    cash = paid if (st in (PAID, PARTIAL) and (v.get("payment_method") or "") == CASH) else 0.0
    return remaining, cash


def doctor_day_sheet(visits, doctor, day, name_fn=None):
    """
    Returns (نص الرسالة, ملخص dict). الزيارات الملغية مش داخلة.
    الترتيب: الوقت، وبعدين المنطقة (الزيارات من غير وقت بتتجمّع بالمنطقة في الأول).
    """
    ds = str(_d(day) or day)
    vs = [v for v in visits if str(v.get("doctor_name") or "").strip() == str(doctor).strip()
          and str(v.get("visit_date") or "")[:10] == ds and v.get("status") != CANCELLED
          and not v.get("deleted_at")]
    vs.sort(key=lambda v: (_time_key(v.get("visit_time")), _area(v), str(v.get("name") or "")))
    rem_t = cash_t = 0.0
    n_cases = 0
    sep = "━━━━━━━━━━━━━━"
    out = [f"🟠 *كشف زيارات د. {doctor}*", f"📅 {day_label(ds)} — {len(vs)} زيارة", sep]
    for i, v in enumerate(vs, 1):
        rem, cash = visit_money(v)
        rem_t += rem
        cash_t += cash
        xps = parse_extra_persons(v.get("extra_persons"))
        n_cases += 1 + len(xps)
        t = str(v.get("visit_time") or "").strip() or "بدون وقت"
        out.append(f"*{i}) {t} — {v.get('name', '')}*")
        if v.get("phone"):
            out.append(f"📞 {v.get('phone')}")
        area, addr = _area(v), str(v.get("address") or "").strip()
        place = " — ".join(p for p in (area, addr) if p)
        if place:
            out.append(f"📍 {place}")
        if v.get("location_link"):
            out.append(f"🗺️ {v.get('location_link')}")
        labs = lab_names(v.get("selected_labs_text"), name_fn)
        if labs:
            out.append("🧪 " + " • ".join(labs))
        for p in xps:
            pl = [name_fn(x) if name_fn else x for x in p.get("labs", [])]
            out.append(f"👥 {extra_person_title(p)}" + (": " + " • ".join(pl) if pl else ""))
        st = v.get("payment_status") or UNPAID
        if rem > 0:
            out.append(f"💵 المطلوب تحصيله: {money(rem)}")
        elif st == PAID:
            how = v.get("payment_method") or ""
            out.append("✅ مدفوع" + (f" ({how})" if how else ""))
        out.append(sep)
    out.append("💰 *الحساب:*")
    out.append(f"• متبقي تحصيله من العملاء: {money(rem_t)}")
    if cash_t:
        out.append(f"• نقدي اتحصّل ومتسجّل: {money(cash_t)}")
    out.append(f"• *المطلوب تسليمه للمعمل آخر اليوم: {money(rem_t + cash_t)}*")
    out.append("_(لو كل المتبقي اتحصّل كاش)_")
    summary = {"visits": len(vs), "cases": n_cases, "remaining": rem_t, "cash": cash_t,
               "to_hand_over": rem_t + cash_t, "ids": [v.get("id") for v in vs]}
    return "\n".join(out), summary


def doctors_on_day(visits, day):
    """[(دكتور, عدد)] للدكاترة اللي عندهم زيارات في اليوم ده — الأكتر الأول."""
    ds = str(_d(day) or day)
    cnt = {}
    for v in visits:
        if str(v.get("visit_date") or "")[:10] == ds and v.get("status") != CANCELLED \
                and not v.get("deleted_at"):
            d = str(v.get("doctor_name") or "").strip()
            if d:
                cnt[d] = cnt.get(d, 0) + 1
    return sorted(cnt.items(), key=lambda x: (-x[1], x[0]))


# ══════════════════════════════════════════════════════════════════════════════
# ③ عملاء مرجعوش
# ══════════════════════════════════════════════════════════════════════════════
def lapsed_clients(visits, today, days, branch=None):
    """
    عميل (بالتليفون) آخر زيارة غير ملغية ليه من `days` يوم أو أكتر، ومالوش زيارة جاية
    (مجدولة/في الطريق من النهاردة ورايح). branch: الفرع اللي آخر زيارة كانت فيه.
    Returns [dict] — الأحدث انقطاعًا الأول (أسهل يرجعوا).
    """
    td = _d(today)
    by_phone = {}
    upcoming = set()
    for v in visits:
        ph = str(v.get("phone") or "").strip()
        if not ph or v.get("deleted_at"):
            continue
        vd = _d(v.get("visit_date"))
        if not vd:
            continue
        stt = v.get("status") or "مجدولة"
        if vd >= td and stt in PENDING:
            upcoming.add(ph)
        if stt == CANCELLED or vd > td:
            continue
        c = by_phone.get(ph)
        if c is None:
            by_phone[ph] = c = {"phone": ph, "name": "", "last_date": vd, "visits": 0,
                                "branch": "", "doctor": "", "last_id": ""}
        c["visits"] += 1
        if vd >= c["last_date"]:
            c.update(last_date=vd, name=str(v.get("name") or c["name"]),
                     branch=str(v.get("branch") or ""), doctor=str(v.get("doctor_name") or ""),
                     last_id=str(v.get("id") or ""))
    out = []
    for ph, c in by_phone.items():
        if ph in upcoming:
            continue
        gap = (td - c["last_date"]).days
        if gap < days:
            continue
        if branch and c["branch"] != branch:
            continue
        out.append({**c, "days": gap, "last_date": c["last_date"].isoformat()})
    out.sort(key=lambda c: (c["days"], c["name"]))
    return out


def lapsed_message(c):
    """رسالة «وحشتنا» قصيرة."""
    months = max(1, round(int(c.get("days", 0)) / 30))
    name = str(c.get("name") or "").strip()
    period = "شهر" if months == 1 else ("شهرين" if months == 2 else f"{months} شهور")
    return "\n".join([
        "🟠 *معمل أورانج لاب*",
        f"أهلاً {name} 🌸" if name else "أهلاً بك 🌸",
        f"وحشتنا! آخر زيارة منزلية ليك كانت من حوالي {period}.",
        "لو حابب تعيد تحاليلك الدورية من البيت، ابعتلنا الميعاد اللي يناسبك ونحجزلك زيارة 🧡",
    ])
