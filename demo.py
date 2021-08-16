import json
import logging
import os
import sys
from datetime import datetime

import tornado.gen
import tornado.ioloop
from tornado.options import options

from bililive.exception import RoomDisconnectException, RoomNotFoundException
from bililive.message import MessageType
from bililive.room import LiveRoom

log = logging.getLogger(__name__)


class DebugRoom(LiveRoom):
    """
    重写消息分发器，收集数据样本
    """

    async def dispatch_message(self, msg: bytes):
        if "DEBUG" in os.environ:
            self.save_to_file(msg)
        return await super().dispatch_message(msg)

    def save_to_file(self, msg: bytes):
        """将消息保存至文件"""
        j = json.loads(msg)
        cmd = j["cmd"]

        if not os.path.exists(f"./data/{cmd}"):
            os.makedirs(f"./data/{cmd}", exist_ok=True)

        ts = datetime.now().timestamp()
        with open(f"./data/{cmd}/{ts}.json", mode="wt") as fp:
            json.dump(j, fp, indent=2, ensure_ascii=False)


async def send_gift_hander(msg: bytes):
    """礼物消息处理，异步方式"""
    j = json.loads(msg)
    data = j["data"]

    action = data["action"]
    uid = data["uid"]
    uname = data["uname"]
    gift_id = data["giftId"]
    gift_name = data["giftName"]
    gift_type = data["giftType"]
    price = data["price"]
    num = data["num"]

    ts = data["timestamp"]
    dt = datetime.fromtimestamp(ts)

    print(f"[{dt.time()}] {uname}({uid}) 赠送礼物 {gift_name}({num}) 价值 {price}")


def danmu_handler(msg: bytes):
    """弹幕消息处理"""
    j = json.loads(msg)
    info = j["info"]

    text = info[1]
    uid = info[2][0]
    uname = info[2][1]
    ts = info[9]["ts"]
    dt = datetime.fromtimestamp(ts)

    print(f"[{dt.time()}] {uname}({uid}): {text}")


async def main():
    options.define("room_id", 6, type=int, help="Room id of which you want listen.")
    options.parse_command_line()

    room_id: int = options["room_id"]
    room = DebugRoom(room_id)

    # 注册消息处理器
    room.handle(MessageType.DANMU_MSG, danmu_handler)
    room.handle(MessageType.SEND_GIFT, send_gift_hander)

    try:
        # 获取直播间信息
        await room.update_info()

        print(f"正在连接至直播间 {room.info.room_id}")
        print(room.info.title)

        # 连接直播间
        await room.connect()
    except RoomNotFoundException as e:
        print(f"直播间 {e.room_id} 不存在.")
        sys.exit(1)
    except RoomDisconnectException as e:
        print(f"直播间 {e.room_id} 已断开连接.")


if __name__ == "__main__":
    try:
        tornado.ioloop.IOLoop.current().run_sync(main)
    except KeyboardInterrupt:
        print("正在退出...")
