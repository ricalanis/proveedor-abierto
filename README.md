# Proveedor Abierto (working name)

Anti-corruption application built on the Ontofill engine. Starts from one open question, no dataset:

> "Who receives public money in Mexico through government contracts, and are they legitimate companies?"

Running the engine (repo 1) on `case/` is what "the application" means. The app layer reads gold from the external lake.

| Folder | What goes there |
|--------|-----------------|
| `case/` | The case package: versioned definition of the case, as text files in git (forkable) |
| `app/` | Investigation tools: dossier, red-flag explainer, relationship view, case journal, watchlist/export |
| `lake.example.yaml` | Pointer to the external Vultr lake (copy to `lake.yaml`, no secrets) |
| `docs/` | Definition docs (copied from planning) |

Code: Apache-2.0. Case package (PRD, ontology): CC-BY. No data in git. Public sources only, no logins.
