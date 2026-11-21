"""
Admin command for kicking a user.
"""

import datetime
import logging

import discord
from discord import app_commands
from discord.utils import get

from src.bot.cogs import BaseCog
from src.bot.cogs._checks import (
    app_is_master_guild,
    app_requires_permissions,
    respond_to_app_command_error,
)
from src.bot.cogs.moderation._message_removal import (
    MAX_MESSAGES_TO_REMOVE,
    remove_and_log_messages,
    send_to_mod_log,
)

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


def embed_quarantine(moderator, some_member):
    """
    Embedding for user quarantine alerts.
    """
    embed = discord.Embed(
        title="",
        description=f"{moderator.name} quarantined {some_member.name}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    return embed


class AdminQuarantine(BaseCog):
    """
    Command to quarantine a user.
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot

    def find_role(self, guild, role_flag):
        """
        Look up a configured role in the guild. None if unset, or if it doesn't exist here.
        """
        response = self.bot.api.get_one_role(role_flag)
        if response["status"] != "ok":
            logger.critical(f"API error. API response not ok. -> {response}")
            return None
        return get(guild.roles, id=int(response["role"]["value"]))

    @app_commands.command()
    @app_is_master_guild()
    @app_requires_permissions(ban_members=True, moderate_members=True)
    async def quarantine(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        messages_to_remove: app_commands.Range[int, 0, MAX_MESSAGES_TO_REMOVE],
    ):
        """
        Quarantines the specified user. Removes their access from public channels.

        Parameters
        ----------
        target : discord.Member
            The member to quarantine.
        messages_to_remove : int
            How many messages to delete and log.
        """

        await interaction.response.defer()
        logger.info(
            f"{interaction.user.name} used the quarantine command on {target.name}"
        )
        if not target.bot:
            if not target.guild_permissions.administrator:
                # Read on every use so changes made with /settings apply without a restart.
                verified_role = self.find_role(interaction.guild, "6")
                naughty_role = self.find_role(interaction.guild, "7")
                missing = [
                    name
                    for name, role in (
                        ("verified (role 6)", verified_role),
                        ("quarantine (role 7)", naughty_role),
                    )
                    if role is None
                ]

                if missing:
                    logger.error(
                        f"Quarantine failed: {', '.join(missing)} not found in {interaction.guild.name}."
                    )
                    await interaction.followup.send(
                        embed=embed_cant_do_that(
                            f"{target.name} was **not** quarantined: the {' and '.join(missing)}"
                            " setting does not match a role in this server. Fix it with /settings."
                        ),
                        ephemeral=True,
                    )
                else:
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

                await remove_and_log_messages(
                    self.bot,
                    interaction.guild,
                    target,
                    messages_to_remove,
                    embed_quarantine(interaction.user, target),
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
    @app_is_master_guild()
    @app_requires_permissions(ban_members=True, moderate_members=True)
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
            verified_role = self.find_role(interaction.guild, "6")
            naughty_role = self.find_role(interaction.guild, "7")
            if verified_role is None or naughty_role is None:
                await interaction.followup.send(
                    embed=embed_cant_do_that(
                        f"{target.name} was **not** released: the verified (role 6) or"
                        " quarantine (role 7) setting does not match a role in this server."
                        " Fix it with /settings."
                    ),
                    ephemeral=True,
                )
                return

            try:
                await target.add_roles(verified_role)
                await target.remove_roles(naughty_role)
                await interaction.followup.send(
                    f"{interaction.user.mention} released {target.mention} from quarantine",
                    ephemeral=True,
                )
                await send_to_mod_log(
                    self.bot,
                    embed_info(
                        f"{interaction.user.mention} released {target.mention} from quarantine"
                    ),
                )

            except Exception as notification1:
                await interaction.followup.send(
                    "There was an issue with the command.", ephemeral=True
                )
                logger.critical(
                    f"There was an error in the release command...\n{notification1}"
                )

    @quarantine.error
    async def quarantine_error(self, interaction: discord.Interaction, error):
        await respond_to_app_command_error(interaction, error, "quarantine users")

    @release.error
    async def release_error(self, interaction: discord.Interaction, error):
        await respond_to_app_command_error(
            interaction, error, "release users from quarantine"
        )


async def setup(bot) -> None:
    """
    required.
    """
    await bot.add_cog(AdminQuarantine(bot))
