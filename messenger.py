import os
import logging
from argparse import ArgumentParser

import asyncio

from tkinter import messagebox

import dotenv
import anyio

import messenger_interface
from messenger_interface import TkAppClosed

from core import InvalidToken
from core import ConnectionParameters
from core import ServerConnection


DEFAULT_HOST = 'minechat.dvmn.org'
READING_PORT, SENDING_PORT = 5000, 5050
DEFAULT_TIMEOUT_SEC = 3
MSG_HISTORY_FILE = 'm.txt'
ENV_FILE = '.env'


async def main():
    parser = ArgumentParser(description='GUI utility for minecraft chatting')
    parser.add_argument('--timeout', type=float,
                        help='Connection timeout (sec)')
    parser.add_argument('--debug', type=bool, choices=[True, False],
                        help='Turn on debug mode')

    dotenv.load_dotenv(ENV_FILE)
    arguments = parser.parse_args()

    if arguments.debug:
        logging.basicConfig(level=logging.DEBUG)

    if arguments.timeout:
        timeout_sec = arguments.timeout
    else:
        timeout_sec = DEFAULT_TIMEOUT_SEC

    token = os.getenv('TOKEN')
    if not token:
        raise Exception("Env file with token don't found")

    connection_params = ConnectionParameters(DEFAULT_HOST, READING_PORT,
                                             SENDING_PORT, token, timeout_sec)
    server_conn = ServerConnection(connection_params, MSG_HISTORY_FILE)
    try:
        async with anyio.create_task_group() as task_ctx:
            task_ctx.start_soon(messenger_interface.draw,
                                server_conn.reader.showing_msgs_queue,
                                server_conn.sender.sending_msgs_queue,
                                server_conn.status_queue)
            task_ctx.start_soon(server_conn.run)
        dotenv.set_key(ENV_FILE, 'TOKEN', token)
    except InvalidToken:
        messagebox.showinfo('Неверный токен',
                            'Проверьте правильность ввода токена')
    except TkAppClosed:
        server_conn.initialize_interruption()


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.debug('App was closed')
