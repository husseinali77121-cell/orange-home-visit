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


def send_message(cfg, msg, smtp_ssl_cls=None, timeout=45):
    """
    بيبعت الرسالة. (ok, رسالة للمستخدم). مابيرميش استثناءات ومابيطبعش الباسورد.
    smtp_ssl_cls للاختبار فقط.
    """
    cls = smtp_ssl_cls or smtplib.SMTP_SSL
    try:
        with cls(cfg["host"], cfg["port"], timeout=timeout,
                 context=ssl.create_default_context()) as s:
            s.login(cfg["user"], cfg["password"])
            s.send_message(msg)
        return True, ""
    except smtplib.SMTPAuthenticationError:
        return False, ("جوجل رفض الدخول — لازم «App Password» (مش الباسورد العادي) "
                       "والتحقق بخطوتين يكون مفعّل على حساب الإرسال")
    except smtplib.SMTPRecipientsRefused:
        return False, "العنوان المستلم اترفض"
    except (smtplib.SMTPException, OSError) as e:
        return False, f"{type(e).__name__}: {e}"
    except Exception as e:                          # أي حاجة غريبة — ماتوقعش الصفحة
        return False, f"{type(e).__name__}: {e}"
