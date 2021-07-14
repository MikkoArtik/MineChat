import os
import asyncio

import dotenv


async def send_message(host: str, port: int, hash_key: str,
                       message_text: str):
    try:
        reader, writer = await asyncio.open_connection(host=host, port=port)
    except ConnectionRefusedError:
        print('Invalid host address')
        return

    hash_key += '\n'
    writer.write(hash_key.encode())
    await writer.drain()

    message_text += '\n\n'
    writer.write(message_text.encode())
    await writer.drain()

    writer.close()
    await writer.wait_closed()


if __name__ == '__main__':
    dotenv.load_dotenv()

    host = os.getenv('HOST')
    port = int(os.getenv('WRITE_PORT'))
    token = os.getenv('TOKEN')

    asyncio.run(send_message(host, port, token, 'first message'))
