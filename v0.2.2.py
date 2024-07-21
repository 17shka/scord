import disnake
from disnake.ext import commands
import asyncio
import aiofiles
import aiohttp
import aioconsole
import json
import logging
import os
import psutil
import subprocess
import sys

# Redirect output
class NullDevice:
    def write(self, s):
        pass
    def flush(self):
        pass

sys.stderr = NullDevice()  # Clear cmd output
logging.getLogger('disnake').setLevel(logging.WARNING)  # Clear disnake logs

# Create files JSON with default content if they don't exist
def create_json_files(directory):
    default_content = {
        "tokens.json": {"bot_tokens": []},
        "settings.json": {"afto_stop": False},
        "list-of-spam.json": {},
        "bots-link.tht": ""
    }

    for file_name, content in default_content.items():
        file_path = os.path.join(directory, file_name)
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                if file_name == "bots-link.tht":
                    f.write(content)
                else:
                    json.dump(content, f, indent=4)
            logging.info(f"Created file: {file_name}")

# Load data from JSON files
async def load_json(file_path):
    async with aiofiles.open(file_path, "r") as f:
        content = await f.read()
        return json.loads(content)

async def load_settings():
    return await load_json(SETTINGS_FILE)

async def save_settings(settings):
    async with aiofiles.open(SETTINGS_FILE, "w") as f:
        await f.write(json.dumps(settings, indent=4))

async def load_list_of_spam():
    return await load_json(LIST_OF_SPAM_FILE)

async def save_list_of_spam(list_of_spam):
    async with aiofiles.open(LIST_OF_SPAM_FILE, "w") as f:
        await f.write(json.dumps(list_of_spam, indent=4))

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, '..', 'config')
TOKENS_FILE = os.path.join(CONFIG_DIR, 'tokens.json')
SETTINGS_FILE = os.path.join(CONFIG_DIR, 'settings.json')
LIST_OF_SPAM_FILE = os.path.join(CONFIG_DIR, 'list-of-spam.json')
LINK_FILE = os.path.join(CONFIG_DIR, 'bots-link.tht')
activity = {}
bot_count = 0
allowed_files = ["settings.json", "tokens.json", "list of spam.json", "bots-link.tht"]

create_json_files(CONFIG_DIR)

connector = aiohttp.TCPConnector(ssl=False)
session = aiohttp.ClientSession(connector=connector)

# Commands
async def update_settings(setting, value): # Settings
    settings = await load_settings()
    if setting == "afto_stop":
        if value.lower() in ["true", "false"]:
            settings["afto_stop"] = value.lower() == "true"
            await save_settings(settings)
            print(f"Accepted.")
    else:
        print(f"Unknown settings. Type 'settings' for available settings.")

async def help_view(): # Help view
    files = []
    for file_name in allowed_files:
        files.append(f"- {file_name}")

    return "Files to view:\n" + "\n".join(files)

async def help_open(): # Help open
    files = []
    for file_name in allowed_files:
        files.append(f"- {file_name}")

    return "Files to open:\n" + "\n".join(files)

async def view_file(file_name):  # View
    file_path = os.path.join(CONFIG_DIR, file_name)
    if file_name in allowed_files:
        try:
            async with aiofiles.open(file_path, 'r') as f:
                content = await f.read()
                if not content:
                    print("Empty.")
                else:
                    print(content)
        except Exception as e:
            print(f"Error reading file '{file_path}': {e}")
    else:
        print(f"File '{file_name}' is not allowed to be viewed.")

async def open_file(file_name):  # Open
    file_path = os.path.join(CONFIG_DIR, file_name)
    if file_name in allowed_files:
        try:
            subprocess.Popen(['start', file_path], shell=True)
            print(f"Opening...")
        except Exception as e:
            print(f"Error opening file '{file_path}': {e}")
    else:
        print(f"File '{file_name}' is not allowed to be opened.")

async def info(): # Info
    process = psutil.Process(os.getpid())
    cpu_usage = psutil.cpu_percent()
    ram_usage_mb = process.memory_info().rss / (1024 ** 2)
    
    print(
        f"Number of bots running: {bot_count} \n" +
        f"CPU usage: {cpu_usage}%" + "\n" +
        f"RAM usage: {ram_usage_mb:.2f} MB"
    )
    
async def start_user(user_id): # Start
    if len(user_id) in [18, 19] and user_id.isdigit():
        list_of_spam = await load_list_of_spam()
        if user_id in list_of_spam:
            print("Already.")
        else:
            list_of_spam[user_id] = " "
            await save_list_of_spam(list_of_spam)
            print("Added.")
    else:
        print(f"Wrong value '{user_id}'. Must be a number with length 18-19.")

async def stop_user(user_id): # Stop
    if len(user_id) in [18, 19] and user_id.isdigit():
        list_of_spam = await load_list_of_spam()
        if user_id in list_of_spam:
            del list_of_spam[user_id]
            await save_list_of_spam(list_of_spam)
            print("Removed.")
        else:
            print("Absent.")
    else:
        print(f"Wrong value. Must be a number with length 18-19.")

