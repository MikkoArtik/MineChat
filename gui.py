import os
import logging
from argparse import ArgumentParser

import asyncio

from tkinter import messagebox

import dotenv
import anyio

import interface
from interface import TkAppClosed

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
    parser.add_argument('--default', type=bool, choices=[True, False],
                        help='Default connection parameters')
    parser.add_argument('--host', type=str, help='Host address')
    parser.add_argument('--read_port', type=int, help='Reading host port')
    parser.add_argument('--send_port', type=int, help='Sending host port')
    parser.add_argument('--token', type=str, help='User token')
    parser.add_argument('--timeout', type=float,
                        help='Connection timeout (sec)')
    parser.add_argument('--debug', type=bool, choices=[True, False],
                        help='Turn on debug mode')

    dotenv.load_dotenv(ENV_FILE)
    arguments = parser.parse_args()

    connection_logger = logging.getLogger('ConnectionLogger')
    if arguments.debug:
        logging.basicConfig(level=logging.DEBUG)
        connection_logger.setLevel(logging.DEBUG)

    if arguments.default:
        host = DEFAULT_HOST
        read_port, send_port = READING_PORT, SENDING_PORT
    else:
        if arguments.host and arguments.read_port and arguments.send_port:
            host = arguments.host
            read_port = arguments.read_port
            send_port = arguments.send_port
        else:
            raise Exception('Host address and/or port is not exist')

    if arguments.token:
        token = arguments.token
    else:
        token = os.getenv('TOKEN')

    if arguments.timeout:
        timeout = arguments.timeout
    else:
        timeout = DEFAULT_TIMEOUT_SEC

    connection_params = ConnectionParameters(host, read_port, send_port, token,
                                             timeout)
    server_conn = ServerConnection(connection_params, MSG_HISTORY_FILE)
    try:
        async with anyio.create_task_group() as task_ctx:
            task_ctx.start_soon(interface.draw,
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
