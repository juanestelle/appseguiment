import smtplib
import urllib.request
import ssl
import base64
import re
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
from streamlit_gsheets import GSheetsConnection
from streamlit_drawable_canvas import st_canvas

# ==========================================
# CONFIGURACIÓ
# ==========================================
SHEETS_TTL_SECONDS = 60

st.set_page_config(page_title="Estellé Parquet · Seguimiento", page_icon="🪵", layout="centered")

# Placeholder per al logo — es renderitza a dalt de tot
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
.foto-count { font-size:0.75rem; color:var(--accent); margin-top:6px; font-weight:500; }
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
        fons = Image.new("RGB", img.size, (255, 249, 229))  # #fff9e5
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

def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [str(c).strip() for c in df.columns]
    return df

def pick_col(df: pd.DataFrame, options: list) -> Optional[str]:
    cols_l = {c.lower(): c for c in df.columns}
    for opt in options:
        if opt.lower() in cols_l: return cols_l[opt.lower()]
    return None

# FUNCIÓ PER ORDENAR AMB ELEMENTS AL FINAL
def sort_with_tail(items_list):
    """Ordena una llista posant 'Visita técnica', 'Reparaciones' i 'Final de obra' al final."""
    tail_items = ["Visita técnica", "Reparaciones", "Final de obra"]
    # Netegem de duplicats i valors buits
    clean_list = list(set([str(x).strip() for x in items_list if pd.notna(x) and str(x).strip()]))
    
    # Separem els que han d'anar al final
    main = sorted([x for x in clean_list if x not in tail_items])
    tail = [x for x in tail_items if x in clean_list]
    
    return main + tail

# ==========================================
# CONNEXIÓ SHEETS
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)
try:
    df_projectes = normalize_columns(conn.read(worksheet="Projectes",       ttl=SHEETS_TTL_SECONDS))
    df_templates = normalize_columns(conn.read(worksheet="Config_Templates", ttl=SHEETS_TTL_SECONDS))
    df_equips    = normalize_columns(conn.read(worksheet="Equips",            ttl=SHEETS_TTL_SECONDS))
except Exception as e:
    st.error("Error de conexión con Google Sheets.")
    st.stop()

col_nom         = pick_col(df_projectes, ["Nom","Nombre","Projecte","Proyecto"])
col_logo        = pick_col(df_projectes, ["Logo_Client","Logo_client","Logo","LogoClient"])
col_emails      = pick_col(df_projectes, ["Emails_Contacte","Emails_contacte","Emails","Email"])
col_equip_proj  = pick_col(df_projectes, ["Equip","Equipo"])
col_treball_def = pick_col(df_projectes, ["Treball_Predeterminat", "Treball_Prioritari", "Trabajo_Prioritario", "Tipo_Defecto"])

col_tipus      = pick_col(df_templates, ["Tipus","Tipo"])
CAMPS_COLS = [pick_col(df_templates, [f"Camp{i}"]) for i in range(1, 11)]

col_equip_eq   = pick_col(df_equips,    ["Equip","Equipo"])
col_pin        = pick_col(df_equips,    ["PIN","Pin","pin"])

if not all([col_nom, col_tipus, col_equip_eq, col_pin]):
    st.error("Falten columnes obligatòries a Sheets.")
    st.stop()

df_projectes = df_projectes[df_projectes[col_nom].notna()].copy()
df_projectes[col_nom] = df_projectes[col_nom].astype(str).str.strip()
df_templates = df_templates[df_templates[col_tipus].notna()].copy()
df_templates[col_tipus] = df_templates[col_tipus].astype(str).str.strip()

# ==========================================
# LOGIN
# ==========================================
if "auth_user" not in st.session_state:
    st.markdown("""<div class="team-header"><h1>Estellé Parquet</h1><p>Acceso Instaladores</p></div>""", unsafe_allow_html=True)
    with st.form("login"):
        pin_in = st.text_input("PIN de Equipo", type="password", placeholder="····")
        if st.form_submit_button("ENTRAR"):
            match = df_equips[df_equips[col_pin].apply(norm_pin) == norm_pin(pin_in)]
            if not match.empty:
                st.session_state.auth_user = str(match.iloc[0][col_equip_eq]).strip()
                st.session_state.fotos_acumulades = []; st.session_state.camara_activa = False
                st.session_state.firma_resp_bytes = None; st.session_state.firma_cli_bytes = None
                st.rerun()
            else: st.error("PIN incorrecto.")
    st.stop()

