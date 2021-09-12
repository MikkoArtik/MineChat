import asyncio

import dotenv
from argparse import ArgumentParser

from core import read_msgs, save_msgs, send_msgs
import interface


DEFAULT_HOST = 'minechat.dvmn.org'
DEFAULT_PORT = 5000
EMPTY_VALUE = -9999

MSG_HISTORY_FILE = 'm.txt'


async def main():
    parser = ArgumentParser(description='GUI utility for minecraft chatting')
    parser.add_argument('--default', type=bool, choices=[True, False],
                        help='Default connection parameters')
    parser.add_argument('--host', type=str, help='Host address')
    parser.add_argument('--port', type=int, help='Host port')
    parser.add_argument('--token', type=str, help='User token')

    dotenv.load_dotenv('.env')
    arguments = parser.parse_args()

    if arguments.default:
        host, port = DEFAULT_HOST, DEFAULT_PORT
    else:
        if arguments.host and arguments.port:
            host, port = arguments.host, arguments.port
        else:
            raise Exception('Host address and/or port is not exist')

    if arguments.token:
        token = arguments.token
    else:
        token = EMPTY_VALUE

    showing_msg_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_queue = asyncio.Queue()
    history_msg_queue = asyncio.Queue()

    showing_msg_coroutine = read_msgs(host, port, showing_msg_queue,
                                      history_msg_queue, MSG_HISTORY_FILE)
    saving_msg_coroutine = save_msgs(MSG_HISTORY_FILE, history_msg_queue)
    sending_msg_coroutine = send_msgs(host, port, sending_queue)
    draw_interface_coroutine = interface.draw(showing_msg_queue, sending_queue,
                                              status_queue)
    await asyncio.gather(draw_interface_coroutine,
                         showing_msg_coroutine,
                         saving_msg_coroutine,
                         sending_msg_coroutine)


if __name__ == '__main__':
    asyncio.run(main())
