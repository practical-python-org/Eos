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


class AdminMute(BaseCog):
    """
    Command to ban a user. Takes in a name, and a reason.
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot

    @is_moderator()
    @is_master_guild()
    @app_commands.command()
    @commands.has_permissions(moderate_members=True)
    async def mute_member(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        time: float,
        reason: str,
    ):
        """
        Moderation command to mute a member.

        Parameters
        ----------
        target : discord.Member
            The member that needs to be muted.
        time : float
            How long the member needs to be muted for in minutes.
        reason : str
            The reason for the mute.
        """

        if not target.bot:
            if not target.guild_permissions.administrator:
                # Message the user, informing them of their fate
                await interaction.response.defer()
                try:
                    await target.send(
                        f"## You were muted by {interaction.user.name}.\n"
                        f"**Time:** {time} minutes"
                    )
                except discord.errors.Forbidden:
                    logger.info(f"{target.name} was muted, but cannot be sent a DM.")
                # Then we do the mute
                await target.timeout(
                    datetime.timedelta(minutes=float(time)), reason=None
                )
                logger.info(
                    "%s muted %s for %s minutes. Reason: %s",
                    interaction.user.name,
                    target.name,
                    time,
                    reason,
                )
                # Then we publicly announce what happened.
                await interaction.followup.send(
                    embed=embed_info(
                        f"**{interaction.user.name}** muted **{target.name}** for {time} minutes"
                        f"\n**Reason:** {reason}"
                    )
                )
            else:
                await interaction.channel.send(
                    embed=embed_info("You can't mute an Admin.")
                )
        else:
            await interaction.channel.send(embed=embed_info("You cant mute a bot."))

    @mute_member.error
    async def mute_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.channel.send(
                embed=embed_info(
                    "User was not found, please check the name and use a mention."
                )
            )

        if isinstance(error, commands.CheckFailure):
            await ctx.channel.send(
                embed=embed_info(
                    f"{ctx.author.mention}, you dont have permission to mute users. The staff has been notified."
                )
            )


async def setup(bot) -> None:
    """
    required.
    """
    await bot.add_cog(AdminMute(bot))
