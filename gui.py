import asyncio
from datetime import datetime
from asyncio import Queue
from asyncio import StreamWriter
import logging
import os
from enum import Enum
from tkinter import messagebox

import dotenv
from argparse import ArgumentParser

from core import InvalidToken
from core import create_send_connection, create_read_connection
from core import authorize
from core import read_history_msgs, read_msgs, save_msgs, submit_msg
import interface
from interface import NicknameReceived


DEFAULT_HOST = 'minechat.dvmn.org'
READING_PORT, SENDING_PORT = 5000, 5050
MSG_HISTORY_FILE = 'm.txt'


class Notification(Enum):
    NEW_MESSAGE = 'New message in chat'
    SENT_MESSAGE = 'Message was sent'


def format_notification(text_val: Notification) -> str:
    timestamp = int(datetime.now().timestamp())
    return f'[{timestamp}] Connection is alive. {text_val}'


async def read_server_msgs(host: str, port: int, status_queue: Queue,
                           showing_msg_queue: Queue, saving_msg_queue: Queue,
                           connection_status_queue: Queue):
    await read_history_msgs(MSG_HISTORY_FILE, showing_msg_queue)
    async with create_read_connection(host, port, status_queue) as connection:
        reader, _ = connection
        async for msg_text in read_msgs(reader):
            showing_msg_queue.put_nowait(msg_text)
            saving_msg_queue.put_nowait(msg_text)

            notification = format_notification(Notification.NEW_MESSAGE)
            connection_status_queue.put_nowait(notification)


async def send_server_msgs(writer: StreamWriter, queue: asyncio.Queue,
                           connection_status_queue: Queue):
    while True:
        msg_text = await queue.get()
        logging.debug(f'Пользователь написал: {msg_text}')
        await submit_msg(writer, msg_text)

        notification = format_notification(Notification.SENT_MESSAGE)
        connection_status_queue.put_nowait(notification)


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

    read_coroutine = read_server_msgs(host, read_port, status_queue,
                                      showing_msg_queue, saving_msgs_queue,
                                      watchdog_queue)

    save_coroutine = save_msgs(MSG_HISTORY_FILE, saving_msgs_queue)

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
