import unittest

from tests.test_graph_extractor import sample_insight_payload


class FakeSession:
    def __init__(self, calls):
        self.calls = calls

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def run(self, cypher, parameters=None, **kwargs):
        params = parameters or kwargs
        self.calls.append((cypher, params))


class FakeDriver:
    def __init__(self):
        self.calls = []
        self.closed = False

    def session(self):
        return FakeSession(self.calls)

    def close(self):
        self.closed = True


class Neo4jGraphStoreTests(unittest.TestCase):
    def test_sanitize_relation_type_uses_safe_uppercase_identifier(self):
        from kg_graph.neo4j_store import sanitize_relation_type

        self.assertEqual(sanitize_relation_type("vehicle_battery_supply"), "VEHICLE_BATTERY_SUPPLY")
        self.assertEqual(sanitize_relation_type("bad relation-1"), "BAD_RELATION_1")
        self.assertEqual(sanitize_relation_type("123 relation"), "REL_123_RELATION")
        self.assertEqual(sanitize_relation_type(""), "RELATED_TO")

    def test_persist_graph_payload_writes_nodes_edges_relation_facts_and_evidence_links(self):
        from kg_graph.builder import build_graph_payload
        from kg_graph.neo4j_store import Neo4jGraphStore

        graph_payload = build_graph_payload(sample_insight_payload())
        fake_driver = FakeDriver()
        store = Neo4jGraphStore(driver=fake_driver)

        result = store.persist_graph_payload(graph_payload)
        combined_cypher = "\n".join(cypher for cypher, _params in fake_driver.calls)

        self.assertEqual(result["node_count"], len(graph_payload["graph_nodes"]))
        self.assertEqual(result["edge_count"], len(graph_payload["graph_edges"]))
        self.assertIn("CREATE CONSTRAINT", combined_cypher)
        self.assertIn("RelationFact", combined_cypher)
        self.assertIn("SUPPORTED_BY", combined_cypher)
        self.assertIn("FROM_SOURCE", combined_cypher)
        self.assertIn("VEHICLE_BATTERY_SUPPLY", combined_cypher)

        store.close()
        self.assertTrue(fake_driver.closed)

    def test_relation_fact_persists_field_metadata(self):
        from kg_graph.neo4j_store import Neo4jGraphStore

        graph_payload = {
            "graph_nodes": [
                {"node_id": "Company:catl", "node_type": "Company", "name": "宁德时代"},
                {"node_id": "BusinessLine:battery", "node_type": "BusinessLine", "name": "动力电池业务"},
            ],
            "evidence_chunks": [
                {
                    "chunk_id": "evidence:1",
                    "text": "宁德时代主营动力电池业务。",
                    "source_url": "https://example.com/catl",
                    "source_title": "宁德时代年报",
                    "source_grade": "A",
                }
            ],
            "graph_edges": [
                {
                    "rel_id": "rel:1",
                    "head": "Company:catl",
                    "head_type": "Company",
                    "relation": "company_has_business_line",
                    "tail": "BusinessLine:battery",
                    "tail_type": "BusinessLine",
                    "edge_kind": "profile",
                    "status": "verified",
                    "confidence": 0.92,
                    "evidence_refs": ["evidence:1"],
                    "evidence_text": "宁德时代主营动力电池业务。",
                    "source_url": "https://example.com/catl",
                    "source_grade": "A",
                    "field_name": "business_lines",
                    "field_value": "动力电池业务",
                }
            ],
        }

        fake_driver = FakeDriver()
        store = Neo4jGraphStore(driver=fake_driver)
        store.persist_graph_payload(graph_payload)

        relation_params = [
            params
            for query, params in fake_driver.calls
            if "RelationFact" in query and params.get("rel_id") == "rel:1"
        ]
        self.assertTrue(relation_params)
        self.assertEqual(relation_params[0]["properties"]["field_name"], "business_lines")
        self.assertEqual(relation_params[0]["properties"]["field_value"], "动力电池业务")


if __name__ == "__main__":
    unittest.main()


