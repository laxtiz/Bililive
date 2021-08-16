class RoomNotFoundException(Exception):
    def __init__(self, room_id: int):
        self.room_id = room_id


class RoomDisconnectException(Exception):
    def __init__(self, room_id: int):
        self.room_id = room_id
