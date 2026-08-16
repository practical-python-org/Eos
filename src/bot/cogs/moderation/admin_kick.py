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


class AdminKick(BaseCog):
    """
    Command to kick a user. Takes in a name, and a reason.
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot

    @is_moderator()
    @is_master_guild()
    @app_commands.command()
    @commands.has_permissions(kick_members=True)
    async def kick_member(
        self, interaction: discord.Interaction, target: discord.Member, reason: str
    ):
        """
        Moderation command to kick a member from the server.

        Parameters
        ----------
        target : discord.Member
            The member that needs to be kicked.
        reason : str
            The reason for the kick.
        """

        if not target.bot:
            await interaction.response.defer()
            if not target.guild_permissions.administrator:
                # Message the user, informing them of their fate
                # TODO: Guild specific settings like the contact email
                await target.send(
                    f"## You were kicked by {interaction.user.name}.\n"
                    f"**Reason:** {reason}\n"
                    "\nIf you wish to appeal this kick,"
                    " contact PracticalPythonStaff@gmail.com"
                )
                await target.kick(reason=f"{interaction.user.name} - {reason}")
                logger.info(
                    "{%s} kicked {%s}. Reason: {%s}",
                    interaction.user.name,
                    target.name,
                    reason,
                )
                # Then we publicly announce what happened.
                await interaction.followup.send(
                    embed=embed_info(
                        f"**{interaction.user.name}** kicked **{target.name}**"
                        f"\n**Reason:** {reason}"
                    )
                )

            else:
                await interaction.channel.send(
                    embed=embed_info("You can't kick an Admin.")
                )
        else:
            await interaction.channel.send(embed=embed_info("You cant kick a bot."))

    @kick_member.error
    async def kick_error(self, ctx, error):
        if isinstance(error, commands.MemberNotFound):
            await ctx.channel.send(
                embed=embed_info(
                    "User was not found, please check the name and use a mention."
                )
            )

        if isinstance(error, commands.CheckFailure):
            await ctx.channel.send(
                embed=embed_info(
                    f"{ctx.author.mention}, you dont have permission to kick users. The staff has been notified."
                )
            )


async def setup(bot) -> None:
    """
    required.
    """
    await bot.add_cog(AdminKick(bot))
