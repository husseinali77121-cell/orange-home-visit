# device_auth.py
# ══════════════════════════════════════════════════════════════════════════════
#  🔐 دخول تلقائي بالجهاز الموثوق — Orange Lab HVMS
#
#  ⚠️ ملاحظة مهمة قبل أي حاجة:
#     "التعرّف على الجهاز بالـ IP" **مش** طريقة آمنة ولا ثابتة:
#       • خطوط الموبايل في مصر شغالة CGNAT — مئات المشتركين بنفس الـ IP.
#         يعني أي حد على نفس الشبكة ممكن يدخل باسمك.
#       • الـ IP بيتغير مع كل إعادة تشغيل للراوتر → هتتقفل بره البرنامج.
#       • Streamlit Cloud بيشوف IP الـ proxy مش جهازك في أغلب الحالات.
#     عشان كده الطريقة الأساسية هنا = **توكن موقّع بالجهاز** (HMAC-SHA256)،
#     والـ IP طبقة إضافية اختيارية بس.
# ══════════════════════════════════════════════════════════════════════════════

import base64
import hashlib
import hmac
import json
import time
import uuid

TOKEN_PARAM = "dev"                 # ?dev=...
COOKIE_NAME = "ol_hvms_dev"
DEFAULT_DAYS = 90

# ── P4: إلغاء الأجهزة ────────────────────────────────────────────────────────
# كل توكن بيحمل رقم الإصدار اللي اتولد بيه. لو الرقم في Secrets اتغيّر،
# كل التوكنات القديمة بتبطل فورًا.
#
# السيناريو اللي بيحلّه: موبايل فرع ضاع. قبل كده مكانش في طريقة تلغي توكنه
# غير إنك تغيّر `device_secret` — وده بيفصل **كل** الأجهزة الموثوقة، ويضطرك
# تعيد تسجيل الدخول من كل جهاز في المعمل.
#
# الاستخدام: زوّد الرقم في Secrets
#     token_version = 2
DEFAULT_TOKEN_VERSION = 1

# مدة توكن الأدمن أقصر من الفروع: توكن الأدمن بيتخطّى الباسورد بالكامل
# (admin_auto_login)، فالمخاطرة أعلى. للتغيير في Secrets: admin_days = 90
DEFAULT_ADMIN_DAYS = 30


def admin_days(st):
    try:
        return int(st.secrets.get("admin_days", DEFAULT_ADMIN_DAYS) or DEFAULT_ADMIN_DAYS)
    except Exception:
        return DEFAULT_ADMIN_DAYS


def token_version(st):
    try:
        return int(st.secrets.get("token_version", DEFAULT_TOKEN_VERSION) or DEFAULT_TOKEN_VERSION)
    except Exception:
        return DEFAULT_TOKEN_VERSION


# ──────────────────────────────────────────────────────────────────────────────
# أدوات
# ──────────────────────────────────────────────────────────────────────────────
def _b64e(b):
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s):
    return base64.urlsafe_b64decode(s + "=" * (-len(s) % 4))


def has_secret(st):
    """
    فيه سر حقيقي في الـ secrets؟
    ⚠️ مهم أمنياً: من غير سر، أي قيمة ثابتة مكتوبة في الملف ده تبقى معروفة
       لأي حد شايف الكود → يقدر يزوّر توكن أدمن. فالأأمن إن الدخول التلقائي
       يتقفل تماماً بدل ما يشتغل بسر مكشوف.
    """
    return bool(_raw_secret(st))


def _raw_secret(st):
    """
    مفتاح توقيع التوكن — `device_secret` **بس**.

    ★ الإصدار القديم كان بيقع على `admin_password` لو `device_secret` مش
      موجود. تصميم غلط لسببين:
        ① باسورد المستخدم مايدخلش في التوقيع التشفيري — دور مختلف تمامًا
        ② تغيير باسورد الأدمن كان بيفصل **كل** الأجهزة الموثوقة فجأة،
           والمستخدم مايعرفش السبب

      دلوقتي: مفيش `device_secret` = الدخول التلقائي مقفول (والبرنامج شغال
      عادي بالباسورد). القفل أوضح من fallback صامت بيكسر حاجة تانية.
    """
    try:
        return str(st.secrets.get("device_secret", "") or "")
    except Exception:
        return ""


def secret_configured(st):
    """للواجهة: تعرض تحذير للأدمن لو المفتاح ناقص."""
    return bool(_raw_secret(st))


def _secret(st):
    return _raw_secret(st).encode()


def _flag(st, key, default=False):
    try:
        return bool(st.secrets.get(key, default))
    except Exception:
        return default


def new_device_id():
    return uuid.uuid4().hex[:12]


