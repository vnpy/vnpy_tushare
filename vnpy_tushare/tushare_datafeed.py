from datetime import timedelta, datetime
from pytz import timezone
from typing import Dict, List, Optional
from copy import deepcopy

import pandas as pd
import tushare as ts

from vnpy.trader.setting import SETTINGS
from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest
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
    Exchange.BITMEX: "C",
    Exchange.BITSTAMP: "C",
    Exchange.OKEX: "C",
    Exchange.HUOBI: "C",
    Exchange.BITFINEX: "C",
    Exchange.BINANCE: "C",
    Exchange.BYBIT: "C",
    Exchange.COINBASE: "C",
    Exchange.DERIBIT: "C",
    Exchange.GATEIO: "C",
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


def to_ts_symbol(symbol, exchange) -> Optional[str]:
    """将交易所代码转换为tushare代码"""
    # 股票
    if exchange in [Exchange.SSE, Exchange.SZSE]:
        ts_symbol = f"{symbol}.{EXCHANGE_VT2TS[exchange]}"
    # 期货
    elif exchange in [
        Exchange.SHFE,
        Exchange.CFFEX,
        Exchange.DCE,
        Exchange.CZCE,
        Exchange.INE
    ]:
        ts_symbol = f"{symbol}.{EXCHANGE_VT2TS[exchange]}".upper()
    # 数字货币
    elif exchange in [
        Exchange.BITSTAMP,
        Exchange.OKEX,
        Exchange.HUOBI,
        Exchange.BITFINEX,
        Exchange.BINANCE,
        Exchange.BYBIT,
        Exchange.COINBASE,
        Exchange.DERIBIT,
        Exchange.BITSTAMP
    ]:
        ts_symbol = symbol
    else:
        return None

    return ts_symbol


class TushareDatafeed(BaseDatafeed):
    """TuShare数据服务接口"""

    def __init__(self):
        """"""
        self.username: str = SETTINGS["datafeed.username"]
        self.password: str = SETTINGS["datafeed.password"]

        self.inited: bool = False

    def init(self) -> bool:
        """初始化"""
        if self.inited:
            return True

        ts.set_token(self.password)
        self.pro = ts.pro_api()
        self.inited = True

        return True

    def query_bar_history(self, req: HistoryRequest) -> Optional[List[BarData]]:
        """查询k线数据"""
        if not self.inited:
            self.init()

        symbol = req.symbol
        exchange = req.exchange
        interval = req.interval
        start = req.start.strftime("%Y%m%d")
        end = req.end.strftime("%Y%m%d")
        asset = ASSET_VT2TS[exchange]

        ts_symbol = to_ts_symbol(symbol, exchange)

        ts_interval = INTERVAL_VT2TS.get(interval)
        if not ts_interval:
            return None

        adjustment = INTERVAL_ADJUSTMENT_MAP[interval]

        # 数字货币
        if asset == "C":
            # 将代码转化为tushare代码
            d = self.pro.coin_pair(exchange=exchange.value.lower())

            base_coin = d.loc[d["symbol"] == symbol]["base_coin"].values[0]
            price_coin = d.loc[d["symbol"] == symbol]["price_coin"].values[0]
            ts_code = f"{base_coin}_{price_coin}"

            d1 = self.pro.coin_bar(
                exchange=exchange.value.lower(),
                ts_code=ts_code,
                freq=ts_interval,
                start_date=start,
                end_date=end
            )
            d2 = d1.loc[d1["symbol"] == symbol]
            df = deepcopy(d2)

            while True:
                if len(d1) != 8000:
                    break
                tmp_end = d2["trade_time"].values[-1]

                d1 = self.pro.coin_bar(
                    exchange=exchange.value.lower(),
                    ts_code=ts_code,
                    freq=ts_interval,
                    start_date=start,
                    end_date=tmp_end
                )
                d2 = d1.loc[d1["symbol"] == symbol]
                df = pd.concat([df[:-1], d2])

        # 其他
        else:
            d1 = ts.pro_bar(
                ts_code=ts_symbol,
                start_date=start,
                end_date=end,
                asset=asset,
                freq=ts_interval
            )
            df = deepcopy(d1)

            while True:
                if len(d1) != 8000:
                    break
                tmp_end = d1["trade_time"].values[-1]

                d1 = ts.pro_bar(
                    ts_code=ts_symbol,
                    start_date=start,
                    end_date=tmp_end,
                    asset=asset,
                    freq=ts_interval
                )
                df = pd.concat([df[:-1], d1])

        bar_keys: List[datetime] = []
        bar_dict: Dict[datetime, BarData] = {}
        data: List[BarData] = []

        if df is not None:
            for ix, row in df.iterrows():
                if row["open"] is None:
                    continue

                if interval.value == "d":
                    dt = row["trade_date"]
                    dt = datetime.strptime(dt, "%Y%m%d")
                else:
                    dt = row["trade_time"]
                    dt = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S") - adjustment

                dt = CHINA_TZ.localize(dt)

                bar: BarData = BarData(
                    symbol=symbol,
                    exchange=exchange,
                    interval=interval,
                    datetime=dt,
                    open_price=round_to(row["open"], 0.000001),
                    high_price=round_to(row["high"], 0.000001),
                    low_price=round_to(row["low"], 0.000001),
                    close_price=round_to(row["close"], 0.000001),
                    volume=row["vol"],
                    turnover=row.get("amount", 0),
                    open_interest=row.get("oi", 0),
                    gateway_name="TS"
                )

                bar_dict[dt] = bar

        bar_keys = bar_dict.keys()
        bar_keys = sorted(bar_keys, reverse=False)
        for i in bar_keys:
            data.append(bar_dict[i])

        return data
