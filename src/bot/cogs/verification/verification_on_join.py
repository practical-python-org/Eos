"""
This is a handler that adds a Need Approval role and sends the user a message.
"""

import logging
import os
from asyncio import sleep

import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


class LoggingVerification(commands.Cog):
    """
    Handled with a role, and a message.
    the role limits the user to one channel, with a verify button.
    If the user does not push the button within one hour, they are auto-kicked.
    """

    def __init__(self, bot):
        self.bot = bot
        self.verification_channel = self.bot.api.get_one_setting("1")["setting"][
            "value"
        ]
        self.verification_log = self.bot.api.get_one_log_setting("1")["log_setting"][
            "value"
        ]
        self.join_log = self.bot.api.get_one_log_setting("2")["log_setting"]["value"]
        self.verified_role = self.bot.api.get_one_role("6")["role"]["value"]
        self.naughty_role = self.bot.api.get_one_role("7")["role"]["value"]

    async def log_unverified_join(self, member, logging_channel):
        await logging_channel.send(f"<@{member.id}> joined, but has not verified.")

    async def send_welcome_message(self, guild, member):
        verification_channel = self.bot.get_channel(int(self.verification_channel))
        welcome_message = f"""
            Hi there, {member.mention}
            I'm Zorak, the moderator of {guild.name}.

            We are very happy that you have decided to join us.
            Before you are allowed to chat, you need to verify that you are NOT a bot.\n
            Dont worry... it's easy.
            Just go to {verification_channel.mention if verification_channel else "the verification channel"}
            and use the **{os.getenv("PREFIX")}verify** command.

            After you do, all of {guild.name} is available to you. Have a great time :-)
            """
        # Send Welcome Message
        try:
            await member.send(welcome_message)
        except discord.errors.Forbidden:
            logger.debug(f"{member.name} cannot be sent a DM.")

    async def kick_if_not_verified(self, member, time_to_kick, logging_channel):
        await sleep(time_to_kick)

        if all(
            x not in [role.id for role in member.roles]
            for x in (self.verified_role, self.naughty_role)
        ):
            await logging_channel.send(
                f"{member.mention} did not verify after {int((time_to_kick / 3600))} hour/s, auto-removed."
            )
            await member.kick(reason="Did not verify.")

    @commands.Cog.listener()
    async def on_member_join(self, member: discord.Member):
        guild = member.guild
        guild_id = member.guild.id

        if guild_id != int(os.getenv("MASTER_GUILD")):
            logger.warning(
                "on_member_join fired, but not in master guild. Ignoring event."
            )
            return

        verification_log = await self.bot.fetch_channel(self.verification_log)

        await self.log_unverified_join(member, verification_log)
        await self.send_welcome_message(guild, member)
        # TODO: fix the kick if unverified feature.
        #  Is being called even though it should not be.
        # await self.kick_if_not_verified(member, 3600, verification_log)

    # @commands.Cog.listener()
    # async def on_message(self, message):
    #     """
    #     Keep verification clean again
    #     """
    #     if message.author.guild.id != int(os.getenv("MASTER_GUILD")):
    #         logger.warning("on_message in verification fired, but not in master guild. Ignoring event.")
    #         return
    #
    #     if message.channel.id == int(self.verification_channel):
    #         if not message.author.bot:
    #             if f"{os.getenv('PREFIX')}verify" == message.content:  # keep it exact
    #                 # user is doing it right, and the verification_dropdown is triggered
    #                 logger.debug(f"{message.author.name} started verification.")
    #                 await sleep(3)
    #                 await message.delete()  # cleanup correct verification calls
    #                 return
    #             else:  # this covers any other message in the channel.
    #                 await message.delete()  # delete the user's incorrect message
    #                 bot_message = await message.channel.send(
    #                     f"You need to use the **{os.getenv('PREFIX')}verify** command.")
    #
    #                 logs_channel = await self.bot.fetch_channel(self.verification_log)
    #                 await logs_channel.send(
    #                     f"{message.author} is failing at life in {self.bot.get_channel(self.verification_channel)}")
    #
    #                 await sleep(8)
    #                 bot_message.delete()  # remove the message to correct people after 8? seconds


async def setup(bot: commands.Bot) -> None:
    """boink"""
    await bot.add_cog(LoggingVerification(bot))