equip_actual = str(st.session_state.auth_user).strip()

# ==========================================
# FILTRAR PROJECTES
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

# ==========================================
# CAPÇALERA
# ==========================================
col_hd, col_out = st.columns([5, 1])
with col_hd:
    st.markdown(f"""<div class="team-header"><p>{datetime.now().strftime("%d · %m · %Y")}</p><h1>{equip_actual}</h1></div>""", unsafe_allow_html=True)
with col_out:
    st.markdown("<div style='margin-top:22px'>", unsafe_allow_html=True)
    if st.button("Salir"):
        for k in ["auth_user","fotos_acumulades","camara_activa","firma_resp_bytes","firma_cli_bytes"]: st.session_state.pop(k, None)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# SELECCIÓ PROJECTE I TREBALL (AMB ORDRE PERSONALITZAT)
# ==========================================
col_a, col_b = st.columns(2)

# Llistes amb la lògica de "cúa" (tail) aplicada
llista_projectes = sort_with_tail(df_proj[col_nom].tolist())
llista_treballs = sort_with_tail(df_templates[col_tipus].tolist())

obra_sel = col_a.selectbox("Proyecto", llista_projectes)

# Dades del projecte seleccionat
dades_p = df_proj[df_proj[col_nom] == obra_sel].iloc[0]

# Lògica de selecció automàtica del Treball Prioritari
treball_predef = str(dades_p.get(col_treball_def, "")).strip() if col_treball_def else ""
idx_treball = 0
if treball_predef in llista_treballs:
    idx_treball = llista_treballs.index(treball_predef)

tipus_sel = col_b.selectbox("Trabajo realizado", llista_treballs, index=idx_treball)

membres_equip = st.text_input("Otros miembros del equipo en obra (opcional)", placeholder="Ej: Edgar, Eric, Mario", key="membres_equip")

# Plantilla dinàmica segons el treball seleccionat
dades_t = df_templates[df_templates[col_tipus] == tipus_sel].iloc[0]

logo_url = normalize_logo_url(str(dades_p.get(col_logo, "")).strip()) if col_logo and pd.notna(dades_p.get(col_logo, "")) else ""
logo_bytes = fetch_logo_jpeg(logo_url) if logo_url else None
with logo_top.container():
    if logo_url.startswith("http"): st.image(logo_url, width=320)
    elif logo_bytes: st.image(logo_bytes, width=320)

# ==========================================
# DINÀMIC: CAMPS CONFIG_TEMPLATES (1-10)
# ==========================================
st.markdown('<span class="label-up">Medidas y avance</span>', unsafe_allow_html=True)

camps_actius = []
for i, col_key in enumerate(CAMPS_COLS, 1):
    if col_key and pd.notna(dades_t.get(col_key, "")) and str(dades_t.get(col_key, "")).strip():
        nom_camp = str(dades_t.get(col_key)).strip()
        tipus = "num" if i <= 4 else "txt"
        camps_actius.append((nom_camp, tipus))

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

# ==========================================
# FOTOS I FIRMES
# ==========================================
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
    for n_f, c_f, _ in st.session_state.fotos_acumulades: t_html += f'<img src="data:image/jpeg;base64,{img_to_thumb_b64(c_f)}">'
    st.markdown(t_html+'</div>', unsafe_allow_html=True)
    if st.button("🗑 Borrar todas las fotos"): st.session_state.fotos_acumulades = []; st.rerun()
st.markdown("</div>", unsafe_allow_html=True)

st.markdown('<div class="panel"><span class="label-up">Firmas</span>', unsafe_allow_html=True)
cf1, cf2 = st.columns(2)
with cf1:
    st.caption("Responsable")
    cv_r = st_canvas(stroke_width=2, stroke_color="#1a1a1a", background_color="#fafafa", height=140, key="cv_r", display_toolbar=False)
    if st.button("💾 Guardar responsable"): st.session_state.firma_resp_bytes = canvas_to_bytes(cv_r); st.rerun()
    if st.session_state.firma_resp_bytes: st.markdown('<div class="firma-ok">✔ Firma lista</div>', unsafe_allow_html=True)
