# vn.py框架的Tushare数据服务接口

<p align="center">
  <img src ="https://vnpy.oss-cn-shanghai.aliyuncs.com/vnpy-logo.png"/>
</p>

<p align="center">
    <img src ="https://img.shields.io/badge/version-1.2.64-blueviolet.svg"/>
    <img src ="https://img.shields.io/badge/platform-windows|linux|macos-yellow.svg"/>
    <img src ="https://img.shields.io/badge/python-3.7-blue.svg"/>
    <img src ="https://img.shields.io/github/license/vnpy/vnpy.svg?color=orange"/>
</p>

## 说明

基于tushare模块的1.2.64版本开发，支持以下中国金融市场的K线数据：

* 期货：
  * CFFEX：中国金融期货交易所
  * SHFE：上海期货交易所
  * DCE：大连商品交易所
  * CZCE：郑州商品交易所
  * INE：上海国际能源交易中心
* 股票：
  * SSE：上海证券交易所
  * SZSE：深圳证券交易所
* 数字货币
  * BITMEX
  * BITSTAMP
  * OKEX
  * HUOBI
  * BITFINEX
  * BINANCE
  * BYBIT
  * COINBASE
  * DERIBIT
  * GATEIO

注意：需要使用相应的数据服务权限，可以通过[该页面](https://www.tushare.pro)注册使用。


## 安装

安装需要基于2.6.0版本以上的[VN Studio](https://www.vnpy.com)。

直接使用pip命令：

```
pip install vnpy_tushare
```


或者下载解压后在cmd中运行：

```
python setup.py install
```

## 使用

在VN Trader中配置时，需要填写以下字段信息：

| 字段名            | 值 |
|---------           |---- |
|datafeed.username   | token|
|datafeed.password   | token|
