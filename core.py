import os
import json
from datetime import datetime

import asyncio
from asyncio import StreamReader, StreamWriter
from asyncio import Queue
from contextlib import asynccontextmanager

import aiofiles
import async_timeout

from interface import ReadConnectionStateChanged
from interface import SendingConnectionStateChanged
from interface import NicknameReceived


READ_CONNECTION, SEND_CONNECTION = 0, 1


def format_msg(msg_text: str) -> str:
    current_datetime = datetime.now().strftime('%d.%m.%y %H:%M')
    return f'[{current_datetime}] {msg_text}'


class InvalidToken(Exception):
    pass


class ConnectionStatement:
    def __init__(self, timeout_sec: float, connection_type: int):
        self.timestamp = int(datetime.now().timestamp())
        self.state = False
        self.timeout_sec = timeout_sec
        self.connection_type = connection_type

    def set_state(self, is_enable: bool):
        self.state = is_enable

    @property
    def status_notification(self) -> str:
        if self.state:
            notification = f'[{self.timestamp}] Connection is alive. '
            if self.connection_type == READ_CONNECTION:
                return notification + 'New message in chat'
            else:
                return notification + 'Message was sent'
        else:
            return f'[{self.timestamp}] {self.timeout_sec}s timeout is elapsed'


class Reader:
    def __init__(self, host: str, port: int, msg_history_file: str,
                 timeout_sec: float, status_queue: Queue,
                 connection_statement_queue: Queue):
        self.__host = host
        self.__port = port
        self.__msg_history_file = msg_history_file
        self.__timeout_sec = timeout_sec

        self.showing_msgs_queue = Queue()
        self.saving_msgs_queue = Queue()
        self.status_queue = status_queue
        self.connection_statement_queue = connection_statement_queue

    @property
    def host(self) -> str:
        return self.__host

    @property
    def port(self) -> int:
        return self.__port

    @property
    def msg_history_file(self):
        return self.__msg_history_file

    @property
    def timeout_sec(self) -> float:
        return self.__timeout_sec

    @asynccontextmanager
    async def create_connection(self):
        queue = self.status_queue
        queue.put_nowait(ReadConnectionStateChanged.INITIATED)
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            queue.put_nowait(ReadConnectionStateChanged.ESTABLISHED)
            yield reader, writer
        finally:
            queue.put_nowait(ReadConnectionStateChanged.CLOSED)
            writer.close()
            await writer.wait_closed()

    async def load_msgs_history(self):
        if not os.path.exists(self.msg_history_file):
            return

        async with aiofiles.open(self.msg_history_file, 'r') as f:
            async for line in f:
                self.showing_msgs_queue.put_nowait(line.rstrip())

    async def save_msgs_to_file(self):
        async with aiofiles.open(self.msg_history_file, 'a') as f:
            while True:
                msg_text = await self.saving_msgs_queue.get()
                await f.write(f'{msg_text}\n')

    async def start_reading(self):
        async with self.create_connection() as connection:
            reader, _ = connection
            while True:
                state = ConnectionStatement(self.timeout_sec, READ_CONNECTION)
                try:
                    with async_timeout.timeout(self.timeout_sec) as time_ctx:
                        server_response = await reader.readline()

                    state.set_state(is_enable=True)

                    msg_text = server_response.decode('utf-8').rstrip()
                    format_msg_text = format_msg(msg_text)

                    self.showing_msgs_queue.put_nowait(format_msg_text)
                    self.saving_msgs_queue.put_nowait(format_msg_text)
                except asyncio.TimeoutError:
                    if time_ctx.expired:
                        state.set_state(is_enable=False)
                    else:
                        raise
                self.connection_statement_queue.put_nowait(state)

    async def run(self):
        await self.load_msgs_history()
        await asyncio.gather(self.start_reading(), self.save_msgs_to_file())


class Sender:
    def __init__(self, host: str, port: int, token: str,
                 timeout_sec: float, status_queue: Queue,
                 connection_statement_queue: Queue):
        self.__host = host
        self.__port = port
        self.__token = token
        self.__timeout_sec = timeout_sec

        self.sending_msgs_queue = Queue()
        self.status_queue = status_queue
        self.connection_statement_queue = connection_statement_queue

    @property
    def host(self) -> str:
        return self.__host

    @property
    def port(self) -> int:
        return self.__port

    @property
    def token(self) -> str:
        return self.__token

    @property
    def timeout_sec(self) -> float:
        return self.__timeout_sec

    @asynccontextmanager
    async def create_connection(self):
        self.status_queue.put_nowait(SendingConnectionStateChanged.INITIATED)
        reader, writer = await asyncio.open_connection(self.host, self.port)
        try:
            self.status_queue.put_nowait(SendingConnectionStateChanged.ESTABLISHED)
            yield reader, writer
        finally:
            self.status_queue.put_nowait(SendingConnectionStateChanged.CLOSED)
            writer.close()
            await writer.wait_closed()

    async def authorize(self, reader: StreamReader, writer: StreamWriter):
        await reader.readline()

        line = self.token + '\n'
        writer.write(line.encode())
        await writer.drain()

        server_response = await reader.readline()
        server_response = server_response.decode().rstrip()
        hash_info = json.loads(server_response)
        if hash_info is None:
            raise InvalidToken(f'Token {self.token} is not exist')
        await reader.readline()
        return hash_info['nickname']

    async def run(self):
        async with self.create_connection() as connection:
            reader, writer = connection
            nickname = await self.authorize(reader, writer)
            self.status_queue.put_nowait(NicknameReceived(nickname))

            while True:
                state = ConnectionStatement(self.timeout_sec, SEND_CONNECTION)
                msg_text = await self.sending_msgs_queue.get()
                msg_text = msg_text.rstrip() + '\n\n'
                writer.write(msg_text.encode())
                try:
                    with async_timeout.timeout(self.timeout_sec) as time_ctx:
                        await writer.drain()
                    state.set_state(is_enable=True)
                except asyncio.TimeoutError:
                    if time_ctx.expired:
                        state.set_state(is_enable=False)
                    else:
                        raise
                self.connection_statement_queue.put_nowait(state)
