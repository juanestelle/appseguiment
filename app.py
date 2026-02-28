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

# Firma opcional: si no está instalada, no rompe la app
try:
    from streamlit_signature_pad import st_signature_pad
except Exception:
    st_signature_pad = None


# ==========================================
# 1. CONFIGURACIÓN Y ESTILO "WARM"
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
}

.stApp { background: var(--bg-warm); color: #2c2c2c; font-family: 'Inter', sans-serif; }
#MainMenu, footer, header { visibility: hidden; }

.hero {
    background: var(--wood);
    color: #fbe9e7;
    border-radius: 16px;
    padding: 2.5rem 1.5rem;
    margin-bottom: 2rem;
    text-align: center;
}

.hero h1 { font-family: 'Playfair Display', serif; font-size: 2rem; margin: 0; }
.beta-badge { font-size: 0.6rem; background: #d7ccc8; color: #4e342e; padding: 2px 8px; border-radius: 4px; vertical-align: middle; margin-left: 10px; }

.panel {
    background: white;
    border: 1px solid #e0d7d0;
    border-radius: 12px;
    padding: 25px;
    margin-bottom: 15px;
}

.stButton > button, .stFormSubmitButton > button {
    background: var(--wood) !important;
    color: white !important;
    border-radius: 8px !important;
    height: 3.5rem;
    font-weight: 700;
    border: none !important;
    width: 100%;
}

.label-bold { font-weight: 700; color: var(--accent); font-size: 0.8rem; text-transform: uppercase; margin-bottom: 10px; display: block; }
</style>
""", unsafe_allow_html=True)


# ==========================================
# 2. FUNCIONES DE APOYO
# ==========================================
def norm_pin(v) -> str:
    return str(v).strip().split(".")[0]


def sanitize_image(name: str, content: bytes) -> Tuple[str, bytes, str]:
    image = Image.open(BytesIO(content))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    image.thumbnail((1200, 1200))
    out = BytesIO()
    image.save(out, format="JPEG", quality=80, optimize=True)
    clean_name = f"{name.rsplit('.', 1)[0] if '.' in name else name}.jpg"
    return clean_name, out.getvalue(), "image/jpeg"


def get_email_body(obra, servicio, responsable, metrics, comentarios, n_fotos):
    rows = ""
    for label, val in metrics:
        if val > 0:
            rows += f"<tr><td style='padding:12px; border-bottom:1px solid #eee; color:#666;'>{label}</td><td style='padding:12px; border-bottom:1px solid #eee; text-align:right;'><b>{int(val)}</b></td></tr>"

    return f"""
    <div style="background:#fdfaf7; padding:30px; font-family:sans-serif;">
        <div style="max-width:600px; margin:auto; background:white; border:1px solid #e0d7d0; border-radius:12px; overflow:hidden;">
            <div style="background:#4e342e; padding:40px 20px; color:white; text-align:center;">
                <h1 style="margin:0; font-family:serif; font-size:26px;">Estellé Parquet</h1>
                <p style="margin:5px 0 0; opacity:0.7; font-size:12px; text-transform:uppercase; letter-spacing:2px;">Informe de Seguimiento</p>
            </div>
            <div style="padding:40px;">
                <h2 style="margin:0; color:#2d2d2d; font-size:20px;">{obra}</h2>
                <p style="color:#8d6e63; margin:5px 0 25px;">Servicio: {servicio} | {datetime.now().strftime('%d/%m/%Y')}</p>
                <table style="width:100%; border-collapse:collapse; margin-bottom:25px;">
                    {rows}
                </table>
                <div style="background:#fcf8f6; border-left:4px solid #8d6e63; padding:20px; border-radius:4px; color:#4e342e;">
                    <b style="font-size:11px; text-transform:uppercase; color:#8d6e63;">Observaciones:</b>
                    <p style="margin:10px 0 0; line-height:1.6;">{comentarios if comentarios else "Jornada completada con normalidad."}</p>
                </div>
                <p style="font-size:12px; color:#999; margin-top:30px;">Responsable: {responsable} | Fotos adjuntas: {n_fotos}</p>
                <div style="margin-top:40px; border-top:1px solid #eee; padding-top:20px; text-align:center;">
                    <p style="font-size:10px; color:#ccc;">Proyecto en <b>Fase BETA</b> generado por Estellé Parquet Digital.</p>
                </div>
            </div>
        </div>
    </div>
    """


# ==========================================
# 3. CARGA DE DATOS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_projectes = conn.read(worksheet="Projectes", ttl=0).dropna(subset=["Nom"])
    df_templates = conn.read(worksheet="Config_Templates", ttl=0).dropna(subset=["Tipus"])
    df_equips = conn.read(worksheet="Equips", ttl=0).dropna(subset=["Equip"])
except Exception as e:
    st.error("Error de conexión con Google Sheets.")
    st.caption(str(e))
    st.stop()

if "auth_user" not in st.session_state:
    st.markdown('<div class="hero"><h1>Estellé Parquet <span class="beta-badge">BETA</span></h1><p>Acceso para instaladores</p></div>', unsafe_allow_html=True)
    with st.form("login"):
        pin_in = st.text_input("PIN de Equipo", type="password")
        if st.form_submit_button("Entrar"):
            match = df_equips[df_equips["PIN"].apply(norm_pin) == norm_pin(pin_in)]
            if not match.empty:
                st.session_state.auth_user = match.iloc[0]["Equip"]
                st.rerun()
            else:
                st.error("PIN incorrecto")
    st.stop()


# ==========================================
# 4. CUERPO DE LA APP
# ==========================================
st.markdown(f'<div class="hero"><h1>{st.session_state.auth_user}</h1><p>{datetime.now().strftime("%d / %m / %Y")}</p></div>', unsafe_allow_html=True)

st.markdown('<div class="panel">', unsafe_allow_html=True)
col_a, col_b = st.columns(2)
obra_sel = col_a.selectbox("Proyecto", df_projectes["Nom"].unique())
tipus_sel = col_b.selectbox("Tipo de Trabajo", df_templates["Tipus"].unique())
st.markdown('</div>', unsafe_allow_html=True)

dades_p = df_projectes[df_projectes["Nom"] == obra_sel].iloc[0]
dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]

with st.form("main_form", clear_on_submit=True):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<span class="label-bold">Datos y Avance</span>', unsafe_allow_html=True)

    m_cols = st.columns(3)
    valors_final = []
    for i, field in enumerate(["Camp1", "Camp2", "Camp3"]):
        nombre = dades_t.get(field, "")
        if pd.notna(nombre) and str(nombre).strip():
            with m_cols[i]:
                v = st.number_input(str(nombre), min_value=0, step=1, format="%d")
                valors_final.append((str(nombre), v))

    comentarios = st.text_area("Notas / Incidencias")

    # Cámara + galería para móvil/tablet
    foto_cam = st.camera_input("Hacer foto")
    fotos = st.file_uploader(
        "Subir fotos",
        accept_multiple_files=True,
        type=["jpg", "png", "jpeg", "webp"],
        label_visibility="collapsed",
    )
    st.markdown('</div>', unsafe_allow_html=True)

    # FIRMAS
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    col_sig1, col_sig2 = st.columns(2)
    with col_sig1:
        st.markdown('<span class="label-bold">Firma Responsable</span>', unsafe_allow_html=True)
        if st_signature_pad:
            st_signature_pad(key="sig_resp", height=150, background_color="#fafafa")
        else:
            st.text_input("Nombre responsable (firma no disponible)", key="sig_resp_fallback")
    with col_sig2:
        st.markdown('<span class="label-bold">Firma Cliente</span>', unsafe_allow_html=True)
        if st_signature_pad:
            st_signature_pad(key="sig_cli", height=150, background_color="#fafafa")
        else:
            st.text_input("Nombre cliente (firma no disponible)", key="sig_cli_fallback")
    st.markdown('</div>', unsafe_allow_html=True)

    enviar = st.form_submit_button("ENVIAR INFORME PROFESIONAL")


# ==========================================
# 5. ENVÍO
# ==========================================
if enviar:
    with st.spinner("Sincronizando..."):
        try:
            # 1. Registro Sheets
            try:
                df_hist = conn.read(worksheet="Seguiment", ttl=0).dropna(how="all")
            except Exception:
                df_hist = pd.DataFrame()

            nueva = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y"),
                "Projecte": obra_sel,
                "Tipus": tipus_sel,
                "Comentaris": comentarios,
                "Operari": st.session_state.auth_user,
                "Fotos": (1 if foto_cam else 0) + (len(fotos) if fotos else 0),
            }])

            conn.update(worksheet="Seguiment", data=pd.concat([df_hist, nueva], ignore_index=True))

            # 2. Email
            smtp = st.secrets["smtp"]
            msg = MIMEMultipart()
            msg["Subject"] = f"Seguimiento proyecto {obra_sel} · Estellé Parquet"
            msg["From"] = f"Estellé Parquet <{smtp['user']}>"

            destinatarios = [e.strip() for e in str(dades_p.get("Emails_Contacte", "")).split(",") if e.strip()]
            if not destinatarios:
                raise ValueError("No hay destinatarios en 'Emails_Contacte'")

            msg["To"] = ", ".join(destinatarios)

            total_fotos = (1 if foto_cam else 0) + (len(fotos) if fotos else 0)
            body = get_email_body(obra_sel, tipus_sel, st.session_state.auth_user, valors_final, comentarios, total_fotos)
            msg.attach(MIMEText(body, "html"))

            # Adjuntar foto cámara
            if foto_cam:
                fname, fcontent, _fmime = sanitize_image("foto_camara", foto_cam.getvalue())
                part = MIMEBase("image", "jpeg")
                part.set_payload(fcontent)
                encoders.encode_base64(part)
                part.add_header("Content-Disposition", f"attachment; filename={fname}")
                msg.attach(part)

            # Adjuntar galería
            if fotos:
                for f in fotos:
                    fname, fcontent, _fmime = sanitize_image(f.name, f.getvalue())
                    part = MIMEBase("image", "jpeg")
                    part.set_payload(fcontent)
                    encoders.encode_base64(part)
                    part.add_header("Content-Disposition", f"attachment; filename={fname}")
                    msg.attach(part)

            with smtplib.SMTP(smtp["server"], int(smtp["port"])) as server:
                server.starttls()
                server.login(smtp["user"], smtp["password"])
                server.sendmail(smtp["user"], destinatarios, msg.as_string())

            st.success("¡Enviado con éxito!")
            st.balloons()

        except Exception as e:
            st.error(f"Error: {e}")
