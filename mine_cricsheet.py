import json
import zipfile
from io import BytesIO
from pathlib import Path

import pandas as pd
import requests
from tqdm import tqdm


DOWNLOADS = {
    "t20i": "https://cricsheet.org/downloads/t20s_json.zip",
    "ipl": "https://cricsheet.org/downloads/ipl_json.zip",
}

OUT_DIR = Path("data/mined")
OUTCOMES = ["0", "1", "2", "3", "4", "6", "W", "Wd", "Nb"]


def innings_phase(over_number_zero_indexed: int) -> str:
    over_number = over_number_zero_indexed + 1

    if over_number <= 6:
        return "powerplay"
    if over_number <= 15:
        return "middle"
    return "death"


def delivery_outcome(delivery: dict) -> str:
    extras = delivery.get("extras", {})

    if "wides" in extras:
        return "Wd"

    if "noballs" in extras:
        return "Nb"

    if delivery.get("wickets"):
        return "W"

    batter_runs = delivery.get("runs", {}).get("batter", 0)

    if batter_runs in [0, 1, 2, 3, 4, 6]:
        return str(batter_runs)

    return "0"


def is_legal_ball(delivery: dict) -> bool:
    extras = delivery.get("extras", {})
    return "wides" not in extras and "noballs" not in extras


def parse_match(match_json: dict, match_id: str, source: str) -> list[dict]:
    info = match_json.get("info", {})
    # Only include men's matches
    gender = str(info.get("gender", "")).strip().lower()

    if gender not in ["male", "men"]:
        return []

    venue = info.get("venue", "Unknown")
    dates = info.get("dates", [])
    match_date = dates[0] if dates else None
    event = info.get("event", {})
    competition = event.get("name", source)

    rows = []

    innings_list = match_json.get("innings", [])

    for innings_index, innings in enumerate(innings_list, start=1):
        batting_team = innings.get("team", "Unknown")

        for over_obj in innings.get("overs", []):
            over_zero = over_obj.get("over")
            phase = innings_phase(over_zero)

            legal_ball_number = 0

            for raw_ball_index, delivery in enumerate(over_obj.get("deliveries", []), start=1):
                legal = is_legal_ball(delivery)

                if legal:
                    legal_ball_number += 1

                batter = delivery.get("batter")
                bowler = delivery.get("bowler")
                non_striker = delivery.get("non_striker")

                if not batter or not bowler:
                    continue

                outcome = delivery_outcome(delivery)
                runs = delivery.get("runs", {})

                rows.append({
                    "source": source,
                    "competition": competition,
                    "match_id": match_id,
                    "match_date": match_date,
                    "venue": venue,
                    "innings": innings_index,
                    "batting_team": batting_team,
                    "over": over_zero + 1,
                    "raw_ball_index": raw_ball_index,
                    "legal_ball_in_over": legal_ball_number if legal else None,
                    "phase": phase,
                    "batter": batter,
                    "bowler": bowler,
                    "non_striker": non_striker,
                    "outcome": outcome,
                    "batter_runs": runs.get("batter", 0),
                    "extras": runs.get("extras", 0),
                    "total_runs": runs.get("total", 0),
                    "is_wicket": outcome == "W",
                    "is_legal_ball": legal,
                })

    return rows


def download_source(source: str, url: str) -> pd.DataFrame:
    print(f"Downloading {source}: {url}")

    response = requests.get(url, timeout=180)
    response.raise_for_status()

    all_rows = []

    with zipfile.ZipFile(BytesIO(response.content)) as z:
        json_files = [f for f in z.namelist() if f.endswith(".json")]

        for filename in tqdm(json_files, desc=f"Parsing {source}"):
            match_id = Path(filename).stem

            try:
                with z.open(filename) as f:
                    match_json = json.load(f)

                all_rows.extend(parse_match(match_json, match_id, source))

            except Exception as exc:
                print(f"Skipped {filename}: {exc}")

    return pd.DataFrame(all_rows)


