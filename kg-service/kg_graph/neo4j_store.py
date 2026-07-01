from __future__ import annotations

import re
from typing import Any


EDGE_STATUSES = {"verified", "strong_candidate"}


def sanitize_relation_type(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "_", str(value or "").strip()).strip("_").upper()
    if not cleaned:
        return "RELATED_TO"
    if not re.match(r"^[A-Z_]", cleaned):
        cleaned = f"REL_{cleaned}"
    return cleaned


def _sanitize_label(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9_]+", "", str(value or "").strip())
    return cleaned or "GraphNode"


class Neo4jGraphStore:
    def __init__(
        self,
        uri: str = "",
        user: str = "neo4j",
        password: str = "password",
        driver: Any | None = None,
    ):
        if driver is not None:
            self._driver = driver
            return

        from neo4j import GraphDatabase

        self._driver = GraphDatabase.driver(uri, auth=(user, password))

    def close(self) -> None:
        close = getattr(self._driver, "close", None)
        if callable(close):
            close()

    def init_schema(self) -> None:
        with self._driver.session() as session:
            self._init_schema(session)

    def persist_graph_payload(self, graph_payload: dict[str, Any]) -> dict[str, int]:
        graph_nodes = list(graph_payload.get("graph_nodes") or [])
        evidence_chunks = list(graph_payload.get("evidence_chunks") or [])
        graph_edges = [
            relation
            for relation in graph_payload.get("graph_edges") or []
            if str(relation.get("status") or "") in EDGE_STATUSES
        ]

        with self._driver.session() as session:
            self._init_schema(session)
            for node in graph_nodes:
                self._upsert_node(session, node)
            for chunk in evidence_chunks:
                self._upsert_evidence(session, chunk)
            for relation in graph_edges:
                self._upsert_relation(session, relation)

        return {
            "node_count": len(graph_nodes),
            "edge_count": len(graph_edges),
            "evidence_count": len(evidence_chunks),
        }

    def _init_schema(self, session: Any) -> None:
        constraints = (
            ("Industry", "node_id"),
            ("Segment", "node_id"),
            ("Subsegment", "node_id"),
            ("Company", "node_id"),
            ("BusinessLine", "node_id"),
            ("Product", "node_id"),
            ("Technology", "node_id"),
            ("Source", "node_id"),
            ("EvidenceChunk", "chunk_id"),
            ("RelationFact", "rel_id"),
        )
        for label, prop in constraints:
            session.run(
                f"CREATE CONSTRAINT {label.lower()}_{prop}_unique IF NOT EXISTS "
                f"FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
            )

    def _upsert_node(self, session: Any, node: dict[str, Any]) -> None:
        label = _sanitize_label(str(node.get("node_type") or "GraphNode"))
        node_id = str(node.get("node_id") or "").strip()
        if not node_id:
            return

        properties = {
            "node_id": node_id,
            "name": str(node.get("name") or "").strip(),
            "normalized_name": str(node.get("normalized_name") or "").strip(),
            "aliases": list(node.get("aliases") or []),
            "source_refs": list(node.get("source_refs") or []),
            "raw_mentions": list(node.get("raw_mentions") or []),
            "normalization_method": str(node.get("normalization_method") or "").strip(),
        }
        session.run(
            f"""
            MERGE (n:{label} {{node_id: $node_id}})
            SET n += $properties
            """,
            {"node_id": node_id, "properties": properties},
        )

    def _upsert_evidence(self, session: Any, chunk: dict[str, Any]) -> None:
        chunk_id = str(chunk.get("chunk_id") or "").strip()
        if not chunk_id:
            return

        source_url = str(chunk.get("source_url") or "").strip()
        properties = {
            "chunk_id": chunk_id,
            "text": str(chunk.get("text") or "").strip(),
            "source_url": source_url,
            "source_title": str(chunk.get("source_title") or "").strip(),
            "source_grade": str(chunk.get("source_grade") or "").strip(),
        }
        session.run(
            """
            MERGE (e:EvidenceChunk {chunk_id: $chunk_id})
            SET e += $properties
            """,
            {"chunk_id": chunk_id, "properties": properties},
        )
        if source_url:
            source_node_id = f"source:{source_url}"
            session.run(
                """
                MERGE (s:Source {node_id: $source_node_id})
                SET s.name = $source_url,
                    s.normalized_name = $source_url,
                    s.source_refs = [$source_url]
                WITH s
                MATCH (e:EvidenceChunk {chunk_id: $chunk_id})
                MERGE (e)-[:FROM_SOURCE]->(s)
                """,
                {"source_node_id": source_node_id, "source_url": source_url, "chunk_id": chunk_id},
            )

    def _upsert_relation(self, session: Any, relation: dict[str, Any]) -> None:
        rel_id = str(relation.get("rel_id") or "").strip()
        head = str(relation.get("head") or "").strip()
        tail = str(relation.get("tail") or "").strip()
        if not rel_id or not head or not tail:
            return

        rel_type = sanitize_relation_type(str(relation.get("relation") or "RELATED_TO"))
        properties = {
            "rel_id": rel_id,
            "relation": str(relation.get("relation") or "").strip(),
            "relation_name": str(relation.get("relation_name") or "").strip(),
            "relation_level": str(relation.get("relation_level") or "").strip(),
            "relation_origin": str(relation.get("relation_origin") or "").strip(),
            "direction": str(relation.get("direction") or "").strip(),
            "explanation": str(relation.get("explanation") or "").strip(),
            "edge_kind": str(relation.get("edge_kind") or "").strip(),
            "confidence": float(relation.get("confidence") or 0.0),
            "status": str(relation.get("status") or "").strip(),
            "evidence_text": str(relation.get("evidence_text") or "").strip(),
            "evidence_refs": list(relation.get("evidence_refs") or []),
            "source_url": str(relation.get("source_url") or "").strip(),
            "source_grade": str(relation.get("source_grade") or "").strip(),
            "field_name": str(relation.get("field_name") or ""),
            "field_value": str(relation.get("field_value") or ""),
        }

        session.run(
            f"""
            MATCH (h {{node_id: $head}})
            MATCH (t {{node_id: $tail}})
            MERGE (h)-[r:{rel_type} {{rel_id: $rel_id}}]->(t)
            SET r += $properties
            """,
            {"head": head, "tail": tail, "rel_id": rel_id, "properties": properties},
        )
        session.run(
            """
            MATCH (h {node_id: $head})
            MATCH (t {node_id: $tail})
            MERGE (rf:RelationFact {rel_id: $rel_id})
            SET rf += $properties
            MERGE (h)-[:HAS_RELATION_FACT]->(rf)
            MERGE (rf)-[:RELATION_TARGET]->(t)
            """,
            {"head": head, "tail": tail, "rel_id": rel_id, "properties": properties},
        )
        for chunk_id in properties["evidence_refs"]:
            session.run(
                """
                MATCH (rf:RelationFact {rel_id: $rel_id})
                MATCH (e:EvidenceChunk {chunk_id: $chunk_id})
                MERGE (rf)-[:SUPPORTED_BY]->(e)
                """,
                {"rel_id": rel_id, "chunk_id": chunk_id},
            )
