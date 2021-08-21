import json
import logging
import os
import struct
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import (Any, Awaitable, Callable, Coroutine, DefaultDict, Optional, Union)

from tornado.httpclient import AsyncHTTPClient
from tornado.ioloop import PeriodicCallback
from tornado.websocket import WebSocketClientConnection, websocket_connect

from bililive.exception import RoomDisconnectException, RoomNotFoundException
from bililive.message import MessageType
from bililive.package import Package, PackageOperation

Message = bytes
MessageHandler = Callable[[Message], None]
AsyncMessageHandler = Callable[[Message], Coroutine[Any, Any, None]]

ROOM_INFO_API_URL = (
    "https://api.live.bilibili.com/xlive/web-room/v1/index/getInfoByRoom?room_id={0}")
BROADCAST_LIVE_URL = "wss://broadcastlv.chat.bilibili.com:443/sub"

LOGLEVEL = os.environ.get("LOGLEVEL", default="INFO")
logging.basicConfig(level=LOGLEVEL)

log = logging.getLogger("Bililive")


class LiveStatus(int, Enum):
    OFFLINE = 0
    ONLINE = 1
    OTHER = 2


@dataclass
class LiveRoomInfo:
    uid: int
    room_id: int
    short_id: int
    title: str
    description: str
    live_status: LiveStatus
    live_start_time: datetime


class LiveRoom:
    _conn: WebSocketClientConnection
    _hb_timer: PeriodicCallback
    _handlers: DefaultDict[str, Union[MessageHandler, AsyncMessageHandler]]
    room_or_short_id: int
    info: LiveRoomInfo
    hot: int = -1

    def __init__(self) -> None:
        self._handlers = defaultdict(lambda: self.discard_message)
        self._hb_timer = PeriodicCallback(self._heartbeat, callback_time=30_000)

    def _send_package(self, package: Package):
        data = package.pack()
        # non wait for write
        self._conn.write_message(data, binary=True)

    def _heartbeat(self):
        package = Package(operation=PackageOperation.HEARTBEAT)

        log.debug("send heartbeat package.")
        self._send_package(package)

    def _authentication(self):
        msg = {"roomid": self.info.room_id, "protover": 3}
        data = json.dumps(msg).encode()
        package = Package(data, operation=PackageOperation.USER_AUTHENTICATION)

        log.debug("send authentication package.")
        self._send_package(package)

    async def update_info(self, room_id: Optional[int] = None):
        if room_id is not None:
            self.room_or_short_id = room_id

        log.debug("get live room info.")
        url = ROOM_INFO_API_URL.format(self.room_or_short_id)

        client = AsyncHTTPClient()
        response = await client.fetch(url)

        result = json.loads(response.body)
        if result["code"] != 0:
            raise RoomNotFoundException(self.room_or_short_id)

        info = result["data"]["room_info"]
        self.info = LiveRoomInfo(
            info["uid"],
            info["room_id"],
            info["short_id"],
            info["title"],
            info["description"],
            info["live_status"],
            datetime.fromtimestamp(info["live_start_time"]),
        )

    async def connect(self):
        if not hasattr(self, "info"):
            await self.update_info()

        log.debug(f"connect to live room {self.info.room_id}")
        self._conn = await websocket_connect(BROADCAST_LIVE_URL)
        self._authentication()

        while True:
            data = await self._conn.read_message()
            if data is None:
                if self._hb_timer.is_running():
                    self._hb_timer.stop()
                self._conn.close()
                raise RoomDisconnectException(self.room_or_short_id)

            if isinstance(data, str):
                data = data.encode()

            for package in Package.unpack(data):
                if package.operation == PackageOperation.CONNECT_SUCCESS:
                    log.debug("connection success.")
                    if not self._hb_timer.is_running():
                        self._hb_timer.start()
                elif package.operation == PackageOperation.HEARTBEAT_REPLY:
                    (v, ) = struct.unpack("!i", package.data)
                    log.debug(f"hot is {v}")
                    self.hot = v
                elif package.operation == PackageOperation.MESSAGE:
                    await self.dispatch_message(package.data)
                else:
                    log.warning(f"unknow operation code {package.operation}.")

    async def dispatch_message(self, msg: bytes):
        cmd = json.loads(msg)["cmd"]
        handler = self._handlers[cmd]

        result = handler(msg)
        if isinstance(result, Awaitable):
            await result

    def discard_message(self, msg: bytes):
        cmd = json.loads(msg)["cmd"]
        log.debug(f"discard message of {cmd}.")

    def on_message(self, cmd: MessageType):
        def _(handler: Union[MessageHandler, AsyncMessageHandler]):
            self._handlers[cmd] = handler

        return _
