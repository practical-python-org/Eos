"""

This cog handles the /verify command.
It allows a user to call a dropdown that,
when an option is selected, can verify or kick the user

"""

import datetime
import logging
from typing import Literal

import discord
from discord import app_commands
from discord.ext import commands

from src.bot.cogs import BaseCog
from src.bot.cogs._checks import (
    app_is_master_guild,
    app_requires_permissions,
    respond_to_app_command_error,
)
from src.bot.cogs.moderation._message_removal import send_to_mod_log

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


VERIFICATION_PAUSED_MESSAGE = (
    "Verification is temporarily paused. Please try again later."
)
VERIFICATION_PARAMETER = "verification_enabled"


def verification_is_enabled(bot):
    cog = bot.get_cog("Verification")
    return cog is None or cog.enabled


class VerificationSelector(discord.ui.Select):
    def __init__(self, bot):
        self.bot = bot
        self.verified_role = self.bot.api.get_one_role("6")["role"]["value"]
        self.join_log = self.bot.api.get_one_log_setting("2")["log_setting"]["value"]
        self.verification_log = self.bot.api.get_one_log_setting("1")["log_setting"][
            "value"
        ]
        self.verification_channel = self.bot.api.get_one_setting("1")["setting"][
            "value"
        ]

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
            # The dropdown may have been opened before verification was paused.
            if not verification_is_enabled(self.bot):
                await interaction.response.send_message(
                    VERIFICATION_PAUSED_MESSAGE, ephemeral=True
                )
                return

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
            await interaction.response.send_message(
                "You are a robot? Nice try.", delete_after=3.0
            )
            await verification_log.send(
                f"{interaction.user.display_name} admitted to being a robot, and was kicked."
            )
            await interaction.user.kick(reason="User admitted to being a robot.")


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
        self.join_log = self.bot.api.get_one_log_setting("4")["log_setting"]["value"]
        self.verification_channel = self.bot.api.get_one_setting("1")["setting"][
            "value"
        ]
        self.verified_role = self.bot.api.get_one_role("6")["role"]["value"]
        self.enabled = self.load_enabled()

    def load_enabled(self):
        """
        Read the stored verification switch. If the API can't answer, stay
        enabled so an outage doesn't lock every new member out.
        """
        response = self.bot.api.get_parameter(VERIFICATION_PARAMETER)
        if response["status"] != "ok":
            logger.critical(
                f"Could not read {VERIFICATION_PARAMETER}; verification stays enabled."
                f" API: {response}"
            )
            return True

        enabled = response["parameter"] != "0"
        if not enabled:
            logger.warning("Verification is paused (restored from the database).")
        return enabled

    @app_commands.command()
    @app_is_master_guild()
    @app_requires_permissions(ban_members=True)
    async def verification(
        self,
        interaction: discord.Interaction,
        action: Literal["enable", "disable", "status"],
    ):
        """
        Pause or resume verification, to stop new members joining the main server.

        Parameters
        ----------
        action : str
            disable pauses verification, enable resumes it, status shows the current state.
        """
        if action == "status":
            state = "enabled" if self.enabled else "**paused**"
            await interaction.response.send_message(
                f"Verification is {state}.", ephemeral=True
            )
            return

        enabled = action == "enable"
        # Apply immediately, even if saving fails, so a raid can be stopped now.
        self.enabled = enabled
        response = self.bot.api.set_parameter(
            VERIFICATION_PARAMETER, "1" if enabled else "0"
        )
        saved = response["status"] == "ok"

        state = "enabled" if enabled else "paused"
        logger.warning(f"{interaction.user.name} {state} verification.")
        reply = f"Verification is now {'enabled' if enabled else '**paused**'}."
        if not saved:
            logger.critical(f"Could not save {VERIFICATION_PARAMETER}. API: {response}")
            reply += (
                "\n⚠️ The setting could not be saved, so it will reset to enabled"
                " if the bot restarts."
            )
        await interaction.response.send_message(reply, ephemeral=True)

        await send_to_mod_log(
            self.bot,
            discord.Embed(
                description=f"{interaction.user.mention} {state} verification.",
                color=discord.Color.green() if enabled else discord.Color.red(),
                timestamp=datetime.datetime.now(datetime.timezone.utc),
            ),
        )

    @verification.error
    async def verification_error(self, interaction: discord.Interaction, error):
        await respond_to_app_command_error(interaction, error, "change verification")

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

        elif not self.enabled:
            logger.info(f"{ctx.author.name} tried to verify while it is paused.")
            await ctx.send(VERIFICATION_PAUSED_MESSAGE, delete_after=15.0)

        else:
            if int(self.verified_role) not in [role.id for role in ctx.author.roles]:
                logger.debug(f"{ctx.author.name} is attempting to verify")
                await ctx.send(
                    "# ~ Verification ~ \n"
                    "_Before you can join the server, we need to make sure you are not a robot._\n"
                    "_Please answer the following question._",
                    view=DropdownView(self.bot),
                    delete_after=15.0,
                )
            else:
                await ctx.send("You are already verified. Go away.", delete_after=10.0)


async def setup(bot: commands.Bot) -> None:
    """boink"""
    await bot.add_cog(Verification(bot))
