import os
import logging
import json
import asyncio

import dotenv


MAX_MESSAGE_BYTE_SIZE = 1024


async def send_message(host: str, port: int, hash_key: str,
                       message_text: str):
    try:
        reader, writer = await asyncio.open_connection(host=host, port=port)
    except ConnectionRefusedError:
        logging.error('Connection refused')
        return

    logging.debug('Соединение установлено')

    server_message = await reader.read(MAX_MESSAGE_BYTE_SIZE)
    server_message = server_message.decode().rstrip()
    logging.debug(f'Server: {server_message}')

    logging.debug(f'Client: {hash_key}')
    hash_key += '\n'
    writer.write(hash_key.encode())
    await writer.drain()

    hash_info = await reader.readline()
    hash_info = hash_info.decode().rstrip()
    if json.loads(hash_info) is None:
        logging.error('Server: Неверный токен. '
                      'Проверьте его или зарегистрируйте заново')
        writer.close()
        await writer.wait_closed()
        return
    else:
        logging.debug(f'Server: {hash_info}')

    server_message = await reader.read(MAX_MESSAGE_BYTE_SIZE)
    server_message = server_message.decode().rstrip()
    logging.debug(f'Server: {server_message}')

    logging.debug(f'Client: {message_text}')
    message_text += '\n\n'
    writer.write(message_text.encode())
    await writer.drain()

    server_message = await reader.read(MAX_MESSAGE_BYTE_SIZE)
    server_message = server_message.decode().rstrip()
    logging.debug(f'Server: {server_message}')

    writer.close()
    await writer.wait_closed()


if __name__ == '__main__':
    dotenv.load_dotenv()

    host = os.getenv('HOST')
    port = int(os.getenv('WRITE_PORT'))
    token = os.getenv('TOKEN')

    logging.basicConfig(level=logging.DEBUG)

    asyncio.run(send_message(host, port, token, 'first message'))
