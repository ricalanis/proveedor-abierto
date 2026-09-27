"""Spanish-first copy (English optional).

Templates write their English source text through `_()`. Spanish is the default language; `?lang=en` switches to
English and a cookie keeps the choice. Domain words (class, property and relation labels, rule text) come from the
case's ontology in whatever language the ontology phase wrote them; only the app's own copy is translated here.
`tests/test_i18n.py` fails when a template string has no Spanish entry.
"""

from __future__ import annotations

from datetime import UTC, datetime

LANGS = ("es", "en")
DEFAULT_LANG = "es"
COOKIE = "pa_lang"

MONTHS_ES = ("ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic")
MONTHS_EN = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

ES: dict[str, str] = {
    # chrome
    "Not in the approved ontology:": "Fuera de la ontología aprobada:",
    "Harness-assisted run (Claude Code), not engine-authored.":
        "Corrida asistida por el arnés (Claude Code), no generada por el motor.",
    "Claude Code built this dataset from public downloads with its own scripts; the Ontofill engine did not produce it. Every value still carries its source, locator and quote.":
        "Claude Code armó este conjunto de datos con descargas públicas y sus propios scripts; el motor Ontofill no lo produjo. Cada dato conserva su fuente, su ubicación y su cita.",
    "Contracts are INAI's own purchases (its official OCDS publication, May 2020 to February 2025), not CompraNet: the CompraNet and ComprasMX downloads were blocked and were not bypassed.":
        "Los contratos son compras del propio INAI (su publicación oficial OCDS, de mayo de 2020 a febrero de 2025), no de CompraNet: las descargas de CompraNet y ComprasMX estaban bloqueadas y no se evadió el bloqueo.",
    "Founding dates are derived from each RFC, not read from a registry.":
        "Las fechas de constitución se derivan de cada RFC, no se leyeron de un registro.",
    "Addresses are as declared in the contracts (8 suppliers use a municipal supplier register instead).":
        "Los domicilios son los declarados en los contratos (8 proveedores usan en su lugar un padrón municipal de proveedores).",
    "Strictly against the approved source classes, 3 of the 4 required are covered: the commercial registry is still missing.":
        "Contra las clases de fuente aprobadas, en sentido estricto se cubren 3 de las 4 requeridas: falta el registro público de comercio.",
    "Skip to content": "Saltar al contenido",
    "Sections": "Secciones",
    "Breadcrumb": "Ruta",
    "Who receives public money": "Quién recibe dinero público",
    "Who receives public money?": "¿Quién recibe dinero público?",
    "Who receives public money, with the receipts": "Quién recibe dinero público, con sus comprobantes",
    "Public-procurement suppliers with the public record behind every value. Signals to verify, not accusations.":
        "Proveedores del gobierno con el registro público detrás de cada dato. Señales para verificar, no acusaciones.",
    "Search": "Buscar",
    "Signals": "Señales",
    "Connections": "Conexiones",
    "My list": "Mi lista",
    "Open data": "Datos abiertos",
    "How complete": "Qué tan completo",
    "How it works": "Cómo funciona",
    "Practice data.": "Datos de práctica.",
    "Every name, identifier and source on this site is invented (.example sites, obviously fake names). The real case has not published its data yet.":
        "Todos los nombres, identificadores y fuentes de este sitio son inventados (sitios .example, nombres obviamente falsos). El caso real todavía no publica sus datos.",
    "Simulated collection.": "Recolección simulada.",
    "These values came from recorded model responses, not a live collection run. Treat them as a placeholder.":
        "Estos datos salieron de respuestas grabadas de un modelo, no de una recolección real. Tómalos como un ejemplo.",
    "Unreviewed preview.": "Vista previa sin revisar.",
    "This data was produced before a person approved the case's definition. It is not the published result.":
        "Estos datos se produjeron antes de que una persona aprobara la definición del caso. No son el resultado publicado.",
    "Every value comes from a public source and links to its capture. A signal says where to look; it is not an accusation.":
        "Cada dato viene de una fuente pública y enlaza a su captura. Una señal dice dónde mirar; no es una acusación.",
    "Something wrong? Dispute it": "¿Algo está mal? Dispútalo",
    "Case journal": "Bitácora del caso",
    "Source code and case package": "Código y paquete del caso",
    # status and confidence words
    "Confirmed": "Confirmado",
    "Sources disagree": "Fuentes en desacuerdo",
    "Not found": "No encontrado",
    "high": "alta",
    "medium": "media",
    "low": "baja",
    "unknown": "desconocida",
    # search
    "Look up a {cls} and see what public records say about it: every value with the page it came from and when it was captured.":
        "Busca un {cls} y mira lo que dicen los registros públicos: cada dato con la página de donde salió y cuándo se capturó.",
    "Name, {idlabel} or ID": "Nombre, {idlabel} o ID",
    "identifier": "identificador",
    "This dataset": "Estos datos",
    "with a complete basic profile": "con perfil básico completo",
    "with signals to verify": "con señales por verificar",
    "public sources consulted": "fuentes públicas consultadas",
    "latest capture": "última captura",
    "How complete is this data?": "¿Qué tan completos son estos datos?",
    "Results for “{q}”": "Resultados para «{q}»",
    "Browse all {plural}": "Todos los {plural}",
    "Show": "Mostrar",
    "All": "Todos",
    "With signals": "Con señales",
    "Incomplete profile": "Perfil incompleto",
    "{n} of {total}": "{n} de {total}",
    "page {n} of {m}": "página {n} de {m}",
    "Pages": "Páginas",
    "Previous": "Anterior",
    "Next": "Siguiente",
    "{label} not found": "{label} no encontrado",
    "{n} of {m} basic facts": "{n} de {m} datos básicos",
    "{n} signal": "{n} señal",
    "{n} signals": "{n} señales",
    "{n} disagreement": "{n} desacuerdo",
    "{n} disagreements": "{n} desacuerdos",
    "Nothing matches. Check the spelling, try the {idlabel}, or clear the filter.":
        "Nada coincide. Revisa la ortografía, prueba con {idlabel} o quita el filtro.",
    "Show everything": "Mostrar todo",
    # dossier
    "Basic profile": "Perfil básico",
    "{n} of {m} facts confirmed": "{n} de {m} datos confirmados",
    "Sources": "Fuentes",
    "Add to my list": "Agregar a mi lista",
    "On my list": "En mi lista",
    "See connections": "Ver conexiones",
    "Download CSV": "Descargar CSV",
    "Signals to verify": "Señales por verificar",
    "A signal is a pattern in public records worth checking. It is not an accusation, and it can have an ordinary explanation.":
        "Una señal es un patrón en los registros públicos que vale la pena revisar. No es una acusación y puede tener una explicación ordinaria.",
    "Based on:": "Se basa en:",
    "How to verify it": "Cómo verificarla",
    "Dispute it": "Disputarla",
    "No signal in this data.": "No hay señales en estos datos.",
    "What public records say": "Lo que dicen los registros públicos",
    "Part of the basic profile": "Parte del perfil básico",
    "basic": "básico",
    "Not found in public sources": "No se encontró en fuentes públicas",
    "captured {date}": "capturado el {date}",
    "confidence {level}": "confianza {level}",
    "See receipt": "Ver comprobante",
    "See {n} receipts": "Ver {n} comprobantes",
    "Connected {plural}": "{plural} conectados",
    "through": "por",
    "Open in the connections map": "Abrir en el mapa de conexiones",
    "No connection to another {cls} in this data.": "Sin conexión con otro {cls} en estos datos.",
    "Receipt": "Comprobante",
    "Choose “See receipt” on any value to see where it came from: the public page, a screenshot of it, and when it was captured.":
        "Elige «Ver comprobante» en cualquier dato para ver de dónde salió: la página pública, una captura de pantalla y cuándo se capturó.",
    # receipt
    "not found": "no encontrado",
    "How we got this value": "Cómo obtuvimos este dato",
    "Only a supporting model backs this value; it still needs a second check.":
        "Solo un modelo de apoyo respalda este dato; todavía necesita una segunda revisión.",
    "Simulated collection: this value came from recorded responses and will be replaced by a live run.":
        "Recolección simulada: este dato salió de respuestas grabadas y se reemplazará con una recolección real.",
    "Sources disagree. Each receipt below shows what that source says; the value above is the best-supported one.":
        "Las fuentes no coinciden. Cada comprobante muestra lo que dice esa fuente; el dato de arriba es el mejor respaldado.",
    "Captured {date}": "Capturado el {date}",
    "Screenshot of {host} captured {date}": "Captura de pantalla de {host} tomada el {date}",
    "Screenshot of the page as the collector saw it. Open it full size.":
        "Captura de la página tal como la vio el recolector. Ábrela en tamaño completo.",
    "Technical details": "Detalles técnicos",
    "Where on the page": "Lugar en la página",
    "Saved copy": "Copia guardada",
    "Source ID": "ID de la fuente",
    "Timestamp": "Marca de tiempo",
    "needs a second check": "necesita una segunda revisión",
    "Public source": "Fuente pública",
    "No link recorded": "Sin enlace registrado",
    "the source": "la fuente",
    "Screenshot of the whole page as the collector saw it. The value is in the part named above; open it full size to read it.":
        "Captura de la página completa tal como la vio el recolector. El dato está en la parte indicada arriba; ábrela en tamaño completo para leerlo.",
    "The screenshot could not be loaded. The saved copy and the link above still show the source.":
        "No se pudo cargar la captura. La copia guardada y el enlace de arriba siguen mostrando la fuente.",
    "No screenshot for this capture; the saved copy below keeps what the collector read.":
        "Esta captura no tiene imagen; la copia guardada de abajo conserva lo que leyó el recolector.",
    "No receipt published for this value": "No se publicó comprobante para este dato",
    "Where in the document": "Lugar en el documento",
    "Cell or row in the file": "Celda o fila en el archivo",
    "Row in the file": "Fila en el archivo",
    "Field in the data": "Campo en los datos",
    "Where in the source": "Lugar en la fuente",
    "No receipt backs this value.": "Ningún comprobante respalda este dato.",
    # signals
    "Patterns in public records that are worth a closer look. Each one follows a written rule and links to the records it rests on. A signal is where to start checking, not a finding: many have an ordinary explanation.":
        "Patrones en los registros públicos que vale la pena mirar de cerca. Cada uno sigue una regla escrita y enlaza a los registros en que se basa. Una señal es por dónde empezar a revisar, no un hallazgo: muchas tienen una explicación ordinaria.",
    "The rule:": "La regla:",
    "Signal to verify": "Señal por verificar",
    "This is not an accusation. It means public records match a pattern that investigators check first. It may have an ordinary explanation, and the records themselves can be wrong or out of date.":
        "Esto no es una acusación. Significa que los registros públicos coinciden con un patrón que quienes investigan revisan primero. Puede tener una explicación ordinaria, y los propios registros pueden estar equivocados o desactualizados.",
    "Why it appears": "Por qué aparece",
    "The rule": "La regla",
    "The records it rests on": "Los registros en que se basa",
    "From": "De",
    "How to verify it yourself": "Cómo verificarla tú",
    "Is this wrong? Dispute it": "¿Está mal? Dispútala",
    "If you represent this {cls} and a value is wrong:": "Si representas a este {cls} y un dato está mal:",
    "Ask the office that published the record to correct it. The receipt above links to the exact page.":
        "Pide a la oficina que publicó el registro que lo corrija. El comprobante de arriba enlaza a la página exacta.",
    "Send the dispute record below, with the document that shows the correct value, by opening an issue in the public repository.":
        "Envía el registro de disputa de abajo, con el documento que muestra el dato correcto, abriendo un issue en el repositorio público.",
    "Open a dispute": "Abrir una disputa",
    "When the public record changes, the next collection picks it up and the signal clears if the rule no longer holds.":
        "Cuando cambie el registro público, la siguiente recolección lo toma y la señal desaparece si la regla ya no se cumple.",
    "Dispute record for this signal": "Registro de disputa de esta señal",
    "Dispute": "Disputa",
    "Copied": "Copiado",
    "Select the text to copy": "Selecciona el texto para copiarlo",
    "Copy record": "Copiar registro",
    # connections
    "{plural} that share something in public records, such as an address or a representative. A shared detail is a lead to check, not proof of a relationship. Each line links to the record that connects them.":
        "{plural} que comparten algo en los registros públicos, como un domicilio o un representante. Un dato compartido es una pista por revisar, no prueba de una relación. Cada línea enlaza al registro que los conecta.",
    "Connect by": "Conectar por",
    "Apply": "Aplicar",
    "{n} group of connected records": "{n} grupo de registros conectados",
    "{n} groups of connected records": "{n} grupos de registros conectados",
    "Group of {n}": "Grupo de {n}",
    "Map of {n} connected records": "Mapa de {n} registros conectados",
    "No connections of the chosen kinds in this data.": "No hay conexiones de los tipos elegidos en estos datos.",
    # watchlist
    "The {plural} you follow, and what changed in public records since the previous collection.":
        "Los {plural} que sigues y lo que cambió en los registros públicos desde la recolección anterior.",
    "compared with run": "comparado con la corrida",
    "Your list is kept in this browser only; nothing is stored on our server. To keep it or share it, copy this page's address.":
        "Tu lista se guarda solo en este navegador; nada se guarda en nuestro servidor. Para conservarla o compartirla, copia la dirección de esta página.",
    "Remove": "Quitar",
    "absent": "ausente",
    "New signal:": "Señal nueva:",
    "Signal cleared:": "Señal que desapareció:",
    "No longer in the latest data": "Ya no aparece en los datos más recientes",
    "New in this collection": "Nuevo en esta recolección",
    "{n} new connection": "{n} conexión nueva",
    "{n} new connections": "{n} conexiones nuevas",
    "No changes since the previous collection.": "Sin cambios desde la recolección anterior.",
    "This is the first collection, so there is nothing to compare yet.":
        "Esta es la primera recolección, así que aún no hay con qué comparar.",
    "Download my list": "Descargar mi lista",
    "Your list is empty. Open any profile and choose “Add to my list”.":
        "Tu lista está vacía. Abre cualquier perfil y elige «Agregar a mi lista».",
    # open data
    "Download everything on this site. Each file carries the same values you see here, with their sources.":
        "Descarga todo lo que hay en este sitio. Cada archivo trae los mismos datos que ves aquí, con sus fuentes.",
    "One row per {cls}, one column per fact, plus the source of each value. Opens in any spreadsheet.":
        "Una fila por {cls}, una columna por dato, más la fuente de cada valor. Se abre en cualquier hoja de cálculo.",
    "Contracts in the Open Contracting Data Standard, the format governments use to publish procurement data.":
        "Contratos en el Estándar de Datos de Contrataciones Abiertas (OCDS), el formato que usan los gobiernos para publicar sus compras.",
    "Linked data for researchers, aligned to public vocabularies where the case defines them.":
        "Datos enlazados para investigación, alineados a vocabularios públicos donde el caso los define.",
    "To download only the {plural} you follow, use the download on": "Para descargar solo los {plural} que sigues, usa la descarga de",
    "Reusing it": "Reutilizarlos",
    "The values come from public records; check each source's own terms before republishing. The case package (the question, the definition, the rules behind signals) and this site's code are in the public repository and can be forked.":
        "Los datos vienen de registros públicos; revisa los términos de cada fuente antes de republicarlos. El paquete del caso (la pregunta, la definición, las reglas de las señales) y el código de este sitio están en el repositorio público y se pueden copiar.",
    "Data from run": "Datos de la corrida",
    # completeness
    "Public records are scattered and often incomplete. This page says plainly how much we found, and what is still missing, so you know how far to trust an empty field.":
        "Los registros públicos están dispersos y muchas veces incompletos. Esta página dice con claridad cuánto encontramos y qué falta, para que sepas cuánto confiar en un campo vacío.",
    "of {total} {plural} have a complete basic profile ({pct}).": "de {total} {plural} tienen su perfil básico completo ({pct}).",
    "A basic profile counts as complete when at least {pct} of its basic facts are confirmed by a public source with a receipt.":
        "Un perfil básico cuenta como completo cuando al menos {pct} de sus datos básicos están confirmados por una fuente pública con comprobante.",
    "Fact by fact": "Dato por dato",
    "Fact": "Dato",
    "Share confirmed": "Porcentaje confirmado",
    "Count": "Cantidad",
    "{n} of {m}": "{n} de {m}",
    "Hardest to find so far:": "Lo más difícil de encontrar hasta ahora:",
    "An empty field means no public source we reached published it, not that the fact is false.":
        "Un campo vacío significa que ninguna fuente pública que consultamos lo publicó, no que el dato sea falso.",
    "What you can rely on": "En qué puedes confiar",
    "Values without a receipt: {n}.": "Datos sin comprobante: {n}.",
    "Every confirmed value links to the public page it came from.": "Cada dato confirmado enlaza a la página pública de donde salió.",
    "{n} value where sources disagree; both versions are shown.": "{n} dato en que las fuentes no coinciden; se muestran ambas versiones.",
    "{n} values where sources disagree; every version is shown.": "{n} datos en que las fuentes no coinciden; se muestran todas las versiones.",
    "{n} kind of public source consulted.": "{n} tipo de fuente pública consultada.",
    "{n} kinds of public source consulted.": "{n} tipos de fuente pública consultados.",
    "Our recount of these numbers does not match the collector's own report; treat them with care.":
        "Nuestro recuento de estas cifras no coincide con el reporte del recolector; tómalas con cuidado.",
    "We recount these numbers from the published data, and they match the collector's own report.":
        "Recontamos estas cifras a partir de los datos publicados y coinciden con el reporte del recolector.",
    "The case's own definition of done (technical)": "La definición de terminado del caso (técnico)",
    "target": "meta",
    "Not counted (simulated)": "No cuenta (simulado)",
    "Met": "Cumplido",
    "Not yet": "Todavía no",
    # about
    "Proveedor Abierto gathers what public records say about the companies that receive public money, and shows where each fact came from.":
        "Proveedor Abierto reúne lo que dicen los registros públicos sobre las empresas que reciben dinero público y muestra de dónde salió cada dato.",
    "Where the data comes from": "De dónde vienen los datos",
    "Software agents read public websites, such as official registries, open-data portals and gazettes, the way a person would: searching, paging through results and downloading published files. They never log in, never get past a captcha and never submit anything except searches. Every page they read is kept as a saved copy with a screenshot.":
        "Agentes de software leen sitios públicos, como registros oficiales, portales de datos abiertos y diarios oficiales, como lo haría una persona: buscan, pasan páginas de resultados y descargan archivos publicados. Nunca inician sesión, nunca saltan un captcha y nunca envían nada que no sea una búsqueda. Cada página que leen se guarda como copia con una captura de pantalla.",
    "This data draws on {n} public source.": "Estos datos provienen de {n} fuente pública.",
    "This data draws on {n} public sources.": "Estos datos provienen de {n} fuentes públicas.",
    "See them in the case journal": "Consúltalas en la bitácora del caso",
    "How to read a profile": "Cómo leer un perfil",
    "A public source published it, and the receipt shows where.": "Una fuente pública lo publicó y el comprobante muestra dónde.",
    "Two sources say different things. Both are shown; neither is hidden.":
        "Dos fuentes dicen cosas distintas. Se muestran ambas; no se oculta ninguna.",
    "No source we reached published it. That is not evidence of anything.":
        "Ninguna fuente que consultamos lo publicó. Eso no es evidencia de nada.",
    "Confidence (high, medium, low) is how sure the collector is that it read the value correctly from the page, not a judgment about the company.":
        "La confianza (alta, media, baja) indica qué tan seguro está el recolector de haber leído bien el dato en la página; no es un juicio sobre la empresa.",
    "Signals are not accusations": "Las señales no son acusaciones",
    "A signal marks a pattern that investigators usually check first, such as a company appearing on an official list or two bidders sharing an address. Each follows a written rule, lists the records it rests on and explains how to verify it. Many signals have an ordinary explanation. This site does not score anyone and does not say anyone did anything wrong.":
        "Una señal marca un patrón que quienes investigan suelen revisar primero, como que una empresa aparezca en una lista oficial o que dos participantes compartan domicilio. Cada una sigue una regla escrita, enumera los registros en que se basa y explica cómo verificarla. Muchas señales tienen una explicación ordinaria. Este sitio no califica a nadie ni dice que alguien haya hecho algo mal.",
    "Profiles are of companies. Information about people is limited to what public records publish about their role, such as a legal representative.":
        "Los perfiles son de empresas. La información sobre personas se limita a lo que los registros públicos publican sobre su cargo, como un representante legal.",
    "Open the signal or value and use its receipt to find the office that published it.":
        "Abre la señal o el dato y usa su comprobante para encontrar la oficina que lo publicó.",
    "Ask that office to correct the public record.": "Pide a esa oficina que corrija el registro público.",
    "Tell us by opening an issue in the public repository with the dispute record the page gives you and the document that shows the correct value. Issues are public.":
        "Avísanos abriendo un issue en el repositorio público con el registro de disputa que te da la página y el documento que muestra el dato correcto. Los issues son públicos.",
    "Open an issue": "Abrir un issue",
    "When the public record changes, the next collection picks it up.": "Cuando cambie el registro público, la siguiente recolección lo tomará.",
    "Open and reusable": "Abierto y reutilizable",
    "All of this data can be downloaded (CSV, OCDS JSON, RDF), and the case definition that produced it is public so anyone can check or repeat the work.":
        "Todos estos datos se pueden descargar (CSV, OCDS JSON, RDF), y la definición del caso que los produjo es pública para que cualquiera pueda revisar o repetir el trabajo.",
    "Download the data": "Descargar los datos",
    "latest capture {date}": "última captura el {date}",
    # journal
    "Every value on this site can be traced back to the original question. Open any receipt and choose “How we got this value”, or start from the documents below.":
        "Cada dato de este sitio se puede rastrear hasta la pregunta original. Abre cualquier comprobante y elige «Cómo obtuvimos este dato», o empieza por los documentos de abajo.",
    "Follow an example value": "Seguir un dato de ejemplo",
    "The case package": "El paquete del caso",
    "Document": "Documento",
    "File": "Archivo",
    "State": "Estado",
    "published": "publicado",
    "not produced yet": "aún no se produce",
    "not in this copy": "no está en esta copia",
    "Technical definition": "Definición técnica",
    "Technical definition document": "Documento de definición técnica",
    "Public sources the collectors found": "Fuentes públicas que encontraron los recolectores",
    "Source": "Fuente",
    "Kind": "Tipo",
    "How it was found": "Cómo se encontró",
    "Objectives": "Objetivos",
    "No sources published yet.": "Aún no hay fuentes publicadas.",
    "Steps in run": "Pasos de la corrida",
    "Phase": "Fase",
    "Steps": "Pasos",
    "Brief": "Pregunta inicial",
    "Global PRD": "Definición del caso (PRD)",
    "Ontology": "Ontología",
    "Scope": "Alcance",
    "Fan out": "Búsqueda de fuentes",
    "Local scoping": "Acuerdo por fuente",
    "Execute": "Recolección",
    "From this value back to the original question. Read top to bottom: the value, the step that captured it, the instructions that step followed, the goal it served, the case definition behind that goal, and the question everything started from.":
        "De este dato de regreso a la pregunta original. Lee de arriba abajo: el dato, el paso que lo capturó, las instrucciones que siguió ese paso, el objetivo al que servía, la definición del caso detrás de ese objetivo y la pregunta con la que empezó todo.",
    "Value": "Dato",
    "No collection step lists this value; part of its history is missing from the published data.":
        "Ningún paso de recolección menciona este dato; falta parte de su historia en los datos publicados.",
    "Path {n} of {m}": "Camino {n} de {m}",
    "Collection mode": "Modo de recolección",
    "Observed": "Observado",
    "Requested": "Solicitado",
    "Executed": "Ejecutado",
    "Evaluated": "Evaluado",
    "objective": "objetivo",
    "How this source was found:": "Cómo se encontró esta fuente:",
    "Open the full document": "Abrir el documento completo",
    "Not in this copy of the case package.": "No está en esta copia del paquete del caso.",
    "not in this copy of the case package yet": "aún no está en esta copia del paquete del caso",
    # empty states and how this was made
    'How this was made':
        'Cómo se hizo',
    'No {plural} have been published yet, so there is nothing to measure. This page fills in as values are confirmed.':
        'Aún no se publican {plural}, así que no hay nada que medir. Esta página se llena conforme se confirman datos.',
    "No signal has fired for this {cls} in the data published so far. That is not a clean record; it means none of the case's rules matched the values found.":
        'Ninguna señal se ha activado para este {cls} en los datos publicados hasta ahora. Eso no es un historial limpio; significa que ninguna regla del caso coincidió con los datos encontrados.',
    'What is checked':
        'Qué se revisa',
    'No connection to another {cls} in the data published so far.':
        'Sin conexión con otro {cls} en los datos publicados hasta ahora.',
    'The case looks for:':
        'El caso busca:',
    'No {plural} have been published yet. The collection is still under way; this page fills in as values are confirmed.':
        'Aún no se publican {plural}. La recolección sigue en curso; esta página se llena conforme se confirman datos.',
    'Nobody typed these records in. It started with one question; from there, software agents defined the case, found the public sources on their own and read them, and each definition goes to a person for approval. These are the steps, in order, each with what it produced.':
        'Nadie capturó estos registros a mano. Todo empezó con una pregunta; a partir de ella, agentes de software definieron el caso, encontraron por su cuenta las fuentes públicas y las leyeron, y cada definición pasa por la aprobación de una persona. Estos son los pasos, en orden, cada uno con lo que produjo.',
    'The question':
        'La pregunta',
    'This is the only thing a person wrote by hand. Everything below was produced from it.':
        'Es lo único que escribió una persona a mano. Todo lo de abajo se produjo a partir de ella.',
    'See the file':
        'Ver el archivo',
    "The case's question has not been published yet.":
        'La pregunta del caso aún no se publica.',
    'The definition':
        'La definición',
    "This definition is still waiting for a person's approval, so it may change.":
        'Esta definición todavía espera la aprobación de una persona, así que puede cambiar.',
    'Who it is for':
        'Para quién es',
    'What they need to find out':
        'Qué necesitan averiguar',
    'The ground rules':
        'Las reglas del juego',
    'Not a goal:':
        'No es objetivo:',
    'When it counts as done':
        'Cuándo se considera terminado',
    'Read the full definition':
        'Leer la definición completa',
    'How close the data is to done':
        'Qué tan cerca están los datos de terminar',
    'The case definition has not been published yet.':
        'La definición del caso aún no se publica.',
    'What is recorded':
        'Qué se registra',
    'From the definition, the case describes what kinds of records exist and which facts matter:':
        'A partir de la definición, el caso describe qué tipos de registro existen y qué datos importan:',
    'Kinds of record':
        'Tipos de registro',
    'Basic facts per {cls}':
        'Datos básicos por {cls}',
    'Signals it checks':
        'Señales que revisa',
    'none defined yet':
        'ninguna definida todavía',
    'Connections it looks for':
        'Conexiones que busca',
    'The public sources':
        'Las fuentes públicas',
    'The agents searched for where each fact is published and kept only public sites: no logins, no captchas, nothing submitted but searches.':
        'Los agentes buscaron dónde se publica cada dato y se quedaron solo con sitios públicos: sin inicios de sesión, sin captchas, sin enviar nada que no sea una búsqueda.',
    'They found {n} candidate source.':
        'Encontraron {n} fuente candidata.',
    'They found {n} candidate sources.':
        'Encontraron {n} fuentes candidatas.',
    'Values it backs':
        'Datos que respalda',
    'No values have been published from any source yet.':
        'Aún no se publican datos de ninguna fuente.',
    'The evidence':
        'La evidencia',
    'Every published value keeps its receipt: the page it came from, a screenshot of that page and a saved copy, with the time it was captured.':
        'Cada dato publicado conserva su comprobante: la página de donde salió, una captura de esa página y una copia guardada, con la hora en que se capturó.',
    'values published':
        'datos publicados',
    'with a receipt':
        'con comprobante',
    'screenshots kept':
        'capturas guardadas',
    'captured between':
        'capturados entre',
    'Follow one value back to the question':
        'Seguir un dato hasta la pregunta',
    'No values have been published yet.':
        'Aún no se publican datos.',
    'Check it yourself':
        'Revísalo tú',
    'any value, traced step by step back to the question.':
        'cualquier dato, rastreado paso a paso hasta la pregunta.',
    'the open-source engine that did the work; it runs any question, not only this one.':
        'el motor de código abierto que hizo el trabajo; sirve para cualquier pregunta, no solo esta.',
    'this case (question, definition, sources, rules) and this site, ready to fork.':
        'este caso (pregunta, definición, fuentes, reglas) y este sitio, listos para copiarse.',
    'No connections found in the data published so far':
        'No se encontraron conexiones en los datos publicados hasta ahora',
    'The case looks for {plural} that share any of these in public records:':
        'El caso busca {plural} que compartan alguno de estos datos en los registros públicos:',
    'not selected above':
        'no seleccionado arriba',
    'None were found yet. A connection needs the same value, taken from a public record, on two {plural}; as more facts are collected, connections can appear.':
        'Aún no se encontró ninguna. Una conexión necesita el mismo dato, tomado de un registro público, en dos {plural}; conforme se recolecten más datos pueden aparecer conexiones.',
    'Connections are not defined yet':
        'Las conexiones aún no están definidas',
    'The case has not published which connections to look for (for example, a shared address or legal representative). When it does, they will be drawn here, each linked to the record that connects them.':
        'El caso aún no publica qué conexiones buscar (por ejemplo, un domicilio o un representante legal compartido). Cuando lo haga, se dibujarán aquí, cada una enlazada al registro que las conecta.',
    'No signal has fired in the data published so far':
        'Ninguna señal se ha activado en los datos publicados hasta ahora',
    'Every {cls} is checked against the rules below. None matched yet. That is not a clean record: a rule can only fire on values the collectors have found, and some facts are still missing.':
        'Cada {cls} se revisa con las reglas de abajo. Ninguna coincidió todavía. Eso no es un historial limpio: una regla solo se activa con datos que los recolectores encontraron, y aún faltan datos.',
    'The case has not published its signal rules yet. Each one will be a written rule, checked against the public records on this site, with the records it rests on and how to verify it.':
        'El caso aún no publica sus reglas de señales. Cada una será una regla escrita, revisada contra los registros públicos de este sitio, con los registros en que se basa y cómo verificarla.',
    'See how complete the data is':
        'Ver qué tan completos son los datos',
    # how to read a profile
    'Full guide':
        'Guía completa',
    'How to read this profile?':
        '¿Cómo leer esta ficha?',
    'How to read it':
        'Cómo leerlo',
    'Every fact in a profile comes with its receipt: where it was published, when it was captured, where on the page it is, and how sure the collector is that it read it right.':
        'Cada dato de una ficha viene con su comprobante: dónde se publicó, cuándo se capturó, en qué lugar de la página está y qué tan seguro está el recolector de haberlo leído bien.',
    'A receipt, part by part':
        'Un comprobante, parte por parte',
    'A real receipt from this data:':
        'Un comprobante real de estos datos:',
    'Example receipt':
        'Comprobante de ejemplo',
    'The fact':
        'El dato',
    'and its value, exactly as the public source shows it.':
        'y su valor, tal como lo muestra la fuente pública.',
    'The stamp':
        'El sello',
    'says what the sources agree on (see below).':
        'dice en qué coinciden las fuentes (ver abajo).',
    'the public website that published the value. “+1 more” means other sources say the same or something different.':
        'el sitio público que publicó el dato. «+1 más» significa que otras fuentes dicen lo mismo o algo distinto.',
    'when the collector read the page. Public records change; a later capture may differ.':
        'cuándo leyó la página el recolector. Los registros públicos cambian; una captura posterior puede ser distinta.',
    'the exact spot on the page or in the file where the value is (a page element, a cell, a field).':
        'el lugar exacto de la página o del archivo donde está el dato (un elemento de la página, una celda, un campo).',
    'how sure the collector is that it read the value correctly (high, medium, low). It is not a judgment about the company.':
        'qué tan seguro está el recolector de haber leído bien el dato (alta, media, baja). No es un juicio sobre la empresa.',
    'opens the screenshot of the whole page, the link to it and a saved copy, so you can check it yourself.':
        'abre la captura de la página completa, el enlace y una copia guardada, para que lo revises tú.',
    'The three stamps':
        'Los tres sellos',
    'Solid stamp. A public source published it and the receipt shows where.':
        'Sello sólido. Una fuente pública lo publicó y el comprobante muestra dónde.',
    'Dashed stamp. Two sources say different things. Both receipts are kept; the value shown is the best-supported one, and you can compare them.':
        'Sello discontinuo. Dos fuentes dicen cosas distintas. Se guardan ambos comprobantes; el dato que se muestra es el mejor respaldado y puedes compararlos.',
    'Dotted stamp. No public source we reached published it. An empty field is not evidence of anything.':
        'Sello punteado. Ninguna fuente pública que consultamos lo publicó. Un campo vacío no es evidencia de nada.',
    'What a signal is, and what it is not':
        'Qué es una señal y qué no es',
    'It is':
        'Es',
    'a pattern in public records that investigators usually check first;':
        'un patrón en los registros públicos que quienes investigan suelen revisar primero;',
    'the result of a written rule, with the records it rests on;':
        'el resultado de una regla escrita, con los registros en que se basa;',
    'a starting point, with steps to verify it yourself.':
        'un punto de partida, con pasos para verificarla tú.',
    'It is not':
        'No es',
    'an accusation or a finding of wrongdoing;':
        'una acusación ni un hallazgo de una falta;',
    'a score or a probability of corruption;':
        'una calificación ni una probabilidad de corrupción;',
    'proof that the records are right: they can be wrong or out of date.':
        'prueba de que los registros son correctos: pueden estar equivocados o desactualizados.',
    'If something is wrong':
        'Si algo está mal',
    "Open the value's receipt and follow the link to the office that published it.":
        'Abre el comprobante del dato y sigue el enlace a la oficina que lo publicó.',
    'Tell us with a public issue in the repository; each signal page gives you a dispute record to paste.':
        'Avísanos con un issue público en el repositorio; cada página de señal te da un registro de disputa para pegar.',
    'More about disputes':
        'Más sobre disputas',
    'All the sources':
        'Todas las fuentes',
    'Meanwhile, you can see how the data is being made:':
        'Mientras tanto, puedes ver cómo se están produciendo los datos:',
    'the engine at work (console tour; sign-in required)':
        'el motor trabajando (recorrido en la consola; requiere iniciar sesión)',
    'Console tour':
        'Recorrido en la consola',
    "the engine's own view of this run, question by question (sign-in required).":
        'la vista del propio motor sobre esta corrida, pregunta por pregunta (requiere iniciar sesión).',
    # no gold / case file
    "Nothing published yet": "Aún no hay nada publicado",
    "This case has not published its data yet, or this site is not connected to it. Please come back later.":
        "Este caso aún no publica sus datos, o este sitio no está conectado a ellos. Vuelve más tarde.",
    "Technical reason": "Motivo técnico",
    "Case package": "Paquete del caso",
    # receipt slips (dossier + receipt panel): mono lines, uppercase on screen
    "Captured": "Captura",
    "Where": "Lugar",
    "Confidence": "Confianza",
    "Receipts": "Comprobantes",
    "+{n} more": "+{n} más",
    # source directory (/fuentes)
    "Source directory": "Directorio de fuentes",
    "Every public source behind a published value: what kind of site it is, which facts it backs, when it was read, and whether the case counts it as a trusted publisher. Each one links to a receipt you can check.":
        "Cada fuente pública detrás de un dato publicado: qué tipo de sitio es, qué datos respalda, cuándo se leyó y si el caso la cuenta como editor de confianza. Cada una enlaza a un comprobante que puedes revisar.",
    "Sources in numbers": "Las fuentes en números",
    "sources behind published values": "fuentes detrás de datos publicados",
    "values with a receipt": "datos con comprobante",
    "on the case's trusted list": "en la lista de confianza del caso",
    "On the case's trusted list": "En la lista de confianza del caso",
    "Not on the case's trusted list": "Fuera de la lista de confianza del caso",
    "The case does not say": "El caso no lo indica",
    "case rule: {action}": "regla del caso: {action}",
    "The case definition names its trusted publishers by domain; for any other site its rule is “{action}”.":
        "La definición del caso nombra a sus editores de confianza por dominio; para cualquier otro sitio su regla es «{action}».",
    "Read the definition": "Leer la definición",
    "The case definition has not published a trusted-publisher list, so no source is ranked here.":
        "La definición del caso aún no publica una lista de editores de confianza, así que aquí no se clasifica ninguna fuente.",
    "Trusted": "De confianza",
    "Unlisted": "Fuera de lista",
    "Backs": "Respalda",
    "{n} value": "{n} dato",
    "{n} values": "{n} datos",
    "First read": "Primera lectura",
    "Last read": "Última lectura",
    "Authority": "Autoridad",
    "Values it backs, by fact": "Datos que respalda, por tipo de dato",
    "Values": "Datos",
    "See one receipt: {prop} of {who}": "Ver un comprobante: {prop} de {who}",
    "No source backs a published value yet": "Ninguna fuente respalda todavía un dato publicado",
    "Sources appear here as soon as a value is published with its receipt. Until then there is nothing to list: the directory never shows a site that has not backed a value.":
        "Las fuentes aparecen aquí en cuanto se publica un dato con su comprobante. Mientras tanto no hay nada que listar: el directorio nunca muestra un sitio que no haya respaldado un dato.",
    "How sources are found": "Cómo se encuentran las fuentes",
    "Found, not backing any published value": "Encontradas, sin respaldar ningún dato publicado",
    "The case found these candidate sources, but no published value rests on them yet.":
        "El caso encontró estas fuentes candidatas, pero todavía ningún dato publicado se basa en ellas.",
    "Open the source directory": "Abrir el directorio de fuentes",
    "every source with the facts it backs, when it was read, whether the case trusts it, and one receipt to check.":
        "cada fuente con los datos que respalda, cuándo se leyó, si el caso confía en ella y un comprobante para revisar.",
    # authority tiers (sources.TIERS) and the PRD's unknown_source_action
    "Primary source": "Fuente primaria",
    "Secondary source": "Fuente secundaria",
    "Used after review": "Se usa tras revisión",
    "Tier not decided": "Nivel sin decidir",
    "review": "revisión",
}


