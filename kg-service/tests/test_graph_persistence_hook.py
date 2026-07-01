import unittest
from unittest.mock import MagicMock, patch

from tests.test_graph_extractor import sample_insight_payload


class GraphPersistenceHookTests(unittest.TestCase):
    def test_persistence_is_skipped_without_neo4j_uri(self):
        from kg_graph.builder import build_graph_payload, persist_graph_payload_if_enabled

        graph_payload = build_graph_payload(sample_insight_payload())
        with patch.dict("os.environ", {}, clear=True):
            result = persist_graph_payload_if_enabled(graph_payload)

        self.assertEqual(result["persistence_meta"]["status"], "skipped")
        self.assertFalse(result["persistence_meta"]["enabled"])
        self.assertEqual(result["persistence_meta"]["reason"], "missing_neo4j_uri")

    def test_persistence_is_skipped_when_disabled(self):
        from kg_graph.builder import build_graph_payload, persist_graph_payload_if_enabled

        graph_payload = build_graph_payload(sample_insight_payload())
        with patch.dict("os.environ", {"NEO4J_URI": "bolt://localhost:7687", "GRAPH_AUTO_PERSIST": "false"}):
            result = persist_graph_payload_if_enabled(graph_payload)

        self.assertEqual(result["persistence_meta"]["status"], "skipped")
        self.assertFalse(result["persistence_meta"]["enabled"])
        self.assertEqual(result["persistence_meta"]["reason"], "graph_auto_persist_disabled")

    def test_persistence_success_sets_persisted_meta(self):
        from kg_graph.builder import build_graph_payload, persist_graph_payload_if_enabled

        graph_payload = build_graph_payload(sample_insight_payload())
        store = MagicMock()
        store.persist_graph_payload.return_value = {"node_count": 2, "edge_count": 1, "evidence_count": 3}

        with patch.dict("os.environ", {"NEO4J_URI": "bolt://localhost:7687"}):
            with patch("kg_graph.builder.Neo4jGraphStore", return_value=store):
                result = persist_graph_payload_if_enabled(graph_payload)

        self.assertEqual(result["persistence_meta"]["status"], "persisted")
        self.assertTrue(result["persistence_meta"]["enabled"])
        self.assertEqual(result["persistence_meta"]["node_count"], 2)
        self.assertEqual(result["persistence_meta"]["edge_count"], 1)
        store.close.assert_called_once()

    def test_persistence_failure_sets_failed_meta_without_raising(self):
        from kg_graph.builder import build_graph_payload, persist_graph_payload_if_enabled

        graph_payload = build_graph_payload(sample_insight_payload())
        with patch.dict("os.environ", {"NEO4J_URI": "bolt://localhost:7687"}):
            with patch("kg_graph.builder.Neo4jGraphStore", side_effect=RuntimeError("boom")):
                result = persist_graph_payload_if_enabled(graph_payload)

        self.assertEqual(result["persistence_meta"]["status"], "failed")
        self.assertTrue(result["persistence_meta"]["enabled"])
        self.assertIn("boom", result["persistence_meta"]["error"])


if __name__ == "__main__":
    unittest.main()


