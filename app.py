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
from streamlit_drawable_canvas import st_canvas

# ==========================================
# 1. CONFIGURACIÓ I ESTILISME
# ==========================================
st.set_page_config(
    page_title="Estellé Parquet · Seguiment",
    page_icon="🪵",
    layout="centered"
)

st.markdown("""
<style>
    :root {
        --wood: #4e342e;
        --accent: #8d6e63;
        --bg-warm: #fdfaf7;
    }
    .stApp { background: var(--bg-warm); }
    
    /* Estil Capçalera */
    .team-header {
        background-color: white;
        border: 1px solid #efebe9;
        padding: 20px;
        border-radius: 20px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.03);
    }
    .team-header h1 { color: var(--wood); margin: 0; font-size: 1.8rem; }
    .team-header p { color: var(--accent); margin: 5px 0 0 0; text-transform: uppercase; letter-spacing: 2px; font-size: 0.8rem; }

    /* Panells */
    .panel {
        background: white;
        border: 1px solid #e0d7d0;
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 20px;
    }
    
    /* Botó Principal */
    .stButton > button {
        background: var(--wood) !important;
        color: white !important;
        border-radius: 12px !important;
        padding: 1rem !important;
        font-weight: 600 !important;
        width: 100%;
    }
    
    /* Amagar peu de pàgina */
    #MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONS TÈCNIQUES
# ==========================================
def norm_pin(v) -> str:
    return str(v).strip().split(".")[0]

def sanitize_image(name: str, content: bytes) -> Tuple[str, bytes, str]:
    try:
        image = Image.open(BytesIO(content))
        image = ImageOps.exif_transpose(image)
        image = image.convert("RGB")
        image.thumbnail((1200, 1200))
        out = BytesIO()
        image.save(out, format="JPEG", quality=85)
        return f"{name}.jpg", out.getvalue(), "image/jpeg"
    except Exception:
        return None, None, None

# ==========================================
# 3. LOGIN I DADES
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_projectes = conn.read(worksheet="Projectes", ttl=0).dropna(subset=["Nom"])
    df_templates = conn.read(worksheet="Config_Templates", ttl=0).dropna(subset=["Tipus"])
    df_equips = conn.read(worksheet="Equips", ttl=0).dropna(subset=["Equip"])
except Exception as e:
    st.error("Error de connexió amb Google Sheets.")
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

st.markdown(f"""
<div class="team-header">
    <p>{datetime.now().strftime("%d · %m · %Y")}</p>
    <h1>{st.session_state.auth_user}</h1>
</div>
""", unsafe_allow_html=True)

# Selecció de Projecte (Fora del formulari per evitar recàrregues constants)
st.markdown('<div class="panel">', unsafe_allow_html=True)
col_a, col_b = st.columns(2)
obra_sel = col_a.selectbox("Projecte", df_projectes["Nom"].unique())
tipus_sel = col_b.selectbox("Treball realitzat", df_templates["Tipus"].unique())
st.markdown('</div>', unsafe_allow_html=True)

dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]

# --- SECCIÓ FIRMES I FOTOS (Fora del Form) ---
# Important: st_canvas i camera_input NO funcionen bé dins de st.form
# perquè necessiten interactuar en temps real.

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<span class="label-bold">Reportatge Fotogràfic</span>', unsafe_allow_html=True)
foto_cam = st.camera_input("Fer foto de l'obra")
fotos_extra = st.file_uploader("Adjuntar més fotos", accept_multiple_files=True, type=["jpg", "png"])
st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<span class="label-bold">Firmes (Signi amb el dit)</span>', unsafe_allow_html=True)
col_f1, col_f2 = st.columns(2)

with col_f1:
    st.caption("Responsable")
    canvas_resp = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=3, # Una mica més gruixut per veure's millor
        stroke_color="#000000",
        background_color="#f5f5f5",
        height=150,
        width=None, # S'adapta a la columna
        key="canvas_resp",
        drawing_mode="freedraw",
        display_toolbar=False
    )

with col_f2:
    st.caption("Client")
    canvas_cli = st_canvas(
        fill_color="rgba(255, 255, 255, 0)",
        stroke_width=3,
        stroke_color="#000000",
        background_color="#f5f5f5",
        height=150,
        width=None,
        key="canvas_cli",
        drawing_mode="freedraw",
        display_toolbar=False
    )
st.markdown('</div>', unsafe_allow_html=True)


# --- FORMULARI DADES NUMÈRIQUES I ENVIAMENT ---
with st.form("main_form"):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<span class="label-bold">Mesures i Observacions</span>', unsafe_allow_html=True)
    
    m_cols = st.columns(3)
    valors_final = []
    
    # Bucle per crear inputs dinàmics
    for i, field in enumerate(["Camp1", "Camp2", "Camp3"]):
        nombre = dades_t.get(field, "")
        if pd.notna(nombre) and str(nombre).strip():
            with m_cols[i]:
                v = st.number_input(str(nombre), min_value=0, step=1, key=f"num_{i}")
                valors_final.append((str(nombre), v))

    comentaris = st.text_area("Notes de la jornada", placeholder="Explica detalls rellevants...", height=100)
    st.markdown('</div>', unsafe_allow_html=True)

    # Botó d'enviament
    enviar = st.form_submit_button("FINALITZAR I ENVIAR INFORME")

# ==========================================
# 5. LÒGICA D'ENVIAMENT
# ==========================================
if enviar:
    # Validació de firma simple
    # (Comprova si el canvas té contingut dibuixat)
    firma_resp_valida = canvas_resp.image_data is not None and canvas_resp.image_data.sum() > 0
    
    if not firma_resp_valida:
        st.warning("⚠️ Si us plau, firma el camp de Responsable abans d'enviar.")
    else:
        # Aquí aniria la lògica d'enviament de correu
        with st.spinner("Enviant informe..."):
            # Simulació de procés
            # process_images(foto_cam, fotos_extra, canvas_resp, canvas_cli)
            # send_email(...)
            
            st.success("✅ Informe enviat correctament!")
            st.balloons()
            
            # Opcional: Netejar caches o recarregar
            # st.rerun() 