# Spanish for ontology items, keyed by ontology id (classes, properties, relations, rules, source classes). The export
# stays in the engine's shape; where an id is not listed here, the export's own label shows (Domain.localized).
ONTOLOGY_ES: dict[str, dict] = {
    # ids of the approved Proveedor Abierto ontology (the harness-assisted instance serves it as is)
    "public_contract": {"label": "Contrato público", "label_plural": "Contratos públicos"},
    "evidence_record": {"label": "Registro de evidencia", "label_plural": "Registros de evidencia"},
    "supplier_name": {"label": "Razón social"}, "supplier_rfc": {"label": "RFC"},
    "registered_address": {"label": "Domicilio registrado"}, "contract_id": {"label": "ID del contrato"},
    "contract_title": {"label": "Título del contrato"}, "contract_rfc": {"label": "RFC del proveedor en el contrato"},
    "awarding_agency": {"label": "Dependencia contratante"}, "contract_value": {"label": "Monto del contrato"},
    "award_date": {"label": "Fecha de adjudicación"}, "evidence_id": {"label": "ID de la evidencia"},
    "evidence_label": {"label": "Etiqueta de la evidencia"}, "source_class": {"label": "Clase de fuente"},
    "authority_tier": {"label": "Nivel de autoridad"}, "source_url": {"label": "URL de la fuente"},
    "retrieved_at": {"label": "Fecha de consulta"}, "supplier_awarded_contract": {"label": "Contratos adjudicados"},
    "r_primary_authority": {"label": "Las fuentes oficiales mexicanas son la autoridad primaria"},
    # flags of a harness-assisted export (gold.FLAG_LABELS)
    "address_variants": {"label": "Domicilio escrito de distintas formas en los registros"},
    "name_variants": {"label": "Nombre escrito de distintas formas en los registros"},
    "shared_contract": {"label": "Comparte un contrato con otros proveedores"},
    "rfc_check_digit_mismatch": {"label": "El RFC no pasa el dígito verificador del SAT"},
    "registry_match": {"label": "Aparece en un padrón municipal de proveedores"},
    "sabg_sanctioned": {"label": "Aparece en el directorio de sancionados (SABG)"},
    "sat_69b_listed": {"label": "Aparece en la lista 69-B del SAT"},
    "name_differs_across_sources": {"label": "El nombre difiere entre fuentes"},
    "sanction_record_name_mention": {"label": "Su nombre aparece en un registro de sanción"},
    "source_class_not_in_approved_ontology": {"label": "Clase de fuente fuera de la ontología aprobada"},
    "proxy_source_class": {"label": "Fuente usada en lugar de otra clase de fuente"},
    "supplier": {"label": "Proveedor", "label_plural": "Proveedores"},
    "contract": {"label": "Contrato", "label_plural": "Contratos"},
    "legal_name": {"label": "Razón social"}, "tax_id": {"label": "RFC"}, "address": {"label": "Domicilio"},
    "founding_date": {"label": "Fecha de constitución"}, "tax_list_status": {"label": "Lista del SAT (69-B)"},
    "sanction_status": {"label": "Sanciones"}, "legal_representative": {"label": "Representante legal"},
    "title": {"label": "Contrato"}, "buyer": {"label": "Comprador"}, "procedure_type": {"label": "Procedimiento"},
    "date": {"label": "Fecha"}, "amount": {"label": "Monto"}, "currency": {"label": "Moneda"},
    "shared_address": {"label": "Mismo domicilio"},
    "shared_representative": {"label": "Mismo representante legal"},
    "same_procedure": {"label": "Mismo procedimiento"}, "awarded": {"label": "Contratos"},
    "awarded_to": {"label": "Adjudicado a"},
    "tax_list_listed": {
        "label": "Aparece en la lista del SAT de empresas que facturan operaciones simuladas",
        "checks": "Si el RFC del proveedor aparece en la lista publicada por la autoridad fiscal de empresas "
                     "que se presume o se confirmó que emiten facturas por operaciones simuladas.",
        "verify": [("Abre la captura de la lista y confirma que el RFC coincide exactamente (no solo un nombre "
                       "parecido)."),
                      ("Revisa la etapa: «presunto» todavía se puede desvirtuar; «definitivo» es una resolución "
                       "firme."),
                      "Compara la fecha de publicación con las fechas de los contratos."]},
    "sanctioned_supplier": {
        "label": "Aparece en el registro de proveedores sancionados",
        "checks": "Si el proveedor aparece en el registro de proveedores y contratistas sancionados.",
        "verify": ["Confirma que el registro se refiere a esta persona moral (por RFC, no solo por nombre).",
                      "Revisa las fechas de inicio y fin de la sanción y si alcanza a la dependencia contratante.",
                      "Busca una resolución judicial posterior que suspenda la sanción."]},
    "founded_shortly_before_award": {
        "label": "Se constituyó poco antes de su primer contrato",
        "checks": "Si la empresa se constituyó menos de un año antes de su primer contrato público registrado.",
        "verify": ["Confirma la fecha de constitución en la captura del registro o del diario oficial.",
                      "Revisa los requisitos de experiencia del procedimiento y si la empresa los cumplía.",
                      "Busca una empresa anterior con los mismos socios o domicilio."]},
    "shared_address_bidders": {
        "label": "Comparte domicilio con otro participante del mismo procedimiento",
        "checks": "Si dos participantes del mismo procedimiento declaran el mismo domicilio.",
        "verify": ["Compara ambas capturas del domicilio carácter por carácter.",
                      "Revisa si el domicilio es un edificio de oficinas grande o un centro de negocios.",
                      "Busca representantes, socios o teléfonos compartidos entre las dos empresas."]},
    "procurement_portal": {"label": "Portal de compras públicas"},
    "tax_authority_list": {"label": "Lista de la autoridad fiscal"},
    "sanctions_registry": {"label": "Registro de sancionados"},
    "company_registry": {"label": "Registro de empresas"}, "official_gazette": {"label": "Diario oficial"},
}

