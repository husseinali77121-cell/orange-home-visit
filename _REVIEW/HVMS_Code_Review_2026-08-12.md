# 🟠 Orange Lab HVMS — تقرير مراجعة الكود
**التاريخ:** 12 أغسطس 2026 · **النسخة المراجَعة:** `orange-home-visit-main` (schema v6)
**الحجم:** 7,935 سطر Python عبر 7 ملفات · `app.py` لوحده 4,705 سطر

---

## 📊 التقييم النهائي

| المحور | الدرجة | الملاحظة |
|---|---|---|
| **الوظائف والتغطية** | 9/10 | نظام كامل فعلًا: CRUD، دفع، متابعات، تقارير، أرشفة، واتساب، إكسيل |
| **حماية البيانات (Data safety)** | 8/10 | الحُرّاس الأربعة + verify-before-prune + rollback = شغل محترم جدًا |
| **الأمان (Security)** | **4/10** | مفيش باسورد للفروع، والتوكن في الـ URL. أضعف نقطة في البرنامج |
| **البنية (Architecture)** | 5/10 | monolith 4,705 سطر + JSON على GitHub كـ DB |
| **جودة الكود** | 6/10 | تعليقات ممتازة وتوثيق أسباب، بس 35 `except` صامت وتكرار كتير |
| **الـ UX** | 8/10 | عربي RTL نضيف، رسائل واضحة، بانرات تشخيص ممتازة |
| **الاختبارات والتوثيق** | 3/10 | صفر tests، README قديم مش بيعكس v5/v6 |

### **الإجمالي: 6.5 / 10**
> برنامج **شغّال وناجح فعليًا** (1,030 زيارة حقيقية متسجّلة، والملفات الثلاثة متطابقة 100%). بس فيه **4 أخطاء حرجة** واحد منهم بيمنع البرنامج من الاشتغال أصلًا على Python 3.11، و**فجوة أمنية** مش مناسبة لبرنامج فيه بيانات مرضى.

---

## ✅ الحاجات اللي شغالة صح (اتأكدت منها بنفسي)

فحصت اتساق ملفات البيانات فعليًا:

| فحص | النتيجة |
|---|---|
| `Visits.json` = 156 زيارة | ✅ الحقل `total` مطابق للعدد الفعلي |
| الملفات الشهرية (06/07/08) = 35+80+41 | ✅ = 156 بالظبط |
| IDs في legacy مش في monthly | ✅ **صفر** |
| IDs في monthly مش في legacy | ✅ **صفر** |
| فروق محتوى بين النسختين | ✅ **صفر** |
| زيارة في bucket شهر غلط | ✅ **صفر** |
| تداخل بين الأرشيف والملف الحي | ✅ **صفر** (874 مؤرشفة، 156 حية) |

**يعني منطق `_bucket_by_month` و`_hash_records` و`KEEP_LEGACY_MIRROR` شغالين بدقة.** ده أصعب جزء في النظام وهو سليم.

كمان: صفر أسماء غير معرّفة، صفر imports مش مستخدمة، صفر مفاتيح widgets مكررة.

---

## 🔴 أخطاء حرجة (لازم تتصلّح دلوقتي)

### C1 — SyntaxError على Python أقل من 3.12 · `app.py:4552`
```python
if st.button("✅ تم", key=f"cp_fu_{fu["id"]}", use_container_width=True):
#                              ^^^^^^^^^^ علامات تنصيص مزدوجة جوّه f-string
```
إعادة استخدام نفس نوع الـ quote جوّه f-string اتسمحت في **Python 3.12 بس** (PEP 701). على 3.11 أو أقل ده **SyntaxError وقت الاستيراد** — البرنامج مش هيفتح خالص، ولا حتى شاشة الدخول.

⚠️ **وده مش نظري:** `.devcontainer/devcontainer.json` مثبّت على `python:1-3.11-bookworm`، وبيشغّل `streamlit run app.py` أوتوماتيك. يعني **أي فتحة Codespaces دلوقتي = البرنامج ميّت**.

