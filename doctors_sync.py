# -*- coding: utf-8 -*-
"""
doctors_sync.py — منطق حفظ الأطباء الدائم (قرار بحت: مفيش شبكة ولا داتابيز ولا Streamlit)

المشكلة: جدول الأطباء كان موجود في الـ SQLite المحلي بس. الزيارات بتتزامن مع GitHub،
لكن الأطباء لأ — فأي دكتور جديد بيتحذف مع أول إعادة تشغيل للسيرفر، و _ensure_default_doctors
بتزرع الـ 8 الأصليين من جديد.

الحل: ملف doctors.json على GitHub. الوحدة دي بتحدد «إيه اللي يتكتب» و«إيه اللي يتطبّق»:

  merge_for_push(remote, local, changed_ids)
      الأساس هو اللي على GitHub، ونطبّق عليه **بس** الأطباء اللي اتغيّروا دلوقتي.
      ده بيمنع إن سيرفر قديم يدوس على تعديل سيرفر تاني، وبيضمن إن الملف عمره ما يقل
      (مفيش حذف في النظام — الإيقاف active=0).

  plan_pull(local, remote)
      وقت الإقلاع: إيه اللي نعمله في الجدول المحلي علشان يطابق GitHub. بنطابق بالـ id
      الأول، وبعدين بالاسم (لأن الـ 8 الافتراضيين بيتزرعوا بـ id عشوائي جديد في كل كونتينر)،
      ولو اتطابقوا بالاسم بناخد id اللي على GitHub عشان الأطباء مايتكررّوش.
"""
import re

FIELDS = ("id", "name", "phone", "branch", "commission_pct",
          "transport_eligible", "active", "created_at")


def norm_name(name):
    """اسم مطبّع للمقارنة: مسافات مكررة + حروف صغيرة + همزات الألف."""
    s = re.sub(r"\s+", " ", str(name or "")).strip().lower()
    return s.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي", "ة": "ه"}))


def clean_row(row):
    """صف دكتور بالحقول المعروفة بس وبأنواع سليمة. None لو مفيش اسم/id."""
    if not isinstance(row, dict):
        return None
    name = str(row.get("name") or "").strip()
    doc_id = str(row.get("id") or "").strip()
    if not name or not doc_id:
        return None
    try:
        comm = float(row.get("commission_pct", 5.0))
    except (TypeError, ValueError):
        comm = 5.0
    return {
        "id": doc_id,
        "name": name,
        "phone": str(row.get("phone") or "").strip(),
        "branch": str(row.get("branch") or "").strip(),
        "commission_pct": comm,
        "transport_eligible": 1 if str(row.get("transport_eligible") or 0) in ("1", "True", "true") else 0,
        "active": 0 if str(row.get("active", 1)) in ("0", "False", "false") else 1,
        "created_at": str(row.get("created_at") or ""),
    }


def clean_rows(rows):
    out = []
    for r in (rows or []):
        c = clean_row(r)
        if c:
            out.append(c)
    return out


def merge_for_push(remote_rows, local_rows, changed_ids=None):
    """
    اللي هيتكتب على GitHub.
      changed_ids=None  → أول مرة (مفيش ملف): كل الأطباء المحليين.
      changed_ids=[...] → الأساس = الملف الحالي + نطبّق الأطباء المتغيّرين بس.
    الناتج أبدًا مايقلّش عن اللي على GitHub (مفيش حذف).
    """
    remote = clean_rows(remote_rows)
    local = clean_rows(local_rows)
    if not remote:                              # أول رفع: كل اللي عندنا
        return sorted(local, key=lambda r: norm_name(r["name"]))

    by_id = {r["id"]: dict(r) for r in remote}
    by_name = {norm_name(r["name"]): r["id"] for r in remote}
    wanted = set(changed_ids or [])
    for row in local:
        if row["id"] not in wanted:
            continue
        target = row["id"] if row["id"] in by_id else by_name.get(norm_name(row["name"]))
        if target:                              # تعديل دكتور موجود
            keep_created = by_id[target].get("created_at") or row.get("created_at", "")
            by_id[target] = {**row, "id": target, "created_at": keep_created}
        else:                                   # دكتور جديد
            by_id[row["id"]] = dict(row)
            by_name[norm_name(row["name"])] = row["id"]
    return sorted(by_id.values(), key=lambda r: norm_name(r["name"]))


def plan_pull(local_rows, remote_rows):
    """
    خطة تطبيق GitHub على الجدول المحلي:
        ("update", local_id, row)   ← row فيها id الجديد (ممكن يختلف عن local_id)
        ("insert", None,     row)
    الأطباء الموجودين محليًا بس (مش على GitHub) بيتساب كما هم.
    """
    local = clean_rows(local_rows)
    remote = clean_rows(remote_rows)
    local_by_id = {r["id"]: r for r in local}
    local_by_name = {}
    for r in local:
        local_by_name.setdefault(norm_name(r["name"]), r)

    ops, used = [], set()
    for rem in remote:
        match = local_by_id.get(rem["id"])
        if match is None:
            cand = local_by_name.get(norm_name(rem["name"]))
            if cand is not None and cand["id"] not in used:
                match = cand
        if match is not None:
            used.add(match["id"])
            if any(match.get(f) != rem.get(f) for f in FIELDS):
                ops.append(("update", match["id"], rem))
        else:
            ops.append(("insert", None, rem))
    return ops


def find_by_name(rows, name):
    """أول دكتور بنفس الاسم (مطبّع) أو None."""
    k = norm_name(name)
    for r in rows or []:
        if norm_name(r.get("name")) == k:
            return r
    return None
