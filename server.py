

import socket

import threading

import json



HOST = "0.0.0.0"

PORT = 5050

ENC = "utf-8"



clients_lock = threading.Lock()

clients = {}  # conn -> {"username": str, "addr": (ip,port)}



def send_json(conn, payload: dict):

    data = (json.dumps(payload) + "\n").encode(ENC)

    conn.sendall(data)



def broadcast(payload: dict, exclude=None):

    with clients_lock:

        dead = []

        for c in clients:

            if c is exclude:

                continue

            try:

                send_json(c, payload)

            except OSError:

                dead.append(c)

        for d in dead:

            try:

                d.close()

            except:

                pass

            clients.pop(d, None)



def user_list():

    with clients_lock:

        return [info["username"] for info in clients.values()]



def announce_users():

    broadcast({"type": "users", "users": user_list()})



def handle_client(conn, addr):

    try:

        # First message must be join with username

        line = conn.makefile("r", encoding=ENC).readline()

        if not line:

            conn.close()

            return

        msg = json.loads(line)

        if msg.get("type") != "join" or not msg.get("username"):

            conn.close()

            return



        username = msg["username"][:20]

        with clients_lock:

            clients[conn] = {"username": username, "addr": addr}



        # Welcome + notify others

        send_json(conn, {"type": "system", "text": f"Welcome {username}! 🎉"})

        broadcast({"type": "system", "text": f"{username} joined the room."}, exclude=conn)

        announce_users()



        # Chat loop

        f = conn.makefile("r", encoding=ENC)

        for line in f:

            try:

                data = json.loads(line.strip())

            except json.JSONDecodeError:

                continue

            if data.get("type") == "chat":

                text = str(data.get("text", ""))[:1000]

                if text.strip():

                    broadcast({"type": "chat", "from": username, "text": text})

            elif data.get("type") == "ping":

                send_json(conn, {"type": "pong"})

        # EOF -> disconnect

    except Exception:

        pass

    finally:

        with clients_lock:

            info = clients.pop(conn, None)

        try:

            conn.close()

        except:

            pass

        if info:

            broadcast({"type": "system", "text": f"{info['username']} left the room."})

            announce_users()



def main():

    print(f"Server listening on {HOST}:{PORT}")

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    s.bind((HOST, PORT))

    s.listen(50)

    try:

        while True:

            conn, addr = s.accept()

            t = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)

            t.start()

    except KeyboardInterrupt:

        print("\nShutting down...")

    finally:

        s.close()



if __name__ == "__main__":

    main() 



client.py



import socket

import threading

import json

import queue

import time

import customtkinter as ctk

from tkinter import messagebox



APP_TITLE = "Fuzzu Chat – Tkinter (Modern)"

ENC = "utf-8"



class ChatClient:

    def __init__(self):

        self.sock = None

        self.reader_thread = None

        self.incoming = queue.Queue()

        self.connected = False



    def connect(self, host, port, username):

        if self.connected:

            return True

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        self.sock.connect((host, port))

        self.file = self.sock.makefile("r", encoding=ENC)

        # join handshake

        self.send({"type": "join", "username": username})

        self.connected = True

        self.reader_thread = threading.Thread(target=self._reader_loop, daemon=True)

        self.reader_thread.start()

        return True



    def _reader_loop(self):

        try:

            for line in self.file:

                try:

                    data = json.loads(line.strip())

                except json.JSONDecodeError:

                    continue

                self.incoming.put(data)

        except OSError:

            pass

        finally:

            self.connected = False

            self.incoming.put({"type": "system", "text": "🔌 Disconnected."})



    def send(self, payload):

        if not self.connected:

            return

        try:

            msg = (json.dumps(payload) + "\n").encode(ENC)

            self.sock.sendall(msg)

        except OSError:

            pass



    def close(self):

        try:

            if self.sock:

                self.sock.close()

        except:

            pass

        self.connected = False



