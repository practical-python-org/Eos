import logging

from discord.ext import commands

from src.bot.cogs import BaseCog
from src.bot.cogs._checks import is_admin, is_master_guild

logger = logging.getLogger(__name__)


class CommandSync(BaseCog):
    def __init__(self, bot: commands.Bot) -> None:
        super().__init__(logger)

        self.bot = bot

    @commands.command(name="sync")
    @is_master_guild()
    @is_admin()
    async def sync(self, ctx):
        """
        Syncs the slash commands with discord.
        """

        synced = await self.bot.tree.sync()
        message = f"Synced {len(synced)} command(s)."

        logger.info(message)
        await ctx.send(message)

    @sync.error
    async def sync_command_error(self, ctx, error):
        if isinstance(error, commands.CheckFailure):
            logger.warning(
                f"{ctx.author.name} has attempted to use the {ctx.invoked_with} command, and was not allowed to do so."
            )
            await ctx.send("For one reason, or another, YOU cannot use this command.")


async def setup(bot: commands.Bot) -> None:
    await bot.add_cog(CommandSync(bot))
