from typing import Any

from PIL.ImageChops import offset

from bili.session import Session
from bili import encrypter
from bili import constants
from bili import decompress
from bili import interaction
from bili.session import User
import requests
from abc import ABC, abstractmethod
import websockets
import asyncio
import json
import struct


class UploadPacket(ABC):

    def __init__(self, packet_type: int, protocol: int):
        self.protocol = protocol
        self.packet_type = packet_type

    @abstractmethod
    async def send(self, ws: websockets.WebSocketClientProtocol):
        pass

    def encode(self, data, sequence: int) -> bytes:
        json_str = json.dumps(data, separators=(',', ':'))
        json_bytes = json_str.encode('utf-8')
        header = struct.pack('>IHHII',
                             16 + len(json_bytes),
                             16, self.protocol,
                             self.packet_type,
                             sequence)
        return bytes(header + json_bytes)


class VerifyPacket(UploadPacket):

    def __init__(self,
                 live_house_id: int,
                 mid: int, token: str):
        super().__init__(7, 1)
        self.live_house_id = live_house_id
        self.mid = mid
        self.token = token

    async def send(self, ws) -> Any:
        data = {
            'uid': self.mid,
            'roomid': self.live_house_id,
            'protover': 3,
            'platform': 'web',
            'type': 2,
            'key': self.token
        }

        packet_bytes = self.encode(data, 0)
        return await ws.send(packet_bytes)


class HeartbeatUploadPacket(UploadPacket):

    def __init__(self, live_house_id: int):
        super().__init__(2, 1)
        self.live_house_id = live_house_id

    async def send(self, ws) -> Any:
        data = {}
        packet_bytes = self.encode(data, 0)
        return await ws.send(packet_bytes)


class DownloadPacket:

    def __init__(self, live_house_id: int, data: bytes):
        self.data = data
        self.room_id = live_house_id
        self.json = None
        self.total_len = -1
        self.header_len = -1
        self.protocol = -1
        self.packet_type = -1
        self.sequence = -1


    def decode(self) -> Any | None:
        self.total_len, self.header_len, self.protocol, self.packet_type, self.sequence = struct.unpack('>IHHII', self.data[:16])
        json_bytes = self.data[16:self.total_len]
        match self.protocol:
            case 0:
                self.json = json.loads(json_bytes)
            case 1:
                self.json = json.loads(json_bytes)
            case 2:
                self.json = json.loads(decompress.decompress(json_bytes, 'zlib'))
            case 3:
                self.json = json.loads(decompress.decompress(json_bytes, 'brotli'))
        return self.json


class VerifyResponsePacket(DownloadPacket):

    def __init__(self, live_house_id: int, data: bytes):
        super().__init__(live_house_id, data)

    def is_ok(self):
        json_data = self.decode()
        if json_data is None:
            return False
        return json_data.get('code', -1) == 0


class HeartbeatResponsePacket(DownloadPacket):

    def __init__(self, live_house_id: int, data: bytes):
        super().__init__(live_house_id, data)
        self.popularity = -1

    def get_popularity(self) -> int | None:
        (self.total_len, self.header_len, self.protocol,
         self.packet_type, self.sequence, self.popularity) = (
            struct.unpack('>IHHIII',self.data[:20]))
        return self.popularity


def get_danmaku(json_data) -> interaction.Danmaku | None:
    if json_data is None:
        return None
    if json_data.get('cmd') != 'DANMU_MSG':
        return None
    info = json_data.get('info', ())
    if len(info) < 3:
        return None
    content = info[1]
    if len(info) > 15:
        send_timestamp = info[9]
        rich_data = info[0][15]
        extra_json = json.loads(rich_data['extra'])
        user_json = rich_data['user']
        user_base_json = user_json['base']
        text_info = interaction.TextInfo(
            font_size=extra_json.get('font_size', 25),
            color=extra_json.get('color', 16777215)
        )
        emots: dict = extra_json.get('emots', {})
        emojis = []
        if emots is not None:
            for k, v in emots.items():
                emoji = interaction.EmojiInfo(
                    descript=v['descript'],
                    emoji=v['emoji'],
                    size=(v.get('width', 20), v.get('height', 20)),
                    url=v['url']
                )
                emojis.append(emoji)
        sender = interaction.SenderData(
            mid=user_json.get('uid', 0),
            name=user_base_json['name'],
            name_color=user_base_json['name_color'],
            avatar_url=user_base_json['face'],
            is_me=extra_json.get('send_from_me', False)
        )
        return interaction.Danmaku(
            content=content,
            time=send_timestamp,
            text_info=text_info,
            emoji_infos=emojis,
            sender_data=sender
        )
    else:
        danmaku_info = info[0]
        sender_info = info[2]
        send_timestamp = -1
        if len(info) > 10:
            send_timestamp = info[9]
        else:
            send_timestamp = danmaku_info[4]
        danmaku_font_size = danmaku_info[2]
        danmaku_color = danmaku_info[3]
        text_info = interaction.TextInfo(
            font_size=danmaku_font_size,
            color=danmaku_color
        )

        sender_mid = sender_info[0]
        sender_name = sender_info[1]
        sender_name_color = 0xffffff
        sender_avatar_url = ''
        sender = interaction.SenderData(
            mid=sender_mid,
            name=sender_name,
            name_color=sender_name_color,
            avatar_url=sender_avatar_url,
            is_me=False
        )
        return interaction.Danmaku(
            content=content,
            time=send_timestamp,
            text_info=text_info,
            emoji_infos=[],
            sender_data=sender
        )


