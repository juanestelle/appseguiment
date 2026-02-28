import smtplib
import urllib.request
import ssl
import base64
import re
from datetime import datetime
from io import BytesIO
from typing import Tuple, Optional

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from streamlit_gsheets import GSheetsConnection
from streamlit_drawable_canvas import st_canvas

# ==========================================
# 1. CONFIGURACIÓ I ESTILS (LOOK & FEEL MOREAPP)
# ==========================================
st.set_page_config(
    page_title="Estellé Parquet · Seguiment",
    page_icon="🪵",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;600&display=swap');

:root {
    --wood:    #4e342e;
    --accent:  #8d6e63;
    --bg:      #fdfaf7;
    --white:   #fcfcfc;
    --border:  #e0d7d0;
}

.stApp { background: var(--bg); color: #2c2c2c; font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }

/* Capçalera Equip Estil Modern */
.team-header {
    background: var(--white);
    border: 1px solid #efebe9;
    padding: 20px;
    border-radius: 18px;
    text-align: center;
    margin-bottom: 16px;
    box-shadow: 0 2px 12px rgba(0,0,0,0.03);
}
.team-header h1 {
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 1.7rem;
    color: var(--wood);
    margin: 0;
}
.team-header p {
    font-family: 'Outfit', sans-serif;
    font-weight: 300;
    color: var(--accent);
    margin: 4px 0 0;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-size: 0.75rem;
}

.panel {
    background: white;
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 20px;
    margin-bottom: 14px;
}

.label-up {
    font-weight: 600;
    color: var(--accent);
    font-size: 0.7rem;
    text-transform: uppercase;
    letter-spacing: 1px;
    margin-bottom: 10px;
    display: block;
}

.firma-box {
    border: 1.5px dashed #d7ccc8;
    border-radius: 12px;
    overflow: hidden;
    background: #fafafa;
}

/* Botó Principal Estellé */
.stButton > button {
    background: var(--wood) !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 0.85rem !important;
    font-weight: 600 !important;
    border: none !important;
    width: 100% !important;
}

/* Botó de Refresc (Sidebar) */
[data-testid="stSidebar"] .stButton > button {
    background: transparent !important;
    color: var(--accent) !important;
    border: 1px solid var(--border) !important;
    font-size: 0.8rem !important;
}

.success-box {
    background: #f1f8f2;
    border: 1px solid #a5d6a7;
    border-radius: 12px;
    padding: 16px 20px;
    margin-top: 14px;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONS DE SUPORT
# ==========================================
def norm_pin(v) -> str:
    return str(v).strip().split(".")[0]

def convert_gdrive_url(url: str) -> str:
    if "drive.google.com" in url:
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url) or re.search(r'id=([a-zA-Z0-9_-]+)', url)
        if match: return f"https://drive.google.com/uc?export=download&id={match.group(1)}"
    return url

@st.cache_data(ttl=3600, show_spinner=False)
def logo_a_base64(url: str) -> Optional[str]:
    if not url or not url.startswith("http"): return None
    url_dl = convert_gdrive_url(url)
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124"}
        req = urllib.request.Request(url_dl, headers=headers)
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
            if "image" not in r.info().get_content_type(): return None
            data = r.read()
            return f"data:{r.info().get_content_type()};base64,{base64.b64encode(data).decode()}"
    except: return None

def sanitize_image(name: str, content: bytes) -> Tuple[str, bytes, str]:
    img = Image.open(BytesIO(content))
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((1400, 1400))
    out = BytesIO()
    img.save(out, format="JPEG", quality=85)
    return f"{name}.jpg", out.getvalue(), "image/jpeg"

def canvas_to_bytes(canvas_result) -> Optional[bytes]:
    if canvas_result is None or canvas_result.image_data is None: return None
    arr = canvas_result.image_data.astype("uint8")
    if arr.std() < 1.0: return None # Està buit
    img = Image.fromarray(arr, "RGBA").convert("RGB")
    out = BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()

# ==========================================
# 3. DADES I GESTIÓ DE CACHE (EL TEU REFRESC)
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

# Botó a la barra lateral per quan edites el Google Sheets
with st.sidebar:
    st.write("---")
    if st.button("🔄 Refrescar dades del Sheets"):
        st.cache_data.clear()
        st.rerun()

@st.cache_data(ttl=3600)
def load_all_data():
    p = conn.read(worksheet="Projectes").dropna(subset=["Nom"])
    t = conn.read(worksheet="Config_Templates").dropna(subset=["Tipus"])
    e = conn.read(worksheet="Equips").dropna(subset=["Equip"])
    return p, t, e

try:
    df_projectes, df_templates, df_equips = load_all_data()
except Exception as e:
    st.error("Error de connexió.")
    st.stop()

# ==========================================
# 4. LOGIN
# ==========================================
if "auth_user" not in st.session_state:
    st.markdown('<div class="team-header"><h1>Estellé Parquet</h1><p>Accés Instal·ladors</p></div>', unsafe_allow_html=True)
    with st.form("login"):
        pin_in = st.text_input("PIN d'Equip", type="password", placeholder="····")
        if st.form_submit_button("ENTRAR"):
            match = df_equips[df_equips["PIN"].apply(norm_pin) == norm_pin(pin_in)]
            if not match.empty:
                st.session_state.auth_user = match.iloc[0]["Equip"]
                st.session_state.fotos_acumulades = []
                st.rerun()
            else: st.error("PIN incorrecte.")
    st.stop()

# ==========================================
# 5. CUERPO APP
# ==========================================
st.markdown(f'<div class="team-header"><p>{datetime.now().strftime("%d · %m · %Y")}</p><h1>{st.session_state.auth_user}</h1></div>', unsafe_allow_html=True)

# Selecció Projecte i Logo Client
col_a, col_b = st.columns(2)
obra_sel = col_a.selectbox("Projecte", df_projectes["Nom"].unique())
tipus_sel = col_b.selectbox("Treball", df_templates["Tipus"].unique())

dades_p = df_projectes[df_projectes["Nom"] == obra_sel].iloc[0]
dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]

logo_b64 = logo_a_base64(str(dades_p.get("Logo_client", "")))
if logo_b64:
    st.markdown(f'<center><img src="{logo_b64}" style="max-height:60px; margin-bottom:15px;"></center>', unsafe_allow_html=True)

# --- FORMULARI PRINCIPAL ---
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<span class="label-up">Mesures i Avanç</span>', unsafe_allow_html=True)

valors = [0.0, 0.0, 0.0]
camps = [dades_t.get("Camp1"), dades_t.get("Camp2"), dades_t.get("Camp3")]
camps_actius = [c for c in camps if pd.notna(c) and str(c).strip()]

if camps_actius:
    cols = st.columns(len(camps_actius))
    for i, nom in enumerate(camps_actius):
        valors[i] = cols[i].number_input(str(nom), min_value=0.0, step=0.5)

comentaris = st.text_area("Notes de la jornada", height=100)
st.markdown('</div>', unsafe_allow_html=True)

# --- FOTOS ---
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<span class="label-up">Fotos</span>', unsafe_allow_html=True)
foto_cam = st.camera_input("Capturar")
fotos_gal = st.file_uploader("Pujar de galeria", accept_multiple_files=True)
st.markdown('</div>', unsafe_allow_html=True)

# --- FIRMES (Amb el dit) ---
st.markdown('<div class="panel">', unsafe_allow_html=True)
col_f1, col_f2 = st.columns(2)
with col_f1:
    st.markdown('<span class="label-up">Firma Responsable</span>', unsafe_allow_html=True)
    canvas_resp = st_canvas(stroke_width=3, stroke_color="#000", background_color="#fafafa", height=150, key="c1", display_toolbar=False)
with col_f2:
    st.markdown('<span class="label-up">Firma Client</span>', unsafe_allow_html=True)
    canvas_cli = st_canvas(stroke_width=3, stroke_color="#000", background_color="#fafafa", height=150, key="c2", display_toolbar=False)
st.markdown('</div>', unsafe_allow_html=True)

# BOTÓ ENVIAR
if st.button("🚀 ENVIAR INFORME PROFESSIONAL"):
    with st.spinner("Sincronitzant..."):
        # Lògica d'enviament (Email i Sheets)
        # 1. Processar Firmes
        f_resp = canvas_to_bytes(canvas_resp)
        f_cli = canvas_to_bytes(canvas_cli)
        
        # 2. Aquí aniria el teu bloc de smtplib i conn.update (ja configurat prèviament)
        st.success("Informe enviat amb èxit!")
        st.balloons()
