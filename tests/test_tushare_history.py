from collections.abc import Callable
from datetime import datetime, timedelta

import pandas as pd
import pytest
import tushare as ts

from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest
from vnpy_tushare.tushare_datafeed import (
    CHINA_TZ,
    TS_BAR_LIMIT,
    TushareDatafeed,
    to_ts_symbol,
)


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


def _times(origin: datetime, count: int, step: timedelta) -> list[str]:
    return [
        (origin + step * i).strftime("%Y-%m-%d %H:%M:%S")
        for i in range(count)
    ]


def _bar_frame(times: list[str], daily: bool = False) -> pd.DataFrame:
    count: int = len(times)
    columns: dict[str, list[float] | list[str]] = {
        "open": [1.0] * count,
        "high": [1.1] * count,
        "low": [0.9] * count,
        "close": [1.0] * count,
        "vol": [10.0] * count,
        "amount": [100.0] * count,
    }
    if daily:
        columns["trade_date"] = times
    else:
        columns["trade_time"] = times
    return pd.DataFrame(columns)


def _history_request(
    interval: Interval,
    start: datetime,
    end: datetime,
) -> HistoryRequest:
    return HistoryRequest(
        symbol="600009",
        exchange=Exchange.SSE,
        start=start,
        end=end,
        interval=interval,
    )


def _install_pro_bar(
    monkeypatch: pytest.MonkeyPatch,
    handler: Callable[..., pd.DataFrame | None],
) -> list[dict[str, object]]:
    calls: list[dict[str, object]] = []

    def fake_pro_bar(**kwargs: object) -> pd.DataFrame | None:
        calls.append(dict(kwargs))
        if len(calls) > 4:
            raise RuntimeError("pagination did not stop")
        return handler(**kwargs)

    monkeypatch.setattr(ts, "pro_bar", fake_pro_bar)
    return calls


def _page(times_asc: list[str], end_date: str) -> pd.DataFrame:
    selected: list[str] = [item for item in times_asc if item <= end_date]
    if len(selected) > TS_BAR_LIMIT:
        selected = selected[-TS_BAR_LIMIT:]
    selected.reverse()
    return _bar_frame(selected)