**الإصلاح (حرف واحد):**
```python
key=f"cp_fu_{fu['id']}"
```

---

### C2 — لوب لانهائي في استيراد الإكسيل · `app.py:2973-2980` و `4475-4482`
```python
uf = st.file_uploader("📥 استيراد من Excel", type=["xlsx"], key="import_excel")
if uf:
    count_imported, count_updated = import_from_excel(uf)
    st.success(...)
    st.rerun()          # ← الملف لسه في الـ uploader بعد الـ rerun
```
بعد `st.rerun()` الـ uploader لسه ماسك الملف → `if uf:` بترجع True → استيراد تاني → rerun → **للأبد**. وكل دورة بتعمل commits على GitHub بعدد الصفوف.

**الإصلاح:**
```python
if uf:
    _sig = hashlib.md5(uf.getvalue()).hexdigest()
    if st.session_state.get("_last_import_sig") != _sig:
        st.session_state["_last_import_sig"] = _sig
        ci, cu = import_from_excel(uf)
        st.success(...)
```

---

### C3 — `import_from_excel` بيرمي KeyError لو عمود ناقص · `app.py:2065-2149`
الحقول دي بتتحط في `record` **بس لو موجودة في ملف الإكسيل**:
`address` · `notes` · `selected_labs_text` · `location_link`

لكن `insert_visit()` و`update_visit()` بيقروها بـ `record["address"]` مش `.get()`:
```python
record["address"], record["location_link"], record["selected_labs_text"],
record["notes"], _xp,
```
→ ملف إكسيل من غير عمود «العنوان» = **KeyError** → الـ `except` الخارجي بيبلعه ويطلع `"حدث خطأ أثناء معالجة الملف"` ويرجّع `0, 0` — **مع إن الصفوف اللي قبل الخطأ اتحفظت فعلًا** (رسالة كدّابة + استيراد نص كامل).

**الإصلاح** — قبل حلقة الحفظ:
```python
for k in ("address","notes","selected_labs_text","location_link","age_unit"):
    record.setdefault(k, "")
```

---

### C4 — commit على GitHub لكل صف في الاستيراد/الاسترجاع
`insert_visit()` و`update_visit()` كل واحدة بتنادي `save_to_github_json()` في آخرها. وde بينادي:
`_get_github_file_sha()` (طلب) + PUT للشهر + `_get_github_file_sha()` + PUT للـ legacy = **~4 طلبات API لكل صف**.

استيراد 200 صف = **800 طلب API** + وقت انتظار بالدقايق + خطر rate limit (5,000/ساعة). ونفس المشكلة في `restore_from_json()`.

**الإصلاح:**
```python
def insert_visit(record, sync=True):
    ...
    if sync: save_to_github_json()
```
وفي الاستيراد: `insert_visit(rec, sync=False)` في اللوب، وبعد اللوب `save_to_github_json()` مرة واحدة.

---

## 🟠 مشاكل عالية الخطورة

### H1 — مفيش أي authentication حقيقي للفروع
```python
if email_clean not in ALLOWED_EMAILS:
    st.error("هذا البريد غير مصرح له بالدخول")
else:
    _grant(email_clean)     # ← دخول كامل. مفيش باسورد.
```
الأدمن بس هو اللي بيتطلب منه باسورد. أي حد يعرف `Orangelab511@gmail.com` (وده إيميل معلن على صفحة المعمل غالبًا) بيدخل ويشوف **أسماء وتليفونات وعناوين وتحاليل 1,030 مريض**.

ده مش مقبول لبرنامج فيه بيانات صحية. **أقل حاجة:** باسورد لكل فرع مخزّن كـ hash في Secrets:
```python
import hashlib
def _check_pw(email, pw):
    h = st.secrets.get("pw_hashes", {}).get(email.lower(), "")
    return bool(h) and hashlib.sha256(pw.encode()).hexdigest() == h
```
(والأحسن `bcrypt` لو تقدر تضيفها في requirements.)

