import os
from typing import Any

from .confidence import RULE_VERSION, apply_confidence
from .extractor import extract_evidence_chunks, extract_nodes, extract_relation_candidates
from .neo4j_store import Neo4jGraphStore
from .normalizer import normalize_entities
from .schema import GraphPayload, RelationCandidate


def build_graph_payload(insight_payload: dict[str, Any]) -> dict[str, Any]:
    raw_nodes = extract_nodes(insight_payload)
    normalization_index, graph_nodes, mention_to_id = normalize_entities(raw_nodes)
    evidence_chunks = extract_evidence_chunks(insight_payload)
    relation_candidates = [
        apply_confidence(relation, evidence_chunks)
        for relation in extract_relation_candidates(insight_payload, mention_to_id, evidence_chunks)
    ]
    graph_edges = _graph_edges(relation_candidates)
    company_edges = _edges_by_kind(graph_edges, "company")
    profile_edges = _edges_by_kind(graph_edges, "profile")
    structural_edges = _edges_by_kind(graph_edges, "structural")

    payload = GraphPayload(
        task_profile=insight_payload.get("task_profile") or {},
        graph_nodes=graph_nodes,
        relation_candidates=relation_candidates,
        graph_edges=graph_edges,
        company_edges=company_edges,
        profile_edges=profile_edges,
        structural_edges=structural_edges,
        inter_company_relations=company_edges,
        evidence_chunks=evidence_chunks,
        normalization_index=normalization_index,
        confidence_meta=_confidence_meta(relation_candidates, graph_edges),
        qa_index_hints=_qa_index_hints(graph_nodes, graph_edges, evidence_chunks),
    )
    return payload.to_dict()


def persist_graph_payload_if_enabled(graph_payload: dict[str, Any]) -> dict[str, Any]:
    if str(os.getenv("GRAPH_AUTO_PERSIST", "true")).strip().lower() in {"false", "0", "no", "off"}:
        graph_payload["persistence_meta"] = {
            "enabled": False,
            "status": "skipped",
            "reason": "graph_auto_persist_disabled",
        }
        return graph_payload

    neo4j_uri = str(os.getenv("NEO4J_URI") or "").strip()
    if not neo4j_uri:
        graph_payload["persistence_meta"] = {
            "enabled": False,
            "status": "skipped",
            "reason": "missing_neo4j_uri",
        }
        return graph_payload

    store = None
    try:
        store = Neo4jGraphStore(
            uri=neo4j_uri,
            user=str(os.getenv("NEO4J_USER") or "neo4j"),
            password=str(os.getenv("NEO4J_PASSWORD") or "password"),
        )
        result = store.persist_graph_payload(graph_payload)
        graph_payload["persistence_meta"] = {
            "enabled": True,
            "status": "persisted",
            **result,
        }
    except Exception as exc:
        graph_payload["persistence_meta"] = {
            "enabled": True,
            "status": "failed",
            "error": str(exc),
        }
    finally:
        if store is not None:
            store.close()
    return graph_payload


def _graph_edges(candidates: list[RelationCandidate]) -> list[RelationCandidate]:
    return [relation for relation in candidates if relation.status in {"verified", "strong_candidate"}]


def _edges_by_kind(edges: list[RelationCandidate], edge_kind: str) -> list[RelationCandidate]:
    return [relation for relation in edges if relation.edge_kind == edge_kind]


def _confidence_meta(candidates: list[RelationCandidate], edges: list[RelationCandidate]) -> dict[str, Any]:
    status_counts: dict[str, int] = {}
    for relation in candidates:
        status_counts[relation.status] = status_counts.get(relation.status, 0) + 1
    return {
        "rule_version": RULE_VERSION,
        "candidate_count": len(candidates),
        "edge_count": len(edges),
        "status_counts": status_counts,
        "edge_statuses": ["verified", "strong_candidate"],
    }


def _qa_index_hints(graph_nodes, graph_edges, evidence_chunks) -> dict[str, Any]:
    return {
        "industries": [node.name for node in graph_nodes if node.node_type == "Industry"],
        "companies": [node.name for node in graph_nodes if node.node_type == "Company"],
        "relations": sorted({edge.relation for edge in graph_edges}),
        "evidence_count": len(evidence_chunks),
    }
