import smtplib
import urllib.request
import ssl
import base64
import re
from datetime import datetime
from io import BytesIO
from typing import Tuple, Optional, List, Dict, Any
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
# CONFIGURACIÓ I CONSTANTS
# ==========================================
CONFIG = {
    "PAGE_TITLE": "Estellé Parquet · Seguimiento",
    "PAGE_ICON": "🪵",
    "LAYOUT": "centered",
    "CSS_FILE": "styles.css"
}

# Colors i estils
COLORS = {
    "wood": "#4e342e",
    "accent": "#8d6e63",
    "bg": "#fdfaf7",
    "white": "#fcfcfc",
    "border": "#e0d7d0",
    "purple": "#7747ff"
}


class EstelleParquetApp:
    """
    Aplicació principal per al seguiment de projectes d'Estellé Parquet
    """
    
    def __init__(self):
        self.setup_page()
        self.load_styles()
        self.initialize_session_state()
        
    def setup_page(self) -> None:
        """Configura la pàgina Streamlit"""
        st.set_page_config(
            page_title=CONFIG["PAGE_TITLE"],
            page_icon=CONFIG["PAGE_ICON"],
            layout=CONFIG["LAYOUT"]
        )
    
    def load_styles(self) -> None:
        """Carrega els estils CSS"""
        css_content = f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Outfit:wght@300;600&display=swap');

        :root {{
            --wood:    {COLORS['wood']};
            --accent:  {COLORS['accent']};
            --bg:      {COLORS['bg']};
            --white:   {COLORS['white']};
            --border:  {COLORS['border']};
            --purple:  {COLORS['purple']};
        }}

        .stApp {{ background: var(--bg); color: #2c2c2c; font-family: 'Inter', sans-serif; }}
        #MainMenu, footer, header {{ visibility: hidden; }}
        .stTabs [data-baseweb="tab-list"] {{ background: transparent !important; gap: 4px; }}

        .team-header {{
            background: var(--white);
            border: 1px solid #efebe9;
            padding: 20px;
            border-radius: 18px;
            text-align: center;
            margin-bottom: 16px;
            box-shadow: 0 2px 12px rgba(0,0,0,0.03);
        }}
        .team-header h1 {{
            font-family: 'Outfit', sans-serif;
            font-weight: 600;
            font-size: 1.7rem;
            color: var(--wood);
            margin: 0;
        }}
        .team-header p {{
            font-family: 'Outfit', sans-serif;
            font-weight: 300;
            color: var(--accent);
            margin: 4px 0 0;
            text-transform: uppercase;
            letter-spacing: 2px;
            font-size: 0.75rem;
        }}

        .panel {{
            background: white;
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            margin-bottom: 14px;
        }}

        .label-up {{
            font-weight: 600;
            color: var(--accent);
            font-size: 0.7rem;
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 10px;
            display: block;
        }}

        .foto-thumb-row {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            margin-top: 10px;
        }}
        .foto-thumb-row img {{
            height: 64px;
            width: 64px;
            object-fit: cover;
            border-radius: 8px;
            border: 1px solid var(--border);
        }}
        .foto-count {{
            font-size: 0.75rem;
            color: var(--accent);
            margin-top: 6px;
            font-weight: 500;
        }}

        .firma-box {{
            border: 1.5px dashed #d7ccc8;
            border-radius: 12px;
            overflow: hidden;
            background: #fafafa;
        }}

        /* Botó submit (verd) */
        .stFormSubmitButton > button {{
            background: var(--wood) !important;
            color: white !important;
            border-radius: 12px !important;
            padding: 0.85rem !important;
            font-weight: 600 !important;
            border: none !important;
            width: 100% !important;
            font-size: 0.9rem !important;
            font-family: 'Inter', sans-serif !important;
        }}

        /* Botons secundaris */
        .stButton > button {{
            background: transparent !important;
            color: var(--accent) !important;
            border: 1px solid var(--border) !important;
            border-radius: 8px !important;
            font-size: 0.78rem !important;
            padding: 0.4rem 0.9rem !important;
            width: auto !important;
            font-family: 'Inter', sans-serif !important;
        }}

        .success-box {{
            background: #f1f8f2;
            border: 1px solid #a5d6a7;
            border-radius: 12px;
            padding: 16px 20px;
            display: flex;
            gap: 12px;
            align-items: flex-start;
            margin-top: 14px;
        }}
        .success-box h4 {{ margin: 0 0 3px; color: #2e7d32; font-size: 0.9rem; }}
        .success-box p  {{ margin: 0; color: #666; font-size: 0.76rem; line-height: 1.5; }}
        </style>
        """
        st.markdown(css_content, unsafe_allow_html=True)
    
    def initialize_session_state(self) -> None:
        """Inicialitza les variables d'estat de la sessió"""
        if "auth_user" not in st.session_state:
            st.session_state.auth_user = None
        if "fotos_acumulades" not in st.session_state:
            st.session_state.fotos_acumulades = []
        if "camara_activa" not in st.session_state:
            st.session_state.camara_activa = False
    
    @staticmethod
    def normalize_pin(value: str) -> str:
        """Normalitza el PIN eliminant espais i decimals"""
        return str(value).strip().split(".")[0]
    
    @staticmethod
    def sanitize_image(name: str, content: bytes) -> Tuple[str, bytes, str]:
        """
        Sanititza i redimensiona una imatge
        
        Args:
            name: Nom de la imatge
            content: Contingut binari de la imatge
            
        Returns:
            Tuple amb (nom_modificat, contingut_procesat, tipus_mime)
        """
        try:
            img = Image.open(BytesIO(content))
            img = ImageOps.exif_transpose(img)
            img = img.convert("RGB")
            img.thumbnail((1400, 1400))
            out = BytesIO()
            img.save(out, format="JPEG", quality=85)
            return f"{name}.jpg", out.getvalue(), "image/jpeg"
        except Exception as e:
            st.error(f"Error processant la imatge: {str(e)}")
            raise
    
    @staticmethod
    def canvas_to_bytes(canvas_result) -> Optional[bytes]:
        """
        Converteix el canvas a bytes JPEG. Retorna None si està en blanc.
        
        Args:
            canvas_result: Resultat del component canvas
            
        Returns:
            Bytes de la imatge o None si està en blanc
        """
        if canvas_result is None or canvas_result.image_data is None:
            return None
        
        arr = canvas_result.image_data.astype("uint8")
        
        # Comprovació millorada per detectar si està en blanc
        if arr.std() < 1.0:  # Si gairebé no hi ha variació (imatge plana)
            return None

        img = Image.fromarray(arr, "RGBA").convert("RGB")
        out = BytesIO()
        img.save(out, format="JPEG", quality=90)
        return out.getvalue()

    @staticmethod
    def convert_gdrive_url(url: str) -> str:
        """
        Converteix URL de Google Drive a URL de descàrrega directa.
        
        Args:
            url: URL original de Google Drive
            
        Returns:
            URL de descàrrega directa
        """
        if "drive.google.com" in url:
            # Patró típic: /d/ID/...
            match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
            if match:
                file_id = match.group(1)
                return f"https://drive.google.com/uc?export=download&id={file_id}"
            # Patró alternatiu: id=ID
            match = re.search(r'id=([a-zA-Z0-9_-]+)', url)
            if match:
                file_id = match.group(1)
                return f"https://drive.google.com/uc?export=download&id={file_id}"
        return url

    @staticmethod
    @st.cache_data(ttl=3600, show_spinner=False)
    def logo_to_base64(url: str) -> Optional[str]:
        """
        Descarrega el logo, converteix a base64 i cacheja.
        
        Args:
            url: URL del logo
            
        Returns:
            Cadena base64 del logo o None si falla
        """
        if not url or not url.startswith("http"):
            return None
        
        # Convertim URL si és de Google Drive
        url_dl = EstelleParquetApp.convert_gdrive_url(url)
        
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(url_dl, headers={
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "image/webp,image/apng,image/*,*/*;q=0.8",
            })
            with urllib.request.urlopen(req, timeout=10, context=ctx) as r:
                data = r.read()
                # Si Google retorna una pàgina HTML (per permisos), no serà una imatge vàlida
                content_type = r.headers.get("Content-Type", "")
                if "image" not in content_type:
                    return None
                    
                ct = content_type.split(";")[0].strip()
            return f"data:{ct};base64,{base64.b64encode(data).decode()}"
        except Exception:
            return None

    @staticmethod
    def format_value(value) -> str:
        """Formata un valor numèric per mostrar-lo"""
        if value is None: 
            return "0"
        f_val = float(value)
        return str(int(f_val)) if f_val == int(f_val) else f"{f_val:.1f}"

    @staticmethod
    def image_to_thumbnail_b64(content: bytes) -> str:
        """Converteix una imatge a miniatura en base64"""
        img = Image.open(BytesIO(content)).convert("RGB")
        img.thumbnail((120, 120))
        out = BytesIO()
        img.save(out, format="JPEG", quality=70)
        return base64.b64encode(out.getvalue()).decode()

    def authenticate_user(self) -> bool:
        """
        Autentica l'usuari mitjançant PIN
        
        Returns:
            True si l'autenticació és correcta, False altrament
        """
        if st.session_state.auth_user:
            return True
            
        st.markdown("""
        <div class="team-header">
            <h1>Estellé Parquet</h1>
            <p>Acceso Instaladores</p>
        </div>""", unsafe_allow_html=True)

        with st.form("login"):
            pin_in = st.text_input("PIN de Equipo", type="password", placeholder="····")
            if st.form_submit_button("ENTRAR"):
                # Connexió a Google Sheets per obtenir equips
                try:
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    df_equips = conn.read(worksheet="Equips", ttl=300).dropna(subset=["Equip"])
                    
                    match = df_equips[df_equips["PIN"].apply(EstelleParquetApp.normalize_pin) == EstelleParquetApp.normalize_pin(pin_in)]
                    if not match.empty:
                        st.session_state.auth_user = match.iloc[0]["Equip"]
                        st.session_state.fotos_acumulades = []
                        st.rerun()
                    else:
                        st.error("PIN incorrecto. Consulta a tu responsable.")
                except Exception as e:
                    st.error("Error de conexión con Google Sheets.")
                    st.error(f"Detalle: {str(e)}")
        
        return False

    def get_data_sources(self) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Obté les fonts de dades de Google Sheets
        
        Returns:
            Tuple amb DataFrames de projectes, templates i equips
        """
        conn = st.connection("gsheets", type=GSheetsConnection)
        
        try:
            df_projectes = conn.read(worksheet="Projectes", ttl=300).dropna(subset=["Nom"])
            df_templates = conn.read(worksheet="Config_Templates", ttl=300).dropna(subset=["Tipus"])
            df_equips = conn.read(worksheet="Equips", ttl=300).dropna(subset=["Equip"])
            return df_projectes, df_templates, df_equips
        except Exception as e:
            st.error("Error de conexión con Google Sheets.")
            with st.expander("Detalle"):
                st.code(str(e))
            st.stop()
            return pd.DataFrame(), pd.DataFrame(), pd.DataFrame()  # Aquesta línia mai s'executarà a causa del st.stop()

    def filter_projects_for_team(self, df_projectes: pd.DataFrame, team_name: str) -> pd.DataFrame:
        """
        Filtra els projectes assignats a l'equip actual
        
        Args:
            df_projectes: DataFrame amb tots els projectes
            team_name: Nom de l'equip
            
        Returns:
            DataFrame filtrat amb projectes per a l'equip
        """
        if "Equip" in df_projectes.columns:
            df_proj = df_projectes[
                df_projectes["Equip"].isna() |
                (df_projectes["Equip"].astype(str).str.strip() == "") |
                (df_projectes["Equip"].astype(str).str.strip() == team_name)
            ]
        else:
            df_proj = df_projectes
        
        if df_proj.empty:
            st.warning("No hay proyectos asignados a este equipo.")
            st.stop()
            
        return df_proj

    def render_header(self, team_name: str) -> None:
        """Renderitza la capçalera de l'aplicació"""
        col_hd, col_out = st.columns([5, 1])
        with col_hd:
            st.markdown(f"""
            <div class="team-header">
                <p>{datetime.now().strftime("%d · %m · %Y")}</p>
                <h1>{team_name}</h1>
            </div>""", unsafe_allow_html=True)
        with col_out:
            st.markdown("<div style='margin-top:22px'>", unsafe_allow_html=True)
            if st.button("Salir"):
                del st.session_state["auth_user"]
                st.session_state.fotos_acumulades = []
                st.rerun()
            st.markdown("</div>", unsafe_allow_html=True)

    def render_main_form(self, df_templates: pd.DataFrame, dades_p: pd.Series) -> bool:
        """
        Renderitza el formulari principal
        
        Args:
            df_templates: DataFrame amb plantilles de treball
            dades_p: Dades del projecte seleccionat
            
        Returns:
            True si s'ha enviat el formulari, False altrament
        """
        # Selecció de projecte i tipus de treball
        col_a, col_b = st.columns(2)
        df_proj = self.filter_projects_for_team(
            pd.DataFrame(), st.session_state.auth_user  # Aquesta funció s'ha de cridar amb dades reals
        )  # Placeholder - caldrà refactoritzar això
        obra_sel = col_a.selectbox("Proyecto", df_proj["Nom"].unique() if not df_proj.empty else [])
        tipus_sel = col_b.selectbox("Trabajo realizado", df_templates["Tipus"].unique())
        
        # Obtenir dades del template
        dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0] if not df_templates[df_templates["Tipus"] == tipus_sel].empty else pd.Series(dtype=object)
        
        # Mostrar logo del client
        logo_url = str(dades_p.get("Logo_client", "")).strip()
        logo_b64_client = EstelleParquetApp.logo_to_base64(logo_url) if logo_url else None
        
        if logo_b64_client:
            st.markdown(f"""
            <div style="margin:8px 0 14px;display:flex;align-items:center;gap:12px">
                <img src="{logo_b64_client}" style="height:36px;width:auto;max-width:160px;object-fit:contain">
                <span style="font-size:0.85rem;font-weight:500;color:#4e342e">{obra_sel}</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="margin:8px 0 14px">
                <span style="font-size:0.9rem;font-weight:600;color:#4e342e">{obra_sel}</span>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:14px'></div>", unsafe_allow_html=True)

        # Formulari principal
        with st.form("main_form", clear_on_submit=False):
            st.markdown('<span class="label-up">Medidas y avance</span>', unsafe_allow_html=True)

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
                        valors[i] = st.number_input(nom, min_value=0.0, value=None,
                                                     step=0.5, format="%.1f", placeholder="0")
            v1 = valors[0] or 0.0
            v2 = valors[1] or 0.0
            v3 = valors[2] or 0.0

            st.markdown("<div style='margin:12px 0'></div>", unsafe_allow_html=True)
            comentaris = st.text_area("Comentarios de la jornada",
                                       placeholder="Describe detalles relevantes del trabajo...",
                                       height=90)

            enviar = st.form_submit_button("▶  FINALIZAR Y ENVIAR INFORME")
        
        return enviar

    def render_photo_section(self) -> None:
        """Renderitza la secció de fotografies"""
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<span class="label-up">Reportaje fotográfico</span>', unsafe_allow_html=True)

        tab_cam, tab_gal = st.tabs(["📷  Cámara", "🖼  Galería"])

        with tab_cam:
            if not st.session_state.camara_activa:
                if st.button("📷  Activar cámara"):
                    st.session_state.camara_activa = True
                    st.rerun()
            else:
                foto_cam = st.camera_input("Capturar foto", label_visibility="collapsed")
                col_add, col_clr = st.columns([2, 1])
                with col_add:
                    if st.button("＋ Añadir esta foto", disabled=(foto_cam is None)):
                        if foto_cam is not None:
                            n, b, m = self.sanitize_image(f"foto_{len(st.session_state.fotos_acumulades)+1:02d}", foto_cam.getvalue())
                            st.session_state.fotos_acumulades.append((n, b, m))
                            st.session_state.camara_activa = False
                            st.rerun()
                with col_clr:
                    if st.button("✕ Cerrar cámara"):
                        st.session_state.camara_activa = False
                        st.rerun()

        with tab_gal:
            fotos_gal = st.file_uploader("Seleccionar imágenes", type=["jpg","jpeg","png","webp"],
                                          accept_multiple_files=True, label_visibility="collapsed")
            if fotos_gal:
                if st.button("＋ Añadir selección a galería"):
                    for f in fotos_gal:
                        n, b, m = self.sanitize_image(f.name.rsplit(".",1)[0], f.getvalue())
                        st.session_state.fotos_acumulades.append((n, b, m))
                    st.rerun()

        # Miniatures
        if st.session_state.fotos_acumulades:
            thumbs_html = '<div class="foto-thumb-row">'
            for nom_f, cont_f, _ in st.session_state.fotos_acumulades:
                b64t = self.image_to_thumbnail_b64(cont_f)
                thumbs_html += f'<img src="data:image/jpeg;base64,{b64t}" title="{nom_f}">'
            thumbs_html += '</div>'
            thumbs_html += f'<div class="foto-count">✔ {len(st.session_state.fotos_acumulades)} foto(s) listas para enviar</div>'
            st.markdown(thumbs_html, unsafe_allow_html=True)
            if st.button("🗑 Borrar todas las fotos"):
                st.session_state.fotos_acumulades = []
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

    def render_signature_section(self) -> Tuple[Optional[bytes], Optional[bytes]]:
        """
        Renderitza la secció de signatures
        
        Returns:
            Tuple amb les firmes (responsable, client)
        """
        st.markdown('<div class="panel">', unsafe_allow_html=True)
        st.markdown('<span class="label-up">Firmas</span>', unsafe_allow_html=True)
        col_f1, col_f2 = st.columns(2)

        with col_f1:
            st.caption("Responsable de obra")
            st.markdown('<div class="firma-box">', unsafe_allow_html=True)
            canvas_resp = st_canvas(fill_color="rgba(255,255,255,0)", stroke_width=2,
                                     stroke_color="#1a1a1a", background_color="#fafafa",
                                     height=140, key="canvas_resp", update_streamlit=False,
                                     drawing_mode="freedraw", display_toolbar=False)
            st.markdown('</div>', unsafe_allow_html=True)

        with col_f2:
            st.caption("Cliente / Propietario")
            st.markdown('<div class="firma-box">', unsafe_allow_html=True)
            canvas_cli = st_canvas(fill_color="rgba(255,255,255,0)", stroke_width=2,
                                    stroke_color="#1a1a1a", background_color="#fafafa",
                                    height=140, key="canvas_cli", update_streamlit=False,
                                    drawing_mode="freedraw", display_toolbar=False)
            st.markdown('</div>', unsafe_allow_html=True)
        
        st.markdown('</div>', unsafe_allow_html=True)
        
        # Processa les firmes
        firma_resp = self.canvas_to_bytes(canvas_resp)
        firma_cli = self.canvas_to_bytes(canvas_cli)
        
        return firma_resp, firma_cli

    def send_report(self, df_projectes: pd.DataFrame, df_templates: pd.DataFrame, 
                   obra_sel: str, tipus_sel: str, v1: float, v2: float, v3: float, 
                   comentaris: str, firma_resp: Optional[bytes], firma_cli: Optional[bytes],
                   dades_p: pd.Series, logo_b64_client: Optional[str], logo_url: str) -> None:
        """
        Envia l'informe a Google Sheets i per correu
        
        Args:
            df_projectes: DataFrame amb projectes
            df_templates: DataFrame amb plantilles
            obra_sel: Projecte seleccionat
            tipus_sel: Tipus de treball seleccionat
            v1, v2, v3: Valors de mesures
            comentaris: Comentaris
            firma_resp: Imatge de la firma del responsable
            firma_cli: Imatge de la firma del client
            dades_p: Dades del projecte
            logo_b64_client: Logo del client en base64
            logo_url: URL original del logo
        """
        totes_fotos = list(st.session_state.fotos_acumulades)  # còpia

        # Afegim firmes NOMÉS si existeixen (no són None)
        if firma_resp: 
            totes_fotos.append(("firma_responsable.jpg", firma_resp, "image/jpeg"))
        if firma_cli:  
            totes_fotos.append(("firma_cliente.jpg", firma_cli, "image/jpeg"))

        with st.spinner("Enviando informe..."):
            errors = []

            # A. Actualització de Google Sheets
            try:
                conn = st.connection("gsheets", type=GSheetsConnection)
                try:
                    df_seg = conn.read(worksheet="Seguiment", ttl=0).dropna(how="all")
                except Exception:
                    df_seg = pd.DataFrame(columns=[
                        "Fecha","Hora","Equipo","Proyecto","Trabajo",
                        "Dato1","Dato2","Dato3","Comentarios","Fotos","Firmas"
                    ])
                
                # Obtenir dades del template per mostrar camps actius
                dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]
                camps_actius = []
                for field in ["Camp1", "Camp2", "Camp3"]:
                    val = dades_t.get(field, "")
                    if pd.notna(val) and str(val).strip():
                        camps_actius.append(str(val))
                
                nova = pd.DataFrame([{
                    "Fecha":       datetime.now().strftime("%d/%m/%Y"),
                    "Hora":        datetime.now().strftime("%H:%M"),
                    "Equipo":      st.session_state.auth_user,
                    "Proyecto":    obra_sel,
                    "Trabajo":     tipus_sel,
                    "Dato1":       v1, "Dato2": v2, "Dato3": v3,
                    "Comentarios": comentaris,
                    "Fotos":       len(st.session_state.fotos_acumulades),
                    "Firmas":      ("Resp" if firma_resp else "") + (" · Cliente" if firma_cli else "")
                }])
                
                conn.update(worksheet="Seguiment",
                            data=pd.concat([df_seg, nova], ignore_index=True))
            except Exception as e:
                errors.append(f"Sheets: {e}")

            # B. Enviament per correu
            try:
                smtp_cfg = st.secrets["smtp"]
                emails_raw = str(dades_p.get("Emails_Contacte", ""))
                destinataris = [e.strip() for e in emails_raw.split(",") if e.strip()]

                if destinataris:
                    msg = MIMEMultipart("mixed")
                    msg["Subject"] = f"Seguimiento del proyecto {obra_sel} - Estellé parquet"
                    msg["From"] = "Estellé Parquet <noreply@estelleparquet.com>"
                    msg["Reply-To"] = smtp_cfg["user"]
                    msg["To"] = ", ".join(destinataris)

                    # Logo: prioritat base64, sino URL original
                    logo_src_email = logo_b64_client if logo_b64_client else logo_url
                    logo_html = (f'<img src="{logo_src_email}" width="180" style="display:block;'
                                 f'margin:0 auto 8px;max-height:70px;object-fit:contain">'
                                 if logo_src_email else "")

                    # Taula de treballs
                    treballs_html = ""
                    for i, nom in enumerate(camps_actius):
                        vf = self.format_value([v1, v2, v3][i])
                        treballs_html += f"""
                        <tr>
                          <td align="right" style="padding:5px 10px 5px 0;font-size:22px;
                              font-weight:700;color:#555;font-family:Montserrat,'Trebuchet MS',sans-serif;
                              white-space:nowrap">{vf}</td>
                          <td align="left" style="padding:5px 0;font-size:17px;color:#888;
                              font-family:Montserrat,'Trebuchet MS',sans-serif">{nom}</td>
                        </tr>"""

                    obs_html = f"""
                    <tr><td colspan="2" style="padding-top:18px">
                      <p style="margin:0 0 4px;color:#421cad;font-size:13px;font-weight:700;
                         font-family:Montserrat,'Trebuchet MS',sans-serif;text-transform:uppercase;
                         letter-spacing:1px">Comentarios de la jornada</p>
                      <p style="margin:0;color:#6b5ea8;font-size:15px;line-height:1.6;
                         font-family:Montserrat,'Trebuchet MS',sans-serif">{comentaris}</p>
                    </td></tr>""" if comentaris.strip() else ""

                    adjunts_info = []
                    if st.session_state.fotos_acumulades:
                        adjunts_info.append(f"{len(st.session_state.fotos_acumulades)} foto(s)")
                    if firma_resp: adjunts_info.append("firma responsable")
                    if firma_cli:  adjunts_info.append("firma cliente")
                    
                    adjunts_html = ""
                    if adjunts_info:
                        adjunts_html = f"""
                        <tr><td colspan="2" style="padding-top:14px;font-size:12px;color:#aaa;
                            font-family:Montserrat,'Trebuchet MS',sans-serif">
                            📎 Adjuntos: {", ".join(adjunts_info)}
                        </td></tr>"""

                    html = f"""<!DOCTYPE html>
<html lang="es"><head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#fefdf1;font-family:'Trebuchet MS',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" bgcolor="#fefdf1">
<tr><td align="center" style="padding:30px 10px">
<table width="580" cellpadding="0" cellspacing="0"
       style="background:#fff9e5;border-radius:14px;overflow:hidden;
              box-shadow:0 4px 20px rgba(0,0,0,0.06)">

  <!-- LOGO -->
  <tr><td align="center" style="padding:32px 30px 16px">
    {logo_html}
  </td></tr>

  <!-- DATA -->
  <tr><td align="center" style="padding:0 30px 8px">
    <p style="margin:0;color:#7747ff;font-size:17px;
       font-family:Montserrat,'Trebuchet MS',sans-serif">
      {datetime.now().strftime("%d · %m · %Y")}
    </p>
  </td></tr>

  <tr><td style="padding:0 30px">
    <hr style="border:none;border-top:1px solid #e8e0d0;margin:0">
  </td></tr>

  <!-- PROYECTO -->
  <tr><td align="center" style="padding:22px 30px 8px">
    <p style="margin:0 0 4px;font-size:11px;color:#777;text-transform:uppercase;
       letter-spacing:2px;font-family:Montserrat,'Trebuchet MS',sans-serif">Proyecto</p>
    <p style="margin:0 0 4px;font-size:20px;font-weight:700;color:#1a1a1a;
       font-family:Montserrat,'Trebuchet MS',sans-serif">{obra_sel}</p>
    <p style="margin:0;font-size:13px;color:#888;font-style:italic;
       font-family:Montserrat,'Trebuchet MS',sans-serif">By ESTELLÉ parquet</p>
  </td></tr>

  <tr><td style="padding:14px 30px 0">
    <hr style="border:none;border-top:1px solid #e8e0d0;margin:0">
  </td></tr>

  <!-- TRABAJOS -->
  <tr><td align="center" style="padding:20px 30px 6px">
    <p style="margin:0;font-size:13px;font-weight:700;color:#7747ff;
       text-transform:uppercase;letter-spacing:3px;
       font-family:Montserrat,'Trebuchet MS',sans-serif">Trabajos</p>
  </td></tr>

  <tr><td align="center" style="padding:4px 30px 20px">
    <table cellpadding="0" cellspacing="0" align="center">
      {treballs_html}
      {obs_html}
      {adjunts_html}
    </table>
  </td></tr>

  <tr><td style="padding:0 30px">
    <hr style="border:none;border-top:1px solid #e8e0d0;margin:0">
  </td></tr>

  <!-- EQUIPO -->
  <tr><td align="center" style="padding:20px 30px">
    <p style="margin:0 0 3px;font-size:12px;color:#aaa;
       font-family:Montserrat,'Trebuchet MS',sans-serif">Equipo responsable</p>
    <p style="margin:0;font-size:20px;font-weight:700;color:#8125bb;
       font-family:Montserrat,'Trebuchet MS',sans-serif">{st.session_state.auth_user}</p>
  </td></tr>

  <!-- FOOTER -->
  <tr><td align="center"
      style="padding:16px 30px 24px;border-top:1px solid #e8e0d0">
    <a href="http://www.estelleparquet.com"
       style="color:#4e342e;font-size:13px;text-decoration:none;
              font-family:Montserrat,'Trebuchet MS',sans-serif">
       www.estelleparquet.com
    </a>
    <p style="margin:10px 0 0;font-size:11px;color:#bbb;line-height:1.6;
       font-family:Montserrat,'Trebuchet MS',sans-serif">
      Realizamos el seguimiento diario para una óptima comunicación<br>y mejora de nuestros servicios.
    </p>
  </td></tr>

</table>
</td></tr></table>
</body></html>"""

                    msg.attach(MIMEText(html, "html"))

                    # Annexem arxius (incloent firmes només si no són None)
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

        # Mostra resultats
        if not errors:
            n_fotos = len(st.session_state.fotos_acumulades)
            firmes_list = []
            if firma_resp: firmes_list.append("responsable")
            if firma_cli:  firmes_list.append("cliente")
            f_txt = " y ".join(firmes_list) if firmes_list else "sin firmas"

            st.markdown(f"""
            <div class="success-box">
                <div style="font-size:1.4rem;line-height:1">✔</div>
                <div>
                    <h4>Informe enviado correctamente</h4>
                    <p>{obra_sel} · {tipus_sel}<br>
                       {datetime.now().strftime('%d/%m/%Y · %H:%M')} · {n_fotos} foto(s) · {f_txt}</p>
                </div>
            </div>""", unsafe_allow_html=True)

            # Netejar fotos un cop enviat
            st.session_state.fotos_acumulades = []
        else:
            for err in errors:
                st.error(err)

    def run(self) -> None:
        """Executa l'aplicació principal"""
        # Autenticació
        if not self.authenticate_user():
            return
        
        # Carrega de dades
        df_projectes, df_templates, df_equips = self.get_data_sources()
        
        # Filtra projectes per equip
        df_proj_filtered = self.filter_projects_for_team(df_projectes, st.session_state.auth_user)
        
        # Capçalera
        self.render_header(st.session_state.auth_user)
        
        # Selecciona projecte i tipus
        col_a, col_b = st.columns(2)
        obra_sel = col_a.selectbox("Proyecto", df_proj_filtered["Nom"].unique())
        tipus_sel = col_b.selectbox("Trabajo realizado", df_templates["Tipus"].unique())
        
        # Obté dades del projecte i template
        dades_p = df_projectes[df_projectes["Nom"] == obra_sel].iloc[0]
        dades_t = df_templates[df_templates["Tipus"] == tipus_sel].iloc[0]
        
        # Mostra logo del client
        logo_url = str(dades_p.get("Logo_client", "")).strip()
        logo_b64_client = EstelleParquetApp.logo_to_base64(logo_url) if logo_url else None
        
        if logo_b64_client:
            st.markdown(f"""
            <div style="margin:8px 0 14px;display:flex;align-items:center;gap:12px">
                <img src="{logo_b64_client}" style="height:36px;width:auto;max-width:160px;object-fit:contain">
                <span style="font-size:0.85rem;font-weight:500;color:#4e342e">{obra_sel}</span>
            </div>""", unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div style="margin:8px 0 14px">
                <span style="font-size:0.9rem;font-weight:600;color:#4e342e">{obra_sel}</span>
            </div>""", unsafe_allow_html=True)

        st.markdown("<div style='margin-bottom:14px'></div>", unsafe_allow_html=True)
        
        # Formulari principal
        with st.form("main_form", clear_on_submit=False):
            st.markdown('<span class="label-up">Medidas y avance</span>', unsafe_allow_html=True)

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
                        valors[i] = st.number_input(nom, min_value=0.0, value=None,
                                                     step=0.5, format="%.1f", placeholder="0")
            v1 = valors[0] or 0.0
            v2 = valors[1] or 0.0
            v3 = valors[2] or 0.0

            st.markdown("<div style='margin:12px 0'></div>", unsafe_allow_html=True)
            comentaris = st.text_area("Comentarios de la jornada",
                                       placeholder="Describe detalles relevantes del trabajo...",
                                       height=90)

            enviar = st.form_submit_button("▶  FINALIZAR Y ENVIAR INFORME")
        
        # Secció de fotografies (fora del form per acumular)
        self.render_photo_section()
        
        # Secció de signatures (fora del form)
        firma_resp, firma_cli = self.render_signature_section()
        
        # Processament de l'enviament
        if enviar:
            self.send_report(df_projectes, df_templates, obra_sel, tipus_sel, 
                           v1, v2, v3, comentaris, firma_resp, firma_cli,
                           dades_p, logo_b64_client, logo_url)


def main():
    """Punt d'entrada principal de l'aplicació"""
    app = EstelleParquetApp()
    app.run()


if __name__ == "__main__":
    main()