---

### H2 — توكن الجهاز (90 يوم) بيتحط في الـ URL
`device_auth.remember_device()` بتحط التوكن في `?dev=...`. الـ URL ده:
- بيتحفظ في history المتصفح
- بيظهر في أي screenshot للشاشة
- بيتبعت لو حد شارك اللينك على واتساب («افتح البرنامج من هنا»)

وأي حد يفتح اللينك = **دخول تلقائي 90 يوم**. وللأدمن كمان، لأن `admin_auto_login` افتراضيًا `True` → بيتخطّى الباسورد بالكامل.

**الإصلاح:**
1. اقرأ التوكن من الـ URL مرة واحدة → اكتبه cookie → `st.query_params.pop("dev")` فورًا.
2. `admin_auto_login` يبقى `False` افتراضيًا.
3. قلّل مدة توكن الأدمن لـ 7 أيام بدل 90.

---

### H3 — مفتاح التوقيع = باسورد الأدمن
```python
def _raw_secret(st):
    for key in ("device_secret", "admin_password"):   # ← fallback خطير
```
لو `device_secret` مش موجود، الـ HMAC بيتوقّع بباسورد الأدمن. النتايج:
- تغيير الباسورد = كل الأجهزة الموثوقة بتتفصل فجأة (من غير ما حد يفهم ليه)
- سر واحد بيعمل شغلانتين مختلفتين

كمان **مفيش أي طريقة لإلغاء توكن معيّن** (موبايل ضاع مثلًا) غير إنك تغيّر السر وتفصل الكل.

**الإصلاح:** اعمل `device_secret` مستقل إجباري + ضيف `"v": TOKEN_VERSION` في الـ payload، وأي زيادة في `TOKEN_VERSION` في Secrets بتلغي كل التوكنات القديمة.

---

### H4 — `.gitignore` مفيهوش `secrets.toml`
```
# قاعدة البيانات
*.db
visits.db
visits_export.xlsx
```
`git add .` واحد بالغلط = **الـ GitHub token وباسورد الأدمن على الإنترنت للأبد** (حتى لو مسحتهم بعدين، فاضلين في الـ history).

**الإصلاح فورًا:**
```gitignore
.streamlit/secrets.toml
secrets.toml
*.xlsx
__pycache__/
```

---

### H5 — HTML injection في كل الكروت
`_esc()` موجودة ومكتوبة صح — بس مستخدمة في **7 مواضع بس** من أصل 95 موضع `unsafe_allow_html=True`.

الحقول دي بتتحقن خام:
| الملف/السطر | الحقل |
|---|---|
| `visit_card_html:2561` | `v["name"]` |
| `visit_list_row_html:2589-2593` | `name`, `phone`, `doctor_name`, `city/district` |
| `generate_visit_print_html:2398-2408` | `name`, `phone`, `address`, `doctor_name` |
| `detail:3794` | `v['name']` |
| `detail:2375` | `notes` |
| `client_profile:4509` | `cv['name']` |

اسم فيه `<` بيبوّظ التنسيق. اسم فيه `<img src=x onerror=...>` بيشغّل JavaScript في متصفح كل مستخدم.

**الإصلاح:** لفّ كل قيمة جاية من المستخدم بـ `_esc()`. مش تغيير كبير — بس لازم يتعمل على كل المواضع.

---

### H6 — `requirements.txt` بيطلب نسخة Streamlit أقدم من اللازم
```
streamlit>=1.32.0
```
بس الكود بيستخدم `st.context.cookies` (محتاجة **≥ 1.42**) و`st.context.ip_address` (أحدث كمان). على 1.32–1.41 الكوكي بتفشل **في صمت** → البرنامج بيقع على التوكن اللي في الـ URL — يعني بيرجع للطريق غير الآمن (H2) بالظبط.

