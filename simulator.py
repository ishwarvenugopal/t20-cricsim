from models import BatterStats, BowlerStats, InningsResult
from probabilities import get_ball_probabilities, sample_outcome


def simulate_innings(
    batting_team_name,
    batting_order,
    bowling_plan,
    ground_info,
    target=None,
):
    score = 0
    wickets = 0
    legal_balls = 0

    striker = batting_order[0]
    non_striker = batting_order[1]
    next_batter_index = 2

    batting_scorecard = {
        player.name: BatterStats()
        for player in batting_order
    }

    bowling_scorecard = {
        bowler.name: BowlerStats()
        for bowler in bowling_plan
    }

    over_log = []

    for over_index in range(20):
        if over_index >= len(bowling_plan):
            break

        over_number = over_index + 1
        bowler = bowling_plan[over_index]
        bowler_stats = bowling_scorecard[bowler.name]

        over_runs = 0
        over_wickets = 0
        over_balls = []
        legal_balls_this_over = 0

        while legal_balls_this_over < 6:
            probs = get_ball_probabilities(
                batter=striker,
                bowler=bowler,
                over_number=over_number,
                ground_info=ground_info,
            )

            outcome = sample_outcome(probs)
            over_balls.append(outcome)

            if outcome == "Wd":
                score += 1
                over_runs += 1
                bowler_stats.runs += 1
                bowler_stats.wides += 1

            elif outcome == "Nb":
                score += 1
                over_runs += 1
                bowler_stats.runs += 1
                bowler_stats.no_balls += 1

            else:
                legal_balls += 1
                legal_balls_this_over += 1
                bowler_stats.balls += 1

                batter_stats = batting_scorecard[striker.name]
                batter_stats.balls += 1

                if outcome in ["0", "1", "2", "3", "4", "6"]:
                    runs = int(outcome)

                    score += runs
                    over_runs += runs
                    bowler_stats.runs += runs
                    batter_stats.runs += runs

                    if runs == 4:
                        batter_stats.fours += 1

                    if runs == 6:
                        batter_stats.sixes += 1

                    if runs in [1, 3]:
                        striker, non_striker = non_striker, striker

                elif outcome == "W":
                    wickets += 1
                    over_wickets += 1
                    bowler_stats.wickets += 1

                    batter_stats.out = True
                    batter_stats.dismissal = f"b {bowler.name}"

                    if wickets >= 10:
                        break

                    striker = batting_order[next_batter_index]
                    next_batter_index += 1

            if target is not None and score > target:
                break

        if over_runs == 0:
            bowler_stats.maidens += 1

        over_log.append({
            "over": over_number,
            "bowler": bowler.name,
            "balls": over_balls,
            "runs": over_runs,
            "wickets": over_wickets,
            "score": f"{score}/{wickets}",
        })

        if wickets >= 10:
            break

        if target is not None and score > target:
            break

        striker, non_striker = non_striker, striker

    return InningsResult(
        team_name=batting_team_name,
        score=score,
        wickets=wickets,
        legal_balls=legal_balls,
        batting_scorecard=batting_scorecard,
        bowling_scorecard=bowling_scorecard,
        over_log=over_log,
    )