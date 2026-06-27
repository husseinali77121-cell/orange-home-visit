import pandas as pd
import json
import os
from datetime import date

# =======================================================
# سكريبت تحويل ملفات الـ Excel المتعددة إلى ملف Visits.json واحد
# =======================================================

def clean_dataframe(df):
    """تنظيف الداتا فريم من الصفوف الزائدة (مثل الإحصائيات والملخصات)"""
    # تحويل الأعمدة لنص لتسهيل المعالجة
    df = df.astype(str)
    # حذف الصفوف التي لا تحتوي على اسم عميل صالح (أو تحتوي على كلمة "الإجمالي")
    df = df[~df['الاسم'].str.contains('الإجمالي', na=False)]
    df = df[~df['الاسم'].str.contains('زيارة', na=False)]
    df = df[df['الاسم'].str.strip() != '']
    df = df.dropna(subset=['الاسم'])
    return df

def convert_excel_to_json(file_paths, output_json="Visits.json"):
    all_records = []
    
    for file_path in file_paths:
        if not os.path.exists(file_path):
            print(f"⚠️ تحذير: الملف {file_path} غير موجود، تم تخطيه.")
            continue
            
        try:
            # قراءة ملف الإكسيل
            df = pd.read_excel(file_path, engine="openpyxl", sheet_name=0)
            df.columns = [str(c).strip().replace(" ", "") for c in df.columns]
            
            # فحص الأعمدة (نتأكد إن الملف يحتوي على الأعمدة الأساسية)
            if 'الاسم' not in df.columns:
                print(f"⚠️ الملف {file_path} لا يحتوي على عمود 'الاسم'، تم تخطيه.")
                continue
            
            df = clean_dataframe(df)
            
            # تحويل الصفوف إلى قاموس (Dictionary)
            for _, row in df.iterrows():
                record = {}
                # تعيين القيم وتجاهل القيم الفارغة (NaN)
                for col in df.columns:
                    val = row[col]
                    if pd.isna(val):
                        val = ""
                    record[col] = val
                
                # إصلاح بعض الحقول لتطابق قاعدة البيانات
                # تحويل التاريخ إلى صيغة YYYY-MM-DD إذا كان موجوداً
                if record.get('تاريخالزيارة'):
                    try:
                        record['تاريخالزيارة'] = pd.to_datetime(record['تاريخالزيارة']).strftime('%Y-%m-%d')
                    except:
                        record['تاريخالزيارة'] = date.today().isoformat()
                
                all_records.append(record)
                
        except Exception as e:
            print(f"❌ خطأ أثناء قراءة {file_path}: {e}")
    
    # حفظ النتيجة في ملف JSON
    with open(output_json, 'w', encoding='utf-8') as f:
        json.dump(all_records, f, ensure_ascii=False, indent=2)
    
    print(f"✅ تم التحويل بنجاح! تم حفظ {len(all_records)} زيارة في ملف '{output_json}'.")

# ⚙️ قائمة بملفات الإكسيل اللي أنت بعتها (ضعها في نفس المجلد)
excel_files = [
    "diamond_2026-05-29_2026-06-20.xlsx",
    "lacite_2026-05-28_2026-06-23.xlsx",
    "lacite_2026-05-29_2026-06-22.xlsx",
    "lacite_2026-05-29_2026-06-23.xlsx",
    "visits_2026-05-28_2026-06-21.xlsx",
    "visits_all_2026-06-20.xlsx",
    "visits_يونيو_2026_La Cite.xlsx"
]

if __name__ == "__main__":
    convert_excel_to_json(excel_files)
