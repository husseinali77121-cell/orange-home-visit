import streamlit as st
import sqlite3
import json
import os
import urllib.parse
from datetime import date, datetime
import pandas as pd
import re

# ─── Page Config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Orange Lab Home Visit",
    page_icon="🟠",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# ─── Auto-migration from JSON to SQLite (runs once on startup) ───────────────
DB_FILE = "visits.db"
OLD_JSON = "visits.json"
MIGRATED_FLAG = "visits_migrated.txt"

def run_migration_if_needed():
    # Only migrate if JSON exists, DB doesn't exist (or is empty), and not previously migrated
    if os.path.exists(OLD_JSON) and not os.path.exists(MIGRATED_FLAG):
        # Create DB and table if not exists
        conn = sqlite3.connect(DB_FILE, check_same_thread=False)
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id TEXT PRIMARY KEY,
                created_at TEXT,
                name TEXT NOT NULL,
                age INTEGER,
                phone TEXT NOT NULL,
                visit_date TEXT NOT NULL,
                visit_time TEXT,
                doctor_name TEXT,
                branch TEXT DEFAULT 'La Cite',
                address TEXT NOT NULL,
                location_link TEXT,
                selected_labs_text TEXT,
                notes TEXT,
                labs_price_before REAL DEFAULT 0,
                labs_price_after REAL DEFAULT 0,
                transport_fee REAL DEFAULT 0,
                total_price REAL DEFAULT 0
            )
        """)

        # Check if DB already has data
        existing = conn.execute("SELECT COUNT(*) FROM visits").fetchone()[0]
        if existing == 0:
            # Load old data
            with open(OLD_JSON, "r", encoding="utf-8") as f:
                old_visits = json.load(f)
            for v in old_visits:
                conn.execute("""
                    INSERT OR REPLACE INTO visits (
                        id, created_at, name, age, phone, visit_date, visit_time,
                        doctor_name, branch, address, location_link,
                        selected_labs_text, notes, labs_price_before,
                        labs_price_after, transport_fee, total_price
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    v.get("id"),
                    v.get("created_at"),
                    v.get("name"),
                    v.get("age"),
                    v.get("phone"),
                    v.get("visit_date"),
                    v.get("visit_time"),
                    v.get("doctor_name", ""),
                    v.get("branch", "La Cite"),
                    v.get("address"),
                    v.get("location_link"),
                    v.get("selected_labs_text", ""),
                    v.get("notes"),
                    v.get("labs_price_before", v.get("labs_price", 0)),
                    v.get("labs_price_after", v.get("labs_price", 0)),
                    v.get("transport_fee", v.get("visit_price", 0)),
                    v.get("total_price", 0)
                ))
            conn.commit()
            # Mark migration as done
            with open(MIGRATED_FLAG, "w") as f:
                f.write("done")
        conn.close()

# Run migration on startup
run_migration_if_needed()

# ─── Database Setup (SQLite) ──────────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS visits (
            id TEXT PRIMARY KEY,
            created_at TEXT,
            name TEXT NOT NULL,
            age INTEGER,
            phone TEXT NOT NULL,
            visit_date TEXT NOT NULL,
            visit_time TEXT,
            doctor_name TEXT,
            branch TEXT DEFAULT 'La Cite',
            address TEXT NOT NULL,
            location_link TEXT,
            selected_labs_text TEXT,
            notes TEXT,
            labs_price_before REAL DEFAULT 0,
            labs_price_after REAL DEFAULT 0,
            transport_fee REAL DEFAULT 0,
            total_price REAL DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()

# Ensure DB file and table exist
if not os.path.exists(DB_FILE):
    init_db()
else:
    try:
        init_db()
    except:
        pass

@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def fetch_visits(filters=None):
    conn = get_connection()
    query = "SELECT * FROM visits"
    params = []
    conditions = []
    if filters:
        if filters.get("search"):
            s = f"%{filters['search']}%"
            conditions.append("(name LIKE ? OR phone LIKE ?)")
            params.extend([s, s])
        if filters.get("branch"):
            conditions.append("branch = ?")
            params.append(filters["branch"])
        if filters.get("doctor"):
            conditions.append("doctor_name = ?")
            params.append(filters["doctor"])
        if filters.get("month") and filters.get("year"):
            y, m = filters["year"], filters["month"]
            conditions.append("strftime('%Y', visit_date) = ? AND strftime('%m', visit_date) = ?")
            params.extend([str(y), f"{m:02d}"])
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY created_at DESC"
    rows = conn.execute(query, params).fetchall()
    return [dict(r) for r in rows]

def fetch_visit_by_id(visit_id):
    conn = get_connection()
    row = conn.execute("SELECT * FROM visits WHERE id = ?", (visit_id,)).fetchone()
    return dict(row) if row else None

def insert_visit(record):
    conn = get_connection()
    conn.execute("""
        INSERT INTO visits (
            id, created_at, name, age, phone, visit_date, visit_time,
            doctor_name, branch, address, location_link,
            selected_labs_text, notes, labs_price_before,
            labs_price_after, transport_fee, total_price
        ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
    """, (
        record["id"], record["created_at"], record["name"], record["age"],
        record["phone"], record["visit_date"], record["visit_time"],
        record["doctor_name"], record.get("branch", "La Cite"),
        record["address"], record["location_link"],
        record["selected_labs_text"], record["notes"],
        record["labs_price_before"], record["labs_price_after"],
        record["transport_fee"], record["total_price"]
    ))
    conn.commit()

def update_visit(record):
    conn = get_connection()
    conn.execute("""
        UPDATE visits SET
            name = ?, age = ?, phone = ?, visit_date = ?, visit_time = ?,
            doctor_name = ?, branch = ?, address = ?, location_link = ?,
            selected_labs_text = ?, notes = ?, labs_price_before = ?,
            labs_price_after = ?, transport_fee = ?, total_price = ?
        WHERE id = ?
    """, (
        record["name"], record["age"], record["phone"], record["visit_date"],
        record["visit_time"], record["doctor_name"], record.get("branch", "La Cite"),
        record["address"], record["location_link"], record["selected_labs_text"],
        record["notes"], record["labs_price_before"], record["labs_price_after"],
        record["transport_fee"], record["total_price"], record["id"]
    ))
    conn.commit()

def delete_visit(visit_id):
    conn = get_connection()
    conn.execute("DELETE FROM visits WHERE id = ?", (visit_id,))
    conn.commit()

# ─── Inject CSS ────────────────────────────────────────────────────────────────
def inject_css():
    css = """
    <link href="https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap" rel="stylesheet">
    <style>
      html, body, [class*="css"] { font-family: 'Cairo', sans-serif !important; direction: rtl; }
      .main { background: #fff8f0; }
      .block-container { padding-top: 0.5rem !important; max-width: 680px; }
      .ohv-header {
        background: linear-gradient(90deg, #FF6B00, #FF9A3C);
        border-radius: 16px; padding: 16px 22px;
        display: flex; align-items: center; justify-content: space-between;
        margin-bottom: 18px; box-shadow: 0 4px 20px rgba(255,107,0,0.3);
      }
      .ohv-header h1 { color:#fff; margin:0; font-size:20px; font-weight:800; }
      .ohv-header span { color:rgba(255,255,255,0.85); font-size:12px; }
      .stat-grid { display:flex; gap:10px; margin-bottom:18px; }
      .stat-box { flex:1; background:#fff; border-radius:14px; padding:12px; text-align:center; border:1px solid #ffe8d1; box-shadow:0 2px 10px rgba(0,0,0,0.05); }
      .stat-num { font-size:24px; font-weight:800; color:#FF6B00; }
      .stat-label { font-size:10px; color:#aaa; margin-top:2px; }
      .visit-card { background:#fff; border-radius:14px; padding:14px; margin-bottom:10px; border:1px solid #ffe8d1; box-shadow:0 2px 10px rgba(0,0,0,0.05); }
      .visit-name { font-size:15px; font-weight:700; color:#222; }
      .visit-meta { font-size:12px; color:#888; margin-top:4px; }
      .visit-badge { background:#fff3e6; color:#FF6B00; border-radius:8px; padding:3px 10px; font-size:12px; font-weight:700; float:left; }
      .price-box { background: linear-gradient(135deg, #FF6B00, #FF9A3C); border-radius:16px; padding:16px 20px; color:#fff; margin-bottom:14px; }
      .price-row { display:flex; justify-content:space-between; font-size:14px; margin-bottom:7px; }
      .price-total { display:flex; justify-content:space-between; font-size:19px; font-weight:800; border-top:2px solid rgba(255,255,255,0.3); padding-top:9px; margin-top:5px; }
      .wa-btn { display:block; padding:11px 16px; border-radius:12px; color:#fff !important; font-weight:700; font-size:13px; text-decoration:none; text-align:center; font-family:'Cairo',sans-serif; margin-bottom: 8px; }
      .wa-client { background:#25D366; }
      .wa-share  { background:#128C7E; }
      .wa-group  { background:#075E54; }
      .detail-row { display:flex; justify-content:space-between; padding:8px 0; border-bottom:1px solid #f5f5f5; font-size:13px; }
      .detail-label { color:#888; }
      .detail-value { font-weight:600; color:#222; max-width:58%; text-align:left; }
      .lab-chip { display:inline-flex; align-items:center; gap:6px; margin:3px; background:#fff3e6; color:#FF6B00; border-radius:20px; padding:4px 12px; font-size:12px; font-weight:600; border:1px solid #ffd4a8; }
      .repeat-banner { background:#fff8f0; border:2px dashed #FF9A3C; border-radius:14px; padding:12px; text-align:center; margin-top:12px; color:#FF6B00; font-weight:700; font-size:14px; }
      .section-title { font-size:14px; font-weight:700; color:#FF6B00; border-right:4px solid #FF6B00; padding-right:10px; margin-bottom:10px; }
      div[data-testid="stButton"] button { font-family:'Cairo',sans-serif !important; font-weight:700 !important; border-radius:12px !important; }
      div[data-testid="stTextInput"] label, div[data-testid="stNumberInput"] label,
      div[data-testid="stDateInput"] label, div[data-testid="stTextArea"] label,
      div[data-testid="stMultiSelect"] label, div[data-testid="stSelectbox"] label {
        font-family:'Cairo',sans-serif !important; font-weight:600 !important; color:#555 !important;
      }
      #MainMenu { visibility: hidden; }
      footer { visibility: hidden; }
      header { visibility: hidden; }
      /* PRINT */
      @media print {
        body * { visibility: hidden; }
        #printable-report, #printable-report * { visibility: visible; }
        #printable-report { position: absolute; left: 0; top: 0; width: 100%; }
        .no-print { display: none; }
      }
    </style>
    """
    st.components.v1.html(css, height=0)

inject_css()

