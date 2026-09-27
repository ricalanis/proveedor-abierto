"""The case's domain, read from its approved ontology (CONTRACT v0.7 §11/§11a).

The app is the anti-corruption application, but it takes every domain word from the ontology: which class a
dossier is about (`primary_class`), property labels and order, which properties count toward the definition of
done, relation labels, the rules behind signals, and source-class labels. Nothing below names a supplier field;
the only procurement vocabulary is `LEGACY_ONTOLOGY`, which describes the pre-§11 export layout for the adapter.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

DEFAULT_DOD_THRESHOLD = 0.8  # used when the DoD criteria do not state the per-entity share; labelled in the UI


def humanize(ident: str) -> str:
    return (ident or "").replace("_", " ").replace("-", " ").strip().capitalize()


@dataclass
class Prop:
    id: str
    label: str
    datatype: str = ""
    domain: str | None = None
    dod: bool = False
    order: int = 1000
    description: str = ""
    aligned_to: str | None = None


@dataclass
class Domain:
    primary_class: str
    classes: dict[str, dict] = field(default_factory=dict)
    properties: dict[str, list[Prop]] = field(default_factory=dict)  # class id -> ordered properties
    relations: dict[str, dict] = field(default_factory=dict)
    rules: dict[str, dict] = field(default_factory=dict)
    source_classes: dict[str, str] = field(default_factory=dict)
    dod_threshold: float = DEFAULT_DOD_THRESHOLD
    threshold_stated: bool = False
    legacy: bool = False
    raw: dict = field(default_factory=dict, repr=False, compare=False)  # the ontology this was built from
    _localized: dict = field(default_factory=dict, repr=False, compare=False)

    def localized(self, lang: str) -> Domain:
        """The same domain with the app's own labels for `lang` (i18n.ONTOLOGY_LABELS, keyed by ontology id) where it
        has them; everything else keeps the export's text."""
        if lang not in self._localized:
            from .i18n import ONTOLOGY_LABELS

            onto = localize_ontology(self.raw, ONTOLOGY_LABELS.get(lang) or {})
            if onto is self.raw:
                self._localized[lang] = self
            else:
                d = Domain.from_ontology(onto, legacy=self.legacy)
                d.dod_threshold, d.threshold_stated = self.dod_threshold, self.threshold_stated
                self._localized[lang] = d
        return self._localized[lang]

    # labels ---------------------------------------------------------------------------------------------------
    def class_label(self, cls: str | None = None, plural: bool = False) -> str:
        c = self.classes.get(cls or self.primary_class) or {}
        if plural:
            return c.get("label_plural") or (c.get("label") or humanize(cls or self.primary_class)) + "s"
        return c.get("label") or humanize(cls or self.primary_class)

    def props(self, cls: str | None = None) -> list[Prop]:
        return self.properties.get(cls or self.primary_class, [])

    def dod_props(self, cls: str | None = None) -> list[Prop]:
        return [p for p in self.props(cls) if p.dod]

    def prop_label(self, prop_id: str, cls: str | None = None) -> str:
        for p in self.props(cls) if cls else [q for ps in self.properties.values() for q in ps]:
            if p.id == prop_id:
                return p.label
        return humanize(prop_id)

    def relation_label(self, rel_id: str) -> str:
        return (self.relations.get(rel_id) or {}).get("label") or humanize(rel_id)

    def source_label(self, source_class: str | None) -> str:
        return self.source_classes.get(source_class or "") or humanize(source_class or "")

    def title_property(self, cls: str | None = None) -> str | None:
        c = self.classes.get(cls or self.primary_class) or {}
        if c.get("title_property"):
            return c["title_property"]
        props = self.props(cls)
        return props[0].id if props else None

    def identifier_property(self, cls: str | None = None) -> str | None:
        return (self.classes.get(cls or self.primary_class) or {}).get("identifier_property")

    def rule(self, rule_id: str, label: str = "") -> dict:
        r = self.rules.get(rule_id) or {}
        return {"label": r.get("label") or label or humanize(rule_id), "checks": r.get("checks") or label or rule_id,
                "verify": list(r.get("verify") or [])}

    def peer_relations(self) -> list[str]:
        """Relations between two entities of the primary class (drawn in the relationship view)."""
        return [rid for rid, r in self.relations.items()
                if (r.get("domain") in (None, self.primary_class)) and (r.get("range") in (None, self.primary_class))]

    # building ---------------------------------------------------------------------------------------------------
    @classmethod
    def from_ontology(cls, onto: dict, legacy: bool = False) -> Domain:
        classes = {c["id"]: c for c in onto.get("classes") or [] if isinstance(c, dict) and c.get("id")}
        primary = onto.get("primary_class") or next((cid for cid, c in classes.items() if c.get("primary")), None) \
            or next(iter(classes), "entity")
        props: dict[str, list[Prop]] = {}
        for i, p in enumerate(onto.get("properties") or []):
            if not isinstance(p, dict) or not p.get("id"):
                continue
            dom = p.get("domain") or primary
            props.setdefault(dom, []).append(Prop(
                id=p["id"], label=p.get("label") or humanize(p["id"]), datatype=p.get("datatype") or "",
                domain=dom, dod=bool(p.get("dod")), order=int(p.get("order", 1000 + i)),
                description=p.get("description") or "", aligned_to=p.get("aligned_to")))
        for plist in props.values():
            plist.sort(key=lambda p: p.order)
        relations = {r["id"]: r for r in onto.get("relations") or [] if isinstance(r, dict) and r.get("id")}
        rules = {r["id"]: r for r in onto.get("rules") or [] if isinstance(r, dict) and r.get("id")}
        sources = {s["id"]: s.get("label") or humanize(s["id"]) for s in onto.get("source_classes") or []
                   if isinstance(s, dict) and s.get("id")}
        threshold = onto.get("dod_threshold")
        return cls(primary_class=primary, classes=classes, properties=props, relations=relations, rules=rules,
                   source_classes=sources, dod_threshold=float(threshold) if threshold else DEFAULT_DOD_THRESHOLD,
                   threshold_stated=threshold is not None, legacy=legacy, raw=onto)

    def usable(self) -> bool:
        return bool(self.props())


