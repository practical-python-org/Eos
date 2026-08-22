import datetime
import logging
import os
import sys
from pathlib import Path

import discord
from __logger__ import setup_logger
from core.api_helper import API
from discord.ext import commands

discord.VoiceClient.warn_nacl = False
logger = logging.getLogger(__name__)
setup_logger(
    level=int(os.getenv("BOT_LOG_LEVEL")), stream_logs=bool(os.getenv("STREAM_LOGS"))
)

intents = discord.Intents.all()


class Eos(commands.Bot):
    """
    The bot
    """

    async def close(self) -> None:
        """
        Closes the shared API session before disconnecting from Discord.
        """
        logger.debug("Executing shutdown tasks...")
        if getattr(self, "api", None) is not None:
            await self.api.close()
        await super().close()


bot = Eos(command_prefix=os.getenv("PREFIX"), intents=intents)
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

    cogs_path = Path(__file__).parent / "cogs"

    for directory in cogs_path.iterdir():
        if directory.is_dir() and not directory.name.startswith("_"):
            for file in directory.glob("*.py"):
                if not file.stem.startswith("_"):
                    logger.info(f"\\{directory.name}\\{file.name}")
                    try:
                        await robot.load_extension(f"cogs.{directory.name}.{file.stem}")
                    except Exception as e:
                        logger.warning("- - - Cog failed to load!!")
                        logger.warning(f"- - - {e}")

    logger.info("... Success.")


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
