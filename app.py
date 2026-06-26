import random
import time

import pandas as pd
import streamlit as st

from simulator import simulate_innings
from utils import (
    load_player_pool,
    load_venues,
    validate_team,
    generate_opponent,
    default_batting_order,
    default_bowling_plan,
    batting_scorecard_df,
    bowling_scorecard_df,
    overs_from_balls,
)


st.set_page_config(
    page_title="T20 Cricket Match Simulator",
    layout="wide",
)

st.title("T20 Cricket Match Simulator")


@st.cache_data
def cached_player_pool():
    return load_player_pool()


@st.cache_data
def cached_venues():
    return load_venues()


def over_log_to_df(over_log):
    return pd.DataFrame([
        {
            "Over": over["over"],
            "Bowler": over["bowler"],
            "Balls": " ".join(over["balls"]),
            "Runs": over["runs"],
            "Wickets": over["wickets"],
            "Score": over["score"],
        }
        for over in over_log
    ])


def show_final_innings_scorecard(innings):
    st.subheader(f"{innings.team_name} Final Scorecard")

    st.write(
        f"**{innings.team_name}: "
        f"{innings.score}/{innings.wickets} "
        f"({overs_from_balls(innings.legal_balls)} overs)**"
    )

    st.write("Batting")
    st.dataframe(
        batting_scorecard_df(innings.batting_scorecard),
        use_container_width=True,
    )

    st.write("Bowling")
    st.dataframe(
        bowling_scorecard_df(innings.bowling_scorecard),
        use_container_width=True,
    )


def play_innings_progressively(innings, delay_seconds):
    st.header(f"{innings.team_name} Innings")

    live_score = st.empty()
    live_latest_over = st.empty()
    live_over_table = st.empty()

    shown_overs = []

    for over in innings.over_log:
        shown_overs.append(over)

        live_score.markdown(
            f"### {innings.team_name}: {over['score']} after {over['over']} overs"
        )

        live_latest_over.markdown(
            f"""
            **Over {over['over']} - {over['bowler']}**  
            Balls: `{" ".join(over["balls"])}`  
            Runs: **{over["runs"]}**, Wickets: **{over["wickets"]}**
            """
        )

        live_over_table.dataframe(
            over_log_to_df(shown_overs),
            use_container_width=True,
        )

        time.sleep(delay_seconds)

    st.success(f"{innings.team_name} innings complete.")
    show_final_innings_scorecard(innings)


def has_consecutive_bowler(plan_names):
    for i in range(1, len(plan_names)):
        if plan_names[i] == plan_names[i - 1]:
            return True
    return False


def validate_bowling_plan(plan_names):
    over_counts = {
        name: plan_names.count(name)
        for name in set(plan_names)
    }

    over_limit_breaches = [
        name for name, count in over_counts.items()
        if count > 4
    ]

    if over_limit_breaches:
        return False, f"These bowlers have more than 4 overs: {over_limit_breaches}"

    if has_consecutive_bowler(plan_names):
        return False, "The same bowler cannot bowl two consecutive overs."

    return True, "Valid bowling plan."


try:
    PLAYER_POOL = cached_player_pool()
    VENUES = cached_venues()
except FileNotFoundError:
    st.error("Run `python mine_cricsheet.py` first, then restart the app.")
    st.stop()


PLAYER_LOOKUP = {p.name: p for p in PLAYER_POOL}
PLAYER_NAMES = sorted(PLAYER_LOOKUP.keys())


if "match_ready" not in st.session_state:
    st.session_state.match_ready = False

if "simulated" not in st.session_state:
    st.session_state.simulated = False


st.sidebar.header("Match Setup")

ground_name = st.sidebar.selectbox("Ground", VENUES)

animation_speed = st.sidebar.slider(
    "Over-by-over speed",
    min_value=0.0,
    max_value=2.0,
    value=0.6,
    step=0.1,
    help="Seconds to wait between overs during match simulation.",
)

st.sidebar.divider()

selected_names = st.sidebar.multiselect(
    "Select your playing XI",
    PLAYER_NAMES,
    default=PLAYER_NAMES[:11],
)

selected_players = [PLAYER_LOOKUP[name] for name in selected_names]

valid_team, msg = validate_team(selected_players)

if valid_team:
    st.sidebar.success(f"Your team: {msg}")
else:
    st.sidebar.error(f"Your team: {msg}")


opponent_mode = st.sidebar.radio(
    "Opponent team",
    ["Random opponent", "Select opponent manually"],
    horizontal=False,
)

