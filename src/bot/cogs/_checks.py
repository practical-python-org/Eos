import logging
import os

import discord
from discord import app_commands
from discord.ext import commands

logger = logging.getLogger(__name__)


def is_admin():
    async def predicate(ctx):
        return ctx.author.guild_permissions.administrator

    return commands.check(predicate)


def is_moderator():
    async def predicate(ctx):
        return ctx.author.guild_permissions.ban_members

    return commands.check(predicate)


def is_master_guild():
    async def predicate(ctx):
        master_guild_id = int(os.getenv("MASTER_GUILD"))
        return ctx.guild and ctx.guild.id == master_guild_id

    return commands.check(predicate)


def app_is_master_guild():
    async def predicate(interaction: discord.Interaction):
        master_guild_id = int(os.getenv("MASTER_GUILD"))
        return interaction.guild is not None and interaction.guild.id == master_guild_id

    return app_commands.check(predicate)


def app_requires_permissions(**permissions):
    """
    Require guild permissions to run a slash command, and hide it by default
    from members who lack them.
    """

    def decorator(func):
        func = app_commands.checks.has_permissions(**permissions)(func)
        func = app_commands.default_permissions(**permissions)(func)
        return app_commands.guild_only()(func)

    return decorator


async def respond_to_app_command_error(interaction: discord.Interaction, error, action):
    """
    Tell the user why a slash command was refused. `action` completes
    "you don't have permission to ...".
    """
    if not isinstance(error, app_commands.CheckFailure):
        return

    logger.warning(f"{interaction.user} tried to {action} without permission.")
    message = f"{interaction.user.mention}, you don't have permission to {action}."
    if interaction.response.is_done():
        await interaction.followup.send(message, ephemeral=True)
    else:
        await interaction.response.send_message(message, ephemeral=True)
