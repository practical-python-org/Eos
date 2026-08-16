"""
Admin command to remove messages in bulk.
"""

import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.bot.cogs import BaseCog
from src.bot.cogs._checks import is_master_guild, is_moderator

logger = logging.getLogger(__name__)


def embed_info(message):
    """
    Embedding for general things
    """
    embed = discord.Embed(
        title="",
        description=message,
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    return embed


def api_request_is_ok(request):
    if request[0]["status"] == "ok":
        return True
    return False


def logging_is_activated(request):
    if request[0]["logging"][2] == "0":
        return False
    return True


class AdminPurge(BaseCog):
    """
    We are limited to 100 messages per command by Discord API
    TODO: This command should be hidden from non-staff users.
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot
        self.log_channel_req = self.bot.api.get_one_log_setting("3")  # chat_log

    @is_moderator()
    @is_master_guild()
    @app_commands.command()
    async def purge_messages(self, interaction: discord.Interaction, amount: int):
        """
        Purge a set of messages from the current channel.

        Parameters
        ----------
        amount : int
            The number of messages that will be purged.
        """

        if api_request_is_ok(self.log_channel_req):
            logger.info(
                f"{interaction.user.name} is purging {amount} messages from "
                f"the {self.log_channel_req[0]['logging'][1]}"
            )
            await interaction.response.defer()
            await interaction.channel.purge(limit=amount + 1)

            if logging_is_activated(self.log_channel_req):
                logging_channel = await self.bot.fetch_channel(
                    self.log_channel_req[0]["logging"][2]
                )

                await logging_channel.send(
                    f"{amount} messages purged"
                    f" from {interaction.channel.mention}"
                    f" by {interaction.user.mention}."
                )

            elif not logging_is_activated(self.log_channel_req):
                logger.warning(
                    f"Purge command was used by {interaction.user.name}, but "
                    f"logging for the chat log was turned off."
                )
        else:
            logger.critical("API error while purging messages. Status is NOT ok.")

    @purge_messages.error
    async def purge_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            await ctx.channel.send(
                embed=embed_info(
                    f"{ctx.author.mention}, you dont have permission to purge messages. The staff has been notified."
                )
            )


async def setup(bot) -> None:
    """
    required by all cogs.
    """
    await bot.add_cog(AdminPurge(bot))
