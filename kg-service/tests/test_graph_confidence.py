import unittest


def relation(**overrides):
    from kg_graph.schema import RelationCandidate

    defaults = {
        "rel_id": "rel:1",
        "head": "company:宁德时代",
        "head_type": "Company",
        "relation": "company_has_product",
        "tail": "product:动力电池",
        "tail_type": "Product",
        "evidence_refs": ["evidence:1"],
        "evidence_text": "宁德时代主营动力电池。",
        "source_url": "https://example.com/catl",
        "source_title": "2025 宁德时代年报",
        "source_grade": "A",
        "relation_origin": "explicit_evidence",
    }
    defaults.update(overrides)
    return RelationCandidate(**defaults)


class GraphConfidenceTests(unittest.TestCase):
    def test_missing_evidence_text_caps_score_at_020(self):
        from kg_graph.confidence import apply_confidence

        rel = apply_confidence(relation(evidence_text=""), [])

        self.assertLessEqual(rel.confidence, 0.20)
        self.assertEqual(rel.status, "rejected_or_insufficient")

    def test_missing_source_url_caps_score_at_030(self):
        from kg_graph.confidence import apply_confidence

        rel = apply_confidence(relation(source_url=""), [])

        self.assertLessEqual(rel.confidence, 0.30)
        self.assertEqual(rel.status, "rejected_or_insufficient")

    def test_c_grade_source_cannot_be_verified(self):
        from kg_graph.confidence import apply_confidence

        rel = apply_confidence(relation(source_grade="C"), [])

        self.assertLessEqual(rel.confidence, 0.55)
        self.assertNotEqual(rel.status, "verified")

    def test_inferred_direction_uncertain_relation_stays_weak_candidate(self):
        from kg_graph.confidence import apply_confidence

        rel = apply_confidence(
            relation(
                relation="supplies_to",
                tail="company:特斯拉",
                tail_type="Company",
                evidence_text="下游客户包括特斯拉。",
                relation_origin="inferred",
                direction_uncertain=True,
            ),
            [],
        )

        self.assertLessEqual(rel.confidence, 0.65)
        self.assertEqual(rel.status, "weak_candidate")

    def test_special_relation_without_explanation_is_capped(self):
        from kg_graph.confidence import apply_confidence

        rel = apply_confidence(
            relation(
                relation="special_relation",
                tail="company:特斯拉",
                tail_type="Company",
                evidence_text="宁德时代与特斯拉存在定向车型联合验证关系。",
                relation_origin="card_structured",
                relation_level="special",
                relation_name="定向车型联合验证",
                explanation="",
            ),
            [],
        )

        self.assertLessEqual(rel.confidence, 0.55)
        self.assertIn("special_relation_missing_explanation", rel.score_breakdown["hard_cap_reason"])

    def test_same_source_url_evidence_refs_do_not_count_as_multi_source(self):
        from kg_graph.confidence import apply_confidence
        from kg_graph.schema import EvidenceChunk

        rel = apply_confidence(
            relation(evidence_refs=["evidence:1", "evidence:2"]),
            [
                EvidenceChunk(chunk_id="evidence:1", text="A", source_url="https://example.com/source"),
                EvidenceChunk(chunk_id="evidence:2", text="B", source_url="https://example.com/source"),
            ],
        )

        self.assertEqual(rel.score_breakdown["multi_source"], 0.0)

    def test_distinct_source_url_evidence_refs_count_as_multi_source(self):
        from kg_graph.confidence import apply_confidence
        from kg_graph.schema import EvidenceChunk

        rel = apply_confidence(
            relation(evidence_refs=["evidence:1", "evidence:2"]),
            [
                EvidenceChunk(chunk_id="evidence:1", text="A", source_url="https://example.com/source-a"),
                EvidenceChunk(chunk_id="evidence:2", text="B", source_url="https://example.com/source-b"),
            ],
        )

        self.assertEqual(rel.score_breakdown["multi_source"], 0.08)


if __name__ == "__main__":
    unittest.main()


