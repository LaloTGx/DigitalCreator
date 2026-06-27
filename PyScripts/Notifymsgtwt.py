#!/usr/bin/env python3
import socket
import os

# Tienes que crear un env dentro del repositorio para poder ejecutar el script
# Comando: python -m venv venv
current_pid = os.getpid()
os.system(f"pgrep -f Notifymsgtwt.py | grep -v {current_pid} | xargs kill -9 2>/dev/null")

server = 'irc.chat.twitch.tv'
port = 6667
nickname = 'User'# Nombre de usuario con mayusculas y minusculas
token = 'oauth:' # Token para recibir los mensajes, lo puedes generar aqui: https://twitchtokengenerator.com/
channel = '#user'# Canal de twitch en minusculas (donde recibira los mensajes)

sock = socket.socket()
sock.connect((server, port))
sock.send(f"PASS {token}\r\n".encode('utf-8'))
sock.send(f"NICK {nickname}\r\n".encode('utf-8'))
sock.send(f"JOIN {channel}\r\n".encode('utf-8'))

while True:
    resp = sock.recv(2048).decode('utf-8')
    if resp.startswith('PING'):
        sock.send("PONG :tmi.twitch.tv\r\n".encode('utf-8'))
    elif "PRIVMSG" in resp:
        try:
            parts = resp.split(':', 2)
            user = parts[1].split('!', 1)[0]
            msg = parts[2].strip()
            os.system(f"notify-send '{user}' '{msg}' -t 3000")
        except:
            continue
