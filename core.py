import json
import logging

import asyncio
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
    except InvalidToken:
        logging.error('Invalid token. Check token or register new user')
    finally:
        writer.close()
        await writer.wait_closed()


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

    await reader.readline()


async def submit_message(writer: StreamWriter, message_text: str):
    message_text = message_text.rstrip() + '\n\n'
    writer.write(message_text.encode())
    await writer.drain()
