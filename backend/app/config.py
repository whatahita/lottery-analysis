from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = Path(os.getenv("LOTTERY_DATA_DIR", str(ROOT_DIR / "data")))
DB_PATH = DATA_DIR / "lottery.sqlite3"


@dataclass(frozen=True)
class LotteryConfig:
    key: str
    name: str
    cwl_name: str
    numbers_per_draw: int
    number_min: int
    number_max: int
    special_min: int | None = None
    special_max: int | None = None


LOTTERIES: dict[str, LotteryConfig] = {
    "ssq": LotteryConfig(
        key="ssq",
        name="双色球",
        cwl_name="ssq",
        numbers_per_draw=6,
        number_min=1,
        number_max=33,
        special_min=1,
        special_max=16,
    ),
    "kl8": LotteryConfig(
        key="kl8",
        name="快乐8",
        cwl_name="kl8",
        numbers_per_draw=20,
        number_min=1,
        number_max=80,
    ),
    "fc3d": LotteryConfig(
        key="fc3d",
        name="福彩3D",
        cwl_name="3d",
        numbers_per_draw=3,
        number_min=0,
        number_max=9,
    ),
}


def get_lottery(lottery_type: str) -> LotteryConfig:
    try:
        return LOTTERIES[lottery_type]
    except KeyError as exc:
        supported = ", ".join(LOTTERIES)
        raise ValueError(f"Unsupported lottery type '{lottery_type}'. Supported: {supported}") from exc
