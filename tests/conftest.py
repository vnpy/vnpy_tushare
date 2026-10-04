import os
import sys
import tempfile
import types
from pathlib import Path

import pytest


REPO_ROOT: Path = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

# vnpy.trader.utility 导入时按当前目录决定 .vntrader 位置，vnpy.trader.setting 导入时读取 vt_setting.json。
# 必须在第一次 import vnpy 之前切到带空 .vntrader 的临时目录，避免读写用户真实配置。
ORIGINAL_CWD: str = os.getcwd()
TRADER_TEMP_DIR: tempfile.TemporaryDirectory = tempfile.TemporaryDirectory()
Path(TRADER_TEMP_DIR.name).joinpath(".vntrader").mkdir()
os.chdir(TRADER_TEMP_DIR.name)

from vnpy.trader.setting import SETTINGS  # noqa: E402

# vnpy.trader.logger 导入时按 log.file 创建日志目录，需在它被导入前关闭。
SETTINGS["log.file"] = False
SETTINGS["log.console"] = False

# tushare_datafeed 导入时会加载 tushare。替身挡住 set_token / pro_api / pro_bar，测试不需要令牌，也不访问网络。
for _name in list(sys.modules):
    if _name == "tushare" or _name.startswith("tushare."):
        del sys.modules[_name]


class _DataApi:
    pass


def _refuse_tushare_network(*args: object, **kwargs: object) -> None:
    raise RuntimeError("tushare network entry is disabled in unit tests")


_tushare: types.ModuleType = types.ModuleType("tushare")
_tushare_pro: types.ModuleType = types.ModuleType("tushare.pro")
_tushare_client: types.ModuleType = types.ModuleType("tushare.pro.client")
_tushare_pro.__path__ = []
_tushare.__path__ = []
_tushare_client.DataApi = _DataApi
_tushare_pro.client = _tushare_client
_tushare.pro = _tushare_pro
_tushare.set_token = _refuse_tushare_network
_tushare.pro_api = _refuse_tushare_network
_tushare.pro_bar = _refuse_tushare_network
sys.modules["tushare"] = _tushare
sys.modules["tushare.pro"] = _tushare_pro
sys.modules["tushare.pro.client"] = _tushare_client


def pytest_unconfigure(config: pytest.Config) -> None:
    os.chdir(ORIGINAL_CWD)
    TRADER_TEMP_DIR.cleanup()
