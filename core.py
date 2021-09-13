import os
import json
import logging
from datetime import datetime

import asyncio
import aiofiles
from asyncio import StreamReader, StreamWriter
from contextlib import asynccontextmanager

from interface import ReadConnectionStateChanged
from interface import SendingConnectionStateChanged


class InvalidToken(Exception):
    pass


@asynccontextmanager
async def create_read_connection(host_address: str, port: int,
                                 queue: asyncio.Queue):
    queue.put_nowait(ReadConnectionStateChanged.INITIATED)
    reader, writer = await asyncio.open_connection(host_address, port)
    try:
        queue.put_nowait(ReadConnectionStateChanged.ESTABLISHED)
        yield reader, writer
    except Exception as e:
        logging.error(str(e))
    finally:
        writer.close()
        await writer.wait_closed()
        queue.put_nowait(ReadConnectionStateChanged.CLOSED)


@asynccontextmanager
async def create_send_connection(host_address: str, port: int,
                                 queue: asyncio.Queue):
    queue.put_nowait(SendingConnectionStateChanged.INITIATED)
    reader, writer = await asyncio.open_connection(host_address, port)
    try:
        queue.put_nowait(SendingConnectionStateChanged.ESTABLISHED)
        yield reader, writer
    except Exception as e:
        logging.error(str(e))
    finally:
        writer.close()
        await writer.wait_closed()
        queue.put_nowait(SendingConnectionStateChanged.CLOSED)


async def read_history_msgs(filepath: str, queue: asyncio.Queue):
    if not os.path.exists(filepath):
        return
    async with aiofiles.open(filepath) as handle:
        async for line in handle:
            queue.put_nowait(line.rstrip())


def format_msg(msg_text: str) -> str:
    current_datetime = datetime.now().strftime('%d.%m.%y %H:%M')
    return f'[{current_datetime}] {msg_text}'


async def read_msgs(reader: StreamReader):
    while True:
        server_response = await reader.readline()
        try:
            msg_src_text = server_response.decode('utf-8').rstrip()
            msg_text = format_msg(msg_src_text)
        except UnicodeDecodeError:
            break
        yield msg_text


async def save_msgs(filepath: str, queue: asyncio.Queue):
    async with aiofiles.open(filepath, 'a') as f:
        while True:
            msg_text = await queue.get()
            await f.write(f'{msg_text}\n')


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
    logging.debug(f'Выполнена авторизация. Имя пользователя - {hash_info["nickname"]}')
    await reader.readline()
    return hash_info['nickname']


async def submit_msg(writer: StreamWriter, message_text: str):
    message_text = message_text.rstrip() + '\n\n'
    writer.write(message_text.encode())
    await writer.drain()
    logging.debug('Сообщение успешно отправлено')


async def send_msgs(writer: StreamWriter, queue: asyncio.Queue):
    while True:
        msg_text = await queue.get()
        logging.debug(f'Пользователь написал: {msg_text}')
        await submit_msg(writer, msg_text)
