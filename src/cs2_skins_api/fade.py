from __future__ import annotations

from functools import lru_cache
from math import ceil, floor
from typing import Any


FADE_LOOKUP_SPECS: dict[str, dict[str, Any]] = {
    "fade": {
        "family_id": "fade",
        "metric_id": "fade-percentage",
        "metric_name": "Fade Percentage",
        "knowledge_source": "open-source-pattern-algorithm",
        "source_repo": "https://github.com/chescos/csgo-fade-percentage-calculator",
        "source_license": "MIT",
        "weapons": (
            "AWP",
            "Bayonet",
            "Bowie Knife",
            "Butterfly Knife",
            "Classic Knife",
            "Falchion Knife",
            "Flip Knife",
            "Glock-18",
            "Gut Knife",
            "Huntsman Knife",
            "Karambit",
            "Kukri Knife",
            "M4A1-S",
            "M9 Bayonet",
            "MAC-10",
            "MP7",
            "Navaja Knife",
            "Nomad Knife",
            "Paracord Knife",
            "R8 Revolver",
            "Shadow Daggers",
            "Skeleton Knife",
            "Stiletto Knife",
            "Survival Knife",
            "Talon Knife",
            "UMP-45",
            "Ursus Knife",
        ),
        "reversed_weapons": (
            "AWP",
            "Karambit",
            "MP7",
            "Talon Knife",
        ),
        "configs": {
            "default": {
                "pattern_offset_x_start": -0.7,
                "pattern_offset_x_end": -0.7,
                "pattern_offset_y_start": -0.7,
                "pattern_offset_y_end": -0.7,
                "pattern_rotate_start": -55.0,
                "pattern_rotate_end": -65.0,
            },
            "MP7": {
                "pattern_offset_x_start": -0.9,
                "pattern_offset_x_end": -0.3,
                "pattern_offset_y_start": -0.7,
                "pattern_offset_y_end": -0.5,
                "pattern_rotate_start": -55.0,
                "pattern_rotate_end": -65.0,
            },
            "M4A1-S": {
                "pattern_offset_x_start": -0.14,
                "pattern_offset_x_end": 0.05,
                "pattern_offset_y_start": 0.0,
                "pattern_offset_y_end": 0.0,
                "pattern_rotate_start": -45.0,
                "pattern_rotate_end": -45.0,
            },
        },
    },
    "amber-fade": {
        "family_id": "amber-fade",
        "metric_id": "fade-percentage",
        "metric_name": "Fade Percentage",
        "knowledge_source": "open-source-pattern-algorithm",
        "source_repo": "https://github.com/chescos/csgo-fade-percentage-calculator",
        "source_license": "MIT",
        "weapons": (
            "AUG",
            "Galil AR",
            "MAC-10",
            "P2000",
            "R8 Revolver",
            "Sawed-Off",
        ),
        "reversed_weapons": (),
        "configs": {
            "default": {
                "pattern_offset_x_start": -0.7,
                "pattern_offset_x_end": -0.7,
                "pattern_offset_y_start": -0.7,
                "pattern_offset_y_end": -0.7,
                "pattern_rotate_start": -55.0,
                "pattern_rotate_end": -65.0,
            },
        },
    },
    "acid-fade": {
        "family_id": "acid-fade",
        "metric_id": "fade-percentage",
        "metric_name": "Fade Percentage",
        "knowledge_source": "open-source-pattern-algorithm",
        "source_repo": "https://github.com/chescos/csgo-fade-percentage-calculator",
        "source_license": "MIT",
        "weapons": ("SSG 08",),
        "reversed_weapons": ("SSG 08",),
        "configs": {
            "default": {
                "pattern_offset_x_start": -2.4,
                "pattern_offset_x_end": -2.1,
                "pattern_offset_y_start": 0.0,
                "pattern_offset_y_end": 0.0,
                "pattern_rotate_start": -55.0,
                "pattern_rotate_end": -65.0,
            },
        },
    },
}


class RandomNumberGenerator:
    def __init__(self) -> None:
        self.m_idum = 0
        self.m_iy = 0
        self.m_iv: list[int] = []

        self.ntab = 32
        self.ia = 16807
        self.im = 2147483647
        self.iq = 127773
        self.ir = 2836
        self.ndiv = 1 + (self.im - 1) / self.ntab
        self.am = 1.0 / self.im
        self.rnmx = 1.0 - 1.2e-7

    def set_seed(self, seed: int) -> None:
        self.m_idum = seed
        if seed >= 0:
            self.m_idum = -seed
        self.m_iy = 0

    def generate_random_number(self) -> int:
        if self.m_idum <= 0 or self.m_iy == 0:
            if -self.m_idum < 1:
                self.m_idum = 1
            else:
                self.m_idum = -self.m_idum

            for j in range(self.ntab + 7, -1, -1):
                k = floor(self.m_idum / self.iq)
                self.m_idum = floor(self.ia * (self.m_idum - k * self.iq) - self.ir * k)
                if self.m_idum < 0:
                    self.m_idum += self.im
                if j < self.ntab:
                    if len(self.m_iv) <= j:
                        self.m_iv.extend([0] * (j + 1 - len(self.m_iv)))
                    self.m_iv[j] = self.m_idum
            self.m_iy = self.m_iv[0]

        k = floor(self.m_idum / self.iq)
        self.m_idum = floor(self.ia * (self.m_idum - k * self.iq) - self.ir * k)
        if self.m_idum < 0:
            self.m_idum += self.im

        j = floor(self.m_iy / self.ndiv)
        self.m_iy = floor(self.m_iv[j])
        self.m_iv[j] = self.m_idum
        return self.m_iy

    def random_float(self, low: float, high: float) -> float:
        value = self.am * self.generate_random_number()
        if value > self.rnmx:
            value = self.rnmx
        return (value * (high - low)) + low


