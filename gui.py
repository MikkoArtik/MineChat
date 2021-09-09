import asyncio
import interface
from datetime import datetime


async def generate_msgs(queue: asyncio.Queue):
    while True:
        msg_text = f'Ping {int(datetime.now().timestamp())}'
        queue.put_nowait(msg_text)
        await asyncio.sleep(2)


async def main():
    messages_queue = asyncio.Queue()
    sending_queue = asyncio.Queue()
    status_queue = asyncio.Queue()

    create_msgs_coroutine = generate_msgs(messages_queue)
    draw_interface_coroutine = interface.draw(messages_queue, sending_queue, status_queue)
    await asyncio.gather(create_msgs_coroutine, draw_interface_coroutine)


if __name__ == '__main__':
    asyncio.run(main())
