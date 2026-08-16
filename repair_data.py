#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
repair_data.py — تنظيف البيانات التاريخية لـ Orange Lab HVMS

التطبيع اللي اتضاف في app.py بيشتغل على البيانات **الجديدة** بس.
السكربت ده بيصلّح الـ1,030 سجل الموجود.

⚠️ الافتراضي هو dry-run — مابيكتبش أي حاجة.
   شغّله من غير --apply الأول واقرا التقرير. لو موافق، شغّله بـ --apply.

الاستخدام:
    python3 repair_data.py                    # معاينة بس (الافتراضي)
    python3 repair_data.py --apply            # التنفيذ الفعلي + backup تلقائي
    python3 repair_data.py --only geo,phone   # إصلاحات محددة بس
    python3 repair_data.py --files Visits.json archive/Visits_upto_2026-05-31.json

الإصلاحات المتاحة:
    geo     توحيد إملاء المنطقة والمدينة (الحى→الحي · 6اكتوبر→6 اكتوبر)
    phone   فصل أرقام التليفون الملزوقة (رقمين في خانة واحدة)
    date    الإبلاغ عن التواريخ الفاسدة  ⚠️ بيبلّغ بس، مابيصلّحش
    pay     الإبلاغ عن التناقضات المالية  ⚠️ بيبلّغ بس، مابيصلّحش

ليه `date` و `pay` بيبلّغوا بس؟
    لأن تصليحهم بالتخمين هو نفس غلطة `date.today()` اللي شيلناها من الاستيراد.
    البرنامج مايخترعش بيانات — بيقول لك فين المشكلة وانت تقرر.
