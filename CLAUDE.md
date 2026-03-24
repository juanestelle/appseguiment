# App Seguiment — Context per a Claude

## Arquitectura

- **Stack:** Streamlit (Python) + Google Sheets com a base de dades
- **GitHub:** https://github.com/juanestelle/appseguiment
- **Desplegat a:** Streamlit Cloud
- **Full de càlcul:** `17vINdoX_lvj7Yq89J3SKHU6ISHoGQHYiA_9vtBTKJEA`

## Projecte relacionat

El **CRM Mundoparquet** (`https://github.com/juanestelle/mundoparquet-crm`) alimenta automàticament la pestanya "Projectes" d'aquesta fulla quan un lead passa a fase "Guanyat".

---

## Pestanyes Google Sheets

| Pestanya | Descripció |
|----------|-----------|
| `Projectes` | Llista de projectes actius. Alimentada automàticament pel CRM. |
| `Config_Templates` | Plantilles de camps per a cada tipus de treball |
| `Equips` | Equips d'instal·ladors amb el seu PIN |
| `Seguiment` | Registre de totes les jornades enviades |
| `Borranys` | Informes pendents de revisió (estat: PENDENT / ENVIAT / REBUTJAT) |

---

## Flux d'un informe

1. **Instal·lador** entra amb PIN (de la pestanya Equips) → crea informe → "ENVIAR A REVISIÓ"
   - Es guarda a `Borranys` amb estat `PENDENT`
   - S'envia email de notificació a `estelleparquetbcn1@gmail.com` i `jestelle@mundoparquet.com`
2. **Revisor** (Luis o Joan) entra amb PIN de revisor → veu borranys pendents → "APROVAR I ENVIAR AL CLIENT"
   - S'envia email al client amb logo, fotos i firmes

### PINs especials (configurats als Secrets de Streamlit)

- **`[revisor] pin`** → accés directe a la pantalla de revisió
- **`[directe] pin`** → l'informe s'envia directament al client sense passar per revisió (per a Joan i Luis quan fan ells mateixos el seguiment)

---

## Secrets de Streamlit necessaris

```toml
[smtp]
server = "..."
port = 587  # o 465 per SSL
user = "..."
password = "..."

[revisor]
pin = "999,888"  # PINs de revisors (Luis, Joan com a revisor)

[directe]
pin = "123,1234"  # PINs que envien directament al client sense revisió

[app_url]
url = "https://appseguiment.streamlit.app"  # URL de l'app per als emails de notificació
```

---

## Decisions tècniques i bugs resolts

### Enviament d'emails
- **Port SMTP:** suporta 465 (SSL) i 587 (STARTTLS) automàticament
- **From header:** usar `formataddr(("Estelle Parquet", smtp_user))` — el From ha de coincidir amb l'usuari SMTP autenticat, sinó els servidors rebutgen el correu
- **Destinataris:** llegits de `Projectes.Emails_Contacte` → guardats a `Borranys.Destinataris`. Si buits, fallback a rellegir de la fulla en el moment de revisió

### Google Sheets — límit 50.000 caràcters/cel·la
- Fotos i firmes es guarden comprimides en base64
- Funció `img_compress_b64(content, max_side=600, quality=40)` amb retry automàtic
- Fotos: compressió adaptativa segons nombre de fotos per quedar sota el límit
- Firmes: max 800px, quality 70

### Camps numèrics amb text
- `build_email_html`: si un camp és `tipus=num` però conté text (ex: "6ª planta 01,02,03..."), es mostra com a text en lloc de "0"
- `fmt_valor`: si el valor no és parsejable com a número, retorna el text tal qual

### Pandas i NaN
- Cel·les buides de Sheets arriben com `NaN` (float), no com a string buit
- Sempre usar `str(brow.get("camp") or "").strip()` en lloc de `brow.get("camp", "").strip()`

### sort_with_tail
- Usar `list(dict.fromkeys(...))` en lloc de `list(set(...))` per preservar l'ordre d'inserció

### st.rerun()
- Cridar `st.rerun()` després d'accions importants (enviar a revisió, guardar firma) per refrescar l'estat

---

## Rols i accés

- **Instal·ladors:** PIN a la pestanya `Equips` → creen i envien informes a revisió
- **Revisors:** PIN als Secrets `[revisor]` → revisen i aproven/rebutgen
- **Directe:** PIN als Secrets `[directe]` → envien directament al client (Joan, Luis)
- Un PIN pot estar tant a `Equips` com als Secrets → permet fer les dues funcions usant el PIN d'instal·lador com a revisor
