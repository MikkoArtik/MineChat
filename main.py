import os
import argparse
import asyncio

import dotenv

from core import create_connection, register, authorization, submit_message


DEFAULT_HOST = 'minechat.dvmn.org'
DEFAULT_WRITE_PORT = 5050


async def main():
    parser = argparse.ArgumentParser(
        description='Utility for sending messages to server')
    parser.add_argument('--default', type=bool,
                        help='Default server host and port')
    parser.add_argument('--host', type=str, help='Server address')
    parser.add_argument('--writeport', type=int,
                        help='Server port for message sending')
    parser.add_argument('--token', type=str, help='User token')
    parser.add_argument('--nick', type=str, help='New user nickname')
    parser.add_argument('message', type=str, help='Message text')

    arguments = parser.parse_args()

    if arguments.default:
        host = DEFAULT_HOST
        port = DEFAULT_WRITE_PORT
    else:
        host = arguments.host
        port = arguments.writeport

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
            await authorization(reader, writer, token)

        await submit_message(writer, arguments.message)


if __name__ == '__main__':
    asyncio.run(main())
