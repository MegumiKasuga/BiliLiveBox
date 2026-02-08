from datetime import datetime, timezone, timedelta
import pytz

def timestamp_to_datetime(timestamp: int, time_zone: str, time_uniform: str) -> str:
    tz = pytz.timezone(time_zone)
    dt = datetime.fromtimestamp(timestamp, timezone.utc if time_zone is None else tz)
    return dt.strftime(time_uniform)


class TextInfo:

    def __init__(self, font_size: int, color: int):
        self.font_size = font_size
        self.color = color


class EmojiInfo:

    def __init__(self, descript: str, emoji: str, size: tuple[int, int], url: str):
        self.descript = descript
        self.emoji = emoji
        self.size = size
        self.url = url


class SenderData:

    def __init__(self, mid: int, name: str,
                 name_color: int, avatar_url: str,
                 is_me: bool):
        self.mid = mid
        self.name = name
        self.name_color = name_color
        self.avatar_url = avatar_url
        self.is_me = is_me


class Danmaku:

    def __init__(self, content: str, time: int, text_info: TextInfo,
                 emoji_infos: list[EmojiInfo], sender_data: SenderData):
        self.content = content
        self.text_info = text_info
        self.emoji_infos = emoji_infos
        self.sender_data = sender_data
        self.time = time


    def get_time(self, time_zone: str = 'Asia/Shanghai', time_uniform: str = "%Y-%m-%d %H:%M:%S") -> str:
        return timestamp_to_datetime(self.time['ts'], time_zone, time_uniform)


    def __str__(self):
        return f'{self.get_time()} - {self.sender_data.name}: {self.content}'