"""Common tree for engine taxonomies (ontology.json) and reference classifications (references/*.yaml),
plus a deterministic label matcher.

The matcher is a proxy for Simula's LLM critic: normalized exact match on labels, ids and aliases, then token
Jaccard over content words. It has no embeddings and no translation beyond the aliases a reference lists, so a
correct engine node phrased differently (e.g. "Public works" vs "Construcción") can go unmatched. Treat its gaps
as prompts for a human look, not verdicts.
"""

from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path

import yaml

STOPWORDS = {
    # Spanish
    "de", "del", "la", "las", "el", "los", "y", "e", "o", "u", "a", "al", "en", "por", "con", "para", "un", "una",
    "sus", "su", "que", "se",
    # English
    "the", "and", "of", "for", "to", "at", "or", "in", "an", "on", "with", "by",
}


def normalize(text: str) -> str:
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def tokens(text: str) -> frozenset[str]:
    return frozenset(t for t in normalize(text).split() if t not in STOPWORDS)


@dataclass
class Node:
    id: str
    label: str
    level: int
    critic_label: str | None = None
    code: str | None = None
    aliases: list[str] = field(default_factory=list)
    children: list[Node] = field(default_factory=list)

    @property
    def variants(self) -> list[str]:
        return [self.label, self.id.replace("_", " "), *self.aliases]

    def walk(self):
        yield self
        for child in self.children:
            yield from child.walk()


@dataclass
class Tree:
    name: str
    nodes: list[Node]  # top-level nodes (level 1); the root itself is not scored
    meta: dict = field(default_factory=dict)

    def all_nodes(self) -> list[Node]:
        return [n for top in self.nodes for n in top.walk()]


def _engine_node(raw: dict, level: int) -> Node:
    return Node(id=raw["id"], label=raw.get("label", raw["id"]), level=raw.get("level", level),
                critic_label=raw.get("critic_label"),
                children=[_engine_node(c, level + 1) for c in raw.get("children") or []])


def load_engine_taxonomies(ontology_path: Path | str) -> list[tuple[str, Tree]]:
    """(factor_id, tree) for each taxonomy in an engine ontology.json."""
    doc = json.loads(Path(ontology_path).read_text())
    out = []
    for tax in doc.get("taxonomies") or []:
        tree = Tree(name=tax.get("root_label", tax.get("factor_id", "?")),
                    nodes=[_engine_node(c, 1) for c in tax.get("children") or []],
                    meta={k: tax.get(k) for k in ("soundness", "coverage", "root_id")})
        out.append((tax.get("factor_id", ""), tree))
    return out


def _ref_node(raw: dict, level: int) -> Node:
    return Node(id=raw["id"], label=raw["label"], level=level, code=raw.get("code"),
                aliases=list(raw.get("aliases") or []),
                children=[_ref_node(c, level + 1) for c in raw.get("children") or []])


REQUIRED_META = ("name", "publisher", "source_url", "license", "retrieved_at", "verified", "notes", "nodes")


def load_reference(path: Path | str) -> Tree:
    doc = yaml.safe_load(Path(path).read_text())
    missing = [k for k in REQUIRED_META if k not in doc]
    if missing:
        raise ValueError(f"{path}: reference is missing metadata {missing}")
    meta = {k: v for k, v in doc.items() if k != "nodes"}
    return Tree(name=doc["name"], nodes=[_ref_node(n, 1) for n in doc["nodes"]], meta=meta)


def reference_as_engine(ref: Tree) -> Tree:
    """A reference dressed as an engine taxonomy whose critic accepted everything (for self-checks)."""
    def conv(n: Node) -> Node:
        return Node(id=n.id, label=n.label, level=n.level, critic_label="Good-Overlapping",
                    children=[conv(c) for c in n.children])
    return Tree(name=ref.name, nodes=[conv(n) for n in ref.nodes])


def similarity(a: Node, b: Node) -> tuple[float, str]:
    """Best match between any label/id/alias of a and of b: (score, method)."""
    best = (0.0, "none")
    for va in a.variants:
        na, ta = normalize(va), tokens(va)
        for vb in b.variants:
            if na and na == normalize(vb):
                return 1.0, "exact"
            tb = tokens(vb)
            if ta and tb:
                j = len(ta & tb) / len(ta | tb)
                if j > best[0]:
                    best = (j, "jaccard")
    return best
