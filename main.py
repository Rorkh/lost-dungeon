import socket
import asyncio
from datetime import datetime
import logging

from login import LRform
from commands import Executor

logging.basicConfig(filename='.log', encoding='utf-8', format="[%(asctime)s] %(levelname)s: %(message)s", level=logging.NOTSET)

# Connection Data
host = ""
port = 4000

# Lists For Clients and Their Nicknames
clients = []
nicknames = []

# Sending Messages To All Connected Clients
async def broadcast(nickname, message):
    loop = asyncio.get_event_loop()
    msg = f"[{datetime.now().strftime('%H:%M %d/%m/%Y')}] {nickname}: {message.decode('utf-8')}"
    for client in clients:
        await loop.sock_sendall(client, msg.encode("utf-8"))

async def handle(client, login):
    loop = asyncio.get_event_loop()
    cmd = Executor(login)
    while True:
        try:
            index = clients.index(client)
            nickname = nicknames[index]
            # Broadcasting Messages
            message = (await loop.sock_recv(client, 1024)).decode("utf-8").strip()
            if message == "":
                continue
            if message[0] == "!":
                if cmd.checkPerms(0) == "1":
                    message = str(message[1:]) + "\n"
                    await broadcast(nickname, message.encode("utf-8"))
                else:
                    await loop.sock_sendall(client, "You not have permissions to chat\n".encode("utf-8"))
            else:
                if not cmd.checkCommand(message):
                    await loop.sock_sendall(client, "Not correct command! For see command list write 'help'\n".encode("utf-8"))
                else:
                    msg = cmd.makeCommand(message) + "\n"
                    if msg[0] == "c":
                        match msg[1]:
                            case "0": 1 / 0 # Error for quit =)
                    await loop.sock_sendall(client, msg.encode("utf-8"))            
        except Exception as err:
            logging.error(f"{err}")
            # Removing And Closing Clients
            logging.info(f"{client.getpeername()} disconnected!")
            index = clients.index(client)
            clients.remove(client)
            client.close()
            nickname = nicknames[index]
            await broadcast("SERVER", f"{nickname} left!\n".encode("utf-8"))
            nicknames.remove(nickname)
            cmd.stop()
            break

# Receiving / Listening Function
async def receive():
    # Starting Server
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((host, port))
    server.listen()
    server.setblocking(False)

    loop = asyncio.get_event_loop()
    
    while True:
        form = LRform()
        cmd = None
        # Accept Connection
        client, address = await loop.sock_accept(server)
        logging.info(f"Connected with {address}")
        
        # Has account or not
        successLogin = False
        hasAcc = ""
        login = ""
        nickname = ""
        password = ""
        try:
            while True:
                client.send("Has account? [y/n] ".encode("utf-8"))
                hasAcc = (await loop.sock_recv(client, 1024)).decode("utf-8").strip()
                if hasAcc in "yes" or hasAcc in "not":
                    break
            while not successLogin:
                if hasAcc in "not":
                    client.send("Your login: ".encode("utf-8"))
                    login = (await loop.sock_recv(client, 1024)).decode("utf-8").strip()
                    client.send("Your nickname: ".encode("utf-8"))
                    nickname = (await loop.sock_recv(client, 1024)).decode("utf-8").strip()
                    client.send("Your password: ".encode("utf-8"))
                    password = (await loop.sock_recv(client, 1024)).decode("utf-8").strip()
                    successLogin = form.registration(login, nickname, password)
                    if not successLogin:
                        msg = f"Login {login} already used or nick not \n"
                        client.send(msg.encode("utf-8"))
                elif hasAcc in "yes":
                    client.send("Your login: ".encode("utf-8"))
                    login = (await loop.sock_recv(client, 1024)).decode("utf-8").strip()
                    client.send("Your password: ".encode("utf-8"))
                    password = (await loop.sock_recv(client, 1024)).decode("utf-8").strip()
                    successLogin, nickname = form.login(login, password)
                    if not successLogin:
                        client.send("Not correct login or password\n".encode("utf-8"))
            cmd = Executor(login)

            if cmd.checkPerms(1) == "0":
                client.send("This account has banned\n".encode("utf-8"))
                logging.info(f"{address} disconnected!")
                form.stop()
                client.close()
                continue
        except Exception as err:
            logging.error(f"{err}")
            logging.info(f"{address} disconnected!")
            form.stop()
            client.close()
            continue

        nicknames.append(nickname)
        clients.append(client)

        # Print And Broadcast Nickname
        logging.info(f"Nickname is {nickname}")
        client.send("Connected to server!\n".encode("utf-8"))
        msg = f"{nickname} joined!\n"
        await broadcast("SERVER", msg.encode("utf-8"))

        form.stop()

        loop.create_task(handle(client, login))

if __name__ == "__main__":
    logging.info(f"--- === SERVER START === ---")
    logging.info(f"Host: {host}")
    logging.info("Port: {port}")
    asyncio.run(receive())
