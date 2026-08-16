"""
Admin command for kicking a user.
"""

import asyncio
import datetime
import logging

import discord
from discord import app_commands
from discord.ext import commands
from discord.utils import get

from src.bot.cogs import BaseCog
from src.bot.cogs._checks import is_master_guild, is_moderator

logger = logging.getLogger(__name__)


def embed_info(message):
    """
    Embedding general info things.
    """
    embed = discord.Embed(
        title="",
        description=message,
        color=discord.Color.green(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    return embed


def embed_cant_do_that(message):
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


def embed_quarantine(moderator, some_member, number_of_removed_messages):
    """
    Embedding for user ban alerts.
    """
    embed = discord.Embed(
        title="",
        description=f"{moderator.name} quarantined {some_member.name}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )

    if number_of_removed_messages > 0:
        embed.add_field(
            name="Messages removed:",
            value=f"{str(number_of_removed_messages)} messages.",
        )

    return embed


class AdminQuarantine(BaseCog):
    """
    Command to quarantine a user.
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot
        self.naughty_role = self.bot.api.get_one_role("7")[0]["roles"][
            2
        ]  # quarantine role ID
        self.verified_role = self.bot.api.get_one_role("6")[0]["roles"][
            2
        ]  # Verification role ID
        self.mod_log = self.bot.api.get_one_log_setting("5")  # mod_log

    @app_commands.command()
    @is_moderator()
    @is_master_guild()
    @commands.has_permissions(moderate_members=True)
    async def quarantine(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        messages_to_remove: int,
    ):
        """
        Quarantines the specified user. Removes their access from public channels.

        Parameters
        ----------
        target : discord.Member
            The member to quarantine.
        messages_to_remove : int
            The number of messages to remove from this member.
        """

        await interaction.response.defer()
        logger.info(
            f"{interaction.user.name} used the quarantine command on {target.name}"
        )
        if not target.bot:
            if not target.guild_permissions.administrator:
                message_counter = 0

                mod_log = await self.bot.fetch_channel(self.mod_log[0]["logging"][2])
                verified_role = get(interaction.guild.roles, id=int(self.verified_role))
                naughty_role = get(interaction.guild.roles, id=int(self.naughty_role))

                try:
                    await target.remove_roles(verified_role)
                    await target.add_roles(naughty_role)
                    await interaction.followup.send(
                        f"{target.name} has been quarantined.", ephemeral=True
                    )

                except Exception as notification1:
                    await interaction.followup.send(
                        "There was an issue with the command.", ephemeral=True
                    )
                    logger.critical(
                        f"There was an error in the Quarantine command...\n{notification1}"
                    )

                    # remove messages, if that was specified.
                    await interaction.followup.send(
                        content=f"Removing {messages_to_remove} messages by {target.name}...",
                        ephemeral=True,
                    )

                if messages_to_remove > 0:
                    async for message in interaction.channel.history(limit=50):
                        if messages_to_remove > message_counter:
                            if message.author.name == target.name:
                                await message.delete()
                                message_counter += 1
                                await asyncio.sleep(0.2)  # Avoiding rate limits.

                await mod_log.send(
                    embed=embed_quarantine(interaction.user, target, message_counter)
                )

            else:
                await interaction.followup.send(
                    embed=embed_cant_do_that("You can't quarantine an Admin."),
                    ephemeral=True,
                )
        else:
            await interaction.followup.send(
                embed=embed_cant_do_that("You cant quarantine a bot."), ephemeral=True
            )

    @app_commands.command()
    @commands.has_permissions(moderate_members=True)
    @is_moderator()
    @is_master_guild()
    async def release(self, interaction: discord.Interaction, target: discord.Member):
        """
        Releases the specified member from quarantine. Gives back their access to public channels.

        Parameters
        ----------
        target : discord.Member
            The member to release from quarantine.
        """

        await interaction.response.defer()
        logger.info(
            f"{interaction.user.name} used the release command on {target.name}"
        )
        if not target.bot:
            mod_log = await self.bot.fetch_channel(self.mod_log[0]["logging"][2])
            verified_role = get(interaction.guild.roles, id=int(self.verified_role))
            naughty_role = get(interaction.guild.roles, id=int(self.naughty_role))

            try:
                await target.add_roles(verified_role)
                await target.remove_roles(naughty_role)
                await interaction.followup.send(
                    f"{interaction.user.mention} released {target.mention} from quarantine",
                    ephemeral=True,
                )
                await mod_log.send(
                    embed=embed_info(
                        f"{interaction.user.mention} released {target.mention} from quarantine"
                    )
                )

            except Exception as notification1:
                await interaction.followup.send(
                    "There was an issue with the command.", ephemeral=True
                )
                logger.critical(
                    f"There was an error in the release command...\n{notification1}"
                )

    @quarantine.error
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
    await bot.add_cog(AdminQuarantine(bot))
