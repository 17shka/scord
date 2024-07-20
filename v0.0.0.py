import disnake
from disnake.ext import commands
import asyncio
import aiofiles
import aiohttp
import aioconsole
import json
import logging
import os
import sys

# Redirect output
class NullDevice:
    def write(self, s):
        pass
    def flush(self):
        pass

sys.stderr = NullDevice() # Clear cmd output
logging.getLogger('disnake').setLevel(logging.WARNING) # Clear disnake logs

# Constants
TOKENS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tokens.json')
LIST_OF_SPAM = []

connector = aiohttp.TCPConnector(ssl=False)
session = aiohttp.ClientSession(connector=connector)

# Load data from JSON file
async def load_tokens():
    async with aiofiles.open(TOKENS_FILE, "r") as f:
        content = await f.read()
        return json.loads(content)

# Commands
async def start_user(user_id):
    if len(user_id) in [18, 19] and user_id.isdigit():
        if user_id in LIST_OF_SPAM:
            print("Already.")
        else:
            LIST_OF_SPAM.append(user_id)
            print("Added.")
    else:
        print(f"Wrong value: {user_id}. Must be a number with length 18-19.")

async def stop_user(user_id):
    if len(user_id) in [18, 19] and user_id.isdigit():
        if user_id in LIST_OF_SPAM:
            LIST_OF_SPAM.remove(user_id)
            print("Removed.")
        else:
            print("Absent.")
    else:
        print(f"Wrong value: {user_id}. Must be a number with length 18-19.")

async def clear():
    if LIST_OF_SPAM:
        cleared = LIST_OF_SPAM.copy()
        LIST_OF_SPAM.clear()
        for idx, user_id in enumerate(cleared, 1):
            print(f"{idx}. {user_id}")
    else:
        print("Empty.")

async def list_users():
    if LIST_OF_SPAM:
        for idx, user_id in enumerate(LIST_OF_SPAM, 1):
            print(f"{idx}. {user_id}")
    else:
        print("Empty.")

# Command handler
async def handle_command(command):
    parts = command.split(" ")
    if parts[0] == "start" and len(parts) == 2:
        user_id = parts[1]
        await start_user(user_id)
    elif parts[0] == "stop" and len(parts) == 2:
        user_id = parts[1]
        await stop_user(user_id)
    elif parts[0] == "clear" and len(parts) == 1:
        await clear()
    elif parts[0] == "list" and len(parts) == 1:
        await list_users()
    elif parts[0] == "help" and len(parts) == 1:
        print("""
        Available commands:
        - help: Show this help
        - start <user_id>: Add user to the list
        - stop <user_id>: Remove user from the list
        - list: Show list of users
        - clear: Clear list of users
        """)
    else:
        print(f"Unknown command: '{command}'. Type 'help' for available commands.")

# Launching bots
async def run_bot(token):
    intents = disnake.Intents.default()
    bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

    @bot.event
    async def on_ready():
        logging.info(f'Bot: [{bot.user}] | launched.')
        await bot.change_presence(status=disnake.Status.dnd)
        bot.loop.create_task(send_messages())

    async def send_messages(MESSAGE="||{user_mention}|| https://discord.gift/z https://discord.gift/x https://discord.gift/c"):
        while True:
            if not LIST_OF_SPAM:
                await asyncio.sleep(1)
                continue

            for user_id in LIST_OF_SPAM:
                try:
                    user = await bot.fetch_user(user_id)
                    await user.send(MESSAGE)
                    await asyncio.sleep(1)
                except disnake.DiscordException as e:
                    logging.error(f"Failed to send message to {user_id}: {e}")

    try:
        await bot.start(token)
    except aiohttp.client_exceptions.ClientOSError as e:
        logging.error(f"Encountered ClientOSError: {e}. Restarting bot...")
        await asyncio.sleep(5)
        await run_bot(token)

# Main function
async def main():
    BOT_TOKENS = await load_tokens()
    tasks = []
    for token in BOT_TOKENS.get("bot_tokens", []):
        tasks.append(run_bot(token))
    bot_task = asyncio.create_task(main_console_loop())
    await asyncio.gather(*tasks, bot_task)

# Main loop
async def main_console_loop():
    while True:
        command = await aioconsole.ainput("\n> ")
        await handle_command(command.strip())

# Run
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(""" 
　　　 　　／＞　　フ
　　　 　　| 　_　 _ l
　 　　 　／ ミ＿xノ
　　 　 /　　　 　 |
　　　 /　 ヽ　　 ﾉ
　 　 │　　|　|　|
　／￣|　　 |　|　|
　| (￣ヽ＿_ヽ_)__)
　＼二つ
    """)
    asyncio.run(main())
