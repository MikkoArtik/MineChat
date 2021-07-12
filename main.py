import asyncio
import logging


async def save_messages(host: str, port: int, output_file: str,
                        messages_count=10):
    reader, writer = await asyncio.open_connection(host, port)
    with open(output_file, 'w') as f:
        for i in range(messages_count):
            logging.info(f'Reading message #{i + 1}...')
            message = await reader.readline()
            message = message.decode().rstrip()
            f.write(message+'\n')
            logging.info(f'Message text: {message}')
    writer.close()
    await writer.wait_closed()


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    asyncio.run(save_messages('minechat.dvmn.org', 5000, 'messages.txt', 2))
