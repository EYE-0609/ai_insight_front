import unittest


class GraphRelationCatalogTests(unittest.TestCase):
    def test_generic_relation_template_match(self):
        from kg_graph.relation_catalog import match_relation_template

        match = match_relation_template("双方建立战略合作关系", "generic")

        self.assertEqual(match["relation_level"], "generic")
        self.assertEqual(match["relation_key"], "cooperate_with")
        self.assertEqual(match["relation_label"], "合作")

    def test_new_energy_relation_template_match(self):
        from kg_graph.relation_catalog import match_relation_template

        match = match_relation_template("动力电池配套", "new_energy")

        self.assertEqual(match["relation_level"], "industry_template")
        self.assertEqual(match["relation_key"], "vehicle_battery_supply")
        self.assertEqual(match["relation_label"], "动力电池配套")

    def test_unknown_relation_falls_back_to_special(self):
        from kg_graph.relation_catalog import match_relation_template

        match = match_relation_template("联合开发钠离子电池材料", "generic")

        self.assertEqual(match["relation_level"], "special")
        self.assertEqual(match["relation_key"], "special_relation")
        self.assertEqual(match["relation_label"], "联合开发钠离子电池材料")

    def test_prompt_hint_contains_profile_templates(self):
        from kg_graph.relation_catalog import build_relation_prompt_hint

        hint = build_relation_prompt_hint("new_energy")

        self.assertIn("通用关系", hint)
        self.assertIn("新能源行业关系", hint)
        self.assertIn("特殊关系", hint)


if __name__ == "__main__":
    unittest.main()


