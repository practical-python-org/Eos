import datetime
import logging
import os

import discord
from discord.ext import commands

from src.bot.cogs import BaseCog

logger = logging.getLogger(__name__)


def embed_hc(api, db, uptime, git_hash):
    """
    Embedding for avatar change alerts.
    """
    color = (
        api.get("color")
        if api.get("color") == db.get("color")
        else discord.Color.yellow()
    )

    embed = discord.Embed(
        title="Health checks",
        color=color,
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    embed.add_field(name=api.get("message"), value=api.get("status_code"), inline=False)
    embed.add_field(name=db.get("message"), value=db.get("status_code"), inline=False)
    embed.add_field(name="Uptime:", value=uptime, inline=False)
    embed.add_field(name="Commit Hash:", value=git_hash, inline=False)
    return embed


class Health(BaseCog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(logger)

        self.bot = bot

    @commands.hybrid_command()
    async def hc(self, ctx: commands.Context) -> None:
        """
        Health check of the bot. Replies with the health stats of the bot.
        """

        logger.debug("healthcheck command used.")

        results = await self.bot.api.health_check()
        hc_api = results["api_status"]
        logger.debug(hc_api)
        try:
            status_api = hc_api[0]["status"]
            status_code_api = hc_api[1]
        except KeyError:
            status_api = "Unhealthy"
            status_code_api = "API Unreachable"

        api_info = {
            "message": f"API Status: {status_api}",
            "status_code": f"Response: {status_code_api}",
            "color": discord.Color.green()
            if status_api == "ok"
            else discord.Color.red(),
        }

        hc_db = results["db_status"]
        logger.debug(hc_db)
        try:
            status_db = hc_db[0]["status"]
            status_code_db = hc_db[1]
        except KeyError:
            status_db = "Unhealthy"
            status_code_db = "DB Unreachable"

        db_info = {
            "message": f"Database Status: {status_db}",
            "status_code": f"Response: {status_code_db}",
            "color": discord.Color.green()
            if status_db == "ok"
            else discord.Color.red(),
        }

        uptime = self.get_uptime(self.bot.boot_time)

        # Get commit hash from .env file
        git_hash = os.getenv("GIT_HASH", default="Spam, Spam, Spam, Egg, and Spam!")

        await ctx.reply(embed=embed_hc(api_info, db_info, uptime, git_hash))

    def get_uptime(self, boot_time: datetime.datetime) -> str:
        """Get uptime from bot"""
        now = datetime.datetime.now()
        delta: datetime.timedelta = now - boot_time
        message = self.format_uptime(delta)
        return message

    def format_uptime(self, time_delta: datetime.timedelta) -> str:
        """Format time_delta components for embed message"""
        total_minutes: int = time_delta.seconds // 60
        minutes: int = total_minutes % 60
        hours: int = time_delta.seconds // 3600
        days: int = time_delta.days

        return f"{days}d {hours}h {minutes}m"


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(Health(bot))