def fade_lookup_supported_weapons(family_id: str) -> tuple[str, ...]:
    spec = FADE_LOOKUP_SPECS.get(family_id)
    if spec is None:
        return ()
    return tuple(spec["weapons"])


def has_fade_lookup(family_id: str | None, weapon_name: str | None) -> bool:
    if not family_id or not weapon_name:
        return False
    return weapon_name in fade_lookup_supported_weapons(family_id)


@lru_cache(maxsize=None)
def build_fade_lookup(family_id: str, weapon_name: str) -> dict[str, Any]:
    spec = FADE_LOOKUP_SPECS.get(family_id)
    if spec is None:
        raise KeyError(f"Unsupported fade lookup family: {family_id}")
    if weapon_name not in spec["weapons"]:
        raise KeyError(f"Unsupported fade lookup weapon '{weapon_name}' for family '{family_id}'")

    config = dict(spec["configs"].get(weapon_name, spec["configs"]["default"]))
    reversed_weapons = set(spec.get("reversed_weapons", ()))
    raw_results: list[float] = []

    for seed in range(0, 1001):
        rng = RandomNumberGenerator()
        rng.set_seed(seed)
        x_offset = rng.random_float(config["pattern_offset_x_start"], config["pattern_offset_x_end"])
        rng.random_float(config["pattern_offset_y_start"], config["pattern_offset_y_end"])
        rotation = rng.random_float(config["pattern_rotate_start"], config["pattern_rotate_end"])

        uses_rotation = config["pattern_rotate_start"] != config["pattern_rotate_end"]
        uses_x_offset = config["pattern_offset_x_start"] != config["pattern_offset_x_end"]

        if uses_rotation and uses_x_offset:
            raw_result = rotation * x_offset
        elif uses_rotation:
            raw_result = rotation
        else:
            raw_result = x_offset
        raw_results.append(raw_result)

    best_result = min(raw_results) if weapon_name in reversed_weapons else max(raw_results)
    worst_result = max(raw_results) if weapon_name in reversed_weapons else min(raw_results)
    result_range = worst_result - best_result

    entries: list[dict[str, Any]] = []
    if result_range == 0:
        for seed in range(0, 1001):
            entries.append({"seed": seed, "percentage": 100.0})
    else:
        for seed, raw_result in enumerate(raw_results):
            percentage_result = (worst_result - raw_result) / result_range
            percentage = 80.0 + (percentage_result * 20.0)
            entries.append({"seed": seed, "percentage": round(percentage, 6)})

    sorted_high = sorted(entries, key=lambda row: (-row["percentage"], row["seed"]))
    sorted_low = sorted(entries, key=lambda row: (row["percentage"], row["seed"]))
    high_rank = {row["seed"]: index + 1 for index, row in enumerate(sorted_high)}
    low_rank = {row["seed"]: index + 1 for index, row in enumerate(sorted_low)}
    for row in entries:
        row["high_rank"] = high_rank[row["seed"]]
        row["low_rank"] = low_rank[row["seed"]]

    percentages = [row["percentage"] for row in entries]
    sorted_percentages = sorted(percentages)
    unique_percentages = sorted(set(percentages))

    def high_threshold(percent: float) -> float:
        count = max(1, ceil(len(sorted_high) * percent))
        return sorted_high[count - 1]["percentage"]

    def low_threshold(percent: float) -> float:
        count = max(1, ceil(len(sorted_low) * percent))
        return sorted_low[count - 1]["percentage"]

    return {
        "family_id": family_id,
        "weapon_name": weapon_name,
        "metric_id": spec["metric_id"],
        "metric_name": spec["metric_name"],
        "knowledge_source": spec["knowledge_source"],
        "source_repo": spec["source_repo"],
        "source_license": spec["source_license"],
        "seed_count": len(entries),
        "minimum_percentage": min(percentages),
        "maximum_percentage": max(percentages),
        "unique_percentage_count": len(unique_percentages),
        "top_thresholds": {
            "top_1_percent_min": high_threshold(0.01),
            "top_5_percent_min": high_threshold(0.05),
            "top_10_percent_min": high_threshold(0.10),
        },
        "bottom_thresholds": {
            "bottom_1_percent_max": low_threshold(0.01),
            "bottom_5_percent_max": low_threshold(0.05),
            "bottom_10_percent_max": low_threshold(0.10),
        },
        "median_percentage": sorted_percentages[len(sorted_percentages) // 2],
        "best_seeds": sorted_high[:12],
        "worst_seeds": sorted_low[:12],
        "entries": entries,
    }
