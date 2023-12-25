from datetime import timedelta, datetime
from typing import Dict, List, Optional, Callable
from copy import deepcopy

import pandas as pd
from pandas import DataFrame
import tushare as ts
from tushare.pro.client import DataApi

from vnpy.trader.setting import SETTINGS
from vnpy.trader.datafeed import BaseDatafeed
from vnpy.trader.constant import Exchange, Interval
from vnpy.trader.object import BarData, HistoryRequest
from vnpy.trader.utility import round_to, ZoneInfo

# 数据频率映射
INTERVAL_VT2TS: Dict[Interval, str] = {
    Interval.MINUTE: "1min",
    Interval.HOUR: "60min",
    Interval.DAILY: "D",
}

# 股票支持列表
STOCK_LIST: List[Exchange] = [
    Exchange.SSE,
    Exchange.SZSE,
    Exchange.BSE,
]

# 期货支持列表
FUTURE_LIST: List[Exchange] = [
    Exchange.CFFEX,
    Exchange.SHFE,
    Exchange.CZCE,
    Exchange.DCE,
    Exchange.INE,
    Exchange.GFEX
]

# 交易所映射
EXCHANGE_VT2TS: Dict[Exchange, str] = {
    Exchange.CFFEX: "CFX",
    Exchange.SHFE: "SHF",
    Exchange.CZCE: "ZCE",
    Exchange.DCE: "DCE",
    Exchange.INE: "INE",
    Exchange.SSE: "SH",
    Exchange.SZSE: "SZ",
    Exchange.GFEX: "GFE"
}

# 时间调整映射
INTERVAL_ADJUSTMENT_MAP: Dict[Interval, timedelta] = {
    Interval.MINUTE: timedelta(minutes=1),
    Interval.HOUR: timedelta(hours=1),
    Interval.DAILY: timedelta()
}

# 中国上海时区
CHINA_TZ = ZoneInfo("Asia/Shanghai")


def to_ts_symbol(symbol, exchange) -> Optional[str]:
    """将交易所代码转换为tushare代码"""
    # 股票
    if exchange in STOCK_LIST:
        ts_symbol: str = f"{symbol}.{EXCHANGE_VT2TS[exchange]}"
    # 期货
    elif exchange in FUTURE_LIST:
        if exchange is not Exchange.CZCE:
            ts_symbol: str = f"{symbol}.{EXCHANGE_VT2TS[exchange]}".upper()
        else:
            for count, word in enumerate(symbol):
                if word.isdigit():
                    break

            year: str = symbol[count]
            month: str = symbol[count + 1:]
            if year == "9":
                year = "1" + year
            else:
                year = "2" + year

            product: str = symbol[:count]
            ts_symbol: str = f"{product}{year}{month}.ZCE".upper()
    else:
        return None

    return ts_symbol


def to_ts_asset(symbol, exchange) -> Optional[str]:
    """生成tushare资产类别"""
    # 股票
    if exchange in STOCK_LIST:
        if exchange is Exchange.SSE and symbol[0] == "6":
            asset: str = "E"
        elif exchange is Exchange.SZSE and symbol[0] == "0" or symbol[0] == "3":
            asset: str = "E"
        else:
            asset: str = "I"
    # 期货
    elif exchange in FUTURE_LIST:
        asset: str = "FT"
    else:
        return None

    return asset


class TushareDatafeed(BaseDatafeed):
    """TuShare数据服务接口"""

    def __init__(self):
        """"""
        self.username: str = SETTINGS["datafeed.username"]
        self.password: str = SETTINGS["datafeed.password"]

        self.inited: bool = False

    def init(self, output: Callable = print) -> bool:
        """初始化"""
        if self.inited:
            return True
        
        if not self.username:
            output("Tushare数据服务初始化失败：用户名为空！")
            return False

        if not self.password:
            output("Tushare数据服务初始化失败：密码为空！")
            return False

        ts.set_token(self.password)
        self.pro: Optional[DataApi] = ts.pro_api()
        self.inited = True

        return True

    def query_bar_history(self, req: HistoryRequest, output: Callable = print) -> Optional[List[BarData]]:
        """查询k线数据"""
        if not self.inited:
            self.init(output)

        symbol: str = req.symbol
        exchange: Exchange = req.exchange
        interval: Interval = req.interval
        start: datetime = req.start.strftime("%Y-%m-%d %H:%M:%S")
        end: datetime = req.end.strftime("%Y-%m-%d %H:%M:%S")

        ts_symbol: str = to_ts_symbol(symbol, exchange)
        if not ts_symbol:
            return None

        asset: str = to_ts_asset(symbol, exchange)
        if not asset:
            return None

        ts_interval: str = INTERVAL_VT2TS.get(interval)
        if not ts_interval:
            return None

        adjustment: timedelta = INTERVAL_ADJUSTMENT_MAP[interval]

        try:
            d1: DataFrame = ts.pro_bar(
                ts_code=ts_symbol,
                start_date=start,
                end_date=end,
                asset=asset,
                freq=ts_interval
            )
        except IOError as ex:
            output(f"发生输入/输出错误：{ex.strerror}")
            return []

        df: DataFrame = deepcopy(d1)

        while True:
            if len(d1) != 8000:
                break
            tmp_end: str = d1["trade_time"].values[-1]

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

        # 处理原始数据中的NaN值
        df.fillna(0, inplace=True)

        if df is not None:
            for ix, row in df.iterrows():
                if row["open"] is None:
                    continue

                if interval.value == "d":
                    dt: str = row["trade_date"]
                    dt: datetime = datetime.strptime(dt, "%Y%m%d")
                else:
                    dt: str = row["trade_time"]
                    dt: datetime = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S") - adjustment

                dt = dt.replace(tzinfo=CHINA_TZ)

                turnover = row.get("amount", 0)
                if turnover is None:
                    turnover = 0

                open_interest = row.get("oi", 0)
                if open_interest is None:
                    open_interest = 0

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
                    turnover=turnover,
                    open_interest=open_interest,
                    gateway_name="TS"
                )

                bar_dict[dt] = bar

        bar_keys: list = bar_dict.keys()
        bar_keys = sorted(bar_keys, reverse=False)
        for i in bar_keys:
            data.append(bar_dict[i])

        return data
