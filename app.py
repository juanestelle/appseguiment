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


st.set_page_config(
    page_title="Estelle Parquet · Seguiment",
    page_icon="🧰",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Manrope:wght@400;600;700;800&family=JetBrains+Mono:wght@500&display=swap');

:root {
  --bg: #f5f7f4;
  --card: #ffffff;
  --text: #1f2a2a;
  --muted: #6a7670;
  --line: #d8e0da;
  --accent: #0f766e;
  --accent-soft: #e3f7f4;
  --ok: #1d9f70;
  --warn: #c97a00;
}

.stApp {
  background:
    radial-gradient(circle at 10% 5%, #e9f4ef 0%, transparent 45%),
    radial-gradient(circle at 90% 0%, #edf2fa 0%, transparent 35%),
    var(--bg);
  color: var(--text);
  font-family: 'Manrope', sans-serif;
}

#MainMenu, footer, header, [data-testid="stToolbar"] { visibility: hidden; }
.block-container { max-width: 760px; padding: 1rem 0.95rem 3.2rem; }

.panel {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  padding: 1rem;
  margin-bottom: 0.75rem;
  box-shadow: 0 10px 25px rgba(15, 41, 26, 0.04);
}

.hero {
  background: linear-gradient(135deg, #0f766e 0%, #0f766e 35%, #115e59 100%);
  color: white;
  border: none;
}

.hero h1 {
  margin: 0;
  font-size: clamp(1.1rem, 2.5vw, 1.45rem);
  line-height: 1.25;
  font-weight: 800;
}

.hero p { margin: 0.25rem 0 0; font-size: 0.84rem; opacity: 0.94; }

.kicker {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.56rem;
  border-radius: 999px;
  background: rgba(255,255,255,0.2);
  font-size: 0.72rem;
  font-family: 'JetBrains Mono', monospace;
}

.section-title {
  margin: 0 0 0.7rem;
  font-size: 0.82rem;
  text-transform: uppercase;
  color: var(--muted);
  letter-spacing: 0.08em;
  font-family: 'JetBrains Mono', monospace;
}

.stSelectbox label, .stNumberInput label, .stTextInput label, .stTextArea label,
.stFileUploader label, .stCameraInput label {
  color: var(--muted) !important;
  font-weight: 700 !important;
  font-size: 0.75rem !important;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.stTextInput > div > div > input,
.stTextArea > div > div > textarea,
.stSelectbox > div > div,
.stNumberInput input {
  border-radius: 12px !important;
  border: 1px solid var(--line) !important;
}

.stButton > button, .stFormSubmitButton > button {
  border-radius: 12px !important;
  border: 1px solid transparent !important;
  background: var(--accent) !important;
  color: white !important;
  font-weight: 800 !important;
  min-height: 46px;
}

.stButton > button[kind="secondary"] {
  background: #fff !important;
  border: 1px solid var(--line) !important;
  color: var(--text) !important;
}

.tip {
  background: var(--accent-soft);
  border: 1px solid #bde6e0;
  border-radius: 12px;
  padding: 0.7rem 0.8rem;
  color: #145e58;
  font-size: 0.84rem;
}

.photo-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit,minmax(140px,1fr));
  gap: 0.55rem;
  margin-top: 0.4rem;
}

.photo-item {
  border: 1px solid var(--line);
  border-radius: 10px;
  background: #fff;
  overflow: hidden;
}

.photo-item img {
  width: 100%;
  height: 112px;
  object-fit: cover;
  display: block;
}

.photo-item span {
  display: block;
  padding: 0.35rem 0.5rem;
  color: var(--muted);
  font-size: 0.72rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.notice-ok {
  border: 1px solid #bde7cf;
  background: #effbf4;
  color: #0f6a45;
  border-radius: 12px;
  padding: 0.85rem;
  font-size: 0.88rem;
}

@media (max-width: 700px) {
  .block-container { padding: 0.7rem 0.65rem 2.6rem; }
  .panel { border-radius: 14px; padding: 0.78rem; }
  .stButton > button, .stFormSubmitButton > button { min-height: 52px; font-size: 1rem !important; }
}
</style>
""",
    unsafe_allow_html=True,
)


def norm_pin(value) -> str:
    return str(value).strip().split(".")[0]


def sanitize_image(name: str, content: bytes, max_side: int = 2200) -> Tuple[str, bytes, str]:
    image = Image.open(BytesIO(content))
    image = ImageOps.exif_transpose(image)

    if image.mode not in ("RGB", "L"):
        image = image.convert("RGB")
    elif image.mode == "L":
        image = image.convert("RGB")

    width, height = image.size
    bigger_side = max(width, height)
    if bigger_side > max_side:
        ratio = max_side / float(bigger_side)
        image = image.resize((int(width * ratio), int(height * ratio)), Image.Resampling.LANCZOS)

    out = BytesIO()
    image.save(out, format="JPEG", quality=88, optimize=True, progressive=True)
    clean_name = f"{name.rsplit('.', 1)[0] if '.' in name else name}.jpg"
    return clean_name, out.getvalue(), "image/jpeg"


def email_html(
    logo_url: str,
    obra: str,
    tipus: str,
    equip: str,
    operari: str,
    camps: List[str],
    valors: List[float],
    comentaris: str,
    n_fotos: int,
) -> str:
    metric_rows = "".join(
        [
            f"""
            <tr>
              <td style="padding:10px 14px;color:#62706a;border-bottom:1px solid #e6ece8;font-size:13px">{label}</td>
              <td style="padding:10px 14px;color:#1f2a2a;border-bottom:1px solid #e6ece8;font-size:14px;font-weight:700;text-align:right">{value:.2f}</td>
            </tr>
            """
            for label, value in zip(camps, valors)
        ]
    )

    obs = (
        f"""
        <tr>
          <td colspan="2" style="padding:12px 14px">
            <div style="background:#f5faf8;border:1px solid #d8ece1;border-radius:10px;padding:10px 12px;color:#24453c;font-size:13px;line-height:1.5">{comentaris}</div>
          </td>
        </tr>
        """
        if comentaris.strip()
        else ""
    )

    logo_html = (
        f'<img src="{logo_url}" alt="Logo client" style="height:30px;width:auto;display:block;margin-bottom:8px">'
        if logo_url.startswith("http")
        else ""
    )

    photos = (
        f"<tr><td colspan=\"2\" style=\"padding:10px 14px;color:#0f766e;font-size:13px\">📷 {n_fotos} foto(s) adjuntada(es)</td></tr>"
        if n_fotos
        else ""
    )

    now = datetime.now().strftime("%d/%m/%Y · %H:%M")

    return f"""
<!doctype html>
<html>
  <body style="margin:0;padding:20px;background:#eef3f0;font-family:Arial,sans-serif;color:#1f2a2a;">
    <table width="100%" cellspacing="0" cellpadding="0">
      <tr>
        <td align="center">
          <table width="560" cellspacing="0" cellpadding="0" style="max-width:560px;background:#fff;border:1px solid #dbe4de;border-radius:14px;overflow:hidden;">
            <tr>
              <td style="padding:18px 18px 14px;background:#0f766e;color:white;">
                {logo_html}
                <div style="font-size:20px;font-weight:700;">Informe de Seguiment</div>
                <div style="font-size:12px;opacity:.92;margin-top:4px;">{obra} · {tipus}</div>
                <div style="font-size:12px;opacity:.88;margin-top:4px;">{now}</div>
              </td>
            </tr>
            <tr>
              <td style="padding:12px 16px;border-bottom:1px solid #e6ece8;">
                <table width="100%" cellspacing="0" cellpadding="0">
                  <tr>
                    <td style="font-size:12px;color:#667670;">Equip</td>
                    <td style="font-size:12px;color:#667670;text-align:right;">Operari</td>
                  </tr>
                  <tr>
                    <td style="font-size:15px;font-weight:700;color:#1f2a2a;">{equip}</td>
                    <td style="font-size:15px;font-weight:700;color:#1f2a2a;text-align:right;">{operari}</td>
                  </tr>
                </table>
              </td>
            </tr>
            <tr>
              <td>
                <table width="100%" cellspacing="0" cellpadding="0">
                  {metric_rows}
                  {obs}
                  {photos}
                </table>
              </td>
            </tr>
            <tr>
              <td style="padding:12px 16px;background:#f7faf8;font-size:11px;color:#6f7b75;text-align:center;">Estelle Parquet · Seguiment automatitzat</td>
            </tr>
          </table>
        </td>
      </tr>
    </table>
  </body>
</html>
"""


conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_projectes = conn.read(worksheet="Projectes", ttl=0).dropna(subset=["Nom"])
    df_templates = conn.read(worksheet="Config_Templates", ttl=0).dropna(subset=["Tipus"])
    df_equips = conn.read(worksheet="Equips", ttl=0).dropna(subset=["Equip"])
except Exception as err:
    st.error("No s'ha pogut connectar amb Google Sheets.")
    with st.expander("Detall de l'error"):
        st.code(str(err))
    st.stop()

if "equip_autenticat" not in st.session_state:
    st.session_state.equip_autenticat = None

if st.session_state.equip_autenticat is None:
    st.markdown(
        """
        <div class="panel hero">
          <span class="kicker">ESTELLE PARQUET</span>
          <h1>Seguiment diari d'obra</h1>
          <p>Accés ràpid per equips de camp. Entra amb el PIN per començar.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.form("login_form"):
        pin_input = st.text_input("PIN d'equip", type="password", placeholder="••••")
        login_btn = st.form_submit_button("Entrar")

    if login_btn:
        pin_match = df_equips[df_equips["PIN"].apply(norm_pin) == norm_pin(pin_input)]
        if pin_match.empty:
            st.error("PIN incorrecte. Revisa'l amb el responsable.")
        else:
            st.session_state.equip_autenticat = str(pin_match.iloc[0]["Equip"])
            st.rerun()

    st.stop()

equip_actual = st.session_state.equip_autenticat

if "Equip" in df_projectes.columns:
    df_proj = df_projectes[
        (df_projectes["Equip"].isna())
        | (df_projectes["Equip"].astype(str).str.strip() == "")
        | (df_projectes["Equip"].astype(str).str.strip() == equip_actual)
    ]
else:
    df_proj = df_projectes

if df_proj.empty:
    st.warning("No hi ha projectes assignats a aquest equip.")
    st.stop()

st.markdown(
    f"""
    <div class="panel hero">
      <span class="kicker">EQUIP: {equip_actual.upper()}</span>
      <h1>Registrar jornada</h1>
      <p>{datetime.now().strftime('%d/%m/%Y · %H:%M')}</p>
    </div>
    """,
    unsafe_allow_html=True,
)

logout_col1, logout_col2 = st.columns([4, 1])
with logout_col2:
    if st.button("Sortir", type="secondary", use_container_width=True):
        st.session_state.equip_autenticat = None
        st.rerun()

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<p class="section-title">1. Assignacio</p>', unsafe_allow_html=True)
sel_col1, sel_col2 = st.columns(2)

with sel_col1:
    obra_sel = st.selectbox("Projecte", sorted(df_proj["Nom"].dropna().unique()))
with sel_col2:
    tipus_sel = st.selectbox("Tipus de treball", sorted(df_templates["Tipus"].dropna().unique()))

dades_p = df_proj[df_proj["Nom"] == obra_sel].iloc[0]
dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]
logo_url = str(dades_p.get("Logo_client", "")).strip()

if logo_url.startswith("http"):
    st.image(logo_url, width=120)

st.markdown('</div>', unsafe_allow_html=True)

st.markdown('<div class="panel">', unsafe_allow_html=True)
st.markdown('<p class="section-title">2. Dades i fotos</p>', unsafe_allow_html=True)

with st.form("form_obra", clear_on_submit=True):
    camps_actius: List[str] = []
    for key in ["Camp1", "Camp2", "Camp3"]:
        val = dades_t.get(key, "")
        if pd.notna(val) and str(val).strip():
            camps_actius.append(str(val))

    valors = [0.0, 0.0, 0.0]
    if camps_actius:
        num_cols = st.columns(len(camps_actius))
        for idx, nom in enumerate(camps_actius):
            with num_cols[idx]:
                valors[idx] = st.number_input(nom, min_value=0.0, step=0.1, format="%.2f")

    comentaris = st.text_area(
        "Observacions",
        placeholder="Quin treball s'ha fet? Hi ha incidencies o material pendent?",
        height=100,
    )
    operari = st.text_input("Operari responsable", placeholder="Nom i cognom")

    st.markdown(
        """
        <div class="tip">
          Per fer fotos amb mobil/tablet: obre la pestanya Galeria i selecciona <b>Camera</b> al selector del dispositiu.
          Pots enviar una foto rapida o multiples imatges.
        </div>
        """,
        unsafe_allow_html=True,
    )

    cam_tab, gal_tab = st.tabs(["Camera rapida", "Galeria / Camera del dispositiu"])

    with cam_tab:
        foto_camera = st.camera_input("Fer foto", label_visibility="collapsed")

    with gal_tab:
        fotos_fitxer = st.file_uploader(
            "Selecciona imatges",
            type=["jpg", "jpeg", "png", "webp", "heic", "heif"],
            accept_multiple_files=True,
            label_visibility="collapsed",
            help="A mobil normalment apareix l'opcio Camera a mes de Galeria.",
        )

    st.markdown("###")
    subm = st.form_submit_button("Enviar informe", use_container_width=True)

st.markdown('</div>', unsafe_allow_html=True)

if subm:
    if not operari.strip():
        st.warning("Cal indicar l'operari responsable.")
        st.stop()

    fotos_processades: List[Tuple[str, bytes, str]] = []

    if foto_camera:
        try:
            fotos_processades.append(sanitize_image("foto_camera.jpg", foto_camera.getvalue()))
        except Exception as err:
            st.warning(f"No s'ha pogut processar la foto de camera: {err}")

    if fotos_fitxer:
        for photo in fotos_fitxer:
            try:
                fotos_processades.append(sanitize_image(photo.name, photo.getvalue()))
            except Exception:
                fotos_processades.append((photo.name, photo.getvalue(), photo.type or "application/octet-stream"))

    if fotos_processades:
        cards = []
        for idx, (name, content, _mime) in enumerate(fotos_processades, start=1):
            encoded = base64.b64encode(content).decode("utf-8")
            cards.append(
                f"<div class='photo-item'><img src='data:image/jpeg;base64,{encoded}' alt='preview {idx}'/><span>{name}</span></div>"
            )
        st.markdown(f"<div class='photo-grid'>{''.join(cards)}</div>", unsafe_allow_html=True)

    with st.spinner("Enviant informe..."):
        errors = []
        v1, v2, v3 = valors

        try:
            try:
                df_seg = conn.read(worksheet="Seguiment", ttl=0).dropna(how="all")
            except Exception:
                df_seg = pd.DataFrame(
                    columns=[
                        "Data",
                        "Hora",
                        "Equip",
                        "Projecte",
                        "Tipus",
                        "Dada1",
                        "Dada2",
                        "Dada3",
                        "Comentaris",
                        "Operari",
                        "Fotos",
                    ]
                )

            now = datetime.now()
            nova = pd.DataFrame(
                [
                    {
                        "Data": now.strftime("%d/%m/%Y"),
                        "Hora": now.strftime("%H:%M"),
                        "Equip": equip_actual,
                        "Projecte": obra_sel,
                        "Tipus": tipus_sel,
                        "Dada1": v1,
                        "Dada2": v2,
                        "Dada3": v3,
                        "Comentaris": comentaris,
                        "Operari": operari,
                        "Fotos": len(fotos_processades),
                    }
                ]
            )
            conn.update(worksheet="Seguiment", data=pd.concat([df_seg, nova], ignore_index=True))
        except Exception as err:
            errors.append(f"Sheets: {err}")

        try:
            smtp_cfg = st.secrets["smtp"]
            emails_raw = str(dades_p.get("Emails_Contacte", ""))
            destinataris = [e.strip() for e in emails_raw.split(",") if e.strip()]

            if destinataris:
                msg = MIMEMultipart("mixed")
                msg["Subject"] = f"[Seguiment] {obra_sel} · {tipus_sel} · {datetime.now().strftime('%d/%m/%Y')}"
                msg["From"] = f"Estelle Parquet <{smtp_cfg['user']}>"
                msg["To"] = ", ".join(destinataris)

                html = email_html(
                    logo_url=logo_url,
                    obra=obra_sel,
                    tipus=tipus_sel,
                    equip=equip_actual,
                    operari=operari,
                    camps=camps_actius,
                    valors=[v1, v2, v3],
                    comentaris=comentaris,
                    n_fotos=len(fotos_processades),
                )
                msg.attach(MIMEText(html, "html"))

                for nom, contingut, mime in fotos_processades:
                    parts = mime.split("/")
                    maintype = parts[0] if parts else "application"
                    subtype = parts[1] if len(parts) > 1 else "octet-stream"

                    adjunt = MIMEBase(maintype, subtype)
                    adjunt.set_payload(contingut)
                    encoders.encode_base64(adjunt)
                    adjunt.add_header("Content-Disposition", "attachment", filename=nom)
                    msg.attach(adjunt)

                with smtplib.SMTP(smtp_cfg["server"], int(smtp_cfg["port"])) as server:
                    server.starttls()
                    server.login(smtp_cfg["user"], smtp_cfg["password"])
                    server.sendmail(smtp_cfg["user"], destinataris, msg.as_string())
        except Exception as err:
            errors.append(f"Email: {err}")

    if errors:
        for err in errors:
            st.error(err)
    else:
        fotos_txt = (
            f"{len(fotos_processades)} foto(s) adjuntada(es)" if fotos_processades else "Sense fotografies"
        )
        st.markdown(
            f"<div class='notice-ok'><b>Informe enviat correctament.</b><br>{obra_sel} · {tipus_sel} · {datetime.now().strftime('%d/%m/%Y %H:%M')} · {fotos_txt}</div>",
            unsafe_allow_html=True,
        )
