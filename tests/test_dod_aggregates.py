"""The completeness page evaluates every aggregate the engine's DoD queries use (the approved case uses
count_entities_with_relation and a completeness share), as eval/gold_probe.py does, and an aggregate it does not know
reads as "not evaluable" instead of a 500. Live: the harness instance's /completeness returned 500."""

from proveedor_app import dod
from proveedor_app.domain import Domain

ONTO = {
    "primary_class": "supplier",
    "classes": [{"id": "supplier", "label": "Supplier"}, {"id": "contract", "label": "Contract"}],
    "properties": [
        {"id": "name", "domain": "supplier", "dod": True},
        {"id": "rfc", "domain": "supplier", "dod": True},
    ],
    "relations": [{"id": "awarded", "domain": "supplier", "range": "contract"}],
}
GOLD = {"status": "gold", "value": "x", "evidence": [{"url": "https://a.example/"}]}


def supplier(i, filled, linked):
    props = {"name": GOLD, "rfc": GOLD if filled else {"status": "missing"}}
    links = [{"property": "awarded", "target": "c1"}] if linked else []
    return {"id": f"s{i}", "class": "supplier", "properties": props, "links": links}


ENTS = [supplier(1, True, True), supplier(2, False, True), supplier(3, True, False)]
DOMAIN = Domain.from_ontology(ONTO)


def test_count_entities_with_relation():
    q = {"aggregate": "count_entities_with_relation", "class_id": "supplier", "relation_id": "awarded"}
    assert dod.evaluate_query(q, ENTS, DOMAIN) == 2


def test_completeness_below_one_is_a_share_of_linked_entities():
    q = {"aggregate": "entities_meeting_completeness", "class": "supplier", "properties": "dod", "min_ratio": 1.0,
         "target": 0.8}
    assert dod.evaluate_query(q, ENTS, DOMAIN, "awarded") == 0.5  # s1 of the linked s1, s2
    assert dod.evaluate_query({**q, "target": 2}, ENTS, DOMAIN, "awarded") == 2  # a count target stays a count


def test_an_unknown_aggregate_is_not_evaluable_not_a_crash():
    rows = dod.criteria({}, {}, DOMAIN, queries=[{"criterion_id": "d9", "aggregate": "made_up", "target": 1}],
                        entities=ENTS)
    assert rows[0]["actual"] is None and rows[0]["met"] is None and "not evaluable" in rows[0]["note"]
