"""Read-only gold probe for the real case: recompute the definition of done from gold/<case>/<run>/entities.jsonl,
independently of the engine's metrics.json, and spot-check that evidence points at real bronze.

    gold-probe.py [run_id]      (default: gold/<case_id>/latest.json)
"""

import json
import os
import random
import sys
from pathlib import Path

LOCAL = os.environ.get("PROBE_LOCAL")  # a directory with lake/ and case/ (fixture validation)
if LOCAL:
    CASE = os.path.join(LOCAL, "case")
    ROOT = os.path.join(LOCAL, "lake")
    CID = min(os.listdir(os.path.join(ROOT, "gold")))

    def get(key):
        path = os.path.join(ROOT, key)
        return Path(path).read_bytes() if os.path.isfile(path) else None

    def exists(key):
        return os.path.isfile(os.path.join(ROOT, key))
else:
    CASE = "/srv/proveedor-abierto/case"
    env = {}
    for line in Path("/opt/ontofill/engine.env").read_text().splitlines():
        if "=" in line and not line.startswith("#"):
            k, v = line.rstrip("\n").split("=", 1)
            env[k] = v.strip().strip('"')
    for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY"):
        os.environ[k] = env[k]
    import boto3
    import yaml

    lake = yaml.safe_load(Path("/srv/proveedor-abierto/lake.yaml").read_text())
    b = lake["bronze"]
    ep = b.get("endpoint") or env["LAKE_S3_ENDPOINT"]
    s3 = boto3.client("s3", endpoint_url=ep if str(ep).startswith("http") else "https://" + ep)
    BUCKET, CID = b["bucket"], lake["case_id"]

    def get(key):
        try:
            return s3.get_object(Bucket=BUCKET, Key=key)["Body"].read()
        except s3.exceptions.NoSuchKey:
            return None

    def exists(key):
        try:
            s3.head_object(Bucket=BUCKET, Key=key)
            return True
        except Exception:  # noqa: BLE001
            return False


run = sys.argv[1] if len(sys.argv) > 1 else json.loads(get(f"gold/{CID}/latest.json") or b"{}").get("run_id")
print("gold run:", run)
if not run:
    sys.exit(0)
base = f"gold/{CID}/{run}"
ents = [json.loads(ln) for ln in (get(f"{base}/entities.jsonl") or b"").splitlines() if ln.strip()]
onto = json.loads(get(f"{base}/ontology.json") or b"{}")
metrics = json.loads(get(f"{base}/metrics.json") or b"{}")
queries = json.loads(Path(f"{CASE}/02-ontology/dod-queries.json").read_text()).get("queries", [])
by_class = {}
for e in ents:
    by_class.setdefault(e.get("class"), []).append(e)
print("entities by class:", {k: len(v) for k, v in by_class.items()})
props = [p for p in onto.get("properties") or [] if isinstance(p, dict)]
dod_props = {}
for p in props:
    if p.get("dod"):
        dod_props.setdefault(p.get("domain"), []).append(p["id"])
print("DoD properties by class:", dod_props)
by_id = {e["id"]: e for e in ents}


def gold_field(e, pid):  # the engine's rule: status exactly "gold" with at least one evidence item
    f = (e.get("properties") or {}).get(pid) or {}
    return f.get("status") == "gold" and bool(f.get("evidence"))


primary = onto.get("primary_class")
rel_of = {q.get("criterion_id"): q.get("relation_id") for q in queries if q.get("relation_id")}
for q in queries:
    cid, agg, tgt, op = q.get("criterion_id"), q.get("aggregate"), q.get("target"), q.get("operator")
    cls = q.get("class_id") or q.get("class") or (primary if agg == "entities_meeting_completeness" else None)
    sel = [e for e in ents if not cls or e.get("class") == cls]
    listed = q.get("properties") or []
    actual = None
    if agg == "count_entities":
        actual = len(sel)
    elif agg == "count_entities_with_relation":
        rel = q["relation_id"]
        actual = sum(any(lk.get("property") == rel for lk in e.get("links") or []) for e in sel)
    elif agg == "count_entities_with_properties":
        ids = dod_props.get(cls, []) if listed == "dod" else listed
        actual = sum(all(gold_field(e, pid) for pid in ids) for e in sel)
    elif agg == "entities_meeting_completeness":
        ids = dod_props.get(cls, [])
        mr = q.get("min_ratio", 0.8)
        meets = lambda e, ids=ids, mr=mr: (
            bool(ids) and sum(gold_field(e, pid) for pid in ids) / len(ids) >= mr
        )
        if q.get("measure") == "share" or (q.get("measure") is None and tgt < 1):
            rel = q.get("relation_id") or next(iter(rel_of.values()), None)
            linked = [e for e in sel if any(lk.get("property") == rel for lk in e.get("links") or [])]
            actual = round(sum(map(meets, linked)) / len(linked), 3) if linked else 0.0
        else:
            actual = sum(map(meets, sel))
    elif agg == "count_values_without_evidence":
        actual = sum(
            1
            for e in sel
            for f in (e.get("properties") or {}).values()
            if f.get("status") == "gold" and not f.get("evidence")
        )
    elif agg == "count_distinct_source_classes":
        actual = len(
            {
                ev.get("source_type")
                for e in sel
                for f in (e.get("properties") or {}).values()
                if f.get("status") == "gold"
                for ev in f.get("evidence") or []
            }
        )
    engine = next((d for d in metrics.get("dod") or [] if d.get("criterion_id") == cid), {})
    agree = "OK" if engine and engine.get("actual") == actual else "DIFF"
    print(
        f"{cid} {agg}: probe={actual} target {op} {tgt} | engine={engine.get('actual')} met={engine.get('met')} [{agree}]"
    )

# per-property completeness for the core class
core = max(dod_props, key=lambda c: len(by_class.get(c, [])), default=None)
if core and by_class.get(core):
    pool = by_class[core]
    print(f"{core}: {len(pool)} entities; per-DoD-property gold coverage:")
    for pid in dod_props[core]:
        n = sum(1 for e in pool if gold_field(e, pid))
        print(f"   {pid}: {n}/{len(pool)} ({n / len(pool):.0%})")

# evidence spot check: the cited bronze exists
evs = [ev for e in ents for f in (e.get("properties") or {}).values() for ev in f.get("evidence") or []]
sample = random.Random(0).sample(evs, min(40, len(evs)))
missing = 0
for ev in sample:
    for key in (ev.get("bronze_key"), ev.get("screenshot_key")):
        if key and key.startswith("sha256:") and not exists("bronze/sha256/" + key.split(":", 1)[1]):
            missing += 1
print(f"evidence items: {len(evs)}; spot-checked {len(sample)}: {missing} bronze/screenshot keys missing")

# a few real rows for the video
for e in (by_class.get(core) or [])[:3]:
    row = {pid: (e["properties"].get(pid) or {}).get("value") for pid in dod_props.get(core, [])[:4]}
    ev = next((f["evidence"][0] for f in e["properties"].values() if f.get("evidence")), {})
    print("sample:", e["id"], row, "| evidence:", ev.get("url"), ev.get("selector"))