async def list_users(): # List
    list_of_spam = await load_list_of_spam()
    if list_of_spam:
        for idx, (user_id, status) in enumerate(list_of_spam.items(), 1):
            print(f"{idx}. {user_id} {status}")
    else:
        print("Empty.")

async def clear(): # Clear
    list_of_spam = await load_list_of_spam()
    if list_of_spam:
        for idx, user_id in enumerate(list_of_spam.keys(), 1):
            print(f"{idx}. {user_id}")
        list_of_spam.clear()
        await save_list_of_spam(list_of_spam)
    else:
        print("Empty.")

# Command handler
async def handle_command(command):
    parts = command.split(" ")
    if parts[0] == "help" and len(parts) == 1: # General help
        print("""
        Available commands:
        - help: Show this help.
        - settings: Show available settings.
        - view <file_name>: Show the content of a file.
        - open <file_name>: Open a file with the default application.
        - info: Show bot info.
        - start <user_id>: Add user to the list.
        - stop <user_id>: Remove user from the list.
        - list: Show list of users.
        - clear: Clear list of users.
        """)
    elif parts[0] == "help" and len(parts) == 2:
        command_name = parts[1]
        if command_name == "settings":
            print("""
            Available settings:
            - afto_stop: True/False

            Possible actions: 
            - on/off
            """)
        elif command_name == "view":
            print(await help_view())
        elif command_name == "open":
            print(await help_open())
        else:
            print(f"No help available for '{command_name}'.")
    elif parts[0] == "settings" and parts[1] in ["on", "off"] and len(parts) == 3:
        value = "true" if parts[1] == "on" else "false"
        await update_settings(parts[2], value)
    elif parts[0] == "view" and len(parts) == 2: # View
        file_name = parts[1]
        await view_file(file_name)
    elif parts[0] == "open" and len(parts) == 2: # Open
        file_name = parts[1]
        await open_file(file_name)
    elif parts[0] == "info" and len(parts) == 1: # Info
        await info()
    elif parts[0] == "start" and len(parts) == 2: # Start
        user_id = parts[1]
        await start_user(user_id)
    elif parts[0] == "stop" and len(parts) == 2: # Stop
        user_id = parts[1]
        await stop_user(user_id)
    elif parts[0] == "list" and len(parts) == 1: # List
        await list_users()
    elif parts[0] == "clear" and len(parts) == 1: # Clear
        await clear()
    else:
        print(f"Unknown command: '{command}'. Type 'help' for available commands.")
        
# Launching bots
async def run_bot(token):
    global bot_count
    bot_count += 1
    intents = disnake.Intents.default()
    bot = commands.Bot(command_prefix=commands.when_mentioned, intents=intents)

    @bot.event
    async def on_ready():
        await bot.change_presence(status=disnake.Status.dnd)
        invite_link = f"https://discord.com/oauth2/authorize?client_id={bot.user.id}&permissions=0&scope=bot"

        # Add bots-link to the list
        try:
            async with aiofiles.open(LINK_FILE, 'r') as f:
                existing_links = await f.read()

            if invite_link + "\n" not in existing_links:
                async with aiofiles.open(LINK_FILE, 'a') as f:
                    await f.write(invite_link + "\n")

        except Exception as e:
            logging.error(f"Error while handling invite link: {e}")

        # Initialize bot in activity
        activity[bot.user.id] = {}

        bot.loop.create_task(send_messages(bot))

    async def send_messages(bot, MESSAGE="||{user_mention}|| https://discord.gift/z https://discord.gift/x https://discord.gift/c"):
        while True:
            list_of_spam = await load_list_of_spam()
            updated_list_of_spam = list_of_spam.copy()

            if not list_of_spam:
                await asyncio.sleep(1)
                continue

            for user_id in list_of_spam:
                try:  # Send message
                    user = await bot.fetch_user(user_id)
                    await user.send(MESSAGE)  # Send message
                    if activity[bot.user.id].get(user_id) != "+":
                        activity[bot.user.id][user_id] = "+"
                except Exception as e:
                    if activity[bot.user.id].get(user_id) != "-":
                        activity[bot.user.id][user_id] = "-"
                    logging.error(f"Error sending message to user {user_id}: {e}")

                await asyncio.sleep(1)  # Pause

            # Check if any status for a user is "+"
            for user_id in list_of_spam:
                if any(status == "+" for bot_id, user_status in activity.items() for user, status in user_status.items() if user == user_id):
                    updated_list_of_spam[user_id] = "+"
                else:
                    updated_list_of_spam[user_id] = "-"

            # Save list_of_spam if there are changes
            if updated_list_of_spam != list_of_spam:
                await save_list_of_spam(updated_list_of_spam)

            # Check settings
            settings = await load_settings()
            if settings.get("afto_stop", False):
                # Remove users with status "-"
                updated_list_of_spam = {user_id: status for user_id, status in updated_list_of_spam.items() if status != "-"}
                await save_list_of_spam(updated_list_of_spam)

    try:
        await bot.start(token)
    except aiohttp.client_exceptions.ClientOSError as e:
        await asyncio.sleep(5)
        await run_bot(token)
        logging.error(f"{e}. Restarting bot.")

# Main function
async def main():
    global bot_count
    BOT_TOKENS = await load_json(TOKENS_FILE)
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
