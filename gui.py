import asyncio
import logging
import os
from tkinter import messagebox

import dotenv
from argparse import ArgumentParser

from core import InvalidToken
from core import create_connection, authorize
from core import read_msgs, save_msgs, send_msgs
import interface


DEFAULT_HOST = 'minechat.dvmn.org'
READING_PORT = 5000
SENDING_PORT = 5050
EMPTY_VALUE = -9999

MSG_HISTORY_FILE = 'm.txt'


async def main():
    parser = ArgumentParser(description='GUI utility for minecraft chatting')
    parser.add_argument('--default', type=bool, choices=[True, False],
                        help='Default connection parameters')
    parser.add_argument('--host', type=str, help='Host address')
    parser.add_argument('--read_port', type=int, help='Reading host port')
    parser.add_argument('-send_port', type=int, help='Sending host port')
    parser.add_argument('--token', type=str, help='User token')
    parser.add_argument('--debug', type=bool, help='Turn on debug mode')

    dotenv.load_dotenv('.env')
    arguments = parser.parse_args()

    if arguments.debug:
        logging.basicConfig(level=logging.DEBUG)

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

    async with create_connection(host, SENDING_PORT) as connection:
        reader, writer = connection
        try:
            await authorize(reader, writer, token)
        except InvalidToken:
            messagebox.showinfo('Неверный токен',
                                'Проверьте правильность ввода токена')
            return

        showing_msg_queue = asyncio.Queue()
        sending_queue = asyncio.Queue()
        status_queue = asyncio.Queue()
        history_msg_queue = asyncio.Queue()

        showing_msg_coroutine = read_msgs(host, read_port, showing_msg_queue,
                                          history_msg_queue, MSG_HISTORY_FILE)
        saving_msg_coroutine = save_msgs(MSG_HISTORY_FILE, history_msg_queue)
        sending_msg_coroutine = send_msgs(writer, sending_queue)
        draw_interface_coroutine = interface.draw(
            showing_msg_queue, sending_queue, status_queue)
        await asyncio.gather(draw_interface_coroutine,
                             showing_msg_coroutine,
                             saving_msg_coroutine,
                             sending_msg_coroutine)


if __name__ == '__main__':
    asyncio.run(main())
