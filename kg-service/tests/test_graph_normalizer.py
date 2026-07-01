import unittest


class GraphNormalizerTests(unittest.TestCase):
    def test_company_aliases_merge_to_one_canonical_node(self):
        from kg_graph.normalizer import normalize_entities
        from kg_graph.schema import GraphNode

        nodes = [
            GraphNode(
                node_id="company:宁德时代新能源科技股份有限公司",
                node_type="Company",
                name="宁德时代新能源科技股份有限公司",
                aliases=["宁德时代", "CATL"],
                normalized_name="宁德时代新能源科技股份有限公司",
                raw_mentions=["宁德时代新能源科技股份有限公司"],
            ),
            GraphNode(
                node_id="company:CATL",
                node_type="Company",
                name="CATL",
                aliases=[],
                normalized_name="CATL",
                raw_mentions=["CATL"],
            ),
        ]

        normalization_index, normalized_nodes, mention_to_id = normalize_entities(nodes)

        company_nodes = [node for node in normalized_nodes if node.node_type == "Company"]
        self.assertEqual(len(company_nodes), 1)
        self.assertEqual(company_nodes[0].node_id, "company:宁德时代")
        self.assertIn("CATL", company_nodes[0].aliases)
        self.assertEqual(mention_to_id["CATL"], "company:宁德时代")
        self.assertIn(
            {
                "raw": "宁德时代新能源科技股份有限公司",
                "canonical_id": "company:宁德时代",
                "method": "alias_match",
            },
            normalization_index,
        )

    def test_english_company_name_without_alias_is_not_merged(self):
        from kg_graph.normalizer import normalize_entities
        from kg_graph.schema import GraphNode

        nodes = [
            GraphNode(node_id="company:宁德时代", node_type="Company", name="宁德时代"),
            GraphNode(node_id="company:CATL", node_type="Company", name="CATL"),
        ]

        _normalization_index, normalized_nodes, mention_to_id = normalize_entities(nodes)

        company_ids = {node.node_id for node in normalized_nodes if node.node_type == "Company"}
        self.assertEqual(company_ids, {"company:宁德时代", "company:CATL"})
        self.assertEqual(mention_to_id["CATL"], "company:CATL")

    def test_same_name_different_entity_types_are_not_merged(self):
        from kg_graph.normalizer import normalize_entities
        from kg_graph.schema import GraphNode

        nodes = [
            GraphNode(node_id="subsegment:动力电池", node_type="Subsegment", name="动力电池"),
            GraphNode(node_id="product:动力电池", node_type="Product", name="动力电池"),
        ]

        _normalization_index, normalized_nodes, _mention_to_id = normalize_entities(nodes)

        typed_ids = {(node.node_type, node.node_id) for node in normalized_nodes}
        self.assertIn(("Subsegment", "subsegment:动力电池"), typed_ids)
        self.assertIn(("Product", "product:动力电池"), typed_ids)


if __name__ == "__main__":
    unittest.main()


