from datetime import datetime

import pandas as pd
import pytest
import tushare as ts

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import HistoryRequest
from vnpy_tushare.tushare_datafeed import TushareDatafeed, to_ts_symbol


@pytest.fixture
def pro_bar_calls(monkeypatch: pytest.MonkeyPatch) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def fake_pro_bar(**kwargs: object) -> pd.DataFrame:
        calls.append(dict(kwargs))
        return pd.DataFrame()

    monkeypatch.setattr(ts, "pro_bar", fake_pro_bar)
    return calls


@pytest.fixture
def feed() -> TushareDatafeed:
    datafeed: TushareDatafeed = TushareDatafeed()
    datafeed.inited = True
    return datafeed


@pytest.mark.parametrize(
    ("symbol", "exchange", "expected"),
    [
        ("600009", Exchange.SSE, "600009.SH"),
        ("000001", Exchange.SZSE, "000001.SZ"),
        ("430418", Exchange.BSE, "430418.BJ"),
        ("IF2406", Exchange.CFFEX, "IF2406.CFX"),
        ("au2412", Exchange.SHFE, "AU2412.SHF"),
        ("TA501", Exchange.CZCE, "TA2501.ZCE"),
        ("i2409", Exchange.DCE, "I2409.DCE"),
        ("sc2412", Exchange.INE, "SC2412.INE"),
        ("si2412", Exchange.GFEX, "SI2412.GFE"),
        ("AAPL", Exchange.NYSE, None),
    ],
)
def test_to_ts_symbol(symbol: str, exchange: Exchange, expected: str | None) -> None:
    assert to_ts_symbol(symbol, exchange) == expected


@pytest.mark.parametrize(
    ("symbol", "exchange", "interval", "ts_code", "asset", "freq"),
    [
        ("600009", Exchange.SSE, Interval.MINUTE, "600009.SH", "E", "1min"),
        ("000001", Exchange.SZSE, Interval.DAILY, "000001.SZ", "E", "D"),
        ("518880", Exchange.SSE, Interval.HOUR, "518880.SH", "FD", "60min"),
        ("i2409", Exchange.DCE, Interval.MINUTE, "I2409.DCE", "FT", "1min"),
        ("TA501", Exchange.CZCE, Interval.DAILY, "TA2501.ZCE", "FT", "D"),
    ],
)
def test_history_request_query_parameters(
    feed: TushareDatafeed,
    pro_bar_calls: list[dict[str, object]],
    symbol: str,
    exchange: Exchange,
    interval: Interval,
    ts_code: str,
    asset: str,
    freq: str,
) -> None:
    req: HistoryRequest = HistoryRequest(
        symbol=symbol,
        exchange=exchange,
        start=datetime(2024, 1, 2, 9, 30),
        end=datetime(2024, 1, 2, 15, 0),
        interval=interval,
    )

    assert feed.query_bar_history(req) == []
    assert pro_bar_calls == [
        {
            "ts_code": ts_code,
            "start_date": "2024-01-02 09:30:00",
            "end_date": "2024-01-02 15:00:00",
            "asset": asset,
            "freq": freq,
        }
    ]


def test_unsupported_exchange_does_not_query(
    feed: TushareDatafeed,
    pro_bar_calls: list[dict[str, object]],
) -> None:
    req: HistoryRequest = HistoryRequest(
        symbol="AAPL",
        exchange=Exchange.NYSE,
        start=datetime(2024, 1, 2, 9, 30),
        end=datetime(2024, 1, 2, 16, 0),
        interval=Interval.MINUTE,
    )

    assert feed.query_bar_history(req) == []
    assert pro_bar_calls == []


def test_unsupported_interval_does_not_query(
    feed: TushareDatafeed,
    pro_bar_calls: list[dict[str, object]],
) -> None:
    req: HistoryRequest = HistoryRequest(
        symbol="600009",
        exchange=Exchange.SSE,
        start=datetime(2024, 1, 2, 9, 30),
        end=datetime(2024, 1, 2, 15, 0),
        interval=Interval.WEEKLY,
    )

    assert feed.query_bar_history(req) == []
    assert pro_bar_calls == []
