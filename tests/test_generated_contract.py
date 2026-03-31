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
        self.assertEqual(schema["version"], 11)
        self.assertEqual(set(schema["layers"]), {"reference", "graph", "consumer", "media"})
        self.assertIn("canonical_slug", schema["slug_policy"])
        self.assertIn("search_slug", schema["slug_policy"])
        self.assertIn("overlays", schema["layout"]["consumer"])

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
            ROOT / "data/api/consumer/cards/skin-variants/500-418__normal__factory-new.json",
            ROOT / "data/api/consumer/overlays/finish-families/case-hardened.json",
            ROOT / "data/api/consumer/overlays/rare-patterns/blue-gem.json",
            ROOT / "data/api/consumer/overlays/phases/418.json",
            ROOT / "data/api/consumer/overlays/market-constraints/cannot-trade.json",
            ROOT / "data/api/consumer/overlays/market-constraints/requires-paint-seed.json",
            ROOT / "data/api/consumer/overlays/seed-lookups/500-38__fade-percentage.json",
            ROOT / "data/api/consumer/meta/discovery.json",
            ROOT / "data/api/consumer/meta/schema.json",
            ROOT / "data/api/consumer/browse/trading.json",
            ROOT / "data/api/consumer/browse/finishes.json",
            ROOT / "data/api/consumer/browse/seed-lookups.json",
            ROOT / "data/api/consumer/lists/by-rarity/legendary.json",
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
        self.assertEqual(skin_card["media"]["media_scope"], "skin-rendered")
        self.assertEqual(skin_card["media"]["coverage_status"], "rendered")
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

    def test_consumer_variant_exposes_trading_phase_and_market_query(self) -> None:
        variant_card = load_json(ROOT / "data/api/consumer/cards/skin-variants/500-418__normal__factory-new.json")
        self.assertEqual(variant_card["trading"]["finish_family"]["id"], "doppler")
        self.assertEqual(variant_card["trading"]["phase"]["id"], "418")
        self.assertTrue(variant_card["trading"]["pattern_sensitive"])
        self.assertEqual(variant_card["trading"]["resolution_level"], "finish")
        self.assertEqual(variant_card["trading"]["deterministic_inputs"], ["paint_index"])
        self.assertFalse(variant_card["trading"]["seed_sensitive"])
        self.assertEqual(variant_card["trading"]["market_query"]["csfloat"]["category"]["code"], 1)
        self.assertFalse(variant_card["trading"]["market_query"]["csfloat"]["supports_paint_seed_filter"])
        self.assertEqual(variant_card["media"]["media_scope"], "skin-variant-rendered")
        self.assertEqual(variant_card["media"]["coverage_status"], "rendered")

    def test_consumer_overlays_link_back_to_cards_and_reference_finishes(self) -> None:
        family = load_json(ROOT / "data/api/consumer/overlays/finish-families/case-hardened.json")
        pattern = load_json(ROOT / "data/api/consumer/overlays/rare-patterns/blue-gem.json")
        phase = load_json(ROOT / "data/api/consumer/overlays/phases/418.json")
        constraint = load_json(ROOT / "data/api/consumer/overlays/market-constraints/cannot-trade.json")

        self.assertEqual(family["overlay_type"], "finish-family")
        self.assertEqual(family["resolution_level"], "paint-seed")
        self.assertEqual(family["seed_domain"]["maximum"], 1000)
        self.assertEqual(family["seed_domain"]["tradeup_only_seed_values"], [1000])
        self.assertTrue(any(item["group"] == "skins" for item in family["example_skins"]))
        self.assertEqual(pattern["finish_families"][0]["group"], "finish-families")
        self.assertEqual(pattern["resolution_level"], "paint-seed")
        self.assertEqual(phase["finish"]["group"], "finishes")
        self.assertEqual(phase["phase_name"], "Phase 1")
        self.assertEqual(phase["resolution_level"], "finish")
        self.assertEqual(constraint["affected_groups"]["collectibles"], 472)
        self.assertEqual(constraint["affected_item_count"], 692)

    def test_consumer_case_uses_rendered_preview(self) -> None:
        case_card = load_json(ROOT / "data/api/consumer/cards/cases/4001.json")
        self.assertEqual(case_card["media"]["preview_status"], "rendered")
        self.assertEqual(
            case_card["media"]["primary_image_png"],
            "data/api/media/rendered/files/containers/4001/primary.png",
        )

    def test_consumer_case_summarizes_trading_relevant_families(self) -> None:
        case_card = load_json(ROOT / "data/api/consumer/cards/cases/4001.json")
        self.assertIn("contains_weapon_groups", case_card["trading"])
        self.assertTrue(
            any(item["id"] == "case-hardened" for item in case_card["trading"]["finish_families"])
        )
        self.assertTrue(
            any(item["id"] == "blue-gem" for item in case_card["trading"]["pattern_mechanics"])
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
        self.assertEqual(
            discovery["entrypoints"]["finish_families"],
            "data/api/consumer/overlays/finish-families/<family_id>.json",
        )
        self.assertEqual(
            discovery["entrypoints"]["rare_patterns"],
            "data/api/consumer/overlays/rare-patterns/<mechanic_id>.json",
        )
        self.assertEqual(
            discovery["entrypoints"]["phases"],
            "data/api/consumer/overlays/phases/<paint_kit_id>.json",
        )
        self.assertEqual(
            discovery["entrypoints"]["market_constraints"],
            "data/api/consumer/overlays/market-constraints/<constraint_id>.json",
        )
        self.assertEqual(
            discovery["entrypoints"]["seed_lookups"],
            "data/api/consumer/overlays/seed-lookups/<lookup_id>.json",
        )
        self.assertEqual(
            discovery["entrypoints"]["rarities"],
            "data/api/consumer/lists/by-rarity/<rarity>.json",
        )
        self.assertEqual(
            discovery["browse_entrypoints"]["finishes"],
            "data/api/consumer/browse/finishes.json",
        )
        self.assertEqual(
            discovery["browse_entrypoints"]["trading"],
            "data/api/consumer/browse/trading.json",
        )
        self.assertEqual(
            discovery["browse_entrypoints"]["seed_lookups"],
            "data/api/consumer/browse/seed-lookups.json",
        )
        self.assertEqual(discovery["overlay_counts"]["finish-families"], 29)
        self.assertEqual(discovery["overlay_counts"]["seed-lookups"], 34)
        self.assertEqual(discovery["overlay_counts"]["phases"], 24)
        self.assertEqual(discovery["list_counts"]["by-finish-family"], 29)
        self.assertEqual(discovery["list_counts"]["by-rarity"], 7)
        self.assertEqual(discovery["list_counts"]["by-market-constraint"], 5)

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

    def test_placeholder_name_fallbacks_are_humanized(self) -> None:
        finish = load_json(ROOT / "data/api/reference/finishes/120.json")
        skin = load_json(ROOT / "data/api/consumer/cards/skins/14-120.json")
        glove = load_json(ROOT / "data/api/consumer/cards/skins/5030-1407.json")
        collectible = load_json(ROOT / "data/api/reference/collectibles/6046.json")

        self.assertEqual(finish["name"], "Hypnosis")
        self.assertEqual(finish["name_status"], "codename-fallback")
        self.assertEqual(skin["name"], "M249 | Hypnosis")
        self.assertEqual(glove["name"], "Sport Gloves | Flames Orange")
        self.assertEqual(collectible["name"], "Coin 6046")

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

    def test_consumer_market_constraint_list_exists(self) -> None:
        constraint_list = load_json(ROOT / "data/api/consumer/lists/by-market-constraint/cannot-trade.json")
        self.assertEqual(constraint_list["key"], "cannot-trade")
        self.assertTrue(any(item["group"] == "collectibles" for item in constraint_list["items"]))

        seed_constraint_list = load_json(ROOT / "data/api/consumer/lists/by-market-constraint/requires-paint-seed.json")
        self.assertEqual(seed_constraint_list["key"], "requires-paint-seed")
        self.assertTrue(any(item["group"] == "skins" for item in seed_constraint_list["items"]))

    def test_skin_rarity_and_collection_breakdowns_use_deterministic_source_tiers(self) -> None:
        skin = load_json(ROOT / "data/api/consumer/cards/skins/7-44.json")
        collection = load_json(ROOT / "data/api/consumer/cards/collections/set_gamma_2.json")
        rarity_list = load_json(ROOT / "data/api/consumer/lists/by-rarity/legendary.json")

        self.assertEqual(skin["rarity"]["id"], "legendary")
        self.assertEqual(skin["rarity"]["source"], "container-tier")
        self.assertGreater(collection["contents"]["known_rarity_skin_count"], 0)
        self.assertTrue(any(entry["tier"] == "ancient" for entry in collection["contents"]["by_rarity"]))
        self.assertTrue(
            any(item["id"] == "7-44" and item["group"] == "skins" for item in rarity_list["items"]),
            "Expected skin cards with deterministic source tiers to appear in rarity lists",
        )

    def test_glove_fade_is_not_mislabeled_as_knife_fade_percentage(self) -> None:
        glove = load_json(ROOT / "data/api/consumer/cards/skins/5034-10063.json")

        self.assertEqual(glove["trading"]["finish_family"]["id"], "glove-fade")
        self.assertTrue(glove["trading"]["pattern_sensitive"])
        self.assertTrue(glove["trading"]["seed_sensitive"])
        self.assertEqual(glove["trading"]["pattern_mechanics"], [])
        self.assertEqual(glove["trading"]["lookup_overlays"], [])

    def test_seed_lookup_overlay_exposes_fade_tables_and_card_links(self) -> None:
        skin = load_json(ROOT / "data/api/consumer/cards/skins/500-38.json")
        lookup = load_json(ROOT / "data/api/consumer/overlays/seed-lookups/500-38__fade-percentage.json")
        trading_browse = load_json(ROOT / "data/api/consumer/browse/trading.json")

        self.assertEqual(skin["trading"]["lookup_overlays"][0]["id"], "500-38__fade-percentage")
        self.assertEqual(lookup["overlay_type"], "seed-lookup")
        self.assertEqual(lookup["metric"]["id"], "fade-percentage")
        self.assertEqual(lookup["seed_count"], 1001)
        self.assertEqual(lookup["value_range"]["maximum"], 100.0)
        self.assertEqual(lookup["value_range"]["minimum"], 80.0)
        self.assertEqual(lookup["best_seeds"][0]["seed"], 763)
        self.assertEqual(trading_browse["seed_lookup_count"], 34)

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