**الإصلاح:** `streamlit>=1.45` وثبّت النسخ التانية:
```
streamlit>=1.45
pandas>=2.2
openpyxl>=3.1
plotly>=5.20
```

---

### H7 — `st.secrets.get()` من غير حماية
السطر 110 محمي بـ `try/except` — بس السطور دي **لأ**:
```python
GITHUB_TOKEN  = st.secrets.get("github_token", "")      # 346
GITHUB_REPO   = st.secrets.get("github_repo", "")       # 347
USE_MONTHLY_SYNC = st.secrets.get("use_monthly_sync", True)   # 365
GITHUB_ARCHIVE_DIR = st.secrets.get("github_archive_dir","archive")  # 387
```
لو مفيش `.streamlit/secrets.toml` خالص، Streamlit بيرمي `StreamlitSecretNotFoundError` (مش `KeyError` عشان `.get()` تمسكها) → **البرنامج بيقع وقت الاستيراد**. أي حد يـ clone الريبو ويجرّب يشغّله محليًا هيقابل ده.

**الإصلاح** — helper واحد واستخدمه في كل مكان:
```python
def _sec(key, default=None):
    try: return st.secrets.get(key, default)
    except Exception: return default
```

---

## 🟡 مشاكل متوسطة

### M1 — كل الأسعار بتظهر بـ `.0` في الكروت
`total_price` عمود `REAL` في SQLite → بيرجع `450.0`.
```python
f'<span class="visit-badge">{total:,} جنيه</span>'   # → "450.0 جنيه"
```
**المواضع:** `visit_card_html:2556`, `visit_list_row_html:2595`, `client_profile:4517`, `xp_sub:3649/3882`.
`format_money()` موجودة وبتعمل `:,.0f` صح — بس مش مستخدمة هنا.

### M2 — «السعر بعد الخصم» بيفضل صفر · `app.py:3694-3697`
```python
labs_price_before = st.number_input(..., value=auto_labs_total if auto_labs_total>0 else ...)
labs_price_after  = st.number_input(..., value=int(pf.get("labs_price_after",0) or 0))   # ← 0 للزيارة الجديدة
total_price = labs_price_after + transport_fee
```
الحساب الآلي بيدخل في «قبل الخصم» بس. لو المستخدم نسي يملا «بعد الخصم» → **الفاتورة = بدل الانتقال بس**.
**الإصلاح:** `value=int(pf.get("labs_price_after",0) or auto_labs_total or 0)`

### M3 — `_lab_price` بياخد أول رقم مش السعر · `app.py:148-151`
اختبار فعلي:
| السطر | المفروض | الفعلي |
|---|---|---|
| `Test — 1,200 جنيه` | 1200 | **200** ❌ |
| `تحليل 25 جنيه شامل — 300 جنيه` | 300 | **25** ❌ |

السطور اللي البرنامج بيولّدها سليمة (مفيش فواصل)، بس **خانة «أضف تحليل يدوياً» بتسمح بأي نص** — والـ placeholder نفسه `BHCG — 500 جنيه`. أي حد يكتب فاصلة بيخسر 1000 جنيه في صمت.
**الإصلاح:**
```python
def _lab_price(entry):
    m = re_module.findall(r'([\d,]+)\s*جنيه', str(entry or ""))
    return int(m[-1].replace(",", "")) if m else 0
```

### M4 — `wa_digits` مابينظّفش الأرقام العربية
`"٠١٠١٦٨٧٢٨٠١"` → `"20٠١٠١٦٨٧٢٨٠١"` → لينك واتساب مكسور.
**الإصلاح:** `p = clean_digits(p)` في أول الدالة لكل الفروع.

### M5 — 53 سجل فيهم **رقمين تليفون ملزوقين** (بيانات فعلية)
```
'0111080851101114997588'   خديجه جمعه
'0122500872701221132682'   هند وحيد
'0100101138001224254233'   ستيفانى رامى نبيل
... و50 غيرهم
```
النتيجة: لينك الواتساب بيروح لرقم مش موجود، و`fetch_client_history` مش بيلاقي تاريخ العميل، و`get_client_tag` بيقول «عميل جديد» لعميل VIP.
**محتاج سكربت تنظيف لمرة واحدة** يقسّم عند تاني `01`.

