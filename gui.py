import os
import logging
from argparse import ArgumentParser

import asyncio
from asyncio import Queue

from tkinter import messagebox

import dotenv

from core import InvalidToken
from core import ConnectionStatement
from core import Reader, Sender

import interface
from interface import NicknameReceived


DEFAULT_HOST = 'minechat.dvmn.org'
READING_PORT, SENDING_PORT = 5000, 5050
DEFAULT_TIMEOUT_SEC = 1
MSG_HISTORY_FILE = 'm.txt'
ENV_FILE = '.env'


async def print_connection_status(logger: logging.Logger, queue: Queue):
    while True:
        state: ConnectionStatement = await queue.get()
        logger.debug(state.status_notification)


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

    status_queue = Queue()
    watchdog_queue = Queue()

    reader = Reader(host, read_port, MSG_HISTORY_FILE, timeout, status_queue,
                    watchdog_queue)

    sender = Sender(host, send_port, token, timeout, status_queue,
                    watchdog_queue)

    draw_interface_coroutine = interface.draw(reader.showing_msgs_queue,
                                              sender.sending_msgs_queue,
                                              status_queue)

    connection_logging_coroutine = print_connection_status(
        connection_logger, watchdog_queue)

    try:
        await asyncio.gather(draw_interface_coroutine, sender.run(),
                             reader.run(), connection_logging_coroutine)
        dotenv.set_key(ENV_FILE, 'TOKEN', token)
    except InvalidToken:
        messagebox.showinfo('Неверный токен',
                            'Проверьте правильность ввода токена')
        return


if __name__ == '__main__':
    asyncio.run(main())
