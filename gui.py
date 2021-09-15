import os
import logging
from argparse import ArgumentParser

import asyncio
from asyncio import Queue

from tkinter import messagebox

import dotenv

from core import InvalidToken
from core import create_send_connection, authorize
from core import read_server_msgs, save_msgs_to_file, send_server_msgs

import interface
from interface import NicknameReceived


DEFAULT_HOST = 'minechat.dvmn.org'
READING_PORT, SENDING_PORT = 5000, 5050
MSG_HISTORY_FILE = 'm.txt'


async def print_connection_status(logger: logging.Logger, queue: Queue):
    while True:
        line = await queue.get()
        logger.debug(line)


async def main():
    parser = ArgumentParser(description='GUI utility for minecraft chatting')
    parser.add_argument('--default', type=bool, choices=[True, False],
                        help='Default connection parameters')
    parser.add_argument('--host', type=str, help='Host address')
    parser.add_argument('--read_port', type=int, help='Reading host port')
    parser.add_argument('-send_port', type=int, help='Sending host port')
    parser.add_argument('--token', type=str, help='User token')
    parser.add_argument('--debug', type=bool, choices=[True, False],
                        help='Turn on debug mode')

    dotenv.load_dotenv('.env')
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

    showing_msg_queue = Queue()
    saving_msgs_queue = Queue()

    sending_queue = Queue()
    status_queue = Queue()

    watchdog_queue = Queue()

    draw_interface_coroutine = interface.draw(showing_msg_queue,
                                              sending_queue,
                                              status_queue)

    read_coroutine = read_server_msgs(host, read_port, MSG_HISTORY_FILE,
                                      status_queue, showing_msg_queue,
                                      saving_msgs_queue, watchdog_queue)

    save_coroutine = save_msgs_to_file(MSG_HISTORY_FILE, saving_msgs_queue)

    connection_logging_coroutine = print_connection_status(
        connection_logger, watchdog_queue)

    async with create_send_connection(host, send_port, status_queue) as connection:
        reader, writer = connection
        try:
            nickname = await authorize(reader, writer, token)
        except InvalidToken:
            messagebox.showinfo('Неверный токен',
                                'Проверьте правильность ввода токена')
            return
        status_queue.put_nowait(NicknameReceived(nickname))

        send_coroutine = send_server_msgs(writer, sending_queue, watchdog_queue)

        await asyncio.gather(draw_interface_coroutine, read_coroutine,
                             save_coroutine, send_coroutine, connection_logging_coroutine)


if __name__ == '__main__':
    asyncio.run(main())
