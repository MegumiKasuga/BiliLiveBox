from typing import Any

from bili.session import Session
from bili import encrypter
from bili import constants
from bili import decompress
import requests
from abc import ABC, abstractmethod
import websockets
import asyncio
import json
import struct


class UploadPacket:

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


class MQHost:

    def __init__(self, host: str, port: int, wss_port: int, ws_port: int):
        self.host = host
        self.port = port
        self.wss_port = wss_port
        self.ws_port = ws_port

    async def verify(self, live_house_id: int, mid: int, token: str):
        try:
            wss_url = f"wss://{self.host}:{self.wss_port}/sub"
            async with websockets.connect(wss_url) as ws:
                packet = VerifyPacket(live_house_id, mid, token)
                await packet.send(ws)
                response = await ws.recv()
                packet = VerifyResponsePacket(live_house_id, response)
                print(f"Verification response from {self.host}:{self.ws_port} - is OK?: {packet.is_ok()}")
        except Exception as e:
            print(f"Failed to connect to {self.host}:{self.ws_port} - {e}")


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


def get_stream_certify_key(live_house_id: int, session: Session, wbi: tuple[str, str]) -> LiveHouse | int:
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