# ─── LABS_DB (unchanged) ─────────────────────────────────────────────────────
LABS_DB = {
    "Allergy Screen": [
        {"name": "IgE Food allergy test panel", "price": 2500},
        {"name": "IgE for milk allergy Rast", "price": 1300},
        {"name": "IgE Inhalant allergy panel", "price": 2000},
        {"name": "IgE Specific Rast Gluten", "price": 1000},
        {"name": "Mixed Allergy Panel (Food &", "price": 3700},
        {"name": "Pediatric Panel (Food &", "price": 2500},
        {"name": "Rast for drugs", "price": 2500},
        {"name": "Tuberculin Skin Test", "price": 200},
    ],
    "Antiphospholipid antibody syndrome": [
        {"name": "Anti Cardiolipin  IgG (ACL IgG)", "price": 650},
        {"name": "Anti Cardiolipin  IgM (ACL IgM)", "price": 650},
        {"name": "Anti-Phospholipid IgG (APL IgG)", "price": 650},
        {"name": "Anti-Phospholipid IgM (APL IgM)", "price": 650},
        {"name": "Lupus Anticoagulant", "price": 600},
        {"name": "Albumin (Ascitic Fluid)", "price": 100},
        {"name": "Ascitic Fluid Examination", "price": 550},
        {"name": "Glucose (Ascitic Fluid)", "price": 80},
        {"name": "LDH (Ascitic Fluid)", "price": 250},
        {"name": "Total Protein (Ascitic Fluid)", "price": 120},
    ],
    "Autoimmune diseases": [
        {"name": "Acetylcholine receptor Ab", "price": 2500},
        {"name": "AChE (Acetylcholinesterase)", "price": 1200},
        {"name": "Actin Antibodies", "price": 1700},
        {"name": "Activated protein C resistance", "price": 2000},
        {"name": "ANA (Antinuclear Ab)", "price": 350},
        {"name": "ANA (Antinuclear Ab) titre by IF", "price": 600},
        {"name": "ANA (Immunoblot technique)", "price": 1600},
        {"name": "ANCA - C", "price": 850},
        {"name": "ANCA - P", "price": 850},
        {"name": "ANCA (Anti neutrophil", "price": 1000},
        {"name": "Anti CCP", "price": 1400},
        {"name": "Anti Centromere Ab", "price": 500},
        {"name": "Anti Endomysial IgA (EMA IgA)", "price": 2000},
        {"name": "Anti Endomysial IgG (EMA IgG)", "price": 2000},
        {"name": "Anti Endomysial IgM (EMA IgM)", "price": 2000},
        {"name": "Anti Gad Abs", "price": 2600},
        {"name": "Anti Hepatic Soluble Antigens", "price": 3500},
        {"name": "Anti Hepatic Soluble Antigens", "price": 3500},
        {"name": "Anti Hepatic Soluble Antigens", "price": 3500},
        {"name": "Anti Hepatic Soluble Antigens", "price": 3500},
        {"name": "Anti Hepatic Soluble Antigens", "price": 3500},
        {"name": "Anti Hepatic Soluble Antigens", "price": 3500},
        {"name": "Anti Insulin Abs.", "price": 2500},
        {"name": "Anti intrinsic factor Abs.", "price": 3000},
        {"name": "Anti Jo1 Ab", "price": 400},
        {"name": "Anti Keratin Ab", "price": 1000},
        {"name": "Anti LKM (Liver Kidney", "price": 600},
        {"name": "Anti MAG Antibodies IgG", "price": 2000},
        {"name": "Anti MCV Abs.", "price": 1800},
        {"name": "Anti Musk Abs (Muscle Specific", "price": 3600},
        {"name": "Anti Ovarian antibodies IgG", "price": 1900},
        {"name": "Anti Proteinase-3", "price": 550},
        {"name": "Anti striated muscle Abs", "price": 780},
        {"name": "Anti-Deamidated gliadin peptide", "price": 600},
        {"name": "Anti-Gliadin IgA", "price": 1200},
        {"name": "Anti-Gliadin IgG", "price": 1200},
        {"name": "Anti-Gliadin IgM", "price": 1200},
        {"name": "Anti-Histone Ab", "price": 550},
        {"name": "Anti-Mitochondrial Abs (AMA)", "price": 550},
        {"name": "Anti-Parietal Cell Abs  (APCA)", "price": 750},
        {"name": "Anti-phospholipase A2 Abs", "price": 7000},
        {"name": "Anti-PLA2R (Anti phospholipase", "price": 3900},
        {"name": "Anti-Reticulin Abs", "price": 350},
        {"name": "Anti-Ribosomal RNA", "price": 1000},
        {"name": "Anti-RNP Abs", "price": 650},
        {"name": "Anti-Scl 70 Abs", "price": 900},
        {"name": "Anti-Smith Abs", "price": 900},
        {"name": "Anti-Smooth muscle Abs (ASMA)", "price": 600},
        {"name": "Anti-Sperm Abs (IgG)", "price": 650},
        {"name": "Anti-SSA (Ro) Abs", "price": 850},
        {"name": "Anti-SSB (La) Abs", "price": 850},
        {"name": "Aquoporin 4 (neuromyelitis optic", "price": 3960},
        {"name": "Aquoporin 4 (neuromyelitis optic", "price": 5940},
        {"name": "ASCA (IgA)", "price": 900},
        {"name": "ASCA (IgG)", "price": 900},
        {"name": "ASOT(Anti-Streptolysin-O)(Quanti", "price": 350},
        {"name": "B2-Glycoprotein Abs(IgG)", "price": 1000},
        {"name": "B2-Glycoprotein Abs(IgM)", "price": 1000},
        {"name": "Cow Milk (class)", "price": 1200},
        {"name": "ds-DNA (Anti ds-DNA Abs)", "price": 300},
        {"name": "Islet cell Ab", "price": 1800},
        {"name": "NK Cells (natural Killer cells", "price": 1700},
        {"name": "Platelet Antibodies (Direct)", "price": 1000},
        {"name": "Platelet Antibodies (Indirect)", "price": 1000},
        {"name": "Soluble Liver Antigen (SLA-Ab)", "price": 2500},
        {"name": "Tissue transglutaminase Ab (IgA)", "price": 1000},
        {"name": "Tissue transglutaminase Ab (IgG)", "price": 1000},
        {"name": "Von Willebrand Factor (VWF)", "price": 2500},
    ],
    "BLOOD GASES": [
        {"name": "Amino Acids in blood", "price": 3300},
        {"name": "Blood Gases", "price": 1000},
        {"name": "Blood pH", "price": 100},
        {"name": "Osmotic fragility test", "price": 250},
    ],
    "Blood Glucose": [
        {"name": "FBG", "price": 120},
        {"name": "GLP-1 (Glucagon like peptide)", "price": 2700},
        {"name": "Glucose 1 hr (100 gm Glucose)", "price": 80},
        {"name": "Glucose 1 hr (50 gm Glucose)", "price": 80},
        {"name": "Glucose 1 hr (75 gm Glucose)", "price": 80},
        {"name": "Glucose 2 hr (100 gm Glucose)", "price": 80},
        {"name": "Glucose 2 hr (50 gm Glucose)", "price": 80},
        {"name": "Glucose 2 hr (75 gm Glucose)", "price": 80},
        {"name": "Glucose Tolerance  1 hr", "price": 80},
        {"name": "Glucose Tolerance  2 hrs", "price": 80},
        {"name": "Glucose Tolerance 1.5 hr", "price": 80},
        {"name": "Glucose Tolerance Curve", "price": 400},
        {"name": "HbA1C", "price": 400},
        {"name": "HOMA1-IR", "price": 550},
        {"name": "PPBG", "price": 100},
        {"name": "RBG", "price": 120},
    ],
    "Blood Group": [
        {"name": "ABO", "price": 70},
        {"name": "Blood Rh", "price": 90},
        {"name": "Direct Coombs", "price": 250},
        {"name": "Indirect Coombs", "price": 250},
        {"name": "Rh Antibody Titre (In direct", "price": 300},
    ],
    "Blood Picture": [
        {"name": "Hb (hemoglobin)", "price": 130},
        {"name": "Hct", "price": 130},
        {"name": "Hgb And Indices", "price": 70},
        {"name": "Platelets", "price": 200},
        {"name": "RBCs", "price": 150},
        {"name": "WBCs", "price": 100},
        {"name": "WBCs (Diff.)", "price": 150},
        {"name": "Albumin (Body Fluid)", "price": 100},
        {"name": "Beta Trace Protein", "price": 3000},
        {"name": "Chloride (Body Fluid)", "price": 250},
        {"name": "Creatinine (Body Fluid)", "price": 100},
        {"name": "Gene Xpert - MTB/RIF", "price": 3000},
        {"name": "Glucose (Body Fluid)", "price": 80},
        {"name": "LDH (Body Fluid)", "price": 250},
        {"name": "Total Protein (Body Fluid)", "price": 120},
    ],
    "Cardiac Profile": [
        {"name": "Brain Natriuretic Peptide (BNP)", "price": 1200},
        {"name": "CK (MB)", "price": 350},
        {"name": "CK(MM)", "price": 700},
        {"name": "CPK (Total)", "price": 350},
        {"name": "CPK Isoenzymes", "price": 2500},
        {"name": "Homocysteine", "price": 1200},
        {"name": "LDH", "price": 250},
        {"name": "Myoglobin in serum", "price": 350},
        {"name": "Pro-Brain Natriuretic Peptide", "price": 1200},
        {"name": "Troponin (I)", "price": 450},
        {"name": "Troponin (T) high sensitive", "price": 600},
    ],
    "Coagulation Profile": [
        {"name": "Anti-thrombin III Abs", "price": 650},
        {"name": "Bleeding Time", "price": 70},
        {"name": "C5 (Complement. C5)", "price": 1500},
        {"name": "Clotting Time", "price": 70},
        {"name": "Complement. (50%) CH50", "price": 1100},
        {"name": "D-dimer", "price": 750},
        {"name": "Factor II (F, 2)", "price": 1200},
        {"name": "Factor IX  (F. 9)", "price": 1300},
        {"name": "Factor V  (F. 5)", "price": 1300},
        {"name": "Factor VII  (F. 7)", "price": 1350},
        {"name": "Factor VIII  (F. 8)", "price": 1750},
        {"name": "Factor VIII Inhibitor", "price": 1750},
        {"name": "Factor X  (F. 10)", "price": 1450},
        {"name": "Factor XI  (F. 11)", "price": 1300},
        {"name": "Factor XII  (F. 12)", "price": 700},
        {"name": "Factor XIII (F,13)", "price": 1450},
        {"name": "Fibrinogen Level", "price": 300},
        {"name": "Platelet aggregation to ADP", "price": 1500},
        {"name": "Platelet aggregation to", "price": 1500},
        {"name": "PTT", "price": 200},
        {"name": "PTT after mixing studies", "price": 200},
        {"name": "Thrombin Time (TT)", "price": 250},
        {"name": "Von Willebrand Factor (VWF) Conc", "price": 2500},
    ],
    "CSF Chemistry Profile": [
        {"name": "AFP (CSF)", "price": 600},
        {"name": "Albumin (CSF)", "price": 100},
        {"name": "Chloride (CL) in CSF", "price": 250},
        {"name": "CSF examination (Pleural,", "price": 750},
        {"name": "CSF Oligoclonal band", "price": 2500},
        {"name": "Glucose (CSF)", "price": 100},
        {"name": "LDH (CSF)", "price": 250},
        {"name": "Magnesium (Mg) CSF", "price": 260},
        {"name": "Total Protein (CSF)", "price": 120},
    ],
    "Culture and Sensitivity": [
        {"name": "Anal Swab Examination", "price": 100},
        {"name": "Ascitic Fluid Culture", "price": 900},
        {"name": "Ascitic Fluid Culture for Fungi", "price": 450},
        {"name": "Blood Culture", "price": 600},
        {"name": "Body Fluid Culture", "price": 700},
        {"name": "Bone marrow examination", "price": 1000},
        {"name": "Breast Discharge Culture", "price": 450},
        {"name": "Conjuntival Swab Culture", "price": 450},
        {"name": "CSF Culture and Sensitivity", "price": 370},
        {"name": "Fungus C/S", "price": 450},
        {"name": "Gum Discharge Culture", "price": 450},
        {"name": "Left Ear Discharge Culture", "price": 350},
        {"name": "Left Eye discharge Culture", "price": 350},
        {"name": "Nail Culture", "price": 450},
        {"name": "Nasal Swab Culture", "price": 450},
        {"name": "Nasal Swab for MRSA", "price": 450},
        {"name": "POST-COITAL", "price": 450},
        {"name": "Prostatic Discharge Examination", "price": 350},
        {"name": "Prostatic Secreation Culture", "price": 450},
        {"name": "Pus Culture and Sensitivity", "price": 450},
        {"name": "Pus From Wound Culture", "price": 450},
        {"name": "Right Ear Discharge Culture", "price": 450},
        {"name": "Right Eye discharge Culture", "price": 450},
        {"name": "Semen Culture", "price": 350},
        {"name": "Sputum Culture", "price": 450},
        {"name": "Sputum Culture for AFB", "price": 1000},
        {"name": "Stool Culture", "price": 500},
        {"name": "Swab C&S", "price": 450},
        {"name": "Synovial Fluid Culture", "price": 450},
        {"name": "Synovial Fluid Examination", "price": 800},
        {"name": "TB Culture and Sensitivity", "price": 1000},
        {"name": "Throat Swab Culture", "price": 450},
        {"name": "Ulcer Swab C&S", "price": 450},
        {"name": "Urethral Discharge Culture", "price": 450},
        {"name": "Urine Culture", "price": 450},
        {"name": "Vaginal Swab Culture", "price": 450},
        {"name": "Vulval Swab Exam. C&S", "price": 450},
        {"name": "Ziehl Nielsen Stain (one slide)", "price": 150},
    ],
    "Drugs monitoring": [
        {"name": "Cyclosporine (Peak)", "price": 850},
        {"name": "Cyclosporine (Random)", "price": 850},
        {"name": "Cyclosporine (Trough)", "price": 850},
        {"name": "Depakine (Valporic) Random", "price": 450},
        {"name": "Depakine (Valporic) Trough", "price": 450},
        {"name": "Depakine (Valproic) peak", "price": 450},
        {"name": "Digoxin (Lanoxin)", "price": 400},
        {"name": "Everolimus(Certican)", "price": 1900},
        {"name": "Lithium", "price": 400},
        {"name": "Methotrexate", "price": 500},
        {"name": "Phenobarbitone", "price": 200},
        {"name": "Phenytoin (Epanutin, Dilantin)", "price": 500},
        {"name": "Tacrolimus (FK506), Peak", "price": 1500},
        {"name": "Tacrolimus (FK506), Random", "price": 1500},
        {"name": "Tacrolimus (FK506), Trough", "price": 1500},
        {"name": "Tegretol (Carbamazepine) Peak", "price": 400},
        {"name": "Tegretol (Carbamazepine) Random", "price": 400},
        {"name": "Tegretol (Carbamazepine) Trough", "price": 400},
        {"name": "Theophylline", "price": 1200},
        {"name": "Vancomycin", "price": 500},
    ],
    "Drugs Of Abuse": [
        {"name": "Alcohol (In blood)", "price": 900},
        {"name": "Alcohol (In Urine)", "price": 900},
        {"name": "Amphetamine", "price": 250},
        {"name": "Bango (Cannabinoids)", "price": 250},
        {"name": "Barbtiurates", "price": 250},
        {"name": "Benzodiazeipines (Valium)", "price": 250},
        {"name": "Cannabinoids (Hashish, Banjo)", "price": 250},
        {"name": "Cocaine", "price": 250},
        {"name": "Codiene (Opiates)", "price": 250},
        {"name": "Cotonine(Nictoine metabolite)", "price": 1450},
        {"name": "Cotonine(Nictoine metabolite) in", "price": 1450},
        {"name": "Ecstasy", "price": 250},
        {"name": "Hashish (Cannabinoids)", "price": 250},
        {"name": "Heroine (Opiates)", "price": 250},
        {"name": "Marijuana (Cannabinoids)", "price": 250},
        {"name": "Methadone", "price": 250},
        {"name": "Morphin (Opiates)", "price": 250},
        {"name": "Nicotine (tobacco - smoking)", "price": 500},
        {"name": "Opiates (Heroine,codiene)", "price": 250},
        {"name": "Phencyclidine(P.C.P)", "price": 300},
        {"name": "Propoxyphene (PPX)", "price": 250},
        {"name": "Toxicology panel", "price": 1500},
        {"name": "Tramadol In urine", "price": 300},
        {"name": "Tramadol in urine (Quantit)", "price": 650},
    ],
    "Erythrocyte Sedimentation Rate": [
        {"name": "ESR", "price": 120},
    ],
    "Fertility Hormones": [
        {"name": "17-Keto steroids", "price": 1200},
        {"name": "AMH (Anti Mullerian Hormone)", "price": 1300},
        {"name": "Androstenedione", "price": 1350},
        {"name": "Basal FSH (LH-RH Stimulation)", "price": 250},
        {"name": "Basal LH (LH-RH Stimulation)", "price": 250},
        {"name": "Chromosome  Y microdeletions", "price": 7900},
        {"name": "DHEA", "price": 450},
        {"name": "DHEA-S", "price": 450},
        {"name": "DHT (Dihydrotestosterone)", "price": 2500},
        {"name": "E1 (Estrone)", "price": 1700},
        {"name": "E2 (Estradiol)", "price": 300},
        {"name": "E3 (Estriol)", "price": 650},
        {"name": "Erythropoitin (EPO) Ab", "price": 1500},
        {"name": "Free testosterone index", "price": 450},
        {"name": "FSH", "price": 350},
        {"name": "Inhibin A", "price": 2500},
        {"name": "Inhibin B", "price": 2500},
        {"name": "Peak E2 (LH-RH Stimulation)", "price": 300},
        {"name": "Peak FSH (LH-RH Stimulation)", "price": 300},
        {"name": "Peak LH (LH-RH Stimulation)", "price": 300},
        {"name": "Progesterone", "price": 330},
        {"name": "Prolactin (PRL)", "price": 330},
        {"name": "SHBG", "price": 1400},
        {"name": "Testosterone Free", "price": 500},
        {"name": "Testosterone Total", "price": 400},
    ],
    "GENETICS UNIT": [
        {"name": "(MTHFR) gene mutation", "price": 3500},
        {"name": "Babymap (Newborn Screening)", "price": 30000},
        {"name": "Calreticulin Mutation CALR", "price": 5100},
        {"name": "Chromosomal Micrarray Analysis", "price": 25000},
        {"name": "Cystic fibrosis (CFTR gene", "price": 12000},
        {"name": "Double markers", "price": 2300},
        {"name": "Extended metabolic screening", "price": 2750},
        {"name": "Factor V  (Leiden gene study)", "price": 1850},
        {"name": "FISH Choromosome", "price": 2600},
        {"name": "FISH del 11 q", "price": 4000},
        {"name": "FISH del 13 q", "price": 4000},
        {"name": "FISH del 17 p", "price": 5000},
        {"name": "FISH for (11,14) q", "price": 4500},
        {"name": "FISH for 5 q", "price": 4500},
        {"name": "FISH for 7 q", "price": 4500},
        {"name": "Flu Respiratory Panel", "price": 2500},
        {"name": "Huntington chorea PCR", "price": 35000},
        {"name": "Islet Antigen 2 Ab (IA2)", "price": 2800},
        {"name": "Match my genome", "price": 60000},
        {"name": "MYELOPROLIFERATIVE MPL", "price": 4800},
        {"name": "Non Invasive prenatal screening", "price": 23000},
        {"name": "Philadelphia Chromosome PCR", "price": 3500},
        {"name": "Prothrombin Mutation (factor II", "price": 1800},
        {"name": "Quadruple markers", "price": 7000},
        {"name": "Respiratory Panel (bacterial", "price": 3000},
        {"name": "Respiratory Panel (Viral only)", "price": 5000},
        {"name": "Respiratory Panel by PCR", "price": 6500},
        {"name": "Thrombophilia gene Profile", "price": 6500},
        {"name": "Triple markers", "price": 1500},
        {"name": "Whole exome sequencing (WES)", "price": 30000},
    ],
    "GH stimulation test": [
        {"name": "Growth hormone after 0.5 hr", "price": 450},
        {"name": "Growth hormone after 1 hr", "price": 450},
        {"name": "Growth hormone after 1.5 hrs", "price": 450},
        {"name": "Growth hormone after 2 hrs", "price": 450},
    ],
    "Heavy Metals": [
        {"name": "Iodines in serum", "price": 400},
        {"name": "Manganese", "price": 3500},
        {"name": "Mercury (blood)", "price": 1500},
    ],
    "HEMATOLOGY": [
        {"name": "Acidified glycerol lysis test", "price": 250},
        {"name": "CBC", "price": 400},
        {"name": "Cross matching (including viral", "price": 360},
        {"name": "Eosin -5- maleimide binding test", "price": 1500},
        {"name": "Fecal Immunochemical Test (FIT)", "price": 1000},
        {"name": "Fibro test/Acti test", "price": 4000},
        {"name": "Folic acid (RBCs)", "price": 1100},
        {"name": "G6PD (Qualitative)", "price": 400},
        {"name": "G6PD (Quantitative)", "price": 400},
        {"name": "LE cell", "price": 400},
        {"name": "Natural killer cells Funcation", "price": 1500},
        {"name": "Occult Blood In Stool (FOB)", "price": 250},
        {"name": "Procalcitonin (PCT)", "price": 2500},
        {"name": "PRP", "price": 350},
        {"name": "PRP 1", "price": 350},
        {"name": "Retics", "price": 150},
    ],
    "Hemoglobin Electrophoresis": [
        {"name": "HB-A1(Hemoglobin A1", "price": 940},
        {"name": "Hemoglobin electrophoresis by", "price": 600},
        {"name": "Hemoglobin electrophoresis by", "price": 4000},
    ],
    "Hepatitis Markers": [
        {"name": "HAV IgG Ab", "price": 400},
        {"name": "HAV IgM Ab", "price": 400},
        {"name": "HBc IgG", "price": 350},
        {"name": "HBc IgM Ab (Hepatitis B core )", "price": 350},
        {"name": "HBe Ab", "price": 300},
        {"name": "HBe Ag", "price": 300},
        {"name": "HBs Ab", "price": 300},
        {"name": "HBs Ab (Quanti)", "price": 300},
        {"name": "HBs Ag", "price": 300},
        {"name": "HCV IgG", "price": 300},
        {"name": "HCV lgM", "price": 750},
        {"name": "HDV Abs  (total)", "price": 1200},
        {"name": "HDV IgG", "price": 1200},
        {"name": "HDV IgM", "price": 1200},
        {"name": "HEV Ab IgG", "price": 1500},
        {"name": "HEV Ab IgM", "price": 1500},
    ],
    "Immunoglobulins": [
        {"name": "Asperagillus fumigatus abs", "price": 1600},
        {"name": "C2 (Complement 2)", "price": 1650},
        {"name": "C3 (Complement. C3)", "price": 500},
        {"name": "C4 (Complement. C4)", "price": 500},
        {"name": "Complement Level C1q", "price": 1500},
        {"name": "Complement Level CH100", "price": 1100},
        {"name": "ENA Profile", "price": 1800},
        {"name": "Food print IgE (20 test)", "price": 3300},
        {"name": "Food print IgE (30 test)", "price": 5500},
        {"name": "Food print IgG (220 test)", "price": 12500},
        {"name": "Food print IgG (60 test)", "price": 8500},
        {"name": "Haptoglobin", "price": 500},
        {"name": "IgA (Immunoglobulin A)", "price": 400},
        {"name": "IgD (Immunoglobulin D)", "price": 1200},
        {"name": "IgE (Total)", "price": 400},
        {"name": "IgG (Immunoglobulin G)", "price": 350},
        {"name": "IgG Index CSF", "price": 2000},
        {"name": "IgG4", "price": 1500},
        {"name": "IgM (Immunoglobulin M)", "price": 350},
        {"name": "Immunofixation Electrophoresis", "price": 3000},
        {"name": "Immunofixation Electrophoresis", "price": 3000},
    ],
    "IMMUNOLOGY": [
        {"name": "C1 Esterase inhibitor", "price": 1350},
        {"name": "Cholinesterase", "price": 750},
        {"name": "Filaria Abs", "price": 1200},
        {"name": "Interleukin-6", "price": 2500},
        {"name": "Liver Cytosol Antigen Abs.", "price": 800},
        {"name": "TB Gold Quantiferon", "price": 3500},
        {"name": "Thiopurine methyl transferase", "price": 5000},
        {"name": "Tissue Polypeptide Anigen (TPA)", "price": 1200},
        {"name": "Tissue Polypeptide Specific", "price": 1200},
    ],
    "Immunophenotyping": [
        {"name": "Anti Kappa", "price": 700},
        {"name": "Anti Lambda", "price": 700},
        {"name": "CD 10", "price": 1000},
        {"name": "CD 103", "price": 1000},
        {"name": "CD 11c", "price": 1000},
        {"name": "CD 13", "price": 1000},
        {"name": "CD 14", "price": 1000},
        {"name": "CD 16", "price": 1000},
        {"name": "CD 19", "price": 1000},
        {"name": "CD 20", "price": 1000},
        {"name": "CD 200", "price": 1000},
        {"name": "CD 22", "price": 1000},
        {"name": "CD 23", "price": 1000},
        {"name": "CD 25", "price": 1000},
        {"name": "CD 3", "price": 1000},
        {"name": "CD 33", "price": 1000},
        {"name": "CD 34", "price": 1000},
        {"name": "CD 4", "price": 1000},
        {"name": "CD 41", "price": 1000},
        {"name": "CD 5", "price": 1000},
        {"name": "CD 55", "price": 1000},
        {"name": "CD 56", "price": 1000},
        {"name": "CD 59", "price": 1700},
        {"name": "CD 7", "price": 1000},
        {"name": "CD 79a", "price": 1000},
        {"name": "CD 79b", "price": 1000},
        {"name": "CD 8", "price": 1000},
        {"name": "CD38", "price": 1000},
        {"name": "CD4/CD8 Ratio", "price": 1500},
        {"name": "CD56", "price": 1000},
        {"name": "FMC-7", "price": 600},
        {"name": "MPO", "price": 650},
    ],
    "Iron Profile": [
        {"name": "Ferritin", "price": 400},
        {"name": "Iron (Serum)", "price": 320},
        {"name": "Serum Transferrin", "price": 1400},
        {"name": "TIBC", "price": 440},
        {"name": "Transferrin Saturation", "price": 500},
    ],
    "Kidney Profile": [
        {"name": "Albumin / creatinine ratio", "price": 200},
        {"name": "BUN", "price": 120},
        {"name": "Ca++", "price": 220},
        {"name": "Calcium (Total)", "price": 200},
        {"name": "Creatinine (Serum)", "price": 150},
        {"name": "Cystatin C", "price": 1250},
        {"name": "Cystatin C in urine", "price": 2200},
        {"name": "eGFR (Glomerular filtration", "price": 200},
        {"name": "K (Potassium)", "price": 150},
        {"name": "Magnesium (Mg) serum", "price": 260},
        {"name": "Microalbuminuria", "price": 300},
        {"name": "Na (Sodium)", "price": 160},
        {"name": "PO4 (Phosphorus)", "price": 150},
        {"name": "Urea", "price": 120},
        {"name": "Uric Acid", "price": 180},
    ],
    "Lipid Profile": [
        {"name": "Cholesterol", "price": 200},
        {"name": "HDL", "price": 200},
        {"name": "LDL", "price": 200},
        {"name": "Triglycerides", "price": 200},
        {"name": "VLDL", "price": 150},
    ],
    "Liver Profile": [
        {"name": "5- Nucleotidase", "price": 1000},
        {"name": "A/G Ratio", "price": 250},
        {"name": "Albumin (ALB)", "price": 100},
        {"name": "Alkaline Phosphatase (ALP)", "price": 150},
        {"name": "ALT (SGPT)", "price": 150},
        {"name": "AST (SGOT)", "price": 150},
        {"name": "Bilirubin Direct", "price": 100},
        {"name": "Bilirubin Total", "price": 200},
        {"name": "GGT (Gamma-glutamyl transferase)", "price": 200},
        {"name": "Globulin", "price": 200},
        {"name": "Total Protein", "price": 120},
    ],
    "Molecular Biology": [
        {"name": "HLA-B51 by PCR", "price": 2000},
        {"name": "CMV DNA by PCR (Qualit)", "price": 1600},
        {"name": "CMV DNA by PCR (Quanti)", "price": 1600},
        {"name": "Diarrhea Panel (bacterial panel)", "price": 3500},
        {"name": "Diarrhea Panel (Parasitic panel)", "price": 2500},
        {"name": "Diarrhea Panel (Viral panel)", "price": 2500},
        {"name": "Duchenne muscle dystrophy", "price": 2800},
        {"name": "Epstein Barr virus (EBV) by pcr", "price": 1500},
        {"name": "FMF (MEFV Gene Mutation) by PCR", "price": 4000},
        {"name": "FMF by PCR", "price": 4000},
        {"name": "FMF Gene Mutation", "price": 4000},
        {"name": "Fragile X chromosome by PCR", "price": 6000},
        {"name": "HBV - DNA (Qualitative) by PCR", "price": 2000},
        {"name": "HBV - DNA (Quantitative) by PCR", "price": 2000},
        {"name": "HCV - RNA (Qualitative) by PCR", "price": 1500},
        {"name": "HCV - RNA (Quantitative) by PCR", "price": 1500},
        {"name": "HCV genotyping", "price": 2800},
        {"name": "HCV in liver biopsy by (ISH)", "price": 1000},
        {"name": "Herpes family Panel by PCR", "price": 2800},
        {"name": "HGV-RNA by PCR", "price": 1400},
        {"name": "HIV  DNA  by PCR (Qualit)", "price": 5000},
        {"name": "HIV by PCR (Qualit) spain", "price": 6000},
        {"name": "HIV by PCR (Quantit) spain", "price": 6000},
        {"name": "HIV by Western Blott", "price": 4000},
        {"name": "HIV-1 DNA by PCR (Quantit)", "price": 6000},
        {"name": "HLA B27 by PCR", "price": 2000},
        {"name": "HLA B5", "price": 2000},
        {"name": "HLA Class l (ABC) by PCR", "price": 10000},
        {"name": "HLA Class ll (DQ) by PCR", "price": 3500},
        {"name": "HLA Class ll (DR) by PCR", "price": 3500},
        {"name": "HLA-B51/B52 genotype", "price": 3500},
        {"name": "HLA-DQ2/HLA-DQ8", "price": 5000},
        {"name": "HLA-Typing class I (A) by PCR", "price": 3500},
        {"name": "HLA-Typing class I (B) by PCR", "price": 3500},
        {"name": "HLA-Typing class I (C) by PCR", "price": 3500},
        {"name": "HSV (I) DNA by PCR", "price": 1200},
        {"name": "HSV (II) DNA by PCR", "price": 1200},
        {"name": "Human Papilloma Virus (HPV)(28", "price": 3500},
        {"name": "Human Papilloma Virus 16 & 18", "price": 4000},
        {"name": "karyotyping for amniocentesis", "price": 5000},
        {"name": "Karyotyping of Products of", "price": 2200},
        {"name": "Karyotyping study", "price": 1700},
        {"name": "Karyotyping with high resolution", "price": 2300},
        {"name": "Lactose intolerance by PCR", "price": 1600},
        {"name": "Respiratory Syncytial Virus", "price": 2500},
        {"name": "Salmonella typhi  IgG", "price": 700},
        {"name": "Salmonella typhi IgM", "price": 700},
        {"name": "STD Panel by PCR", "price": 5000},
        {"name": "TB - DNA by PCR", "price": 1800},
        {"name": "Triple test for HCV-RNA", "price": 2500},
        {"name": "Vaginal Panel by PCR", "price": 3000},
    ],
    "Pancreas Hormones": [
        {"name": "Aldolase", "price": 950},
        {"name": "Amylase (Urine)", "price": 400},
        {"name": "Amylase in (serum)", "price": 400},
        {"name": "C-Peptide (Fasting)", "price": 850},
        {"name": "C-Peptide (Postprandial)", "price": 850},
        {"name": "C-Peptide (Random)", "price": 850},
        {"name": "C-Peptide (Urine)", "price": 850},
        {"name": "Fecal Pancreatic Elastase 1", "price": 3500},
        {"name": "Gastrin", "price": 2400},
        {"name": "Glucagon", "price": 2700},
        {"name": "Insulin (120 Min.)", "price": 400},
        {"name": "Insulin (180 Min.)", "price": 400},
        {"name": "Insulin (30 Min.)", "price": 400},
        {"name": "Insulin (60 Min.)", "price": 400},
        {"name": "Insulin (Fasting)", "price": 400},
        {"name": "Insulin level (p.p)", "price": 400},
        {"name": "Lipase in serum", "price": 370},
    ],
    "Parathyroid Hormones": [
        {"name": "Parathormone (PTH)", "price": 430},
    ],
    "Pregnancy Tests": [
        {"name": "BHCG (Quantitative)", "price": 400},
        {"name": "Pregnancy in serum Qualit.", "price": 170},
        {"name": "Pregnancy in urine  Qualit.", "price": 150},
    ],
    "Protein Electrophoresis": [
        {"name": "Protein electrophoresis", "price": 750},
        {"name": "Protein Electrophoresis in Urine", "price": 1800},
    ],
    "Semen Examination": [
        {"name": "Alpha Glucosidase in semen", "price": 800},
        {"name": "Beta Galactosidase in semen", "price": 1650},
        {"name": "Fructose in semen", "price": 400},
        {"name": "Semen Examination", "price": 300},
        {"name": "Semen peroxidase", "price": 400},
        {"name": "Sperm DNA fragmentation", "price": 4660},
    ],
    "Separate": [
        {"name": "Acid Phosphatase (Prostatic)", "price": 350},
        {"name": "Acid Phosphatase (Total)", "price": 350},
        {"name": "ACID-FAST STAIN (ZN Film) 3", "price": 300},
        {"name": "Acrosin Activity", "price": 400},
        {"name": "Adenosine Deaminase (ADA) in", "price": 500},
        {"name": "Adenosine Deaminase (ADA) in", "price": 500},
        {"name": "Albumin (Urine)", "price": 100},
        {"name": "Alpha-1 antitrypsin in blood", "price": 750},
        {"name": "Alpha-1 antitrypsin in stool", "price": 950},
        {"name": "Alpha-2 macroglobulin", "price": 950},
        {"name": "Ammonia", "price": 600},
        {"name": "Amyloid A protein", "price": 2300},
        {"name": "Anal adhesive strip", "price": 300},
        {"name": "Angiotensin Converting Enz.", "price": 1200},
        {"name": "Anti Adrenal Ab", "price": 1400},
        {"name": "Anti Diuretic hormone (ADH)", "price": 2000},
        {"name": "Anti Rabies Abs", "price": 2700},
        {"name": "Apolipoprotein  A1", "price": 600},
        {"name": "Apolipoprotein  B", "price": 600},
        {"name": "Aspergillus Galactomannan", "price": 1700},
        {"name": "Bartonnella Henselae", "price": 1060},
        {"name": "Bile Acids, serum", "price": 1600},
        {"name": "Bilharziasis Ag (urine)", "price": 400},
        {"name": "Bilharziasis Antigen (serum)", "price": 400},
        {"name": "Biotinidase Activity", "price": 1400},
        {"name": "Body fluid Examination", "price": 800},
        {"name": "Bone marrow Biobsy", "price": 2000},
        {"name": "Bone marrow Film: Consultation", "price": 700},
        {"name": "Borrelia Burgdorferi IgG Abs", "price": 1300},
        {"name": "Borrelia Burgdorferi IgM Abs", "price": 1300},
        {"name": "Bronchial Lavage Examination C/S", "price": 450},
        {"name": "Bronchial Lavage Film For AFB", "price": 200},
        {"name": "Brucella IgG", "price": 700},
        {"name": "Brucella IgM", "price": 700},
        {"name": "BUN/Creatinine ratio", "price": 220},
        {"name": "Calcium/creatinine ratio", "price": 350},
        {"name": "Calprotectin in stool (Qual)", "price": 1200},
        {"name": "Calprotectin in stool (Quant)", "price": 1750},
        {"name": "Catecholamines Plasma", "price": 2600},
        {"name": "Ceruloplasmin", "price": 550},
        {"name": "Chlamydia lgM", "price": 1000},
        {"name": "Chlamydia pneumonia IgG", "price": 1500},
        {"name": "Chlamydia pneumonia IgM", "price": 1500},
        {"name": "Chlamydia Trachomatis IgG", "price": 1500},
        {"name": "Chlamydia Trachomatis IgM", "price": 1500},
        {"name": "Clostridium difficile", "price": 1700},
        {"name": "Creatinine Clearance", "price": 300},
        {"name": "CRP", "price": 350},
        {"name": "Cryoglobulins", "price": 230},
        {"name": "CSF -Cells", "price": 230},
        {"name": "Cytology Examination", "price": 1100},
        {"name": "DNA by sequencer", "price": 9000},
        {"name": "Dopamine Beta hydroxylase", "price": 1600},
        {"name": "Estrogen Receptors", "price": 1900},
        {"name": "FFAs (Free fatty acid)", "price": 6500},
        {"name": "Filaria Film", "price": 400},
        {"name": "Free light Kappa/Lambda ratio", "price": 2300},
        {"name": "Fructosamine", "price": 400},
        {"name": "Fungus examination by KOH", "price": 250},
        {"name": "Galactose", "price": 1450},
        {"name": "Glycine level", "price": 2700},
        {"name": "Growth Hormone (basal)", "price": 450},
        {"name": "H.pylori Ag in Stool (Quanti)", "price": 650},
        {"name": "H.pylori Line IgG", "price": 1750},
        {"name": "hs-CRP", "price": 300},
        {"name": "IGF-1", "price": 2500},
        {"name": "IGFBP-3", "price": 2500},
        {"name": "Ketone Bodies in Blood", "price": 300},
        {"name": "Kidney profile", "price": 850},
        {"name": "Lactate in blood", "price": 350},
        {"name": "Lamotrigine", "price": 1570},
        {"name": "Leptin", "price": 2500},
        {"name": "Levetiracetam (kepra)", "price": 2020},
        {"name": "Link index parameter", "price": 1700},
        {"name": "Lipid Electrophoresis", "price": 1200},
        {"name": "Lipid profile", "price": 700},
        {"name": "Lipoprotein  a", "price": 1300},
        {"name": "Liver profile", "price": 850},
        {"name": "Malaria Antigen (film)", "price": 350},
        {"name": "Malaria IgG Ab", "price": 1500},
        {"name": "Mumps Abs(IgG)", "price": 1200},
        {"name": "Noradrenaline in urine", "price": 2800},
        {"name": "Organic acid in urine", "price": 3500},
        {"name": "Osteocalcin Level", "price": 1500},
        {"name": "Oxalate (urine)", "price": 1500},
        {"name": "Phenylalanine (PKU)", "price": 1500},
        {"name": "Plasminogen", "price": 2000},
        {"name": "Plasminogen Activator inhibitor", "price": 2000},
        {"name": "Protein C Activity", "price": 1000},
        {"name": "Protein S Activity", "price": 1000},
        {"name": "Protein/creatinine ratio", "price": 250},
        {"name": "Pyruvate Kinase PK", "price": 1000},
        {"name": "Reducing Suger In Stool", "price": 270},
        {"name": "Rota virus antigen", "price": 500},
        {"name": "S.Bicarbonate (blood)", "price": 550},
        {"name": "Sickling test", "price": 400},
        {"name": "Stone Analysis", "price": 550},
        {"name": "Thyroid profie", "price": 870},
        {"name": "Total Lipid", "price": 400},
        {"name": "TPHA", "price": 250},
        {"name": "Urate in Urine", "price": 550},
        {"name": "Urea Breath Test", "price": 2100},
        {"name": "Uric Acid (Urine)", "price": 120},
        {"name": "Uric acid/creatinine ratio", "price": 220},
        {"name": "VDRL", "price": 250},
    ],
    "SEROLOGY": [
        {"name": "Brucella Test", "price": 300},
        {"name": "H.pylori  IgA  (quantit)", "price": 560},
        {"name": "H.pylori  IgG  (qualiti)", "price": 300},
        {"name": "H.pylori  IgG  (quantit)", "price": 550},
        {"name": "H.pylori  IgM  (quantit)", "price": 700},
        {"name": "H.pylori Ag in Stool (Qualit)", "price": 560},
        {"name": "RF (Qualit)", "price": 150},
        {"name": "RF (Quantit)", "price": 250},
        {"name": "Widal Test", "price": 250},
    ],
    "Serum Electrolytes": [
        {"name": "Chloride (CL) in serum", "price": 300},
        {"name": "Osmolality. (serum)", "price": 350},
    ],
    "Stool Examination": [
        {"name": "Stool Examination", "price": 150},
    ],
    "Suprarenal Hormones": [
        {"name": "11-Desoxycortisol", "price": 1800},
        {"name": "17 OH Progesterone", "price": 1800},
        {"name": "5-HIAA (hydroxyindoleacetic", "price": 1500},
        {"name": "ACTH (AM)", "price": 900},
        {"name": "ACTH (PM)", "price": 900},
        {"name": "ACTH (Random)", "price": 900},
        {"name": "ACTH level after Inj.", "price": 900},
        {"name": "Adrenaline (Epinephrine)", "price": 2500},
        {"name": "Aldosterone", "price": 1600},
        {"name": "Catecholamines free fraction", "price": 2500},
        {"name": "Cortisol (AM)", "price": 350},
        {"name": "Cortisol (PM)", "price": 350},
        {"name": "Cortisol (random)", "price": 350},
        {"name": "Cortisol (Urine)", "price": 350},
        {"name": "Cortisol level after Inj.", "price": 350},
        {"name": "Cortisol level before Inj.", "price": 350},
        {"name": "Dopamine", "price": 4000},
        {"name": "Free metanephrine", "price": 3500},
        {"name": "Free Normetanephrine", "price": 3500},
        {"name": "Ghrelin", "price": 4000},
        {"name": "Homovanillic acid (HVA)", "price": 2500},
        {"name": "Metanephrine in urine", "price": 3500},
        {"name": "Noradrenaline (Norepinephrine)", "price": 3000},
        {"name": "Normetanephrine in urine", "price": 3500},
        {"name": "Plasma Renin", "price": 2200},
        {"name": "Serotonin", "price": 3500},
        {"name": "VMA (Urine)", "price": 2000},
    ],
    "Thyroid Hormones": [
        {"name": "Anti Microsomal/peroxidase Ab.", "price": 600},
        {"name": "Anti Thyroid Antibodies", "price": 635},
        {"name": "Anti-Thyroglobulin Abs", "price": 650},
        {"name": "Calcitonin", "price": 1700},
        {"name": "FT3", "price": 270},
        {"name": "FT4", "price": 270},
        {"name": "FTI  (Free Thyroxin Index)", "price": 300},
        {"name": "PBI (Protein Bound Iodine)", "price": 250},
        {"name": "Reverse T3 (rT3)", "price": 2500},
        {"name": "T3 (Total)", "price": 270},
        {"name": "T3 Uptake", "price": 270},
        {"name": "T4 (Total)", "price": 270},
        {"name": "Thyroglobulin (Tg)", "price": 1000},
        {"name": "TSH", "price": 330},
        {"name": "TSH Receptor Ab (Anti-TSHR)", "price": 2000},
    ],
    "TORCH Screen": [
        {"name": "CMV IgG", "price": 350},
        {"name": "CMV IgM", "price": 350},
        {"name": "Epstein Barr virus (EBV - VCA", "price": 650},
        {"name": "Epstein Barr virus (EBV- VCA", "price": 650},
        {"name": "Herpes (I) IgG", "price": 300},
        {"name": "Herpes (I) IgM", "price": 300},
        {"name": "Herpes (II)  IgG", "price": 300},
        {"name": "Herpes (II)  IgM", "price": 300},
        {"name": "Rubella IgG", "price": 300},
        {"name": "Rubella IgM", "price": 300},
        {"name": "Toxo IgG", "price": 300},
        {"name": "Toxo IgM", "price": 300},
        {"name": "Toxo IHA", "price": 120},
    ],
    "Trace Elements": [
        {"name": "Aluminium (blood)", "price": 6000},
        {"name": "Aluminium (Hair)", "price": 2500},
        {"name": "Aluminium (urine)", "price": 6000},
        {"name": "Arsenic (blood)", "price": 5000},
        {"name": "Arsenic (Hair)", "price": 1500},
        {"name": "Cadmium (blood)", "price": 1200},
        {"name": "Cadmium (urine)", "price": 1200},
        {"name": "Chromium (blood)", "price": 550},
        {"name": "Chromium (urine)", "price": 650},
        {"name": "Cobalt (blood)", "price": 1500},
        {"name": "Cobalt (urine)", "price": 1500},
        {"name": "Copper (blood)", "price": 550},
        {"name": "Copper (urine)", "price": 550},
        {"name": "heavy metals (in hair)", "price": 12000},
        {"name": "Lead (blood)", "price": 1500},
        {"name": "Lead (hair)", "price": 2000},
        {"name": "Lead (urine)", "price": 1500},
        {"name": "Mercury (hair)", "price": 1000},
        {"name": "Mercury (urine)", "price": 1500},
        {"name": "Nickel (blood)", "price": 1200},
        {"name": "Nickel (urine)", "price": 1200},
        {"name": "Selenium (blood)", "price": 5000},
        {"name": "Selenium (urine)", "price": 5000},
        {"name": "Water Examination", "price": 1500},
        {"name": "Water Examination (chemical)", "price": 1000},
        {"name": "Zinc (blood)", "price": 550},
        {"name": "Zinc (urine)", "price": 550},
    ],
    "Tumors Markers": [
        {"name": "AFP", "price": 600},
        {"name": "B2 Microglobulin (Serum)", "price": 600},
        {"name": "B2 Microglobulin (Urine)", "price": 1000},
        {"name": "Bcl - 2", "price": 1000},
        {"name": "BCR-ABL by FISH", "price": 1600},
        {"name": "BCR-ABL by PCR", "price": 5000},
        {"name": "BHCG (TUMOR MARKER)", "price": 400},
        {"name": "BRCA 1 ,2 gene mutation", "price": 19000},
        {"name": "CA 125", "price": 650},
        {"name": "CA 15.3", "price": 650},
        {"name": "CA 19.9", "price": 650},
        {"name": "CA 27.29", "price": 5000},
        {"name": "CA 27.29 Antigen", "price": 4500},
        {"name": "CA 50", "price": 4000},
        {"name": "CA 72.4", "price": 4500},
        {"name": "CEA (Carcinoembryonic Antigen)", "price": 550},
        {"name": "IGHV by Fish", "price": 4000},
        {"name": "Jak - 2 Exon 12 Mutation", "price": 2500},
        {"name": "Jak - 2(V617F)", "price": 2500},
        {"name": "Kappa light chain in serum", "price": 1500},
        {"name": "Kappa light chain in urine", "price": 1800},
        {"name": "Lambda Light Chain in serum", "price": 1300},
        {"name": "Lambda Light Chain in urine", "price": 1600},
        {"name": "NSE", "price": 1500},
        {"name": "Pap Smear", "price": 1300},
        {"name": "Pathological Examination", "price": 2500},
        {"name": "PSA (Free)", "price": 450},
        {"name": "PSA (Total)", "price": 300},
        {"name": "PSA Ratio", "price": 800},
        {"name": "Schebo test (M2-PK)", "price": 2500},
        {"name": "Urinary Bladder Cancer (UBC)", "price": 1800},
    ],
    "Urine Electrolytes": [
        {"name": "Calcium (Ca) urine", "price": 220},
        {"name": "Chloride (CL) in urine", "price": 300},
        {"name": "Citrate (urine)", "price": 1350},
        {"name": "Magnesium (Mg) in urine", "price": 260},
        {"name": "Osmolality. (urine)", "price": 350},
        {"name": "Phosphorus (Ph) urine", "price": 150},
        {"name": "Potassium (k) urine", "price": 150},
        {"name": "Sodium (Na) urine", "price": 170},
    ],
    "Urine Examination": [
        {"name": "Amino Acids in urine", "price": 3500},
        {"name": "Bence jones protein (Urine)", "price": 250},
        {"name": "Creatinine (urine)", "price": 150},
        {"name": "Dysmorphic RBCs in urine", "price": 300},
        {"name": "Free light Kappa/Lambda in Urine", "price": 3500},
        {"name": "Protein in urine", "price": 150},
        {"name": "STROX in urine", "price": 400},
        {"name": "Urine Examination", "price": 120},
    ],
    "Virology": [
        {"name": "Adeno Virus Ab", "price": 500},
        {"name": "Bartonnella Henselae", "price": 1060},
        {"name": "EBV  (IgG)", "price": 450},
        {"name": "EBV  (IgM)", "price": 450},
        {"name": "EBV- EBNA (IgG)", "price": 450},
        {"name": "EBV- EBNA (IgM)", "price": 450},
        {"name": "Entero Virus (Coxsackie A9) IgG", "price": 1800},
        {"name": "Entero Virus (Coxsackie A9) IgM", "price": 1800},
        {"name": "Entero Virus (Coxsackie B1-6)", "price": 1800},
        {"name": "Entero Virus (Coxsackie B1-6)", "price": 1800},
        {"name": "H1N1 by Real Time PCR", "price": 2500},
        {"name": "HIV (I,II) Abs", "price": 450},
        {"name": "HIV Combi Ag/Ab", "price": 500},
        {"name": "Human Papilloma Virus (IgG) HPV", "price": 4000},
        {"name": "Malaria IgM Ab", "price": 1500},
        {"name": "Measles IgG", "price": 1400},
        {"name": "Measles IgM", "price": 1400},
        {"name": "Mumps Abs(IgM)", "price": 1200},
        {"name": "Spike Corona IgG Abs", "price": 600},
        {"name": "Spike Corona IgM Abs", "price": 600},
        {"name": "Varicella Zoster (IgA)", "price": 1200},
        {"name": "Varicella Zoster (IgG)", "price": 1200},
        {"name": "Varicella Zoster (IgM)", "price": 1300},
        {"name": "Viral Ag (Rapid test)", "price": 700},
        {"name": "Viral PCR-RNA (Qualitative)", "price": 1700},
        {"name": "Viral PCR-RNA (Qualitative)", "price": 1500},
        {"name": "Viral PCR-RNA (Urgently)", "price": 2800},
    ],
    "Vitamins": [
        {"name": "Ascorbic acid in plasma (vitamin", "price": 6000},
        {"name": "Biotin (Vitamin H/ B7 /B8)", "price": 7500},
        {"name": "Folate (Folic Acid) serum", "price": 1200},
        {"name": "Index Omega 3", "price": 7000},
        {"name": "Lactoferrin", "price": 2000},
        {"name": "Vitamin A", "price": 4500},
        {"name": "Vitamin B1", "price": 7000},
        {"name": "Vitamin B12", "price": 1500},
        {"name": "Vitamin B2", "price": 6000},
        {"name": "Vitamin B3", "price": 6000},
        {"name": "Vitamin B5", "price": 8000},
        {"name": "Vitamin B6", "price": 6000},
        {"name": "Vitamin C", "price": 6000},
        {"name": "Vitamin D2 (1,25 Dihydroxy)", "price": 2000},
        {"name": "Vitamin D3(25 Hydroxy Cholecal.)", "price": 1000},
        {"name": "Vitamin E", "price": 6000},
        {"name": "Vitamin K", "price": 6000},
    ],
}

