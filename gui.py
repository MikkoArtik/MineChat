import os
import logging
from argparse import ArgumentParser
from typing import NamedTuple

import asyncio
from asyncio import Queue

from tkinter import messagebox

import dotenv

from core import InvalidToken
from core import ConnectionStatement
from core import Reader, Sender

import interface


DEFAULT_HOST = 'minechat.dvmn.org'
READING_PORT, SENDING_PORT = 5000, 5050
DEFAULT_TIMEOUT_SEC = 5
MSG_HISTORY_FILE = 'm.txt'
ENV_FILE = '.env'


class ConnectionParameters(NamedTuple):
    host: str
    read_port: int
    send_port: int
    token: str
    timeout_sec: float


async def monitor_connection_status(logger: logging.Logger, queue: Queue):
    while True:
        state: ConnectionStatement = await queue.get()
        logger.debug(state.status_notification)
        if not state.is_enable:
            raise ConnectionError


async def handle_connection(conn_params: ConnectionParameters,
                            logger: logging.Logger):
    status_queue = Queue()
    conn_monitoring_queue = Queue()
    reader = Reader(conn_params.host, conn_params.read_port,
                    MSG_HISTORY_FILE, conn_params.timeout_sec,
                    status_queue, conn_monitoring_queue)

    sender = Sender(conn_params.host, conn_params.send_port,
                    conn_params.token, conn_params.timeout_sec,
                    status_queue, conn_monitoring_queue)

    draw_interface_coroutine = interface.draw(reader.showing_msgs_queue,
                                              sender.sending_msgs_queue,
                                              status_queue)

    monitor_conn_coroutine = monitor_connection_status(logger,
                                                       conn_monitoring_queue)

    await asyncio.gather(draw_interface_coroutine, reader.run(), sender.run(),
                         monitor_conn_coroutine)


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
    try:
        await handle_connection(connection_params, connection_logger)
        dotenv.set_key(ENV_FILE, 'TOKEN', token)
    except InvalidToken:
        messagebox.showinfo('Неверный токен',
                            'Проверьте правильность ввода токена')


if __name__ == '__main__':
    asyncio.run(main())