class ModernChatGUI(ctk.CTk):

    def __init__(self):

        super().__init__()

        ctk.set_appearance_mode("dark")      # "light" | "dark" | "system"

        ctk.set_default_color_theme("blue")  # built-in theme accents

        self.title(APP_TITLE)

        self.geometry("980x640")

        self.minsize(860, 560)



        self.client = ChatClient()

        self.username = ctk.StringVar(value="")

        self.host = ctk.StringVar(value="127.0.0.1")

        self.port = ctk.IntVar(value=5050)



        # Root grid

        self.grid_rowconfigure(0, weight=1)

        self.grid_columnconfigure(0, weight=1)



        # ---- Frames ----

        self.login_frame = self.build_login_frame()

        self.chat_frame = self.build_chat_frame()



        self.login_frame.grid(row=0, column=0, sticky="nsew")

        self.chat_frame.grid_forget()



        # Poll network queue

        self.after(50, self.process_incoming)



    # ------------- UI: Login -------------

    def build_login_frame(self):

        frame = ctk.CTkFrame(self, corner_radius=24)

        frame.grid_rowconfigure(0, weight=1)

        frame.grid_rowconfigure(1, weight=0)

        frame.grid_rowconfigure(2, weight=0)

        frame.grid_rowconfigure(3, weight=0)

        frame.grid_rowconfigure(4, weight=1)

        frame.grid_columnconfigure(0, weight=1)



        title = ctk.CTkLabel(frame, text="💬 Fuzzu Chat", font=("Segoe UI", 28, "bold"))

        subtitle = ctk.CTkLabel(frame, text="Real-Time Chat • Tkinter + Sockets",

                                font=("Segoe UI", 14))



        card = ctk.CTkFrame(frame, corner_radius=24)

        for r in range(4):

            card.grid_rowconfigure(r, weight=0)

        card.grid_columnconfigure(1, weight=1)



        u_lbl = ctk.CTkLabel(card, text="Username")

        u_ent = ctk.CTkEntry(card, textvariable=self.username, placeholder_text="e.g., FuzzuDev")



        h_lbl = ctk.CTkLabel(card, text="Server Host")

        h_ent = ctk.CTkEntry(card, textvariable=self.host, placeholder_text="127.0.0.1")



        p_lbl = ctk.CTkLabel(card, text="Port")

        p_ent = ctk.CTkEntry(card, textvariable=self.port)



        btn = ctk.CTkButton(card, text="Join Chat ▶", height=42, command=self.on_connect)



        footer = ctk.CTkLabel(frame, text="Tip: Run server.py first • Clean UI • Minimal latency",

                              font=("Segoe UI", 12))



        # Layout

        title.grid(row=0, column=0, pady=(40, 6), padx=24)

        subtitle.grid(row=1, column=0, pady=(0, 24), padx=24)

        card.grid(row=2, column=0, padx=28, pady=12, sticky="n")

        u_lbl.grid(row=0, column=0, padx=(16, 12), pady=12, sticky="e")

        u_ent.grid(row=0, column=1, padx=(0, 16), pady=12, sticky="ew")

        h_lbl.grid(row=1, column=0, padx=(16, 12), pady=12, sticky="e")

        h_ent.grid(row=1, column=1, padx=(0, 16), pady=12, sticky="ew")

        p_lbl.grid(row=2, column=0, padx=(16, 12), pady=12, sticky="e")

        p_ent.grid(row=2, column=1, padx=(0, 16), pady=12, sticky="ew")

        btn.grid(row=3, column=0, columnspan=2, padx=16, pady=(12, 16), sticky="ew")

        footer.grid(row=3, column=0, pady=(8, 24))



        return frame



    # ------------- UI: Chat -------------

    def build_chat_frame(self):

        frame = ctk.CTkFrame(self, corner_radius=0)

        frame.grid_rowconfigure(1, weight=1)

        frame.grid_columnconfigure(0, weight=3)

        frame.grid_columnconfigure(1, weight=1)



        # Header

        header = ctk.CTkFrame(frame, corner_radius=0)

        title = ctk.CTkLabel(header, text="Room: #general", font=("Segoe UI", 18, "bold"))

        self.status_lbl = ctk.CTkLabel(header, text="● Offline", text_color="#f87171")

        leave_btn = ctk.CTkButton(header, text="⏏ Leave", width=80, command=self.on_disconnect)



        header.grid(row=0, column=0, columnspan=2, sticky="ew")

        header.grid_columnconfigure(0, weight=1)

        title.grid(row=0, column=0, padx=16, pady=12, sticky="w")

        self.status_lbl.grid(row=0, column=1, padx=8, pady=12, sticky="e")

        leave_btn.grid(row=0, column=2, padx=16, pady=12, sticky="e")



        # Chat area

        chat_card = ctk.CTkFrame(frame, corner_radius=20)

        chat_card.grid_rowconfigure(0, weight=1)

        chat_card.grid_columnconfigure(0, weight=1)



        self.chat_box = ctk.CTkTextbox(chat_card, wrap="word", activate_scrollbars=True)

        self.chat_box.configure(state="disabled")



        chat_card.grid(row=1, column=0, padx=(16, 8), pady=(8, 8), sticky="nsew")

        self.chat_box.grid(row=0, column=0, padx=12, pady=12, sticky="nsew")



        # Sidebar: users

        users_card = ctk.CTkFrame(frame, corner_radius=20)

        users_card.grid_rowconfigure(1, weight=1)

        users_title = ctk.CTkLabel(users_card, text="👥 Online", font=("Segoe UI", 14, "bold"))

        self.users_list = ctk.CTkTextbox(users_card, height=200)

        self.users_list.configure(state="disabled")

        users_title.grid(row=0, column=0, padx=12, pady=(12, 6), sticky="w")

        self.users_list.grid(row=1, column=0, padx=12, pady=(0, 12), sticky="nsew")



        users_card.grid(row=1, column=1, padx=(8, 16), pady=(8, 8), sticky="nsew")



        # Composer

        composer = ctk.CTkFrame(frame, corner_radius=20)

        composer.grid_columnconfigure(0, weight=1)



        self.msg_entry = ctk.CTkEntry(composer, placeholder_text="Type a message… (Enter to send)")

        send_btn = ctk.CTkButton(composer, text="Send ➤", width=100, command=self.on_send)

        emoji_btn = ctk.CTkButton(composer, text="😊", width=42, command=self.insert_emoji)



        self.msg_entry.bind("<Return>", lambda e: self.on_send())



        self.msg_entry.grid(row=0, column=0, padx=(12, 8), pady=12, sticky="ew")

        emoji_btn.grid(row=0, column=1, padx=(0, 8), pady=12)

        send_btn.grid(row=0, column=2, padx=(0, 12), pady=12)



        composer.grid(row=2, column=0, columnspan=2, padx=16, pady=(0, 16), sticky="ew")



        return frame



    # ------------- Actions -------------

    def on_connect(self):

        username = self.username.get().strip()

        host = self.host.get().strip()

        try:

            port = int(self.port.get())

        except ValueError:

            messagebox.showerror("Invalid Port", "Port must be a number.")

            return



        if not username:

            messagebox.showerror("Username Required", "Please enter a username.")

            return

        try:

            self.client.connect(host, port, username)

        except Exception as e:

            messagebox.showerror("Connection Failed", f"Could not connect:\n{e}")

            return



        self.login_frame.grid_forget()

        self.chat_frame.grid(row=0, column=0, sticky="nsew")

        self.set_status(True)



    def on_disconnect(self):

        self.client.close()

        self.set_status(False)

        self.chat_frame.grid_forget()

        self.login_frame.grid(row=0, column=0, sticky="nsew")



    def on_send(self):

        text = self.msg_entry.get().strip()

        if not text:

            return

        self.client.send({"type": "chat", "text": text})

        self.msg_entry.delete(0, "end")



    def insert_emoji(self):

        # simple quick emoji wheel

        choices = ["😀", "🥳", "🔥", "🚀", "💡", "👍", "✨", "💬"]

        current = self.msg_entry.get()

        self.msg_entry.delete(0, "end")

        self.msg_entry.insert(0, current + " " + choices[int(time.time()) % len(choices)])



    def set_status(self, online: bool):

        if online:

            self.status_lbl.configure(text="● Online", text_color="#34d399")

        else:

            self.status_lbl.configure(text="● Offline", text_color="#f87171")



    # ------------- Networking -> UI -------------

    def process_incoming(self):

        try:

            while True:

                data = self.client.incoming.get_nowait()

                self.handle_message(data)

        except queue.Empty:

            pass

        self.after(50, self.process_incoming)



    def handle_message(self, data: dict):

        t = data.get("type")

        if t == "chat":

            self.append_chat(f"{data.get('from', 'Someone')}: {data.get('text','')}")

        elif t == "system":

            self.append_chat(f"[{data.get('text','')}]")

        elif t == "users":

            self.update_users(data.get("users", []))



    def append_chat(self, line: str):

        self.chat_box.configure(state="normal")

        self.chat_box.insert("end", line + "\n")

        self.chat_box.see("end")

        self.chat_box.configure(state="disabled")



    def update_users(self, users):

        self.users_list.configure(state="normal")

        self.users_list.delete("1.0", "end")

        for u in users:

            self.users_list.insert("end", f"• {u}\n")

        self.users_list.configure(state="disabled")



if __name__ == "__main__":

    app = ModernChatGUI()


    app.mainloop() 