ALL_LABS = [{"name": t["name"], "price": t["price"], "category": cat}
            for cat, tests in LABS_DB.items() for t in tests]

# ─── Helper functions ────────────────────────────────────────────────────────
def format_date_ar(d):
    if not d:
        return ""
    if isinstance(d, str):
        try:
            d = datetime.strptime(d, "%Y-%m-%d").date()
        except:
            return d
    months = ["يناير","فبراير","مارس","أبريل","مايو","يونيو",
              "يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"]
    return f"{d.day} {months[d.month-1]} {d.year}"

def make_whatsapp_msg(v, target="internal"):
    labs_price_before = v.get("labs_price_before", 0)
    labs_price_after  = v.get("labs_price_after", 0)
    transport_fee     = v.get("transport_fee", 0)
    total             = v.get("total_price", 0)
    visit_date        = format_date_ar(v.get("visit_date", ""))
    visit_time        = v.get("visit_time", "")
    datetime_str      = f"{visit_date}" + (f" — {visit_time}" if visit_time else "")
    doc_name          = v.get("doctor_name", "غير محدد")
    address           = v.get("address", "")
    location          = v.get("location_link", "")
    branch            = v.get("branch", "")

    labs_text = v.get("selected_labs_text", "")
    if labs_text.strip():
        labs_lines = "\n".join(f"🧪 {l.strip()}" for l in labs_text.splitlines() if l.strip()) + "\n"
    else:
        labs_lines = "🚫 لا توجد تحاليل\n"

    loc_line = f"📍 *الموقع:* {location}\n" if location else ""
    branch_line = f"🏥 *الفرع:* {branch}\n" if branch else ""

    if target == "client":
        return (
            f"🟠 *Orange Lab Home Visit*\n"
            f"🏠 أهلاً بك\n"
            f"━━━━━━━━━━━━━━\n"
            f"👨‍⚕️ *الدكتور القائم بالزيارة:* {doc_name}\n"
            f"📅 *موعد الزيارة:* {datetime_str}\n"
            f"━━━━━━━━━━━━━━\n"
            f"📍 *عنوان الزيارة:*\n{address}\n"
            f"{loc_line}"
            f"{branch_line}"
            f"━━━━━━━━━━━━━━\n"
            f"🧪 *التحاليل المطلوبة:*\n{labs_lines}"
            f"━━━━━━━━━━━━━━\n"
            f"💰 *السعر قبل الخصم:* {labs_price_before} جنيه\n"
            f"💰 *السعر بعد الخصم:* {labs_price_after} جنيه\n"
            f"🚗 *بدل الانتقال:* {transport_fee} جنيه\n"
            f"💵 *الإجمالي المطلوب:* {total} جنيه\n"
            f"━━━━━━━━━━━━━━\n"
            f"✏️ *برجاء تأكيد حجزك بالرد برقم:*\n"
            f"  1️⃣ - تأكيد الزيارة\n"
            f"  2️⃣ - تأجيل الزيارة\n"
            f"  3️⃣ - إلغاء الزيارة\n\n"
            f"شكراً لثقتكم 🧡 *معمل أورانج لاب*"
        )
    elif target == "group":
        return (
            f"🟠 *زيارة منزلية*\n"
            f"━━━━━━━━━━━━━━\n"
            f"👨‍⚕️ *الدكتور القائم بالزيارة:* {doc_name}\n"
            f"📅 *الموعد:* {datetime_str}"
        )
    else:   # internal
        notes = f"📝 *ملاحظات:* {v.get('notes','')}\n" if v.get("notes") else ""
        return (
            f"🟠 *Orange Lab Home Visit*\n"
            f"━━━━━━━━━━━━━━\n"
            f"👤 *الاسم:* {v['name']}\n"
            f"🎂 *السن:* {v.get('age','')} سنة\n"
            f"📞 *التليفون:* {v.get('phone','')}\n"
            f"📅 *الموعد:* {datetime_str}\n"
            f"👨‍⚕️ *دكتور الزيارة:* {doc_name}\n"
            f"🏥 *الفرع:* {branch}\n"
            f"━━━━━━━━━━━━━━\n"
            f"📍 *العنوان:* {address}\n"
            f"{loc_line}"
            f"━━━━━━━━━━━━━━\n"
            f"🧪 *التحاليل المطلوبة:*\n{labs_lines}"
            f"━━━━━━━━━━━━━━\n"
            f"💰 *السعر قبل الخصم:* {labs_price_before} جنيه\n"
            f"💰 *السعر بعد الخصم:* {labs_price_after} جنيه\n"
            f"🚗 *بدل الانتقال:* {transport_fee} جنيه\n"
            f"💵 *الإجمالي:* {total} جنيه\n"
            f"━━━━━━━━━━━━━━\n"
            f"{notes}"
        )

