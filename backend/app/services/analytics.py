from __future__ import annotations

from collections import Counter
from statistics import mean

from ..config import LotteryConfig


def _number_range(config: LotteryConfig, special: bool = False) -> list[int]:
    if special and config.special_min is not None and config.special_max is not None:
        return list(range(config.special_min, config.special_max + 1))
    return list(range(config.number_min, config.number_max + 1))


def _format_number(value: int, config: LotteryConfig) -> str:
    if config.key == "fc3d":
        return str(value)
    return f"{value:02d}"


def _recent_draws(draws: list[dict], window: int) -> list[dict]:
    return sorted(draws, key=lambda item: (item["draw_date"], item["issue"]), reverse=True)[:window]


def calculate_stats(config: LotteryConfig, draws: list[dict], window: int = 30) -> dict:
    recent = _recent_draws(draws, window)
    all_desc = _recent_draws(draws, len(draws))
    numbers = _number_range(config)
    latest_numbers = set(all_desc[0]["numbers"]) if all_desc else set()

    recent_counter = Counter(num for draw in recent for num in draw["numbers"])
    full_counter = Counter(num for draw in all_desc for num in draw["numbers"])
    omission = {}
    for number in numbers:
        miss = 0
        for draw in all_desc:
            if number in draw["numbers"]:
                break
            miss += 1
        omission[number] = miss

    hot = recent_counter.most_common(10)
    cold = sorted(((num, recent_counter[num]) for num in numbers), key=lambda pair: (pair[1], -pair[0]))[:10]
    sums = [sum(draw["numbers"]) + sum(draw.get("special", [])) for draw in recent]
    odd = sum(1 for draw in recent for num in draw["numbers"] if num % 2 == 1)
    even = sum(1 for draw in recent for num in draw["numbers"] if num % 2 == 0)
    small_line = 5 if config.key == "fc3d" else (40 if config.key == "kl8" else 16)
    small = sum(1 for draw in recent for num in draw["numbers"] if num <= small_line)
    big = sum(1 for draw in recent for num in draw["numbers"] if num > small_line)

    zones = _zone_distribution(config, recent)
    trend = [
        {
            "issue": draw["issue"],
            "date": draw["draw_date"],
            "sum": sum(draw["numbers"]) + sum(draw.get("special", [])),
            "span": max(draw["numbers"]) - min(draw["numbers"]) if draw["numbers"] else 0,
        }
        for draw in reversed(recent)
    ]

    payload = {
        "lottery": config.key,
        "window": window,
        "draw_count": len(draws),
        "recent_count": len(recent),
        "hot": [{"number": _format_number(num, config), "count": count} for num, count in hot],
        "cold": [{"number": _format_number(num, config), "count": count} for num, count in cold],
        "omission": [
            {
                "number": _format_number(num, config),
                "miss": omission[num],
                "recent_count": recent_counter[num],
                "total_count": full_counter[num],
                "latest": num in latest_numbers,
            }
            for num in numbers
        ],
        "summary": {
            "avg_sum": round(mean(sums), 2) if sums else 0,
            "odd": odd,
            "even": even,
            "small": small,
            "big": big,
            "zones": zones,
        },
        "trend": trend,
    }

    if config.key == "ssq":
        payload["special"] = _special_stats(config, all_desc, recent)
    if config.key == "fc3d":
        payload["digits"] = _fc3d_digit_stats(recent)

    return payload


def _zone_distribution(config: LotteryConfig, draws: list[dict]) -> list[dict]:
    if config.key == "kl8":
        bounds = [(1, 20), (21, 40), (41, 60), (61, 80)]
    elif config.key == "ssq":
        bounds = [(1, 11), (12, 22), (23, 33)]
    else:
        bounds = [(0, 3), (4, 6), (7, 9)]

    zones = []
    for start, end in bounds:
        count = sum(1 for draw in draws for num in draw["numbers"] if start <= num <= end)
        zones.append({"label": f"{start}-{end}", "count": count})
    return zones


def _special_stats(config: LotteryConfig, all_desc: list[dict], recent: list[dict]) -> dict:
    numbers = _number_range(config, special=True)
    recent_counter = Counter(num for draw in recent for num in draw.get("special", []))
    omission = {}
    for number in numbers:
        miss = 0
        for draw in all_desc:
            if number in draw.get("special", []):
                break
            miss += 1
        omission[number] = miss

    return {
        "hot": [
            {"number": _format_number(num, config), "count": count}
            for num, count in recent_counter.most_common(8)
        ],
        "omission": [
            {"number": _format_number(num, config), "miss": omission[num], "recent_count": recent_counter[num]}
            for num in numbers
        ],
    }


