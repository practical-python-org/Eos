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
        self, interaction: discord.Interaction, target: discord.Member, reason: str
    ):
        """
        Moderation command to ban a member from the server.

        Parameters
        ----------
        target : discord.Member
            The member that needs to be banned.
        reason : str
            The reason for the ban.
        """
        # Cant ban bots or admins.
        if not target.bot:
            if not target.guild_permissions.administrator:
                # Message the user, informing them of their fate
                # TODO: Guild specific settings like the contact email
                await interaction.response.defer()
                await target.send(
                    f"## You were banned by {interaction.user.name}.\n"
                    f"**Reason:** {reason}\n"
                    "\nIf you wish to appeal this ban,"
                    " contact PracticalPythonStaff@gmail.com"
                )
                # Then we do the ban
                await target.ban(reason=f"{interaction.user.name} - {reason}")
                logger.info(
                    "{%s} banned {%s}. Reason: {%s}",
                    interaction.user.name,
                    target.name,
                    reason,
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