### M6 — تواريخ غير صالحة بتكسر التقسيم الشهري
سجل واحد فعلي: `visit_date = "19:00:00"` (اسم: الين شوقى ابراهيم).
وكمان `_month_of("2026-8-1")` بترجّع `"2026-8-"` → اسم ملف بايظ `visits/2026-8-.json`.
**الإصلاح:**
```python
def _month_of(rec):
    d = str(rec.get("visit_date") or "").strip()
    try:
        date.fromisoformat(d); return d[:7]
    except Exception:
        return "0000-00"
```

### M7 — تعريفين مختلفين لكلمة «إيراد»
| الصفحة | المصدر |
|---|---|
| الرئيسية / Dashboard | `total_price` (شامل بدل الانتقال) |
| التقارير | `labs_price_after` (تحاليل بس) |

نفس اللافتة، رقمين مختلفين. وكمان استعلام سنة التقارير (`app.py:4089`) **مابيستبعدش `archived`** خلافًا لـ `fetch_visits`.
**الإصلاح:** دالة واحدة `revenue(visits)` يستخدمها الكل.

### M8 — تناقض في إكسيل التصدير
`df_valid` بيستبعد الملغية لملخص الأطباء، بس صف «الإجمالي الكلي» بيعمل `=SUM()` على **كل** الصفوف (شاملة الملغية). ورقة واحدة فيها رقمين متعارضين.

### M9 — التصدير بيكتب في مجلد العمل باسم ثابت
`export_to_excel()` بتحفظ `visits_export.xlsx` / `lacite_<period>.xlsx` في CWD. لو مستخدمين اتنين صدّروا نفس الفترة في نفس اللحظة، الملف الأول بيتداس قبل ما ينزّله. الأفضل `io.BytesIO` بدل الكتابة على القرص.

### M10 — اتصال SQLite واحد مشترك بين كل الـ threads
```python
@st.cache_resource
def get_connection():
    return sqlite3.connect(DB_FILE, check_same_thread=False)
```
`check_same_thread=False` بتقفل التحذير — بس **مابتخليش الاتصال thread-safe**. Streamlit بيشغّل كل session في thread مستقل. 3 مستخدمين بيضغطوا في نفس اللحظة = احتمال `Recursive use of cursors` أو تداخل transactions.
**الإصلاح:** `threading.Lock` حوالين كل كتابة، أو اتصال لكل session.

### M11 — سطر debug متسيب في production · `app.py:2062`
```python
st.sidebar.write("✅ الأعمدة التي تم التعرف عليها في الملف:", col_mapping)
```

### M12 — التحويل الآلي لـ«تمت» بيلوّث الأرقام
`auto_complete_due_visits()` بيحوّل أي زيارة عدّى ميعادها + ساعتين → «تمت» من غير أي تأكيد بشري. زيارة العميل لغاها بالتليفون ومحدش سجّل الإلغاء → بتبقى «تمت» وبتدخل الإيراد و`get_client_tag`.
**اقتراح:** حالة منفصلة «انتهى ميعادها» بدل «تمت»، أو استثناء الزيارات اللي `payment_status = "غير مدفوع"`.

### M13 — 12 `except:` عارية + 23 `except: pass`
```
bare except: 2229, 2193, 2101, 2082, 3403, 3384, 4139, 4151, 4161, 4173, 4184, 4342
```
دي بالظبط العائلة اللي خبّت بق الـ `NameError` قبل كده (واللي التعليق في سطر 1539 بيوصفه). أقل حاجة: `log_error()` بدل `pass`.

