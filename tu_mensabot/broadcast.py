#!/usr/bin/env python3

# -- broadcast.py --
# This script simplifies broadcasting messages to single users or all newsletter
# receivers via the bot. It reads user data from the main databse specified in
# the section 'db_config' of the config file.
# Usage: `python broadcast.py [config_file]`
#

import sys
import json
from os import environ
from os.path import isfile
import sqlite3
from tgsend import Telegram, ParseMode
from time import sleep

# use 'config.json' as default config file
if len(sys.argv) > 1:
    config_file = sys.argv[1]
else:
    config_file = "config.json"
with open(config_file, 'r') as f:
    config = json.load(f)

telegram = Telegram(config["token"], 1)
db_config = config.get("db_config")
if not db_config or not "main" in db_config:
    exit
db_file = db_config["main"]

def choose_newsletter():
    users = []
    _conn = sqlite3.connect(db_file)
    _cur = _conn.cursor()
    _cur.execute("select id from newsletter where time != 'off'")    
    for item in _cur.fetchall():
        users.append(item[0])   
    _conn.commit()
    _conn.close()
    return users

def choose_single_chat():
    print("Enter a comma-separated list of chat IDs:")
    id_str_list = input("Chat ID list > ")
    users = []
    try:
        for id_str in id_str_list.split(","):
            users.append(int(id_str))
        return users
    except:
        print("ERROR: Invalid input.")
        exit()

def get_user_names(users):
    names = {}
    _conn = sqlite3.connect(db_file)
    _cur = _conn.cursor()
    for user in users:
        if not user > 0:
            continue # TODO this skips groups
        _cur.execute("select firstname from userstats where id=?", (user,))    
        name=_cur.fetchone()[0]
        names[user] = name  
    _conn.close()
    return names

groups=[
    ("Newsletter receivers.", choose_newsletter),
    ("Specify Chat IDs.", choose_single_chat)
]

print("-"*30)
print("Broadcast Messages to tu_mensabot Users")
print("-"*30)
# 1. Choose group
print("1. Choose the target group:")
for i, group in enumerate(groups):
    print(" "*5 + "[{0:2}] {1}".format(i, group[0]))
number = int(input("Select a number > "))
print("You've chosen \"{}\"".format(groups[number][0]))
ids = groups[number][1]()
# 2. Choose file
print("2. Now enter the file containing your message:")
file = input("Enter file name > ")
if not isfile(file):
    print("ERROR: The given file does not exist.")
    exit()
with open(file, 'r', encoding='utf-8') as f:
    text = f.read()
names = get_user_names(ids)
# 3. Confirm
print("-"*30)
print("RECEIVERS: {0}".format(ids))
print("MESSAGE:")
print(text)
print("-"*30)
confirm = input("Do you really want to send this message? (y/n) > ")
if confirm != "y":
    print("Aborted sending message.")
    exit()
# 4. Send message
for id in ids:
    if not id > 0: # TODO skips groups
        continue
    telegram.chat_id = id
    custom_text = text.replace('%name%', names[id])
    response = telegram.send_message(custom_text, parse_mode=ParseMode.HTML)
    print(response.json())
    sleep(0.05)
