from pathlib import Path

APP_ID = "730"
GAME_NAME = "Counter-Strike 2"
GAME_INSTALLDIR = "Counter-Strike Global Offensive"
GAME_VPK_PATH = Path("game/csgo/pak01_dir.vpk")
ITEMS_GAME_PATH = "scripts/items/items_game.txt"
LOCALE_PREFIX = "resource/csgo_"
LOCALE_SUFFIX = ".txt"

DEFAULT_STEAM_ROOTS = [
    Path.home() / ".local/share/Steam",
    Path.home() / ".steam/steam",
    Path.home() / ".steam/root",
    Path.home() / ".var/app/com.valvesoftware.Steam/.local/share/Steam",
    Path.home() / "Library/Application Support/Steam",
    Path("/mnt/c/Program Files (x86)/Steam"),
    Path("/mnt/c/Program Files/Steam"),
    Path("/mnt/c/Steam"),
]

HANDLED_TOP_LEVEL_BLOCKS = {
    "game_info",
    "rarities",
    "qualities",
    "colors",
    "graffiti_tints",
    "player_loadout_slots",
    "alternate_icons2",
    "prefabs",
    "items",
    "attributes",
    "sticker_kits",
    "paint_kits",
    "paint_kits_rarity",
    "item_sets",
    "client_loot_lists",
    "revolving_loot_lists",
    "quest_reward_loot_lists",
    "item_levels",
    "kill_eater_score_types",
    "music_definitions",
    "quest_definitions",
    "recurring_mission_periods",
    "campaign_definitions",
    "skirmish_modes",
    "skirmish_rank_info",
    "recipes",
    "seasonaloperations",
    "pro_event_results",
    "pro_players",
    "pro_teams",
    "items_game_live",
    "keychain_definitions",
    "highlight_reels",
}

CONTAINER_PREFABS = {
    "weapon_case",
    "weapon_case_base",
    "weapon_case_souvenirpkg",
    "sticker_capsule",
}

STANDARD_EXTERIORS = [
    {
        "id": "factory-new",
        "name": "Factory New",
        "short_name": "FN",
        "min_float": 0.00,
        "max_float": 0.07,
    },
    {
        "id": "minimal-wear",
        "name": "Minimal Wear",
        "short_name": "MW",
        "min_float": 0.07,
        "max_float": 0.15,
    },
    {
        "id": "field-tested",
        "name": "Field-Tested",
        "short_name": "FT",
        "min_float": 0.15,
        "max_float": 0.38,
    },
    {
        "id": "well-worn",
        "name": "Well-Worn",
        "short_name": "WW",
        "min_float": 0.38,
        "max_float": 0.45,
    },
    {
        "id": "battle-scarred",
        "name": "Battle-Scarred",
        "short_name": "BS",
        "min_float": 0.45,
        "max_float": 1.00,
    },
]

WEAPON_GROUPS = {
    "weapon_cz75a": "pistol",
    "weapon_deagle": "pistol",
    "weapon_elite": "pistol",
    "weapon_fiveseven": "pistol",
    "weapon_glock": "pistol",
    "weapon_hkp2000": "pistol",
    "weapon_p250": "pistol",
    "weapon_revolver": "pistol",
    "weapon_tec9": "pistol",
    "weapon_usp_silencer": "pistol",
    "weapon_taser": "equipment",
    "weapon_mac10": "smg",
    "weapon_mp5sd": "smg",
    "weapon_mp7": "smg",
    "weapon_mp9": "smg",
    "weapon_p90": "smg",
    "weapon_bizon": "smg",
    "weapon_ump45": "smg",
    "weapon_mag7": "shotgun",
    "weapon_nova": "shotgun",
    "weapon_sawedoff": "shotgun",
    "weapon_xm1014": "shotgun",
    "weapon_m249": "machinegun",
    "weapon_negev": "machinegun",
    "weapon_ak47": "rifle",
    "weapon_aug": "rifle",
    "weapon_famas": "rifle",
    "weapon_galilar": "rifle",
    "weapon_m4a1": "rifle",
    "weapon_m4a1_silencer": "rifle",
    "weapon_sg556": "rifle",
    "weapon_awp": "sniper-rifle",
    "weapon_g3sg1": "sniper-rifle",
    "weapon_scar20": "sniper-rifle",
    "weapon_ssg08": "sniper-rifle",
}

STICKER_FINISH_ORDER = [
    ("lenticular", "Lenticular"),
    ("embroidered", "Embroidered"),
    ("glitter", "Glitter"),
    ("gold", "Gold"),
    ("foil", "Foil"),
    ("holo", "Holo"),
]

