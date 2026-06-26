from dataclasses import dataclass, field


@dataclass(frozen=True)
class Player:
    name: str
    role: str = "Unknown"
    can_bowl: bool = False


@dataclass
class BatterStats:
    runs: int = 0
    balls: int = 0
    fours: int = 0
    sixes: int = 0
    out: bool = False
    dismissal: str = "not out"


@dataclass
class BowlerStats:
    balls: int = 0
    runs: int = 0
    wickets: int = 0
    wides: int = 0
    no_balls: int = 0
    maidens: int = 0


@dataclass
class InningsResult:
    team_name: str
    score: int
    wickets: int
    legal_balls: int
    batting_scorecard: dict = field(default_factory=dict)
    bowling_scorecard: dict = field(default_factory=dict)
    over_log: list = field(default_factory=list)