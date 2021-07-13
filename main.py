import os
from datetime import datetime
import logging
import argparse

import dotenv

import asyncio
import aiofiles


def message_formatting(message: str) -> str:
    current_datetime = datetime.now().strftime('%d.%m.%y %H:%M')
    return f'[{current_datetime}] {message}'


async def save_messages(host: str, port: int, output_file: str):
    try:
        reader, writer = await asyncio.open_connection(host, port)
    except ConnectionRefusedError:
        logging.error('Host is unreachable')
        return

    async with aiofiles.open(output_file, 'a') as file_handle:
        message = message_formatting('Установлено соединение')
        logging.debug(message)
        await file_handle.write('-' * 50 + '\n')
        await file_handle.write(message + '\n')

        while True:
            message = await reader.readline()
            try:
                message = message.decode().rstrip()
            except UnicodeDecodeError:
                break

            message = message_formatting(message)
            await file_handle.write(message + '\n')
            await file_handle.flush()
            logging.debug(message)
    writer.close()
    await writer.wait_closed()


if __name__ == '__main__':
    dotenv.load_dotenv()

    parser = argparse.ArgumentParser(description='Minechat listener')
    parser.add_argument('--host', type=str, help='server host')
    parser.add_argument('--port', type=int, help='server port number')
    parser.add_argument('--out', type=str,
                        help='output path message history file')
    parser.add_argument('--debug', type=str,
                        help='turn on/off logger. Values - ON/OFF')
    args = parser.parse_args()

    if ((not args.host or not args.port or not args.out) and
            not os.path.exists('.env')):
        logging.error('required parameters not found')
        exit()

    if args.debug == 'ON':
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.ERROR)

    host_addr = args.host if args.host else os.getenv('HOST')
    port = args.port if args.port else int(os.getenv('PORT'))
    out_path = args.out if args.out else os.getenv('OUT')

    asyncio.run(save_messages(host_addr, port, out_path))