def whatsapp_link(msg, phone=None):
    encoded = urllib.parse.quote(msg, encoding='utf-8')  # ← quote مش quote_plus
    if phone:
        p = phone.strip().replace(" ", "").replace("-", "").replace("+", "")
        if p.startswith("0"):
            p = "20" + p[1:]
        elif not p.startswith("20"):
            p = "20" + p
        return f"https://wa.me/{p}?text={encoded}"
    return f"https://wa.me/?text={encoded}"

# ─── Session State ──────────────────────────────────────────────────────────
for k, v in [("page", "home"), ("prefill", {}), ("selected_id", None), ("search_q", "")]:
    if k not in st.session_state:
        st.session_state[k] = v

def go(page, prefill=None, visit_id=None):
    st.session_state.page = page
    if prefill is not None:
        st.session_state.prefill = prefill
    if visit_id is not None:
        st.session_state.selected_id = visit_id
    st.rerun()

# ─── Header ─────────────────────────────────────────────────────────────────
st.markdown(f'''
<div class="ohv-header">
  <h1>🟠 Orange Lab Home Visit</h1>
  <span>📅 {format_date_ar(date.today())}</span>
</div>
''', unsafe_allow_html=True)

col1, col2, col3, col4 = st.columns(4)
with col1:
    if st.button("🏠 الرئيسية", use_container_width=True): go("home")
