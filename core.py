from typing import NamedTuple
from datetime import datetime
import os
import logging
import json

import socket

import asyncio
from asyncio import StreamReader, StreamWriter
from asyncio import Queue
from contextlib import asynccontextmanager

import aiofiles
import async_timeout
import anyio

from messenger_interface import ReadConnectionStateChanged
from messenger_interface import SendingConnectionStateChanged
from messenger_interface import NicknameReceived


NULL_NICKNAME = 'неизвестно'
BOT_NAMES_FILTER = ['eva', 'vlad']


class InvalidToken(Exception):
    pass


class TimeoutException(Exception):
    pass


class ConnectionParameters(NamedTuple):
    host: str
    read_port: int
    send_port: int
    token: str
    timeout_sec: float


def is_bot(nickname: str) -> bool:
    for template in BOT_NAMES_FILTER:
        if template in nickname.lower():
            return True
    return False


@asynccontextmanager
async def create_connection(host: str, port: int):
    reader, writer = await asyncio.open_connection(host, port)
    try:
        yield reader, writer
    finally:
        writer.close()
        await writer.wait_closed()


async def register(reader: StreamReader, writer: StreamWriter, nickname: str) -> str:
    await reader.readline()

    writer.write('\n'.encode())
    await writer.drain()

    await reader.readline()

    writer.write(f'{nickname}\n'.encode())
    await writer.drain()

    server_response = await reader.readline()
    user_info = json.loads(server_response.decode('utf-8').rstrip())
    if user_info is None:
        raise InvalidToken('Empty server response')
    return user_info['account_hash']


async def authorize(reader: StreamReader, writer: StreamWriter, token: str) -> str:
    await reader.readline()

    line = token + '\n'
    writer.write(line.encode())
    await writer.drain()

    server_response = await reader.readline()
    server_response = server_response.decode().rstrip()
    hash_info = json.loads(server_response)
    if hash_info is None:
        raise InvalidToken(f'Token {token} is not exist')
    await reader.readline()
    return hash_info['nickname']


class ConnectionStatement:
    def __init__(self, timeout_sec: float, is_enable=False):
        self.timestamp = int(datetime.now().timestamp())
        self.is_enable = is_enable
        self.timeout_sec = timeout_sec

    @property
    def status_notification(self) -> str:
        if self.is_enable:
            return f'[{self.timestamp}] Connection is alive'
        else:
            return f'[{self.timestamp}] {self.timeout_sec}s timeout is elapsed'


class Reader:
    def __init__(self, conn_params: ConnectionParameters,
                 msg_history_file: str):
        self.__conn_params = conn_params
        self.__msg_history_file = msg_history_file

        self.showing_msgs_queue = Queue()
        self.saving_msgs_queue = Queue()

    @property
    def conn_params(self) -> ConnectionParameters:
        return self.__conn_params

    @property
    def msg_history_file(self) -> str:
        return self.__msg_history_file

    @staticmethod
    def format_msg(msg_text: str) -> str:
        current_datetime = datetime.now().strftime('%d.%m.%y %H:%M')
        return f'[{current_datetime}] {msg_text}'

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
        host, port = self.conn_params.host, self.conn_params.read_port
        try:
            async with create_connection(host, port) as connection:
                reader, _ = connection
                while True:
                    server_response = await reader.readline()
                    msg_text = server_response.decode('utf-8').rstrip()

                    nickname = msg_text.split(':')[0]
                    if is_bot(nickname):
                        continue

                    format_msg_text = self.format_msg(msg_text)
                    self.showing_msgs_queue.put_nowait(format_msg_text)
                    self.saving_msgs_queue.put_nowait(format_msg_text)
        except socket.gaierror:
            return

    async def run(self):
        async with anyio.create_task_group() as task_ctx:
            task_ctx.start_soon(self.start_reading)
            task_ctx.start_soon(self.save_msgs_to_file)


