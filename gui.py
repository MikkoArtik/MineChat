from datetime import datetime
import asyncio

import dotenv
from argparse import ArgumentParser

import interface


DEFAULT_HOST = 'minechat.dvmn.org'
DEFAULT_PORT = 5050
EMPTY_VALUE = -9999


async def generate_msgs(queue: asyncio.Queue):
    while True:
        msg_text = f'Ping {int(datetime.now().timestamp())}'
        queue.put_nowait(msg_text)
        await asyncio.sleep(2)


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

    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_queue = asyncio.Queue()

    create_msgs_coroutine = generate_msgs(messages_queue)
    draw_interface_coroutine = interface.draw(messages_queue, sending_queue, status_queue)
    await asyncio.gather(create_msgs_coroutine, draw_interface_coroutine)


if __name__ == '__main__':
    asyncio.run(main())
