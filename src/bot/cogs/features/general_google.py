"""
A simple sarcastic google command.
"""

import logging

from discord.ext import commands

from src.bot.cogs import BaseCog

logger = logging.getLogger(__name__)


class GeneralSarcasticGoogle(BaseCog):
    """
    # Creates a link to the Let me google that for you site.
    """

    def __init__(self, bot):
        super().__init__(logger)
        self.bot = bot

    @commands.hybrid_command(name="google")
    async def google(self, ctx, question: str):
        """
        Sarcastically googles a question.

        Parameters
        ----------
        question : str
            The question you want to "search" up.
        """
        logger.info("%s used the %s command.", ctx.author.name, ctx.command)
        await ctx.send(
            f"Here, allow me to google that one for you:"
            f"\nhttps://letmegooglethat.com/?q={question.replace(' ', '+')}"
        )


async def setup(bot):
    """
    Required.
    """
    await bot.add_cog(GeneralSarcasticGoogle(bot))
