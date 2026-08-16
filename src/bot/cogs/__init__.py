from __future__ import annotations

from typing import TYPE_CHECKING

from discord.ext import commands

if TYPE_CHECKING:
    from logging import Logger


__all__ = ("BaseCog",)


class BaseCog(commands.Cog):
    """The base cog which comes along with basic logging."""

    def __init__(self, logger: None | Logger = None) -> None:
        super().__init__()
        self.logger: None | Logger = logger

    async def cog_load(self) -> None:
        if self.logger:
            self.logger.info(f"Cog: {self.qualified_name} has been loaded.")

    async def cog_unload(self) -> None:
        if self.logger:
            self.logger.info(f"Cog: {self.qualified_name} has been unloaded.")