class Sender:
    def __init__(self, conn_params: ConnectionParameters):
        self.__conn_params = conn_params
        self.sending_msgs_queue = Queue()

    @property
    def conn_params(self) -> ConnectionParameters:
        return self.__conn_params

    async def run(self):
        host, port = self.conn_params.host, self.conn_params.send_port
        try:
            async with create_connection(host, port) as connection:
                reader, writer = connection
                await authorize(reader, writer, self.conn_params.token)
                while True:
                    msg_text = await self.sending_msgs_queue.get()
                    msg_text = msg_text.rstrip() + '\n\n'
                    writer.write(msg_text.encode())
                    await writer.drain()
                    await reader.readline()
        except socket.gaierror:
            return


class ServerConnection:
    def __init__(self, params: ConnectionParameters,
                 msgs_history_file: str):
        self.__conn_params = params

        self.status_queue = Queue()
        self.conn_statement_queue = Queue()

        self.reader = Reader(params, msgs_history_file)
        self.sender = Sender(params)
        self.logger = logging.getLogger('ConnectionState')

        self.__is_interrupt_connection = False

    @property
    def conn_params(self) -> ConnectionParameters:
        return self.__conn_params

    def initialize_interruption(self):
        self.__is_interrupt_connection = True

    async def ping_server(self):
        self.status_queue.put_nowait(ReadConnectionStateChanged.INITIATED)
        self.status_queue.put_nowait(SendingConnectionStateChanged.INITIATED)
        self.status_queue.put_nowait(NicknameReceived(NULL_NICKNAME))

        host, port = self.conn_params.host, self.conn_params.send_port
        timeout_sec = self.conn_params.timeout_sec
        async with create_connection(host, port) as conn_ctx:
            reader, writer = conn_ctx
            try:
                async with async_timeout.timeout(timeout_sec) as time_ctx:
                    nickname = await authorize(reader, writer,
                                               self.conn_params.token)
            except asyncio.TimeoutError:
                if time_ctx.expired:
                    state = ConnectionStatement(timeout_sec, False)
                    self.conn_statement_queue.put_nowait(state)
                    raise TimeoutException
                else:
                    raise

            self.status_queue.put_nowait(NicknameReceived(nickname))
            self.status_queue.put_nowait(ReadConnectionStateChanged.ESTABLISHED)
            self.status_queue.put_nowait(SendingConnectionStateChanged.ESTABLISHED)

            state = ConnectionStatement(timeout_sec, True)
            self.conn_statement_queue.put_nowait(state)

            while True:
                writer.write('\n\n'.encode())
                try:
                    async with async_timeout.timeout(timeout_sec) as time_ctx:
                        await writer.drain()
                        await reader.readline()
                except asyncio.TimeoutError:
                    if time_ctx.expired:
                        state = ConnectionStatement(timeout_sec, False)
                        self.conn_statement_queue.put_nowait(state)
                        raise TimeoutException
                    else:
                        raise

                state = ConnectionStatement(timeout_sec, True)
                self.conn_statement_queue.put_nowait(state)
                await asyncio.sleep(timeout_sec)

    async def print_connection_state(self):
        while True:
            state: ConnectionStatement = await self.conn_statement_queue.get()
            self.logger.debug(state.status_notification)

    async def run(self):
        await self.reader.load_msgs_history()
        while not self.__is_interrupt_connection:
            try:
                async with anyio.create_task_group() as my_ctx:
                    my_ctx.start_soon(self.ping_server)
                    my_ctx.start_soon(self.print_connection_state)
                    my_ctx.start_soon(self.reader.run)
                    my_ctx.start_soon(self.sender.run)
            except (socket.gaierror, TimeoutException):
                self.logger.debug(f'Trying to connect after {self.conn_params.timeout_sec}s...')
                await asyncio.sleep(self.conn_params.timeout_sec)

        self.status_queue.put_nowait(ReadConnectionStateChanged.CLOSED)
        self.status_queue.put_nowait(SendingConnectionStateChanged.CLOSED)
