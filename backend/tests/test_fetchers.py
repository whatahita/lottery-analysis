from app.config import LOTTERIES
from app.fetchers.cwl import _parse_500_html


def test_parse_500_ssq_html():
    html = """
    <tr><td>26011</td><td>2026-01-25 21:15:00</td>
    <td>02 03 04 20 31 32 04</td></tr>
    """

    draws = _parse_500_html(LOTTERIES["ssq"], html)

    assert draws[0]["issue"] == "2026011"
    assert draws[0]["numbers"] == [2, 3, 4, 20, 31, 32]
    assert draws[0]["special"] == [4]
    assert draws[0]["source"] == "500彩票网"


def test_parse_500_kl8_html():
    html = """
    <tr><td>2026028</td><td>2026-01-28</td>
    <td>09 11 14 16 17 20 28 30 32 33 46 51 54 57 58 62 66 68 71 74</td></tr>
    """

    draws = _parse_500_html(LOTTERIES["kl8"], html)

    assert draws[0]["issue"] == "2026028"
    assert len(draws[0]["numbers"]) == 20
    assert draws[0]["special"] == []


def test_parse_500_fc3d_html():
    html = """
    <tr><td>2026028</td><td>2026-01-28</td><td>2 7 0</td></tr>
    """

    draws = _parse_500_html(LOTTERIES["fc3d"], html)

    assert draws[0]["issue"] == "2026028"
    assert draws[0]["numbers"] == [2, 7, 0]
    assert draws[0]["special"] == []