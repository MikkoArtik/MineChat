import os
import json
import logging
from datetime import datetime

import asyncio
import aiofiles
from asyncio import StreamReader, StreamWriter
from contextlib import asynccontextmanager


EMPTY_LINE = '\n'


class InvalidToken(Exception):
    pass


@asynccontextmanager
async def create_connection(host_address: str, port: int):
    reader, writer = await asyncio.open_connection(host_address, port)
    try:
        yield reader, writer
    except Exception as e:
        logging.error(str(e))
    finally:
        writer.close()
        await writer.wait_closed()


def format_msg(msg_text: str) -> str:
    current_datetime = datetime.now().strftime('%d.%m.%y %H:%M')
    return f'[{current_datetime}] {msg_text}'


async def read_msgs(host: str, port: int,
                    showing_msg_queue: asyncio.Queue,
                    saving_msg_queue: asyncio.Queue,
                    msg_history_file: str):
    if os.path.exists(msg_history_file):
        async with aiofiles.open(msg_history_file) as handle:
            async for line in handle:
                showing_msg_queue.put_nowait(line.rstrip())

    async with create_connection(host, port) as connection:
        reader, writer = connection
        while True:
            server_response = await reader.readline()
            try:
                text_line = server_response.decode('utf-8').rstrip()
            except UnicodeDecodeError:
                break

            msg_text = format_msg(text_line)
            showing_msg_queue.put_nowait(msg_text)
            saving_msg_queue.put_nowait(msg_text)


async def save_msgs(filepath: str, queue: asyncio.Queue):
    async with aiofiles.open(filepath, 'a') as f:
        while True:
            msg_text = await queue.get()
            await f.write(f'{msg_text}\n')


async def send_msgs(host: str, port: int, queue: asyncio.Queue):
    while True:
        msg_text = await queue.get()
        logging.debug(f'Пользователь написал: {msg_text}')


async def listen_server(reader: StreamReader, output_file: str):
    async with aiofiles.open(output_file, 'a', encoding='utf-8') as handle:
        await handle.write('-' * 50 + '\n')

        message = format_msg('Соединение установлено')
        logging.debug(message)
        await handle.write(f'{message}\n')

        while True:
            server_response = await reader.readline()
            try:
                text_line = server_response.decode('utf-8').rstrip()
            except UnicodeDecodeError:
                break
            message = format_msg(text_line)
            logging.debug(message)
            await handle.write(f'{message}\n')


async def register(reader: StreamReader, writer: StreamWriter, nickname: str) -> str:
    await reader.readline()

    writer.write(EMPTY_LINE.encode())
    await writer.drain()

    await reader.readline()

    nickname = nickname.replace('\n', '-')
    writer.write(f'{nickname}\n'.encode())
    await writer.drain()

    server_line = await reader.readline()
    user_info = json.loads(server_line.decode())

    logging.debug(f'Account token: {user_info["account_hash"]}')

    await reader.readline()
    return user_info['account_hash']


async def authorize(reader: StreamReader, writer: StreamWriter,
                    token: str):
    await reader.readline()

    token += '\n'
    writer.write(token.encode())
    await writer.drain()

    hash_info = await reader.readline()
    hash_info = hash_info.decode().rstrip()
    if json.loads(hash_info) is None:
        raise InvalidToken(f'Token {token} is not exist')

    logging.debug('Авторизация прошла успешно')
    await reader.readline()


async def submit_message(writer: StreamWriter, message_text: str):
    message_text = message_text.rstrip() + '\n\n'
    writer.write(message_text.encode())
    await writer.drain()
    logging.debug('Сообщение успешно отправлено')
