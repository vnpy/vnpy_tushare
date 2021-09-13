from datetime import timedelta
import datetime
from numpy import ndarray
from pytz import timezone
from typing import List, Optional

from tushare import set_token, pro_bar

from vnpy.trader.setting import SETTINGS
from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, TickData, HistoryRequest
from vnpy.trader.utility import round_to

INTERVAL_VT2TS = {
    Interval.MINUTE: "1min",
    Interval.HOUR: "60min",
    Interval.DAILY: "D",
}

ASSET_VT2TS = {
    Exchange.CFFEX: "FT",
    Exchange.SHFE: "FT",
    Exchange.CZCE: "FT",
    Exchange.DCE: "FT",
    Exchange.INE: "FT",
    Exchange.SSE: "E",
    Exchange.SZSE: "E",
}

EXCHANGE_VT2TS = {
    Exchange.CFFEX: "CFX",
    Exchange.SHFE: "SHF",
    Exchange.CZCE: "ZCE",
    Exchange.DCE: "DCE",
    Exchange.INE: "INE",
    Exchange.SSE: "SH",
    Exchange.SZSE: "SZ",
}

INTERVAL_ADJUSTMENT_MAP = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta()
}

CHINA_TZ = timezone("Asia/Shanghai")


def to_ts_symbol(symbol, exchange):
    """将交易所代码转换为tushare代码"""
    # 股票
    if exchange in [Exchange.SSE, Exchange.SZSE]:
        ts_symbol = f"{symbol}.{EXCHANGE_VT2TS[exchange]}"
    # 期货
    elif exchange in [Exchange.SHFE, Exchange.CFFEX, Exchange.DCE, Exchange.CZCE, Exchange.INE]:
        ts_symbol = f"{symbol}.{EXCHANGE_VT2TS[exchange]}".upper()

    return ts_symbol


class TushareDatafeed(BaseDatafeed):
    """Tushare数据服务接口"""

    def __init__(self):
        """"""
        self.username: str = SETTINGS["datafeed.username"]
        self.password: str = SETTINGS["datafeed.password"]

        self.inited: bool = False
        self.symbols: ndarray = None

    def init(self) -> bool:
        """初始化"""
        if self.inited:
            return True

        if not self.password:
            return False

        set_token(self.username)

        self.inited = True
        return True

    def query_bar_history(self, req: HistoryRequest) -> Optional[List[BarData]]:
        """查询k线数据"""
        if not self.inited:
            self.init()

        symbol = req.symbol
        exchange = req.exchange
        interval = req.interval
        start = req.start
        end = req.end
        asset = ASSET_VT2TS[exchange]

        ts_symbol = to_ts_symbol(symbol, exchange)

        ts_interval = INTERVAL_VT2TS.get(interval)
        if not ts_interval:
            return None

        adjustment = INTERVAL_ADJUSTMENT_MAP[interval]

        df = pro_bar(
            ts_code=ts_symbol,
            start_date=start,
            end_date=end,
            asset=asset,
            freq=ts_interval
        )

        data: List[BarData] = []

        if df is not None:
            for ix, row in df.iterrows():
                if row["open"] is None:
                    continue

                if interval.value == "d":
                    dt = row["trade_date"]
                    dt = datetime.datetime.strptime(dt, "%Y%m%d")
                else:
                    dt = row["trade_time"]
                    dt = datetime.datetime.strptime(dt, "%Y-%m-%d %H:%M:%S") - adjustment

                dt = CHINA_TZ.localize(dt)

                bar = BarData(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    datetime=dt,
                    open_price=round_to(row["open"], 0.000001),
                    high_price=round_to(row["high"], 0.000001),
                    low_price=round_to(row["low"], 0.000001),
                    close_price=round_to(row["close"], 0.000001),
                    volume=row["vol"],
                    open_interest=row.get("open_interest", 0),
                    gateway_name="TS"
                )

                data.append(bar)

        return data

    def query_tick_history(self, req: HistoryRequest) -> Optional[List[TickData]]:
        pass