# ──────────────────────────────────────────────────────────────────────────────
# التوكن
# ──────────────────────────────────────────────────────────────────────────────
def make_token(st, email, is_admin=False, device_id=None, days=DEFAULT_DAYS, ip=None):
    if not has_secret(st):
        return ""
    payload = {
        "e": str(email or "").strip().lower(),
        "a": 1 if is_admin else 0,
        "d": device_id or new_device_id(),
        "x": int(time.time()) + int(days) * 86400,
        "v": token_version(st),          # P4 — رقم الإصدار للإلغاء الجماعي
    }
    if ip:
        payload["p"] = ip_prefix(ip)
    raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
    sig = hmac.new(_secret(st), raw, hashlib.sha256).digest()[:16]
    return _b64e(raw) + "." + _b64e(sig)


def read_token(st, token):
    """يرجّع الـ payload لو التوقيع سليم والتاريخ لسه صالح، وإلا None."""
    if not has_secret(st) or not token:
        return None
    try:
        p, s = str(token).split(".", 1)
        raw = _b64d(p)
        sig = _b64d(s)
        # base64 من غير padding ليه تهجئات مكافئة (آخر حرف فيه bits مهملة).
        # مش ثغرة — المحتوى بيفضل هو هو — بس بنلزم الصيغة القانونية عشان
        # التوكن يبقى تمثيل واحد ووحيد.
        if _b64e(raw) != p or _b64e(sig) != s:
            return None
        expected = hmac.new(_secret(st), raw, hashlib.sha256).digest()[:16]
        if not hmac.compare_digest(expected, sig):
            return None
        data = json.loads(raw)
        if int(data.get("x", 0)) < time.time():
            return None
        # P4 — التوكن من إصدار قديم = ملغي. التوكنات القديمة (من غير "v")
        # بتتعامل كإصدار 1 عشان الترقية ماتفصلش الأجهزة الحالية.
        if int(data.get("v", DEFAULT_TOKEN_VERSION)) != token_version(st):
            return None
        return data
    except Exception:
        return None


# ──────────────────────────────────────────────────────────────────────────────
# IP
# ──────────────────────────────────────────────────────────────────────────────
def client_ip(st):
    """أفضل تخمين متاح للـ IP. ممكن يرجّع None على Streamlit Cloud."""
    try:
        ip = getattr(st.context, "ip_address", None)
        if ip:
            return str(ip)
    except Exception:
        pass
    try:
        h = st.context.headers
        for k in ("X-Forwarded-For", "x-forwarded-for", "X-Real-Ip", "x-real-ip"):
            v = h.get(k)
            if v:
                return str(v).split(",")[0].strip()
    except Exception:
        pass
    return None


def ip_prefix(ip):
    """/24 لـ IPv4 و أول ٤ مجموعات لـ IPv6 — يسمح بتغيّر بسيط داخل نفس الشبكة."""
    ip = str(ip or "")
    if ":" in ip:
        return ":".join(ip.split(":")[:4])
    parts = ip.split(".")
    return ".".join(parts[:3]) if len(parts) == 4 else ip


def trusted_ip_email(st, ip):
    """
    اختياري تماماً. في secrets.toml:
        [trusted_ips]
        "197.45.12" = "Orangelab511@gmail.com"
    المفتاح ممكن يكون IP كامل أو prefix.
    """
    if not ip:
        return None
    try:
        table = st.secrets.get("trusted_ips", {}) or {}
    except Exception:
        return None
    try:
        items = dict(table).items()
    except Exception:
        return None
    pfx = ip_prefix(ip)
    for k, v in items:
        k = str(k).strip()
        # ⚠️ startswith لوحده غلط: "197.45.1" كان بيقبل "197.45.100.5" كمان.
        #    لازم يقف عند حد النقطة/النقطتين.
        if ip == k or pfx == ip_prefix(k) or ip.startswith(k + ("." if "." in k else ":")):
            return str(v).strip()
    return None


# ──────────────────────────────────────────────────────────────────────────────
# الكوكيز (best-effort — بيشتغل على أغلب النسخ، ولو فشل التوكن في الـ URL بيغطي)
# ──────────────────────────────────────────────────────────────────────────────
def read_cookie(st, name=COOKIE_NAME):
    try:
        return st.context.cookies.get(name)
    except Exception:
        return None


def write_cookie(st, value, days=DEFAULT_DAYS, name=COOKIE_NAME):
    safe = "".join(ch for ch in str(value) if ch.isalnum() or ch in "-_.=")
    try:
        import streamlit.components.v1 as components
        components.html(
            "<script>try{var d=new Date();d.setTime(d.getTime()+%d*864e5);"
            "document.cookie='%s=%s;expires='+d.toUTCString()+';path=/;SameSite=Lax';"
            "}catch(e){}</script>" % (int(days), name, safe),
            height=0,
        )
    except Exception:
        pass


