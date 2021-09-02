import logging
import os
import argparse
import asyncio

import dotenv

from core import create_connection, register, authorization, \
    submit_message, listen_server


DEFAULT_HOST = 'minechat.dvmn.org'
DEFAULT_LISTEN_PORT = 5000
DEFAULT_SENDING_PORT = 5050

SENDING_MODE = 'send'
READING_MODE = 'listen'


async def main():
    parser = argparse.ArgumentParser(
        description='Utility for reading/sending messages from/to server')
    parser.add_argument('mode', type=str,
                        help='Mode: listen or send messages')
    parser.add_argument('--debug', type=bool, help='Turn on debug messages')
    parser.add_argument('--default', type=bool, help='Default host and port')
    parser.add_argument('--host', type=str, help='Server address')
    parser.add_argument('--port', type=int, help='Server port')
    parser.add_argument('--token', type=str, help='User token')
    parser.add_argument('--nick', type=str, help='New user nickname')
    parser.add_argument('--message', type=str, help='Message text')
    parser.add_argument('--outfile', type=str, help='Message saving file')

    arguments = parser.parse_args()
    if arguments.debug:
        logging.basicConfig(level=logging.DEBUG)
    if arguments.default:
        host = DEFAULT_HOST
    else:
        host = arguments.host

    if arguments.mode == READING_MODE and arguments.default:
        port = DEFAULT_LISTEN_PORT
    elif arguments.mode == SENDING_MODE and arguments.default:
        port = DEFAULT_SENDING_PORT
    else:
        port = arguments.port

    async with create_connection(host, port) as connection:
        reader, writer = connection
        if arguments.mode == SENDING_MODE:
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

            if not arguments.message:
                logging.error('Empty message text')
                return
            await submit_message(writer, arguments.message)
        elif arguments.mode == READING_MODE:
            if not arguments.outfile:
                logging.error('Output file is not specified')
                return
            await listen_server(reader, arguments.outfile)
        else:
            logging.error('Unexpected message option')
            return


if __name__ == '__main__':
    asyncio.run(main())
