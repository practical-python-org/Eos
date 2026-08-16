"""
Logging for role changes. Logs the user who did the changing, the target user and the role.
"""

import datetime
import logging
import os

import discord
from discord.ext import commands

from src.bot.cogs import BaseCog

logger = logging.getLogger(__name__)


def embed_role_add(some_member, member_who_did_action, role_obj):
    """
    Embedding for user kick alerts.
    """
    embed = discord.Embed(
        title="",
        description=f"<@{member_who_did_action.id}> added <@&{role_obj.id}> to <@{some_member.id}>",
        color=discord.Color.green(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    return embed


def embed_role_remove(some_member, member_who_did_action, role_obj):
    """
    Embedding for user kick alerts.
    """
    embed = discord.Embed(
        title="",
        description=f"<@{member_who_did_action.id}> removed <@&{role_obj.id}> from <@{some_member.id}>",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    return embed


class LoggingRoles(BaseCog):
    """
    Simple listener to on_member_update
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot
        self.mod_log = self.bot.api.get_one_log_setting("5")  # mod_log

    @commands.Cog.listener()
    async def on_member_update(self, before, after):
        """
        Checks what roles were changed, and logs it in the log channel.
        Can be quite spammy.
        """
        if before.guild.id != int(os.getenv("MASTER_GUILD")) or before.guild.id is None:
            logger.warning(
                "on_member_update fired, but not in master guild. Ignoring event."
            )
            return

        audit_log = [entry async for entry in before.guild.audit_logs(limit=1)][0]

        if str(audit_log.action) == "AuditLogAction.member_role_update":
            target_member = audit_log.target
            responsible_member = audit_log.user

            changed_roles = []
            if self.mod_log[0]["status"] == "ok":
                if self.mod_log[0]["logging"][2] == "0":
                    logger.debug(
                        f"log was triggered, but logging is disabled. API: {self.mod_log}"
                    )
                    return
                logs_channel = await self.bot.fetch_channel(
                    self.mod_log[0]["logging"][2]
                )

                if len(before.roles) > len(after.roles):
                    for role in before.roles:
                        if role not in after.roles:
                            changed_roles.append(role)
                    for item in changed_roles:
                        embed = embed_role_remove(
                            target_member, responsible_member, item
                        )
                        await logs_channel.send(embed=embed)

                elif len(before.roles) < len(after.roles):
                    for role in after.roles:
                        if role not in before.roles:
                            changed_roles.append(role)
                    for item in changed_roles:
                        embed = embed_role_add(target_member, responsible_member, item)
                        await logs_channel.send(embed=embed)
            else:
                logger.critical(f"API error. API response not ok. -> {self.mod_log}")


async def setup(bot: commands.Bot) -> None:
    """boink"""
    await bot.add_cog(LoggingRoles(bot))
