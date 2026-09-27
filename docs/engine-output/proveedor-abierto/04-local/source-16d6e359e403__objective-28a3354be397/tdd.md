---
generated_by:
  backend: vultr
  model: glm-5.3-flash
  at: '2026-09-27T11:24:25.106220+00:00'
---
# Technical definition document

Discovered source: `https://www.sat.gob.mx/minisitio/DatosAbiertos/padron.html`

Allowed domain: `www.sat.gob.mx`

Extraction method: download

Site graph starting path bronze key: `sha256:9991793e063ccab8e3d83bba55cd63c57f6cff3a65ec375527f557f763cb4f75`

Site graph path: `03-fanout/surface-map/source-16d6e359e403/site-graph.json`

## Steps

- **step-1-navigate-padron** SAFE GET navigate to the confirmed padron listing page https://www.sat.gob.mx/minisitio/DatosAbiertos/padron.html (page-ce033af290b60cecc9dd93c9) and re-verify the captured download links, including AvisosAntRFC.xls (link_index 27), without inventing any URLs.
- **step-2-download-avisos-ant-rfc** LOW-risk read-only GET download of the captured SAT open-data file https://wu1agsprosta001.blob.core.windows.net/agsc-publicaciones/Datos_abiertos/Cifras_SAT/Documents/AvisosAntRFC.xls (Avisos de inscripción, suspensión y cancelación) which carries RFC registration records.
- **step-3-parse-rfc-records** Parse the downloaded AvisosAntRFC.xls to extract supplier_rfc and supplier_name rows (registration/suspension/cancellation notices), tagging each value with the file's evidence key and the SAT primary source class.