LOCALIZABLE = ("label", "label_plural", "description", "checks", "verify")
_ONTOLOGY_LISTS = ("classes", "properties", "relations", "rules", "source_classes")


def localize_ontology(onto: dict, labels: dict[str, dict]) -> dict:
    """Overlay translated text by ontology id ({id: {label, label_plural, description, checks, verify}}) without
    changing the export's shape. Unchanged input comes back as is."""
    out, changed = dict(onto), False
    for key in _ONTOLOGY_LISTS:
        items = []
        for item in onto.get(key) or []:
            extra = labels.get(item.get("id")) if isinstance(item, dict) else None
            if extra:
                item = {**item, **{k: v for k, v in extra.items() if k in LOCALIZABLE and v}}
                changed = True
            items.append(item)
        out[key] = items
    return out if changed else onto


# The pre-§11 export layout (suppliers.jsonl + contracts.jsonl), described as an ontology so the same screens can
# read it through the adapter until the engine's §11 export lands.
LEGACY_ONTOLOGY = {
    "primary_class": "supplier",
    "classes": [
        {"id": "supplier", "label": "Supplier", "label_plural": "Suppliers", "title_property": "legal_name",
         "identifier_property": "tax_id", "description": "A legal entity that received a public contract",
         "aligned_to": "https://schema.org/Organization"},
        {"id": "contract", "label": "Contract", "label_plural": "Contracts", "title_property": "title",
         "identifier_property": "title", "description": "A public contract awarded to one or more suppliers",
         "aligned_to": "https://standard.open-contracting.org/latest/en/schema/reference/#contract"},
    ],
    "properties": [
        {"id": "legal_name", "description": "Recorded value of this property", "label": "Legal name", "domain": "supplier", "dod": True, "order": 1,
         "datatype": "xsd:string", "aligned_to": "https://schema.org/legalName"},
        {"id": "tax_id", "description": "Recorded value of this property", "label": "Tax ID (RFC)", "domain": "supplier", "dod": True, "order": 2,
         "datatype": "xsd:string", "aligned_to": "https://schema.org/taxID"},
        {"id": "address", "description": "Recorded value of this property", "label": "Address", "domain": "supplier", "dod": True, "order": 3,
         "datatype": "xsd:string", "aligned_to": "https://schema.org/address"},
        {"id": "founding_date", "description": "Recorded value of this property", "label": "Founding date", "domain": "supplier", "dod": True, "order": 4,
         "datatype": "xsd:date", "aligned_to": "https://schema.org/foundingDate"},
        {"id": "tax_list_status", "description": "Recorded value of this property", "label": "Tax-list status", "domain": "supplier", "dod": True, "order": 5,
         "datatype": "xsd:string", "aligned_to": None},
        {"id": "sanction_status", "description": "Recorded value of this property", "label": "Sanction status", "domain": "supplier", "dod": True, "order": 6,
         "datatype": "xsd:string", "aligned_to": None},
        {"id": "legal_representative", "description": "Recorded value of this property", "label": "Legal representative", "domain": "supplier", "order": 7,
         "datatype": "xsd:string", "aligned_to": None, "dod": False},
        {"id": "title", "description": "Recorded value of this property", "label": "Contract", "domain": "contract", "order": 1, "datatype": "xsd:string", "aligned_to": None, "dod": False},
        {"id": "buyer", "description": "Recorded value of this property", "label": "Buyer", "domain": "contract", "order": 2, "datatype": "xsd:string", "aligned_to": None, "dod": False},
        {"id": "procedure_type", "description": "Recorded value of this property", "label": "Procedure", "domain": "contract", "order": 3, "datatype": "xsd:string", "aligned_to": None, "dod": False},
        {"id": "date", "description": "Recorded value of this property", "label": "Date", "domain": "contract", "order": 4, "datatype": "xsd:date", "aligned_to": None, "dod": False},
        {"id": "amount", "description": "Recorded value of this property", "label": "Amount", "domain": "contract", "order": 5, "datatype": "xsd:decimal", "aligned_to": None, "dod": False},
        {"id": "currency", "description": "Recorded value of this property", "label": "Currency", "domain": "contract", "order": 6, "datatype": "xsd:string", "aligned_to": None, "dod": False},
    ],
    "relations": [
        {"id": "shared_address", "label": "Shared address", "domain": "supplier", "range": "supplier", "symmetric": True},
        {"id": "shared_representative", "label": "Shared legal representative", "domain": "supplier",
         "range": "supplier", "symmetric": True},
        {"id": "same_procedure", "label": "Same procedure", "domain": "supplier", "range": "supplier", "symmetric": True},
        {"id": "awarded", "label": "Contracts", "domain": "supplier", "range": "contract", "symmetric": False},
    ],
    "rules": [
        {"id": "tax_list_listed", "label": "Listed on the tax authority's fake-invoice list",
         "checks": "Whether the supplier's RFC appears on the tax authority's published list of companies presumed "
                   "or confirmed to issue invoices for simulated operations.",
         "verify": ["Open the list capture and confirm the RFC matches exactly (not a similar name).",
                    "Check the listing stage: 'presunto' can still be rebutted; 'definitivo' is a final finding.",
                    "Compare the listing date with the contract dates."]},
        {"id": "sanctioned_supplier", "label": "Appears in the sanctioned-supplier registry",
         "checks": "Whether the supplier appears in the registry of sanctioned suppliers.",
         "verify": ["Confirm the registry entry refers to this legal entity (RFC, not only the name).",
                    "Check the sanction's start and end dates and whether it covers the contracting agency.",
                    "Look for a later court decision that suspends the sanction."]},
        {"id": "founded_shortly_before_award", "label": "Created shortly before its first award",
         "checks": "Whether the company was founded within a year before its first recorded public contract.",
         "verify": ["Confirm the founding date in the company registry or official gazette capture.",
                    "Check the procedure's experience requirements and whether the company met them.",
                    "Look for a predecessor company with the same partners or address."]},
        {"id": "shared_address_bidders", "label": "Shares an address with another bidder in the same procedure",
         "checks": "Whether two participants in the same procedure declare the same address.",
         "verify": ["Compare both address captures character by character.",
                    "Check whether the address is a large office building or a business centre.",
                    "Look for shared representatives, partners or phone numbers between the two companies."]},
    ],
    "source_classes": [
        {"id": "procurement_portal", "label": "Procurement portal"},
        {"id": "tax_authority_list", "label": "Tax authority list"},
        {"id": "sanctions_registry", "label": "Sanctions registry"},
        {"id": "company_registry", "label": "Company registry"},
        {"id": "official_gazette", "label": "Official gazette"},
    ],
}


