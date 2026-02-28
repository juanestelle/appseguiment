import smtplib
from datetime import datetime
from io import BytesIO
from typing import Tuple

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
# 1. CONFIGURACIÓ
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

.team-header {
    background: var(--soft-white);
    border: 1px solid #efebe9;
    padding: 22px 20px;
    border-radius: 20px;
    text-align: center;
    margin-bottom: 22px;
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

.stButton > button {
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
.stButton > button:hover {
    background: #6d4c41 !important;
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

#MainMenu, footer, header { visibility: hidden; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. FUNCIONS
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

def canvas_to_bytes(canvas_resp) -> bytes | None:
    """Converteix el canvas a bytes JPEG si s'ha signat."""
    if canvas_resp is None or canvas_resp.image_data is None:
        return None
    img = Image.fromarray(canvas_resp.image_data.astype("uint8"), "RGBA")
    img = img.convert("RGB")
    out = BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()

# ==========================================
# 3. CONNEXIÓ SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_projectes = conn.read(worksheet="Projectes",       ttl=0).dropna(subset=["Nom"])
    df_templates = conn.read(worksheet="Config_Templates", ttl=0).dropna(subset=["Tipus"])
    df_equips    = conn.read(worksheet="Equips",           ttl=0).dropna(subset=["Equip"])
except Exception as e:
    st.error("Error de connexió amb Google Sheets.")
    with st.expander("Detall"):
        st.code(str(e))
    st.stop()

# ==========================================
# 4. LOGIN
# ==========================================
if "auth_user" not in st.session_state:
    st.markdown("""
    <div class="team-header">
        <h1>Estellé Parquet</h1>
        <p>Accés Instal·ladors</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login"):
        pin_in = st.text_input("PIN d'Equip", type="password", placeholder="····")
        if st.form_submit_button("ENTRAR"):
            match = df_equips[df_equips["PIN"].apply(norm_pin) == norm_pin(pin_in)]
            if not match.empty:
                st.session_state.auth_user = match.iloc[0]["Equip"]
                st.rerun()
            else:
                st.error("PIN incorrecte. Consulta el teu responsable.")
    st.stop()

equip_actual = st.session_state.auth_user

# ==========================================
# 5. FILTRAR PROJECTES PER EQUIP
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
    st.warning("No hi ha projectes assignats a aquest equip.")
    st.stop()

# ==========================================
# 6. CAPÇALERA
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
    st.markdown("<div style='margin-top:18px'>", unsafe_allow_html=True)
    if st.button("Sortir"):
        del st.session_state["auth_user"]
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# 7. SELECCIÓ (fora del form — correcte)
# ==========================================
st.markdown('<div class="panel">', unsafe_allow_html=True)
col_a, col_b = st.columns(2)
obra_sel  = col_a.selectbox("Projecte", df_proj["Nom"].unique())
tipus_sel = col_b.selectbox("Treball realitzat", df_templates["Tipus"].unique())

dades_p = df_proj[df_proj["Nom"] == obra_sel].iloc[0]
dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]

# Logo client
logo_url = str(dades_p.get("Logo_client", "")).strip()
if logo_url.startswith("http"):
    st.markdown(f"""
    <div style="margin-top:12px;display:flex;align-items:center;gap:10px">
        <img src="{logo_url}" style="height:28px;width:auto;object-fit:contain">
        <span style="font-size:0.78rem;color:#8d6e63">{obra_sel}</span>
    </div>
    """, unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 8. FORMULARI — sense canvas aquí dins
# ==========================================
with st.form("main_form", clear_on_submit=False):
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<span class="label-bold">Mesures i Avanç</span>', unsafe_allow_html=True)

    camps_actius = []
    for field in ["Camp1", "Camp2", "Camp3"]:
        val = dades_t.get(field, "")
        if pd.notna(val) and str(val).strip():
            camps_actius.append(str(val))

    valors = [0.0, 0.0, 0.0]
    if camps_actius:
        m_cols = st.columns(len(camps_actius))
        for i, nom in enumerate(camps_actius):
            with m_cols[i]:
                valors[i] = st.number_input(nom, min_value=0.0, step=0.5, format="%.1f")

    v1, v2, v3 = valors

    comentaris = st.text_area(
        "Notes de la jornada",
        placeholder="Explica detalls rellevants...",
        height=90
    )
    operari = st.text_input("Operari responsable", value="Luis")
    st.markdown('</div>', unsafe_allow_html=True)

    # Fotos
    st.markdown('<div class="panel">', unsafe_allow_html=True)
    st.markdown('<span class="label-bold">Reportatge Fotogràfic</span>', unsafe_allow_html=True)
    tab_cam, tab_gal = st.tabs(["📷 Càmera", "🖼 Galeria"])
    with tab_cam:
        foto_cam = st.camera_input("Fer foto", label_visibility="collapsed")
    with tab_gal:
        fotos_extra = st.file_uploader(
            "Adjuntar fotos",
            accept_multiple_files=True,
            type=["jpg", "jpeg", "png", "webp"],
            label_visibility="collapsed"
        )
    st.markdown('</div>', unsafe_allow_html=True)

    enviar = st.form_submit_button("▶  FINALITZAR I ENVIAR INFORME")

# ==========================================
# 9. FIRMES — FORA del form (obligatori)
# ==========================================
st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<span class="label-bold">Signatures</span>', unsafe_allow_html=True)
col_f1, col_f2 = st.columns(2)

with col_f1:
    st.caption("Responsable d'obra")
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
    st.caption("Client / Propietari")
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
# 10. ENVIAMENT
# ==========================================
if enviar:
    if not operari.strip():
        st.warning("Cal indicar l'operari responsable.")
        st.stop()

    # Recollir fotos
    totes_fotos = []
    if foto_cam:
        n, b, m = sanitize_image("foto_obra", foto_cam.getvalue())
        totes_fotos.append((n, b, m))
    if fotos_extra:
        for f in fotos_extra:
            n, b, m = sanitize_image(f.name.rsplit(".", 1)[0], f.getvalue())
            totes_fotos.append((n, b, m))

    # Firmes
    firma_resp = canvas_to_bytes(canvas_resp)
    firma_cli  = canvas_to_bytes(canvas_cli)
    if firma_resp:
        totes_fotos.append(("firma_responsable.jpg", firma_resp, "image/jpeg"))
    if firma_cli:
        totes_fotos.append(("firma_client.jpg", firma_cli, "image/jpeg"))

    with st.spinner("Enviant informe..."):
        errors = []

        # A. Guardar a Sheets
        try:
            try:
                df_seg = conn.read(worksheet="Seguiment", ttl=0).dropna(how="all")
            except Exception:
                df_seg = pd.DataFrame(columns=[
                    "Data","Hora","Equip","Projecte","Tipus",
                    "Dada1","Dada2","Dada3","Comentaris","Operari","Fotos","Firmes"
                ])

            nova = pd.DataFrame([{
                "Data":       datetime.now().strftime("%d/%m/%Y"),
                "Hora":       datetime.now().strftime("%H:%M"),
                "Equip":      equip_actual,
                "Projecte":   obra_sel,
                "Tipus":      tipus_sel,
                "Dada1":      v1, "Dada2": v2, "Dada3": v3,
                "Comentaris": comentaris,
                "Operari":    operari,
                "Fotos":      len(totes_fotos),
                "Firmes":     ("Resp" if firma_resp else "") + ("·Client" if firma_cli else "")
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
                msg["Subject"] = f"[Seguiment] {obra_sel} · {tipus_sel} · {datetime.now().strftime('%d/%m/%Y')}"
                msg["From"]    = f"Estellé Parquet <{smtp_cfg['user']}>"
                msg["To"]      = ", ".join(destinataris)

                files_m = "".join(
                    f'<tr><td style="padding:8px 16px;border-bottom:1px solid #f0ebe8;color:#8d6e63;font-size:12px">{nom}</td>'
                    f'<td style="padding:8px 16px;border-bottom:1px solid #f0ebe8;color:#2c2c2c;font-size:14px;font-weight:600;text-align:right">{[v1,v2,v3][i]}</td></tr>'
                    for i, nom in enumerate(camps_actius)
                )
                logo_h  = f'<img src="{logo_url}" style="height:26px;margin-bottom:6px"><br>' if logo_url.startswith("http") else ""
                obs_h   = f'<div style="background:#fdf8f5;border-left:3px solid #8d6e63;padding:10px 14px;border-radius:0 8px 8px 0;color:#4a4a4a;font-size:13px;line-height:1.6;margin:14px 0">{comentaris}</div>' if comentaris.strip() else ""
                fotos_h = f'<p style="color:#8d6e63;font-size:12px">📎 {len(totes_fotos)} adjunt(s)</p>' if totes_fotos else ""

                html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#fdfaf7;font-family:'Helvetica Neue',sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="padding:24px 0"><tr><td align="center">
<table width="520" cellpadding="0" cellspacing="0" style="background:white;border:1px solid #e0d7d0;border-radius:14px;overflow:hidden">
<tr><td style="background:#4e342e;padding:22px 20px">
    {logo_h}
    <table width="100%"><tr>
        <td><div style="font-size:16px;font-weight:700;color:white">Informe de Seguiment</div>
            <div style="font-size:11px;color:rgba(255,255,255,0.6);margin-top:2px">{obra_sel} · {tipus_sel}</div></td>
        <td style="text-align:right"><div style="font-size:11px;color:rgba(255,255,255,0.6)">{datetime.now().strftime('%d/%m/%Y · %H:%M')}</div></td>
    </tr></table>
</td></tr>
<tr><td><table width="100%">
<tr>
    <td width="50%" style="padding:14px 16px;border-right:1px solid #f0ebe8;border-bottom:1px solid #f0ebe8">
        <div style="font-size:9px;color:#8d6e63;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px">Equip</div>
        <div style="font-size:14px;color:#2c2c2c;font-weight:600">{equip_actual}</div>
    </td>
    <td width="50%" style="padding:14px 16px;border-bottom:1px solid #f0ebe8">
        <div style="font-size:9px;color:#8d6e63;letter-spacing:2px;text-transform:uppercase;margin-bottom:4px">Operari</div>
        <div style="font-size:14px;color:#2c2c2c;font-weight:600">{operari}</div>
    </td>
</tr>
{files_m}
</table></td></tr>
{'<tr><td style="padding:0 16px">' + obs_h + '</td></tr>' if obs_h else ''}
{'<tr><td style="padding:8px 16px">' + fotos_h + '</td></tr>' if fotos_h else ''}
<tr><td style="padding:14px 16px;border-top:1px solid #f0ebe8;text-align:center">
    <div style="font-size:9px;color:#bcaaa4;letter-spacing:1px">ESTELLÉ PARQUET · SISTEMA DE SEGUIMENT AUTOMATITZAT</div>
</td></tr>
</table></td></tr></table></body></html>"""

                msg.attach(MIMEText(html, "html"))

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
                    s.sendmail(smtp_cfg["user"], destinataris, msg.as_string())

        except Exception as e:
            errors.append(f"Email: {e}")

    if not errors:
        fotos_txt = f"{len(totes_fotos)} adjunt(s)" if totes_fotos else "Sense adjunts"
        firmes_txt = []
        if firma_resp: firmes_txt.append("firma responsable")
        if firma_cli:  firmes_txt.append("firma client")
        f_txt = " · ".join(firmes_txt) if firmes_txt else "sense firmes"

        st.markdown(f"""
        <div class="success-box">
            <div style="font-size:1.3rem">✔</div>
            <div>
                <h4>Informe registrat correctament</h4>
                <p>{obra_sel} · {tipus_sel} · {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>{fotos_txt} · {f_txt}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for err in errors:
            st.error(err)
