from enum import Enum


class MessageType(str, Enum):
    DANMU_MSG = "DANMU_MSG"
    SEND_GIFT = "SEND_GIFT"
    COMBO_SEND = "COMBO_SEND"
    INTERACT_WORD = "INTERACT_WORD"
    ENTRY_EFFECT = "ENTRY_EFFECT"
    NOTICE_MSG = "NOTICE_MSG"
