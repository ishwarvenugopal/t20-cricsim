# 🏏 T20 Cricket Match Simulator

A data-driven T20 cricket simulator built using historical **ball-by-ball data** from Cricsheet. Instead of relying on arbitrary probabilities, every delivery in the simulation is based on real historical outcomes from men's **T20 Internationals (T20Is)** and the **Indian Premier League (IPL)**.

The project combines data mining, statistical probability modelling and match simulation to create realistic T20 matches where users can build teams, choose batting and bowling orders, and watch a complete match unfold over by over.

---

# Features

## Data-driven simulation

The simulator mines thousands of real deliveries from Cricsheet to estimate probabilities for every ball.

For every delivery, the simulator attempts to use:

1. Batter vs Bowler + Match Phase
2. Batter + Match Phase
3. Bowler + Match Phase
4. League-wide Match Phase

This hierarchical fallback system allows even players with limited historical data to be simulated realistically.

---

## Real T20 phases

Each innings is divided into:

| Phase        | Overs |
| ------------ | ----- |
| Powerplay    | 1–6   |
| Middle Overs | 7–15  |
| Death Overs  | 16–20 |

Separate probability distributions are built for each phase.

---

## Venue adjustments

Ground-specific modifiers are mined from historical matches.

Each venue adjusts:

* Boundary frequency
* Six frequency
* Wicket probability

This produces noticeably different behaviour between batting-friendly and bowling-friendly grounds.

---

## Team selection

Users can:

* Select their own Playing XI
* Select an opponent manually
* Generate a random opponent
* Choose available bowlers
* Select batting order
* Select bowling order

Validation ensures:

* Exactly 11 players
* At least 5 bowling options
* Maximum 4 overs per bowler
* No consecutive overs by the same bowler

---

## Toss simulation

A toss is performed before every match.

If the user wins the toss they may choose whether to bat or bowl first.

---

## Live over-by-over simulation

Rather than displaying the final score immediately, the simulator plays through the innings over by over.

For every over the app displays:

* Current score
* Bowler
* Ball outcomes
* Runs scored
* Wickets taken

At the completion of the innings a full scorecard is displayed before the second innings begins.

---

## Scorecards

For every innings the simulator generates complete batting and bowling scorecards.

Batting statistics include:

* Runs
* Balls
* Fours
* Sixes
* Strike Rate
* Dismissal

Bowling statistics include:

* Overs
* Maidens
* Runs
* Wickets
* Wides
* No Balls
* Economy

---

# Project Structure

```text
.
├── app.py
├── mine_cricsheet.py
├── models.py
├── probabilities.py
├── simulator.py
├── utils.py
├── requirements.txt
│
└── data/
    └── mined/
```

---

# Building the Database

The simulator first mines all historical ball-by-ball data from Cricsheet.

Simply run

```bash
python mine_cricsheet.py
```

This script downloads and processes

* Men's T20 Internationals
* Men's IPL matches

The mining process creates:

```text
data/mined/

cricsheet_t20_ipl_ball_by_ball.csv

league_phase_probs.csv

batter_phase_probs.csv

bowler_phase_probs.csv

batter_bowler_phase_probs.csv

ground_phase_probs.csv

ground_modifiers.csv

batting_position_profiles.csv

bowling_phase_usage.csv

player_pool.csv
```

This only needs to be run again when new matches are added to Cricsheet.

---

# Running the Simulator

Start the Streamlit application

```bash
streamlit run app.py
```

---

# Probability Model

Every delivery follows the hierarchy

```
Batter vs Bowler (same phase)
        ↓
Batter (same phase)
        ↓
Bowler (same phase)
        ↓
League Average (same phase)
        ↓
Venue Modifiers
```

This prevents unrealistic behaviour for players with limited historical data while still rewarding strong player-specific records.

---

# Data Mining Pipeline

The mining script performs the following steps.

## 1. Download

Downloads all available

* Men's T20I matches
* Men's IPL matches

from Cricsheet.

---

## 2. Parse

Every delivery is extracted into a flat dataset.

Each row contains information including

* Batter
* Bowler
* Venue
* Innings
* Over
* Phase
* Runs
* Extras
* Wicket
* Delivery outcome

---

## 3. Build Probability Tables

Historical probabilities are generated for

* Batter × Bowler × Phase
* Batter × Phase
* Bowler × Phase
* League × Phase

---

## 4. Venue Modifiers

Ground-specific modifiers are calculated for

* Boundary frequency
* Six frequency
* Wicket frequency

relative to the league average.

---

## 5. Player Profiles

The miner estimates

* Average batting position
* Bowling phase usage
* Player roles
* Bowling eligibility

These profiles are used to generate sensible default batting and bowling orders.

---

# Current Assumptions

The simulator currently models:

* Phase-dependent batting
* Venue effects
* Historical batting order
* Historical bowling usage
* Maximum 4 overs per bowler
* No consecutive overs by the same bowler
* Toss
* Chasing logic

The current model does **not** yet account for

* Batter handedness
* Bowling style
* Pitch type
* Weather
* Dew
* Injuries
* Match pressure
* Fatigue
* Player form
* Captaincy strategy

---

# Data Source

This project uses publicly available ball-by-ball data from **Cricsheet**, which provides detailed structured scorecards and match data for international and domestic cricket competitions.

Please support the Cricsheet project if you find their datasets useful.

---

# Disclaimer

This simulator is intended for entertainment, educational and statistical exploration purposes.

Although every delivery is based on historical probabilities, simulated matches are stochastic and should not be interpreted as predictive models for real-world outcomes.


