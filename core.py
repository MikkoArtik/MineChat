import json
import logging

import asyncio
from asyncio import StreamReader, StreamWriter

EMPTY_LINE = '\n'
MAX_MESSAGE_BYTE_SIZE = 1024


async def get_connection(host_address: str, port: int):
    try:
        reader, writer = await asyncio.open_connection(host_address, port)
        return reader, writer
    except ConnectionRefusedError:
        logging.error('Error of connection')
        return


async def register(reader: StreamReader, writer: StreamWriter, nickname: str):
    await reader.readline()

    writer.write(EMPTY_LINE.encode())
    await writer.drain()

    await reader.readline()

    nickname = nickname.replace('\n', '-')
    writer.write(f'{nickname}\n'.encode())
    await writer.drain()

    user_info = await reader.readline()
    user_info = json.loads(user_info.decode())

    logging.debug(f'Account token: {user_info["account_hash"]}')

    writer.close()
    await writer.wait_closed()
    logging.debug('Connection was closed')
    return user_info['account_hash']


async def is_authorise(reader: StreamReader, writer: StreamWriter,
                       hash_key: str):
    await reader.read(MAX_MESSAGE_BYTE_SIZE)

    hash_key += '\n'
    writer.write(hash_key.encode())
    await writer.drain()

    hash_info = await reader.readline()
    hash_info = hash_info.decode().rstrip()
    if json.loads(hash_info) is None:
        logging.error('Invalid token. Check token or register new user')
        writer.close()
        await writer.wait_closed()
        logging.debug('Connection was closed')
        return False
    return True


async def submit_message(reader: StreamReader, writer: StreamWriter,
                         message_text: str):
    await reader.read(MAX_MESSAGE_BYTE_SIZE)

    message_text += '\n\n'
    writer.write(message_text.encode())
    await writer.drain()
