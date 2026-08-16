"""

This cog handles the /verify command.
It allows a user to call a dropdown that,
when an option is selected, can verify or kick the user

"""

import datetime
import logging
from time import sleep

import discord
from discord.ext import commands

from src.bot.cogs import BaseCog

logger = logging.getLogger(__name__)


def embed_verified_success(name, amount):
    """
    Embedding for user verification success, and therefore a join
    """
    embed = discord.Embed(
        title="",
        description=f"{name}, human number {amount} has joined.",
        color=discord.Color.dark_green(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )

    return embed


class VerificationSelector(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        self.verified_role = self.bot.api.get_one_role("6")[0]["roles"][2]
        self.join_log = self.bot.api.get_one_log_setting("2")[0]["logging"][2]
        self.verification_log = self.bot.api.get_one_log_setting("1")[0]["logging"][2]
        self.verification_channel = self.bot.api.get_one_setting("1")[0]["setting"][2]

        self.robot = [
            discord.SelectOption(
                label="I'm a robot.",
                description="I am definitely, 100% a robot.",
                emoji="🔴",
                value=str(x),
            )
            for x in range(4)
        ]
        self.not_a_robot = [
            discord.SelectOption(
                label="I'm not a robot! Verify me!",
                description="Human after all.",
                emoji="🟢",
                value="not_robot",
            )
        ]

        options = self.robot + self.not_a_robot

        # The placeholder is what will be shown when no option is chosen
        # The min and max values indicate we can only pick one of the three options
        # The options parameter defines the dropdown options. We defined this above
        super().__init__(
            placeholder="Choose something.", min_values=1, max_values=1, options=options
        )

    async def callback(self, interaction: discord.Interaction):
        verification_log = self.bot.get_channel(int(self.verification_log))

        if self.values[0] == "not_robot":
            you_win = interaction.guild.get_role(int(self.verified_role))
            join_log = await self.bot.fetch_channel(self.join_log)
            try:
                await interaction.user.add_roles(you_win)
                await join_log.send(
                    embed=embed_verified_success(
                        interaction.user.display_name, interaction.guild.member_count
                    )
                )
                logger.info(f"{interaction.user.display_name} has verified!")
                await interaction.response.defer()

            except AttributeError as no_role_set:
                await verification_log.send(
                    f"{interaction.user.display_name} is trying to verify, but there is no "
                    f"verification role set!"
                )
                logger.critical(no_role_set)
                logger.critical(
                    "Someone is verifying, but there is no verification role set!"
                )
        else:
            msg = await interaction.response.send_message("You are a robot? Nice try.")
            await verification_log.send(
                f"{interaction.user.display_name} admitted to being a robot, and was kicked. "
            )
            sleep(3)
            await interaction.user.kick(reason="User admitted to being a robot.")
            await msg.delete()


class DropdownView(discord.ui.View):
    def __init__(self, bot):
        super().__init__()
        self.add_item(VerificationSelector(bot))


class Verification(BaseCog):
    """
    This is the class that defines the actual slash command.
    It uses the view above to execute actual logic.
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot  # Passed in from main.py
        self.join_log = self.bot.api.get_one_log_setting("4")[0]["logging"][2]
        self.verification_channel = self.bot.api.get_one_setting("1")[0]["setting"][2]
        self.verified_role = self.bot.api.get_one_role("6")[0]["roles"][2]

    @commands.command()
    async def verify(self, ctx):
        """Command to verify yourself."""

        if isinstance(ctx.channel, discord.DMChannel):
            verification_channel = self.bot.get_channel(int(self.verification_channel))
            await ctx.send(
                f"You need to use the command in the "
                f"{verification_channel.mention if verification_channel else 'verification'} channel."
            )
            return

        else:
            if self.verified_role not in [role.id for role in ctx.author.roles]:
                logger.debug(f"{ctx.author.name} is attempting to verify")
                await ctx.send(
                    "# ~ Verification ~ \n"
                    "_Before you can join the server, we need to make sure you are not a robot._\n"
                    "_Please answer the following question._",
                    view=DropdownView(self.bot),
                    delete_after=15.0,
                )
            else:
                await ctx.send("You are already verified. Go away.")


async def setup(bot: commands.Bot) -> None:
    """boink"""
    await bot.add_cog(Verification(bot))