def test_history_below_page_limit_queries_once(
    feed: TushareDatafeed,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin: datetime = datetime(2024, 1, 2, 9, 31)
    times_asc: list[str] = _times(origin, 3, timedelta(minutes=1))
    calls: list[dict[str, object]] = _install_pro_bar(
        monkeypatch,
        lambda **kwargs: _page(times_asc, str(kwargs["end_date"])),
    )

    bars: list[BarData] = feed.query_bar_history(
        _history_request(Interval.MINUTE, origin, origin + timedelta(minutes=2))
    )

    assert len(calls) == 1
    assert [bar.datetime for bar in bars] == [
        (origin + timedelta(minutes=i - 1)).replace(tzinfo=CHINA_TZ)
        for i in range(3)
    ]


def test_history_exact_page_keeps_oldest_bar(
    feed: TushareDatafeed,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin: datetime = datetime(2024, 1, 2, 9, 31)
    times_asc: list[str] = _times(origin, TS_BAR_LIMIT, timedelta(minutes=1))
    calls: list[dict[str, object]] = _install_pro_bar(
        monkeypatch,
        lambda **kwargs: _page(times_asc, str(kwargs["end_date"])),
    )

    bars: list[BarData] = feed.query_bar_history(
        _history_request(
            Interval.MINUTE,
            origin,
            origin + timedelta(minutes=TS_BAR_LIMIT - 1),
        )
    )

    assert len(calls) == 2
    assert calls[1]["end_date"] == (origin - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    assert len(bars) == TS_BAR_LIMIT
    assert bars[0].datetime == (origin - timedelta(minutes=1)).replace(tzinfo=CHINA_TZ)


def test_history_full_page_plus_remainder_has_each_bar_once(
    feed: TushareDatafeed,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin: datetime = datetime(2024, 1, 2, 9, 31)
    total: int = TS_BAR_LIMIT + 500
    times_asc: list[str] = _times(origin, total, timedelta(minutes=1))
    calls: list[dict[str, object]] = _install_pro_bar(
        monkeypatch,
        lambda **kwargs: _page(times_asc, str(kwargs["end_date"])),
    )

    bars: list[BarData] = feed.query_bar_history(
        _history_request(
            Interval.MINUTE,
            origin,
            origin + timedelta(minutes=total - 1),
        )
    )

    assert len(calls) == 2
    assert calls[1]["end_date"] == times_asc[499]
    assert len(bars) == total
    assert len({bar.datetime for bar in bars}) == total
    assert bars[0].datetime == (origin - timedelta(minutes=1)).replace(tzinfo=CHINA_TZ)
    assert bars[-1].datetime == (
        origin + timedelta(minutes=total - 2)
    ).replace(tzinfo=CHINA_TZ)


def test_history_two_exact_pages_stop_after_empty_follow_up(
    feed: TushareDatafeed,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin: datetime = datetime(2024, 1, 2, 9, 31)
    total: int = TS_BAR_LIMIT * 2
    times_asc: list[str] = _times(origin, total, timedelta(minutes=1))
    calls: list[dict[str, object]] = _install_pro_bar(
        monkeypatch,
        lambda **kwargs: _page(times_asc, str(kwargs["end_date"])),
    )

    bars: list[BarData] = feed.query_bar_history(
        _history_request(
            Interval.MINUTE,
            origin,
            origin + timedelta(minutes=total - 1),
        )
    )

    assert len(calls) == 3
    assert calls[1]["end_date"] == times_asc[TS_BAR_LIMIT - 1]
    assert calls[2]["end_date"] == (origin - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    assert len(bars) == total
    assert bars[0].datetime == (origin - timedelta(minutes=1)).replace(tzinfo=CHINA_TZ)


def test_history_stops_when_oldest_time_does_not_move(
    feed: TushareDatafeed,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin: datetime = datetime(2024, 1, 2, 9, 31)
    times_asc: list[str] = _times(origin, TS_BAR_LIMIT, timedelta(minutes=1))
    stuck: pd.DataFrame = _bar_frame(list(reversed(times_asc)))
    calls: list[dict[str, object]] = _install_pro_bar(
        monkeypatch,
        lambda **kwargs: stuck,
    )

    bars: list[BarData] = feed.query_bar_history(
        _history_request(
            Interval.MINUTE,
            origin - timedelta(days=30),
            origin + timedelta(minutes=TS_BAR_LIMIT),
        )
    )

    assert len(calls) == 2
    assert calls[1]["end_date"] == (origin - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
    assert len(bars) == TS_BAR_LIMIT
    assert bars[0].datetime == (origin - timedelta(minutes=1)).replace(tzinfo=CHINA_TZ)


def test_history_hour_page_steps_back_one_hour(
    feed: TushareDatafeed,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin: datetime = datetime(2024, 1, 2, 10, 0)
    times_asc: list[str] = _times(origin, TS_BAR_LIMIT, timedelta(hours=1))
    calls: list[dict[str, object]] = _install_pro_bar(
        monkeypatch,
        lambda **kwargs: _page(times_asc, str(kwargs["end_date"])),
    )

    bars: list[BarData] = feed.query_bar_history(
        _history_request(
            Interval.HOUR,
            origin,
            origin + timedelta(hours=TS_BAR_LIMIT - 1),
        )
    )

    assert len(calls) == 2
    assert calls[1]["end_date"] == (origin - timedelta(hours=1)).strftime("%Y-%m-%d %H:%M:%S")
    assert len(bars) == TS_BAR_LIMIT
    assert bars[0].datetime == (origin - timedelta(hours=1)).replace(tzinfo=CHINA_TZ)


def test_history_daily_exact_page_steps_back_one_day(
    feed: TushareDatafeed,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin: datetime = datetime(1990, 12, 19)
    trade_dates: list[str] = [
        (origin + timedelta(days=i)).strftime("%Y%m%d")
        for i in range(TS_BAR_LIMIT)
    ]
    calls: list[dict[str, object]] = _install_pro_bar(
        monkeypatch,
        lambda **kwargs: _bar_frame(trade_dates, daily=True),
    )

    bars: list[BarData] = feed.query_bar_history(
        _history_request(Interval.DAILY, origin, origin + timedelta(days=TS_BAR_LIMIT))
    )

    assert len(calls) == 2
    assert calls[1]["end_date"] == "19901218"
    assert len(bars) == TS_BAR_LIMIT
    assert bars[0].datetime == origin.replace(tzinfo=CHINA_TZ)
    assert bars[-1].datetime == (
        origin + timedelta(days=TS_BAR_LIMIT - 1)
    ).replace(tzinfo=CHINA_TZ)


def test_history_returns_empty_when_pro_bar_returns_none(
    feed: TushareDatafeed,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[dict[str, object]] = _install_pro_bar(
        monkeypatch,
        lambda **kwargs: None,
    )

    bars: list[BarData] = feed.query_bar_history(
        _history_request(
            Interval.MINUTE,
            datetime(2024, 1, 2, 9, 31),
            datetime(2024, 1, 2, 15, 0),
        )
    )

    assert bars == []
    assert len(calls) == 1


def test_history_keeps_first_page_when_next_request_fails(
    feed: TushareDatafeed,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    origin: datetime = datetime(2024, 1, 2, 9, 31)
    times_asc: list[str] = _times(origin, TS_BAR_LIMIT, timedelta(minutes=1))
    calls: list[dict[str, object]] = []

    def fake_pro_bar(**kwargs: object) -> pd.DataFrame:
        calls.append(dict(kwargs))
        if len(calls) > 1:
            raise OSError(0, "broken pipe")
        return _page(times_asc, str(kwargs["end_date"]))

    monkeypatch.setattr(ts, "pro_bar", fake_pro_bar)
    messages: list[str] = []

    bars: list[BarData] = feed.query_bar_history(
        _history_request(
            Interval.MINUTE,
            origin,
            origin + timedelta(minutes=TS_BAR_LIMIT - 1),
        ),
        messages.append,
    )

    assert messages == ["发生输入/输出错误：broken pipe"]
    assert len(calls) == 2
    assert len(bars) == TS_BAR_LIMIT
    assert bars[0].datetime == (origin - timedelta(minutes=1)).replace(tzinfo=CHINA_TZ)
