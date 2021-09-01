import os
import argparse
import asyncio

import dotenv

from core import get_connection, register, is_authorise, submit_message


DEFAULT_HOST = 'minechat.dvmn.org'
DEFAULT_PORT = 5050


async def main():
    parser = argparse.ArgumentParser(
        description='Utility for sending messages to server')
    parser.add_argument('--default', type=bool, help='Default server host and port')
    parser.add_argument('--host', type=str, help='Server address')
    parser.add_argument('--port', type=int, help='Server port')
    parser.add_argument('--token', type=str, help='User token')
    parser.add_argument('--nick', type=str, help='New user nickname')
    parser.add_argument('message', type=str, help='Message text')

    arguments = parser.parse_args()

    if arguments.default:
        host = DEFAULT_HOST
        port = DEFAULT_PORT
    else:
        host = arguments.host
        port = arguments.port

    connection = await get_connection(host, port)
    if not connection:
        return
    reader, writer = connection

    if arguments.nick:
        token = await register(reader, writer, arguments.nick)
        connection = await get_connection(host, port)
        if not connection:
            return
        reader, writer = connection
    elif arguments.token:
        token = arguments.token
    else:
        dotenv.load_dotenv()
        token = os.getenv('HOST')

    is_auth = await is_authorise(reader, writer, token)
    if is_auth:
        await submit_message(reader, writer, arguments.message)
    writer.close()
    await writer.wait_closed()


if __name__ == '__main__':
    asyncio.run(main())
