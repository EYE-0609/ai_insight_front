import copy
import unittest


def sample_insight_payload():
    return {
        "task_profile": {
            "industry": "新能源",
            "profile_id": "new_energy",
            "profile_name": "新能源",
        },
        "chain_skeleton": [
            {
                "segment_key": "upstream",
                "segment": "上游",
                "description": "材料和资源",
                "subsegments": ["锂电材料"],
                "confidence": 0.8,
                "evidence_sources": ["https://example.com/chain"],
            }
        ],
        "segment_companies": [
            {
                "segment_key": "upstream",
                "segment": "上游",
                "subsegments": ["锂电材料"],
                "companies": [
                    {
                        "company_name": "宁德时代",
                        "subsegment": "动力电池",
                        "reason": "宁德时代是动力电池龙头。",
                        "evidence_sources": ["https://example.com/catl"],
                    },
                    {
                        "company_name": "特斯拉",
                        "subsegment": "整车应用",
                        "reason": "特斯拉是下游整车企业。",
                        "evidence_sources": ["https://example.com/tesla"],
                    },
                ],
            }
        ],
        "company_cards": [
            {
                "company_name": "宁德时代",
                "aliases": ["CATL"],
                "segment": "上游",
                "subsegment": "动力电池",
                "business_lines": ["动力电池业务"],
                "product_lines": ["动力电池"],
                "core_technologies": ["电池管理系统"],
                "relationship_clues": [
                    "目标企业=特斯拉；关系层级=industry_template；关系名称=动力电池配套；方向=本企业->目标企业；证据=宁德时代为特斯拉提供动力电池配套。；来源=https://example.com/catl；来源等级=A；解释=宁德时代为特斯拉提供动力电池配套"
                ],
                "key_sources": [
                    {
                        "title": "宁德时代年报",
                        "url": "https://example.com/catl",
                        "snippet": "宁德时代主营动力电池，核心技术包括电池管理系统，下游客户包括特斯拉。",
                        "source_grade": "A",
                    }
                ],
                "evidence_excerpts": [
                    "宁德时代主营动力电池，核心技术包括电池管理系统，下游客户包括特斯拉。"
                ],
            }
        ],
        "source_index": [
            {
                "title": "宁德时代年报",
                "url": "https://example.com/catl",
                "snippet": "宁德时代主营动力电池，核心技术包括电池管理系统，下游客户包括特斯拉。",
                "source_grade": "A",
            },
            {
                "title": "特斯拉官网",
                "url": "https://example.com/tesla",
                "snippet": "特斯拉是新能源汽车整车企业。",
                "source_grade": "B",
            },
        ],
    }


class GraphExtractorTests(unittest.TestCase):
    def test_extract_nodes_from_insight_payload(self):
        from kg_graph.extractor import extract_nodes

        nodes = extract_nodes(sample_insight_payload())
        node_keys = {(node.node_type, node.name) for node in nodes}

        self.assertIn(("Industry", "新能源"), node_keys)
        self.assertIn(("Segment", "上游"), node_keys)
        self.assertIn(("Subsegment", "锂电材料"), node_keys)
        self.assertIn(("Company", "宁德时代"), node_keys)
        self.assertIn(("Product", "动力电池"), node_keys)
        self.assertIn(("Technology", "电池管理系统"), node_keys)

    def test_extract_nodes_adds_target_company_from_structured_relationship_clue(self):
        from kg_graph.extractor import extract_nodes

        payload = copy.deepcopy(sample_insight_payload())
        payload["segment_companies"][0]["companies"] = payload["segment_companies"][0]["companies"][:1]
        nodes = extract_nodes(payload)
        node_keys = {(node.node_type, node.name) for node in nodes}

        self.assertIn(("Company", "特斯拉"), node_keys)

    def test_extract_relations_parses_structured_relationship_clues(self):
        from kg_graph.extractor import extract_evidence_chunks, extract_relation_candidates
        from kg_graph.normalizer import normalize_entities
        from kg_graph.extractor import extract_nodes

        payload = sample_insight_payload()
        _normalization_index, _nodes, mention_to_id = normalize_entities(extract_nodes(payload))
        chunks = extract_evidence_chunks(payload)
        relations = extract_relation_candidates(payload, mention_to_id, chunks)
        relation_keys = {(rel.head, rel.relation, rel.tail) for rel in relations}

        self.assertIn(("industry:新能源", "industry_has_segment", "segment:上游"), relation_keys)
        self.assertIn(("company:宁德时代", "company_has_product", "product:动力电池"), relation_keys)
        self.assertIn(("company:宁德时代", "company_has_technology", "technology:电池管理系统"), relation_keys)
        self.assertIn(("company:宁德时代", "vehicle_battery_supply", "company:特斯拉"), relation_keys)

        relation = next(rel for rel in relations if rel.relation == "vehicle_battery_supply")
        self.assertEqual(relation.relation_origin, "card_structured")
        self.assertEqual(relation.relation_level, "industry_template")
        self.assertEqual(relation.relation_name, "动力电池配套")
        self.assertFalse(relation.direction_uncertain)
        self.assertIn("宁德时代为特斯拉提供动力电池配套", relation.evidence_text)

    def test_legacy_relationship_clues_do_not_create_company_edges(self):
        from kg_graph.extractor import extract_evidence_chunks, extract_relation_candidates
        from kg_graph.normalizer import normalize_entities
        from kg_graph.extractor import extract_nodes

        payload = sample_insight_payload()
        payload["company_cards"][0]["relationship_clues"] = ["下游客户包括特斯拉。"]
        _normalization_index, _nodes, mention_to_id = normalize_entities(extract_nodes(payload))
        chunks = extract_evidence_chunks(payload)
        relations = extract_relation_candidates(payload, mention_to_id, chunks)

        self.assertFalse(any(rel.tail == "company:特斯拉" for rel in relations if rel.head == "company:宁德时代"))


