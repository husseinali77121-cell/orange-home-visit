# -*- coding: utf-8 -*-
"""
email_backup.py — إرسال نسخة قاعدة البيانات على إيميل الفرع الرئيسي (للأدمن بس)

إضافة بحتة: مابتلمسش الحفظ ولا المزامنة. مفيش Streamlit هنا — الدوال بتاخد
الإعدادات كـ dict وبترجّع (ok, رسالة) فبتتختبر من غير شبكة.

الإعداد (Secrets على Streamlit Cloud):
    smtp_user     = "Orangelab511@gmail.com"      # الإيميل اللي هيبعت
    smtp_password = "xxxx xxxx xxxx xxxx"         # «App Password» من حساب جوجل (مش الباسورد العادي)
    # اختياري: smtp_host (smtp.gmail.com) · smtp_port (465)

⚠️ الـ App Password بيتعمل من: حساب جوجل ← الأمان ← التحقق بخطوتين (لازم يكون مفعّل) ← App passwords.
"""
import smtplib
import ssl
from email.message import EmailMessage

DEFAULT_HOST = "smtp.gmail.com"
DEFAULT_PORT = 465
MAX_TOTAL_BYTES = 20 * 1024 * 1024          # جيميل بيرفض فوق ~25MB — نسيب هامش


def smtp_config(get):
    """
    get(key, default) → قيمة من الـ secrets. بيرجّع dict جاهز أو None لو الإعداد ناقص.
    الباسورد بيتنضّف من المسافات (جوجل بيعرضه 4×4 بمسافات).
    """
    user = str(get("smtp_user", "") or "").strip()
    pwd = str(get("smtp_password", "") or "").replace(" ", "").strip()
    if not user or not pwd:
        return None
    try:
        port = int(get("smtp_port", DEFAULT_PORT) or DEFAULT_PORT)
    except (TypeError, ValueError):
        port = DEFAULT_PORT
    return {"user": user, "password": pwd,
            "host": str(get("smtp_host", DEFAULT_HOST) or DEFAULT_HOST).strip(),
            "port": port}


def build_message(sender, recipient, subject, body, attachments):
    """
    attachments: list من (filename, bytes, mimetype "type/subtype").
    بيرجّع EmailMessage جاهز. بيرمي ValueError لو الحجم الكلي كبير أو مفيش مرفقات.
    """
    files = [(n, b, m) for n, b, m in (attachments or []) if b]
    if not files:
        raise ValueError("مفيش مرفقات للإرسال")
    total = sum(len(b) for _, b, _ in files)
    if total > MAX_TOTAL_BYTES:
        raise ValueError(f"حجم المرفقات {total / 1048576:.1f}MB أكبر من الحد المسموح")
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = recipient
    msg["Subject"] = subject
    msg.set_content(body)
    for name, data, mime in files:
        maintype, _, subtype = (mime or "application/octet-stream").partition("/")
        msg.add_attachment(data, maintype=maintype or "application",
                           subtype=subtype or "octet-stream", filename=name)
    return msg


def _attempts(cfg):
    """
    ترتيب المحاولات: المنفذ المضبوط في الإعدادات الأول، وبعدين البديل.
    465 = SSL مباشر، 587 = STARTTLS. بعض السيرفرات/الشبكات بتقفل واحد منهم وتسيب التاني.
    """
    ssl_first = int(cfg.get("port") or DEFAULT_PORT) != 587
    a = ("SSL:465", "ssl", 465)
    b = ("STARTTLS:587", "starttls", 587)
    out = [a, b] if ssl_first else [b, a]
    if int(cfg.get("port") or 0) not in (465, 587):        # منفذ مخصص → يتجرّب الأول بالنوع المناسب
        out.insert(0, (f"custom:{cfg['port']}", "ssl", int(cfg["port"])))
    return out


_AUTH_MSG = ("جوجل رفض الدخول — لازم «App Password» من نفس الحساب smtp_user "
             "(مش الباسورد العادي) والتحقق بخطوتين يكون مفعّل")