def clear_cookie(st, name=COOKIE_NAME):
    try:
        import streamlit.components.v1 as components
        components.html(
            "<script>try{document.cookie='%s=;expires=Thu, 01 Jan 1970 00:00:00 GMT;"
            "path=/';}catch(e){}</script>" % name, height=0)
    except Exception:
        pass


# ──────────────────────────────────────────────────────────────────────────────
# الواجهة اللي بيستدعيها app.py
# ──────────────────────────────────────────────────────────────────────────────
def try_auto_login(st, allowed_emails):
    """
    بيدوّر على جهاز موثوق بالترتيب: query param → cookie → trusted IP.
    يرجّع dict {'email','is_admin','via'} أو None.
    """
    # نحتفظ بشكل الإيميل الأصلي (حروف كبيرة/صغيرة) عشان سجل التدقيق
    # يبقى متسق مع الدخول اليدوي.
    allowed_map = {str(e).strip().lower(): str(e).strip() for e in (allowed_emails or [])}
    allowed_lc = set(allowed_map)
    if not allowed_lc:
        return None
    ip = client_ip(st)

    candidates = []
    try:
        t = st.query_params.get(TOKEN_PARAM, "")
        if t:
            candidates.append(("link", t))
    except Exception:
        pass
    ck = read_cookie(st)
    if ck:
        candidates.append(("cookie", ck))

    for via, tok in candidates:
        data = read_token(st, tok)
        if not data:
            continue
        email = data.get("e", "")
        if email not in allowed_lc:
            continue
        # ربط الـ IP (اختياري — مقفول افتراضياً لأن IP الموبايل بيتغيّر)
        if _flag(st, "device_bind_ip", False) and data.get("p") and ip:
            if ip_prefix(ip) != data["p"]:
                continue
        is_admin = bool(data.get("a")) and _flag(st, "admin_auto_login", True)
        # ★ P2 — التوكن اللي جه من الـ URL بيتنقل للكوكي **ويتشال من العنوان
        #   فورًا**. من غير الخطوة دي، أي مستخدم حالي عنده اللينك محفوظ هيفضل
        #   ماشي بتوكن مكشوف للأبد حتى بعد إصلاح remember_device.
        #   بنسيبه في الـ URL بس لو الاحتياطي مفعّل صراحة.
        if via == "link" and not _flag(st, "allow_url_token", False):
            try:
                st.session_state["_pending_cookie"] = tok
                st.session_state["_cookie_tries"] = 0
                st.query_params.pop(TOKEN_PARAM, None)
            except Exception:
                pass
        return {"email": allowed_map[email], "is_admin": is_admin, "via": via,
                "device_id": data.get("d", ""), "token": tok}

    # allowlist بالـ IP (اختياري بالكامل)
    tie = trusted_ip_email(st, ip)
    if tie and tie.lower() in allowed_lc:
        return {"email": allowed_map[tie.lower()], "is_admin": False, "via": "ip",
                "device_id": "", "token": ""}
    return None


def remember_device(st, email, is_admin=False, days=DEFAULT_DAYS):
    """
    يولّد توكن ويرجّعه عشان app.py يكتبه في الكوكي.

    ★ P2 — التوكن **مابقاش** يتحط في الـ URL افتراضيًا.
      كان: st.query_params[TOKEN_PARAM] = tok  ← وبيفضل هناك للأبد.
      المشكلة إن الـ URL بيتحفظ في history المتصفح، وبيظهر في أي screenshot،
      وبيتبعت لو حد شارك اللينك على واتساب. وأي حد يفتحه = **دخول 90 يوم**.
      دلوقتي الكوكي هي المخزن الوحيد.

      لو الكوكيز مقفولة عند مستخدم معيّن (سفاري في وضع خاص مثلاً)، يقدر
      يفعّل الاحتياطي صراحة في Secrets:  allow_url_token = true

    ⚠️ الكوكي **مش** بتتكتب هنا: الـ JS بتاعها بيتنفّذ في المتصفح، وأي
       st.rerun() بعدها على طول بيلغي الفريم قبل ما يشتغل. عشان كده app.py
       بيحطّ التوكن في _pending_cookie ويكتبه في الرن اللي بعده.
    """
    if is_admin and days == DEFAULT_DAYS:
        days = admin_days(st)          # الأدمن ياخد المدة الأقصر افتراضيًا
    tok = make_token(st, email, is_admin=is_admin, days=days, ip=client_ip(st))
    if not tok:
        return ""
    try:
        if _flag(st, "allow_url_token", False):
            st.query_params[TOKEN_PARAM] = tok
        else:
            st.query_params.pop(TOKEN_PARAM, None)
        st.query_params.pop("remember", None)
    except Exception:
        pass
    return tok


def forget_device(st):
    """خروج نهائي من الجهاز ده."""
    try:
        st.query_params.clear()
    except Exception:
        pass
    clear_cookie(st)
