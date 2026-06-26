import random
from pathlib import Path

import pandas as pd

from models import Player


DATA_DIR = Path("data/mined")


def overs_from_balls(balls: int) -> str:
    return f"{balls // 6}.{balls % 6}"


def strike_rate(runs: int, balls: int) -> float:
    if balls == 0:
        return 0.0
    return round((runs / balls) * 100, 2)


def economy_rate(runs: int, balls: int) -> float:
    if balls == 0:
        return 0.0
    return round(runs / (balls / 6), 2)


def load_player_pool(min_batting_events: int = 50) -> list[Player]:
    path = DATA_DIR / "player_pool.csv"

    if not path.exists():
        raise FileNotFoundError("Run python mine_cricsheet.py first.")

    df = pd.read_csv(path)

    df = df[
        (df["balls_faced_events"] >= min_batting_events)
        | (df["legal_balls_bowled"] >= 60)
    ].copy()

    players = []

    for _, row in df.iterrows():
        players.append(
            Player(
                name=row["player"],
                role=row["role"],
                can_bowl=bool(row["can_bowl"]),
            )
        )

    return players


def load_venues() -> list[str]:
    path = DATA_DIR / "ground_modifiers.csv"

    if not path.exists():
        return ["Unknown"]

    df = pd.read_csv(path)
    venues = sorted(df["venue"].dropna().unique().tolist())

    return venues if venues else ["Unknown"]


def validate_team(players: list[Player]):
    if len(players) != 11:
        return False, "Select exactly 11 players."

    if len(set(p.name for p in players)) != 11:
        return False, "Each player must be unique."

    bowlers = [p for p in players if p.can_bowl]

    if len(bowlers) < 5:
        return False, "Select at least 5 players who can bowl."

    return True, "Valid XI."


def generate_opponent(player_pool: list[Player], user_team: list[Player]) -> list[Player]:
    user_names = {p.name for p in user_team}
    available = [p for p in player_pool if p.name not in user_names]

    for _ in range(2000):
        opponent = random.sample(available, 11)
        if len([p for p in opponent if p.can_bowl]) >= 5:
            return opponent

    raise ValueError("Could not generate valid opponent team.")


def default_batting_order(players: list[Player]) -> list[Player]:
    path = DATA_DIR / "batting_position_profiles.csv"

    if not path.exists():
        return players

    profile = pd.read_csv(path)
    pos_map = dict(zip(profile["batter"], profile["avg_batting_position"]))

    return sorted(players, key=lambda p: pos_map.get(p.name, 99))


def default_bowling_plan(bowlers: list[Player]) -> list[Player]:
    """
    Builds a 20-over default bowling plan.

    Rules:
    - Max 4 overs per bowler
    - Same bowler cannot bowl two consecutive overs
    - Prefer historical phase usage where available
    """

    path = DATA_DIR / "bowling_phase_usage.csv"
    usage = pd.read_csv(path) if path.exists() else None

    plan = []
    overs_used = {b.name: 0 for b in bowlers}

    previous_bowler_name = None

    for over in range(1, 21):
        if over <= 6:
            phase = "powerplay"
        elif over <= 15:
            phase = "middle"
        else:
            phase = "death"

        eligible = [
            b for b in bowlers
            if overs_used[b.name] < 4 and b.name != previous_bowler_name
        ]

        if not eligible:
            eligible = [
                b for b in bowlers
                if overs_used[b.name] < 4
            ]

        if not eligible:
            break

        if usage is not None:
            scored = []

            for b in eligible:
                row = usage[
                    (usage["bowler"] == b.name)
                    & (usage["phase"] == phase)
                ]

                score = (
                    float(row["phase_usage_probability"].iloc[0])
                    if not row.empty
                    else 0.0
                )

                scored.append((b, score))

            max_score = max(score for _, score in scored)

            if max_score > 0:
                best = [b for b, score in scored if score == max_score]
                chosen = random.choice(best)
            else:
                chosen = random.choice(eligible)
        else:
            chosen = random.choice(eligible)

        plan.append(chosen)
        overs_used[chosen.name] += 1
        previous_bowler_name = chosen.name

    return plan


def batting_scorecard_df(scorecard: dict) -> pd.DataFrame:
    rows = []

    for name, stats in scorecard.items():
        rows.append({
            "Batter": name,
            "R": stats.runs,
            "B": stats.balls,
            "4s": stats.fours,
            "6s": stats.sixes,
            "SR": strike_rate(stats.runs, stats.balls),
            "Status": stats.dismissal,
        })

    return pd.DataFrame(rows)


def bowling_scorecard_df(scorecard: dict) -> pd.DataFrame:
    rows = []

    for name, stats in scorecard.items():
        rows.append({
            "Bowler": name,
            "O": overs_from_balls(stats.balls),
            "M": stats.maidens,
            "R": stats.runs,
            "W": stats.wickets,
            "Wd": stats.wides,
            "Nb": stats.no_balls,
            "Econ": economy_rate(stats.runs, stats.balls),
        })

    return pd.DataFrame(rows)