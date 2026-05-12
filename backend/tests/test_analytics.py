from app.config import LOTTERIES
from app.services.analytics import calculate_stats, recommend


def test_ssq_stats_include_hot_omission_and_special():
    draws = [
        {"issue": "2026003", "draw_date": "2026-01-07", "numbers": [1, 2, 3, 4, 5, 6], "special": [7]},
        {"issue": "2026002", "draw_date": "2026-01-05", "numbers": [1, 8, 9, 10, 11, 12], "special": [8]},
        {"issue": "2026001", "draw_date": "2026-01-03", "numbers": [2, 13, 14, 15, 16, 17], "special": [7]},
    ]

    stats = calculate_stats(LOTTERIES["ssq"], draws, window=3)

    assert stats["draw_count"] == 3
    assert stats["hot"][0]["number"] in {"01", "02"}
    assert len(stats["omission"]) == 33
    assert len(stats["special"]["omission"]) == 16


def test_kl8_recommendation_has_20_unique_numbers():
    draws = [
        {
            "issue": str(2026000 + idx),
            "draw_date": f"2026-01-{idx:02d}",
            "numbers": list(range(1 + idx % 5, 21 + idx % 5)),
            "special": [],
        }
        for idx in range(1, 8)
    ]

    result = recommend(LOTTERIES["kl8"], draws, count=2, window=5)

    assert len(result["recommendations"]) == 2
    assert len(result["recommendations"][0]["numbers"]) == 20
    assert len(set(result["recommendations"][0]["numbers"])) == 20


def test_fc3d_stats_include_digit_hot():
    draws = [
        {"issue": "1", "draw_date": "2026-01-01", "numbers": [1, 2, 3], "special": []},
        {"issue": "2", "draw_date": "2026-01-02", "numbers": [1, 5, 9], "special": []},
    ]

    stats = calculate_stats(LOTTERIES["fc3d"], draws, window=2)

    assert len(stats["digits"]) == 3
    assert stats["summary"]["avg_sum"] == 10.5
