from __future__ import annotations

import re
from datetime import datetime
from typing import Any

import httpx

from ..config import LotteryConfig


CWL_ENDPOINT = "https://www.cwl.gov.cn/cwl_admin/front/cwlkj/search/kjxx/findDrawNotice"
FIVE_HUNDRED_URLS = {
    "ssq": "https://www.500.com/kaijiang/ssq/lskj/",
    "kl8": "https://www.500.com/kaijiang/kl8/lskj/",
    "fc3d": "https://www.500.com/kaijiang/3d/lskj/",
}


class FetchError(RuntimeError):
    pass


def _split_numbers(value: str) -> list[int]:
    return [int(item) for item in re.findall(r"\d+", value or "")]


def _normalize_date(value: str) -> str:
    value = (value or "").strip()
    for fmt in ("%Y-%m-%d", "%Y/%m/%d", "%Y年%m月%d日"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except ValueError:
            continue
    return value[:10]


def _parse_draw(config: LotteryConfig, item: dict[str, Any]) -> dict | None:
    issue = str(item.get("code") or item.get("issue") or item.get("qh") or "").strip()
    date = item.get("date") or item.get("drawDate") or item.get("kjsj") or ""
    red = item.get("red") or item.get("number") or item.get("hm") or item.get("kjhm") or ""
    blue = item.get("blue") or item.get("special") or ""

    numbers = _split_numbers(str(red))
    special = _split_numbers(str(blue))

    if config.key == "ssq":
        if len(numbers) < 6:
            return None
        numbers = numbers[:6]
        special = special[:1]
    elif config.key == "kl8":
        if len(numbers) < 20:
            return None
        numbers = numbers[:20]
        special = []
    elif config.key == "fc3d":
        if len(numbers) < 3:
            return None
        numbers = numbers[:3]
        special = []

    if not _valid_numbers(config, numbers, special):
        return None
    if not issue or not date:
        return None

    return {
        "issue": issue,
        "draw_date": _normalize_date(str(date)),
        "numbers": numbers,
        "special": special,
        "source": "中国福彩网",
    }


def _valid_numbers(config: LotteryConfig, numbers: list[int], special: list[int]) -> bool:
    if len(numbers) != config.numbers_per_draw:
        return False
    if any(num < config.number_min or num > config.number_max for num in numbers):
        return False
    if config.key != "fc3d" and len(set(numbers)) != len(numbers):
        return False
    if config.special_min is not None and config.special_max is not None:
        return len(special) == 1 and config.special_min <= special[0] <= config.special_max
    return not special


async def fetch_cwl_draws(config: LotteryConfig, page_size: int = 100) -> list[dict]:
    params = {
        "name": config.cwl_name,
        "issueCount": "",
        "issueStart": "",
        "issueEnd": "",
        "dayStart": "",
        "dayEnd": "",
        "pageNo": 1,
        "pageSize": page_size,
        "week": "",
        "systemType": "PC",
    }
    headers = {
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "User-Agent": "Mozilla/5.0 lottery-analysis-local/1.0",
        "Referer": "https://www.cwl.gov.cn/ygkj/kjgg/",
        "X-Requested-With": "XMLHttpRequest",
    }

    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
        response = await client.get(CWL_ENDPOINT, params=params)
        response.raise_for_status()
        payload = response.json()

    result = payload.get("result")
    if not isinstance(result, list):
        raise FetchError(f"Unexpected CWL response for {config.key}")

    draws = []
    for item in result:
        parsed = _parse_draw(config, item)
        if parsed:
            draws.append(parsed)

    if not draws:
        raise FetchError(f"No valid draws parsed for {config.key}")
    return draws


async def fetch_500_draws(config: LotteryConfig, page_size: int = 100) -> list[dict]:
    url = FIVE_HUNDRED_URLS.get(config.key)
    if not url:
        raise FetchError(f"No 500.com fallback configured for {config.key}")

    headers = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "User-Agent": "Mozilla/5.0 lottery-analysis-local/1.0",
    }

    async with httpx.AsyncClient(timeout=20, follow_redirects=True, headers=headers) as client:
        response = await client.get(url)
        response.raise_for_status()

    draws = _parse_500_html(config, response.text)
    if not draws:
        raise FetchError(f"No valid 500.com draws parsed for {config.key}")
    return draws[:page_size]


async def fetch_draws(config: LotteryConfig, page_size: int = 100) -> list[dict]:
    try:
        return await fetch_cwl_draws(config, page_size=page_size)
    except Exception as official_error:
        try:
            return await fetch_500_draws(config, page_size=page_size)
        except Exception as fallback_error:
            raise FetchError(
                f"官方源失败：{official_error}; 备用源失败：{fallback_error}"
            ) from fallback_error


def _parse_500_html(config: LotteryConfig, html: str) -> list[dict]:
    text = re.sub(r"<[^>]+>", " ", html)
    text = re.sub(r"\s+", " ", text)
    issue_matches = list(
        re.finditer(
            r"(?P<issue>\d{5,7})\s+(?P<date>20\d{2}-\d{2}-\d{2})(?:\s+\d{2}:\d{2}:\d{2})?",
            text,
        )
    )
    draws = []
    total_needed = config.numbers_per_draw + (1 if config.special_min is not None else 0)

    for index, match in enumerate(issue_matches):
        start = match.end()
        end = issue_matches[index + 1].start() if index + 1 < len(issue_matches) else len(text)
        values = [int(item) for item in re.findall(r"\b\d{1,2}\b", text[start:end])[:total_needed]]
        if len(values) < total_needed:
            continue

        numbers = values[: config.numbers_per_draw]
        special = values[config.numbers_per_draw :] if config.special_min is not None else []
        if not _valid_numbers(config, numbers, special):
            continue

        draws.append(
            {
                "issue": _normalize_500_issue(config, match.group("issue")),
                "draw_date": _normalize_date(match.group("date")),
                "numbers": numbers,
                "special": special,
                "source": "500彩票网",
            }
        )

    return draws


def _normalize_500_issue(config: LotteryConfig, issue: str) -> str:
    if config.key == "ssq" and len(issue) == 5:
        return f"20{issue}"
    return issue