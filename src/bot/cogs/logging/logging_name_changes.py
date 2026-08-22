"""
logs when a username is changed.
"""

import datetime
import logging
import os

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


def embed_name_change(username_before, username_after):
    """
    Embedding for user name change alerts.
    """
    embed = discord.Embed(
        title="",
        description=f"{username_before} changed their name to {username_after}",
        color=discord.Color.dark_grey(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    return embed


class LoggingNameChanges(commands.Cog):
    """
    Simple listener to on_member_update
    """

    def __init__(self, bot):
        self.bot = bot
        self.user_log = self.bot.api.get_one_log_setting("4")  # User_log

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """
        Just checking if the name before is != to the name after.
        """
        if before.guild.id != int(os.getenv("MASTER_GUILD")) or before.guild.id is None:
            logger.warning(
                "on_member_update fired, but not in master guild. Ignoring event."
            )
            return

        username_before = before.nick or before.name
        username_after = after.nick or after.name

        logger.debug(f"{username_before}, {username_after}")

        if username_after == before.name:
            return

        if username_before != username_after:
            if self.user_log["status"] == "ok":
                if self.user_log["log_setting"]["value"] == "0":
                    logger.debug(
                        f"log was triggered, but logging is disabled. API: {self.user_log}"
                    )
                    return
                logs_channel = await self.bot.fetch_channel(
                    self.user_log["log_setting"]["value"]
                )

                embed = embed_name_change(username_before, username_after)

                await logs_channel.send(embed=embed)
            else:
                logger.critical(f"API error. API response not ok. -> {self.user_log}")


async def setup(bot: commands.Bot) -> None:
    """boink"""
    await bot.add_cog(LoggingNameChanges(bot))
