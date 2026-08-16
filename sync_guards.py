# -*- coding: utf-8 -*-
"""
sync_guards.py — منطق قرار حُرّاس المزامنة

الحُرّاس دول أخطر كود في النظام: هما اللي بيمنعوا إن قاعدة بيانات محلية
بايظة تمسح 1,030 سجل على GitHub. ومع ذلك كانوا **مالهمش ولا اختبار مباشر** —
اتحققنا منهم بشكل غير مباشر بس (اتساق ملفات البيانات).

المشكلة إنهم كانوا مدفونين جوّه `save_to_github_json()` وسط نداءات شبكة،
يعني اختبارهم كان بيحتاج GitHub حقيقي. الوحدة دي بتفصل **القرار** عن
**التنفيذ**: دخل حالة، اطلع بقرار. مفيش شبكة، مفيش داتابيز، مفيش Streamlit.

الحُرّاس:
  ① قاعدة محلية فاضية        → ممنوع الكتابة (كان هيمسح كل حاجة)
  ② المحلي أقل من البعيد      → ممنوع (soft delete يعني العدد مايقلش)
  ③ تعذّر التحقق من GitHub    → ممنوع (الرفض أأمن من الكتابة على أعمى)
  ④ شهر قلّ/فضي              → مسموح **بس** لو الحارس ② عدّى

الاستثناء الوحيد لـ ②: `allow_shrink_once` من `archive_and_prune()` —
إذن لمرة واحدة بعد أرشفة متحقَّق منها.
"""
from dataclasses import dataclass


@dataclass
class SaveDecision:
    """قرار الحارس: يرفع ولا يرفض، وليه."""
    allowed: bool
    reason: str = ""
    guard: str = ""          # اسم الحارس اللي رفض

    def __bool__(self):
        return self.allowed


def check_save_allowed(local_total, remote_total, has_credentials=True,
                       allow_shrink_once=False):
    """
    القرار الأساسي: هل الرفع مسموح؟

    local_total       عدد الصفوف غير المؤرشفة في الـ DB المحلي
    remote_total      آخر عدد معروف على GitHub (None = مقدرناش نتحقق)
    has_credentials   github_token و github_repo موجودين
    allow_shrink_once إذن لمرة واحدة بالانكماش (من archive_and_prune)
    """
    if not has_credentials:
        return SaveDecision(False, "github_token أو github_repo مش موجودين في Secrets",
                            "credentials")

    # ── الحارس ①: ملف فاضي = ممنوع ──
    if local_total == 0:
        return SaveDecision(
            False,
            "اترفض الحفظ: قاعدة البيانات المحلية فاضية — كان هيمسح كل اللي على GitHub",
            "empty_db")

    # ── الحارس ③: مقدرناش نتحقق ──
    if remote_total is None:
        return SaveDecision(False, "اترفض الحفظ: تعذّر التحقق من GitHub", "unverified")

    # ── الحارس ②: انكماش ──
    if local_total < remote_total and not allow_shrink_once:
        return SaveDecision(
            False,
            f"اترفض الحفظ: المحلي فيه {local_total} زيارة وGitHub فيه {remote_total} — "
            f"استرجع من GitHub الأول قبل أي تعديل",
            "shrink")

    return SaveDecision(True)


def months_to_write(buckets, prev_hash, prev_totals, hash_fn):
    """
    بيرجّع (الشهور اللي محتاجة رفع، الشهور اللي هتتفضّى).

    الشهر اللي بصمته ماتغيرتش **مايترفعش** — ده اللي بيخلّي حفظ زيارة واحدة
    يعمل commit واحد بدل ما يعيد كتابة كل الشهور.

    الشهر اللي كان على GitHub وما بقاش ليه صفوف محليًا بيتفضّى (مش بيتساب)،
    لأن الصفوف اتنقلت لشهر تاني — والحارس ② فوق ضامن إنها ما ضاعتش.
    """
    work = dict(buckets)
    for m in prev_totals:
        work.setdefault(m, [])          # شهر اتفضّى
    changed, emptied = [], []
    for m in sorted(work):
        recs = work[m]
        if prev_hash.get(m) == hash_fn(recs):
            continue                    # ماتغيرش
        changed.append(m)
        if not recs and prev_totals.get(m):
            emptied.append(m)
    return changed, emptied


def verify_before_prune(archived_ids, archive_file_ids):
    """
    قبل ما نشيل صفوف من الملف الحي، نتأكد إنها وصلت ملف الأرشيف فعلًا.

    ده حارس `archive_and_prune`: من غيره، فشل في رفع ملف الأرشيف + نجاح في
    تفريغ الملف الحي = **ضياع البيانات نهائيًا**.
    """
    missing = set(archived_ids) - set(archive_file_ids)
    if missing:
        return SaveDecision(
            False,
            f"اترفض التقليم: {len(missing)} سجل مش موجود في ملف الأرشيف",
            "prune_verify")
    return SaveDecision(True)
