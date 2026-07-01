import unittest

from tests.test_graph_extractor import sample_insight_payload


class GraphBuilderTests(unittest.TestCase):
    def test_build_graph_payload_returns_nodes_candidates_edges_and_meta(self):
        from kg_graph.builder import build_graph_payload

        graph_payload = build_graph_payload(sample_insight_payload())

        self.assertEqual(graph_payload["task_profile"]["industry"], "新能源")
        self.assertGreaterEqual(len(graph_payload["graph_nodes"]), 1)
        self.assertGreaterEqual(len(graph_payload["evidence_chunks"]), 1)
        self.assertGreaterEqual(len(graph_payload["relation_candidates"]), 1)
        self.assertIn("normalization_index", graph_payload)
        self.assertEqual(graph_payload["confidence_meta"]["rule_version"], "v1.0")
        self.assertIn("qa_index_hints", graph_payload)
        self.assertIn("company_edges", graph_payload)
        self.assertIn("profile_edges", graph_payload)
        self.assertIn("structural_edges", graph_payload)
        self.assertIn("inter_company_relations", graph_payload)

    def test_structured_relationship_clues_enter_company_edges(self):
        from kg_graph.builder import build_graph_payload

        graph_payload = build_graph_payload(sample_insight_payload())
        candidate_keys = {
            (rel["head"], rel["relation"], rel["tail"], rel["status"])
            for rel in graph_payload["relation_candidates"]
        }
        edge_keys = {(rel["head"], rel["relation"], rel["tail"]) for rel in graph_payload["graph_edges"]}
        company_edge_keys = {(rel["head"], rel["relation"], rel["tail"]) for rel in graph_payload["company_edges"]}
        profile_edge_keys = {(rel["head"], rel["relation"], rel["tail"]) for rel in graph_payload["profile_edges"]}
        inter_company_keys = {
            (rel["head"], rel["relation"], rel["tail"]) for rel in graph_payload["inter_company_relations"]
        }

        self.assertIn(("company:宁德时代", "vehicle_battery_supply", "company:特斯拉", "strong_candidate"), candidate_keys)
        self.assertIn(("company:宁德时代", "vehicle_battery_supply", "company:特斯拉"), edge_keys)
        self.assertIn(("company:宁德时代", "vehicle_battery_supply", "company:特斯拉"), company_edge_keys)
        self.assertIn(("company:宁德时代", "vehicle_battery_supply", "company:特斯拉"), inter_company_keys)
        self.assertIn(("company:宁德时代", "company_has_product", "product:动力电池"), edge_keys)
        self.assertIn(("company:宁德时代", "company_has_product", "product:动力电池"), profile_edge_keys)


if __name__ == "__main__":
    unittest.main()


