import disnake, asyncio, aiofiles, aiohttp, aioconsole, json, logging, os, psutil, subprocess, sys
from disnake.ext import commands

class NullDevice:
    def write(self, s):
        pass
    def flush(self):
        pass

async def load_settings():
    return await load_json(OPTIONS_FILE)

# Load data from JSON files
async def load_json(file_path):
    async with aiofiles.open(file_path, "r") as f:
        content = await f.read()
        return json.loads(content)

# Create directories if they don't exist
def create_directories(directories):
    for directory in directories:
        if not os.path.exists(directory):
            os.makedirs(directory)
            logging.info(f"Created directory {directory}")

# Create files JSON with default content if they don't exist
def create_json_files(directory):
    default_content = {
        "config/options.json": {"version": "0.2.4", "bot-tokens": [], "debug": False, "afto-remove": False},
        "data/list-of-spam.json": {},
        "data/bots-link.tht": ""
    }

    for file_name, content in default_content.items():
        file_path = os.path.join(directory, file_name)
        if not os.path.exists(file_path):
            with open(file_path, "w") as f:
                if file_name == "data/bots-link.tht":
                    f.write(content)
                else:
                    json.dump(content, f, indent=4)
            logging.info(f"Created file {file_name}")

async def configure_logging():
    settings = await load_settings()
    if settings.get("debug", True):
        logging.basicConfig(level=logging.WARNING) # Configure logging
    elif settings.get("debug", False):
        logging.getLogger('disnake').setLevel(logging.ERROR) # Clear disnake logs
        sys.stderr = NullDevice() # Clear cmd output


async def save_settings(settings):
    async with aiofiles.open(OPTIONS_FILE, "w") as f:
        await f.write(json.dumps(settings, indent=4))

async def load_list_of_spam():
    return await load_json(LIST_OF_SPAM_FILE)

async def save_list_of_spam(list_of_spam):
    async with aiofiles.open(LIST_OF_SPAM_FILE, "w") as f:
        await f.write(json.dumps(list_of_spam, indent=4))

# Constants
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
CONFIG_DIR = os.path.join(BASE_DIR, 'config')
OPTIONS_FILE = os.path.join(CONFIG_DIR, 'options.json')
TOKENS_FILE = OPTIONS_FILE
LIST_OF_SPAM_FILE = os.path.join(DATA_DIR, 'list-of-spam.json')
LINK_FILE = os.path.join(DATA_DIR, 'bots-link.tht')
activity = {}
bot_count = 0
allowed_files = {
    "options": "options.json",
    "list-of-spam": "data/list-of-spam.json",
    "bots-link": "data/bots-link.tht"
}

# Create necessary directories and JSON files
create_directories([DATA_DIR, CONFIG_DIR])
create_json_files(BASE_DIR)

