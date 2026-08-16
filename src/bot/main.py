import datetime
import logging
import os
import sys
from pathlib import Path

import discord
from discord.ext import commands

from src.bot.__logger__ import setup_logger
from src.bot.core.api_helper import API

discord.VoiceClient.warn_nacl = False
logger = logging.getLogger(__name__)
setup_logger(
    level=int(os.getenv("BOT_LOG_LEVEL")), stream_logs=bool(os.getenv("STREAM_LOGS"))
)

intents = discord.Intents.all()
bot = commands.Bot(command_prefix=os.getenv("PREFIX"), intents=intents)
bot.boot_time = datetime.datetime.now()


async def load_cogs(robot: commands.Bot) -> None:
    """
    Loads all the cog extensions from the directories under the /cogs/ folder into the bot.

    This function iterates through each directory within the /cogs/ folder, excluding those
    that start with an underscore. It then attempts to load each Python file as a cog extension,
    provided the file does not start with an underscore.

    Parameters:
    robot (commands.Bot): The instance of the bot to which the cogs will be loaded.

    Returns:
    None: This function does not return any value.
    """
    logger.info("Loading Cogs...")

    base_dir = Path(__file__).parent.parent.parent
    cogs_path = Path(__file__).parent / "cogs"
    cogs_loaded = 0
    cogs_failed = 0

    for directory in cogs_path.iterdir():
        if directory.is_dir() and not directory.name.startswith("_"):
            for file in directory.glob("*.py"):
                if not file.stem.startswith("_"):
                    relative_path = file.relative_to(base_dir)
                    module_name = (
                        str(relative_path).replace(os.sep, ".").replace(".py", "")
                    )

                    try:
                        await robot.load_extension(module_name)
                        cogs_loaded += 1
                    except commands.ExtensionAlreadyLoaded:
                        logger.warning(f"Already loaded: {module_name}")
                    except commands.ExtensionFailed as e:
                        logger.warning(f"Failed to load {module_name}: {e}")
                        cogs_failed += 1
                    except commands.NoEntryPointError:
                        logger.warning(f"No setup() function in: {module_name}")
                        cogs_failed += 1
                    except Exception as e:
                        logger.warning(
                            f"Unexpected error loading {module_name}: {e}",
                            exc_info=True,
                            stack_info=True,
                        )
                        cogs_failed += 1

    logger.info("Loaded: %s | Failed: %s", cogs_loaded, cogs_failed)
    logger.info("Finished loading cogs.")


@bot.event
async def setup_hook() -> None:
    """
    Executes custom setup logic before the bot logs in.

    This function is called before the bot connects to Discord and logs in.
    It can be used to perform any necessary setup tasks that need to be
    completed before the bot becomes operational.

    Parameters:
    None

    Returns:
    None: This function does not return any value.
    """
    logger.debug("Executing set up hook...")
    bot.api = API()
    await bot.api.setup()
    await load_cogs(bot)
    logger.info("Startup tasks complete")


@bot.event
async def on_ready() -> None:
    """
    The on_ready is executed AFTER the bot logs in.
    """
    logger.debug("Executing on_ready event.")
    # synced = await bot.tree.sync()
    # logger.info(f"Synced {len(synced)} command(s).")
    logger.info(f"{bot.user.name} is online and ready to go.")


def boink() -> None:
    """
    Loads the bot key as the first arg when running the bot OR from an env variable.
    For example:
        "python main.py BOT_TOKEN_HERE"
    """

    if len(sys.argv) > 1:  # Check args for the token first
        token = sys.argv[1].replace("TOKEN=", "")
        logger.debug("Loading Token from arg.")
        bot.run(token)

    elif os.environ["TOKEN"] is not None:  # if not in args, check the env vars
        logger.debug("Loading Token from environment variable.")
        bot.run(os.environ["TOKEN"])

    else:
        logger.critical("You must include a bot token...")
        logger.critical("TOKEN must be in the .env file")
        logger.critical(
            'OR you must run the bot using: "python __main__.py TOKEN=YOUR_DISCORD_TOKEN"'
        )
        return


if __name__ == "__main__":
    boink()