### M14 — مقارنة الإيميل حسّاسة لحالة الحروف
```python
if email_clean not in ALLOWED_EMAILS:      # ← مقارنة حرفية
```
لكن `_user_type_for` بتعمل `.lower()`. حد يكتب `Hussein.Ali77121@gmail.com` بحرف كبير غلط → مرفوض من غير سبب واضح.

---

## 🟢 ملاحظات صغيرة

- الرئيسية بتجيب **كل** الجدول مرتين في كل rerun (`fetch_visits` مع pagination + `all_vs` من غير) — مع نمو البيانات ده بيبقى بطيء.
- KPI «الإيراد» في الرئيسية = إيراد **العمر كله** مش الفترة الحالية، واللافتة مش موضّحة.
- `visit_card_html:2539`: شرط الطول بيتحسب على `loc_label + " " + addr` لكن القص بيتم على `loc_label + " — " + addr` — تلات حروف فرق.
- `restore_from_json` بيرجّع `0, 0` عند أي استثناء — نفس مشكلة الرسالة الكدّابة بتاعة C3.
- `README.md` لسه بيقول `visits.json` وبيوصف بنية v1 — مفيهوش أي ذكر للمزامنة الشهرية ولا الـ Secrets ولا الأرشفة.
- `easter_eggs.py` بيستخدم `datetime.utcnow()` (deprecated في 3.12).
- `.devcontainer` بيشغّل بـ `--server.enableXsrfProtection false` — مقبول للتطوير، بس متسيبهاش تتسرّب لأي deployment.

---

## 💡 اقتراحات التطوير (بترتيب العائد)

### 1. قسّم `app.py` — ده مفتاح كل حاجة تانية
4,705 سطر في ملف واحد هو السبب الحقيقي في إن الأخطاء دي عاشت. التقسيم المقترح:
```
app.py            (~150 سطر — routing بس)
core/db.py        (schema + CRUD + migrations)
core/sync.py      (GitHub + الحُرّاس + الأرشفة)
core/auth.py      (الدخول + الصلاحيات)
core/money.py     (revenue/format — مصدر حقيقة واحد)
ui/pages/*.py     (صفحة لكل ملف)
```
ودي **نفس الخطوة اللي أنت مخططها للنسخة التجارية** — الـ config-driven refactor مستحيل من غيرها.

### 2. اطلع من «JSON على GitHub» كقاعدة بيانات
كل الحُرّاس والأرشفة والتقسيم الشهري اللي بنيتهم — دول كلهم **حلول لعرض واحد**: إن GitHub مش database. بديل مجاني وبيلغي المشاكل دي كلها:
- **Supabase** (Postgres مجاني 500MB) — SQL حقيقي، concurrent writes آمنة، backups تلقائية، Row-Level Security
- **Turso / libSQL** — SQLite موزّع، أقرب حاجة لكودك الحالي، الهجرة تقريبًا مجرد تغيير connection string

المكسب: تلغي `save_to_github_json` (120 سطر) + الحُرّاس + `_hash_records` + `archive_and_prune` + طبقة الإنقاذ + بانر «تعديلات محلية». **~400 سطر بيتشالوا.**

### 3. `config.json` لكل عميل
الحاجات المدفونة في الكود دلوقتي: الإيميلات الثلاثة، أسماء الأطباء الثمانية، `["La Cite","Diamond"]`، `CITY_OPTIONS`، `transport_fee=100`، لينك المراجعة، اسم المطوّر في كل تقرير. كلهم لازم يطلعوا لـ `config.json` قبل أي كلام عن نسخة تجارية.

### 4. اختبارات للطبقة النقية (أسرع مكسب)
`phone_utils` · `lab_picker` · `_lab_price` · `_month_of` · `_time_key` · `parse_extra_persons` — كلهم دوال نقية **مالهاش أي علاقة بـ Streamlit**، يعني تتختبر بـ pytest عادي. ~40 test في ساعتين هيمسكوا M3 و M4 و M6 كلهم أوتوماتيك.