"""
import json, re, sys, shutil, argparse, os
from datetime import datetime, date
from collections import Counter, defaultdict

DEFAULT_FILES = ["Visits.json", "archive/Visits_upto_2026-05-31.json",
                 "visits/2026-06.json", "visits/2026-07.json", "visits/2026-08.json"]

# ── الطبقة النقية مستوردة من core.py ────────────────────────────────────────
# ★ مافيش نسخ. السكربت والبرنامج بيستخدموا **نفس** الكود، فمستحيل يحصل
#   انحراف بينهم (السكربت يصلّح بشكل والبرنامج يخزّن بشكل تاني).
from core import (
    normalize_ar, clean_text, canonicalize_geo,
    _payment_problems as payment_problems,
    _GEO_CANON_LIST, _GEO_ALIASES,
)

_RICH = set("ةأإآئؤي")


def pick_canonical(variants):
    """
    من مجموعة أشكال لنفس المكان، بيختار **أصحّ** إملاء — مش الأكتر تكرارًا.

    الترتيب: غنى الإملاء (ة/أ/ئ/ي) ← تباعد سليم بين الرقم والحرف ← التكرار.
    عشان كده «6 أكتوبر» (281 مرة) بتكسب «6اكتوبر» (542 مرة)، و«حدائق الاهرام»
    بتكسب «حدايق الاهرام». التكرار وحده كان هيخزّن الشكل المشوّه.
    """
    def score(item):
        v, freq = item
        rich   = sum(1 for c in v if c in _RICH)
        spaced = 0 if re.search(r"\d[\u0600-\u06FF]", v) else 1
        return (rich, spaced, freq)
    return max(variants.items(), key=score)[0]


def build_geo_canon(records):
    """
    خريطة: مفتاح المطابقة → أصحّ شكل.
    القوائم القانونية من core.py ليها الأولوية المطلقة، وبعدين نستنتج الباقي
    من البيانات نفسها. كده السكربت والبرنامج متفقين حرفيًا.
    """
    groups = defaultdict(Counter)
    for r in records:
        for fld in ("city", "district"):
            v = clean_text(r.get(fld))
            if v:
                groups[normalize_ar(v)][v] += 1
    canon = {}
    for c in _GEO_CANON_LIST:
        canon[normalize_ar(c)] = c
    for a, c in _GEO_ALIASES.items():
        canon[normalize_ar(a)] = c
    for k, vs in groups.items():
        canon.setdefault(k, pick_canonical(vs))
    return canon


def split_glued_phone(raw):
    """
    رقمين مصريين ملزوقين في خانة واحدة → (الأول, الثاني) أو None.

    المصري 11 رقم بيبدأ بـ 01. الشكل السائد في البيانات: 22 رقم = 11+11.
    بنكون متحفظين عن قصد: لو الشكل مش مطابق بالظبط، بنسيبه ونبلّغ عنه
    بدل ما نخمّن ونقطع رقم صح نصين.
    """
    d = re.sub(r"\D", "", str(raw or ""))
    if len(d) == 22 and d.startswith("01") and d[11:13] == "01":
        return d[:11], d[11:]
    return None




def valid_date(d):
    try:
        date.fromisoformat(str(d or "")[:10]); return True
    except Exception:
        return False


# ── المحرك ──────────────────────────────────────────────────────────────────
def repair(files, only, apply):
    changes = defaultdict(list)   # نوع الإصلاح → [تفاصيل]
    reports = defaultdict(list)   # مشاكل بتتبلّغ بس
    loaded  = {}

    # قراءة كل الملفات الأول — خريطة الأشكال القانونية لازم تتبني من
    # **كل** البيانات مع بعض، مش ملف ملف، وإلا كل ملف هيختار شكل مختلف.
    for path in files:
        if not os.path.exists(path):
            print(f"  ⚠️  ملف مش موجود، هيتخطى: {path}")
            continue
        with open(path, encoding="utf-8") as f:
            loaded[path] = json.load(f)

    all_records = [r for p in loaded.values() for r in p.get("visits", [])]
    geo_canon = build_geo_canon(all_records)

    for path, payload in loaded.items():
        for rec in payload.get("visits", []):
            vid = rec.get("id", "?")

            # ① لمّ الأشكال على أصحّ إملاء
            if "geo" in only:
                for fld in ("city", "district"):
                    old = str(rec.get(fld) or "")
                    if not old.strip():
                        continue
                    new = geo_canon.get(normalize_ar(old), clean_text(old))
                    if new != old:
                        changes["geo"].append((path, vid, fld, old, new))
                        rec[fld] = new

            # ② فصل الأرقام الملزوقة
            if "phone" in only:
                raw = str(rec.get("phone") or "")
                digits = re.sub(r"\D", "", raw)
                if len(digits) > 13:
                    pair = split_glued_phone(raw)
                    if pair:
                        first, second = pair
                        changes["phone"].append((path, vid, "phone", raw, first))
                        rec["phone"] = first
                        # الرقم التاني مايتـرمىش — بيتحفظ في الملاحظات
                        note = str(rec.get("notes") or "").strip()
                        tag = f"رقم إضافي: {second}"
                        if tag not in note:
                            rec["notes"] = (note + ("\n" if note else "") + tag)
                    else:
                        reports["phone_odd"].append((path, vid, raw, rec.get("name", "")))

            # ③ التواريخ الفاسدة — إبلاغ بس
            if "date" in only and not valid_date(rec.get("visit_date")):
                reports["date"].append((path, vid, rec.get("visit_date"), rec.get("name", "")))

            # ④ التناقضات المالية — إبلاغ بس
            if "pay" in only:
                probs = payment_problems(rec)
                if probs:
                    reports["pay"].append((path, vid, rec.get("name", ""), " · ".join(probs)))

    return changes, reports, loaded


def main():
    ap = argparse.ArgumentParser(description="تنظيف بيانات Orange Lab HVMS")
    ap.add_argument("--apply", action="store_true", help="نفّذ التغييرات فعلياً (الافتراضي معاينة)")
    ap.add_argument("--only", default="geo,phone,date,pay", help="إصلاحات محددة بفاصلة")
    ap.add_argument("--files", nargs="*", default=DEFAULT_FILES)
    args = ap.parse_args()
    only = {x.strip() for x in args.only.split(",") if x.strip()}

    mode = "🔴 تنفيذ فعلي" if args.apply else "🔵 معاينة فقط (dry-run)"
    print("═" * 66)
    print(f"  تنظيف بيانات Orange Lab HVMS — {mode}")
    print(f"  الإصلاحات: {', '.join(sorted(only))}")
    print("═" * 66)

    changes, reports, loaded = repair(args.files, only, args.apply)

    # ── تقرير التغييرات ──
    if changes["geo"]:
        pairs = Counter((o, n) for _, _, _, o, n in changes["geo"])
        print(f"\n① توحيد الإملاء الجغرافي — {len(changes['geo'])} سجل\n")
        for (o, n), c in pairs.most_common():
            print(f"   {c:>4} × «{o}»  →  «{n}»")

    if changes["phone"]:
        print(f"\n② فصل الأرقام الملزوقة — {len(changes['phone'])} سجل")
        print("   (الرقم التاني بيتحفظ في الملاحظات، مش بيتشال)\n")
        for path, vid, _, old, new in changes["phone"][:12]:
            second = re.sub(r"\D", "", old)[11:]
            print(f"   {old}  →  {new}   + ملاحظة «رقم إضافي: {second}»")
        if len(changes["phone"]) > 12:
            print(f"   ... و{len(changes['phone'])-12} غيرهم")

    # ── تقرير المشاكل اللي محتاجة قرار بشري ──
    if reports["phone_odd"]:
        print(f"\n⚠️  أرقام طويلة بشكل غير مفهوم — {len(reports['phone_odd'])} (اتساب بلا تغيير)")
        for path, vid, raw, name in reports["phone_odd"][:8]:
            print(f"   {raw:<26} {name[:24]}")

    if reports["date"]:
        print(f"\n⚠️  تواريخ فاسدة — {len(reports['date'])} (محتاجة تصحيح يدوي)")
        for path, vid, d, name in reports["date"][:10]:
            print(f"   id={vid[:12]:<14} «{d}»  {name[:24]}")
        print("   ← صلّحهم من داخل البرنامج؛ التخمين هنا هيبقى نفس غلطة date.today()")

    if reports["pay"]:
        print(f"\n⚠️  تناقضات مالية — {len(reports['pay'])} (محتاجة مراجعة)")
        by = Counter(p.split("(")[0].strip() for _, _, _, p in reports["pay"])
        for k, c in by.most_common():
            print(f"   {c:>4} × {k}")
        print("\n   أول 8 سجلات:")
        for path, vid, name, p in reports["pay"][:8]:
            print(f"   id={vid[:12]:<14} {name[:20]:<22} {p[:44]}")
        print("   ← معظمهم بيانات تاريخية ناقصة. راجعهم قبل أي تقرير مالي.")

    total_changes = len(changes["geo"]) + len(changes["phone"])
    total_reports = sum(len(v) for v in reports.values())

    print("\n" + "═" * 66)
    print(f"  تغييرات جاهزة للتطبيق : {total_changes}")
    print(f"  مشاكل للإبلاغ فقط     : {total_reports}")
    print("═" * 66)

    if not args.apply:
        print("\n🔵 مافيش حاجة اتكتبت. للتنفيذ:  python3 repair_data.py --apply")
        return 0

    if total_changes == 0:
        print("\n✅ مفيش تغييرات محتاجة تطبيق.")
        return 0

    # ── backup إجباري قبل أي كتابة ──
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    bdir = f"backup_before_repair_{stamp}"
    os.makedirs(bdir, exist_ok=True)
    for path in loaded:
        dst = os.path.join(bdir, path.replace("/", "_"))
        shutil.copy2(path, dst)
    print(f"\n💾 backup اتعمل في: {bdir}/  ({len(loaded)} ملف)")

    for path, payload in loaded.items():
        payload["total"] = len(payload.get("visits", []))
        payload["repaired_at"] = datetime.now().isoformat()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        print(f"   ✅ اتكتب: {path}")

    print(f"\n✅ تم تطبيق {total_changes} تغيير.")
    print("\n⚠️  الخطوة الجاية مهمة:")
    print("   الملفات اتغيّرت **محلياً بس**. عشان البرنامج ياخدها:")
    print("     1. git add -A && git commit -m 'data: repair historical records'")
    print("     2. git push")
    print("     3. من البرنامج: «💾 نسخ احتياطي واسترجاع» → استرجاع من JSON")
    print(f"\n   للتراجع:  cp {bdir}/* . (وارجّع أسماء الملفات لأصلها)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
