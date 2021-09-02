import json
import logging
from datetime import datetime

import asyncio
import aiofiles
from asyncio import StreamReader, StreamWriter
from contextlib import asynccontextmanager


EMPTY_LINE = '\n'
MAX_MESSAGE_BYTE_SIZE = 1024


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


def message_formatting(message: str) -> str:
    current_datetime = datetime.now().strftime('%d.%m.%y %H:%M')
    return f'[{current_datetime}] {message}'


async def listen_server(reader: StreamReader, output_file: str):
    async with aiofiles.open(output_file, 'a') as handle:
        await handle.write('-' * 50 + '\n')

        message = message_formatting('Соединение установлено')
        logging.debug(message)
        await handle.write(f'{message}\n')

        while True:
            server_response = await reader.readline()
            try:
                text_line = server_response.decode().rstrip()
            except UnicodeDecodeError:
                break
            message = message_formatting(text_line)
            logging.debug(message)
            await handle.write(f'{message}\n')
            await handle.flush()


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


async def authorization(reader: StreamReader, writer: StreamWriter,
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
