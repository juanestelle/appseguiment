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
from streamlit_signature_pad import st_signature_pad

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
}

.hero h1 { font-family: 'Playfair Display', serif; font-size: 1.8rem; margin: 0; }
.beta-badge { font-size: 0.7rem; background: #ffab91; color: #4e342e; padding: 2px 8px; border-radius: 4px; vertical-align: middle; margin-left: 10px; }

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

.sig-label { font-size: 0.8rem; color: var(--wood-soft); font-weight: 700; margin-bottom: 5px; text-transform: uppercase; margin-top: 15px; }

</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONES DE APOYO
# ==========================================
def sanitize_image(name: str, content: bytes) -> Tuple[str, bytes, str]:
    image = Image.open(BytesIO(content))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    image.thumbnail((1200, 1200)) # Tamaño óptimo para email
    out = BytesIO()
    image.save(out, format="JPEG", quality=85, optimize=True)
    return f"{name}.jpg", out.getvalue(), "image/jpeg"

def email_html_warm(obra, tipus, equip, metrics, comentaris, n_fotos):
    now = datetime.now().strftime("%d/%m/%Y")
    
    # Generar filas de la tabla de medidas (solo si son > 0)
    rows = ""
    for label, val in metrics:
        if val > 0:
            rows += f"""
            <tr>
                <td style='padding:12px; border-bottom:1px solid #eee; color:#666;'>{label}</td>
                <td style='padding:12px; border-bottom:1px solid #eee; text-align:right; color:#5d4037;'><b>{int(val)}</b></td>
            </tr>
            """
    
    return f"""
    <div style="background:#fdfaf7; padding:20px; font-family:sans-serif;">
        <div style="max-width:600px; margin:auto; background:white; border-radius:12px; overflow:hidden; border:1px solid #e0d7d0; box-shadow:0 4px 12px rgba(0,0,0,0.05);">
            <div style="background:#5d4037; padding:40px 20px; color:white; text-align:center;">
                <h1 style="margin:0; font-family:serif; font-size:28px; letter-spacing:1px;">Estellé Parquet</h1>
                <p style="margin:10px 0 0; opacity:0.8; font-size:14px; text-transform:uppercase; letter-spacing:2px;">Seguimiento de Proyecto</p>
            </div>
            <div style="padding:40px 30px;">
                <p style="font-size:11px; color:#8d6e63; text-transform:uppercase; letter-spacing:2px; margin-bottom:8px;">Resumen de la jornada</p>
                <h2 style="margin:0; color:#2d2d2d; font-size:22px;">{obra}</h2>
                <p style="color:#888; font-size:14px; margin-top:5px;">Servicio: {tipus} | Fecha: {now}</p>
                
                <table style="width:100%; border-collapse:collapse; margin:30px 0;">
                    {rows}
                </table>
                
                <div style="background:#fcf8f6; border-left:4px solid #8d6e63; padding:20px; border-radius:4px; color:#4e342e;">
                    <b style="font-size:11px; text-transform:uppercase; color:#8d6e63;">Observaciones:</b><br>
                    <p style="margin:10px 0 0; line-height:1.6; font-size:15px;">{comentaris if comentaris else "Sin observaciones adicionales."}</p>
                </div>
                
                <div style="margin-top:30px; padding-top:20px; border-top:1px solid #eee;">
                    <p style="font-size:13px; color:#666;"><b>Responsable:</b> {equip}</p>
                    <p style="font-size:13px; color:#666;"><b>Fotos adjuntas:</b> {n_fotos}</p>
                </div>

                <div style="margin-top:40px; background:#f9f9f9; padding:15px; text-align:center; border-radius:8px;">
                    <p style="font-size:10px; color:#bbb; margin:0;">
                        Este es un documento profesional generado por el sistema <b>Estellé Digital (Fase BETA)</b>.
                    </p>
                </div>
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
    st.markdown('<div class="hero"><h1>Estellé Parquet <span class="beta-badge">BETA</span></h1><p>Gestión profesional de obra</p></div>', unsafe_allow_html=True)
    with st.form("login"):
        pin = st.text_input("PIN de acceso", type="password", placeholder="Introduce tu PIN")
        if st.form_submit_button("Acceder"):
            match = df_equips[df_equips["PIN"].astype(str) == pin]
            if not match.empty:
                st.session_state.equip = match.iloc[0]["Equip"]
                st.rerun()
            else: st.error("PIN incorrecto")
    st.stop()

# APP CUERPO
st.markdown(f'<div class="hero"><h1>{st.session_state.equip}</h1><p>{datetime.now().strftime("%d/%m/%Y")}</p></div>', unsafe_allow_html=True)

with st.sidebar:
    if st.button("Cerrar Sesión"):
        st.session_state.equip = None
        st.rerun()

# PANEL 1: SELECCIÓN
st.markdown('<div class="panel">', unsafe_allow_html=True)
c1, c2 = st.columns(2)
obra_sel = c1.selectbox("Proyecto", df_projectes["Nom"].unique())
tipus_sel = c2.selectbox("Tipo de Trabajo", df_templates["Tipus"].unique())
st.markdown('</div>', unsafe_allow_html=True)

dades_p = df_projectes[df_projectes["Nom"] == obra_sel].iloc[0]
dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]

# FORMULARIO PRINCIPAL
with st.form("seguimiento", clear_on_submit=True):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    
    # Métricas (Enteros)
    m_cols = st.columns(3)
    valors_data = []
    for i, camp in enumerate(["Camp1", "Camp2", "Camp3"]):
        nombre_camp = dades_t.get(camp, "")
        if pd.notna(nombre_camp) and nombre_camp != "":
            with m_cols[i]:
                val = st.number_input(nombre_camp, min_value=0, step=1, format="%d")
                valors_data.append((nombre_camp, val))
    
    comentaris = st.text_area("Comentarios / Incidencias", placeholder="Escribe aquí los detalles del día...")
    
    st.markdown('<p class="sig-label">Fotografías</p>', unsafe_allow_html=True)
    fotos = st.file_uploader("Adjuntar fotos", accept_multiple_files=True, type=['jpg','png','jpeg'], label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # FIRMAS
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<p class="sig-label">Firma del Responsable</p>', unsafe_allow_html=True)
    sig_resp = st_signature_pad(key="resp", background_color="#fcfcfc", height=150)
    
    st.markdown('<p class="sig-label">Firma del Cliente</p>', unsafe_allow_html=True)
    sig_cli = st_signature_pad(key="cli", background_color="#fcfcfc", height=150)
    st.markdown('</div>', unsafe_allow_html=True)

    submit = st.form_submit_button("FINALIZAR Y ENVIAR INFORME PROFESIONAL")

# PROCESO DE ENVÍO
if submit:
    with st.spinner("Sincronizando y enviando informe..."):
        try:
            # 1. Guardar datos en Google Sheets
            df_seg = conn.read(worksheet="Seguiment", ttl=0)
            nueva = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y"),
                "Projecte": obra_sel,
                "Tipus": tipus_sel,
                "Comentaris": comentaris,
                "Operari": st.session_state.equip
            }])
            conn.update(worksheet="Seguiment", data=pd.concat([df_seg, nueva], ignore_index=True))

            # 2. Configurar Email SMTP
            smtp = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg["Subject"] = f"Seguimiento proyecto {obra_sel} · Estellé Parquet"
            msg["From"] = f"Estellé Parquet <{smtp['user']}>"
            
            # Destinatarios (lista limpia)
            dest_list = [e.strip() for e in str(dades_p["Emails_Contacte"]).split(",") if e.strip()]
            msg["To"] = ", ".join(dest_list)

            html = email_html_warm(str(dades_p.get("Logo_client", "")), obra_sel, tipus_sel, st.session_state.equip, valors_data, comentaris, len(fotos) if fotos else 0)
            msg.attach(MIMEText(html, "html"))

            # Adjuntar fotos optimizadas
            if fotos:
                for f in fotos:
                    fname, fcontent, fmime = sanitize_image(f.name, f.getvalue())
                    part = MIMEBase("image", "jpeg")
                    part.set_payload(fcontent)
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={fname}")
                    msg.attach(part)

            # Conexión y envío
            with smtplib.SMTP(smtp["server"], int(smtp["port"])) as server:
                server.starttls()
                server.login(smtp["user"], smtp["password"])
                server.sendmail(smtp["user"], dest_list, msg.as_string())

            st.success("¡Informe enviado con éxito!")
            st.balloons()
            
        except Exception as e:
            st.error(f"Se ha producido un error: {e}")
