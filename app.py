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
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=Inter:wght@400;600&display=swap');

:root {
    --wood: #4e342e;
    --accent: #8d6e63;
    --bg-warm: #fdfaf7;
    --text: #2c2c2c;
}

.stApp { background: var(--bg-warm); color: var(--text); font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }

.hero {
    background: var(--wood);
    color: #fbe9e7;
    border-radius: 16px;
    padding: 2.5rem 1.5rem;
    margin-bottom: 2rem;
    text-align: center;
    box-shadow: 0 10px 30px rgba(0,0,0,0.1);
}

.hero h1 { font-family: 'Playfair Display', serif; font-size: 2.2rem; margin: 0; }
.beta-tag { font-size: 0.65rem; background: #d7ccc8; color: #4e342e; padding: 3px 10px; border-radius: 4px; vertical-align: middle; margin-left: 10px; letter-spacing: 1px; }

.panel {
    background: white;
    border: 1px solid #e0d7d0;
    border-radius: 12px;
    padding: 25px;
    margin-bottom: 15px;
}

.stButton > button {
    background: var(--wood) !important;
    color: white !important;
    border-radius: 8px !important;
    height: 3.5rem;
    font-weight: 700;
    border: none !important;
}

.label-bold { font-weight: 700; color: var(--accent); font-size: 0.75rem; text-transform: uppercase; letter-spacing: 1.2px; margin-bottom: 10px; display: block; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONES DE APOYO
# ==========================================
def sanitize_image(name: str, content: bytes) -> Tuple[str, bytes, str]:
    image = Image.open(BytesIO(content))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    image.thumbnail((1200, 1200)) 
    out = BytesIO()
    image.save(out, format="JPEG", quality=82, optimize=True)
    return f"{name}.jpg", out.getvalue(), "image/jpeg"

def get_email_body(obra, servicio, responsable, metrics, comentarios, n_fotos):
    rows = ""
    for label, val in metrics:
        if val > 0:
            rows += f"<tr><td style='padding:12px; border-bottom:1px solid #eee; color:#666;'>{label}</td><td style='padding:12px; border-bottom:1px solid #eee; text-align:right; color:#4e342e;'><b>{int(val)}</b></td></tr>"
    
    return f"""
    <div style="background:#fdfaf7; padding:40px 20px; font-family:sans-serif; color:#2c2c2c;">
        <div style="max-width:600px; margin:auto; background:white; border:1px solid #e0d7d0; border-radius:16px; overflow:hidden; box-shadow:0 10px 20px rgba(0,0,0,0.05);">
            <div style="background:#4e342e; padding:50px 20px; color:#fbe9e7; text-align:center;">
                <h1 style="margin:0; font-family:serif; font-size:28px;">Estellé Parquet</h1>
                <p style="margin:10px 0 0; opacity:0.7; font-size:12px; text-transform:uppercase; letter-spacing:3px;">Seguimiento de Obra</p>
            </div>
            <div style="padding:40px 30px;">
                <h2 style="margin:0; color:#4e342e; font-size:22px;">{obra}</h2>
                <p style="color:#8d6e63; margin:5px 0 30px; font-size:14px; border-bottom:1px solid #fdfaf7; padding-bottom:15px;">Servicio: {servicio} | {datetime.now().strftime('%d/%m/%Y')}</p>
                
                <table style="width:100%; border-collapse:collapse; margin-bottom:30px;">
                    {rows}
                </table>
                
                <div style="background:#f9f6f4; border-left:4px solid #8d6e63; padding:25px; border-radius:8px; margin-bottom:30px;">
                    <b style="font-size:11px; color:#8d6e63; text-transform:uppercase;">Observaciones de la jornada:</b>
                    <p style="margin:10px 0 0; color:#2c2c2c; line-height:1.7; font-size:15px;">{comentarios if comentarios else "Jornada transcurrida sin incidencias."}</p>
                </div>
                
                <p style="font-size:13px; color:#666;"><b>Responsable en obra:</b> {responsable}</p>
                <p style="font-size:13px; color:#666;"><b>Documentación:</b> {n_fotos} fotos adjuntas</p>

                <div style="margin-top:50px; padding-top:20px; border-top:1px solid #eee; text-align:center;">
                    <p style="font-size:10px; color:#bbb;">
                        Este es un informe profesional en <b>fase BETA</b> generado por Estellé Parquet Digital.
                    </p>
                </div>
            </div>
        </div>
    </div>
    """

# ==========================================
# 3. CONEXIÓN Y ACCESO
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_projectes = conn.read(worksheet="Projectes", ttl=0).dropna(subset=["Nom"])
    df_templates = conn.read(worksheet="Config_Templates", ttl=0).dropna(subset=["Tipus"])
    df_equips = conn.read(worksheet="Equips", ttl=0).dropna(subset=["Equip"])
except:
    st.error("Error conectando con la base de datos.")
    st.stop()

if "auth_user" not in st.session_state:
    st.markdown('<div class="hero"><h1>Estellé Parquet <span class="beta-tag">BETA</span></h1><p>Acceso para equipos técnicos</p></div>', unsafe_allow_html=True)
    with st.form("login"):
        pin_in = st.text_input("Introduce tu PIN", type="password")
        if st.form_submit_button("Acceder"):
            match = df_equips[df_equips["PIN"].astype(str) == pin_in]
            if not match.empty:
                st.session_state.auth_user = match.iloc[0]["Equip"]
                st.rerun()
            else: st.error("PIN incorrecto")
    st.stop()

# ==========================================
# 4. CUERPO DE LA APP
# ==========================================
st.markdown(f'<div class="hero"><h1>{st.session_state.auth_user}</h1><p>{datetime.now().strftime("%d / %m / %Y")}</p></div>', unsafe_allow_html=True)

with st.sidebar:
    if st.button("Cerrar Sesión"):
        st.session_state.auth_user = None
        st.rerun()

# PANEL SELECCIÓN
st.markdown('<div class="panel">', unsafe_allow_html=True)
c_a, c_b = st.columns(2)
obra_sel = c_a.selectbox("Selecciona Proyecto", df_projectes["Nom"].unique())
tipus_sel = c_b.selectbox("Tipo de Trabajo", df_templates["Tipus"].unique())
st.markdown('</div>', unsafe_allow_html=True)

dades_p = df_projectes[df_projectes["Nom"] == obra_sel].iloc[0]
dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]

with st.form("main_form", clear_on_submit=True):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<span class="label-bold">Métricas y Avance</span>', unsafe_allow_html=True)
    
    # Métricas (Enteros)
    m_cols = st.columns(3)
    valors_final = []
    for i, field in enumerate(["Camp1", "Camp2", "Camp3"]):
        nombre = dades_t.get(field, "")
        if pd.notna(nombre) and nombre != "":
            with m_cols[i]:
                # Sin decimales: step=1, format=%d
                v = st.number_input(nombre, min_value=0, step=1, format="%d")
                valors_final.append((nombre, v))
    
    comentarios = st.text_area("Notas del día / Incidencias", placeholder="Escribe aquí los detalles del trabajo...")
    
    st.markdown('<span class="label-bold">Fotografías</span>', unsafe_allow_html=True)
    fotos = st.file_uploader("Subir archivos", accept_multiple_files=True, type=['jpg','png','jpeg'], label_visibility="collapsed")
    st.markdown('</div>', unsafe_allow_html=True)

    # FIRMAS
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    col_sig1, col_sig2 = st.columns(2)
    with col_sig1:
        st.markdown('<span class="label-bold">Firma Responsable</span>', unsafe_allow_html=True)
        st_signature_pad(key="sig_resp", height=150, background_color="#fafafa")
    with col_sig2:
        st.markdown('<span class="label-bold">Firma Cliente</span>', unsafe_allow_html=True)
        st_signature_pad(key="sig_cli", height=150, background_color="#fafafa")
    st.markdown('</div>', unsafe_allow_html=True)

    submit = st.form_submit_button("FINALIZAR Y ENVIAR INFORME PROFESIONAL")

# ==========================================
# 5. PROCESO DE ENVÍO
# ==========================================
if submit:
    with st.spinner("Generando reporte de alta calidad..."):
        try:
            # 1. Guardar en Sheets
            df_hist = conn.read(worksheet="Seguiment", ttl=0)
            nueva = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y"),
                "Projecte": obra_sel,
                "Tipus": tipus_sel,
                "Comentaris": comentarios,
                "Operari": st.session_state.auth_user
            }])
            conn.update(worksheet="Seguiment", data=pd.concat([df_hist, nueva], ignore_index=True))

            # 2. Enviar Email
            smtp_cfg = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg["Subject"] = f"Seguimiento proyecto {obra_sel} · Estellé Parquet"
            # Alias corporativo
            msg["From"] = f"Estellé Parquet <{smtp_cfg['user']}>"
            
            destinatarios = [e.strip() for e in str(dades_p["Emails_Contacte"]).split(",") if e.strip()]
            msg["To"] = ", ".join(destinatarios)

            body = get_email_body(obra_sel, tipus_sel, st.session_state.auth_user, valors_final, comentarios, len(fotos) if fotos else 0)
            msg.attach(MIMEText(body, "html"))

            if fotos:
                for f in fotos:
                    fname, fcontent, fmime = sanitize_image(f.name, f.getvalue())
                    part = MIMEBase("image", "jpeg")
                    part.set_payload(fcontent)
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={fname}")
                    msg.attach(part)

            with smtplib.SMTP(smtp_cfg["server"], int(smtp_cfg["port"])) as server:
                server.starttls()
                server.login(smtp_cfg["user"], smtp_cfg["password"])
                server.sendmail(smtp_cfg["user"], destinatarios, msg.as_string())

            st.success("¡Informe enviado con éxito!")
            st.balloons()
            
        except Exception as e:
            st.error(f"Error en el envío: {e}")
