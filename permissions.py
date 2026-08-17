# -*- coding: utf-8 -*-
"""
permissions.py — صلاحيات على مستوى البيانات (Defense in Depth)

الحماية الحالية في الواجهة بس: كل صفحة بتفحص `user_type` وبتوقف اللي مالوش
صلاحية. وده شغال — بس بيفشل **بصمت** لو حد نسي الحارس في صفحة جديدة.

وده حصل فعلًا: تلات صفحات (`new` · `detail` · `client_profile`) اتشحنت من غير
حارس، والتحليل الثابت مشافهاش — اتكشفوا بس لما اتنفّذت الصفحات بمستخدم مالوش دور.

الوحدة دي بتنقل القاعدة لطبقة البيانات نفسها:

    admin    → كل الفروع
    diamond  → Diamond بس
    lacite   → La Cite بس
    غير كده  → ممنوع

كده لو الواجهة غلطت بكرة، البيانات نفسها بترفض. الواجهة بتبقى **طبقة راحة**
مش **طبقة أمان**.

⚠️ ملحوظة مهمة: الوحدة دي **مابتغيّرش** أي سلوك حالي — الواجهة بالفعل بتقصر
كل فرع على فرعه (الـselectbox معطّل للفروع). هي بس بتقفل الباب الخلفي.
"""

# نوع المستخدم → الفرع المسموح. None = كل الفروع.
_SCOPE = {
    "admin":   None,
    "diamond": "Diamond",
    "lacite":  "La Cite",
}


class PermissionDenied(Exception):
    """محاولة وصول لبيانات فرع تاني."""


def allowed_branch(user_type):
    """
    بيرجّع الفرع المسموح للمستخدم:
      None      → كل الفروع (أدمن)
      "Diamond" → فرع واحد
      False     → ممنوع تمامًا (مستخدم مالوش دور معروف)
    """
    ut = str(user_type or "").strip().lower()
    if ut in _SCOPE:
        return _SCOPE[ut]
    return False


def can_access(record, user_type):
    """
    هل المستخدم ده مسموح له يشوف/يعدّل السجل ده؟

    السجل بلا فرع (بيانات قديمة) بيتعامل كمسموح للأدمن بس — عشان مايختفيش
    من غير ما حد يعرف، ولا يتسرّب لفرع غلط.
    """
    scope = allowed_branch(user_type)
    if scope is False:
        return False
    if scope is None:
        return True
    if not isinstance(record, dict):
        return False
    branch = str(record.get("branch") or "").strip()
    if not branch:
        return False          # سجل بلا فرع → أدمن بس
    return branch == scope


def enforce(record, user_type, what="السجل"):
    """
    بيرجّع السجل لو مسموح، أو يرمي PermissionDenied.
    للاستخدام في نقاط الوصول المباشرة (فتح زيارة بالـid مثلاً).
    """
    if record is None:
        return None
    if not can_access(record, user_type):
        raise PermissionDenied(f"مالكش صلاحية على {what} ده")
    return record


def filter_visible(records, user_type):
    """بيصفّي قائمة سجلات على اللي المستخدم مسموح له يشوفه."""
    scope = allowed_branch(user_type)
    if scope is False:
        return []
    if scope is None:
        return list(records or [])
    return [r for r in (records or []) if can_access(r, user_type)]


def scope_filters(filters, user_type):
    """
    بيفرض فلتر الفرع على استعلام القائمة.

    الفرع **مايقدرش** يتخطّاه حتى لو بعت filters فيها فرع تاني — بنكتب فوقه.
    الأدمن بيفضل حر.
    """
    f = dict(filters or {})
    scope = allowed_branch(user_type)
    if scope is False:
        f["branch"] = "__DENY__"      # فرع مايطابقش أي سجل
    elif scope is not None:
        f["branch"] = scope           # يدوس على أي محاولة تخطّي
    return f
