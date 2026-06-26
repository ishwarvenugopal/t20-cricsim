from pathlib import Path
import random

import pandas as pd


DATA_DIR = Path("data/mined")
OUTCOMES = ["0", "1", "2", "3", "4", "6", "W", "Wd", "Nb"]


_TABLES = {}


def get_phase(over_number: int) -> str:
    if over_number <= 6:
        return "powerplay"
    if over_number <= 15:
        return "middle"
    return "death"


def load_table(filename: str) -> pd.DataFrame:
    if filename not in _TABLES:
        path = DATA_DIR / filename

        if not path.exists():
            raise FileNotFoundError(
                f"Missing {path}. Run: python mine_cricsheet.py"
            )

        _TABLES[filename] = pd.read_csv(path)

    return _TABLES[filename]


def normalise_probs(probs: dict) -> dict:
    total = sum(probs.values())

    if total <= 0:
        return {outcome: 1 / len(OUTCOMES) for outcome in OUTCOMES}

    return {outcome: probs.get(outcome, 0) / total for outcome in OUTCOMES}


def rows_to_probs(rows: pd.DataFrame) -> dict:
    prob_col = "probability" if "probability" in rows.columns else "probability_raw"

    probs = {outcome: 0.0 for outcome in OUTCOMES}

    for _, row in rows.iterrows():
        probs[row["outcome"]] = float(row[prob_col])

    return normalise_probs(probs)


def apply_ground_modifier(probs: dict, venue: str, phase: str) -> dict:
    if not venue:
        return probs

    ground = load_table("ground_modifiers.csv")

    rows = ground[
        (ground["venue"] == venue)
        & (ground["phase"] == phase)
    ]

    if rows.empty:
        return probs

    row = rows.iloc[0]

    probs = probs.copy()
    probs["4"] *= float(row["four_modifier"])
    probs["6"] *= float(row["six_modifier"])
    probs["W"] *= float(row["wicket_modifier"])

    return normalise_probs(probs)


def get_ball_probabilities(batter, bowler, over_number: int, ground_info: dict) -> dict:
    phase = get_phase(over_number)
    batter_name = batter.name
    bowler_name = bowler.name
    venue = ground_info.get("venue")

    batter_bowler = load_table("batter_bowler_phase_probs.csv")

    rows = batter_bowler[
        (batter_bowler["batter"] == batter_name)
        & (batter_bowler["bowler"] == bowler_name)
        & (batter_bowler["phase"] == phase)
    ]

    if not rows.empty:
        probs = rows_to_probs(rows)
        return apply_ground_modifier(probs, venue, phase)

    batter_phase = load_table("batter_phase_probs.csv")

    rows = batter_phase[
        (batter_phase["batter"] == batter_name)
        & (batter_phase["phase"] == phase)
    ]

    if not rows.empty:
        probs = rows_to_probs(rows)
        return apply_ground_modifier(probs, venue, phase)

    bowler_phase = load_table("bowler_phase_probs.csv")

    rows = bowler_phase[
        (bowler_phase["bowler"] == bowler_name)
        & (bowler_phase["phase"] == phase)
    ]

    if not rows.empty:
        probs = rows_to_probs(rows)
        return apply_ground_modifier(probs, venue, phase)

    league = load_table("league_phase_probs.csv")

    rows = league[league["phase"] == phase]
    probs = rows_to_probs(rows)

    return apply_ground_modifier(probs, venue, phase)


def sample_outcome(probs: dict) -> str:
    return random.choices(
        population=list(probs.keys()),
        weights=list(probs.values()),
        k=1,
    )[0]