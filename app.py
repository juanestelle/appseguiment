import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
import smtplib
import base64
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓ
# ==========================================
st.set_page_config(
    page_title="Estellé Parquet · Seguiment",
    page_icon="📋",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ==========================================
# 2. ESTILS — Disseny Tècnic Professional
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@300;400;500;600&family=IBM+Plex+Mono:wght@400;500&display=swap');

*, *::before, *::after { box-sizing: border-box; }

.stApp {
    background: #0D1117;
    font-family: 'IBM Plex Sans', sans-serif;
    color: #E6EDF3;
}

#MainMenu, footer, header, [data-testid="stToolbar"] { visibility: hidden; }
.block-container { padding: 1.5rem 1rem 4rem; max-width: 700px; }

.app-header {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 20px 24px;
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    margin-bottom: 20px;
}
.app-header-text h1 {
    font-size: 1.15rem;
    font-weight: 600;
    color: #E6EDF3;
    margin: 0;
    letter-spacing: 0.01em;
}
.app-header-text p {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: #8B949E;
    margin: 2px 0 0;
    letter-spacing: 0.05em;
}

.equip-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: rgba(31,111,235,0.1);
    border: 1px solid rgba(31,111,235,0.3);
    color: #58A6FF;
    padding: 4px 12px;
    border-radius: 20px;
    font-size: 0.75rem;
    font-family: 'IBM Plex Mono', monospace;
    font-weight: 500;
    letter-spacing: 0.05em;
}