ONTOLOGY_LABELS = {"es": ONTOLOGY_ES}


def pick_lang(query: str | None, cookie: str | None) -> str:
    for candidate in (query, cookie):
        if candidate in LANGS:
            return candidate
    return DEFAULT_LANG


def translator(lang: str):
    catalog = ES if lang == "es" else {}

    def _(text: str, **kw) -> str:
        out = catalog.get(text, text)
        return out.format(**kw) if kw else out

    return _


def ngettext(lang: str):
    _ = translator(lang)

    def plural(singular: str, many: str, n: int, **kw) -> str:
        return _(singular if n == 1 else many, n=n, **kw)

    return plural


def value_label(value, datatype: str = "", lang: str = DEFAULT_LANG) -> str:
    """A gold value for readers: booleans as Sí/No (list membership comes out as true/false), dates in words, integral
    numbers without a trailing .0. Anything else is shown as exported."""
    if isinstance(value, bool):
        return ("Sí" if value else "No") if lang == "es" else ("Yes" if value else "No")
    if datatype == "xsd:date" and isinstance(value, str) and parse_ts(value):
        return date_label(value, lang)
    if isinstance(value, float) and value.is_integer() and datatype not in ("xsd:decimal", "xsd:double"):
        return str(int(value))
    return "" if value is None else str(value)


def parse_ts(value) -> datetime | None:
    if not value:
        return None
    try:
        ts = datetime.fromisoformat(str(value))
    except ValueError:
        return None
    return ts if ts.tzinfo else ts.replace(tzinfo=UTC)  # comparable with offset-aware timestamps


def date_label(value, lang: str = DEFAULT_LANG, with_time: bool = False) -> str:
    """'26 sep 2026' (es) or 'Sep 26, 2026' (en); the raw text when it is not an ISO timestamp."""
    ts = parse_ts(value)
    if ts is None:
        return str(value or "—")
    if lang == "es":
        out = f"{ts.day} {MONTHS_ES[ts.month - 1]} {ts.year}"
    else:
        out = f"{MONTHS_EN[ts.month - 1]} {ts.day}, {ts.year}"
    if with_time and (ts.hour or ts.minute):
        out += f", {ts:%H:%M}" + (" UTC" if ts.utcoffset() is not None and not ts.utcoffset() else "")
    return out