def add_missing_outcomes(prob_df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    groups = prob_df[group_cols].drop_duplicates()
    outcomes = pd.DataFrame({"outcome": OUTCOMES})

    full = groups.merge(outcomes, how="cross")
    out = full.merge(prob_df, on=group_cols + ["outcome"], how="left")

    out["n"] = out["n"].fillna(0)

    out["total_n"] = (
        out.groupby(group_cols)["n"]
        .transform("sum")
        .replace(0, pd.NA)
    )

    out["probability_raw"] = (out["n"] / out["total_n"]).fillna(0)

    return out


def make_probs(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    counts = (
        df.groupby(group_cols + ["outcome"])
        .size()
        .reset_index(name="n")
    )

    totals = (
        counts.groupby(group_cols)["n"]
        .sum()
        .reset_index(name="total_n")
    )

    probs = counts.merge(totals, on=group_cols, how="left")
    probs["probability_raw"] = probs["n"] / probs["total_n"]

    return add_missing_outcomes(probs, group_cols)


def smooth_against_fallback(
    specific: pd.DataFrame,
    fallback: pd.DataFrame,
    specific_group_cols: list[str],
    fallback_group_cols: list[str],
    alpha: int,
) -> pd.DataFrame:
    fb = fallback[fallback_group_cols + ["outcome", "probability_raw"]].copy()
    fb = fb.rename(columns={"probability_raw": "fallback_probability"})

    merged = specific.merge(
        fb,
        on=fallback_group_cols + ["outcome"],
        how="left",
    )

    merged["fallback_probability"] = merged["fallback_probability"].fillna(
        1 / len(OUTCOMES)
    )

    merged["probability"] = (
        merged["n"] + alpha * merged["fallback_probability"]
    ) / (
        merged["total_n"] + alpha
    )

    return merged


def build_probability_tables(ball_df: pd.DataFrame):
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    league_phase = make_probs(ball_df, ["phase"])
    league_phase["probability"] = league_phase["probability_raw"]
    league_phase.to_csv(OUT_DIR / "league_phase_probs.csv", index=False)

    batter_phase = make_probs(ball_df, ["batter", "phase"])
    batter_phase = smooth_against_fallback(
        batter_phase,
        league_phase,
        ["batter", "phase"],
        ["phase"],
        alpha=40,
    )
    batter_phase.to_csv(OUT_DIR / "batter_phase_probs.csv", index=False)

    bowler_phase = make_probs(ball_df, ["bowler", "phase"])
    bowler_phase = smooth_against_fallback(
        bowler_phase,
        league_phase,
        ["bowler", "phase"],
        ["phase"],
        alpha=40,
    )
    bowler_phase.to_csv(OUT_DIR / "bowler_phase_probs.csv", index=False)

    batter_bowler_phase = make_probs(ball_df, ["batter", "bowler", "phase"])
    batter_bowler_phase = smooth_against_fallback(
        batter_bowler_phase,
        league_phase,
        ["batter", "bowler", "phase"],
        ["phase"],
        alpha=80,
    )
    batter_bowler_phase.to_csv(
        OUT_DIR / "batter_bowler_phase_probs.csv",
        index=False,
    )

    ground_phase = make_probs(ball_df, ["venue", "phase"])
    ground_phase = smooth_against_fallback(
        ground_phase,
        league_phase,
        ["venue", "phase"],
        ["phase"],
        alpha=100,
    )
    ground_phase.to_csv(OUT_DIR / "ground_phase_probs.csv", index=False)


def build_ground_modifiers():
    league = pd.read_csv(OUT_DIR / "league_phase_probs.csv")
    ground = pd.read_csv(OUT_DIR / "ground_phase_probs.csv")

    league_wide = league.pivot_table(
        index="phase",
        columns="outcome",
        values="probability",
        fill_value=0,
    ).reset_index()

    ground_wide = ground.pivot_table(
        index=["venue", "phase"],
        columns="outcome",
        values="probability",
        fill_value=0,
    ).reset_index()

    merged = ground_wide.merge(
        league_wide,
        on="phase",
        suffixes=("_ground", "_league"),
        how="left",
    )

    for outcome, label in [("4", "four"), ("6", "six"), ("W", "wicket")]:
        merged[f"{label}_modifier"] = (
            merged[f"{outcome}_ground"] / merged[f"{outcome}_league"]
        ).replace([float("inf"), -float("inf")], 1).fillna(1)

        merged[f"{label}_modifier"] = merged[f"{label}_modifier"].clip(0.5, 1.8)

    ground_modifiers = merged[
        ["venue", "phase", "four_modifier", "six_modifier", "wicket_modifier"]
    ]

    ground_modifiers.to_csv(OUT_DIR / "ground_modifiers.csv", index=False)


def build_batting_profiles(ball_df: pd.DataFrame):
    legal = ball_df[ball_df["is_legal_ball"]].copy()

    first_seen = (
        legal.sort_values(["match_id", "innings", "over", "legal_ball_in_over"])
        .groupby(["match_id", "innings", "batter"])
        .first()
        .reset_index()
    )

    first_seen = first_seen.sort_values(
        ["match_id", "innings", "over", "legal_ball_in_over"]
    )

    first_seen["batting_position_proxy"] = (
        first_seen.groupby(["match_id", "innings"]).cumcount() + 1
    )

    profile = (
        first_seen.groupby("batter")
        .agg(
            avg_batting_position=("batting_position_proxy", "mean"),
            innings_seen=("match_id", "count"),
        )
        .reset_index()
        .sort_values("avg_batting_position")
    )

    profile.to_csv(OUT_DIR / "batting_position_profiles.csv", index=False)


def build_bowling_profiles(ball_df: pd.DataFrame):
    legal = ball_df[ball_df["is_legal_ball"]].copy()

    usage = (
        legal.groupby(["bowler", "phase"])
        .size()
        .reset_index(name="legal_balls")
    )

    usage["overs"] = usage["legal_balls"] / 6

    totals = (
        usage.groupby("bowler")["overs"]
        .sum()
        .reset_index(name="total_overs")
    )

    usage = usage.merge(totals, on="bowler", how="left")
    usage["phase_usage_probability"] = usage["overs"] / usage["total_overs"]

    usage.to_csv(OUT_DIR / "bowling_phase_usage.csv", index=False)


def build_player_pool(ball_df: pd.DataFrame):
    batters = (
        ball_df.groupby("batter")
        .size()
        .reset_index(name="balls_faced_events")
        .rename(columns={"batter": "player"})
    )

    bowlers = (
        ball_df[ball_df["is_legal_ball"]]
        .groupby("bowler")
        .size()
        .reset_index(name="legal_balls_bowled")
        .rename(columns={"bowler": "player"})
    )

    players = batters.merge(bowlers, on="player", how="outer").fillna(0)

    players["can_bowl"] = players["legal_balls_bowled"] >= 60

    def role(row):
        if row["can_bowl"] and row["balls_faced_events"] >= 100:
            return "All-rounder"
        if row["can_bowl"]:
            return "Bowler"
        return "Batter"

    players["role"] = players.apply(role, axis=1)

    players = players.sort_values(
        ["balls_faced_events", "legal_balls_bowled"],
        ascending=False,
    )

    players.to_csv(OUT_DIR / "player_pool.csv", index=False)


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    all_dfs = []

    for source, url in DOWNLOADS.items():
        all_dfs.append(download_source(source, url))

    ball_df = pd.concat(all_dfs, ignore_index=True)

    ball_df.to_csv(OUT_DIR / "cricsheet_t20_ipl_ball_by_ball.csv", index=False)

    build_probability_tables(ball_df)
    build_ground_modifiers()
    build_batting_profiles(ball_df)
    build_bowling_profiles(ball_df)
    build_player_pool(ball_df)

    print("\nDone.")
    print(f"Files saved to: {OUT_DIR.resolve()}")


if __name__ == "__main__":
    main()