with cf2:
    st.caption("Cliente")
    cv_c = st_canvas(stroke_width=2, stroke_color="#1a1a1a", background_color="#fafafa", height=140, key="cv_c", display_toolbar=False)
    if st.button("💾 Guardar cliente"): st.session_state.firma_cli_bytes = canvas_to_bytes(cv_c); st.rerun()
    if st.session_state.firma_cli_bytes: st.markdown('<div class="firma-ok">✔ Firma lista</div>', unsafe_allow_html=True)
st.markdown("</div>", unsafe_allow_html=True)

# ==========================================
# ENVIAMENT FINAL
# ==========================================
if st.button("▶ FINALIZAR Y ENVIAR INFORME", type="primary", use_container_width=True):
    with st.spinner("Enviando..."):
        try:
            df_seg = normalize_columns(conn.read(worksheet="Seguiment", ttl=0)).dropna(how="all")
        except:
            df_seg = pd.DataFrame(columns=["Fecha","Hora","Equipo","Miembros","Proyecto","Trabajo"] + [f"Dato{i}" for i in range(1,11)] + ["Comentarios","Fotos","Firmas"])
        
        noms_camps = [n for n, _ in camps_actius]
        row = {
            "Fecha": datetime.now().strftime("%d/%m/%Y"), "Hora": datetime.now().strftime("%H:%M"),
            "Equipo": equip_actual, "Miembros": membres_equip.strip(),
            "Proyecto": obra_sel, "Trabajo": tipus_sel,
            "Comentarios": comentaris, "Fotos": len(st.session_state.fotos_acumulades),
            "Firmas": ("Resp" if st.session_state.firma_resp_bytes else "") + (" · Cli" if st.session_state.firma_cli_bytes else "")
        }
        for i in range(10):
            nom = noms_camps[i] if i < len(noms_camps) else ""
            row[f"Dato{i+1}"] = valors_raw.get(nom, "") if nom else ""
        
        try:
            conn.update(worksheet="Seguiment", data=pd.concat([df_seg, pd.DataFrame([row])], ignore_index=True))
        except Exception as e:
            st.error(f"Error actualizando Sheets: {e}")

        # Lògica Email
        try:
            smtp_cfg = st.secrets["smtp"]
            destinataris = [e.strip() for e in str(dades_p.get(col_emails, "")).split(",") if e.strip()]
            if destinataris:
                msg = MIMEMultipart("mixed")
                msg["Subject"]  = f"Seguimiento del proyecto {obra_sel} - Estellé parquet"
                msg["From"]     = "Estellé Parquet <noreply@estelleparquet.com>"
                msg["Reply-To"] = smtp_cfg["user"]
                msg["To"]       = ", ".join(destinataris)
                logo_cid = "logo_client_estelle"

                treballs_html = ""
                for nom, tipus in camps_actius:
                    val = valors_raw.get(nom, "").strip()
                    if not val or val == "0" or val == "0.0": continue
                    if tipus == "num":
                        vf = fmt_valor(to_float_or_zero(val))
                        treballs_html += f'<tr><td align="right" style="padding:5px 10px 5px 0;font-size:22px;font-weight:700;color:#555;font-family:Montserrat,sans-serif;white-space:nowrap">{vf}</td><td align="left" style="padding:5px 0;font-size:17px;color:#888;font-family:Montserrat,sans-serif">{nom}</td></tr>'
                    else:
                        treballs_html += f'<tr><td colspan="2" style="padding:5px 0;font-size:15px;font-family:Montserrat,sans-serif"><span style="color:#7747ff;font-weight:600">{nom}:</span> <span style="color:#555;margin-left:6px">{val}</span></td></tr>'

                obs_html = f'<tr><td colspan="2" style="padding-top:18px"><p style="margin:0 0 4px;color:#421cad;font-size:13px;font-weight:700;font-family:Montserrat,sans-serif;text-transform:uppercase;letter-spacing:1px">Comentarios de la jornada</p><p style="margin:0;color:#6b5ea8;font-size:15px;line-height:1.6;font-family:Montserrat,sans-serif">{comentaris}</p></td></tr>' if comentaris.strip() else ""

                adj_parts = []
                if st.session_state.fotos_acumulades: adj_parts.append(f"{len(st.session_state.fotos_acumulades)} foto(s)")
                if st.session_state.firma_resp_bytes: adj_parts.append("firma responsable")
                if st.session_state.firma_cli_bytes:  adj_parts.append("firma cliente")
                adj_html = (f'<tr><td colspan="2" style="padding-top:14px;font-size:12px;color:#aaa;font-family:Montserrat,sans-serif">📎 Adjuntos: {", ".join(adj_parts)}</td></tr>' if adj_parts else "")

                logo_html = f'<img src="cid:{logo_cid}" width="225" style="display:block;margin:0 auto;max-width:225px;border:0">' if logo_bytes else (f'<img src="{logo_url}" width="225" style="display:block;margin:0 auto;max-width:225px;border:0">' if logo_url.startswith("http") else "")

                def f_td(lbl, has, fn):
                    return f'<td width="50%" style="padding:25px;vertical-align:top"><p style="margin:0;font-family:Montserrat,sans-serif;font-size:16px;color:#101112">📎 {lbl}</p><p style="margin:4px 0 0;font-family:Montserrat,sans-serif;font-size:12px;color:#aaa">{fn}</p></td>' if has else ""

                f_row = f'<tr><td style="padding:0 30px"><hr style="border:none;border-top:1px solid #e8e0d0;margin:0"></td></tr><tr><td style="padding:10px 0"><table width="100%"><tr>{f_td("Firma responsable", st.session_state.firma_resp_bytes is not None, "firma_responsable.jpg")}{f_td("Firma cliente", st.session_state.firma_cli_bytes is not None, "firma_cliente.jpg")}</tr></table></td></tr>' if (st.session_state.firma_resp_bytes or st.session_state.firma_cli_bytes) else ""

                eq_html = f'<table width="60%" align="center" style="margin-top:16px;"><tr><td style="border-top:1px solid #e8e0d0; padding-top:16px;" align="center"><p style="margin:0;font-size:14px;color:#aaa;font-weight:600;font-family:Montserrat,sans-serif">Equipo</p><p style="margin:0;font-size:18px;font-weight:600;color:#8125bb;font-family:Montserrat,sans-serif">{membres_equip.strip()}</p></td></tr></table>' if membres_equip.strip() else ""

                html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#fefdf1">
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

                body_related = MIMEMultipart("related")
                body_alt = MIMEMultipart("alternative")
                body_alt.attach(MIMEText(html, "html"))
                body_related.attach(body_alt)

                if logo_bytes:
                    img_logo = MIMEImage(logo_bytes, _subtype="jpeg")
                    img_logo.add_header("Content-ID", f"<{logo_cid}>")
                    body_related.attach(img_logo)
                msg.attach(body_related)

                for n_f, cont, mime in list(st.session_state.fotos_acumulades) + ([(f"firma_responsable.jpg", st.session_state.firma_resp_bytes, "image/jpeg")] if st.session_state.firma_resp_bytes else []) + ([(f"firma_cliente.jpg", st.session_state.firma_cli_bytes, "image/jpeg")] if st.session_state.firma_cli_bytes else []):
                    adj = MIMEBase(*(mime.split("/")))
                    adj.set_payload(cont); encoders.encode_base64(adj)
                    adj.add_header("Content-Disposition", "attachment", filename=n_f); msg.attach(adj)

                with smtplib.SMTP(smtp_cfg["server"], smtp_cfg["port"]) as s:
                    s.starttls(); s.login(smtp_cfg["user"], smtp_cfg["password"])
                    s.sendmail(smtp_cfg["user"], destinataris, msg.as_string())

                st.markdown('<div class="success-box"><h4>✔ Informe enviado correctamente</h4></div>', unsafe_allow_html=True)
                st.session_state.fotos_acumulades = []; st.session_state.firma_resp_bytes = None; st.session_state.firma_cli_bytes = None

        except Exception as e: st.error(f"Error Email: {e}")
