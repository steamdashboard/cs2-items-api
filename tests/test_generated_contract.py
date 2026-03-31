from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


class GeneratedContractTests(unittest.TestCase):
    def test_schema_exposes_layered_api(self) -> None:
        schema = load_json(ROOT / "data/api/meta/schema.json")
        self.assertEqual(schema["version"], 8)
        self.assertEqual(set(schema["layers"]), {"reference", "graph", "consumer", "media"})
        self.assertIn("canonical_slug", schema["slug_policy"])
        self.assertIn("search_slug", schema["slug_policy"])

    def test_reference_consumer_and_media_counts_match_stats(self) -> None:
        stats = load_json(ROOT / "data/api/meta/stats.json")
        self.assertEqual(stats["skins"], len(list((ROOT / "data/api/reference/skins").glob("*.json"))))
        self.assertEqual(
            stats["consumer.skins"],
            len(list((ROOT / "data/api/consumer/cards/skins").glob("*.json"))),
        )
        self.assertEqual(
            stats["assets"],
            len(list((ROOT / "data/api/media/manifests").glob("*.json"))),
        )
        self.assertEqual(
            stats["rendered.skins_with_rendered_previews"],
            len(list((ROOT / "data/api/media/rendered/manifests/skins").glob("*.json"))),
        )
        self.assertEqual(
            stats["rendered.skin_variants_with_rendered_preview"],
            len(list((ROOT / "data/api/media/rendered/manifests/skin-variants").glob("*.json"))),
        )

    def test_sample_reference_consumer_and_media_files_exist(self) -> None:
        sample_paths = [
            ROOT / "data/api/reference/collectibles/875.json",
            ROOT / "data/api/reference/equipment/50.json",
            ROOT / "data/api/reference/skins/1-1006.json",
            ROOT / "data/api/reference/skins/500-42.json",
            ROOT / "data/api/reference/skins/5030-10018.json",
            ROOT / "data/api/reference/containers/4001.json",
            ROOT / "data/api/reference/stickers/10.json",
            ROOT / "data/api/consumer/cards/collectibles/875.json",
            ROOT / "data/api/consumer/cards/equipment/50.json",
            ROOT / "data/api/consumer/cards/skins/1-37.json",
            ROOT / "data/api/consumer/cards/skins/500-42.json",
            ROOT / "data/api/consumer/cards/skins/5030-10018.json",
            ROOT / "data/api/consumer/cards/cases/4001.json",
            ROOT / "data/api/consumer/cards/special-pools/unusual_revolving_list.json",
            ROOT / "data/api/consumer/cards/tools/4000.json",
            ROOT / "data/api/consumer/meta/discovery.json",
            ROOT / "data/api/media/manifests/collectible__875.json",
            ROOT / "data/api/media/manifests/equipment__50.json",
            ROOT / "data/api/media/manifests/weapon__1.json",
            ROOT / "data/api/media/manifests/container__4001.json",
            ROOT / "data/api/media/rendered/manifests/skins/1-37.json",
            ROOT / "data/api/media/rendered/manifests/skin-variants/1-37__normal__factory-new.json",
            ROOT / "data/api/media/rendered/files/skins/1-37/light.png",
            ROOT / "data/api/media/rendered/manifests/containers/4001.json",
            ROOT / "data/api/media/rendered/manifests/stickers/10.json",
            ROOT / "data/api/media/rendered/manifests/agents/4613.json",
        ]
        for path in sample_paths:
            self.assertTrue(path.exists(), f"Missing expected generated file: {path}")

    def test_skin_variant_contracts_stay_linked(self) -> None:
        skin = load_json(ROOT / "data/api/reference/skins/1-1006.json")
        variant = load_json(ROOT / "data/api/reference/skin-variants/1-1006__normal__factory-new.json")
        self.assertEqual(variant["skin_id"], skin["id"])

    def test_consumer_case_links_to_special_pool(self) -> None:
        case_card = load_json(ROOT / "data/api/consumer/cards/cases/4904.json")
        special_pool_ids = case_card["rare_special_item"]["special_pool_ids"]
        self.assertIn("set_community_33_unusual", special_pool_ids)

    def test_special_pool_skins_are_first_class_reference_entities(self) -> None:
        knife_skin = load_json(ROOT / "data/api/reference/skins/500-42.json")
        glove_skin = load_json(ROOT / "data/api/reference/skins/5030-10018.json")
        relation = load_json(ROOT / "data/api/graph/relations/special-pool-to-skins.json")

        self.assertEqual(knife_skin["weapon"]["weapon_group"], "knife")
        self.assertEqual(glove_skin["weapon"]["weapon_group"], "glove")
        self.assertTrue(knife_skin["generation_notes"]["derived_from_special_pool"])
        self.assertTrue(glove_skin["generation_notes"]["derived_from_special_pool"])
        self.assertEqual(knife_skin["sources"]["special_pools"][0]["expansion_rule"], "legacy-knives")
        self.assertEqual(glove_skin["sources"]["special_pools"][0]["expansion_rule"], "legacy-gloves")
        self.assertIn("500-42", relation["unusual_revolving_list"])
        self.assertIn("5030-10018", relation["community_case_15_unusual"])

    def test_consumer_skin_uses_rendered_preview(self) -> None:
        skin_card = load_json(ROOT / "data/api/consumer/cards/skins/1-37.json")
        self.assertEqual(skin_card["media"]["preview_status"], "rendered")
        self.assertEqual(
            skin_card["media"]["primary_image_png"],
            "data/api/media/rendered/files/skins/1-37/light.png",
        )

    def test_special_pool_consumer_skin_exposes_pool_sources_and_rendered_preview(self) -> None:
        knife_skin_card = load_json(ROOT / "data/api/consumer/cards/skins/500-42.json")
        glove_skin_card = load_json(ROOT / "data/api/consumer/cards/skins/5030-10018.json")

        self.assertEqual(knife_skin_card["weapon"]["weapon_group"], "knife")
        self.assertEqual(glove_skin_card["weapon"]["weapon_group"], "glove")
        self.assertEqual(knife_skin_card["media"]["preview_status"], "rendered")
        self.assertEqual(glove_skin_card["media"]["preview_status"], "rendered")
        self.assertTrue(knife_skin_card["sources"]["special_pools"])
        self.assertTrue(glove_skin_card["sources"]["cases"])
        self.assertTrue(knife_skin_card["generation_notes"]["derived_from_special_pool"])
        self.assertTrue(glove_skin_card["generation_notes"]["derived_from_special_pool"])

    def test_consumer_case_uses_rendered_preview(self) -> None:
        case_card = load_json(ROOT / "data/api/consumer/cards/cases/4001.json")
        self.assertEqual(case_card["media"]["preview_status"], "rendered")
        self.assertEqual(
            case_card["media"]["primary_image_png"],
            "data/api/media/rendered/files/containers/4001/primary.png",
        )

    def test_consumer_agent_exposes_side(self) -> None:
        agent_card = load_json(ROOT / "data/api/consumer/cards/agents/5505.json")
        self.assertEqual(agent_card["side"], "terrorists")

    def test_discovery_exposes_agents_side_lists_and_new_groups(self) -> None:
        discovery = load_json(ROOT / "data/api/consumer/meta/discovery.json")
        self.assertEqual(
            discovery["entrypoints"]["agents"],
            "data/api/consumer/cards/agents/<item_definition_id>.json",
        )
        self.assertEqual(
            discovery["entrypoints"]["collectibles"],
            "data/api/consumer/cards/collectibles/<item_definition_id>.json",
        )
        self.assertEqual(
            discovery["entrypoints"]["equipment"],
            "data/api/consumer/cards/equipment/<item_definition_id>.json",
        )
        self.assertEqual(
            discovery["entrypoints"]["tools"],
            "data/api/consumer/cards/tools/<item_definition_id>.json",
        )
        self.assertEqual(
            discovery["entrypoints"]["agent_sides"],
            "data/api/consumer/lists/by-side/<side>.json",
        )
        self.assertEqual(
            discovery["entrypoints"]["canonical_slugs"],
            "data/api/consumer/lists/by-canonical-slug/<canonical_slug>.json",
        )
        self.assertEqual(
            discovery["entrypoints"]["search_slugs"],
            "data/api/consumer/lists/by-search-slug/<search_slug>.json",
        )

    def test_graph_and_consumer_side_indexes_exist(self) -> None:
        by_side = load_json(ROOT / "data/api/graph/indexes/by-side/terrorists.json")
        self.assertIn("items", by_side)
        self.assertIn("agents", by_side["items"])
        consumer_side = load_json(ROOT / "data/api/consumer/lists/by-side/terrorists.json")
        self.assertTrue(consumer_side["items"], "Expected agent refs for terrorists side list")

    def test_reference_and_consumer_canonical_slug_indexes_exist(self) -> None:
        collection = load_json(ROOT / "data/api/reference/collections/set_gamma_2.json")
        self.assertEqual(collection["canonical_slug"], "set-gamma-2")

        graph_index = load_json(
            ROOT / "data/api/graph/indexes/by-canonical-slug" / f"{collection['canonical_slug']}.json"
        )
        self.assertIn({"kind": "collection", "id": "set_gamma_2"}, graph_index["items"])

        agent = load_json(ROOT / "data/api/reference/agents/5505.json")
        agent_card = load_json(ROOT / "data/api/consumer/cards/agents/5505.json")
        self.assertEqual(agent_card["canonical_slug"], agent["canonical_slug"])

        consumer_index = load_json(
            ROOT / "data/api/consumer/lists/by-canonical-slug" / f"{agent_card['canonical_slug']}.json"
        )
        self.assertTrue(
            any(item["id"] == "5505" and item["group"] == "agents" for item in consumer_index["items"]),
            "Expected canonical slug consumer list to resolve agent card refs",
        )

        graph_agent_index = load_json(
            ROOT / "data/api/graph/indexes/by-canonical-slug" / f"{agent['canonical_slug']}.json"
        )
        self.assertIn({"kind": "agent", "id": "5505"}, graph_agent_index["items"])

    def test_collection_name_fallback_is_humanized(self) -> None:
        collection = load_json(ROOT / "data/api/reference/collections/set_gamma_2.json")
        self.assertEqual(collection["name"], "The Gamma 2 Collection")

    def test_collectibles_and_equipment_are_exposed(self) -> None:
        collectible = load_json(ROOT / "data/api/reference/collectibles/875.json")
        self.assertEqual(collectible["collectible_group"], "trophy")
        self.assertEqual(collectible["tournament_event_id"], 1)

        equipment = load_json(ROOT / "data/api/reference/equipment/50.json")
        self.assertEqual(equipment["equipment_group"], "kevlar")

        tool = load_json(ROOT / "data/api/reference/tools/4000.json")
        self.assertEqual(tool["tool_type"], "display-case")

        tournament = load_json(ROOT / "data/api/consumer/cards/tournaments/15.json")
        self.assertTrue(tournament["collectible_ids"], "Expected tournament cards to reference collectibles")

    def test_unknown_prefabs_are_resolved(self) -> None:
        stats = load_json(ROOT / "data/api/meta/stats.json")
        report = load_json(ROOT / "data/reports/unknown-prefabs.json")
        self.assertEqual(stats["unknown_prefabs"], 0)
        self.assertEqual(report, [])

    def test_rendered_stats_match_unresolved_media_report(self) -> None:
        stats = load_json(ROOT / "data/api/meta/stats.json")
        rendered_stats = load_json(ROOT / "data/api/media/rendered/stats.json")
        unresolved = load_json(ROOT / "data/api/media/rendered/unresolved.json")

        self.assertEqual(rendered_stats["generic_entities_without_rendered_preview"], len(unresolved))
        self.assertEqual(rendered_stats["unresolved_total"], len(unresolved))
        self.assertEqual(stats["rendered.generic_entities_without_rendered_preview"], len(unresolved))
        self.assertEqual(stats["rendered.unresolved_total"], len(unresolved))
        self.assertEqual(
            rendered_stats["generic_entities"],
            rendered_stats["generic_entities_with_rendered_preview"]
            + rendered_stats["generic_entities_without_rendered_preview"],
        )

    def test_public_build_metadata_does_not_expose_local_paths(self) -> None:
        for path in (
            ROOT / "data/api/meta/build.json",
            ROOT / "data/source/steam/build.json",
        ):
            payload = load_json(path)
            for key in ("library_path", "steam_root", "game_root", "appmanifest_path", "pak_path"):
                self.assertNotIn(key, payload, f"{path} must not expose local path field {key}")


if __name__ == "__main__":
    unittest.main()
