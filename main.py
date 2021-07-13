from datetime import datetime
import logging

import asyncio
import aiofiles


def message_formatting(message: str) -> str:
    current_datetime = datetime.now().strftime('%d.%m.%y %H:%M')
    return f'[{current_datetime}] {message}'


async def save_messages(host: str, port: int, output_file: str):
    try:
        reader, writer = await asyncio.open_connection(host, port)
    except ConnectionRefusedError:
        logging.error('Host is unreachable')
        return

    async with aiofiles.open(output_file, 'a') as file_handle:
        message = message_formatting('Установлено соединение')
        logging.debug(message)
        await file_handle.write(message+'\n')

        while True:
            message = await reader.readline()
            try:
                message = message.decode().rstrip()
            except UnicodeDecodeError:
                break

            message = message_formatting(message)
            await file_handle.write(message + '\n')
            await file_handle.flush()
            logging.debug(message)
    writer.close()
    await writer.wait_closed()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(save_messages('minechat.dvmn.org', 5000, 'messages.txt'))
