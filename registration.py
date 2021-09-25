import asyncio
import socket

from tkinter import END
from tkinter import Tk, Label, Entry, Button, messagebox, TclError

import anyio

import dotenv

from core import create_connection
from core import register


DEFAULT_HOST = 'minechat.dvmn.org'
SENDING_PORT = 5050
TIMEOUT_SEC = 1
ENV_FILE = '.env'
TOKEN_KEY = 'TOKEN'


class TkAppClosed(Exception):
    pass


class RegistrationInterface:
    def __init__(self):
        self.__nickname = ''
        self.interface_root = self.create_interface()

    @property
    def nickname(self) -> str:
        return self.__nickname

    def set_current_nickname(self, text_field: Entry):
        nickname = text_field.get()
        if not nickname:
            messagebox.showerror('Incorrect nickname',
                                 'Length of nickname must be more than zero')
        else:
            self.__nickname = nickname
        text_field.delete(0, END)

    @staticmethod
    async def update_frame(root: Tk, time_interval=0.1):
        while True:
            try:
                root.update()
            except TclError:
                raise TkAppClosed
            await asyncio.sleep(time_interval)

    def create_interface(self):
        root = Tk()
        root.title('Chat registration')

        Label(text='Your nickname').grid(row=0, column=0)

        nickname_field = Entry(width=50)
        nickname_field.grid(row=0, column=1, columnspan=2)

        apply_button = Button(text='Registration')
        apply_button.grid(row=1, column=1)
        apply_button['command'] = lambda: self.set_current_nickname(nickname_field)
        return root

    async def get_token(self) -> str:
        async with create_connection(DEFAULT_HOST, SENDING_PORT) as conn_ctx:
            reader, writer = conn_ctx
            token = await register(reader, writer, self.nickname)
            return token

    async def register_in_chat(self):
        while True:
            nickname = self.nickname
            if nickname:
                token = await self.get_token()
                dotenv.set_key(ENV_FILE, TOKEN_KEY, token)
                messagebox.showinfo('token info', 'Your token was saved')
                self.__nickname = ''
            await asyncio.sleep(TIMEOUT_SEC)

    async def run(self):
        try:
            async with anyio.create_task_group() as task_ctx:
                task_ctx.start_soon(self.register_in_chat)
                task_ctx.start_soon(self.update_frame, self.interface_root)
        except socket.gaierror:
            messagebox.showerror('Connection problem',
                                 'No internet connection')
        except TkAppClosed:
            pass


if __name__ == '__main__':
    gui = RegistrationInterface()
    try:
        asyncio.run(gui.run())
    except KeyboardInterrupt:
        pass
