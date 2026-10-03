"""
Admin command for kicking a user.
"""

import datetime
import logging

import discord
from discord import app_commands

from src.bot.cogs import BaseCog
from src.bot.cogs._checks import (
    app_is_master_guild,
    app_requires_permissions,
    respond_to_app_command_error,
)
from src.bot.cogs.moderation._message_removal import (
    MAX_MESSAGES_TO_REMOVE,
    add_message_entries,
    collect_images,
    delete_messages,
    find_recent_messages,
    send_to_mod_log,
)

logger = logging.getLogger(__name__)

MAX_DELETE_MINUTES = 7 * 24 * 60  # Discord's delete_message_seconds limit


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

    @app_commands.command()
    @app_is_master_guild()
    @app_requires_permissions(ban_members=True)
    async def ban_member(
        self,
        interaction: discord.Interaction,
        target: discord.Member,
        reason: str,
        messages_to_remove: app_commands.Range[int, 0, MAX_MESSAGES_TO_REMOVE] = 0,
        delete_last_minutes: app_commands.Range[int, 0, MAX_DELETE_MINUTES] = 0,
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
            How many messages to delete and log. Optional, defaults to 0.
        delete_last_minutes : int
            Delete everything they sent in the last X minutes. Optional, defaults to 0.
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
                since = None
                if delete_last_minutes:
                    since = discord.utils.utcnow() - datetime.timedelta(
                        minutes=delete_last_minutes
                    )
                messages = await find_recent_messages(
                    interaction.guild, target, messages_to_remove, since=since
                )
                upload_limit = interaction.guild.filesize_limit
                images = await collect_images(messages, upload_limit)
                # Then we do dat ban
                await target.ban(
                    reason=f"{interaction.user.name} - {reason}",
                    delete_message_seconds=delete_last_minutes * 60,
                )
                logger.info(
                    "{%s} banned {%s}. Reason: {%s}",
                    interaction.user.name,
                    target.name,
                    reason,
                )
                await send_to_mod_log(
                    self.bot,
                    *add_message_entries(
                        embed_info(
                            f"{interaction.user.mention} banned {target.mention}"
                            f"\n**Reason:** {reason}"
                        ),
                        target,
                        messages,
                    ),
                    images=images,
                    upload_limit=upload_limit,
                )
                await delete_messages(
                    [
                        message
                        for message in messages
                        if since is None or message.created_at < since
                    ]
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
    async def ban_error(self, interaction: discord.Interaction, error):
        await respond_to_app_command_error(interaction, error, "ban users")


async def setup(bot) -> None:
    """
    required.
    """
    await bot.add_cog(AdminBan(bot))
