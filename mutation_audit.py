#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
mutation_audit.py — اختبار الطفرات الشامل

بيرجّع كل إصلاح واحد واحد للحالة القديمة (البايظة) ويشغّل كل الاختبارات.
لو الاختبارات **ماسكتش** الطفرة، يبقى الإصلاح ده مالوش شبكة أمان — أي حد
يعدّل الكود بكرة ممكن يرجّع البق من غير ما حد يعرف.

ده المقياس الحقيقي لقيمة الـ test suite: مش عدد الاختبارات، لكن
كام بق تقدر تمسكه.

التشغيل:  python3 mutation_audit.py
"""
import subprocess, shutil, sys, os, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))


# (اسم الطفرة، الملف، النص الصح، النص البايظ القديم)
MUTATIONS = [
 # ── الطبقة النقية ────────────────────────────────────────────────────────
 ("M01 _lab_price يرجع لأول تطابق", "core.py",
  '''    m = re_module.findall(r'(\\d[\\d,]*)\\s*جنيه', str(entry or ""))
    if not m:
        return 0
    try:
        return int(m[-1].replace(",", ""))
    except ValueError:
        return 0''',
  '''    m = re_module.search(r'(\\d+)\\s*جنيه', str(entry or ""))
    return int(m.group(1)) if m else 0'''),

 ("M02 _month_of بالفحص الضعيف", "core.py",
  '''    d = str(rec.get("visit_date") or "").strip()
    try:
        date.fromisoformat(d[:10])
        return d[:7]
    except Exception:
        return "0000-00"''',
  '''    d = str(rec.get("visit_date") or "").strip()
    return d[:7] if len(d) >= 7 and d[4] == "-" else "0000-00"'''),

 ("M03 _safe_url يسمح بأي رابط", "core.py",
  '''    return _esc(u) if u.lower().startswith(("http://", "https://")) else ""''',
  '''    return _esc(u)'''),

 ("M04 _esc مايهربش HTML", "core.py",
  '''    return (str(txt or "").strip().replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;"))''',
  '''    return str(txt or "").strip()'''),

 ("M05 format_money بيرجّع الكسور", "core.py",
  '''        return f"{val:,.0f} جنيه"''',
  '''        return f"{val:,} جنيه"'''),

 ("M06 format_date_ar بترمي على غير النص", "core.py",
  '''    try:
        if not (1 <= d.month <= 12):
            return str(d)
        return f"{d.day} {MONTHS_AR[d.month - 1]} {d.year}"
    except Exception:
        return str(d)''',
  '''    return f"{d.day} {MONTHS_AR[d.month - 1]} {d.year}"'''),

 ("M07 canonicalize_geo بيشوّه الإملاء", "core.py",
  '''    return _GEO_CANON.get(normalize_ar(v), v)''',
  '''    return normalize_ar(v)'''),

 ("M08 _payment_problems مابيمنعش «مدفوع» بصفر", "core.py",
  '''    if st_pay == "مدفوع" and total > 0 and paid <= 0:''',
  '''    if False and st_pay == "مدفوع" and total > 0 and paid <= 0:'''),

 ("M09 revenue بيشمل الملغية", "core.py",
  '''    return isinstance(v, dict) and str(v.get("status") or "") != "ملغية"''',
  '''    return isinstance(v, dict)'''),

 ("M10 _hash_records بيرمي على مدخل بايظ", "core.py",
  '''    rows = [r for r in (recs or []) if isinstance(r, dict)] if isinstance(recs, (list, tuple)) else []''',
  '''    rows = recs'''),

 ("M11 extra_persons_total بيرمي على None", "core.py",
  '''    return sum(_lab_price(l) for p in _valid_persons(persons) for l in (p.get("labs") or []))''',
  '''    return sum(_lab_price(l) for p in (persons or []) for l in p.get("labs", []))'''),

 # ── قواعد الاستيراد ──────────────────────────────────────────────────────
 ("M12 التاريخ الفاسد يبقى تاريخ النهاردة", "import_rules.py",
  '''        except Exception:
            # احتياطي بلا pandas — عشان الوحدة تفضل قابلة للاختبار لوحدها
            for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"):
                try:
                    iso = datetime.strptime(txt[:10], fmt).strftime("%Y-%m-%d")
                    break
                except Exception:
                    continue
            else:
                return None, f"تاريخ غير صالح ({txt[:24]})"''',
  '''        except Exception:
            from datetime import date as _d
            return _d.today().isoformat(), None'''),

 ("M13 ترتيب اليوم/الشهر أمريكي", "import_rules.py",
  '''            parsed = pd.to_datetime(raw, errors="raise", dayfirst=True)''',
  '''            parsed = pd.to_datetime(raw, errors="raise")'''),

 ("M14 مفيش حارس مدى للتاريخ", "import_rules.py",
  '''    if not (DATE_MIN <= iso <= DATE_MAX):
        return None, f"تاريخ خارج المدى ({iso})"''',
  '''    if False:
        return None, ""'''),

 ("M15 الأرقام السالبة تعدّي", "import_rules.py",
  '''                if record[key] < 0:
                    notes.append(f"{key} سالب ({record[key]:g})")
                    record[key] = 0''',
  '''                pass'''),

 ("M16 القيم التصنيفية مش مقصورة", "import_rules.py",
  '''            notes.append(f"{fld}=«{val[:20]}» مش من القيم المسموحة → {default}")
            record[fld] = default''',
  '''            pass'''),

 ("M17 fill_insert_defaults بتمسح البيانات", "import_rules.py",
  '''def validate_row(record, opts=None):''',
  '''def validate_row(record, opts=None, _unused=None):
    """طفرة: بتملا الحقول الاختيارية دايمًا → بتمسح بيانات محفوظة"""
    record = dict(record or {})
    for _k in OPTIONAL_TEXT:
        record.setdefault(_k, "")
    return _validate_row_real(record, opts)


def _validate_row_real(record, opts=None):'''),

 # ── التليفونات ───────────────────────────────────────────────────────────
 ("M18 wa_digits مابينظّفش الأرقام العربية", "phone_utils.py",
  '''    p = clean_digits(p)              # ← أرقام إنجليزية نضيفة بس''',
  '''    p = p.replace(" ", "").replace("-", "")'''),

 # ── المصادقة ─────────────────────────────────────────────────────────────
 ("M19 الفروع تدخل بإيميل لوحده", "app.py",
  '''            st.session_state.login_email   = email_clean
            st.session_state.need_password = True
            st.rerun()''',
  '''            if email_clean.lower() == ADMIN_EMAIL.lower():
                st.session_state.login_email   = email_clean
                st.session_state.need_password = True
            else:
                _grant(email_clean)
            st.rerun()'''),



 ("M22 مفيش تحديد محاولات", "app.py",
  '''                if _fails >= PW_MAX_ATTEMPTS:''',
  '''                if False:'''),

 # ── توكن الجهاز ──────────────────────────────────────────────────────────
 ("M23 التوكن يرجع للـURL", "device_auth.py",
  '''        if _flag(st, "allow_url_token", False):
            st.query_params[TOKEN_PARAM] = tok
        else:
            st.query_params.pop(TOKEN_PARAM, None)''',
  '''        st.query_params[TOKEN_PARAM] = tok'''),

 ("M24 التوكن مايتشالش من الـURL", "device_auth.py",
  '''                st.query_params.pop(TOKEN_PARAM, None)
            except Exception:
                pass
        return {"email": allowed_map[email]''',
  '''                pass
            except Exception:
                pass
        return {"email": allowed_map[email]'''),

 ("M25 token_version مش بيتفحص", "device_auth.py",
  '''        if int(data.get("v", DEFAULT_TOKEN_VERSION)) != token_version(st):
            return None''',
  '''        if False:
            return None'''),

 # ── حُرّاس المزامنة ───────────────────────────────────────────────────────
 ("M27 حارس القاعدة الفاضية اتشال", "sync_guards.py",
  """    if local_total == 0:
        return SaveDecision(
            False,
            "اترفض الحفظ: قاعدة البيانات المحلية فاضية — كان هيمسح كل اللي على GitHub",
            "empty_db")""",
  """    if False:
        pass"""),

 ("M28 حارس الانكماش اتشال", "sync_guards.py",
  """    if local_total < remote_total and not allow_shrink_once:""",
  """    if False:"""),

 ("M29 الكتابة على أعمى مسموحة", "sync_guards.py",
  """    if remote_total is None:
        return SaveDecision(False, "اترفض الحفظ: تعذّر التحقق من GitHub", "unverified")""",
  """    if remote_total is None:
        remote_total = 0"""),

 ("M30 verify_before_prune مابيتحققش", "sync_guards.py",
  """    missing = set(archived_ids) - set(archive_file_ids)""",
  """    missing = set()"""),

 ("M31 الشهر اللي ماتغيرش بيترفع", "sync_guards.py",
  """        if prev_hash.get(m) == hash_fn(recs):
            continue                    # ماتغيرش""",
  """        if False:
            continue"""),

 ("M32 CAS اتشال — الكتابة المتزامنة", "app.py",
  """        sha = expected_sha if expected_sha is not None else _get_github_file_sha(path)""",
  """        sha = _get_github_file_sha(path)"""),

 ("M33 حارس التعارض اتشال", "app.py",
  """    if USE_CAS and _GH_STATE.get("conflict"):
        return _block(""",
  """    if False:
        return _block("""),

 ("M34 SHA بيتشال بعد 409", "app.py",
  """            _GH_STATE["conflict"] = path
            _GH_STATE["last_error"] = (
                f"تعارض على {path}: فرع تاني عدّل نفس الملف. "
                "اضغط «تحديث من GitHub ودمج» قبل ما تكمّل.")
            return False""",
  """            _GH_STATE["conflict"] = path
            _GH_STATE.setdefault("file_sha", {}).pop(path, None)
            return False"""),

 ("M35 تعريف محلي بيدوس على المستورد", "app.py",
  """def _official_price_for(entry):""",
  """def _payment_problems(rec):
    return []   # طفرة: نسخة محلية فاضية بتدوس على المستوردة من core


def _official_price_for(entry):"""),

 ("M36 نطاق الفرع اتشال", "permissions.py",
  """    if scope is None:
        return True
    if not isinstance(record, dict):
        return False""",
  """    return True
    if not isinstance(record, dict):
        return False"""),

 ("M37 الفرع يقدر يتخطّى الفلتر", "permissions.py",
  """    elif scope is not None:
        f["branch"] = scope           # يدوس على أي محاولة تخطّي""",
  """    elif scope is not None and not f.get("branch"):
        f["branch"] = scope"""),

 ("M38 device_secret يرجع fallback", "device_auth.py",
  """        return str(st.secrets.get("device_secret", "") or "")""",
  """        return str(st.secrets.get("device_secret", "")
                   or st.secrets.get("admin_password", "") or "")"""),

 ("M20 fallback للباسورد الافتراضي", "app.py",
  '            if not _sec_key:\n                _sec_key = _keys[0]',
  '            if not _sec_key:\n                _sec_key, correct_password = _keys[0], "123456"'),

 ("M21 الفرع يقبل سر فرع تاني", "app.py",
  '                _keys = ["diamond_password", "branch_password"]',
  '                _keys = ["lacite_password", "diamond_password", "branch_password"]'),

 # ── الصلاحيات ────────────────────────────────────────────────────────────
 ("M26 صفحة new من غير حارس", "app.py",
  '''elif st.session_state.page == "new":
    # ★ حارس صلاحية — كان ناقص. الصفحة دي كانت مفتوحة لأي إيميل في
    #   allowed_emails حتى لو مالوش دور معروف (user_type == "other").
    #   الاكتشاف جه من تنفيذ الصفحات فعليًا، مش من قراءة الكود.
    if st.session_state.user_type not in ["admin", "diamond", "lacite"]:
        st.info("ليس لديك صلاحية عرض بيانات الزيارات."); st.stop()''',
  '''elif st.session_state.page == "new":'''),
]

