#!/usr/bin/python
#
# config.py
#
# Copyright (c) 2023, Paul Holleis, Marko Luther
# All rights reserved.
#
#
# ABOUT
# This module connects to the artisan.plus inventory management service

# LICENSE
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 2 of the License, or
# version 3 of the License, or (at your option) any later version. It is
# provided for educational purposes and is distributed in the hope that
# it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
# the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from typing import Final, TYPE_CHECKING
import os
import sys
import json
import logging
from pathlib import Path

if TYPE_CHECKING:
    from artisanlib.main import ApplicationWindow  # pylint: disable=unused-import


# ──────────────────────────────────────────────
# 外部配置文件（仅 Modbus 相关参数可配置）
# ──────────────────────────────────────────────

def _get_config_dir() -> Path:
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", str(Path.home()))
        return Path(base) / "artisan"
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "artisan"
    xdg = os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
    return Path(xdg) / "artisan"


CONFIG_DIR: Final[Path] = _get_config_dir()
CONFIG_FILE: Final[Path] = CONFIG_DIR / "TotalLINK_config.json"

# 只有这 10 个字段可以被外部配置覆盖
_CONFIGURABLE_DEFAULTS: dict = {
    "modbusIPCharge": "127.0.0.1",
    "modbusPortCharge": 5020,
    "modbusByteOrderCharge": "little",
    "modbusWordOrderCharge": "little",
    "registerAddressCharge": 10,
    "modbusIPDrop": "127.0.0.1",
    "modbusPortDrop": 5020,
    "modbusByteOrderDrop": "little",
    "modbusWordOrderDrop": "little",
    "registerAddressDrop": 10,
}


def _ensure_config_file() -> None:
    """配置文件不存在时自动创建，写入可配置字段的默认值。"""
    if CONFIG_FILE.exists():
        return
    try:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        template = {
            "_comment": "TotalLINK 配置文件。修改对应字段后重启程序生效。不需要的字段可以删除，将使用源码默认值。",
        }
        template.update(_CONFIGURABLE_DEFAULTS)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(template, f, indent=4, ensure_ascii=False)
        logging.info("config: 已自动生成配置文件 %s", CONFIG_FILE)
    except Exception as e:  # noqa: BLE001
        logging.warning("config: 自动生成配置文件失败，将使用源码默认值: %s", e)


def _load_user_overrides() -> dict:
    _ensure_config_file()
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            if isinstance(data, dict):
                # 只取可配置字段，其余一律忽略
                return {k: v for k, v in data.items() if k in _CONFIGURABLE_DEFAULTS}
            logging.warning("config: %s 顶层不是 JSON 对象，已忽略", CONFIG_FILE)
    except Exception as e:  # noqa: BLE001
        logging.warning("config: 读取 %s 失败，将使用默认值: %s", CONFIG_FILE, e)
    return {}


_user: dict = _load_user_overrides()


def _cfg(key: str, default):
    """从外部配置取值，取不到就用默认值。"""
    return _user.get(key, default)


# ──────────────────────────────────────────────
# 以下为原始配置，仅 Modbus 部分改为可配置
# ──────────────────────────────────────────────

# Constants
app_name: Final[str] = 'artisan.plus'
profile_ext: Final[str] = 'alog'
uuid_tag: Final[
    str] = 'roastUUID'  # as used in .alog profiles, send as 'roast_id' as part of the sync record to the server
schedule_uuid_tag: Final[str] = 'scheduleID'  # send as 's_item_id' as part of the sync record to the server
schedule_date_tag: Final[str] = 'scheduleDate'  # send as 's_item_date' as part of the sync record to the server

# Service URLs

# # LOCAL SETUP
# api_base_url         = 'https://localhost:62602/api/v1'
# web_base_url         = 'https://localhost:8088'

# # CLOUD SETUP
api_base_url: Final[str] = 'http://124.71.144.80:8081/api'
# api_base_url: Final[str] = 'https://artisan.plus/api/v1'
web_base_url: Final[str] = 'http://124.71.144.80:8081/formbuilder'

shop_base_url: Final[str] = 'http://124.71.144.80:8081/'

register_url: Final[str] = web_base_url + '/register'
reset_passwd_url: Final[str] = web_base_url + '/resetPassword'
# auth_url: Final[str] = api_base_url + '/accounts/users/authenticate'
auth_url: Final[str] = api_base_url + '/LINK/linkUserLoginAPI'
stock_url: Final[str] = api_base_url + '/acoffees'
roast_url: Final[str] = api_base_url + '/aroast'
lock_schedule_url: Final[str] = api_base_url + '/aschedule/lock'
notifications_url: Final[str] = api_base_url + '/notifications'
loginID: str = ""  # 可修改的字符串

chargeModel = "TMESEXC15"
chargeAttachModel = "TMESEXC1510X"
chargeAttachModelLOC = "TMESEXC1510X700X.LOC"
chargeAttachModelSubmit = "TMESEXC1510X700X"
chargeAttachModelDropSubmit = "TMESEXC1510X701X"