# Command handler
async def handle_command(command):
    parts = command.split(" ")

    if parts[0] == "help":  # help
        if len(parts) == 1:
            print("""
            Available commands:
            - help <command>: Show help for a command.
            - set <action> <value> [value]: Update a setting.
            - info: Show bot info.
            - view <file_name>: Show the content of a file.
            - open <file_name>: Open a file with the default application.
            - list <action> [value]: Manage list of users.
            """)
        elif len(parts) == 2:
            command_name = parts[1]
            if command_name == "set": # help set
                print(
                    """
                    Available actions:
                    - afto-remove: True/False
                    - debug: True/False
                    - token: add/remove/view/clear
                    """
                )
            elif command_name == "view" or command_name == "open": # help view
                print(
                    """
                    Available files:
                    - options
                    - list-of-spam
                    - bots-link
                    """
                )
            elif command_name == "list": # help list
                print(
                    """
                    Available actions:
                    - add <user_id>: Add user to the list.
                    - remove <user_id>: Remove user from the list.
                    - view: Show list of users.
                    - clear: Clear list of users.
                    """
                )
            else:
                print(f"No help available.")

    elif parts[0] == "set" and len(parts) >= 3:  # set
        setting, *value_parts = parts[1:]
        value = " ".join(value_parts)

        settings = await load_settings()
        if setting == "afto-remove":  # set afto-remove
            if value.lower() in ["true", "false"]:
                settings["afto-remove"] = value.lower() == "true"
                await save_settings(settings)
                print("Setting updated.")
            else:
                print("Invalid value. Use 'true' or 'false'.")
        elif setting == "debug":  # set debug
            if value.lower() in ["true", "false"]:
                settings["debug"] = value.lower() == "true"
                await save_settings(settings)
                await configure_logging()
                print("Debug setting updated.")
            else:
                print("Invalid value. Use 'true' or 'false'.")
        elif setting == "token":  # set token
            if value.startswith("add "):
                token = value[4:]  # Extract token after "add "
                if len(token) != 72:
                    print("Invalid token length. Token must be 72 characters long.")
                elif token in settings["bot-tokens"]:
                    print("Token already exists.")
                else:
                    settings["bot-tokens"].append(token)
                    await save_settings(settings)
                    print("Token added.")
            elif value.startswith("remove "):  # set token remove
                token = value[7:]  # Extract token after "remove "
                if len(token) != 72:
                    print("Invalid token length. Token must be 72 characters long.")
                elif token in settings["bot-tokens"]:
                    settings["bot-tokens"].remove(token)
                    await save_settings(settings)
                    print("Token removed.")
                else:
                    print("Token not found.")
            elif value == "view":  # set token view
                if settings["bot-tokens"]:
                    for idx, token in enumerate(settings["bot-tokens"], 1):
                        print(f"{idx}. {token}")
                else:
                    print("Empty.")
            elif value == "clear":  # set token clear
                settings["bot-tokens"] = []
                await save_settings(settings)
                print("Cleared.")
            else:
                print("Invalid value.")
        else:
            print("Unknown action.")

    elif parts[0] == "info": # info
        process = psutil.Process(os.getpid())
        cpu_usage = psutil.cpu_percent()
        ram_usage_mb = process.memory_info().rss / (1024 ** 2)
        
        print(
            f"Bots running: {bot_count} \n" +
            f"CPU: {cpu_usage}%" + "\n" +
            f"RAM: {ram_usage_mb:.2f} MB"
        )

    elif parts[0] == "list" and len(parts) >= 2:  # list
        sub_command = parts[1]
        user_id = parts[2] if len(parts) > 2 else None
        list_of_spam = await load_list_of_spam()

        if sub_command == "add" and len(parts) == 3:  # list add
            if len(user_id) == [18, 19] and user_id.isdigit():
                if user_id in list_of_spam:
                    print("Already.")
                else:
                    list_of_spam[user_id] = " "
                    await save_list_of_spam(list_of_spam)
                    print("User added.")
            else:
                print("Invalid user ID. Must be 18-19 characters long.")
        elif sub_command == "remove": # list remove
            if user_id in list_of_spam:
                del list_of_spam[user_id]
                await save_list_of_spam(list_of_spam)
                print("User removed.")
            else:
                print("User not found.")
        elif sub_command == "view":  # list view
            if list_of_spam:
                for user_id, status in list_of_spam.items():
                    print(f"{user_id}: {status}")
            else:
                print("Empty.")
        elif sub_command == "clear":  # list clear
            list_of_spam.clear()
            await save_list_of_spam(list_of_spam)
            print("Cleared.")
        else:
            print("Invalid action.")

    elif parts[0] == "view" and len(parts) == 2:  # view
        key = parts[1].strip()
        file_path = allowed_files.get(key)
        if file_path:
            file_path = os.path.join(BASE_DIR, file_path)
            try:
                async with aiofiles.open(file_path, 'r') as f:
                    content = await f.read()
                    if not content:
                        print("Empty.")
                    else:
                        print(content)
                return
            except Exception as e:
                print(f"Error reading file '{file_path}': {e}")
        print(f"File '{key}' not found.")

    elif parts[0] == "open" and len(parts) == 2:  # open
        key = parts[1].strip()
        file_path = allowed_files.get(key)
        if file_path:
            file_path = os.path.join(BASE_DIR, file_path)
            try:
                subprocess.Popen(['start', file_path], shell=True)
                print(f"Opening {file_path}...")
                return
            except Exception as e:
                print(f"Error opening file '{file_path}': {e}")
        print(f"File '{key}' not found.")

    else:
        print("Invalid command.")


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
            logging.error(f"Bot {bot.user.id} Error: {e}")

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
                    logging.warning(f"Bot {bot.user.id} to user {user_id} Error: {e}")

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
    except Exception as e:
        logging.error(f"Bot with token '{token}' failed to start. Error: {e}")

# Main function
async def main():
    global bot_count
    BOT_TOKENS = await load_json(TOKENS_FILE)
    tasks = []
    for token in BOT_TOKENS.get("bot-tokens", []):
        tasks.append(run_bot(token))
    bot_task = asyncio.create_task(main_console_loop())
    await asyncio.gather(*tasks, bot_task)

# Main loop
async def main_console_loop():
    while True:
        command = await aioconsole.ainput("\n")
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
