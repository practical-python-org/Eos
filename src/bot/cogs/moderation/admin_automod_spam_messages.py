import datetime
import hashlib
import logging
import os

import discord
import discord.errors
from discord.ext import commands

logger = logging.getLogger(__name__)
DRAIN_SECONDS_PER_TOKEN = 60 * 20  # 1 token evaporated every 20 minutes
WARN_THRESHOLD = 3
QUARANTINE_THRESHOLD = 4


def embed_spammer_warn(channel1, channel2):
    """
    Embedding regular warn for detected spam messages.
    """
    embed = discord.Embed(
        title="Warning",
        description=f"When you send the same message **{QUARANTINE_THRESHOLD} times**, you get the quarantine.\n",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    report = f"Detected the same message in {channel1.mention} and {channel2.mention}"
    embed.add_field(name="What happened?", value=report, inline=True)
    embed.add_field(
        name="What should you do?",
        value="Don't panic, and be patient."
        " Someone will answer you as soon as they can.",
        inline=True,
    )
    embed.set_footer(
        text="In the meantime... Maybe make sure your question contains your code, as well as the output."
    )
    return embed


def embed_spammer_quarantine(spammer, message_to_report=None, file_url=None):
    """
    Embedding quarantine warn for detected spam messages.
    """
    embed = discord.Embed(
        title="Firewall has been triggered",
        description=f"When you send the same message **{QUARANTINE_THRESHOLD} times**, {spammer.mention}, you get the quarantine."
        f" Wait for the staff to come let you out.",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )
    if message_to_report:
        embed.add_field(name="Message:", value=message_to_report, inline=True)
    if file_url:
        embed.add_field(name="Image:", value=file_url, inline=True)
    return embed


class ModerationSpamMessages(commands.Cog):
    """
    A cog for detecting and moderating spam messages in Discord channels.

    This cog monitors user messages to identify repeated messages sent in quick succession.
    Upon detecting repeated messages, it takes moderation actions such as warning or
    quarantining the user and deleting spam messages.
    """

    # TODO: Images currently get entered into memory as a blank string. We can use the message.attachment to fix that.
    def __init__(self, bot):
        """
        Initializes the cog with the bot instance.

        Args:
            bot (commands.Bot): The bot instance to which this cog is added.
        """
        self.bot = bot
        self.records = {}
        self.warn_message = "Hello there!"

    @commands.Cog.listener()
    async def on_message(self, message):
        """
        Listens for incoming messages and checks for repeated content.

        Args:
            message (discord.Message): The message object representing the user's message.
        """
        if message.author.bot or isinstance(message.channel, discord.DMChannel):
            # Don't track bot, or DM's
            return
        if message.author.guild_permissions.ban_members:
            # Don't track the staff man.
            return
        if message.content.startswith(os.getenv("PREFIX")):
            # Don't track bot commands
            return

        author_id = message.author.id
        content = message.content or ""
        attachment = message.attachments[0] if message.attachments else None
        if attachment:
            content += hashlib.sha256(
                f"|{attachment.filename}|{attachment.size}|{attachment.content_type}".encode()
            ).hexdigest()

        now = datetime.datetime.now(datetime.timezone.utc)
        record = self.records.get(
            author_id,
            {
                "last_message": None,
                "occurrence": 0.0,
                "last_update": now,
                "stage": 0,
                "messages": [],
            },
        )

        # Drain Leaky Bucket
        elapsed = (now - record["last_update"]).total_seconds()
        record["occurrence"] = max(
            0.0, record["occurrence"] - (elapsed / DRAIN_SECONDS_PER_TOKEN)
        )
        record["last_update"] = now

        if record["occurrence"] < WARN_THRESHOLD:
            record["stage"] = 0

        if record["occurrence"] <= 0:
            record["last_message"] = None
            record["messages"] = []
            record["stage"] = 0

        # Check if the current message is the same as the last message
        if record["last_message"] == content:
            record["occurrence"] += 1
            logger.debug(
                "%s has sent a double message in %s",
                message.author.name,
                message.channel.name,
            )

            record["messages"].append(
                {
                    "message_id": message.id,
                    "channel_id": message.channel.id,
                    "file_name": attachment.filename
                    if attachment and not message.content
                    else None,
                    "file_url": attachment.url
                    if attachment and not message.content
                    else None,
                }
            )

            self.records[author_id] = record
            await self.handle_repeated_messages(message, record)
        else:
            self.records[author_id] = {
                "last_message": content,
                "occurrence": 1.0,
                "last_update": now,
                "stage": 0,
                "messages": [
                    {
                        "message_id": message.id,
                        "channel_id": message.channel.id,
                        "file_name": attachment.filename
                        if attachment and not message.content
                        else None,
                        "file_url": attachment.url
                        if attachment and not message.content
                        else None,
                    }
                ],
            }

    async def handle_repeated_messages(self, message, record):
        """
        Handles actions based on the number of repeated messages.

        Args:
            message (discord.Message): The message object triggering this action.
            record (dict): The user's message record containing repeated messages.
        """

        # Number of times user sent the same message
        count = record["occurrence"]
        error_rate = 0.5

        # Quarantine eligible user
        if count >= (QUARANTINE_THRESHOLD - error_rate) and record["stage"] < 3:
            record["stage"] = 3
            logger.info(
                f"{message.author.name} was quarantined (bucket >= {QUARANTINE_THRESHOLD}). Message: {message.content}"
            )
            await self.quarantine_user(message, record)

        # Warn eligible user
        elif count >= (WARN_THRESHOLD - error_rate) and record["stage"] < 2:
            record["stage"] = 2
            logger.info(
                f"{message.author.name} was timed out (bucket >= {WARN_THRESHOLD}). Message: {message.content}"
            )
            await self.warn_user(message, record)

    async def warn_user(self, message, record):
        """
        Warns the user for sending repeated messages.

        Args:
            message (discord.Message): The triggering message object.
            record (dict): The user's message record.
        """
        try:
            first_channel = await self.bot.fetch_channel(
                record["messages"][0]["channel_id"]
            )
            second_channel = await self.bot.fetch_channel(
                record["messages"][1]["channel_id"]
            )

            self.warn_message = await message.author.send(
                embed=embed_spammer_warn(first_channel, second_channel)
            )
            logger.debug(
                "%s was sent a DM about their double message.", message.author.name
            )
        except discord.errors.Forbidden:
            first_channel = await self.bot.fetch_channel(
                record["messages"][0]["channel_id"]
            )
            await message.reply(
                f"{message.author.mention}, Please do not post the same message in multiple channels.\n"
                f"You already posted this in {first_channel.mention}"
            )
        finally:
            fifteen_seconds = datetime.datetime.now().astimezone() + datetime.timedelta(
                seconds=15
            )
            await message.author.timeout(
                fifteen_seconds, reason="Sending the same message multiple times."
            )

    async def quarantine_user(self, message, record):
        """
        Quarantines the user for sending three repeated messages and deletes the spam messages.

        Args:
            message (discord.Message): The triggering message object.
            record (dict): The user's message record.
        """
        author_id = message.author.id
        try:
            naughty_role = await message.guild.fetch_role(
                self.bot.api.get_one_role("7")["role"]["value"]
            )
            verified_role = await message.guild.fetch_role(
                self.bot.api.get_one_role("6")["role"]["value"]
            )

            quarantine_channel = self.bot.api.get_one_setting("2")["setting"]["value"]
            quarantine_channel = await self.bot.fetch_channel(quarantine_channel)
            thirty_seconds = datetime.datetime.now().astimezone() + datetime.timedelta(
                seconds=30
            )

            await message.author.timeout(
                thirty_seconds, reason="Sending the same message multiple times."
            )
            await message.author.remove_roles(verified_role)
            await message.author.add_roles(naughty_role)

            await quarantine_channel.send(
                embed=embed_spammer_quarantine(
                    message.author, message.content, record["messages"][-1]["file_url"]
                )
            )

            for msg in record["messages"]:
                channel = await self.bot.fetch_channel(msg["channel_id"])
                msg_to_delete = await channel.fetch_message(msg["message_id"])
                await msg_to_delete.delete()

        finally:
            self.records[author_id] = {
                "last_message": None,
                "occurrence": 0.0,
                "last_update": datetime.datetime.now().astimezone(),
                "stage": 0,
                "messages": [],
            }


async def setup(bot) -> None:
    """
    Adds the ModerationSpamMessages cog to the bot.

    Args:
        bot (commands.Bot): The bot instance to which the cog is added.
    """
    await bot.add_cog(ModerationSpamMessages(bot))
