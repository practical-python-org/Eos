"""
Command that links to the official server site.
"""

import logging

from discord import Interaction, app_commands
from discord.ext import commands

from ..constants import WEBPAGE_CHOICES

logger = logging.getLogger(__name__)

SITE_LINK: str = "https://www.practicalpython.org/"


class LinkTo(commands.Cog):
    """Creates a link to the server website or one of its pages."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(description="Links to the official server site.")
    @app_commands.describe(page="Site page to link to.")
    @app_commands.choices(page=WEBPAGE_CHOICES)
    async def link_to(
        self, interaction: Interaction, *, page: app_commands.Choice[str] | None = None
    ) -> None:
        """
        Send message with desired link.

        Parameters
        ----------
        page : app_commands.Choice[str] | None
            Selected site page or the homepage as default.
        """
        logger.info(
            "%s used the %s command.", interaction.user.name, interaction.command.name
        )

        page = page or WEBPAGE_CHOICES[0]
        await interaction.response.send_message(f"{page.name}: {SITE_LINK}{page.value}")


async def setup(bot: commands.Bot) -> None:
    """Required."""
    await bot.add_cog(LinkTo(bot))
