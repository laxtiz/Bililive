import argparse
import json
import sys
from datetime import datetime
from enum import Enum

from tornado.ioloop import IOLoop

from bililive.exception import RoomDisconnectException, RoomNotFoundException
from bililive.message import MessageType
from bililive.room import LiveRoom


class CoinType(str, Enum):
    银瓜子 = "silver"
    金瓜子 = "gold"


class GuardLevel(int, Enum):
    路人 = 0
    总督 = 1
    提督 = 2
    舰长 = 3


room = LiveRoom()


@room.on_message(MessageType.SEND_GIFT)
async def gift_handler(msg: bytes):
    """礼物消息处理，异步方式"""
    j = json.loads(msg)
    data = j["data"]

    uid = data["uid"]
    uname = data["uname"]
    guard_level = GuardLevel(data["guard_level"])

    gift_id = data["giftId"]
    gift_name = data["giftName"]
    gift_type = data["giftType"]
    coin_type = CoinType(data["coin_type"])
    total_coin = data["total_coin"]
    num = data["num"]

    ts = data["timestamp"]
    dt = datetime.fromtimestamp(ts)

    print(
        f"[{dt.time()}] [{guard_level.name}]{uname}({uid}) 赠送礼物 {gift_name}({num}) 价值 {total_coin:_} {coin_type.name}"
    )


@room.on_message(MessageType.DANMU_MSG)
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
    parser = argparse.ArgumentParser(description="哔哩哔哩直播间弹幕检测工具")
    parser.add_argument("room_id", type=int, metavar="room_id", help="直播间房号")
    args = parser.parse_args()
    room_id = args.room_id

    try:
        # 获取直播间信息
        await room.update_info(room_id)
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
        IOLoop.current().run_sync(main)
    except KeyboardInterrupt:
        print("正在退出...")
