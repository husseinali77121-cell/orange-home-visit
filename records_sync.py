# -*- coding: utf-8 -*-
"""
records_sync.py — حفظ المتابعات وسجل النشاط على GitHub (قرار بحت: مفيش شبكة ولا داتابيز)

المشكلة: جدولين follow_ups و audit_log كانوا في الـ SQLite المحلي بس، فبيتمسحوا مع كل
sleep أو إعادة نشر للبرنامج.

الحل (نفس فكرة doctors.json بالظبط — ملفات منفصلة، معزولة عن حفظ الزيارات):
  followups.json        — كل المتابعات (عددها صغير)
  audit/YYYY-MM.json    — سجل النشاط، ملف لكل شهر

القاعدة الذهبية: الرفع **دايمًا** = اللي على GitHub + اللي عندنا (دمج). عمر الملف ما يقل،
فكونتينر جديد أو جهاز تاني عمره ما يمسح متابعة أو سطر سجل كتبه جهاز تاني.
"""

FU_FIELDS = ("id", "visit_id", "client_name", "client_phone", "follow_up_date",
             "reason", "done", "created_at", "created_by")
AUDIT_FIELDS = ("user_email", "action", "table_name", "record_id", "field_name",
                "old_value", "new_value", "details", "timestamp")


def _s(v):
    return "" if v is None else str(v)


# ══════════════════════════════════════════════════════════════════════════════
# المتابعات
# ══════════════════════════════════════════════════════════════════════════════
def clean_fu(row):
    """صف متابعة بالحقول المعروفة بس. None لو مفيش id أو تاريخ."""
    if not isinstance(row, dict):
        return None
    fid = _s(row.get("id")).strip()
    fdate = _s(row.get("follow_up_date")).strip()
    if not fid or not fdate:
        return None
    out = {k: _s(row.get(k)) for k in FU_FIELDS}
    out["id"], out["follow_up_date"] = fid, fdate
    out["done"] = 1 if _s(row.get("done")) in ("1", "True", "true") else 0
    return out


def merge_followups(remote_rows, local_rows):
    """
    اتحاد بالـ id. نفس المتابعة في الاتنين: «تمت» بتكسب (متابعة اتقفلت عمرها ما ترجع
    مفتوحة)، وأي خانة فاضية في نسخة بتتملا من التانية. الناتج مرتّب بالتاريخ ثم الـ id.
    """
    by_id = {}
    for src in (remote_rows or [], local_rows or []):
        for r in src:
            c = clean_fu(r)
            if not c:
                continue
            cur = by_id.get(c["id"])
            if cur is None:
                by_id[c["id"]] = c
                continue
            merged = dict(cur)
            for k in FU_FIELDS:
                if not _s(merged.get(k)).strip() and _s(c.get(k)).strip():
                    merged[k] = c[k]
            merged["done"] = max(int(cur["done"]), int(c["done"]))
            by_id[c["id"]] = merged
    return sorted(by_id.values(), key=lambda r: (r["follow_up_date"], r["id"]))


def plan_fu_pull(local_rows, remote_rows):
    """
    وقت الإقلاع: إيه اللي يتعمل في الجدول المحلي.
    Returns (inserts: [row], mark_done: [id]) — مفيش حذف ولا فتح متابعة مقفولة.
    """
    local = {c["id"]: c for c in (clean_fu(r) for r in (local_rows or [])) if c}
    inserts, mark_done = [], []
    for r in remote_rows or []:
        c = clean_fu(r)
        if not c:
            continue
        cur = local.get(c["id"])
        if cur is None:
            inserts.append(c)
            local[c["id"]] = c
        elif c["done"] == 1 and cur["done"] == 0:
            mark_done.append(c["id"])
    return inserts, mark_done


def fu_differs(remote_rows, merged_rows):
    """محتاجين نرفع؟ (الدمج زوّد متابعة أو قفل واحدة) — عشان مانعملش commit فاضي."""
    a = {c["id"]: c["done"] for c in (clean_fu(r) for r in (remote_rows or [])) if c}
    b = {c["id"]: c["done"] for c in (clean_fu(r) for r in (merged_rows or [])) if c}
    return a != b


# ══════════════════════════════════════════════════════════════════════════════
# سجل النشاط
# ══════════════════════════════════════════════════════════════════════════════
def clean_audit(row):
    if not isinstance(row, dict):
        return None
    ts = _s(row.get("timestamp")).strip()
    if len(ts) < 7:
        return None
    return {k: _s(row.get(k)) for k in AUDIT_FIELDS}


def audit_key(row):
    """بصمة سطر السجل (الـ id المحلي مش ثابت بين الأجهزة فمابنعتمدش عليه)."""
    return tuple(_s(row.get(k)) for k in AUDIT_FIELDS)


def audit_month(row):
    return _s(row.get("timestamp"))[:7]


def merge_audit(remote_rows, local_rows):
    """اتحاد من غير تكرار، مرتّب بالوقت."""
    seen, out = set(), []
    for src in (remote_rows or [], local_rows or []):
        for r in src:
            c = clean_audit(r)
            if not c:
                continue
            k = audit_key(c)
            if k in seen:
                continue
            seen.add(k)
            out.append(c)
    out.sort(key=lambda r: (r["timestamp"], r["action"], r["record_id"]))
    return out


def audit_missing_locally(local_rows, remote_rows):
    """سطور على GitHub مش موجودة محليًا (للإقلاع)."""
    have = {audit_key(c) for c in (clean_audit(r) for r in (local_rows or [])) if c}
    out = []
    for r in remote_rows or []:
        c = clean_audit(r)
        if c and audit_key(c) not in have:
            have.add(audit_key(c))
            out.append(c)
    return out


def prev_month(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"
