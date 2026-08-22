"""
A simple monthly Yapathon, gives the yapper role to the member with the most points every month.
"""

import datetime
import logging
import os

from discord.ext import commands, tasks
from discord.utils import get

logger = logging.getLogger(__name__)


# NOTE: Currently this time is not customizable through /update_settings
TIME = datetime.time(hour=0, minute=0, second=0, tzinfo=datetime.timezone.utc)
DATE = 1


class MonthlyYapathon(commands.Cog):
    """
    This cog deals with all the stuff of monthly yapathon.
    """

    def __init__(self, bot):
        self.bot = bot
        self.yapper_role_id = self.bot.api.get_one_role("8")["role"]["value"]
        self.announcement_channel_id = self.bot.api.get_one_setting("5")["setting"][
            "value"
        ]
        self.appoint_monthly_yapper.start()

    def cog_unload(self):
        self.appoint_monthly_yapper.cancel()

    @tasks.loop(time=TIME)
    async def appoint_monthly_yapper(self):
        """
        Function that is called to appoint monthly yapper.
        """
        if datetime.datetime.now(datetime.timezone.utc).day == DATE:
            logger.info("Bot running appoint_monthly_yapper.")

            monthly_top_point_earner = self.bot.api.monthly_top_point_earner()
            current_monthly_yapper = self.bot.api.get_parameter("monthly_yapper")

            if current_monthly_yapper["status"] != "ok":
                logger.error(
                    f"Error reading the current monthly yapper: {current_monthly_yapper['message']}"
                )
                return

            if monthly_top_point_earner["status"] == "ok":
                try:
                    guild = self.bot.get_guild(int(os.getenv("MASTER_GUILD")))

                    yapper_role = get(guild.roles, id=int(self.yapper_role_id))

                    new_yapper = get(
                        guild.members,
                        id=int(monthly_top_point_earner["top_earner"]["discord_id"]),
                    )
                    current_yapper = get(
                        guild.members, id=int(current_monthly_yapper["parameter"])
                    )
                    # This condition will save this from crash when the current yapper has left the guild
                    if current_yapper is not None:
                        await current_yapper.remove_roles(yapper_role)

                    announcement_channel = get(
                        guild.channels, id=int(self.announcement_channel_id)
                    )

                    await new_yapper.add_roles(yapper_role)
                    self.bot.api.set_parameter("monthly_yapper", str(new_yapper.id))
                    await announcement_channel.send(
                        f"The winner of last month's Monthly Yapathon is {new_yapper.mention}. Keep yapping and you might be the next yapper!"
                    )

                    self.bot.api.reset_monthly_points()
                    logger.info("Successfully appointed new yapper.")
                except Exception as err:
                    logger.error(f"Error appointing new monthly yapper: {err}")
            else:
                logger.error(
                    f"Error appointing new monthly yapper: {monthly_top_point_earner['message']}"
                )

    @appoint_monthly_yapper.before_loop
    async def wait_until_bot_ready(self):
        await self.bot.wait_until_ready()


async def setup(bot):
    await bot.add_cog(MonthlyYapathon(bot))