apsNum = ""
apsLin = 0

# ── Modbus 充填秤（可配置）──
modbusIPCharge: str = _cfg("modbusIPCharge", _CONFIGURABLE_DEFAULTS["modbusIPCharge"])
modbusPortCharge: int = _cfg("modbusPortCharge", _CONFIGURABLE_DEFAULTS["modbusPortCharge"])
modbusByteOrderCharge: str = _cfg("modbusByteOrderCharge", _CONFIGURABLE_DEFAULTS["modbusByteOrderCharge"])
modbusWordOrderCharge: str = _cfg("modbusWordOrderCharge", _CONFIGURABLE_DEFAULTS["modbusWordOrderCharge"])
registerAddressCharge: int = _cfg("registerAddressCharge", _CONFIGURABLE_DEFAULTS["registerAddressCharge"])

# ── Modbus 跌落秤（可配置）──
modbusIPDrop: str = _cfg("modbusIPDrop", _CONFIGURABLE_DEFAULTS["modbusIPDrop"])
modbusPortDrop: int = _cfg("modbusPortDrop", _CONFIGURABLE_DEFAULTS["modbusPortDrop"])
modbusByteOrderDrop: str = _cfg("modbusByteOrderDrop", _CONFIGURABLE_DEFAULTS["modbusByteOrderDrop"])
modbusWordOrderDrop: str = _cfg("modbusWordOrderDrop", _CONFIGURABLE_DEFAULTS["modbusWordOrderDrop"])
registerAddressDrop: int = _cfg("registerAddressDrop", _CONFIGURABLE_DEFAULTS["registerAddressDrop"])

# Connection configurations

# verify_ssl: Final[bool] = False
verify_ssl: Final[bool] = False
connect_timeout: Final[int] = 6  # in seconds
read_timeout: Final[int] = 12  # in seconds
read_timeout_max: Final[int] = 30  # in seconds
min_passwd_len: Final[int] = 4
min_login_len: Final[int] = 3
compress_posts: Final[bool] = True
# post_compression_threshold holds the number in bytes before compression
# kicks in
# (data smaller than this are always send uncompressed via POST)
post_compression_threshold: Final[int] = 500

# Authentication configuration

# do not authentify successfully after max_days after the subscription expired
expired_subscription_max_days: Final[int] = 90

# Cache and queue parameters

# Note: stock_cache_expiration should be larger than schedule_cache_expiration
stock_cache_expiration: Final[int] = 35  # expiration period in seconds for full stock updates (expensive)
schedule_cache_expiration: Final[
    int] = 5  # expiration period in seconds for full stock updates only in case the schedule on the server has changed

queue_start_delay: Final[int] = 5  # startup time of queue in seconds
# delay between tasks in seconds (cycling interval of the queue)
queue_task_delay: Final[float] = 2.0
queue_retries: Final[int] = 2  # number of retries (should be >=0)
queue_retry_delay: Final[int] = 30  # time between retries in seconds
queue_discard_after: Final[int] = 3 * 24 * 60 * 60  # period in seconds after 'modified_at'..
# .. until a queued item is removed from the queue; if queue_discard_after is 0 items are never discarded
# queque_put_timeout indicates the number of seconds to wait on putting
# a new item into the queue (unused for now)
queue_put_timeout: Final[float] = 0.5

# AppData

# the stock cache reflects the current coffee stock of the account and
# gets automatically synced with the cloud
stock_cache: Final[str] = 'cache'

# the completed roasts cache reflects the last roasted scheduled items
completed_roasts_cache: Final[str] = 'completed'

# the prepared items cache reflects the prepared scheduled items
prepared_items_cache: Final[str] = 'prepared'

# the hidden items cache reflects the hidden items
hidden_items_cache: Final[str] = 'hidden'

# the uuid register that associates UUIDs with local filepaths where to
# locate the corresponding Artisan profiles
uuid_cache: Final[str] = 'uuids'

# the account register that associates account ids with a local running
# account number
# Note: the account_cache file is shared between the main Artisan and the
# ArtisanViewer app, protected by a filelock
account_cache: Final[str] = 'account'

# the account nr locally associated to the current account, or None
account_nr: int | None = None

# the sync register that associates UUIDs with last known modification dates
# modified_at for profiles uploaded/synced automatically
# Note: the sync_cache file is shared between the main Artisan and the
# ArtisanViewer app, protected by a filelock
sync_cache: Final[str] = 'sync'

# the outbox queues the outgoing PUSH/PUT data requests
# Note: the outbox_cache file is shared between the main Artisan and the
# ArtisanViewer app, NOT protected by an extra filelock
outbox_cache: Final[str] = 'outbox'

# Runtime variables

app_window: 'ApplicationWindow|None' = None  # handle to the main Artisan application window
#   if set, app_window.plus_login holds the current login account if any and
#   app_window.updatePlusIcon() is a function that updates the toolbar
#   plus service connection indicator icon
connected: bool = False  # connection status
# the session token
token: str | None = None
# login nickname assigned on login with session token
nickname: str | None = None
