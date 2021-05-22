import socket
import select
import threading
from tkinter import *
import tkinter.messagebox as mb
from xtra_widgets import *


HEADER_LENGTH = 10
IP = "127.0.0.1"
PORT = 5000
SERVER_USRNAME = "SERVER"
SERVER_HEADER = f"{len(SERVER_USRNAME):<{HEADER_LENGTH}}"
server_socket = None
sockets_list = None
clients = None
client_username_list = []


class ChatServerApp(Tk):

    def __init__(self, *args, **kwargs):
        Tk.__init__(self, *args, **kwargs)
        self.title("LAN Chat Server")
        container = Frame(self)

        container.pack(side="top", fill="both", expand=True)

        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)

        self.frames = {}

        for F in (CreationPage, ManagerFrame):
            frame = F(container, self)

            self.frames[F] = frame

            frame.grid(row=0, column=0, sticky="nsew")

        self.show_frame(CreationPage)

    def show_frame(self, cont):
        frame = self.frames[cont]
        if hasattr(frame, "geometry"):  self.geometry(frame.geometry)
        if hasattr(frame, "on_enter"): frame.on_enter()
        frame.tkraise()


class CreationPage(Frame):

    geometry = "205x80"

    def __init__(self, parent, controller):
        Frame.__init__(self, parent)
        self.controller = controller

        self.ip_var = StringVar()
        self.ip_entry = Entry(self, textvariable=self.ip_var)
        self.ip_var.set("127.0.0.1")
        self.port_var = StringVar()
        self.port_entry = Entry(self, textvariable=self.port_var)
        self.port_var.set("5000")
        self.start_button = Button(self, text="Start Server!", command=self.start)

        Label(self, text="IP: ").grid(row=0, column=0, sticky='w')
        self.ip_entry.grid(row=0, column=1, sticky='ew')
        Label(self, text="Port: ").grid(row=1, column=0, sticky='w')
        self.port_entry.grid(row=1, column=1, sticky='ew')
        self.start_button.grid(row=3, column=0, columnspan=2, sticky='ew')

    def start(self):
        global server_socket, sockets_list, clients, IP, PORT

        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            IP = self.ip_var.get()
            PORT = int(self.port_var.get())
            server_socket.bind((IP, PORT))
            server_socket.listen()

            sockets_list = [server_socket]

            clients = {}
        except Exception as e:
            mb.showerror("Server not created", f"Error while creating server:\n{str(e)}")
        else:
            self.controller.show_frame(ManagerFrame)
            mb.showinfo("Server Created", "The server was created successfully!")


class ManagerFrame(Frame):

    geometry = "650x660"

    def on_enter(self):
        self.server_runner_thread.start()

    def __init__(self, parent, controller):
        Frame.__init__(self, parent)

        self.server_runner_thread = threading.Thread(target=self.run_server, daemon=True)

        self.evnt_box = ScrollBox(self, width=50, height=35)
        self.info_frame = LabelFrame(self, text="Server Info")
        self.clients_box = ScrollBox(self.info_frame, height=30)

        self.evnt_box.grid(row=0, column=0, sticky='nsew')
        self.info_frame.grid(row=0, column=1, sticky='nsew')
        Label(self.info_frame, text="Connected Clients: ", font=("Arial", 11, "bold")).grid(row=0, column=0, sticky='w')
        self.connected_clients_var = StringVar()
        self.connected_clients_var.set("0")
        Label(self.info_frame, textvariable=self.connected_clients_var, font=("Arial", 11, "italic")).grid(row=0, column=1,
                                                                                                           sticky='e')
        self.clients_box.grid(row=1, column=0, columnspan=2, sticky='nsew')
        Label(self.info_frame, text="IP: ", font=("Arial", 11, "bold")).grid(row=2, column=0, sticky='w')
        Label(self.info_frame, text=IP, font=("Arial", 11, "italic")).grid(row=2, column=1, sticky='e')
        Label(self.info_frame, text="Port: ", font=("Arial", 11, "bold")).grid(row=3, column=0, sticky='w')
        Label(self.info_frame, text=PORT, font=("Arial", 11, "italic")).grid(row=3, column=1, sticky='e')

    def run_server(self):
        global server_socket, sockets_list, clients, client_username_list
        while True:
            read_sockets, _, exception_sockets = select.select(sockets_list, [], sockets_list)

            for notified_socket in read_sockets:
                if notified_socket == server_socket:
                    client_socket, client_address = server_socket.accept()
                    user = self._receive_message(client_socket)
                    if user is False:
                        continue
                    sockets_list.append(client_socket)

                    clients[client_socket] = user

                    nusrn = user['data'].decode('utf-8')
                    client_username_list.append(nusrn)
                    self.clients_box.insert(END, nusrn)
                    self.evnt_box.insert(END, f"Accepted new connection from {client_address[0]}:{client_address[1]} "
                                              f"username:{nusrn}")
                    msg = f"{user['data'].decode('utf-8')} has entered the room!"''
                    self.evnt_box.insert(END, f"<{SERVER_USRNAME}> {msg}")
                    self.connected_clients_var.set(int(self.connected_clients_var.get()) + 1)
                    for client_socket in clients:
                        if client_socket != notified_socket:
                            client_socket.send(
                                (SERVER_HEADER + SERVER_USRNAME + f'{len(msg) + 1:<{HEADER_LENGTH}}' + f'{msg}').encode(
                                    'utf-8'))

                else:
                    message = self._receive_message(notified_socket)
                    if message is False:
                        usr = clients[notified_socket]['data'].decode('utf-8')
                        self.evnt_box.insert(END, f"<{SERVER_USRNAME}> {usr} has disconnected!")
                        self.connected_clients_var.set(int(self.connected_clients_var.get()) - 1)
                        self.clients_box.list_box.delete(client_username_list.index(usr))
                        client_username_list.remove(usr)
                        for client_socket in clients:
                            if client_socket != notified_socket:
                                msg = f'{usr} has disconnected!'
                                client_socket.send((SERVER_HEADER + SERVER_USRNAME + f'{len(msg) + 1:<{HEADER_LENGTH}}'
                                                    + f'{msg}').encode('utf-8'))
                        sockets_list.remove(notified_socket)
                        del clients[notified_socket]
                        continue
                    user = clients[notified_socket]
                    self.evnt_box.insert(END, f"<{user['data'].decode('utf-8')}>: {message['data'].decode('utf-8')}")

                    for client_socket in clients:
                        if client_socket != notified_socket:
                            client_socket.send(user['header'] + user['data'] + message['header'] + message['data'])

                for notified_socket in exception_sockets:
                    sockets_list.remove(notified_socket)
                    del clients[notified_socket]

    @staticmethod
    def _receive_message(client_socket):
        try:
            message_header = client_socket.recv(HEADER_LENGTH)

            if not len(message_header):
                return False

            message_length = int(message_header.decode('utf-8').strip())
            return {"header": message_header, "data": client_socket.recv(message_length)}
        except:
            return False


if __name__ == "__main__":
    a = ChatServerApp()
    a.mainloop()
