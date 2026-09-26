"""Read-only access to the gold export.

Layout (same for S3 and a local directory):

    gold/<case_id>/latest.json            {"run_id": ...}
    gold/<case_id>/<run_id>/suppliers.jsonl
    gold/<case_id>/<run_id>/contracts.jsonl
    gold/<case_id>/<run_id>/trace.jsonl
    gold/<case_id>/<run_id>/metrics.json

Bronze objects (screenshots, raw captures) are addressed by `sha256:<hex>` keys and live in the same bucket
under `bronze_key_template` (default `bronze/sha256/{hex}`).
"""

from __future__ import annotations

import json
import os
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Protocol

import yaml

DEFAULT_BRONZE_TEMPLATE = "bronze/sha256/{hex}"


class Source(Protocol):
    def read(self, key: str) -> bytes | None: ...
    def list_dirs(self, prefix: str) -> list[str]: ...


class LocalSource:
    """A directory laid out like the bucket (fixtures, cached fallback run)."""

    def __init__(self, root: str | Path):
        self.root = Path(root).resolve()

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(f"key escapes root: {key}")
        return path

    def read(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.is_file() else None

    def list_dirs(self, prefix: str) -> list[str]:
        path = self._path(prefix)
        return sorted(p.name for p in path.iterdir() if p.is_dir()) if path.is_dir() else []

    def __repr__(self) -> str:
        return f"LocalSource({self.root})"


class S3Source:
    """Any S3 API (Vultr Object Storage, MinIO). Credentials come from the standard AWS_* env vars."""

    def __init__(self, bucket: str, endpoint: str | None = None, region: str | None = None):
        import boto3  # optional dependency: `uv sync --extra s3`

        if endpoint and not endpoint.startswith("http"):
            endpoint = f"https://{endpoint}"
        self.bucket = bucket
        self.client = boto3.client("s3", endpoint_url=endpoint, region_name=region)

    def read(self, key: str) -> bytes | None:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.client.exceptions.NoSuchKey:
            return None

    def list_dirs(self, prefix: str) -> list[str]:
        prefix = prefix.rstrip("/") + "/"
        pages = self.client.get_paginator("list_objects_v2").paginate(
            Bucket=self.bucket, Prefix=prefix, Delimiter="/"
        )
        return sorted(
            cp["Prefix"][len(prefix) :].rstrip("/") for page in pages for cp in page.get("CommonPrefixes", [])
        )

    def __repr__(self) -> str:
        return f"S3Source({self.bucket})"


def _jsonl(raw: bytes | None) -> list[dict]:
    if not raw:
        return []
    return [json.loads(line) for line in raw.decode("utf-8").splitlines() if line.strip()]


@dataclass
class ValueRef:
    """One field value of one supplier, indexed by its value_id."""

    value_id: str
    supplier_id: str
    field: str
    data: dict


@dataclass
class Run:
    """One gold export run, fully loaded and indexed."""

    case_id: str
    run_id: str
    suppliers: list[dict]
    contracts: list[dict]
    trace: list[dict]
    metrics: dict
    suppliers_by_id: dict[str, dict] = field(default_factory=dict)
    contracts_by_id: dict[str, dict] = field(default_factory=dict)
    values: dict[str, ValueRef] = field(default_factory=dict)
    steps_by_id: dict[str, dict] = field(default_factory=dict)
    steps_by_value: dict[str, list[dict]] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self.suppliers_by_id = {s["id"]: s for s in self.suppliers}
        self.contracts_by_id = {c["id"]: c for c in self.contracts}
        for s in self.suppliers:
            for name, f in (s.get("fields") or {}).items():
                if f.get("value_id"):
                    self.values[f["value_id"]] = ValueRef(f["value_id"], s["id"], name, f)
        for step in self.trace:
            self.steps_by_id[step["step_id"]] = step
            for vid in step.get("value_ids") or []:
                self.steps_by_value.setdefault(vid, []).append(step)

    def lineage(self, value_id: str) -> list[list[dict]]:
        """One chain per step that produced the value: that step, then its parent_step_id ancestors."""
        chains = []
        for step in self.steps_by_value.get(value_id, []):
            chain, seen, cur = [], set(), step
            while cur and cur["step_id"] not in seen:  # guard against cycles in a malformed trace
                seen.add(cur["step_id"])
                chain.append(cur)
                cur = self.steps_by_id.get(cur.get("parent_step_id") or "")
            chains.append(chain)
        return chains


class GoldStore:
    """Gold export for one case. Lookups that cannot be answered yet raise LookupError."""

    def __init__(
        self,
        source: Source,
        case_id: str | None = None,
        bronze_key_template: str = DEFAULT_BRONZE_TEMPLATE,
    ):
        self.source = source
        self.bronze_key_template = bronze_key_template
        self._case_id = case_id
        self._cache: dict[str, Run] = {}

    @property
    def case_id(self) -> str:
        if not self._case_id:  # resolved lazily: the bucket may hold no gold yet when the app starts
            self._case_id = self._detect_case_id()
        return self._case_id

    def _detect_case_id(self) -> str:
        cases = self.source.list_dirs("gold")
        if len(cases) != 1:
            raise LookupError(f"set PA_CASE_ID: found {len(cases)} cases under gold/ in {self.source!r}: {cases}")
        return cases[0]

    @property
    def prefix(self) -> str:
        return f"gold/{self.case_id}"

    def latest_run_id(self) -> str | None:
        raw = self.source.read(f"{self.prefix}/latest.json")
        return json.loads(raw)["run_id"] if raw else None

    def run_ids(self) -> list[str]:
        return self.source.list_dirs(self.prefix)

    def run(self, run_id: str | None = None) -> Run:
        run_id = run_id or self.latest_run_id()
        if not run_id:
            raise LookupError(f"no latest.json under {self.prefix} in {self.source!r}")
        if run_id not in self._cache:
            base = f"{self.prefix}/{run_id}"
            metrics_raw = self.source.read(f"{base}/metrics.json")
            self._cache[run_id] = Run(
                case_id=self.case_id,
                run_id=run_id,
                suppliers=_jsonl(self.source.read(f"{base}/suppliers.jsonl")),
                contracts=_jsonl(self.source.read(f"{base}/contracts.jsonl")),
                trace=_jsonl(self.source.read(f"{base}/trace.jsonl")),
                metrics=json.loads(metrics_raw) if metrics_raw else {},
            )
        return self._cache[run_id]

    def refresh(self) -> None:
        self._cache.clear()

    def _bronze_path(self, key: str) -> str | None:
        algo, _, hexdigest = key.partition(":")
        if algo != "sha256" or not hexdigest or not all(c in "0123456789abcdef" for c in hexdigest):
            return None
        return self.bronze_key_template.format(hex=hexdigest)

    def bronze(self, key: str) -> bytes | None:
        path = self._bronze_path(key)
        return self.source.read(path) if path else None

    def bronze_meta(self, key: str) -> dict:
        """Sidecar `<object>.meta.json`: {content_type, url, captured_at, source_id, step_id} (CONTRACT section 3)."""
        path = self._bronze_path(key)
        raw = self.source.read(f"{path}.meta.json") if path else None
        try:
            return json.loads(raw) if raw else {}
        except ValueError:
            return {}


def sniff_media_type(data: bytes) -> str:
    head = data[:512].lstrip()
    if head.startswith(b"\x89PNG"):
        return "image/png"
    if head.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if head[:4] == b"RIFF" and head[8:12] == b"WEBP":
        return "image/webp"
    if head.startswith(b"%PDF"):
        return "application/pdf"
    if head.startswith(b"<svg") or (head.startswith(b"<?xml") and b"<svg" in head):
        return "image/svg+xml"
    if head[:1] in (b"{", b"["):
        return "application/json"
    if head[:1] == b"<":
        return "text/plain; charset=utf-8"  # captured HTML is shown as text, never rendered in our origin
    return "application/octet-stream"


def load_store(repo_root: Path, env: dict[str, str] | None = None) -> GoldStore:
    """Pick the gold source: PA_GOLD_DIR (local layout) wins, else lake.yaml's bronze bucket over S3."""
    env = dict(os.environ if env is None else env)
    template = env.get("PA_BRONZE_KEY_TEMPLATE", DEFAULT_BRONZE_TEMPLATE)
    case_id = env.get("PA_CASE_ID") or None
    if env.get("PA_GOLD_DIR"):
        return GoldStore(LocalSource(env["PA_GOLD_DIR"]), case_id, template)
    lake_path = Path(env.get("PA_LAKE_YAML", repo_root / "lake.yaml"))
    if not lake_path.is_file():
        raise FileNotFoundError(
            f"no gold source: set PA_GOLD_DIR to a local export, or create {lake_path} (see lake.example.yaml)"
        )
    lake = yaml.safe_load(lake_path.read_text()) or {}
    bronze = lake.get("bronze") or {}
    case_id = case_id or lake.get("case_id")
    template = bronze.get("key_template", template)
    if bronze.get("kind") in ("file", "local"):  # local dev / cached fallback run, same layout as the bucket
        raw_root = os.path.expandvars(str(bronze.get("root") or bronze.get("path")))
        root = Path(raw_root.removeprefix("file://"))
        return GoldStore(LocalSource(root if root.is_absolute() else lake_path.parent / root), case_id, template)
    if bronze.get("kind") != "s3":
        raise ValueError(f"unsupported bronze kind in {lake_path}: {bronze.get('kind')!r}")
    endpoint = env.get(bronze["endpoint_env"]) if bronze.get("endpoint_env") else bronze.get("endpoint")
    source = S3Source(bronze["bucket"], endpoint, bronze.get("region") or env.get("AWS_REGION"))
    return GoldStore(source, case_id, template)


def iter_evidence(field_data: dict) -> Iterable[dict]:
    return field_data.get("evidence") or []


class UnavailableStore:
    """Stands in when no gold source is configured yet (the approver URL must work before any gold exists)."""

    def __init__(self, reason: str):
        self.reason = reason
        self.case_id = "no-case"

    def run(self, run_id: str | None = None) -> Run:
        raise LookupError(self.reason)

    def run_ids(self) -> list[str]:
        return []

    def refresh(self) -> None:
        pass

    def bronze(self, key: str) -> bytes | None:
        return None

    def bronze_meta(self, key: str) -> dict:
        return {}
