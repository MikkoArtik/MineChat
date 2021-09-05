import argparse
import asyncio
import logging

from core import create_connection
from core import listen_server


DEFAULT_HOST = 'minechat.dvmn.org'
DEFAULT_PORT = 5000


async def main():
    parser = argparse.ArgumentParser(
        description='Utility for reading messages from server')
    parser.add_argument('--default', type=bool, choices=[True, False],
                        help='Default host address and port number')
    parser.add_argument('--host', type=str, help='Host address')
    parser.add_argument('--port', type=int, help='Host port number')
    parser.add_argument('--debug', type=bool, choices=[True, False],
                        help='Turn on/off debug mode')
    parser.add_argument('outfile', type=str,
                        help='Output file path for saving messages history')

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

    output_file = arguments.outfile
    async with create_connection(host, port) as connection:
        reader, _ = connection
        await listen_server(reader, output_file)


if __name__ == '__main__':
    asyncio.run(main())
