#!/usr/bin/env bash
# run_tests.sh — تشغيل كل الاختبارات دفعة واحدة
#
# ★ ملاحظة QA مهمة: ممنوع استخدام `cmd | tail` هنا.
#   الـ pipe بيخلّي الـ shell ياخد كود خروج آخر أمر في السلسلة (tail = صفر دايمًا)
#   بدل كود Python. `set -e` مابتمسكهاش. النتيجة: اختبار فاشل بيتقال عنه ✅.
#   الحل: كل suite بتتنفّذ لوحدها، كود الخروج بيتفحص، والمخرجات من ملف.
set -uo pipefail

RC=0
run_suite() {          # run_suite "الاسم" ملف.py
  local label="$1" file="$2" log
  log="$(mktemp)"
  echo "  ▸ $label"
  if python3 "$file" > "$log" 2>&1; then
    tail -2 "$log" | sed 's/^/    /'
  else
    echo "    ❌ فشل — التفاصيل:"
    grep -E "❌" "$log" | head -12 | sed 's/^/      /'
    tail -3 "$log" | sed 's/^/    /'
    RC=1
  fi
  rm -f "$log"
}

echo "════════════════════════════════════════════"
echo "  Orange Lab HVMS — تشغيل الاختبارات"
echo "════════════════════════════════════════════"
echo
echo "① فحص الصياغة"
if python3 - <<'PY'
import ast, sys
files = ["app.py","core.py","import_rules.py","sync_guards.py","device_auth.py",
         "phone_utils.py","lab_picker.py","login_theme.py","easter_eggs.py",
         "labs_price_list.py","tests_pure.py","tests_guards.py","tests_import.py",
         "tests_auth.py","tests_device.py","tests_pages.py","_stub_streamlit.py",
         "mutation_audit.py","repair_data.py"]
bad = 0
for f in files:
    try:
        ast.parse(open(f, encoding="utf-8").read())
    except SyntaxError as e:
        print(f"   ❌ {f}:{e.lineno} — {e.msg}"); bad += 1
print(f"   ✅ {len(files)-bad}/{len(files)} ملف سليم")
sys.exit(1 if bad else 0)
PY
then :; else RC=1; fi
echo
echo "② اختبارات الوحدة"
run_suite "الطبقة النقية"    tests_pure.py
run_suite "حُرّاس المزامنة"   tests_guards.py
run_suite "قواعد الاستيراد"  tests_import.py
run_suite "مسار المصادقة"    tests_auth.py
run_suite "توكن الجهاز"      tests_device.py
echo
echo "③ تنفيذ الصفحات فعليًا"
run_suite "44 حالة"          tests_pages.py
echo
echo "④ معاينة تنظيف البيانات (بلا كتابة)"
if python3 repair_data.py > /tmp/_repair.log 2>&1; then
  grep -E "تغييرات جاهزة|مشاكل للإبلاغ" /tmp/_repair.log | sed 's/^/  /'
else
  echo "  ❌ فشل"; RC=1
fi
echo
if [ "${SKIP_MUTATION:-0}" = "1" ]; then
  echo "⑤ اختبار الطفرات — ⏭ متخطّى (SKIP_MUTATION=1)"
else
  echo "⑤ اختبار الطفرات (بياخد دقايق)"
  if python3 mutation_audit.py > /tmp/_mut.log 2>&1; then
    grep -E "اتمسك:" /tmp/_mut.log | sed 's/^/  /'
  else
    echo "  ❌ فشل:"; grep -E "❌|عدّى" /tmp/_mut.log | head -8 | sed 's/^/    /'; RC=1
  fi
fi
echo
echo "════════════════════════════════════════════"
if [ "$RC" -eq 0 ]; then echo "  ✅ كل الاختبارات نجحت"; else echo "  ❌ فيه اختبارات فاشلة"; fi
echo "════════════════════════════════════════════"
exit "$RC"