def legacy_to_entities(suppliers: list[dict], contracts: list[dict]) -> list[dict]:
    """The adapter: pre-§11 supplier/contract rows as §11 entities (see LEGACY_ONTOLOGY)."""
    entities = []
    title_vid = {}
    for c in contracts:
        slug = re.sub(r"[^A-Za-z0-9._:-]", "-", c["id"].split(":", 1)[-1])
        props = {}
        for key in ("title", "buyer", "procedure_type", "date", "amount", "currency"):
            if c.get(key) is not None:
                props[key] = {"value_id": f"val:contract-{slug}-{key}", "value": c[key], "confidence": 1.0,
                              "status": "gold", "evidence": c.get("evidence") or [],
                              **({"generated_by": c["generated_by"]} if c.get("generated_by") else {})}
        title_vid[c["id"]] = props.get("title", {}).get("value_id")
        entities.append({"id": c["id"], "class": "contract", "classified_as": [], "properties": props,
                         "links": [{"property": "awarded_to", "target": sid, "via_value_id": title_vid[c["id"]]}
                                   for sid in c.get("supplier_ids") or []],
                         "flags": [], **({"generated_by": c["generated_by"]} if c.get("generated_by") else {})})
    for s in suppliers:
        links = [{"property": link["type"], "target": link["target"], "via_value_id": link.get("via_value_id")}
                 for link in s.get("links") or []]
        links += [{"property": "awarded", "target": cid, "via_value_id": title_vid.get(cid)}
                  for cid in s.get("contract_ids") or []]
        entities.append({"id": s["id"], "class": "supplier", "classified_as": s.get("classified_as") or [],
                         "properties": s.get("fields") or {}, "links": links, "flags": s.get("flags") or [],
                         **({"generated_by": s["generated_by"]} if s.get("generated_by") else {})})
    return entities
