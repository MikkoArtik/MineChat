import os
import json
import logging

import asyncio
from asyncio import StreamReader, StreamWriter

import dotenv

EMPTY_LINE = '\n'
MAX_MESSAGE_BYTE_SIZE = 1024


def change_env_file(hash_value: str):
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.close()
    dotenv.load_dotenv()
    dotenv.set_key('.env', 'TOKEN', hash_value)
    logging.debug('Hash-код сохранен в файл')


async def get_connection(host_addr: str, port: int):
    try:
        reader, writer = await asyncio.open_connection(host_addr, port)
        return reader, writer
    except ConnectionRefusedError:
        logging.error('Ошибка соединения')
        return


async def register(reader: StreamReader, writer: StreamWriter, nickname: str):
    await reader.readline()

    writer.write(EMPTY_LINE.encode())
    await writer.drain()

    await reader.readline()

    writer.write(f'{nickname}\n'.encode())
    await writer.drain()

    user_info = await reader.readline()
    user_info = json.loads(user_info.decode())

    logging.debug(f'Hash-код аккаунта: {user_info["account_hash"]}')
    change_env_file(user_info['account_hash'])

    writer.close()
    await writer.wait_closed()
    logging.debug('Соединение закрыто')


async def authorise(reader: StreamReader, writer: StreamWriter, hash_key: str):
    await reader.read(MAX_MESSAGE_BYTE_SIZE)

    hash_key += '\n'
    writer.write(hash_key.encode())
    await writer.drain()

    hash_info = await reader.readline()
    hash_info = hash_info.decode().rstrip()
    if json.loads(hash_info) is None:
        logging.error(
            'Неверный токен. Проверьте его или зарегистрируйте заново')
        writer.close()
        await writer.wait_closed()
        logging.debug('Соединение закрыто')


async def submit_message(reader: StreamReader, writer: StreamWriter,
                         message_text: str):
    await reader.read(MAX_MESSAGE_BYTE_SIZE)

    message_text += '\n\n'
    writer.write(message_text.encode())
    await writer.drain()