```python
def test_lab_price_with_comma():
    assert _lab_price("Test — 1,200 جنيه") == 1200   # حاليًا بيرجّع 200
def test_month_of_invalid_date():
    assert _month_of({"visit_date": "19:00:00"}) == "0000-00"
```

### 5. الفلوس تبقى `INTEGER` قروش مش `REAL`
`REAL` = floating point = أخطاء تقريب متراكمة في التقارير المالية. `450.0` بيتحول لـ `449.99999` بعد عمليات كفاية. خزّنها `INTEGER` (بالقرش) واقسم على 100 عند العرض بس.

### 6. صفحة لعرض `audit_log`
الجدول بيتكتب فيه من 9 أماكن — و**محدش بيقراه**. صفحة أدمن بسيطة (آخر 200 حدث + فلتر بالمستخدم/التاريخ) بتخلّي البيانات دي ليها قيمة فعلية، وبتفيدك في التتبّع القانوني كمان.

### 7. سكربت تنظيف بيانات لمرة واحدة
- 53 رقم ملزوق (M5)
- 1 تاريخ بايظ (M6)
- 14 سجل «مدفوع» بـ `paid_amount = 0`
- 213 سجل من غير `selected_labs_text`
- 795 سجل مؤرشف بـ `labs_price_after = 0` (تقدر تستنتجها = `total_price - transport_fee`)

### 8. PDF عربي لورقة الزيارة
عندك الـ shaper العربي جاهز من برنامج الـ Price List. ورقة الزيارة دلوقتي HTML — والدكتور بيطبعها من المتصفح. PDF مباشر أنضف وأثبت.

### 9. `st.cache_data(ttl=30)` على الـ KPIs
`get_today_count`, `get_pending_followups_count`, ودوال الإحصائيات في الرئيسية بتتنفّذ في **كل rerun** لكل مستخدم.

---

## 📋 ترتيب التنفيذ المقترح

| # | البند | الوقت | الأثر |
|---|---|---|---|
| 1 | C1 — الـ quote في سطر 4552 | دقيقة | البرنامج بيشتغل على 3.11 |
| 2 | H4 — `.gitignore` | دقيقتين | يمنع تسريب كارثي |
| 3 | C2 — لوب الاستيراد | 10 د | يمنع تعليق + آلاف الـ commits |
| 4 | C3 — `setdefault` للحقول | 5 د | الاستيراد يشتغل صح |
| 5 | H6/H7 — requirements + `_sec()` | 15 د | البرنامج يشتغل محليًا وعلى أي نسخة |
| 6 | M1/M2/M3 — الفلوس | 30 د | أرقام مالية صحيحة |
| 7 | C4 — `sync=False` | 30 د | الاستيراد من دقايق لثواني |
| 8 | H5 — `_esc()` في كل مكان | ساعة | يقفل الـ HTML injection |
| 9 | **H1/H2/H3 — الأمان** | 3–4 ساعات | **أهم بند استراتيجي** |
| 10 | تقسيم `app.py` | 2–3 أيام | يفتح الباب للنسخة التجارية |

---

## 🎯 الخلاصة في سطرين

البرنامج **ناجح ومستخدم فعليًا وبيحمي بياناته بشكل مثير للإعجاب** — الحُرّاس والـ verify-before-prune والتقسيم الشهري ده شغل مهندس مش هاوي، والدليل إن الـ 1,030 سجل متطابقين عبر التلات ملفات بصفر انحراف.

الفجوة مش في المنطق — الفجوة في **الأمان** (بيانات مرضى من غير باسورد) وفي **البنية** (4,705 سطر في ملف واحد بيخلّي أخطاء زي سطر 4552 تعيش من غير ما حد ياخد باله). الاتنين دول بالظبط هما اللي واقفين بينك وبين النسخة التجارية.

---
*مراجعة أُجريت على النسخة المرفوعة في 12 أغسطس 2026 — تشمل فحص كود ثابت، تحليل AST، وتدقيق اتساق البيانات الفعلية على 1,030 سجل.*
