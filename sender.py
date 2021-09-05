import logging
import os
import argparse
import asyncio

import dotenv

from core import create_connection, register, authorize, submit_message


DEFAULT_HOST = 'minechat.dvmn.org'
DEFAULT_PORT = 5050


async def main():
    parser = argparse.ArgumentParser(
        description='Utility for sending messages to server')
    parser.add_argument('--default', type=bool, choices=[True, False],
                        help='Default host and port')
    parser.add_argument('--host', type=str, help='Host address')
    parser.add_argument('--port', type=int, help='Host port')
    parser.add_argument('--token', type=str, help='User token')
    parser.add_argument('--nick', type=str, help='New user nickname')
    parser.add_argument('--debug', type=bool, choices=[True, False],
                        help='Turn on/off debug messages')
    parser.add_argument('message', type=str, help='Message text')

    arguments = parser.parse_args()
    if arguments.debug:
        logging.basicConfig(level=logging.DEBUG)

    if arguments.default:
        host, port = DEFAULT_HOST, DEFAULT_PORT
    else:
        if not arguments.host or not arguments.port:
            raise Exception('Host address and/or port is not exist')
        else:
            host, port = arguments.host, arguments.port

    async with create_connection(host, port) as connection:
        reader, writer = connection
        if arguments.nick:
            token = await register(reader, writer, arguments.nick)
            dotenv.set_key('.env', 'TOKEN', token)
        else:
            if arguments.token:
                token = arguments.token
            else:
                dotenv.load_dotenv()
                token = os.getenv('TOKEN')
            await authorize(reader, writer, token)

        if not arguments.message:
            logging.error('Empty message text')
            return
        await submit_message(writer, arguments.message)


if __name__ == '__main__':
    asyncio.run(main())
