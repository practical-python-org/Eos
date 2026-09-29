"""
Admin command for kicking a user.
"""

import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.bot.cogs import BaseCog
from src.bot.cogs._checks import is_master_guild, is_moderator
from src.bot.cogs.moderation._message_removal import (
    MAX_MESSAGES_TO_REMOVE,
    remove_and_log_messages,
)

logger = logging.getLogger(__name__)


def embed_info(message):
    """
    Embedding for things you cant do.
    """
    embed = discord.Embed(
        title="",
        description=message,
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    return embed


class AdminBan(BaseCog):
    """
    Command to ban a user. Takes in a name, and a reason.
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot

    @is_moderator()
    @is_master_guild()
    @commands.has_permissions(ban_members=True)
    @app_commands.command()
    async def ban_member(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str,
        messages_to_remove: app_commands.Range[int, 0, MAX_MESSAGES_TO_REMOVE],
    ):
        """
        Moderation command to ban a member from the server.

        Parameters
        ----------
        target : discord.Member
            The member that needs to be banned.
        reason : str
            The reason for the ban.
        messages_to_remove : int
            How many messages to delete and log.
        """
        # Cant ban bots or admins.
        if not target.bot:
            if not target.guild_permissions.administrator:
                # Message the user, informing them of their fate
                # TODO: Guild specific settings like the contact email
                await interaction.response.defer()
                try:
                    await target.send(
                        f"## You were banned by {interaction.user.name}.\n"
                        f"**Reason:** {reason}\n"
                        "\nIf you wish to appeal this ban,"
                        " contact PracticalPythonStaff@gmail.com"
                    )
                except discord.HTTPException:
                    # Closed DMs must not stop the ban.
                    logger.info("Could not DM %s about their ban.", target.name)
                # Then we do dat ban
                await target.ban(
                    reason=f"{interaction.user.name} - {reason}",
                    delete_message_seconds=0,
                )
                logger.info(
                    "{%s} banned {%s}. Reason: {%s}",
                    interaction.user.name,
                    target.name,
                    reason,
                )
                await remove_and_log_messages(
                    self.bot,
                    interaction.guild,
                    target,
                    messages_to_remove,
                    embed_info(
                        f"{interaction.user.mention} banned {target.mention}"
                        f"\n**Reason:** {reason}"
                    ),
                )
                # Then we publicly announce what happened.
                await interaction.followup.send(
                    embed=embed_info(
                        f"**{interaction.user.name}** banned **{target.name}**"
                        f"\n**Reason:** {reason}"
                    )
                )
            else:
                await interaction.channel.send(
                    embed=embed_info("You can't ban an Admin.")
                )
        else:
            await interaction.channel.send(embed=embed_info("You cant ban a bot."))

    @ban_member.error
    async def ban_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.channel.send(
                embed=embed_info(
                    "User was not found, please check the name and use a mention."
                )
            )

        if isinstance(error, commands.CheckFailure):
            await ctx.channel.send(
                embed=embed_info(
                    f"{ctx.author.mention}, you dont have permission to ban users. The staff has been notified."
                )
            )


async def setup(bot) -> None:
    """
    required.
    """
    await bot.add_cog(AdminBan(bot))
