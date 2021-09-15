import os
import json
import logging
from datetime import datetime
from enum import Enum

import asyncio
from asyncio import StreamReader, StreamWriter
from asyncio import Queue
from contextlib import asynccontextmanager

import aiofiles
import async_timeout

from interface import ReadConnectionStateChanged
from interface import SendingConnectionStateChanged


class InvalidToken(Exception):
    pass


class MsgNotification(Enum):
    NEW_MESSAGE = 'New message in chat'
    SENT_MESSAGE = 'Message was sent'


async def read_history_msgs_from_file(filepath: str, queue: Queue):
    if not os.path.exists(filepath):
        return
    async with aiofiles.open(filepath) as handle:
        async for line in handle:
            queue.put_nowait(line.rstrip())


async def save_msgs_to_file(filepath: str, queue: Queue):
    async with aiofiles.open(filepath, 'a') as f:
        while True:
            msg_text = await queue.get()
            await f.write(f'{msg_text}\n')


@asynccontextmanager
async def create_read_connection(host_address: str, port: int,
                                 queue: Queue):
    queue.put_nowait(ReadConnectionStateChanged.INITIATED)
    reader, writer = await asyncio.open_connection(host_address, port)
    try:
        queue.put_nowait(ReadConnectionStateChanged.ESTABLISHED)
        yield reader, writer
    except Exception as e:
        logging.error(str(e))
    finally:
        queue.put_nowait(ReadConnectionStateChanged.CLOSED)
        writer.close()
        await writer.wait_closed()


@asynccontextmanager
async def create_send_connection(host_address: str, port: int,
                                 queue: Queue):
    queue.put_nowait(SendingConnectionStateChanged.INITIATED)
    reader, writer = await asyncio.open_connection(host_address, port)
    try:
        queue.put_nowait(SendingConnectionStateChanged.ESTABLISHED)
        yield reader, writer
    except Exception as e:
        logging.error(str(e))
    finally:
        queue.put_nowait(SendingConnectionStateChanged.CLOSED)
        writer.close()
        await writer.wait_closed()


async def authorize(reader: StreamReader, writer: StreamWriter,
                    token: str):
    await reader.readline()

    token += '\n'
    writer.write(token.encode())
    await writer.drain()

    server_response = await reader.readline()
    server_response = server_response.decode().rstrip()
    hash_info = json.loads(server_response)
    if hash_info is None:
        raise InvalidToken(f'Token {token} is not exist')
    await reader.readline()
    return hash_info['nickname']


def format_msg(msg_text: str) -> str:
    current_datetime = datetime.now().strftime('%d.%m.%y %H:%M')
    return f'[{current_datetime}] {msg_text}'


def format_notification(text_val: str) -> str:
    timestamp = int(datetime.now().timestamp())
    return f'[{timestamp}] Connection is alive. {text_val}'


def format_failure_connection_notification(timeout_sec: float) -> str:
    timestamp = int(datetime.now().timestamp())
    return f'[{timestamp}] {timeout_sec}s timeout is elapsed'


async def read_server_msgs(host: str, port: int, msg_history_file: str,
                           status_queue: Queue, showing_msg_queue: Queue,
                           saving_msg_queue: Queue,
                           connection_status_queue: Queue, timeout_sec=1.0):
    await read_history_msgs_from_file(msg_history_file, showing_msg_queue)
    async with create_read_connection(host, port, status_queue) as connection:
        reader, _ = connection
        while True:
            try:
                with async_timeout.timeout(timeout_sec) as time_ctx:
                    server_response = await reader.readline()
            except asyncio.TimeoutError:
                if time_ctx.expired:
                    notification = format_failure_connection_notification(timeout_sec)
                    connection_status_queue.put_nowait(notification)
                    continue
                else:
                    raise

            msg_src_text = server_response.decode('utf-8').rstrip()
            msg_text = format_msg(msg_src_text)

            showing_msg_queue.put_nowait(msg_text)
            saving_msg_queue.put_nowait(msg_text)

            notification = format_notification(MsgNotification.NEW_MESSAGE.value)
            connection_status_queue.put_nowait(notification)


async def send_server_msgs(writer: StreamWriter, queue: asyncio.Queue,
                           connection_status_queue: Queue, timeout_sec=1.0):
    while True:
        msg_text = await queue.get()
        msg_text = msg_text.rstrip() + '\n\n'
        writer.write(msg_text.encode())
        try:
            with async_timeout.timeout(timeout_sec) as time_ctx:
                await writer.drain()
        except asyncio.TimeoutError:
            if time_ctx.expired:
                notification = format_failure_connection_notification(
                    timeout_sec)
                connection_status_queue.put_nowait(notification)
                continue
            else:
                raise

        notification = format_notification(MsgNotification.SENT_MESSAGE.value)
        connection_status_queue.put_nowait(notification)