class MQHost:

    def __init__(self, host: str, port: int, wss_port: int, ws_port: int):
        self.host = host
        self.port = port
        self.wss_port = wss_port
        self.ws_port = ws_port


    def get_ws_url(self) -> str:
        return f'ws://{self.host}:{self.ws_port}/sub'


    def get_wss_url(self) -> str:
        return f'wss://{self.host}:{self.wss_port}/sub'


    def get_url(self):
        return f'https://{self.host}:{self.port}/sub'


    async def verify(self, socket, live_house_id: int, mid: int, token: str) -> bool:
        try:
            packet = VerifyPacket(live_house_id, mid, token)
            await packet.send(socket)
            response = await socket.recv()
            packet = VerifyResponsePacket(live_house_id, response)
            return packet.is_ok()
        except Exception as e:
            return False


    async def heartbeat(self, socket) -> int:
        try:
            packet = HeartbeatUploadPacket(0)
            await packet.send(socket)
            response = await socket.recv()
            packet = HeartbeatResponsePacket(0, response)
            return packet.get_popularity()
        except Exception as e:
            return -1


class LiveHouse:

    def __init__(self,
                 room_id: int,
                 refresh_factor: float,
                 refresh_rate: float,
                 max_delay: float,
                 token: str,
                 host_list: list[MQHost]):
        self.room_id = room_id
        self.refresh_factor = refresh_factor
        self.refresh_rate = refresh_rate
        self.max_delay = max_delay
        self.token = token
        self.host_list = host_list


def get_live_house(live_house_id: int, session: Session, wbi: tuple[str, str]) -> LiveHouse | int:
    img_key, sub_key = wbi[0], wbi[1]
    signed_params = encrypter.enc_wbi(
       params  = {'id': live_house_id},
       img_key = img_key,
       sub_key = sub_key
    )

    response = requests.get("https://api.live.bilibili.com/xlive/web-room/v1/index/getDanmuInfo",
                            headers=constants.headers, cookies=session.cookies, params=signed_params)

    json_obj = response.json()
    if json_obj['code'] != 0:
        return json_obj['code']

    data = json_obj['data']
    refresh_factor = data['refresh_row_factor']
    refresh_rate = data['refresh_rate']
    max_delay = data['max_delay']
    token = data['token']
    host_list: list[MQHost] = []
    for item in data['host_list']:
        host_list.append(MQHost(
            host=item['host'],
            port=item['port'],
            wss_port=item['wss_port'],
            ws_port=item['ws_port']
        ))
    return LiveHouse(
        room_id=live_house_id,
        refresh_factor=refresh_factor,
        refresh_rate=refresh_rate,
        max_delay=max_delay,
        token=token,
        host_list=host_list
    )


def decode_packets(live_house_id: int, packet_bytes: bytes) -> list[DownloadPacket]:
    total_len, header_len, protocol, packet_type, sequence = struct.unpack('>IHHII', packet_bytes[0 : 16])
    match protocol:
        case 0:
            return [DownloadPacket(live_house_id, packet_bytes)]
        case 1:
            return []
        case 2:
            return [DownloadPacket(live_house_id, packet_bytes)]
        case 3:
            packet_bytes = decompress.decompress(packet_bytes[16:], 'brotli')
            packets = []
            offset = 0
            while offset < len(packet_bytes):
                lens, h_len, proto, p_type, seq = struct.unpack('>IHHII', packet_bytes[offset:offset + 16])
                packet_data = packet_bytes[offset:offset + lens]
                packets.append(DownloadPacket(live_house_id, packet_data))
                offset += lens
            return packets
    return []


class LiveEventLoop:


    def __init__(self, live: LiveHouse, host: MQHost, user: User, heartbeat_interval: float = 30.0):
        self.live = live
        self.user = user
        self.host = host
        self.heartbeat_interval = heartbeat_interval
        self.popularity = -1
        self.ended = False
        self.running = False
        self.received_danmakus = []


    async def start(self):
        self.__set_state__(True, False)
        try:
            async with websockets.connect(self.host.get_ws_url()) as ws:
                verified = await self.host.verify(ws, self.live.room_id, self.user.mid, self.live.token)
                if not verified:
                    self.__set_state__(False, True)
                    return
                asyncio.create_task(self.heartbeat_loop(ws))
                while True:
                    response = await ws.recv()
                    packets = decode_packets(self.live.room_id, response)
                    for packet in packets:
                        try:
                            json_data = packet.decode()
                            danmaku = get_danmaku(json_data)
                            if danmaku is not None:
                                self.received_danmakus.append(danmaku)
                                print(f'{danmaku.get_time()} - {danmaku.sender_data.name}: {danmaku.content} ')
                        except Exception as e:
                            continue
        finally:
            self.__set_state__(False, True)


    def pop_danmakus(self) -> list[interaction.Danmaku]:
        danmakus = self.received_danmakus.copy()
        self.received_danmakus.clear()
        return danmakus


    def stop(self) -> list[interaction.Danmaku]:
        self.__set_state__(False, True)
        return self.pop_danmakus()


    async def heartbeat_loop(self, ws):
        while self.running and not self.ended:
            popularity = await self.host.heartbeat(ws)
            if popularity != -1:
                self.popularity = popularity
            await asyncio.sleep(self.heartbeat_interval)


    def __set_state__(self, running: bool, ended: bool):
        self.running = running
        self.ended = ended