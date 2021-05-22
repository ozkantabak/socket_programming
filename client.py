from tkinter import *
import tkinter.messagebox as mb
from xtra_widgets import *
import threading
import socket
import select
import errno
import sys
import random


HEADER_LENGTH = 10

IP = "127.0.0.1"
PORT = 1234

my_username = None
username = None
username_header = None
client_socket = None


class ChatApp(Tk):

    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.title("LAN Chat")
        container = Frame(self)

        container.pack(side="top", fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        for F in (ConnectionPage, ChatPage):
            frame = F(container, self)

            self.frames[F] = frame

            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(ConnectionPage)

    def show_frame(self, cont):
        frame = self.frames[cont]
        if hasattr(frame, "geometry"):  self.geometry(frame.geometry)
        if hasattr(frame, "on_enter"): frame.on_enter()
        frame.tkraise()


class ConnectionPage(Frame):

    geometry = "245x100"

    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.controller = controller

        self.username_entry = Entry(self)
        self.username_entry.insert(0, str(random.randrange(0, 9999999)))
        self.ip_entry = Entry(self)
        self.ip_entry.insert(0, "127.0.0.1")
        self.port_entry = Entry(self)
        self.port_entry.insert(0, "5000")
        self.connect_button = Button(self, text="Connect", command=self.connect, bd=3)

        Label(self, text="Username: ").grid(row=0, column=0, sticky='w')
        self.username_entry.grid(row=0, column=1, sticky='ew')
        Label(self, text="IP: ").grid(row=1, column=0, sticky='w')
        self.ip_entry.grid(row=1, column=1, sticky='ew')
        Label(self, text="Port: ").grid(row=2, column=0, sticky='w')
        self.port_entry.grid(row=2, column=1, sticky='ew')
        self.connect_button.grid(row=3, column=0, columnspan=2, sticky='ew')

    def connect(self):
        global IP, PORT, client_socket, my_username, username, username_header

        try:
            IP = self.ip_entry.get()
            PORT = int(self.port_entry.get())

            client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            client_socket.connect((IP, PORT))
            client_socket.setblocking(False)

            my_username = self.username_entry.get()
            username = my_username.encode('utf-8')
            username_header = f"{len(username):<{HEADER_LENGTH}}".encode('utf-8')
            client_socket.send(username_header + username)

            self.controller.show_frame(ChatPage)
        except ConnectionRefusedError:
            mb.showerror("Connection Error", "ERROR: Connection Refused!\n\nTIP: Check if the IP address and port are "
                                             "correct.")


class ChatPage(Frame):

    geometry = "350x425"

    def on_enter(self):
        self.check_thread.start()

    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.chat_box = ScrollBox(self, width=40, height=20)
        self.txtinvar = StringVar()
        self.text_input_entry = Entry(self, textvariable=self.txtinvar)
        self.text_input_entry.bind("<Return>", lambda _: self.send_msg())
        self.send_button = Button(self, text="Send", command=self.send_msg)

        self.chat_box.grid(row=0, column=0, columnspan=2, sticky='nsew')
        self.text_input_entry.grid(row=1, column=0, sticky='ew')
        self.send_button.grid(row=1, column=1, sticky='ew')
        self.check_thread = threading.Thread(target=self.check_messages, daemon=True)

    def send_msg(self):
        global my_username
        txt_input = str(self.txtinvar.get())
        if txt_input:
            self.chat_box.insert(END, f'<{my_username}>: {txt_input}')
            message = txt_input.encode('utf-8')
            message_header = f"{len(message):<{HEADER_LENGTH}}".encode('utf-8')
            client_socket.send(message_header + message)
        self.text_input_entry.delete(0, END)

    def check_messages(self):
        global client_socket, username_header
        while True:
            try:
                while True:
                    username_header = client_socket.recv(HEADER_LENGTH)

                    if not len(username_header):
                        print('Connection closed by the server')
                        sys.exit()

                    username_length = int(username_header.decode('utf-8').strip())

                    username = client_socket.recv(username_length).decode('utf-8')

                    message_header = client_socket.recv(HEADER_LENGTH)
                    message_length = int(message_header.decode('utf-8').strip())
                    message = client_socket.recv(message_length).decode('utf-8')

                    # Print message
                    self.chat_box.insert(END, f'<{username}>: {message}')

            except IOError as e:
                if e.errno != errno.EAGAIN and e.errno != errno.EWOULDBLOCK:
                    mb.showerror('Reading Error', 'Reading error: {}'.format(str(e)))
                    sys.exit()
                continue

            except Exception as e:
                mb.showerror('Reading Error', 'Reading error: {}'.format(str(e)))
                sys.exit()


if __name__ == "__main__":
    a = ChatApp()
    a.mainloop()
