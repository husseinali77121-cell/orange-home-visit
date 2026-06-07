# 🟠 Orange Home Visit

نظام إدارة الزيارات المنزلية للتحاليل الطبية — مبني بـ Python + Streamlit

## المميزات

- ✅ حفظ بيانات العملاء (الاسم، السن، التليفون، العنوان، الموقع)
- 🔍 بحث بالاسم أو التليفون
- 🧪 اختيار التحاليل من قائمة جاهزة مع الأسعار
- 💰 حساب تلقائي للإجمالي
- 📱 إرسال على واتساب للعميل أو مشاركة الملخص
- 🔄 زيارة متكررة بضغطة واحدة
- 📊 إحصائيات يومية وإجمالية

## هيكل المشروع

```
orange-home-visit/
├── app.py               ← الكود الرئيسي
├── requirements.txt     ← المكتبات المطلوبة
├── visits.json          ← قاعدة البيانات (تُنشأ تلقائياً)
└── .streamlit/
    └── config.toml      ← إعدادات التصميم
```

## التشغيل المحلي

```bash
pip install streamlit
streamlit run app.py
```

## النشر على Streamlit Cloud (مجاناً)

1. ارفع المشروع على GitHub
2. اذهب إلى https://share.streamlit.io
3. اضغط "New app"
4. اختر الـ repo والملف `app.py`
5. اضغط Deploy ✅

---
🟠 Orange Home Visit Team