with col2:
    if st.button("➕ زيارة جديدة", use_container_width=True): go("new", prefill={})
with col3:
    if st.button("🔍 بحث", use_container_width=True): go("search")
with col4:
    if st.button("📊 التقارير", use_container_width=True): go("reports")
st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# HOME
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.page == "home":
    # Get unique doctors and branches for filter
    conn = get_connection()
    all_doctors = [row[0] for row in conn.execute("SELECT DISTINCT doctor_name FROM visits WHERE doctor_name != ''").fetchall()]
    all_branches = [row[0] for row in conn.execute("SELECT DISTINCT branch FROM visits").fetchall()]
    if "الكل" not in all_branches:
        all_branches.insert(0, "الكل")
    if "الكل" not in all_doctors:
        all_doctors.insert(0, "الكل")

    st.markdown("### تصفية الزيارات")
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        selected_branch = st.selectbox("الفرع", options=all_branches, index=0)
    with col_f2:
        selected_doctor = st.selectbox("الدكتور", options=all_doctors, index=0)
    with col_f3:
        search_query = st.text_input("بحث بالاسم أو التليفون", value=st.session_state.search_q, placeholder="ابحث...")
        st.session_state.search_q = search_query

    filters = {}
    if selected_branch != "الكل":
        filters["branch"] = selected_branch
    if selected_doctor != "الكل":
        filters["doctor"] = selected_doctor
    if search_query:
        filters["search"] = search_query

    visits = fetch_visits(filters)
    today = date.today().isoformat()
    t_visits = len(visits)
    # For stats we fetch all visits without filters to get total counts
    all_visits = fetch_visits()  # unfiltered
    t_today = sum(1 for v in all_visits if v.get("visit_date") == today)
    t_rev = sum(v.get("total_price", 0) for v in all_visits)

    st.markdown(f'''
    <div class="stat-grid">
      <div class="stat-box"><div class="stat-num">{len(all_visits)}</div><div class="stat-label">إجمالي الزيارات</div></div>
      <div class="stat-box"><div class="stat-num">{t_today}</div><div class="stat-label">زيارات اليوم</div></div>
      <div class="stat-box"><div class="stat-num" style="font-size:17px">{t_rev:,}</div><div class="stat-label">الإيراد (جنيه)</div></div>
    </div>''', unsafe_allow_html=True)

    if not visits:
        st.info("لا توجد زيارات تطابق التصفية.")
    else:
        for v in visits:
            total = v.get("total_price", 0)
            vdate = format_date_ar(v.get("visit_date", ""))
            addr = (v.get("address", "") or "")[:38] + ("..." if len(v.get("address", "") or "") > 38 else "")
            labs_count = len(v.get("selected_labs_text", "").splitlines()) if v.get("selected_labs_text") else 0
            doctor_show = f" | 👨‍⚕️ {v.get('doctor_name','')}" if v.get("doctor_name") else ""
            branch_show = f" | 🏥 {v.get('branch','')}" if v.get("branch") else ""
            st.markdown(f'''
            <div class="visit-card">
              <span class="visit-badge">{total:,} جنيه</span>
              <div class="visit-name">👤 {v["name"]}</div>
              <div class="visit-meta">📞 {v.get("phone","")} &nbsp;|&nbsp; 📅 {vdate}</div>
              <div class="visit-meta">📍 {addr}</div>
              <div class="visit-meta" style="margin-top:5px">🧪 {labs_count} تحليل{doctor_show}{branch_show}</div>
            </div>''', unsafe_allow_html=True)
            if st.button(f"📂 فتح {v['name']}", key=f"o_{v['id']}", use_container_width=True):
                go("detail", visit_id=v["id"])

    st.markdown("""
    <div style="text-align:center;margin-top:50px;padding-top:20px;border-top:1px solid #ffe8d1;color:#aaa;font-size:13px;font-weight:600;">
      Developed with <span style="color:#FF6B00;">❤️</span> by <b>Dr. Hussein Ali</b> — 2026
    </div>
    """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# NEW VISIT
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "new":
    pf = st.session_state.prefill or {}
    is_edit = pf.get("_edit", False)
    st.markdown(f"### {'✏️ تعديل الزيارة' if is_edit else '➕ زيارة جديدة'}")

    st.markdown('<div class="section-title">👤 البيانات الشخصية</div>', unsafe_allow_html=True)
    name = st.text_input("الاسم الكامل *", value=pf.get("name", ""))
    c1, c2 = st.columns(2)
    with c1:
        age = st.number_input("السن *", 0, 120, int(pf.get("age", 0) or 0))
    with c2:
        phone = st.text_input("رقم التليفون *", value=pf.get("phone", ""), placeholder="01xxxxxxxxx")

    doctor_name = st.text_input("👨‍⚕️ الدكتور القائم بالزيارة", value=pf.get("doctor_name", ""))
    branch = st.selectbox("🏥 الفرع", options=["La Cite", "Diamond"],
                          index=0 if pf.get("branch", "La Cite") == "La Cite" else 1)

    d1, d2 = st.columns(2)
    with d1:
        default_date = date.today()
        if pf.get("visit_date"):
            try:
                default_date = datetime.strptime(pf["visit_date"], "%Y-%m-%d").date()
            except:
                pass
        visit_date = st.date_input("📅 تاريخ الزيارة *", value=default_date)
    with d2:
        visit_time = st.text_input("🕐 وقت الزيارة", value=pf.get("visit_time", ""), placeholder="مثال: 2:00 PM")
    st.markdown("---")

    st.markdown('<div class="section-title">📍 العنوان</div>', unsafe_allow_html=True)
    address = st.text_area("العنوان بالتفصيل *", value=pf.get("address", ""),
                           placeholder="المحافظة - المدينة - الشارع - رقم المبنى - الدور - الشقة...", height=90)
    location_link = st.text_input("🗺️ رابط الموقع (Google Maps)", value=pf.get("location_link", ""))
    st.markdown("---")

    visit_id_key = pf.get("id", "new_visit")
    labs_ss_key = f"added_labs_{visit_id_key}"
    search_ss_key = f"lab_search_{visit_id_key}"

    if labs_ss_key not in st.session_state:
        if pf.get("selected_labs_text", ""):
            st.session_state[labs_ss_key] = [l.strip() for l in pf["selected_labs_text"].splitlines() if l.strip()]
        else:
            st.session_state[labs_ss_key] = []
    if search_ss_key not in st.session_state:
        st.session_state[search_ss_key] = ""

    st.markdown('<div class="section-title">🔍 ابحث وأضف من قائمة الأسعار</div>', unsafe_allow_html=True)
    st.caption("💰 = يضاف مع السعر  |  📋 = يضاف بدون سعر")

    price_search = st.text_input("ابحث باسم التحليل", value=st.session_state[search_ss_key],
                                 placeholder="مثال: CBC أو سكر أو Vitamin D...", key=f"search_input_{visit_id_key}")
    st.session_state[search_ss_key] = price_search

    if price_search:
        results = [l for l in ALL_LABS if price_search.lower() in l["name"].lower()]
        if results:
            st.caption(f"🔎 {len(results)} نتيجة:")
            for r in results[:12]:
                c_name, c_price, c_priced, c_plain = st.columns([5, 2, 1, 1])
                with c_name:
                    st.markdown(f'<div style="padding:6px 2px;font-size:13px;color:#222">🧪 {r["name"]}</div>', unsafe_allow_html=True)
                with c_price:
                    st.markdown(f'<div style="padding:6px 2px;font-size:13px;font-weight:700;color:#FF6B00">{r["price"]:,} جنيه</div>', unsafe_allow_html=True)
                with c_priced:
                    if st.button("💰", key=f"ap_{visit_id_key}_{r['name']}", help="أضف مع السعر"):
                        entry = f"{r['name']} — {r['price']} جنيه"
                        if entry not in st.session_state[labs_ss_key]:
                            st.session_state[labs_ss_key].append(entry)
                        st.rerun()
                with c_plain:
                    if st.button("📋", key=f"an_{visit_id_key}_{r['name']}", help="أضف بدون سعر"):
                        entry = r["name"]
                        if entry not in st.session_state[labs_ss_key]:
                            st.session_state[labs_ss_key].append(entry)
                        st.rerun()
            if len(results) > 12:
                st.caption(f"+ {len(results)-12} نتيجة أخرى")
        else:
            st.info("لا توجد نتائج — جرب كلمة تانية")
    st.markdown("---")

    st.markdown('<div class="section-title">🧪 التحاليل المضافة</div>', unsafe_allow_html=True)
    if st.session_state[labs_ss_key]:
        import re as _re
        auto_total = sum(int(m.group(1)) for e in st.session_state[labs_ss_key] for m in [_re.search(r'(\d+)\s*جنيه', e)] if m)
        st.markdown(f'<div style="font-size:12px;color:#FF6B00;font-weight:700;margin-bottom:8px">✅ {len(st.session_state[labs_ss_key])} تحليل{"  —  إجمالي: " + f"{auto_total:,} جنيه" if auto_total else ""}</div>', unsafe_allow_html=True)
        to_remove = None
        for i, entry in enumerate(st.session_state[labs_ss_key]):
            ca, cb = st.columns([10, 1])
            with ca:
                st.markdown(f'<div style="font-size:13px;padding:4px 0;border-bottom:1px solid #f5f5f5;color:#333">🔹 {entry}</div>', unsafe_allow_html=True)
            with cb:
                if st.button("✕", key=f"del_{visit_id_key}_{i}", help="احذف"):
                    to_remove = i
        if to_remove is not None:
            st.session_state[labs_ss_key].pop(to_remove)
            st.rerun()
        if st.button("🗑️ مسح الكل", key=f"clear_{visit_id_key}"):
            st.session_state[labs_ss_key] = []
            st.rerun()
    else:
        st.markdown('<div style="color:#aaa;font-size:13px;padding:8px 0">لا توجد تحاليل — ابحث وأضف من فوق أو أضف يدوياً</div>', unsafe_allow_html=True)

    col_m1, col_m2 = st.columns([8, 2])
    with col_m1:
        manual_entry = st.text_input("أو أضف يدوياً", placeholder="CBC — 400 جنيه  أو  سكر صائم", key=f"manual_{visit_id_key}")
    with col_m2:
        st.markdown('<div style="margin-top:28px"></div>', unsafe_allow_html=True)
        if st.button("➕ أضف", key=f"manual_btn_{visit_id_key}", use_container_width=True):
            if manual_entry.strip():
                st.session_state[labs_ss_key].append(manual_entry.strip())
                st.rerun()

    selected_labs_text = "\n".join(st.session_state[labs_ss_key])
    selected_labs = st.session_state[labs_ss_key][:]
    st.markdown("---")

    st.markdown('<div class="section-title">📌 ملاحظات</div>', unsafe_allow_html=True)
    notes = st.text_area("ملاحظات خاصة", value=pf.get("notes", ""), height=75)
    st.markdown("---")

    st.markdown('<div class="section-title">💰 الأسعار</div>', unsafe_allow_html=True)
    import re as _re2
    auto_labs_total = sum(int(m.group(1)) for e in selected_labs for m in [_re2.search(r'(\d+)\s*جنيه', e)] if m)

    p1, p2, p3 = st.columns(3)
    with p1:
        labs_price_before = st.number_input("⭐ السعر قبل الخصم", min_value=0, step=10,
                                            value=auto_labs_total if auto_labs_total > 0 else int(pf.get("labs_price_before", 0) or 0))
    with p2:
        labs_price_after = st.number_input("⭐ السعر بعد الخصم", min_value=0, step=10,
                                           value=int(pf.get("labs_price_after", 0) or 0))
    with p3:
        transport_fee = st.number_input("⭐ بدل الانتقال", min_value=0, step=10,
                                        value=int(pf.get("transport_fee", 100) or 100))
    total_price = labs_price_after + transport_fee
    st.markdown(f'''
    <div class="price-box">
      <div class="price-row"><span>⭐ السعر قبل الخصم</span><span>{labs_price_before} جنيه</span></div>
      <div class="price-row"><span>⭐ السعر بعد الخصم</span><span>{labs_price_after} جنيه</span></div>
      <div class="price-row"><span>⭐ بدل الانتقال</span><span>{transport_fee} جنيه</span></div>
      <div class="price-total"><span>⭐ الإجمالي</span><span>{total_price} جنيه</span></div>
    </div>''', unsafe_allow_html=True)

    if st.button("💾 حفظ الزيارة" if not is_edit else "💾 حفظ التعديلات", use_container_width=True):
        if not name or not phone or not address:
            st.error("⚠️ من فضلك املأ الاسم والتليفون والعنوان")
        else:
            record = {
                "id": pf.get("id", str(int(datetime.now().timestamp() * 1000))),
                "created_at": pf.get("created_at", datetime.now().isoformat()),
                "name": name,
                "age": age,
                "phone": phone,
                "visit_date": visit_date.isoformat(),
                "visit_time": visit_time,
                "doctor_name": doctor_name,
                "branch": branch,
                "address": address,
                "location_link": location_link,
                "selected_labs_text": selected_labs_text,
                "notes": notes,
                "labs_price_before": labs_price_before,
                "labs_price_after": labs_price_after,
                "transport_fee": transport_fee,
                "total_price": total_price,
            }
            if is_edit:
                update_visit(record)
                st.success("✅ تم تحديث الزيارة!")
            else:
                insert_visit(record)
                st.success("✅ تم حفظ الزيارة!")
            go("detail", visit_id=record["id"])

    if is_edit:
        if st.button("← رجوع بدون حفظ", use_container_width=True):
            go("detail", visit_id=pf.get("id"))

# ══════════════════════════════════════════════════════════════════════════════
# DETAIL
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "detail":
    vid = st.session_state.selected_id
    v = fetch_visit_by_id(vid) if vid else None
    if not v:
        st.error("لم يتم العثور على الزيارة")
        go("home")
    else:
        labs_price_before = v.get("labs_price_before", 0)
        labs_price_after  = v.get("labs_price_after", 0)
        transport_fee     = v.get("transport_fee", 0)
        total_price       = v.get("total_price", 0)
        visit_time        = v.get("visit_time", "")
        datetime_display  = format_date_ar(v.get("visit_date", "")) + (f" — {visit_time}" if visit_time else "")

        st.markdown('<div class="section-title">👤 البيانات الشخصية</div>', unsafe_allow_html=True)
        st.markdown(f'''
        <div class="detail-row"><span class="detail-label">👤 الاسم</span><span class="detail-value">{v["name"]}</span></div>
        <div class="detail-row"><span class="detail-label">🎂 السن</span><span class="detail-value">{v.get("age","")} سنة</span></div>
        <div class="detail-row"><span class="detail-label">📞 التليفون</span><span class="detail-value">{v.get("phone","")}</span></div>
        <div class="detail-row"><span class="detail-label">📅 الموعد</span><span class="detail-value">{datetime_display}</span></div>
        <div class="detail-row"><span class="detail-label">👨‍⚕️ الدكتور</span><span class="detail-value">{v.get("doctor_name","")}</span></div>
        <div class="detail-row"><span class="detail-label">🏥 الفرع</span><span class="detail-value">{v.get("branch","")}</span></div>
        ''', unsafe_allow_html=True)
        st.markdown("---")

        st.markdown('<div class="section-title">📍 العنوان</div>', unsafe_allow_html=True)
        st.write(v.get("address", ""))
        if v.get("location_link"):
            st.markdown(f'<a href="{v["location_link"]}" target="_blank" style="color:#FF6B00;font-weight:700;">🗺️ فتح الموقع على الخريطة</a>', unsafe_allow_html=True)
        st.markdown("---")

        labs_text = v.get("selected_labs_text", "")
        if labs_text.strip():
            st.markdown('<div class="section-title">🧪 التحاليل المطلوبة</div>', unsafe_allow_html=True)
            lines_html = "".join(f'<div class="detail-row"><span class="detail-label">🔹 {l.strip()}</span></div>' for l in labs_text.splitlines() if l.strip())
            st.markdown(f'<div style="background:#fffaf6;border-radius:12px;padding:8px 14px;border:1px solid #ffe8d1">{lines_html}</div>', unsafe_allow_html=True)
            st.markdown("---")

        st.markdown(f'''
        <div class="price-box">
          <div class="price-row"><span>⭐ السعر قبل الخصم</span><span>{labs_price_before} جنيه</span></div>
          <div class="price-row"><span>⭐ السعر بعد الخصم</span><span>{labs_price_after} جنيه</span></div>
          <div class="price-row"><span>⭐ بدل الانتقال</span><span>{transport_fee} جنيه</span></div>
          <div class="price-total"><span>⭐ الإجمالي</span><span>{total_price} جنيه</span></div>
        </div>''', unsafe_allow_html=True)

        if v.get("notes"):
            st.markdown('<div class="section-title">📌 ملاحظات</div>', unsafe_allow_html=True)
            st.write(v["notes"])
            st.markdown("---")

        st.markdown('<div class="section-title">📱 إرسال على واتساب</div>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f'<a href="{whatsapp_link(make_whatsapp_msg(v, "client"), v.get("phone"))}" target="_blank" class="wa-btn wa-client">📱 واتساب العميل</a>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<a href="{whatsapp_link(make_whatsapp_msg(v, "group"))}" target="_blank" class="wa-btn wa-group">👥 جروب العمل</a>', unsafe_allow_html=True)
        with c3:
            st.markdown(f'<a href="{whatsapp_link(make_whatsapp_msg(v, "internal"))}" target="_blank" class="wa-btn wa-share">📋 ملخص الزيارة</a>', unsafe_allow_html=True)
        st.markdown("---")

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✏️ تعديل", use_container_width=True):
                go("new", prefill={**v, "_edit": True})
        with c2:
            if st.button("🗑️ حذف", use_container_width=True):
                st.session_state["confirm_delete"] = True

        if st.session_state.get("confirm_delete"):
            st.warning("⚠️ هل أنت متأكد من الحذف؟")
            cc1, cc2 = st.columns(2)
            with cc1:
                if st.button("✅ نعم، احذف", use_container_width=True):
                    delete_visit(vid)
                    st.session_state["confirm_delete"] = False
                    go("home")
            with cc2:
                if st.button("❌ إلغاء", use_container_width=True):
                    st.session_state["confirm_delete"] = False
                    st.rerun()

        st.markdown(f'<div class="repeat-banner">🔄 هتروح لـ {v["name"]} مرة تانية؟</div>', unsafe_allow_html=True)
        if st.button(f"➕ زيارة جديدة لـ {v['name']}", use_container_width=True):
            go("new", prefill={
                "name": v["name"], "age": v.get("age", ""), "phone": v.get("phone", ""),
                "address": v.get("address", ""), "location_link": v.get("location_link", ""),
                "doctor_name": v.get("doctor_name", ""), "branch": v.get("branch", "La Cite"),
                "selected_labs": [], "selected_labs_text": "", "visit_time": "",
                "notes": "", "labs_price_before": 0, "labs_price_after": 0, "transport_fee": 100
            })
        if st.button("← رجوع للقائمة", use_container_width=True):
            go("home")

# ══════════════════════════════════════════════════════════════════════════════
# SEARCH
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "search":
    st.markdown("### 🔍 البحث عن عميل")
    query = st.text_input("اكتب الاسم أو التليفون", placeholder="مثال: محمد أو 01012345678")
    if query:
        visits = fetch_visits({"search": query})
        st.markdown(f"**{len(visits)} نتيجة**")
        for v in visits:
            total = v.get("total_price", 0)
            vdate = format_date_ar(v.get("visit_date", ""))
            st.markdown(f'''
            <div class="visit-card">
              <span class="visit-badge">{total:,} جنيه</span>
              <div class="visit-name">👤 {v["name"]}</div>
              <div class="visit-meta">📞 {v.get("phone","")} &nbsp;|&nbsp; 📅 {vdate}</div>
            </div>''', unsafe_allow_html=True)
            if st.button(f"📂 فتح {v['name']}", key=f"s_{v['id']}", use_container_width=True):
                go("detail", visit_id=v["id"])

# ══════════════════════════════════════════════════════════════════════════════
# REPORTS
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.page == "reports":
    st.markdown("### 📊 تقارير نهاية الشهر")
    col_y, col_m, col_b = st.columns(3)
    with col_y:
        year = st.selectbox("السنة", options=list(range(2023, 2031)), index=3)  # 2026
    with col_m:
        month = st.selectbox("الشهر", options=list(range(1, 13)),
                             format_func=lambda m: ["يناير","فبراير","مارس","أبريل","مايو","يونيو",
                                                     "يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"][m-1],
                             index=date.today().month - 1)
    with col_b:
        branch_filter = st.selectbox("الفرع", options=["الكل", "La Cite", "Diamond"])

    filters = {"year": year, "month": month}
    if branch_filter != "الكل":
        filters["branch"] = branch_filter

    visits = fetch_visits(filters)

    if not visits:
        st.info("لا توجد زيارات في هذا الشهر / الفرع.")
    else:
        # Build summary per doctor
        summary = {}
        for v in visits:
            doc = v.get("doctor_name", "غير محدد")
            if doc not in summary:
                summary[doc] = {"count": 0, "before": 0, "after": 0, "transport": 0, "total": 0}
            summary[doc]["count"] += 1
            summary[doc]["before"] += v.get("labs_price_before", 0)
            summary[doc]["after"] += v.get("labs_price_after", 0)
            summary[doc]["transport"] += v.get("transport_fee", 0)
            summary[doc]["total"] += v.get("total_price", 0)

        df = pd.DataFrame(summary).T
        df["الطبيب"] = df.index
        df = df[["الطبيب", "count", "before", "after", "transport", "total"]]
        df.columns = ["الدكتور", "عدد الزيارات", "قبل الخصم", "بعد الخصم", "الانتقال", "الإجمالي"]
        df = df.sort_values("عدد الزيارات", ascending=False)

        # Overall totals
        total_count = df["عدد الزيارات"].sum()
        total_before = df["قبل الخصم"].sum()
        total_after = df["بعد الخصم"].sum()
        total_transport = df["الانتقال"].sum()
        total_total = df["الإجمالي"].sum()

        st.markdown("---")
        st.markdown(f"**إجمالي عدد الزيارات:** {total_count}  |  **الإجمالي العام:** {total_total:,} جنيه")
        st.dataframe(df.style.format({
            "قبل الخصم": "{:,} جنيه",
            "بعد الخصم": "{:,} جنيه",
            "الانتقال": "{:,} جنيه",
            "الإجمالي": "{:,} جنيه"
        }), use_container_width=True)

        # Printable report
        st.markdown("---")
        st.markdown('<div class="no-print">', unsafe_allow_html=True)
        if st.button("🖨️ طباعة التقرير"):
            # The print will use CSS media print to only show #printable-report
            pass
        st.markdown('</div>', unsafe_allow_html=True)

        # Build printable div
        month_name = ["يناير","فبراير","مارس","أبريل","مايو","يونيو",
                      "يوليو","أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"][month-1]
        branch_title = f" - فرع {branch_filter}" if branch_filter != "الكل" else ""
        report_title = f"تقرير زيارات {month_name} {year}{branch_title}"

        printable_html = f"""
        <div id="printable-report" style="direction: rtl; font-family: 'Cairo', sans-serif; padding: 20px; background: white; color: black;">
            <h1 style="color:#FF6B00; text-align:center;">Orange Lab - تقرير الزيارات المنزلية</h1>
            <h2 style="text-align:center;">{report_title}</h2>
            <table border="1" cellpadding="8" cellspacing="0" style="width:100%; border-collapse:collapse; margin-top:20px;">
                <thead>
                    <tr style="background:#FF6B00; color:white;">
                        <th>الدكتور</th><th>عدد الزيارات</th><th>قبل الخصم</th><th>بعد الخصم</th><th>الانتقال</th><th>الإجمالي</th>
                    </tr>
                </thead>
                <tbody>
        """
        for _, row in df.iterrows():
            printable_html += f"""
                <tr>
                    <td>{row['الدكتور']}</td>
                    <td>{row['عدد الزيارات']}</td>
                    <td>{row['قبل الخصم']:,} ج</td>
                    <td>{row['بعد الخصم']:,} ج</td>
                    <td>{row['الانتقال']:,} ج</td>
                    <td><b>{row['الإجمالي']:,} ج</b></td>
                </tr>
            """
        printable_html += f"""
                <tr style="background:#f5f5f5; font-weight:bold;">
                    <td>الإجمالي الكلي</td>
                    <td>{total_count}</td>
                    <td>{total_before:,} ج</td>
                    <td>{total_after:,} ج</td>
                    <td>{total_transport:,} ج</td>
                    <td>{total_total:,} ج</td>
                </tr>
                </tbody>
            </table>
            <p style="text-align:center; margin-top:30px;">تم إنشاؤه بواسطة تطبيق Orange Lab Home Visit</p>
        </div>
        """

        st.components.v1.html(printable_html, height=600, scrolling=True)

        # CSV Export
        csv = df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label="📥 تحميل التقرير CSV",
            data=csv,
            file_name=f"تقرير_زيارات_{month_name}_{year}.csv",
            mime="text/csv",
        )
