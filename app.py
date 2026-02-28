import smtplib
import urllib.request
import base64
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
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(
    page_title="Estellé Parquet · Seguimiento",
    page_icon="🪵",
    layout="centered"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&family=Outfit:wght@300;600&display=swap');

:root {
    --wood:       #4e342e;
    --accent:     #8d6e63;
    --bg-warm:    #fdfaf7;
    --soft-white: #fcfcfc;
}

.stApp {
    background: var(--bg-warm);
    color: #2c2c2c;
    font-family: 'Inter', sans-serif;
}

/* Capçalera equip */
.team-header {
    background: var(--soft-white);
    border: 1px solid #efebe9;
    padding: 22px 20px;
    border-radius: 20px;
    text-align: center;
    margin-bottom: 18px;
    box-shadow: 0 4px 15px rgba(0,0,0,0.03);
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
    margin: 5px 0 0;
    text-transform: uppercase;
    letter-spacing: 2px;
    font-size: 0.78rem;
}

/* Panel genèric */
.panel {
    background: white;
    border: 1px solid #e0d7d0;
    border-radius: 16px;
    padding: 22px;
    margin-bottom: 16px;
}

.label-bold {
    font-weight: 700;
    color: var(--accent);
    font-size: 0.72rem;
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

/* Botó principal */
.stFormSubmitButton > button {
    background: var(--wood) !important;
    color: white !important;
    border-radius: 12px !important;
    padding: 0.85rem !important;
    font-weight: 600 !important;
    letter-spacing: 0.5px !important;
    border: none !important;
    width: 100% !important;
    font-size: 0.9rem !important;
}

/* Botó secundari (Salir) */
.stButton > button {
    background: transparent !important;
    color: var(--accent) !important;
    border: 1px solid #d7ccc8 !important;
    border-radius: 8px !important;
    font-size: 0.78rem !important;
    padding: 0.4rem 0.8rem !important;
    width: auto !important;
}

.success-box {
    background: #e8f5e9;
    border: 1px solid #a5d6a7;
    border-radius: 12px;
    padding: 18px 20px;
    display: flex;
    gap: 12px;
    align-items: flex-start;
    margin-top: 12px;
}
.success-box h4 { margin: 0 0 4px; color: #2e7d32; font-size: 0.95rem; }
.success-box p  { margin: 0; color: #555; font-size: 0.78rem; }

/* Amagar elements Streamlit innecessaris */
#MainMenu, footer, header { visibility: hidden; }

/* Tabs sense fons blanc extra */
.stTabs [data-baseweb="tab-list"] { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONES
# ==========================================
def norm_pin(v: str) -> str:
    return str(v).strip().split(".")[0]

def sanitize_image(name: str, content: bytes) -> Tuple[str, bytes, str]:
    img = Image.open(BytesIO(content))
    img = ImageOps.exif_transpose(img)
    img = img.convert("RGB")
    img.thumbnail((1200, 1200))
    out = BytesIO()
    img.save(out, format="JPEG", quality=85)
    return f"{name}.jpg", out.getvalue(), "image/jpeg"

def canvas_to_bytes(canvas_result) -> Optional[bytes]:
    if canvas_result is None or canvas_result.image_data is None:
        return None
    img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
    img = img.convert("RGB")
    out = BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()

def logo_a_base64(url: str) -> Optional[str]:
    """Descarrega el logo i el converteix a base64 per embeure'l a l'email."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            data = r.read()
        ext = url.split(".")[-1].lower().split("?")[0]
        mime = {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "gif": "image/gif", "svg": "image/svg+xml"}.get(ext, "image/png")
        b64 = base64.b64encode(data).decode()
        return f"data:{mime};base64,{b64}"
    except Exception:
        return None

def fmt_valor(v) -> str:
    """Mostra enter si no té decimals, decimal si en té."""
    if v is None:
        return "0"
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:.1f}"

# ==========================================
# 3. CONEXIÓN SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_projectes = conn.read(worksheet="Projectes",        ttl=300).dropna(subset=["Nom"])
    df_templates = conn.read(worksheet="Config_Templates", ttl=300).dropna(subset=["Tipus"])
    df_equips    = conn.read(worksheet="Equips",           ttl=300).dropna(subset=["Equip"])
except Exception as e:
    st.error("Error de conexión con Google Sheets.")
    with st.expander("Detalle"):
        st.code(str(e))
    st.stop()

# ==========================================
# 4. LOGIN
# ==========================================
if "auth_user" not in st.session_state:
    st.markdown("""
    <div class="team-header">
        <h1>Estellé Parquet</h1>
        <p>Acceso Instaladores</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login"):
        pin_in = st.text_input("PIN de Equipo", type="password", placeholder="····")
        if st.form_submit_button("ENTRAR"):
            match = df_equips[df_equips["PIN"].apply(norm_pin) == norm_pin(pin_in)]
            if not match.empty:
                st.session_state.auth_user = match.iloc[0]["Equip"]
                st.rerun()
            else:
                st.error("PIN incorrecto. Consulta a tu responsable.")
    st.stop()

equip_actual = st.session_state.auth_user

# ==========================================
# 5. FILTRAR PROYECTOS POR EQUIPO
# ==========================================
if "Equip" in df_projectes.columns:
    df_proj = df_projectes[
        df_projectes["Equip"].isna() |
        (df_projectes["Equip"].astype(str).str.strip() == "") |
        (df_projectes["Equip"].astype(str).str.strip() == equip_actual)
    ]
else:
    df_proj = df_projectes

if df_proj.empty:
    st.warning("No hay proyectos asignados a este equipo.")
    st.stop()

# ==========================================
# 6. CABECERA — sin panel blanco extra
# ==========================================
col_hd, col_out = st.columns([5, 1])
with col_hd:
    st.markdown(f"""
    <div class="team-header">
        <p>{datetime.now().strftime("%d · %m · %Y")}</p>
        <h1>{equip_actual}</h1>
    </div>
    """, unsafe_allow_html=True)
with col_out:
    st.markdown("<div style='margin-top:22px'>", unsafe_allow_html=True)
    if st.button("Salir"):
        del st.session_state["auth_user"]
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 7. SELECCIÓN — directamente sin panel encima
# ==========================================
col_a, col_b = st.columns(2)
obra_sel  = col_a.selectbox("Proyecto", df_proj["Nom"].unique())
tipus_sel = col_b.selectbox("Trabajo realizado", df_templates["Tipus"].unique())

dades_p = df_proj[df_proj["Nom"] == obra_sel].iloc[0]
dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]

# Logo cliente (solo si existe URL)
logo_url = str(dades_p.get("Logo_client", "")).strip()
if logo_url.startswith("http"):
    st.markdown(f"""
    <div style="margin:8px 0 16px;display:flex;align-items:center;gap:10px">
        <img src="{logo_url}" style="height:28px;width:auto;object-fit:contain">
        <span style="font-size:0.78rem;color:#8d6e63">{obra_sel}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<div style='margin-bottom:16px'></div>", unsafe_allow_html=True)

# ==========================================
# 8. FORMULARIO
# ==========================================
with st.form("main_form", clear_on_submit=False):

    # Medidas — directamente sin panel encima del form
    st.markdown('<span class="label-bold">Medidas y avance</span>', unsafe_allow_html=True)

    camps_actius = []
    for field in ["Camp1", "Camp2", "Camp3"]:
        val = dades_t.get(field, "")
        if pd.notna(val) and str(val).strip():
            camps_actius.append(str(val))

    valors = [None, None, None]
    if camps_actius:
        m_cols = st.columns(len(camps_actius))
        for i, nom in enumerate(camps_actius):
            with m_cols[i]:
                # value=None → camp buit per defecte (sense 0)
                valors[i] = st.number_input(
                    nom,
                    min_value=0.0,
                    value=None,
                    step=0.5,
                    format="%.1f",
                    placeholder="0"
                )

    v1 = valors[0] or 0.0
    v2 = valors[1] or 0.0
    v3 = valors[2] or 0.0

    st.markdown("<div style='margin-bottom:12px'></div>", unsafe_allow_html=True)

    comentaris = st.text_area(
        "Comentarios de la jornada",
        placeholder="Describe detalles relevantes del trabajo...",
        height=90
    )
    operari = st.text_input("Responsable en obra")

    st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)

    # Fotos
    st.markdown('<span class="label-bold">Reportaje fotográfico</span>', unsafe_allow_html=True)
    tab_cam, tab_gal = st.tabs(["📷 Cámara", "🖼 Galería"])
    with tab_cam:
        foto_cam = st.camera_input("Hacer foto", label_visibility="collapsed")
    with tab_gal:
        fotos_extra = st.file_uploader(
            "Adjuntar fotos",
            accept_multiple_files=True,
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed"
        )

    enviar = st.form_submit_button("▶  FINALIZAR Y ENVIAR INFORME")

# ==========================================
# 9. FIRMAS — FUERA del form (obligatorio)
# ==========================================
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<span class="label-bold">Firmas</span>', unsafe_allow_html=True)
col_f1, col_f2 = st.columns(2)

with col_f1:
    st.caption("Responsable de obra")
    st.markdown('<div class="firma-box">', unsafe_allow_html=True)
    canvas_resp = st_canvas(
        fill_color="rgba(255,255,255,0)",
        stroke_width=2,
        stroke_color="#1a1a1a",
        background_color="#fafafa",
        height=140,
        key="canvas_resp",
        update_streamlit=False,
        drawing_mode="freedraw",
        display_toolbar=False,
    )
    st.markdown('</div>', unsafe_allow_html=True)

with col_f2:
    st.caption("Cliente / Propietario")
    st.markdown('<div class="firma-box">', unsafe_allow_html=True)
    canvas_cli = st_canvas(
        fill_color="rgba(255,255,255,0)",
        stroke_width=2,
        stroke_color="#1a1a1a",
        background_color="#fafafa",
        height=140,
        key="canvas_cli",
        update_streamlit=False,
        drawing_mode="freedraw",
        display_toolbar=False,
    )
    st.markdown('</div>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 10. ENVÍO
# ==========================================
if enviar:
    if not operari.strip():
        st.warning("Indica el responsable en obra.")
        st.stop()

    # Recopilar fotos
    totes_fotos = []
    if foto_cam:
        n, b, m = sanitize_image("foto_obra", foto_cam.getvalue())
        totes_fotos.append((n, b, m))
    if fotos_extra:
        for f in fotos_extra:
            n, b, m = sanitize_image(f.name.rsplit(".", 1)[0], f.getvalue())
            totes_fotos.append((n, b, m))

    # Firmas
    firma_resp = canvas_to_bytes(canvas_resp)
    firma_cli  = canvas_to_bytes(canvas_cli)
    if firma_resp:
        totes_fotos.append(("firma_responsable.jpg", firma_resp, "image/jpeg"))
    if firma_cli:
        totes_fotos.append(("firma_cliente.jpg", firma_cli, "image/jpeg"))

    with st.spinner("Enviando informe..."):
        errors = []

        # A. Guardar en Sheets
        try:
            try:
                df_seg = conn.read(worksheet="Seguiment", ttl=0).dropna(how="all")
            except Exception:
                df_seg = pd.DataFrame(columns=[
                    "Fecha","Hora","Equipo","Proyecto","Trabajo",
                    "Dato1","Dato2","Dato3","Comentarios","Responsable","Fotos","Firmas"
                ])

            nova = pd.DataFrame([{
                "Fecha":        datetime.now().strftime("%d/%m/%Y"),
                "Hora":         datetime.now().strftime("%H:%M"),
                "Equipo":       equip_actual,
                "Proyecto":     obra_sel,
                "Trabajo":      tipus_sel,
                "Dato1":        v1, "Dato2": v2, "Dato3": v3,
                "Comentarios":  comentaris,
                "Responsable":  operari,
                "Fotos":        len(totes_fotos),
                "Firmas":       ("Resp" if firma_resp else "") + (" · Cliente" if firma_cli else "")
            }])
            conn.update(worksheet="Seguiment", data=pd.concat([df_seg, nova], ignore_index=True))
        except Exception as e:
            errors.append(f"Sheets: {e}")

        # B. Email
        try:
            smtp_cfg     = st.secrets["smtp"]
            emails_raw   = str(dades_p.get("Emails_Contacte", ""))
            destinataris = [e.strip() for e in emails_raw.split(",") if e.strip()]

            if destinataris:
                msg = MIMEMultipart("mixed")
                # Asunto tal como lo quieres
                msg["Subject"] = f"Seguimiento del proyecto {obra_sel} - Estellé parquet"
                # From: nombre visible sin mostrar el email real
                msg["From"]    = "Estellé Parquet · Seguimiento <noreply@estelleparquet.com>"
                msg["Reply-To"] = smtp_cfg["user"]
                msg["To"]      = ", ".join(destinataris)

                # Logo embebido en base64 (evita bloquejos de clients de correu)
                logo_b64 = logo_a_base64(logo_url) if logo_url.startswith("http") else None
                logo_html = f'<img src="{logo_b64}" style="height:40px;width:auto;object-fit:contain;margin-bottom:10px;display:block">' if logo_b64 else ""

                # Línies de treballs — format compacte: "72 m² parquet"
                treballs_html = ""
                for i, nom in enumerate(camps_actius):
                    val_fmt = fmt_valor([v1, v2, v3][i])
                    treballs_html += f"""
                    <tr>
                        <td style="padding:6px 0;font-size:20px;font-weight:700;color:#787879;
                                   font-family:Montserrat,sans-serif;white-space:nowrap">
                            {val_fmt}
                        </td>
                        <td style="padding:6px 0 6px 10px;font-size:20px;color:#9c9c94;
                                   font-family:Montserrat,sans-serif">
                            {nom}
                        </td>
                    </tr>"""

                obs_html = f"""
                <tr><td colspan="2" style="padding-top:16px">
                    <div style="color:#421cad;font-family:Montserrat,sans-serif;font-size:15px;font-weight:600;margin-bottom:4px">
                        COMENTARIOS DE LA JORNADA:
                    </div>
                    <div style="color:#8c7bc6;font-family:Montserrat,sans-serif;font-size:15px;line-height:1.5">
                        {comentaris}
                    </div>
                </td></tr>""" if comentaris.strip() else ""

                firmes_info = []
                if firma_resp: firmes_info.append("Firma responsable adjunta")
                if firma_cli:  firmes_info.append("Firma cliente adjunta")
                firmes_html = ""
                if firmes_info:
                    firmes_html = f"""
                    <tr><td colspan="2" style="padding-top:12px;font-size:12px;color:#8d6e63;
                                               font-family:Montserrat,sans-serif">
                        📎 {" · ".join(firmes_info)}
                    </td></tr>"""

                html = f"""<!DOCTYPE html>
<html><body style="margin:0;padding:0;background:#fefdf1;font-family:Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#fefdf1;padding:20px 0">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0"
       style="background:#fff9e5;border-radius:12px;overflow:hidden;max-width:600px">

  <!-- Logo -->
  <tr><td style="padding:30px 30px 10px;text-align:center">
    {logo_html}
  </td></tr>

  <!-- Fecha -->
  <tr><td style="padding:0 30px 10px;text-align:center">
    <div style="color:#7747ff;font-family:Montserrat,sans-serif;font-size:18px">
      {datetime.now().strftime("%d · %m · %Y")}
    </div>
  </td></tr>

  <!-- Separador -->
  <tr><td style="padding:0 30px">
    <hr style="border:none;border-top:1px solid #ddd;margin:0">
  </td></tr>

  <!-- Proyecto -->
  <tr><td style="padding:20px 30px 5px;text-align:center">
    <div style="font-size:11px;color:#0b0b0b;font-family:Montserrat,sans-serif;
                text-transform:uppercase;letter-spacing:1px">PROYECTO</div>
    <h3 style="margin:6px 0 0;color:#0b0b0b;font-family:Montserrat,sans-serif;
               font-size:18px">{obra_sel}</h3>
    <em style="color:#0b0b0b;font-family:Montserrat,sans-serif;font-size:13px">
      By ESTELLÉ parquet
    </em>
  </td></tr>

  <!-- Separador -->
  <tr><td style="padding:15px 30px 0">
    <hr style="border:none;border-top:1px solid #ddd;margin:0">
  </td></tr>

  <!-- TRABAJOS -->
  <tr><td style="padding:20px 30px 0;text-align:center">
    <h2 style="margin:0;color:#7747ff;font-family:Montserrat,sans-serif;
               font-size:18px;font-weight:700;letter-spacing:2px">TRABAJOS</h2>
  </td></tr>

  <tr><td style="padding:12px 30px 20px">
    <table cellpadding="0" cellspacing="0" align="center">
      {treballs_html}
      {obs_html}
      {firmes_html}
    </table>
  </td></tr>

  <!-- Separador -->
  <tr><td style="padding:0 30px">
    <hr style="border:none;border-top:1px solid #ddd;margin:0">
  </td></tr>

  <!-- Equipo y responsable -->
  <tr><td style="padding:20px 30px;text-align:center">
    <div style="color:#9c9c94;font-family:Montserrat,sans-serif;font-size:16px">Responsable en obra</div>
    <div style="color:#8125bb;font-family:Montserrat,sans-serif;font-size:20px;font-weight:600;margin:4px 0 14px">{operari}</div>
    <div style="color:#9c9c94;font-family:Montserrat,sans-serif;font-size:16px">Equipo</div>
    <div style="color:#8125bb;font-family:Montserrat,sans-serif;font-size:20px;font-weight:600;margin:4px 0">{equip_actual}</div>
  </td></tr>

  <!-- Footer -->
  <tr><td style="padding:20px 30px;text-align:center">
    <a href="http://www.estelleparquet.com"
       style="color:#4e342e;font-size:13px;font-family:Montserrat,sans-serif">
      www.estelleparquet.com
    </a>
    <p style="margin:12px 0 0;font-size:12px;color:#888;font-family:Montserrat,sans-serif;line-height:1.6">
      Realizamos el seguimiento diario para una óptima comunicación y mejora de nuestros servicios.
    </p>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""

                msg.attach(MIMEText(html, "html"))

                # Adjuntos (fotos + firmas)
                for nom_f, contingut, mime_t in totes_fotos:
                    p1, p2 = (mime_t.split("/") + ["octet-stream"])[:2]
                    adj = MIMEBase(p1, p2)
                    adj.set_payload(contingut)
                    encoders.encode_base64(adj)
                    adj.add_header("Content-Disposition", "attachment", filename=nom_f)
                    msg.attach(adj)

                with smtplib.SMTP(smtp_cfg["server"], smtp_cfg["port"]) as s:
                    s.starttls()
                    s.login(smtp_cfg["user"], smtp_cfg["password"])
                    # sendmail necessita l'email real per enviar, però el From del header és el visible
                    s.sendmail(smtp_cfg["user"], destinataris, msg.as_string())

        except Exception as e:
            errors.append(f"Email: {e}")

    # Resultat
    if not errors:
        fotos_txt   = f"{len(totes_fotos)} adjunto(s)" if totes_fotos else "Sin adjuntos"
        firmes_list = []
        if firma_resp: firmes_list.append("firma responsable")
        if firma_cli:  firmes_list.append("firma cliente")
        f_txt = " · ".join(firmes_list) if firmes_list else "sin firmas"

        st.markdown(f"""
        <div class="success-box">
            <div style="font-size:1.3rem">✔</div>
            <div>
                <h4>Informe registrado correctamente</h4>
                <p>{obra_sel} · {tipus_sel} · {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
                   {fotos_txt} · {f_txt}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for err in errors:
            st.error(err)