manual_opponent_players = []

if opponent_mode == "Select opponent manually":
    unavailable_names = set(selected_names)
    opponent_options = [
        name for name in PLAYER_NAMES
        if name not in unavailable_names
    ]

    default_opponent = opponent_options[:11]

    opponent_names = st.sidebar.multiselect(
        "Select opponent XI",
        opponent_options,
        default=default_opponent,
    )

    manual_opponent_players = [PLAYER_LOOKUP[name] for name in opponent_names]

    valid_opponent, opponent_msg = validate_team(manual_opponent_players)

    if valid_opponent:
        st.sidebar.success(f"Opponent: {opponent_msg}")
    else:
        st.sidebar.error(f"Opponent: {opponent_msg}")
else:
    valid_opponent = True


if valid_team and valid_opponent:
    possible_bowlers = [p for p in selected_players if p.can_bowl]

    selected_bowler_names = st.sidebar.multiselect(
        "Select your bowling options",
        [p.name for p in possible_bowlers],
        default=[p.name for p in possible_bowlers],
    )

    selected_bowlers = [PLAYER_LOOKUP[name] for name in selected_bowler_names]

    if len(selected_bowlers) < 5:
        st.sidebar.error("Select at least 5 bowling options.")
    else:
        if st.sidebar.button("Generate Match"):
            if opponent_mode == "Random opponent":
                opponent_team = generate_opponent(PLAYER_POOL, selected_players)
            else:
                opponent_team = manual_opponent_players

            toss_winner = random.choice(["User", "Opponent"])
            opponent_decision = random.choice(["bat", "bowl"])

            st.session_state.user_team = selected_players
            st.session_state.user_bowlers = selected_bowlers
            st.session_state.opponent_team = opponent_team
            st.session_state.ground_name = ground_name
            st.session_state.toss_winner = toss_winner
            st.session_state.opponent_decision = opponent_decision
            st.session_state.match_ready = True
            st.session_state.simulated = False