.section {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 10px;
    padding: 20px 22px;
    margin-bottom: 14px;
}
.section-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid #21262D;
}
.section-title {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    font-weight: 500;
    color: #8B949E;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    margin: 0;
}
.section-dot { width: 6px; height: 6px; border-radius: 50%; background: #238636; flex-shrink: 0; }
.section-dot.blue { background: #1F6FEB; }
.section-dot.amber { background: #D29922; }

.stSelectbox label, .stNumberInput label,
.stTextInput label, .stTextArea label,
.stFileUploader label, .stCameraInput label {
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.75rem !important;
    font-weight: 500 !important;
    color: #8B949E !important;
    letter-spacing: 0.04em !important;
    text-transform: uppercase !important;
    margin-bottom: 4px !important;
}

.stSelectbox > div > div,
.stTextInput > div > div > input,
.stTextArea > div > div > textarea {
    background: #0D1117 !important;
    border: 1px solid #30363D !important;
    border-radius: 6px !important;
    color: #E6EDF3 !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.9rem !important;
}
.stNumberInput > div > div > input {
    background: #0D1117 !important;
    border: 1px solid #30363D !important;
    border-radius: 6px !important;
    color: #E6EDF3 !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 1rem !important;
    font-weight: 500 !important;
}

.stFormSubmitButton > button, .stButton > button {
    background: #238636 !important;
    color: #FFFFFF !important;
    border: 1px solid #2EA043 !important;
    border-radius: 6px !important;
    padding: 0.6rem 1.5rem !important;
    font-family: 'IBM Plex Sans', sans-serif !important;
    font-size: 0.85rem !important;
    font-weight: 500 !important;
    width: 100% !important;
    margin-top: 8px !important;
}

.login-wrap {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 4rem 1rem;
}
.login-card {
    background: #161B22;
    border: 1px solid #30363D;
    border-radius: 12px;
    padding: 2.5rem 2rem;
    width: 100%;
    max-width: 340px;
    text-align: center;
}
.login-card h2 { font-size: 1.2rem; font-weight: 600; color: #E6EDF3; margin: 0 0 4px; }
.login-card p { font-size: 0.7rem; color: #8B949E; margin: 0 0 1.5rem; font-family: 'IBM Plex Mono', monospace; letter-spacing: 1px; }

.success-banner {
    background: rgba(35,134,54,0.1);
    border: 1px solid #238636;
    border-radius: 8px;
    padding: 16px 20px;
    display: flex;
    align-items: flex-start;
    gap: 12px;
    margin-top: 12px;
}
.success-banner .icon { font-size: 1.1rem; flex-shrink: 0; margin-top: 2px; }
.success-banner h4 { margin: 0 0 4px; font-size: 0.9rem; color: #3FB950; font-weight: 600; }
.success-banner p  { margin: 0; font-size: 0.75rem; color: #8B949E; font-family: 'IBM Plex Mono', monospace; }

.data-badge {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: #8B949E;
    background: #0D1117;
    border: 1px solid #21262D;
    border-radius: 4px;
    padding: 3px 8px;
    display: inline-block;
    margin-bottom: 14px;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. CONNEXIÓ
# ==========================================
conn = st.connection("gsheets", type=GSheetsConnection)

try:
    df_projectes = conn.read(worksheet="Projectes", ttl=0).dropna(subset=['Nom'])
    df_templates = conn.read(worksheet="Config_Templates", ttl=0).dropna(subset=['Tipus'])
    df_equips    = conn.read(worksheet="Equips", ttl=0).dropna(subset=['Equip'])
except Exception as e:
    st.error("No s'ha pogut connectar amb Google Sheets")
    with st.expander("Detall de l'error"):
        st.code(str(e))
    st.stop()

# ==========================================
# 4. AUTENTICACIÓ PER PIN
# ==========================================
if 'equip_autenticat' not in st.session_state:
    st.session_state.equip_autenticat = None

if st.session_state.equip_autenticat is None:
    st.markdown('<div class="login-wrap">', unsafe_allow_html=True)
    st.markdown("""
    <div class="login-card">
        <h2>Estellé Parquet</h2>
        <p>SISTEMA DE SEGUIMENT D'OBRA</p>
    </div>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        pin_input = st.text_input("PIN d'equip", type="password", placeholder="····")
        login_btn = st.form_submit_button("Accedir")

    if login_btn:
        pin_match = df_equips[df_equips['PIN'].astype(str).str.strip() == pin_input.strip()]
        if not pin_match.empty:
            st.session_state.equip_autenticat = pin_match.iloc[0]['Equip']
            st.rerun()
        else:
            st.error("PIN incorrecte. Consulta el teu responsable.")
    st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

equip_actual = st.session_state.equip_autenticat

# ==========================================
# 5. FILTRAR PROJECTES PER EQUIP
# ==========================================
if 'Equip' in df_projectes.columns:
    df_proj = df_projectes[
        (df_projectes['Equip'].isna()) |
        (df_projectes['Equip'].astype(str).str.strip() == '') |
        (df_projectes['Equip'].astype(str).str.strip() == equip_actual)
    ]
else:
    df_proj = df_projectes

if df_proj.empty:
    st.warning("No hi ha projectes assignats a aquest equip.")
    st.stop()

# ==========================================
# 6. CAPÇALERA
# ==========================================
st.markdown(f"""
<div class="app-header">
    <div class="app-header-text">
        <h1>Estellé Parquet</h1>
        <p>SEGUIMENT D'OBRA · {equip_actual.upper()}</p>
    </div>
</div>
""", unsafe_allow_html=True)

col_eq, col_out = st.columns([4, 1])
with col_eq:
    st.markdown(f'<div class="equip-badge">⬡ {equip_actual}</div>', unsafe_allow_html=True)
with col_out:
    if st.button("Sortir"):
        st.session_state.equip_autenticat = None
        st.rerun()

st.markdown(f'<div class="data-badge">{datetime.now().strftime("%d/%m/%Y · %H:%M")}</div>', unsafe_allow_html=True)

# ==========================================
# 7. SELECCIÓ
# ==========================================
st.markdown('<div class="section"><div class="section-header"><div class="section-dot blue"></div><p class="section-title">Assignació</p></div>', unsafe_allow_html=True)

col1, col2 = st.columns(2)
with col1:
    obra_sel = st.selectbox("Projecte", df_proj['Nom'].unique())
    dades_p  = df_proj[df_proj['Nom'] == obra_sel].iloc[0]
with col2:
    tipus_sel = st.selectbox("Tipus de treball", df_templates['Tipus'].unique())
    dades_t   = df_templates[df_templates['Tipus'] == tipus_sel].iloc[0]

# Logo del client
logo_url = str(dades_p.get('Logo_client', '')).strip()
if logo_url.startswith('http'):
    st.markdown(f"""
    <div style="margin-top:12px;padding:10px 14px;background:#0D1117;border:1px solid #21262D;
                border-radius:8px;display:flex;align-items:center;gap:12px">
        <img src="{logo_url}" style="height:30px;width:auto;object-fit:contain">
        <span style="font-size:0.75rem;color:#8B949E;font-family:'IBM Plex Mono',monospace">{obra_sel}</span>
    </div>
    """, unsafe_allow_html=True)

st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 8. FORMULARI
# ==========================================
st.markdown('<div class="section"><div class="section-header"><div class="section-dot amber"></div><p class="section-title">Dades de la jornada</p></div>', unsafe_allow_html=True)

with st.form("form_obra", clear_on_submit=True):

    camps_actius = []
    for ck in ['Camp1', 'Camp2', 'Camp3']:
        v = dades_t.get(ck, "")
        if pd.notna(v) and str(v).strip():
            camps_actius.append(str(v))

    valors = [0.0, 0.0, 0.0]
    if camps_actius:
        cols_n = st.columns(len(camps_actius))
        for idx, nom in enumerate(camps_actius):
            with cols_n[idx]:
                valors[idx] = st.number_input(nom, min_value=0.0, step=0.1, format="%.2f")

    v1, v2, v3 = valors

    comentaris = st.text_area("Observacions", placeholder="Treball realitzat, incidències, material...", height=85)
    operari    = st.text_input("Operari responsable", value="Luis")

    st.markdown("<div style='margin-top:6px'></div>", unsafe_allow_html=True)

    tab_cam, tab_gal = st.tabs(["📷  Càmera", "🖼  Galeria"])
    with tab_cam:
        foto_camera = st.camera_input("Fer foto", label_visibility="collapsed")
    with tab_gal:
        fotos_fitxer = st.file_uploader(
            "Selecciona imatges",
            type=["jpg", "jpeg", "png", "webp"],
            accept_multiple_files=True,
            label_visibility="collapsed"
        )

    subm = st.form_submit_button("▶  Enviar informe")

st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 9. ENVIAMENT
# ==========================================
if subm:
    if not operari.strip():
        st.warning("Cal indicar l'operari responsable.")
        st.stop()

    totes_fotos = []
    if foto_camera:
        totes_fotos.append(("foto_camera.jpg", foto_camera.getvalue(), "image/jpeg"))
    if fotos_fitxer:
        for f in fotos_fitxer:
            totes_fotos.append((f.name, f.getvalue(), f.type))

    with st.spinner("Enviant informe..."):
        errors = []

        # A. Sheets
        try:
            try:
                df_seg = conn.read(worksheet="Seguiment", ttl=0).dropna(how='all')
            except Exception:
                df_seg = pd.DataFrame(columns=[
                    "Data","Hora","Equip","Projecte","Tipus",
                    "Dada1","Dada2","Dada3","Comentaris","Operari","Fotos"
                ])

            nova = pd.DataFrame([{
                "Data": datetime.now().strftime("%d/%m/%Y"),
                "Hora": datetime.now().strftime("%H:%M"),
                "Equip": equip_actual,
                "Projecte": obra_sel,
                "Tipus": tipus_sel,
                "Dada1": v1, "Dada2": v2, "Dada3": v3,
                "Comentaris": comentaris,
                "Operari": operari,
                "Fotos": len(totes_fotos)
            }])
            conn.update(worksheet="Seguiment", data=pd.concat([df_seg, nova], ignore_index=True))
        except Exception as e:
            errors.append(f"Sheets: {e}")

        # B. Email
        try:
            smtp_cfg    = st.secrets["smtp"]
            emails_raw  = str(dades_p.get('Emails_Contacte', ''))
            destinataris = [e.strip() for e in emails_raw.split(',') if e.strip()]

            if destinataris:
                msg = MIMEMultipart('mixed')
                msg['Subject'] = f"[Seguiment] {obra_sel} · {tipus_sel} · {datetime.now().strftime('%d/%m/%Y')}"
                msg['From']    = f"Estellé Parquet <{smtp_cfg['user']}>"
                msg['To']      = ", ".join(destinataris)

                files_m = ""
                for idx, nom in enumerate(camps_actius):
                    files_m += f"""<tr>
                        <td style="padding:8px 16px;border-bottom:1px solid #21262D;color:#8B949E;font-size:12px;font-family:monospace">{nom}</td>
                        <td style="padding:8px 16px;border-bottom:1px solid #21262D;color:#E6EDF3;font-size:14px;font-family:monospace;font-weight:600;text-align:right">{[v1,v2,v3][idx]}</td>
                    </tr>"""

                logo_h = f'<img src="{logo_url}" style="height:26px;width:auto;margin-bottom:4px"><br>' if logo_url.startswith('http') else ''
                obs_h  = f'<tr><td colspan="2" style="padding:14px 16px"><div style="background:#161B22;border-left:3px solid #238636;padding:10px 12px;border-radius:0 6px 6px 0;color:#C9D1D9;font-size:13px;line-height:1.6">{comentaris}</div></td></tr>' if comentaris.strip() else ''
                foto_h = f'<tr><td colspan="2" style="padding:10px 16px;color:#58A6FF;font-size:12px;font-family:monospace">📎 {len(totes_fotos)} imatge(s) adjuntada(s)</td></tr>' if totes_fotos else ''

                html = f"""<!DOCTYPE html><html><body style="margin:0;padding:0;background:#0D1117;font-family:'Helvetica Neue',sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0D1117;padding:24px 0"><tr><td align="center">
<table width="540" cellpadding="0" cellspacing="0" style="background:#161B22;border:1px solid #30363D;border-radius:10px;overflow:hidden">
<tr><td style="padding:20px 16px;border-bottom:1px solid #21262D">
    {logo_h}
    <table width="100%"><tr>
        <td><div style="font-size:15px;font-weight:600;color:#E6EDF3">Informe de Seguiment</div>
            <div style="font-size:11px;color:#8B949E;font-family:monospace;margin-top:2px">{obra_sel.upper()} · {tipus_sel.upper()}</div></td>
        <td style="text-align:right"><div style="font-size:11px;color:#8B949E;font-family:monospace">{datetime.now().strftime('%d/%m/%Y · %H:%M')}</div></td>
    </tr></table>
</td></tr>
<tr><td><table width="100%">
<tr>
    <td width="50%" style="padding:12px 16px;border-right:1px solid #21262D;border-bottom:1px solid #21262D">
        <div style="font-size:9px;color:#8B949E;letter-spacing:2px;text-transform:uppercase;font-family:monospace;margin-bottom:3px">Equip</div>
        <div style="font-size:14px;color:#E6EDF3;font-weight:500">{equip_actual}</div>
    </td>
    <td width="50%" style="padding:12px 16px;border-bottom:1px solid #21262D">
        <div style="font-size:9px;color:#8B949E;letter-spacing:2px;text-transform:uppercase;font-family:monospace;margin-bottom:3px">Operari</div>
        <div style="font-size:14px;color:#E6EDF3;font-weight:500">{operari}</div>
    </td>
</tr>
{files_m}
{obs_h}
{foto_h}
</table></td></tr>
<tr><td style="padding:12px 16px;border-top:1px solid #21262D;text-align:center">
    <div style="font-size:9px;color:#484F58;font-family:monospace;letter-spacing:1px">ESTELLÉ PARQUET · SISTEMA AUTOMATITZAT DE SEGUIMENT</div>
</td></tr>
</table></td></tr></table></body></html>"""

                msg.attach(MIMEText(html, 'html'))

                for nom_f, contingut, mime_type in totes_fotos:
                    parts = mime_type.split('/')
                    adjunt = MIMEBase(parts[0], parts[1] if len(parts) > 1 else 'octet-stream')
                    adjunt.set_payload(contingut)
                    encoders.encode_base64(adjunt)
                    adjunt.add_header('Content-Disposition', 'attachment', filename=nom_f)
                    msg.attach(adjunt)

                with smtplib.SMTP(smtp_cfg['server'], smtp_cfg['port']) as s:
                    s.starttls()
                    s.login(smtp_cfg['user'], smtp_cfg['password'])
                    s.sendmail(smtp_cfg['user'], destinataris, msg.as_string())

        except Exception as e:
            errors.append(f"Email: {e}")

    # Resultat
    if not errors:
        fotos_txt = f"{len(totes_fotos)} foto(s) adjuntada(s)" if totes_fotos else "Sense fotografies"
        st.markdown(f"""
        <div class="success-banner">
            <div class="icon">✔</div>
            <div>
                <h4>Informe registrat correctament</h4>
                <p>{obra_sel} · {tipus_sel} · {datetime.now().strftime('%d/%m/%Y %H:%M')} · {fotos_txt}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)
    else:
        for err in errors:
            st.error(err)
