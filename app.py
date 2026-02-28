import base64
import smtplib
from datetime import datetime
from io import BytesIO
from typing import List, Tuple

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from streamlit_gsheets import GSheetsConnection
# Utilitzarem aquesta llibreria per la firma, és la més robusta per a mòbils
from streamlit_drawable_canvas import st_canvas

# ==========================================
# 1. CONFIGURACIÓ I ESTILISME AVANÇAT
# ==========================================
st.set_page_config(
    page_title="Estellé Parquet · Seguiment",
    page_icon="🪵",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@300;600&display=swap');

:root {
    --wood: #4e342e;
    --accent: #8d6e63;
    --bg-warm: #fdfaf7;
    --soft-white: #fcfcfc;
}

.stApp { 
    background: var(--bg-warm); 
    color: #2c2c2c; 
    font-family: 'Inter', sans-serif; 
}

/* Header Equip Estil Modern */
.team-header {
    background-color: var(--soft-white);
    border: 1px solid #efebe9;
    padding: 20px;
    border-radius: 20px;
    text-align: center;
    margin-bottom: 25px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.02);
}

.team-header h1 {
    font-family: 'Outfit', sans-serif;
    font-weight: 600;
    font-size: 1.8rem;
    color: var(--wood);
    margin: 0;
    letter-spacing: -0.5px;
}

.team-header p {
    font-family: 'Outfit', sans-serif;
    font-weight: 300;
    color: var(--accent);
    margin: 5px 0 0 0;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-size: 0.8rem;
}

.panel {
    background: white;
    border: 1px solid #e0d7d0;
    border-radius: 16px;
    padding: 25px;
    margin-bottom: 20px;
}

.label-bold { 
    font-weight: 700; 
    color: var(--accent); 
    font-size: 0.75rem; 
    text-transform: uppercase; 
    letter-spacing: 1px;
    margin-bottom: 12px; 
    display: block; 
}

/* Botó tipus App Professional */
.stButton > button {
    background: var(--wood) !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    border: none !important;
    transition: all 0.3s ease;
}

/* Amagar elements innecessaris */
#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONS TÈCNIQUES
# ==========================================
def norm_pin(v) -> str:
    return str(v).strip().split(".")[0]

def sanitize_image(name: str, content: bytes) -> Tuple[str, bytes, str]:
    image = Image.open(BytesIO(content))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    image.thumbnail((1200, 1200))
    out = BytesIO()
    image.save(out, format="JPEG", quality=85)
    return f"{name}.jpg", out.getvalue(), "image/jpeg"

# ==========================================
# 3. LOGIN I DADES
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_projectes = conn.read(worksheet="Projectes", ttl=0).dropna(subset=["Nom"])
    df_templates = conn.read(worksheet="Config_Templates", ttl=0).dropna(subset=["Tipus"])
    df_equips = conn.read(worksheet="Equips", ttl=0).dropna(subset=["Equip"])
except Exception as e:
    st.error("Error de connexió.")
    st.stop()

if "auth_user" not in st.session_state:
    st.markdown('<div class="team-header"><h1>Estellé Parquet</h1><p>Accés Instal·ladors</p></div>', unsafe_allow_html=True)
    with st.form("login"):
        pin_in = st.text_input("PIN d'Equip", type="password")
        if st.form_submit_button("ENTRAR"):
            match = df_equips[df_equips["PIN"].apply(norm_pin) == norm_pin(pin_in)]
            if not match.empty:
                st.session_state.auth_user = match.iloc[0]["Equip"]
                st.rerun()
            else:
                st.error("PIN incorrecte")
    st.stop()

# ==========================================
# 4. FORMULARI PRINCIPAL
# ==========================================

# Capçalera moderna de l'equip
st.markdown(f"""
<div class="team-header">
    <p>{datetime.now().strftime("%d · %m · %Y")}</p>
    <h1>{st.session_state.auth_user}</h1>
</div>
""", unsafe_allow_html=True)

# Selecció de Projecte
st.markdown('<div class="panel">', unsafe_allow_html=True)
col_a, col_b = st.columns(2)
obra_sel = col_a.selectbox("Projecte", df_projectes["Nom"].unique())
tipus_sel = col_b.selectbox("Treball realitzat", df_templates["Tipus"].unique())
st.markdown('</div>', unsafe_allow_html=True)

dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]

with st.form("main_form"):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<span class="label-bold">Mesures i Avanç</span>', unsafe_allow_html=True)
    
    m_cols = st.columns(3)
    valors_final = []
    for i, field in enumerate(["Camp1", "Camp2", "Camp3"]):
        nombre = dades_t.get(field, "")
        if pd.notna(nombre) and str(nombre).strip():
            with m_cols[i]:
                v = st.number_input(str(nombre), min_value=0, step=1)
                valors_final.append((str(nombre), v))

    comentaris = st.text_area("Notes de la jornada", placeholder="Explica detalls rellevants...")
    
    st.markdown('<span class="label-bold">Reportatge Fotogràfic</span>', unsafe_allow_html=True)
    foto_cam = st.camera_input("Fer foto de l'obra")
    fotos_extra = st.file_uploader("Adjuntar més fotos", accept_multiple_files=True, type=["jpg", "png"])
    st.markdown('</div>', unsafe_allow_html=True)

    # SECCIÓ DE FIRMES (AMB EL DIT)
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    col_f1, col_f2 = st.columns(2)
    
    with col_f1:
        st.markdown('<span class="label-bold">Firma Responsable</span>', unsafe_allow_html=True)
        canvas_resp = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#f9f9f9",
            height=150,
            key="canvas_resp",
            update_壓力=True,
            drawing_mode="freedraw",
            display_toolbar=False,
        )

    with col_f2:
        st.markdown('<span class="label-bold">Firma Client</span>', unsafe_allow_html=True)
        canvas_cli = st_canvas(
            fill_color="rgba(255, 255, 255, 0)",
            stroke_width=2,
            stroke_color="#000000",
            background_color="#f9f9f9",
            height=150,
            key="canvas_cli",
            drawing_mode="freedraw",
            display_toolbar=False,
        )
    st.markdown('</div>', unsafe_allow_html=True)

    enviar = st.form_submit_button("FINALITZAR I ENVIAR INFORME")

# ==========================================
# 5. LÒGICA D'ENVIAMENT (Resumida)
# ==========================================
if enviar:
    if canvas_resp.image_data is not None:
        # Aquí processaries la firma com una imatge i l'enviaries per mail
        st.success("Informe enviat correctament!")
        st.balloons()
