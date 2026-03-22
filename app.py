import smtplib
import urllib.request
import ssl
import base64
import re
import json
from datetime import datetime
from io import BytesIO
from typing import Tuple, Optional
from urllib.parse import urlparse, parse_qs

import pandas as pd
import streamlit as st
from PIL import Image, ImageOps
from email import encoders
from email.mime.base import MIMEBase
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formataddr
from streamlit_gsheets import GSheetsConnection
from streamlit_drawable_canvas import st_canvas

# ==========================================
# CONFIGURACIÓ
# ==========================================
SHEETS_TTL_SECONDS = 60

st.set_page_config(page_title="Estellé Parquet · Seguimiento", page_icon="🪵", layout="centered")

logo_top = st.empty()

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;600&display=swap');
:root { --wood:#4e342e; --accent:#8d6e63; --bg:#fdfaf7; --white:#fcfcfc; --border:#e0d7d0; }
.stApp { background:var(--bg); color:#2c2c2c; font-family:'Inter',sans-serif; }
#MainMenu,footer,header { visibility:hidden; }
.block-container { max-width:980px; padding-top:.6rem; }
.stTabs [data-baseweb="tab-list"] { background:transparent !important; gap:4px; }
.team-header { background:var(--white); border:1px solid #efebe9; padding:20px; border-radius:18px;
    text-align:center; margin-bottom:16px; box-shadow:0 2px 12px rgba(0,0,0,0.03); }
.team-header h1 { font-family:'Outfit',sans-serif; font-weight:600; font-size:1.7rem; color:var(--wood); margin:0; }
.team-header p  { font-family:'Outfit',sans-serif; font-weight:300; color:var(--accent); margin:4px 0 0;
    text-transform:uppercase; letter-spacing:2px; font-size:0.75rem; }
.panel { background:white; border:1px solid var(--border); border-radius:16px; padding:20px; margin-bottom:14px; }
.label-up { font-weight:600; color:var(--accent); font-size:0.7rem; text-transform:uppercase;
    letter-spacing:1px; margin-bottom:10px; display:block; }
.foto-thumb-row { display:flex; flex-wrap:wrap; gap:8px; margin-top:10px; }
.foto-thumb-row img { height:64px; width:64px; object-fit:cover; border-radius:8px; border:1px solid var(--border); }
.firma-box { border:1.5px dashed #d7ccc8; border-radius:12px; overflow:hidden; background:#fafafa; }
.firma-ok { background:#e8f5e9; border:1px solid #a5d6a7; border-radius:8px;
    padding:6px 12px; font-size:0.78rem; color:#2e7d32; margin-top:6px; text-align:center; }
.stButton > button {
    background:transparent !important; color:var(--accent) !important;
    border:1px solid var(--border) !important; border-radius:8px !important;
    font-size:0.78rem !important; padding:0.4rem 0.9rem !important; width:auto !important; }
.stButton > button[kind="primary"] {
    background:var(--wood) !important; color:white !important;
    border-radius:12px !important; padding:0.85rem !important; font-weight:600 !important;
    border:none !important; font-size:1rem !important; min-height:56px !important;
    width:100% !important; }
.success-box { background:#f1f8f2; border:1px solid #a5d6a7; border-radius:12px; padding:16px 20px;
    display:flex; gap:12px; align-items:flex-start; margin-top:14px; }
.success-box h4 { margin:0 0 3px; color:#2e7d32; font-size:0.9rem; }
.success-box p  { margin:0; color:#666; font-size:0.76rem; line-height:1.5; }
/* ── REVISOR SPECIFIC ── */
.rev-banner { background:#fff8e1; border:1px solid #ffe082; border-left:4px solid #f59e0b;
    border-radius:10px; padding:14px 18px; margin-bottom:16px; }
.rev-banner h3 { margin:0 0 3px; color:#92400e; font-size:0.95rem; }
.rev-banner p  { margin:0; color:#78350f; font-size:0.76rem; }
.draft-card { background:white; border:1px solid var(--border); border-radius:14px;
    padding:16px 20px; margin-bottom:10px; cursor:pointer;
    transition: box-shadow 0.2s, border-color 0.2s; }
.draft-card:hover { box-shadow:0 4px 16px rgba(0,0,0,0.08); border-color:var(--accent); }
.draft-card h4 { margin:0 0 4px; color:var(--wood); font-size:1rem; }
.draft-card .meta { font-size:0.72rem; color:var(--accent); }
.badge-pendent { background:#fff3e0; color:#e65100; border:1px solid #ffcc80;
    border-radius:20px; padding:2px 10px; font-size:0.68rem; font-weight:600; }
.badge-enviat  { background:#e8f5e9; color:#2e7d32; border:1px solid #a5d6a7;
    border-radius:20px; padding:2px 10px; font-size:0.68rem; font-weight:600; }
.badge-rebutjat{ background:#fce4ec; color:#c62828; border:1px solid #ef9a9a;
    border-radius:20px; padding:2px 10px; font-size:0.68rem; font-weight:600; }
.preview-box { background:#f5f0eb; border:1px solid var(--border); border-radius:12px;
    padding:0; overflow:hidden; margin-top:8px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# HELPERS
# ==========================================
def norm_pin(v) -> str:
    return str(v).strip().split(".")[0]

def to_float_or_zero(x: str) -> float:
    x = (x or "").strip().replace(",", ".")
    try:
        return float(x) if x else 0.0
    except ValueError:
        return 0.0

def sanitize_image(name: str, content: bytes) -> Tuple[str, bytes, str]:
    img = Image.open(BytesIO(content))
    img = ImageOps.exif_transpose(img).convert("RGB")
    img.thumbnail((1400, 1400))
    out = BytesIO()
    img.save(out, format="JPEG", quality=85)
    return f"{name.rsplit('.', 1)[0]}.jpg", out.getvalue(), "image/jpeg"

def canvas_to_bytes(canvas_result) -> Optional[bytes]:
    if canvas_result is None or canvas_result.image_data is None:
        return None
    arr = canvas_result.image_data.astype("uint8")
    if arr[:, :, 3].max() < 10:
        return None
    img = Image.fromarray(arr, "RGBA").convert("RGB")
    out = BytesIO()
    img.save(out, format="JPEG", quality=90)
    return out.getvalue()

def normalize_logo_url(url: str) -> str:
    if not url: return ""
    u = url.strip().replace(" ", "%20")
    m = re.search(r"/file/d/([a-zA-Z0-9_-]+)", u)
    if m: return f"https://drive.google.com/uc?export=view&id={m.group(1)}"
    if "drive.google.com/open" in u and "id=" in u:
        q = parse_qs(urlparse(u).query)
        fid = q.get("id", [""])[0]
        if fid: return f"https://drive.google.com/uc?export=view&id={fid}"
    if "dropbox.com" in u: return u.replace("?dl=0", "?raw=1").replace("&dl=0", "&raw=1")
    return u

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_logo_jpeg(url: str) -> Optional[bytes]:
    u = normalize_logo_url(url)
    if not u.startswith("http"): return None
    req = urllib.request.Request(u, headers={"User-Agent": "Mozilla/5.0", "Accept": "image/*,*/*;q=0.8"})
    try:
        with urllib.request.urlopen(req, timeout=12, context=ssl.create_default_context()) as r:
            data = r.read()
        img = Image.open(BytesIO(data))
        img = ImageOps.exif_transpose(img)
        img.thumbnail((600, 200))
        fons = Image.new("RGB", img.size, (255, 249, 229))
        if img.mode in ("RGBA", "LA", "P"):
            img = img.convert("RGBA")
            fons.paste(img, mask=img.split()[3])
        else:
            fons.paste(img.convert("RGB"))
        out = BytesIO()
        fons.save(out, format="JPEG", quality=92, optimize=True)
        return out.getvalue()
    except Exception: return None

def fmt_valor(v) -> str:
    if v is None: return "0"
    f = float(v)
    return str(int(f)) if f == int(f) else f"{f:.1f}"

def img_to_thumb_b64(content: bytes) -> str:
    img = Image.open(BytesIO(content)).convert("RGB")
    img.thumbnail((120, 120))
    out = BytesIO()
    img.save(out, format="JPEG", quality=70)
    return base64.b64encode(out.getvalue()).decode()

def bytes_to_b64(b: bytes) -> str:
    return base64.b64encode(b).decode()

def b64_to_bytes(s: str) -> bytes:
    return base64.b64decode(s)

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def pick_col(df: pd.DataFrame, options: list) -> Optional[str]:
    cols_l = {c.lower(): c for c in df.columns}
    for opt in options:
        if opt.lower() in cols_l: return cols_l[opt.lower()]
    return None

def sort_with_tail(items_list):
    tail_items = ["Visita técnica", "Reparaciones", "Final de obra"]
    clean_list = list(dict.fromkeys(str(x).strip() for x in items_list if pd.notna(x) and str(x).strip()))
    main = sorted([x for x in clean_list if x not in tail_items])
    tail = [x for x in tail_items if x in clean_list]
    return main + tail

def get_camps_actius(dades_t_row) -> list:
    """Retorna la llista de (nom_camp, tipus) per a una fila de Config_Templates."""
    camps = []
    for i, col_key in enumerate(CAMPS_COLS, 1):
        if col_key and pd.notna(dades_t_row.get(col_key, "")) and str(dades_t_row.get(col_key, "")).strip():
            camps.append((str(dades_t_row.get(col_key)).strip(), "num" if i <= 4 else "txt"))
    return camps

# ==========================================
# EMAIL HTML BUILDER (funció reutilitzable)
# ==========================================
def build_email_html(obra_sel, camps_actius, valors_raw, comentaris,
                     equip_actual, membres_equip, logo_bytes, logo_url,
                     fotos_acumulades, firma_resp_bytes, firma_cli_bytes) -> str:
    logo_cid = "logo_client_estelle"
    treballs_html = ""
    for nom, tipus in camps_actius:
        val = valors_raw.get(nom, "").strip()
        if not val or val == "0" or val == "0.0": continue
        if tipus == "num":
            vf = fmt_valor(to_float_or_zero(val))
            treballs_html += (
                f'<tr><td align="right" style="padding:5px 10px 5px 0;font-size:22px;font-weight:700;'
                f'color:#555;font-family:Montserrat,sans-serif;white-space:nowrap">{vf}</td>'
                f'<td align="left" style="padding:5px 0;font-size:17px;color:#888;'
                f'font-family:Montserrat,sans-serif">{nom}</td></tr>'
            )
        else:
            treballs_html += (
                f'<tr><td colspan="2" style="padding:5px 0;font-size:15px;font-family:Montserrat,sans-serif">'
                f'<span style="color:#7747ff;font-weight:600">{nom}:</span>'
                f' <span style="color:#555;margin-left:6px">{val}</span></td></tr>'
            )

    obs_html = (
        f'<tr><td colspan="2" style="padding-top:18px">'
        f'<p style="margin:0 0 4px;color:#421cad;font-size:13px;font-weight:700;'
        f'font-family:Montserrat,sans-serif;text-transform:uppercase;letter-spacing:1px">Comentarios de la jornada</p>'
        f'<p style="margin:0;color:#6b5ea8;font-size:15px;line-height:1.6;font-family:Montserrat,sans-serif">'
        f'{comentaris}</p></td></tr>'
    ) if comentaris.strip() else ""

    adj_parts = []
    if fotos_acumulades:     adj_parts.append(f"{len(fotos_acumulades)} foto(s)")
    if firma_resp_bytes:     adj_parts.append("firma responsable")
    if firma_cli_bytes:      adj_parts.append("firma cliente")
    adj_html = (
        f'<tr><td colspan="2" style="padding-top:14px;font-size:12px;color:#aaa;'
        f'font-family:Montserrat,sans-serif">📎 Adjuntos: {", ".join(adj_parts)}</td></tr>'
    ) if adj_parts else ""

    logo_html = (
        f'<img src="cid:{logo_cid}" width="225" style="display:block;margin:0 auto;max-width:225px;border:0">'
        if logo_bytes else (
            f'<img src="{logo_url}" width="225" style="display:block;margin:0 auto;max-width:225px;border:0">'
            if logo_url and logo_url.startswith("http") else ""
        )
    )

    def f_td(lbl, has, fn):
        return (
            f'<td width="50%" style="padding:25px;vertical-align:top">'
            f'<p style="margin:0;font-family:Montserrat,sans-serif;font-size:16px;color:#101112">📎 {lbl}</p>'
            f'<p style="margin:4px 0 0;font-family:Montserrat,sans-serif;font-size:12px;color:#aaa">{fn}</p></td>'
        ) if has else ""

    f_row = (
        f'<tr><td style="padding:0 30px"><hr style="border:none;border-top:1px solid #e8e0d0;margin:0"></td></tr>'
        f'<tr><td style="padding:10px 0"><table width="100%"><tr>'
        f'{f_td("Firma responsable", firma_resp_bytes is not None, "firma_responsable.jpg")}'
        f'{f_td("Firma cliente", firma_cli_bytes is not None, "firma_cliente.jpg")}'
        f'</tr></table></td></tr>'
    ) if (firma_resp_bytes or firma_cli_bytes) else ""

    eq_html = (
        f'<table width="60%" align="center" style="margin-top:16px;">'
        f'<tr><td style="border-top:1px solid #e8e0d0; padding-top:16px;" align="center">'
        f'<p style="margin:0;font-size:14px;color:#aaa;font-weight:600;font-family:Montserrat,sans-serif">Equipo</p>'
        f'<p style="margin:0;font-size:18px;font-weight:600;color:#8125bb;font-family:Montserrat,sans-serif">'
        f'{membres_equip.strip()}</p></td></tr></table>'
    ) if membres_equip.strip() else ""

    return f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#fefdf1">
<table width="100%" bgcolor="#fefdf1"><tr><td align="center" style="padding:30px 10px">
<table width="580" style="background:#fff9e5;border-radius:14px;overflow:hidden;box-shadow:0 4px 20px rgba(0,0,0,0.06)">
  <tr><td align="center" style="padding:32px 30px 16px;">{logo_html}</td></tr>
  <tr><td align="center" style="padding:16px 30px 8px"><p style="margin:0;color:#7747ff;font-size:17px;font-family:Montserrat,sans-serif">{datetime.now().strftime("%d · %m · %Y")}</p></td></tr>
  <tr><td style="padding:0 30px"><hr style="border:none;border-top:1px solid #e8e0d0;margin:0"></td></tr>
  <tr><td align="center" style="padding:22px 30px 8px"><p style="margin:0 0 4px;font-size:11px;color:#777;text-transform:uppercase;letter-spacing:2px;font-family:Montserrat,sans-serif">Proyecto</p><p style="margin:0 0 4px;font-size:20px;font-weight:700;color:#1a1a1a;font-family:Montserrat,sans-serif">{obra_sel}</p></td></tr>
  <tr><td style="padding:14px 30px 0"><hr style="border:none;border-top:1px solid #e8e0d0;margin:0"></td></tr>
  <tr><td align="center" style="padding:20px 30px 6px"><p style="margin:0;font-size:13px;font-weight:700;color:#7747ff;text-transform:uppercase;letter-spacing:3px;font-family:Montserrat,sans-serif">Trabajos</p></td></tr>
  <tr><td align="center" style="padding:4px 30px 20px"><table align="center">{treballs_html}{obs_html}{adj_html}</table></td></tr>
  <tr><td style="padding:0 30px"><hr style="border:none;border-top:1px solid #e8e0d0;margin:0"></td></tr>
  <tr><td align="center" style="padding:20px 30px"><p style="margin:0;font-size:14px;color:#aaa;font-weight:600;font-family:Montserrat,sans-serif">Responsable en obra</p><p style="margin:0;font-size:20px;font-weight:700;color:#8125bb;font-family:Montserrat,sans-serif">{equip_actual}</p>{eq_html}</td></tr>
  {f_row}
  <tr><td align="center" style="padding:16px 30px 24px;border-top:1px solid #e8e0d0"><a href="http://www.estelleparquet.com" style="color:#4e342e;font-size:13px;text-decoration:none;font-family:Montserrat,sans-serif">www.estelleparquet.com</a></td></tr>
</table></td></tr></table></body></html>"""

# ==========================================
# SEND EMAIL (funció reutilitzable)
# ==========================================
def send_email(smtp_cfg, destinataris, subject, html_body,
               logo_bytes, logo_url,
               fotos: list, firma_resp: Optional[bytes], firma_cli: Optional[bytes]):
    msg = MIMEMultipart("mixed")
    msg["Subject"]  = subject
    msg["From"]     = formataddr(("Estelle Parquet", smtp_cfg["user"]))
    msg["Reply-To"] = smtp_cfg["user"]
    msg["To"]       = ", ".join(destinataris)
    logo_cid = "logo_client_estelle"

    body_related = MIMEMultipart("related")
    body_alt = MIMEMultipart("alternative")
    body_alt.attach(MIMEText(html_body, "html"))
    body_related.attach(body_alt)

    if logo_bytes:
        img_logo = MIMEImage(logo_bytes, _subtype="jpeg")
        img_logo.add_header("Content-ID", f"<{logo_cid}>")
        body_related.attach(img_logo)
    msg.attach(body_related)

    adjunts = list(fotos)
    if firma_resp: adjunts.append(("firma_responsable.jpg", firma_resp, "image/jpeg"))
    if firma_cli:  adjunts.append(("firma_cliente.jpg",     firma_cli,  "image/jpeg"))
    for n_f, cont, mime in adjunts:
        adj = MIMEBase(*(mime.split("/")))
        adj.set_payload(cont); encoders.encode_base64(adj)
        adj.add_header("Content-Disposition", "attachment", filename=n_f)
        msg.attach(adj)

    port = int(smtp_cfg.get("port", 587))
    if port == 465:
        with smtplib.SMTP_SSL(smtp_cfg["server"], port) as s:
            s.login(smtp_cfg["user"], smtp_cfg["password"])
            s.sendmail(smtp_cfg["user"], destinataris, msg.as_string())
    else:
        with smtplib.SMTP(smtp_cfg["server"], port) as s:
            s.starttls()
            s.login(smtp_cfg["user"], smtp_cfg["password"])
            s.sendmail(smtp_cfg["user"], destinataris, msg.as_string())

# ==========================================
# BORRANYS: LLEGIR / GUARDAR
# ==========================================
BORRANYS_COLS = [
    "ID", "Timestamp", "Equip", "Membres", "Obra", "Tipus",
    "Comentaris", "Valors_JSON", "Fotos_B64_JSON",
    "Firma_resp_B64", "Firma_cli_B64",
    "Destinataris", "Estat", "Nota_revisor"
]

def load_borranys() -> pd.DataFrame:
    try:
        df = normalize_columns(conn.read(worksheet="Borranys", ttl=0))
        if df.empty or list(df.columns) != BORRANYS_COLS:
            return pd.DataFrame(columns=BORRANYS_COLS)
        return df.dropna(how="all")
    except Exception:
        return pd.DataFrame(columns=BORRANYS_COLS)

def save_borrany(equip, membres, obra, tipus, comentaris,
                 camps_actius, valors_raw,
                 fotos_acumulades, firma_resp_bytes, firma_cli_bytes,
                 destinataris: list):
    """Desa un esborrany d'informe a la pestanya Borranys."""
    borrany_id = str(int(datetime.now().timestamp()))

    valors_dict = {nom: valors_raw.get(nom, "") for nom, _ in camps_actius}
    valors_json = json.dumps(valors_dict, ensure_ascii=False)

    fotos_b64 = json.dumps([bytes_to_b64(b) for _, b, _ in fotos_acumulades])

    firma_resp_b64 = bytes_to_b64(firma_resp_bytes) if firma_resp_bytes else ""
    firma_cli_b64  = bytes_to_b64(firma_cli_bytes)  if firma_cli_bytes  else ""

    row = {
        "ID":            borrany_id,
        "Timestamp":     datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Equip":         equip,
        "Membres":       membres,
        "Obra":          obra,
        "Tipus":         tipus,
        "Comentaris":    comentaris,
        "Valors_JSON":   valors_json,
        "Fotos_B64_JSON": fotos_b64,
        "Firma_resp_B64": firma_resp_b64,
        "Firma_cli_B64":  firma_cli_b64,
        "Destinataris":  ",".join(destinataris),
        "Estat":         "PENDENT",
        "Nota_revisor":  ""
    }

    try:
        df_borr = load_borranys()
        df_new  = pd.concat([df_borr, pd.DataFrame([row])], ignore_index=True)
        conn.update(worksheet="Borranys", data=df_new)
        return borrany_id
    except Exception as e:
        st.error(f"Error desant l'esborrany: {e}")
        return None

def update_borrany_estat(borrany_id: str, estat: str, nota: str = ""):
    try:
        df = load_borranys()
        idx = df[df["ID"] == str(borrany_id)].index
        if not idx.empty:
            df.at[idx[0], "Estat"] = estat
            df.at[idx[0], "Nota_revisor"] = nota
            conn.update(worksheet="Borranys", data=df)
    except Exception as e:
        st.error(f"Error actualitzant estat: {e}")

def update_borrany_contingut(borrany_id: str, comentaris: str, valors_dict: dict, nota: str = ""):
    try:
        df = load_borranys()
        idx = df[df["ID"] == str(borrany_id)].index
        if not idx.empty:
            df.at[idx[0], "Comentaris"]  = comentaris
            df.at[idx[0], "Valors_JSON"] = json.dumps(valors_dict, ensure_ascii=False)
            df.at[idx[0], "Nota_revisor"] = nota
            conn.update(worksheet="Borranys", data=df)
    except Exception as e:
        st.error(f"Error actualitzant contingut: {e}")

# ==========================================
# CONNEXIÓ SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df_projectes = normalize_columns(conn.read(worksheet="Projectes",        ttl=SHEETS_TTL_SECONDS))
    df_templates = normalize_columns(conn.read(worksheet="Config_Templates",  ttl=SHEETS_TTL_SECONDS))
    df_equips    = normalize_columns(conn.read(worksheet="Equips",             ttl=SHEETS_TTL_SECONDS))
except Exception as e:
    st.error("Error de conexión con Google Sheets.")
    st.stop()

col_nom         = pick_col(df_projectes, ["Nom","Nombre","Projecte","Proyecto"])
col_logo        = pick_col(df_projectes, ["Logo_Client","Logo_client","Logo","LogoClient"])
col_emails      = pick_col(df_projectes, ["Emails_Contacte","Emails_contacte","Emails","Email"])
col_equip_proj  = pick_col(df_projectes, ["Equip","Equipo"])
col_treball_def = pick_col(df_projectes, ["Treball_Predeterminat","Treball_Prioritari","Trabajo_Prioritario","Tipo_Defecto"])

col_tipus    = pick_col(df_templates, ["Tipus","Tipo"])
CAMPS_COLS   = [pick_col(df_templates, [f"Camp{i}"]) for i in range(1, 11)]
col_equip_eq = pick_col(df_equips, ["Equip","Equipo"])
col_pin      = pick_col(df_equips, ["PIN","Pin","pin"])

if not all([col_nom, col_tipus, col_equip_eq, col_pin]):
    st.error("Falten columnes obligatòries a Sheets.")
    st.stop()

df_projectes = df_projectes[df_projectes[col_nom].notna()].copy()
df_projectes[col_nom] = df_projectes[col_nom].astype(str).str.strip()
df_templates = df_templates[df_templates[col_tipus].notna()].copy()
df_templates[col_tipus] = df_templates[col_tipus].astype(str).str.strip()

# ==========================================
# LOGIN — NORMAL + REVISOR
# ==========================================
def get_revisor_pins() -> list:
    try:
        raw = st.secrets["revisor"]["pin"]
        return [norm_pin(p) for p in str(raw).split(",")]
    except Exception:
        return []

if "auth_user" not in st.session_state:
    st.markdown("""<div class="team-header"><h1>Estellé Parquet</h1><p>Acceso Instaladores</p></div>""", unsafe_allow_html=True)
    with st.form("login"):
        pin_in = st.text_input("PIN de Equipo", type="password", placeholder="····")
        if st.form_submit_button("ENTRAR"):
            pin_norm = norm_pin(pin_in)
            if pin_norm in get_revisor_pins():
                st.session_state.auth_user = "Revisor"
                st.session_state.auth_rol  = "revisor"
                st.rerun()
            else:
                match = df_equips[df_equips[col_pin].apply(norm_pin) == pin_norm]
                if not match.empty:
                    st.session_state.auth_user = str(match.iloc[0][col_equip_eq]).strip()
                    st.session_state.auth_rol  = "instalador"
                    st.session_state.fotos_acumulades = []
                    st.session_state.camara_activa    = False
                    st.session_state.firma_resp_bytes = None
                    st.session_state.firma_cli_bytes  = None
                    st.rerun()
                else:
                    st.error("PIN incorrecto.")
    st.stop()

equip_actual = str(st.session_state.auth_user).strip()
rol_actual   = st.session_state.get("auth_rol", "instalador")

# ==========================================
# ══════ VISTA REVISOR ══════════════════════
# ==========================================
if rol_actual == "revisor":

    col_hd, col_out = st.columns([5, 1])
    with col_hd:
        st.markdown(f"""<div class="team-header">
            <p>{datetime.now().strftime("%d · %m · %Y")}</p>
            <h1>🔍 Panel de Revisió</h1></div>""", unsafe_allow_html=True)
    with col_out:
        st.markdown("<div style='margin-top:22px'>", unsafe_allow_html=True)
        if st.button("Salir"):
            for k in ["auth_user", "auth_rol"]:
                st.session_state.pop(k, None)
            st.rerun()
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("""<div class="rev-banner">
        <h3>⚠️ Informes pendents d'aprovació</h3>
        <p>Revisa, edita si cal i aprova l'enviament al client. Els informes rebutjats queden registrats però no s'envien.</p>
    </div>""", unsafe_allow_html=True)

    df_borranys = load_borranys()
    pendents    = df_borranys[df_borranys["Estat"] == "PENDENT"]
    enviats     = df_borranys[df_borranys["Estat"] == "ENVIAT"]
    rebutjats   = df_borranys[df_borranys["Estat"] == "REBUTJAT"]

    tab_pend, tab_hist = st.tabs([
        f"🟡 Pendents ({len(pendents)})",
        f"📋 Historial ({len(enviats) + len(rebutjats)})"
    ])

    with tab_pend:
        if pendents.empty:
            st.success("✅ No hi ha informes pendents de revisió.")
        else:
            pendent_opts = {
                f"[{r['Timestamp']}]  {r['Obra']}  ·  {r['Equip']}  ·  {r['Tipus']}": r["ID"]
                for _, r in pendents.iterrows()
            }
            sel_label = st.selectbox("Selecciona un informe:", list(pendent_opts.keys()))
            borrany_id = pendent_opts[sel_label]
            brow = pendents[pendents["ID"] == borrany_id].iloc[0]

            try:
                valors_dict_orig = json.loads(brow["Valors_JSON"]) if brow["Valors_JSON"] else {}
            except Exception:
                valors_dict_orig = {}
            try:
                fotos_b64_list = json.loads(brow["Fotos_B64_JSON"]) if brow["Fotos_B64_JSON"] else []
            except Exception:
                fotos_b64_list = []

            firma_resp_b = b64_to_bytes(brow["Firma_resp_B64"]) if brow.get("Firma_resp_B64", "").strip() else None
            firma_cli_b  = b64_to_bytes(brow["Firma_cli_B64"])  if brow.get("Firma_cli_B64", "").strip()  else None
            fotos_bytes  = [(f"foto_{i+1:02d}.jpg", b64_to_bytes(b), "image/jpeg")
                            for i, b in enumerate(fotos_b64_list)]

            # Emails: primer del borrany desat, fallback de la fulla actual
            destinataris_orig = [e.strip() for e in str(brow.get("Destinataris","")).split(",") if e.strip()]
            if not destinataris_orig and col_emails:
                dades_p_rev = df_projectes[df_projectes[col_nom] == brow["Obra"]]
                if not dades_p_rev.empty:
                    emails_fulla = str(dades_p_rev.iloc[0].get(col_emails, "")).strip()
                    destinataris_orig = [e.strip() for e in emails_fulla.split(",") if e.strip()]

            st.markdown("---")
            st.markdown(f"""
            <div style="display:flex;gap:24px;margin-bottom:12px;font-size:0.82rem;color:var(--accent);">
                <span>📁 <b>{brow['Obra']}</b></span>
                <span>👷 {brow['Equip']}</span>
                <span>🛠 {brow['Tipus']}</span>
                <span>🗓 {brow['Timestamp']}</span>
            </div>""", unsafe_allow_html=True)

            with st.expander("✏️ Editar contingut de l'informe", expanded=True):

                comentaris_ed = st.text_area(
                    "Comentarios de la jornada",
                    value=brow.get("Comentaris", ""),
                    height=100,
                    key="rev_comentaris"
                )

                st.markdown('<span class="label-up">Valors del informe</span>', unsafe_allow_html=True)
                valors_ed = {}
                if valors_dict_orig:
                    cols_ed = st.columns(min(len(valors_dict_orig), 4))
                    for i, (nom, val) in enumerate(valors_dict_orig.items()):
                        with cols_ed[i % 4]:
                            valors_ed[nom] = st.text_input(nom, value=str(val), key=f"rev_val_{i}")
                else:
                    st.info("Sense camps de mesures.")
                    valors_ed = {}

                nota_rev = st.text_input(
                    "Nota interna del revisor (opcional, no s'envia al client)",
                    placeholder="Ex: Corregit import m² incorrecte",
                    key="rev_nota"
                )

                if fotos_bytes:
                    st.markdown(f'<span class="label-up">Fotografies adjuntes ({len(fotos_bytes)})</span>', unsafe_allow_html=True)
                    t_html = '<div class="foto-thumb-row">'
                    for _, b, _ in fotos_bytes:
                        t_html += f'<img src="data:image/jpeg;base64,{img_to_thumb_b64(b)}">'
                    st.markdown(t_html + '</div>', unsafe_allow_html=True)

                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    if firma_resp_b:
                        st.caption("Firma Responsable")
                        st.image(firma_resp_b, width=160)
                    else:
                        st.caption("Firma Responsable: —")
                with col_f2:
                    if firma_cli_b:
                        st.caption("Firma Client")
                        st.image(firma_cli_b, width=160)
                    else:
                        st.caption("Firma Client: —")

                # Destinataris: avís si buit i camp editable
                if not destinataris_orig:
                    st.warning(
                        "⚠️ Aquest projecte no té cap email configurat. "
                        "Afegeix l'email del client a la fulla Projectes (columna Emails\_Contacte) "
                        "o escriu-lo manualment avar."
                    )
                dest_ed = st.text_input(
                    "Destinataris (emails separats per comes)",
                    value=", ".join(destinataris_orig),
                    placeholder="client@empresa.com, cap.obra@empresa.com",
                    key="rev_dest"
                )

            with st.expander("👁 Previsualitzar email al client"):
                dades_t_match = df_templates[df_templates[col_tipus] == brow["Tipus"]]
                camps_actius_rev = get_camps_actius(dades_t_match.iloc[0]) if not dades_t_match.empty else []

                dades_p_match = df_projectes[df_projectes[col_nom] == brow["Obra"]]
                logo_bytes_rev, logo_url_rev = None, ""
                if not dades_p_match.empty and col_logo:
                    logo_url_rev = normalize_logo_url(str(dades_p_match.iloc[0].get(col_logo, "")).strip())
                    logo_bytes_rev = fetch_logo_jpeg(logo_url_rev) if logo_url_rev else None

                html_preview = build_email_html(
                    obra_sel=brow["Obra"],
                    camps_actius=camps_actius_rev,
                    valors_raw=valors_ed if valors_ed else valors_dict_orig,
                    comentaris=comentaris_ed,
                    equip_actual=brow["Equip"],
                    membres_equip=brow.get("Membres", ""),
                    logo_bytes=logo_bytes_rev,
                    logo_url=logo_url_rev,
                    fotos_acumulades=fotos_bytes,
                    firma_resp_bytes=firma_resp_b,
                    firma_cli_bytes=firma_cli_b
                )
                st.components.v1.html(html_preview, height=600, scrolling=True)

            st.markdown("---")
            c_apr, c_reb = st.columns(2)

            with c_apr:
                if st.button("✅ APROVAR I ENVIAR AL CLIENT", type="primary", use_container_width=True):
                    dest_final = [e.strip() for e in dest_ed.split(",") if e.strip()]
                    if not dest_final:
                        st.error("❌ Cap destinatari. Afegeix l'email a la fulla Projectes o escriu-lo al camp de sobre.")
                    else:
                        with st.spinner("Enviant email al client..."):
                            try:
                                update_borrany_contingut(borrany_id, comentaris_ed, valors_ed, nota_rev)

                                dades_t_match = df_templates[df_templates[col_tipus] == brow["Tipus"]]
                                camps_actius_send = get_camps_actius(dades_t_match.iloc[0]) if not dades_t_match.empty else []

                                html_final = build_email_html(
                                    obra_sel=brow["Obra"],
                                    camps_actius=camps_actius_send,
                                    valors_raw=valors_ed if valors_ed else valors_dict_orig,
                                    comentaris=comentaris_ed,
                                    equip_actual=brow["Equip"],
                                    membres_equip=brow.get("Membres",""),
                                    logo_bytes=logo_bytes_rev,
                                    logo_url=logo_url_rev,
                                    fotos_acumulades=fotos_bytes,
                                    firma_resp_bytes=firma_resp_b,
                                    firma_cli_bytes=firma_cli_b
                                )
                                smtp_cfg = st.secrets["smtp"]
                                send_email(
                                    smtp_cfg=smtp_cfg,
                                    destinataris=dest_final,
                                    subject=f"Seguimiento del proyecto {brow['Obra']} - Estelle parquet",
                                    html_body=html_final,
                                    logo_bytes=logo_bytes_rev,
                                    logo_url=logo_url_rev,
                                    fotos=fotos_bytes,
                                    firma_resp=firma_resp_b,
                                    firma_cli=firma_cli_b
                                )
                                update_borrany_estat(borrany_id, "ENVIAT", nota_rev)
                                st.success(f"✅ Email enviat correctament a: {', '.join(dest_final)}")
                                st.balloons()
                            except Exception as e:
                                st.error(f"Error enviant email: {e}")

            with c_reb:
                motiu_reb = st.text_input("Motiu del rebuig (opcional)", key="motiu_reb", placeholder="Ex: Falta informació del client")
                if st.button("❌ Rebutjar informe", use_container_width=True):
                    update_borrany_estat(borrany_id, "REBUTJAT", motiu_reb)
                    st.warning("Informe marcat com a rebutjat. L'instal·lador haurà de reenviar.")
                    st.rerun()

    with tab_hist:
        if enviats.empty and rebutjats.empty:
            st.info("Encara no hi ha historial d'informes.")
        else:
            df_hist = pd.concat([enviats, rebutjats]).sort_values("Timestamp", ascending=False)
            for _, r in df_hist.iterrows():
                badge = (
                    '<span class="badge-enviat">ENVIAT</span>' if r["Estat"] == "ENVIAT"
                    else '<span class="badge-rebutjat">REBUTJAT</span>'
                )
                nota_txt = f" · <i>{r['Nota_revisor']}</i>" if r.get("Nota_revisor") else ""
                st.markdown(f"""
                <div class="draft-card">
                    <div style="display:flex;justify-content:space-between;align-items:center">
                        <div>
                            <h4>{r['Obra']} — {r['Tipus']}</h4>
                            <div class="meta">👷 {r['Equip']} &nbsp;·&nbsp; 🗓 {r['Timestamp']}{nota_txt}</div>
                        </div>
                        {badge}
                    </div>
                </div>""", unsafe_allow_html=True)

    st.stop()

# ==========================================
# ══════ VISTA INSTAL·LADOR ═════════════════
# ==========================================

if col_equip_proj:
    def projecte_permet_equip(row_equip):
        if pd.isna(row_equip) or str(row_equip).strip() == "": return True
        llista_equips = [e.strip().lower() for e in str(row_equip).split(",")]
        return equip_actual.lower() in llista_equips
    df_proj = df_projectes[df_projectes[col_equip_proj].apply(projecte_permet_equip)].copy()
else:
    df_proj = df_projectes.copy()

df_proj = df_proj.drop_duplicates(subset=[col_nom])
if df_proj.empty: st.warning("No hay proyectos asignados."); st.stop()

col_hd, col_out = st.columns([5, 1])
with col_hd:
    st.markdown(f"""<div class="team-header"><p>{datetime.now().strftime("%d · %m · %Y")}</p><h1>{equip_actual}</h1></div>""", unsafe_allow_html=True)
with col_out:
    st.markdown("<div style='margin-top:22px'>", unsafe_allow_html=True)
    if st.button("Salir"):
        for k in ["auth_user","auth_rol","fotos_acumulades","camara_activa","firma_resp_bytes","firma_cli_bytes"]:
            st.session_state.pop(k, None)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

llista_projectes = sort_with_tail(df_proj[col_nom].tolist())
llista_treballs  = sort_with_tail(df_templates[col_tipus].tolist())

col_a, col_b = st.columns(2)
obra_sel = col_a.selectbox("Proyecto", llista_projectes)
dades_p  = df_proj[df_proj[col_nom] == obra_sel].iloc[0]

treball_predef = str(dades_p.get(col_treball_def, "")).strip() if col_treball_def else ""
idx_treball    = llista_treballs.index(treball_predef) if treball_predef in llista_treballs else 0
tipus_sel = col_b.selectbox("Trabajo realizado", llista_treballs, index=idx_treball)

membres_equip = st.text_input("Otros miembros del equipo en obra (opcional)", placeholder="Ej: Edgar, Eric, Mario", key="membres_equip")

dades_t = df_templates[df_templates[col_tipus] == tipus_sel].iloc[0]

logo_url   = normalize_logo_url(str(dades_p.get(col_logo, "")).strip()) if col_logo and pd.notna(dades_p.get(col_logo, "")) else ""
logo_bytes = fetch_logo_jpeg(logo_url) if logo_url else None
with logo_top.container():
    if logo_url.startswith("http"):  st.image(logo_url, width=320)
    elif logo_bytes:                  st.image(logo_bytes, width=320)

camps_actius = get_camps_actius(dades_t)

st.markdown('<span class="label-up">Medidas y avance</span>', unsafe_allow_html=True)
valors_raw = {}
if camps_actius:
    camps_num = [(n, t) for n, t in camps_actius if t == "num"]
    camps_txt = [(n, t) for n, t in camps_actius if t == "txt"]
    if camps_num:
        cols_num = st.columns(min(len(camps_num), 4))
        for i, (nom, _) in enumerate(camps_num):
            with cols_num[i % 4]:
                valors_raw[nom] = st.text_input(nom, value="", placeholder="0", key=f"val_num_{i}")
    if camps_txt:
        st.markdown("<div style='margin-top:8px'></div>", unsafe_allow_html=True)
        cols_txt = st.columns(min(len(camps_txt), 2))
        for i, (nom, _) in enumerate(camps_txt):
            with cols_txt[i % 2]:
                valors_raw[nom] = st.text_input(nom, value="", placeholder="—", key=f"val_txt_{i}")

comentaris = st.text_area("Comentarios de la jornada", placeholder="Detalles relevantes...", height=90, key="comentaris")

st.markdown('<div class="panel"><span class="label-up">Reportaje fotográfico</span>', unsafe_allow_html=True)
tab_cam, tab_gal = st.tabs(["📷 Cámara", "🖼 Galería"])
with tab_cam:
    if not st.session_state.camara_activa:
        if st.button("📷 Activar cámara"): st.session_state.camara_activa = True; st.rerun()
    else:
        foto_cam = st.camera_input("Capturar", label_visibility="collapsed")
        if st.button("＋ Añadir foto") and foto_cam:
            n, b, m = sanitize_image(f"foto_{len(st.session_state.fotos_acumulades)+1:02d}", foto_cam.getvalue())
            st.session_state.fotos_acumulades.append((n, b, m)); st.session_state.camara_activa = False; st.rerun()
with tab_gal:
    fotos_gal = st.file_uploader("Subir fotos", type=["jpg","jpeg","png","webp"], accept_multiple_files=True, label_visibility="collapsed")
    if fotos_gal and st.button("＋ Añadir selección"):
        for f in fotos_gal:
            n, b, m = sanitize_image(f.name, f.getvalue())
            st.session_state.fotos_acumulades.append((n, b, m))
        st.rerun()
if st.session_state.fotos_acumulades:
    t_html = '<div class="foto-thumb-row">'
    for n_f, c_f, _ in st.session_state.fotos_acumulades:
        t_html += f'<img src="data:image/jpeg;base64,{img_to_thumb_b64(c_f)}">'
    st.markdown(t_html + '</div>', unsafe_allow_html=True)
    if st.button("🗑 Borrar todas las fotos"): st.session_state.fotos_acumulades = []; st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="panel"><span class="label-up">Firmas</span>', unsafe_allow_html=True)
cf1, cf2 = st.columns(2)
with cf1:
    st.caption("Responsable")
    cv_r = st_canvas(stroke_width=2, stroke_color="#1a1a1a", background_color="#fafafa", height=140, key="cv_r", display_toolbar=False)
    if st.button("💾 Guardar responsable"): st.session_state.firma_resp_bytes = canvas_to_bytes(cv_r); st.rerun()
    if st.session_state.firma_resp_bytes:
        st.markdown('<div class="firma-ok">✔ Firma lista</div>', unsafe_allow_html=True)
        if st.button("🗑 Esborrar firma resp.", key="del_firma_r"):
            st.session_state.firma_resp_bytes = None; st.rerun()
with cf2:
    st.caption("Cliente")
    cv_c = st_canvas(stroke_width=2, stroke_color="#1a1a1a", background_color="#fafafa", height=140, key="cv_c", display_toolbar=False)
    if st.button("💾 Guardar cliente"): st.session_state.firma_cli_bytes = canvas_to_bytes(cv_c); st.rerun()
    if st.session_state.firma_cli_bytes:
        st.markdown('<div class="firma-ok">✔ Firma lista</div>', unsafe_allow_html=True)
        if st.button("🗑 Esborrar firma client", key="del_firma_c"):
            st.session_state.firma_cli_bytes = None; st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# ENVIAMENT → ARA VA A REVISIÓ
# ==========================================
if st.button("▶ ENVIAR A REVISIÓ", type="primary", use_container_width=True):
    with st.spinner("Desant informe per a revisió..."):
        try:
            df_seg = normalize_columns(conn.read(worksheet="Seguiment", ttl=0)).dropna(how="all")
        except Exception:
            df_seg = pd.DataFrame(columns=["Fecha","Hora","Equipo","Miembros","Proyecto","Trabajo"] +
                                  [f"Dato{i}" for i in range(1,11)] + ["Comentarios","Fotos","Firmas","Estat"])

        noms_camps = [n for n, _ in camps_actius]
        row_seg = {
            "Fecha": datetime.now().strftime("%d/%m/%Y"), "Hora": datetime.now().strftime("%H:%M"),
            "Equipo": equip_actual, "Miembros": membres_equip.strip(),
            "Proyecto": obra_sel, "Trabajo": tipus_sel, "Comentarios": comentaris,
            "Fotos": len(st.session_state.fotos_acumulades),
            "Firmas": ("Resp" if st.session_state.firma_resp_bytes else "") + (" · Cli" if st.session_state.firma_cli_bytes else ""),
            "Estat": "PENDENT REVISIÓ"
        }
        for i in range(10):
            nom = noms_camps[i] if i < len(noms_camps) else ""
            row_seg[f"Dato{i+1}"] = valors_raw.get(nom, "") if nom else ""
        try:
            conn.update(worksheet="Seguiment", data=pd.concat([df_seg, pd.DataFrame([row_seg])], ignore_index=True))
        except Exception as e:
            st.warning(f"Error actualitzant Seguiment: {e}")

        destinataris_proj = [e.strip() for e in str(dades_p.get(col_emails, "")).split(",") if e.strip()]
        bid = save_borrany(
            equip=equip_actual,
            membres=membres_equip.strip(),
            obra=obra_sel,
            tipus=tipus_sel,
            comentaris=comentaris,
            camps_actius=camps_actius,
            valors_raw=valors_raw,
            fotos_acumulades=st.session_state.fotos_acumulades,
            firma_resp_bytes=st.session_state.firma_resp_bytes,
            firma_cli_bytes=st.session_state.firma_cli_bytes,
            destinataris=destinataris_proj
        )

        if bid:
            st.markdown("""
            <div class="success-box">
                <div>
                    <h4>✅ Informe enviat a revisió</h4>
                    <p>El responsable d'àrea revisarà el contingut i l'enviarà al client quan l'aprovi.<br>
                    Pots tancar l'aplicació, el teu informe ja està desat.</p>
                </div>
            </div>""", unsafe_allow_html=True)
            st.session_state.fotos_acumulades = []
            st.session_state.firma_resp_bytes = None
            st.session_state.firma_cli_bytes  = None
            st.rerun()