SUITES = ["tests_pure.py", "tests_guards.py", "tests_permissions.py", "tests_import.py",
          "tests_auth.py", "tests_device.py", "tests_pages.py"]


def run_suites(workdir):
    """بيرجّع قائمة الـ suites اللي فشلت — بتتنفّذ في نسخة معزولة."""
    failed = []
    for suite in SUITES:
        r = subprocess.run([sys.executable, suite], capture_output=True,
                           text=True, cwd=workdir)
        if r.returncode != 0:
            failed.append(suite.replace("tests_", "").replace(".py", ""))
    return failed


def main():
    print("═" * 70)
    print("  اختبار الطفرات — هل الاختبارات بتمسك رجوع كل إصلاح؟")
    print("═" * 70)
    print(f"\n  {len(MUTATIONS)} طفرة × {len(SUITES)} suite")

    # ★★ الطفرات بتتعمل في **نسخة معزولة** مش على الكود نفسه.
    #    النسخة الأولى كانت بتعدّل الملفات في مكانها وترجّعها في finally —
    #    وده معناه إن أي مقاطعة (Ctrl+C · timeout · انقطاع) بتسيب الكود
    #    في حالة الطفرة. وده حصل فعلًا: مستخدم قاطع الأداة فاتساب core.py
    #    بـ _month_of القديم، وبعدها كل الاختبارات بتفشل من غير سبب واضح.
    #    دلوقتي: نسخة مؤقتة، والأصل مايتلمسش خالص.
    workdir = tempfile.mkdtemp(prefix="mutation_")
    try:
        for item in os.listdir(HERE):
            if item.startswith((".", "__")) or item.endswith(".zip"):
                continue
            src = os.path.join(HERE, item)
            dst = os.path.join(workdir, item)
            if os.path.isdir(src):
                shutil.copytree(src, dst, dirs_exist_ok=True)
            else:
                shutil.copy2(src, dst)
        print(f"  نسخة معزولة: {workdir}\n")
        return _run(workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def _run(HERE):
    base = run_suites(HERE)
    if base:
        print(f"  ❌ الاختبارات فاشلة قبل أي طفرة: {base}")
        print("     ⇒ صلّحها الأول — نتيجة الطفرات مالهاش معنى من غير خط أساس نضيف")
        return 1
    print("  ✅ الخط الأساسي نضيف — كل الـ suites بتعدّي\n")
    print("  " + "─" * 66)

    caught = escaped = skipped = 0
    escaped_list = []
    for name, fname, good, bad in MUTATIONS:
        path = os.path.join(HERE, fname)
        src = open(path, encoding="utf-8").read()
        if good not in src:
            print(f"  ⚠️  {name:<44} الكود مالقيش")
            skipped += 1
            continue
        backup = src
        open(path, "w", encoding="utf-8").write(src.replace(good, bad, 1))
        try:
            failed = run_suites(HERE)
        finally:
            open(path, "w", encoding="utf-8").write(backup)
        if failed:
            print(f"  ✅ {name:<44} اتمسك ← {', '.join(failed)}")
            caught += 1
        else:
            print(f"  ❌ {name:<44} **عدّى**")
            escaped += 1
            escaped_list.append(name)

    print("  " + "─" * 66)
    total = caught + escaped
    pct = (caught * 100 // total) if total else 0
    print(f"\n  اتمسك: {caught}/{total} ({pct}%)"
          + (f" · متخطّى: {skipped}" if skipped else ""))
    if escaped_list:
        print("\n  ⚠️ طفرات عدّت من غير ما حد يمسكها:")
        for e in escaped_list:
            print(f"     • {e}")
        print("\n  ⇒ الإصلاحات دي مالهاش شبكة أمان — أي تعديل بكرة ممكن يرجّعها.")
    print("\n" + "═" * 70)
    return 0 if not escaped_list else 1


if __name__ == "__main__":
    sys.exit(main())