def test_profile_edges_prefer_field_level_evidence():
    from kg_graph.builder import build_graph_payload

    payload = {
        "task_profile": {"industry": "新能源", "profile_id": "new_energy"},
        "chain_skeleton": [],
        "segment_companies": [],
        "source_index": [],
        "company_cards": [
            {
                "company_name": "宁德时代",
                "business_lines": ["动力电池业务"],
                "product_lines": [],
                "core_technologies": [],
                "relationship_clues": [],
                "key_sources": [
                    {
                        "title": "泛化来源",
                        "url": "https://example.com/generic",
                        "snippet": "泛化来源只说明公司概况。",
                        "source_grade": "C",
                    }
                ],
                "evidence_excerpts": ["泛化来源只说明公司概况。"],
                "field_evidence": {
                    "business_lines": [
                        {
                            "value": "动力电池业务",
                            "evidence_text": "宁德时代主营动力电池业务。",
                            "source_url": "https://example.com/catl-annual-report",
                            "source_title": "宁德时代年报",
                            "source_grade": "A",
                        }
                    ]
                },
            }
        ],
    }

    graph_payload = build_graph_payload(payload)
    edge = next(item for item in graph_payload["profile_edges"] if item["relation"] == "company_has_business_line")

    assert edge["field_name"] == "business_lines"
    assert edge["field_value"] == "动力电池业务"
    assert edge["evidence_text"] == "宁德时代主营动力电池业务。"
    assert edge["source_url"] == "https://example.com/catl-annual-report"
    assert edge["source_grade"] == "A"
    assert edge["evidence_refs"]


def test_malformed_field_evidence_falls_back_to_card_evidence():
    from kg_graph.builder import build_graph_payload

    payload = {
        "task_profile": {"industry": "新能源", "profile_id": "new_energy"},
        "chain_skeleton": [],
        "segment_companies": [],
        "source_index": [],
        "company_cards": [
            {
                "company_name": "宁德时代",
                "business_lines": ["动力电池业务"],
                "product_lines": [],
                "core_technologies": [],
                "relationship_clues": [],
                "key_sources": [
                    {
                        "title": "宁德时代年报",
                        "url": "https://example.com/catl-annual-report",
                        "snippet": "宁德时代主营动力电池业务。",
                        "source_grade": "A",
                    }
                ],
                "evidence_excerpts": ["宁德时代主营动力电池业务。"],
                "field_evidence": {"business_lines": ["bad"]},
            }
        ],
    }

    graph_payload = build_graph_payload(payload)
    edge = next(item for item in graph_payload["profile_edges"] if item["relation"] == "company_has_business_line")

    assert edge["field_name"] == "business_lines"
    assert edge["field_value"] == "动力电池业务"
    assert edge["evidence_text"] == "宁德时代主营动力电池业务。"
    assert edge["source_url"] == "https://example.com/catl-annual-report"
    assert edge["source_grade"] == "A"


def test_field_evidence_without_source_url_uses_card_source_as_whole_fallback():
    from kg_graph.builder import build_graph_payload

    payload = {
        "task_profile": {"industry": "新能源", "profile_id": "new_energy"},
        "chain_skeleton": [],
        "segment_companies": [],
        "source_index": [],
        "company_cards": [
            {
                "company_name": "宁德时代",
                "business_lines": ["动力电池业务"],
                "product_lines": [],
                "core_technologies": [],
                "relationship_clues": [],
                "key_sources": [
                    {
                        "title": "泛化来源",
                        "url": "https://example.com/generic",
                        "snippet": "宁德时代主营动力电池业务。",
                        "source_grade": "C",
                    }
                ],
                "evidence_excerpts": ["宁德时代主营动力电池业务。"],
                "field_evidence": {
                    "business_lines": [
                        {
                            "value": "动力电池业务",
                            "evidence_text": "字段证据不应被采用。",
                            "source_title": "缺 URL 的年报",
                            "source_grade": "A",
                        }
                    ]
                },
            }
        ],
    }

    graph_payload = build_graph_payload(payload)
    edge = next(
        item
        for item in graph_payload["relation_candidates"]
        if item["relation"] == "company_has_business_line"
    )

    assert edge["evidence_text"] == "宁德时代主营动力电池业务。"
    assert edge["source_url"] == "https://example.com/generic"
    assert edge["source_title"] == "泛化来源"
    assert edge["source_grade"] == "C"
    assert not any(
        chunk["source_url"] == "" and chunk["text"] == "字段证据不应被采用。"
        for chunk in graph_payload["evidence_chunks"]
    )


if __name__ == "__main__":
    unittest.main()


