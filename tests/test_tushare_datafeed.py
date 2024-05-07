import unittest
from vnpy_tushare.tushare_datafeed import to_ts_asset
from vnpy.trader.constant import Exchange


class TestToTsAsset(unittest.TestCase):
  # 股票
  def test_stock(self):
    self.assertEqual(to_ts_asset('600009', Exchange.SSE), "E")  # 沪市
    self.assertEqual(to_ts_asset('688981', Exchange.SSE), "E")  # 科创版
    self.assertEqual(to_ts_asset('000001', Exchange.SZSE), "E")  # 深市
    self.assertEqual(to_ts_asset('300308', Exchange.SZSE), "E")  # 创业板
    self.assertEqual(to_ts_asset('430418', Exchange.BSE), "E")  # 北交所
    self.assertEqual(to_ts_asset('835305', Exchange.BSE), "E")  # 北交所
  
  # 指数
  def test_index(self):
    self.assertEqual(to_ts_asset('000001', Exchange.SSE), "I")  # 上证指数
    self.assertEqual(to_ts_asset('000688', Exchange.SSE), "I")  # 科创版指
    self.assertEqual(to_ts_asset('399001', Exchange.SZSE), "I")  # 深证指数
    self.assertEqual(to_ts_asset('399006', Exchange.SZSE), "I")  # 创业板指
    self.assertEqual(to_ts_asset('899050', Exchange.BSE), "I")  # 北交所50
  
  # 基金
  def test_fund(self):
    self.assertEqual(to_ts_asset('159934', Exchange.SZSE), "FD")  # 深市etf
    self.assertEqual(to_ts_asset('518880', Exchange.SSE), "FD")  # 沪市etf
  
  # 期货
  def test_future(self):
    self.assertEqual(to_ts_asset('i2409', Exchange.CFFEX), "FT")

if __name__ == '__main__':
  unittest.main()