def _try_once(cfg, mode, port, msg, ssl_cls, plain_cls, timeout, send=True):
    """محاولة واحدة. بيرجّع (ok, stage, خطأ). stage = connect/login/send."""
    stage = "connect"
    ctx = ssl.create_default_context()
    try:
        if mode == "ssl":
            conn = (ssl_cls or smtplib.SMTP_SSL)(cfg["host"], port, timeout=timeout, context=ctx)
        else:
            conn = (plain_cls or smtplib.SMTP)(cfg["host"], port, timeout=timeout)
        with conn as s:
            if mode == "starttls":
                s.ehlo()
                s.starttls(context=ctx)
                s.ehlo()
            stage = "login"
            s.login(cfg["user"], cfg["password"])
            if send:
                stage = "send"
                s.send_message(msg)
        return True, stage, ""
    except smtplib.SMTPAuthenticationError:
        return False, "auth", _AUTH_MSG
    except smtplib.SMTPServerDisconnected:
        return False, stage, "السيرفر قفل الاتصال فجأة"
    except smtplib.SMTPRecipientsRefused:
        return False, stage, "العنوان المستلم اترفض"
    except (smtplib.SMTPException, OSError) as e:
        return False, stage, f"{type(e).__name__}: {e}"
    except Exception as e:                              # أي حاجة غريبة — ماتوقعش الصفحة
        return False, stage, f"{type(e).__name__}: {e}"


_STAGE_AR = {"connect": "الاتصال", "login": "تسجيل الدخول", "send": "إرسال الرسالة"}


def send_message_ex(cfg, msg, smtp_ssl_cls=None, smtp_cls=None, timeout=30):
    """
    بيبعت الرسالة وبيجرّب المنفذين (465 SSL ثم 587 STARTTLS). مابيرميش استثناءات ومابيطبعش الباسورد.
    بيرجّع dict: ok / message / stage (أبعد مرحلة وصلت لها أي محاولة) / attempts [(label, stage, err)].
    باسورد غلط بيوقف فورًا (مفيش فايدة من تجربة منفذ تاني).
    """
    attempts = []
    for label, mode, port in _attempts(cfg):
        ok, stage, err = _try_once(cfg, mode, port, msg, smtp_ssl_cls, smtp_cls, timeout)
        if ok:
            return {"ok": True, "message": "", "stage": "", "attempts": attempts}
        attempts.append((label, stage, err))
        if stage == "auth":
            return {"ok": False, "message": err, "stage": "auth", "attempts": attempts}
    detail = " | ".join(f"{lb}: {_STAGE_AR.get(st, st)} — {er}" for lb, st, er in attempts)
    order = {"connect": 0, "login": 1, "send": 2}
    furthest = max((st for _, st, _ in attempts), key=lambda x: order.get(x, 0))   # أبعد مرحلة وصلنا لها
    return {"ok": False, "message": detail, "stage": furthest, "attempts": attempts}


def send_message(cfg, msg, smtp_ssl_cls=None, smtp_cls=None, timeout=30):
    """نفس send_message_ex بس بيرجّع (ok, رسالة)."""
    r = send_message_ex(cfg, msg, smtp_ssl_cls, smtp_cls, timeout)
    return r["ok"], r["message"]


def check_connection(cfg, smtp_ssl_cls=None, smtp_cls=None, timeout=20):
    """
    اختبار الاتصال وتسجيل الدخول **من غير إرسال أي حاجة**. بيجرّب المنفذين ويرجّع
    (ok, تقرير لكل محاولة) علشان نعرف المشكلة فين بالظبط.
    """
    lines, any_ok = [], False
    for label, mode, port in _attempts(cfg):
        ok, stage, err = _try_once(cfg, mode, port, None, smtp_ssl_cls, smtp_cls, timeout, send=False)
        if ok:
            any_ok = True
            lines.append(f"✅ {label}: الاتصال وتسجيل الدخول نجحوا")
        else:
            lines.append(f"❌ {label}: {_STAGE_AR.get(stage, stage)} — {err}")
            if stage == "auth":
                break
    return any_ok, "\n".join(lines)
