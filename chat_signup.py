import os
import json
import argparse

import asyncio

import dotenv

EMPTY_LINE = '\n'


def change_env_file(hash_value: str):
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.close()
    dotenv.load_dotenv()
    dotenv.set_key('.env', 'TOKEN', hash_value)


async def get_account_hash(host: str, port: int, nickname: str):
    try:
        reader, writer = await asyncio.open_connection(host, port)
    except ConnectionRefusedError:
        return

    await reader.readline()

    writer.write(EMPTY_LINE.encode())
    await writer.drain()

    await reader.readline()

    writer.write(f'{nickname}\n'.encode())
    await writer.drain()

    user_info = await reader.readline()
    user_info = json.loads(user_info.decode())

    writer.close()
    await writer.wait_closed()

    change_env_file(user_info['account_hash'])


if __name__ == '__main__':
    cli_helper = argparse.ArgumentParser(
        description='Utility for signup in chat')
    cli_helper.add_argument('--host', type=str, help='chat host')
    cli_helper.add_argument('--port', type=int, help='port number')
    cli_helper.add_argument('--nick', type=str, help='your nickname')

    params = cli_helper.parse_args()
    asyncio.run(get_account_hash(params.host, params.port, params.nick))

