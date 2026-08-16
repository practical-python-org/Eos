"""
This cog allows us to create tickets.
"""

import logging

import discord
from discord import app_commands
from discord.ext import commands

from src.bot.cogs import BaseCog

logger = logging.getLogger(__name__)


class AddTicketButton(BaseCog):
    """
    This is the slash command that sends our UI element.
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot

    @app_commands.command(description="Make a ticket and contact the Staff.")
    async def ticket(self, interaction: discord.Interaction):
        """
        A simple command with a view.
        """

        logger.info(
            "%s used the %s command.", interaction.user.name, interaction.command.name
        )
        await interaction.response.defer()

        await interaction.followup.send(
            "Do you need help, or do you have a question for the Staff?",
            view=MakeATicket(self.bot),
            ephemeral=True,
        )


class MakeATicket(discord.ui.View):
    """
    A UI component that sends a button, which does other things.
    """

    def __init__(self, bot, *, timeout=None):
        super().__init__(timeout=timeout)
        self.bot = bot

    @discord.ui.button(label="Open a support Ticket", style=discord.ButtonStyle.primary)
    async def button_callback(self, interaction, button):
        """
        The callback on the button, or... what happens on click.
        """
        await interaction.response.defer()
        button.label = "Ticket Created!"
        button.disabled = True
        await interaction.edit_original_response(view=self)

        support = (
            interaction.channel
        )  # TODO: guild specific settings for a support channel
        staff = interaction.guild.get_role(
            self.bot.api.get_one_role("3")[0]["roles"][2]
        )  # Staff

        ticket = await support.create_thread(
            name=f"[Ticket] - {interaction.user}",
            message=None,
            auto_archive_duration=4320,
            type=discord.ChannelType.private_thread,
            reason=None,
        )

        for person in interaction.guild.members:
            if staff in person.roles:
                await ticket.add_user(person)

        await ticket.add_user(interaction.user)
        await interaction.delete_original_response()
        await ticket.send(
            f"**{interaction.user.mention}, we have received your ticket.**"
        )
        await ticket.send("To better help you, please describe your issue.")


async def setup(bot: commands.Bot) -> None:
    """boink"""
    await bot.add_cog(AddTicketButton(bot))
