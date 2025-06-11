# VeighNa框架的TuShare数据服务接口

<p align="center">
  <img src ="https://vnpy.oss-cn-shanghai.aliyuncs.com/vnpy-logo.png"/>
</p>

<p align="center">
    <img src ="https://img.shields.io/badge/version-1.4.21.0-blueviolet.svg"/>
    <img src ="https://img.shields.io/badge/platform-windows|linux|macos-yellow.svg"/>
    <img src ="https://img.shields.io/badge/python-3.10|3.11|3.12|3.13-blue.svg"/>
    <img src ="https://img.shields.io/github/license/vnpy/vnpy.svg?color=orange"/>
</p>

## 说明

基于tushare模块的1.4.21版本开发，支持以下中国金融市场的K线数据：

* 期货：
  * CFFEX：中国金融期货交易所
  * SHFE：上海期货交易所
  * DCE：大连商品交易所
  * CZCE：郑州商品交易所
  * INE：上海国际能源交易中心
* 股票：
  * SSE：上海证券交易所
  * SZSE：深圳证券交易所
  * BSE：北京证券交易所

注意：需要使用相应的数据服务权限，可以通过[该页面](https://www.tushare.pro)注册使用。

## 数据使用事项

tushare数据源期货数据中，第一条夜盘k线数据是集合竞价数据，用户可以根据自己需求进行过滤或者合并。

## 安装

安装环境推荐基于4.0.0版本以上的【[**VeighNa Studio**](https://www.vnpy.com)】。

直接使用pip命令：

```
pip install vnpy_tushare
```


或者下载源代码后，解压后在cmd中运行：

```
pip install .
```


## 使用

在VeighNa中使用TuShare时，需要在全局配置中填写以下字段信息：

|名称|含义|必填|举例|
|---------|----|---|---|
|datafeed.name|名称|是|tushare|
|datafeed.username|用户名|否|token|
|datafeed.password|密码|是|c3a110417f08f26d2c221edc0c50d4a8a5001502eea89cf5|


# 单元测试

单元测试代码目录为`./tests/test_*.py`
```sh
# 指定文件执行单元测试
python -m unittest tests\test_your_file_name.py

# 全量执行
python -m unittest
```