def _fc3d_digit_stats(draws: list[dict]) -> list[dict]:
    labels = ["百位", "十位", "个位"]
    result = []
    for idx, label in enumerate(labels):
        counter = Counter(draw["numbers"][idx] for draw in draws if len(draw["numbers"]) > idx)
        result.append(
            {
                "position": label,
                "hot": [{"number": str(num), "count": count} for num, count in counter.most_common(5)],
            }
        )
    return result


def recommend(config: LotteryConfig, draws: list[dict], count: int = 5, window: int = 30) -> dict:
    stats = calculate_stats(config, draws, window)
    candidates = _score_numbers(config, draws, window, special=False)
    special_candidates = _score_numbers(config, draws, window, special=True) if config.key == "ssq" else []

    rows = []
    for offset in range(max(1, count)):
        selected = _pick_group(config, candidates, offset)
        special = []
        if config.key == "ssq" and special_candidates:
            special = [special_candidates[offset % len(special_candidates)]]
        rows.append(
            {
                "numbers": [_format_number(item["number"], config) for item in sorted(selected, key=lambda x: x["number"])],
                "special": [_format_number(item["number"], config) for item in special],
                "score": round(sum(item["score"] for item in selected + special), 2),
                "reasons": _summarize_reasons(selected + special),
            }
        )

    return {
        "lottery": config.key,
        "count": len(rows),
        "warning": "彩票开奖结果具有随机性，以下号码仅基于历史统计评分，不能保证中奖。",
        "recommendations": rows,
        "basis": {
            "window": window,
            "draw_count": stats["draw_count"],
            "factors": ["近期热度", "长期频率", "遗漏回补", "上期重复降权", "区间轮换"],
        },
    }


def _score_numbers(config: LotteryConfig, draws: list[dict], window: int, special: bool) -> list[dict]:
    if special and config.special_min is None:
        return []

    all_desc = _recent_draws(draws, len(draws))
    recent = _recent_draws(draws, window)
    numbers = _number_range(config, special=special)
    field = "special" if special else "numbers"
    recent_counter = Counter(num for draw in recent for num in draw.get(field, []))
    full_counter = Counter(num for draw in all_desc for num in draw.get(field, []))
    latest = set(all_desc[0].get(field, [])) if all_desc else set()
    max_recent = max(recent_counter.values() or [1])
    max_full = max(full_counter.values() or [1])

    scored = []
    for number in numbers:
        miss = 0
        for draw in all_desc:
            if number in draw.get(field, []):
                break
            miss += 1

        heat = recent_counter[number] / max_recent
        long_term = full_counter[number] / max_full
        omission_score = min(miss / max(window, 1), 1.4)
        repeat_penalty = 0.25 if number in latest else 0
        score = heat * 42 + long_term * 24 + omission_score * 28 - repeat_penalty * 20
        scored.append(
            {
                "number": number,
                "score": score,
                "recent_count": recent_counter[number],
                "total_count": full_counter[number],
                "miss": miss,
            }
        )

    return sorted(scored, key=lambda item: (item["score"], item["miss"]), reverse=True)


def _pick_group(config: LotteryConfig, candidates: list[dict], offset: int) -> list[dict]:
    need = config.numbers_per_draw
    if config.key == "fc3d":
        pool = candidates[offset : offset + need]
        if len(pool) < need:
            pool = candidates[:need]
        return pool

    selected = []
    zones = _zone_distribution_for_numbers(config)
    zone_counts = {idx: 0 for idx in range(len(zones))}
    for item in candidates[offset:] + candidates[:offset]:
        zone = _zone_index(item["number"], zones)
        cap = max(1, need // len(zones) + 1)
        if zone_counts[zone] >= cap:
            continue
        selected.append(item)
        zone_counts[zone] += 1
        if len(selected) == need:
            return selected
    return candidates[:need]


def _zone_distribution_for_numbers(config: LotteryConfig) -> list[tuple[int, int]]:
    if config.key == "kl8":
        return [(1, 20), (21, 40), (41, 60), (61, 80)]
    if config.key == "ssq":
        return [(1, 11), (12, 22), (23, 33)]
    return [(0, 3), (4, 6), (7, 9)]


def _zone_index(number: int, zones: list[tuple[int, int]]) -> int:
    for idx, (start, end) in enumerate(zones):
        if start <= number <= end:
            return idx
    return 0


def _summarize_reasons(items: list[dict]) -> list[str]:
    top = sorted(items, key=lambda item: item["score"], reverse=True)[:3]
    return [
        f"{item['number']}：近期开奖{item['recent_count']}次，当前遗漏{item['miss']}期，综合评分{item['score']:.1f}"
        for item in top
    ]

