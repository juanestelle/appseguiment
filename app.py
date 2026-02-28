import base64
from datetime import datetime
from io import BytesIO
from typing import List, Tuple

import pandas as pd
import smtplib
import streamlit as st
from PIL import Image, ImageOps
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from streamlit_gsheets import GSheetsConnection
from streamlit_signature_pad import st_signature_pad # Requiere instalación

# ==========================================
# 1. CONFIGURACIÓN Y ESTILO VISUAL (CÁLIDO)
# ==========================================
st.set_page_config(
    page_title="Estellé Parquet · Seguimiento",
    page_icon="🪵",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600;700&display=swap');

:root {
    --bg: #fdfaf7;
    --wood-dark: #5d4037;
    --wood-soft: #8d6e63;
    --accent: #4e342e;
    --text: #2d2d2d;
    --line: #e0d7d0;
}

.stApp {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', sans-serif;
}

#MainMenu, footer, header, [data-testid="stToolbar"] { visibility: hidden; }

.hero {
    background: var(--wood-dark);
    color: #fbe9e7;
    border-radius: 16px;
    padding: 2rem;
    margin-bottom: 1.5rem;
    text-align: center;
    box-shadow: 0 10px 30px rgba(93, 64, 55, 0.15);
}

.hero h1 { font-family: 'Playfair Display', serif; font-size: 1.8rem; margin: 0; }
.beta-badge { font-size: 0.7rem; background: #ffab91; color: #4e342e; padding: 2px 8px; border-radius: 4px; vertical-align: middle; }

.panel {
    background: white;
    border: 1px solid var(--line);
    border-radius: 12px;
    padding: 1.5rem;
    margin-bottom: 1rem;
}

.stButton > button {
    background: var(--wood-dark) !important;
    color: white !important;
    border-radius: 8px !important;
    border: none !important;
    height: 3.5rem;
    font-weight: 700;
}

.sig-label { font-size: 0.8rem; color: var(--wood-soft); font-weight: 700; margin-bottom: 5px; text-transform: uppercase; }

</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONES DE APOYO
# ==========================================
def sanitize_image(name: str, content: bytes) -> Tuple[str, bytes, str]:
    image = Image.open(BytesIO(content))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    image.thumbnail((1600, 1600))
    out = BytesIO()
    image.save(out, format="JPEG", quality=80, optimize=True)
    return f"{name}.jpg", out.getvalue(), "image/jpeg"

def email_html_warm(obra, tipus, equip, metrics, comentaris, n_fotos):
    now = datetime.now().strftime("%d/%m/%Y")
    
    rows = "".join([f"<tr><td style='padding:12px; border-bottom:1px solid #eee;'>{m[0]}</td><td style='padding:12px; border-bottom:1px solid #eee; text-align:right;'><b>{int(m[1])}</b></td></tr>" for m in metrics if m[1] > 0])
    
    return f"""
    <div style="background:#fdfaf7; padding:40px; font-family:sans-serif;">
        <div style="max-width:600px; margin:auto; background:white; border-radius:12px; overflow:hidden; border:1px solid #e0d7d0;">
            <div style="background:#5d4037; padding:30px; color:white; text-align:center;">
                <h1 style="margin:0; font-family:serif;">Estellé Parquet</h1>
                <p style="margin:5px 0 0; opacity:0.8; font-size:14px;">Seguimiento de Proyecto</p>
            </div>
            <div style="padding:30px;">
                <p style="font-size:12px; color:#8d6e63; text-transform:uppercase; letter-spacing:1px; margin-bottom:5px;">Detalles de la jornada</p>
                <h2 style="margin:0; color:#4e342e;">{obra}</h2>
                <p style="color:#666;">Servicio: {tipus} | Fecha: {now}</p>
                
                <table style="width:100%; border-collapse:collapse; margin:20px 0;">
                    {rows}
                </table>
                
                <div style="background:#fbe9e7; padding:20px; border-radius:8px; color:#5d4037;">
                    <b style="font-size:12px;">OBSERVACIONES:</b><br>{comentaris}
                </div>
                
                <p style="font-size:13px; color:#999; margin-top:20px;">Responsable en obra: {equip}</p>
                <p style="font-size:10px; color:#bbb; border-top:1px solid #eee; padding-top:10px; margin-top:30px;">
                    Este es un informe automático en <b>fase BETA</b> generado por el sistema de gestión de Estellé Parquet.
                </p>
            </div>
        </div>
    </div>
    """

# ==========================================
# 3. LÓGICA DE APLICACIÓN
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_projectes = conn.read(worksheet="Projectes", ttl=0).dropna(subset=["Nom"])
    df_templates = conn.read(worksheet="Config_Templates", ttl=0).dropna(subset=["Tipus"])
    df_equips = conn.read(worksheet="Equips", ttl=0).dropna(subset=["Equip"])
except:
    st.error("Error conectando con la base de datos.")
    st.stop()

# LOGIN
if "equip" not in st.session_state:
    st.markdown('<div class="hero"><h1>Estellé Parquet <span class="beta-badge">BETA</span></h1><p>Control de obra para profesionales</p></div>', unsafe_allow_html=True)
    with st.form("login"):
        pin = st.text_input("Introduce tu PIN", type="password")
        if st.form_submit_button("Acceder"):
            match = df_equips[df_equips["PIN"].astype(str) == pin]
            if not match.empty:
                st.session_state.equip = match.iloc[0]["Equip"]
                st.rerun()
            else: st.error("PIN inválido")
    st.stop()

# APP CUERPO
st.markdown(f'<div class="hero"><h1>{st.session_state.equip}</h1><p>{datetime.now().strftime("%d/%m/%Y")}</p></div>', unsafe_allow_html=True)

with st.expander("⚙️ Cambiar de Equipo / Salir"):
    if st.button("Cerrar Sesión"):
        st.session_state.equip = None
        st.rerun()

st.markdown('<div class="panel">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
obra_sel = c1.selectbox("Selecciona el Proyecto", df_projectes["Nom"].unique())
tipus_sel = c2.selectbox("Tipo de Trabajo", df_templates["Tipus"].unique())
st.markdown('</div>', unsafe_allow_html=True)

dades_p = df_projectes[df_projectes["Nom"] == obra_sel].iloc[0]
dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]

with st.form("seguimiento", clear_on_submit=True):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    
    # Métricas sin decimales
    m_cols = st.columns(3)
    valors = []
    for i, camp in enumerate(["Camp1", "Camp2", "Camp3"]):
        nombre_camp = dades_t.get(camp, "")
        if pd.notna(nombre_camp) and nombre_camp != "":
            with m_cols[i]:
                valors.append((nombre_camp, st.number_input(nombre_camp, min_value=0, step=1, format="%d")))
    
    comentaris = st.text_area("Comentarios y Observaciones", placeholder="Ej: Nivelación de solera completada...")
    
    st.markdown('<p class="sig-label">Fotos de la jornada</p>', unsafe_allow_html=True)
    fotos = st.file_uploader("Subir fotos", accept_multiple_files=True, type=['jpg','png','jpeg'], label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # FIRMAS
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<p class="sig-label">Firma del Responsable</p>', unsafe_allow_html=True)
    sig_resp = st_signature_pad(key="resp", background_color="#f9f9f9", height=150)
    
    st.markdown('<p class="sig-label">Firma del Cliente</p>', unsafe_allow_html=True)
    sig_cli = st_signature_pad(key="cli", background_color="#f9f9f9", height=150)
    st.markdown('</div>', unsafe_allow_html=True)

    submit = st.form_submit_button("FINALIZAR Y ENVIAR INFORME")

if submit:
    with st.spinner("Enviando informe profesional..."):
        try:
            # 1. Guardar en Sheets
            df_seg = conn.read(worksheet="Seguiment", ttl=0)
            nueva = pd.DataFrame([{"Data": datetime.now().strftime("%d/%m/%Y"), "Projecte": obra_sel, "Tipus": tipus_sel, "Comentaris": comentaris, "Operari": st.session_state.equip}])
            conn.update(worksheet="Seguiment", data=pd.concat([df_seg, nueva], ignore_index=True))

            # 2. Enviar Email
            smtp = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg["Subject"] = f"Seguimiento proyecto {obra_sel} · Estellé Parquet"
            msg["From"] = f"Estellé Parquet <{smtp['user']}>"
            msg["To"] = dades_p["Emails_Contacte"]

            html = email_html_warm(str(dades_p.get("Logo_client", "")), obra_sel, tipus_sel, st.session_state.equip, valors, comentaris, len(fotos) if fotos else 0)
            msg.attach(MIMEText(html, "html"))

            # Adjuntar fotos
            if fotos:
                for f in fotos:
                    name, content, mime = sanitize_image(f.name, f.getvalue())
                    part = MIMEBase("image", "jpeg")
                    part.set_payload(content)
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={name}")
                    msg.attach(part)

            with smtplib.SMTP(smtp["server"], int(smtp["port"])) as server:
                server.starttls()
                server.login(smtp["user"], smtp["password"])
                server.sendmail(smtp["user"], [e.strip() for e in dades_p["Emails_Contacte"].split(",")], msg.as_string())

            st.success("¡Informe enviado con éxito!")
            st.balloons()
        except Exception as e:
            st.error(f"Error: {e}")