if st.session_state.match_ready:
    user_team = st.session_state.user_team
    user_bowlers = st.session_state.user_bowlers
    opponent_team = st.session_state.opponent_team
    ground_name = st.session_state.ground_name

    ground_info = {"venue": ground_name}

    st.subheader("Ground")
    st.write(ground_name)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Your XI")
        st.dataframe(
            [{"Player": p.name, "Role": p.role, "Can bowl": p.can_bowl} for p in user_team],
            use_container_width=True,
        )

    with col2:
        st.subheader("Opponent XI")
        st.dataframe(
            [{"Player": p.name, "Role": p.role, "Can bowl": p.can_bowl} for p in opponent_team],
            use_container_width=True,
        )

    st.divider()

    st.subheader("Toss")

    toss_winner = st.session_state.toss_winner

    if toss_winner == "User":
        toss_decision = st.radio(
            "You won the toss. Choose:",
            ["bat", "bowl"],
            horizontal=True,
        )
    else:
        toss_decision = st.session_state.opponent_decision
        st.write(f"Opponent won the toss and chose to **{toss_decision}**.")

    user_bats_first = (
        toss_winner == "User" and toss_decision == "bat"
    ) or (
        toss_winner == "Opponent" and toss_decision == "bowl"
    )

    st.divider()

    st.subheader("Confirm Your Batting Order")

    default_user_order = default_batting_order(user_team)
    user_order_names = []

    for i in range(11):
        options = [p.name for p in user_team]
        default_name = default_user_order[i].name

        name = st.selectbox(
            f"Your batter {i + 1}",
            options,
            index=options.index(default_name),
            key=f"user_bat_{i}",
        )

        user_order_names.append(name)

    if len(set(user_order_names)) != 11:
        st.error("Your batting order has duplicate players.")
        valid_user_batting_order = False
    else:
        valid_user_batting_order = True

    user_batting_order = [PLAYER_LOOKUP[name] for name in user_order_names]

    st.divider()

    st.subheader("Confirm Opponent Batting Order")

    default_opponent_order = default_batting_order(opponent_team)
    opponent_order_names = []

    for i in range(11):
        options = [p.name for p in opponent_team]
        default_name = default_opponent_order[i].name

        name = st.selectbox(
            f"Opponent batter {i + 1}",
            options,
            index=options.index(default_name),
            key=f"opponent_bat_{i}",
        )

        opponent_order_names.append(name)

    if len(set(opponent_order_names)) != 11:
        st.error("Opponent batting order has duplicate players.")
        valid_opponent_batting_order = False
    else:
        valid_opponent_batting_order = True

    opponent_batting_order = [PLAYER_LOOKUP[name] for name in opponent_order_names]

    st.divider()

    st.subheader("Confirm Your Bowling Order")

    default_user_bowling = default_bowling_plan(user_bowlers)
    user_bowling_plan_names = []

    user_bowler_options = [p.name for p in user_bowlers]

    for over in range(20):
        default_name = default_user_bowling[over].name

        name = st.selectbox(
            f"Your bowler - Over {over + 1}",
            user_bowler_options,
            index=user_bowler_options.index(default_name),
            key=f"user_bowl_{over}",
        )

        user_bowling_plan_names.append(name)

    valid_user_bowling_order, user_bowling_msg = validate_bowling_plan(
        user_bowling_plan_names
    )

    if valid_user_bowling_order:
        st.success(user_bowling_msg)
    else:
        st.error(user_bowling_msg)

    user_bowling_plan = [PLAYER_LOOKUP[name] for name in user_bowling_plan_names]

    st.divider()

    st.subheader("Confirm Opponent Bowling Order")

    opponent_bowlers = [p for p in opponent_team if p.can_bowl]
    default_opponent_bowling = default_bowling_plan(opponent_bowlers)
    opponent_bowling_plan_names = []

    opponent_bowler_options = [p.name for p in opponent_bowlers]

    for over in range(20):
        default_name = default_opponent_bowling[over].name

        name = st.selectbox(
            f"Opponent bowler - Over {over + 1}",
            opponent_bowler_options,
            index=opponent_bowler_options.index(default_name),
            key=f"opponent_bowl_{over}",
        )

        opponent_bowling_plan_names.append(name)

    valid_opponent_bowling_order, opponent_bowling_msg = validate_bowling_plan(
        opponent_bowling_plan_names
    )

    if valid_opponent_bowling_order:
        st.success(opponent_bowling_msg)
    else:
        st.error(opponent_bowling_msg)

    opponent_bowling_plan = [
        PLAYER_LOOKUP[name]
        for name in opponent_bowling_plan_names
    ]

    st.divider()

    can_simulate = (
        valid_user_batting_order
        and valid_opponent_batting_order
        and valid_user_bowling_order
        and valid_opponent_bowling_order
    )

    if st.button("Simulate Full Match", disabled=not can_simulate):
        st.session_state.simulated = False

        if user_bats_first:
            innings_1 = simulate_innings(
                batting_team_name="Your Team",
                batting_order=user_batting_order,
                bowling_plan=opponent_bowling_plan,
                ground_info=ground_info,
            )

            play_innings_progressively(innings_1, animation_speed)

            st.divider()

            innings_2 = simulate_innings(
                batting_team_name="Opponent",
                batting_order=opponent_batting_order,
                bowling_plan=user_bowling_plan,
                ground_info=ground_info,
                target=innings_1.score,
            )

            play_innings_progressively(innings_2, animation_speed)

        else:
            innings_1 = simulate_innings(
                batting_team_name="Opponent",
                batting_order=opponent_batting_order,
                bowling_plan=user_bowling_plan,
                ground_info=ground_info,
            )

            play_innings_progressively(innings_1, animation_speed)

            st.divider()

            innings_2 = simulate_innings(
                batting_team_name="Your Team",
                batting_order=user_batting_order,
                bowling_plan=opponent_bowling_plan,
                ground_info=ground_info,
                target=innings_1.score,
            )

            play_innings_progressively(innings_2, animation_speed)

        st.session_state.innings_1 = innings_1
        st.session_state.innings_2 = innings_2
        st.session_state.simulated = True

        st.divider()
        st.header("Match Result")

        st.write(
            f"**{innings_1.team_name}**: "
            f"{innings_1.score}/{innings_1.wickets} "
            f"({overs_from_balls(innings_1.legal_balls)} overs)"
        )

        st.write(
            f"**{innings_2.team_name}**: "
            f"{innings_2.score}/{innings_2.wickets} "
            f"({overs_from_balls(innings_2.legal_balls)} overs)"
        )

        if innings_1.score > innings_2.score:
            st.success(
                f"{innings_1.team_name} won by "
                f"{innings_1.score - innings_2.score} runs."
            )
        elif innings_2.score > innings_1.score:
            st.success(
                f"{innings_2.team_name} won by "
                f"{10 - innings_2.wickets} wickets."
            )
        else:
            st.warning("Match tied.")