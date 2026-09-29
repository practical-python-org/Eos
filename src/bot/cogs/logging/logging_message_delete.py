"""
Logging for message deletes
"""

import datetime
import logging
import os
from io import BytesIO

import discord
from discord.ext import commands

from src.bot.cogs import BaseCog
from src.bot.cogs.moderation._message_removal import (
    UNSAFE_FILENAME_CHARACTERS,
    batch_posts,
)

logger = logging.getLogger(__name__)


def embed_message_delete(
    some_member, some_message, some_moderator=None, unrecovered=()
):
    """
    Embedding for user message deletion alerts.
    """
    embed = discord.Embed(
        title="<:red_circle:1043616578744357085> Deleted Message",
        description=f"{some_moderator.mention if some_moderator is not None else some_member.mention} deleted a message"
        f"\nIn {some_message.channel}\n"
        f"Message author: {some_member.mention}",
        color=discord.Color.red(),
        timestamp=datetime.datetime.now(datetime.timezone.utc),
    )

    embed.set_thumbnail(
        url=some_member.avatar if some_moderator is None else some_moderator.avatar
        # the person who DELETED the message
    )
    if len(some_message.content) > 1020:
        the_message = some_message.content[0:1020] + "..."
    else:
        the_message = some_message.content

    if not the_message:
        the_message = "*No text content*"
    embed.add_field(name="Message: ", value=the_message, inline=True)

    if some_message.attachments:
        embed.add_field(
            name="Attachments: ",
            value="\n".join(
                f"{attachment.filename} *(could not be recovered)*"
                if attachment.filename in unrecovered
                else attachment.filename
                for attachment in some_message.attachments
            )[0:1020],
            inline=False,
        )

    return embed


class LoggingMessageDelete(BaseCog):
    """
    Simple listener to on_message_delete
    then checks the audit log for exact details
    """

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot
        setting = self.bot.api.get_one_setting("3")  # Staff Channel ID
        if setting["status"] != "ok":
            raise RuntimeError("Failed to fetch staff channel setting from API.")
        self.staff_channel = setting["setting"]["value"]

        setting = self.bot.api.get_one_setting("1")  # Verification Channel ID
        if setting["status"] != "ok":
            raise RuntimeError("Failed to fetch verification channel setting from API.")
        self.verification_channel = setting["setting"]["value"]
        self.verification_command = f"{os.getenv('PREFIX')}verify"

        self.chat_log = self.bot.api.get_one_log_setting("3")  # chat_log
        if self.chat_log["status"] != "ok":
            raise RuntimeError("Failed to fetch chat log setting from API.")

    async def read_deleted_attachment(self, attachment: discord.Attachment) -> bytes:
        """
        Download an attachment whose message was just deleted.

        The direct CDN URL is purged immediately after a delete so we can try Discord's
        media proxy first
        """
        try:
            return await attachment.read(use_cached=True)
        except discord.HTTPException as err:
            logger.debug(
                f"Proxy fetch failed for {attachment.filename}, trying CDN -> {err}"
            )
            return await attachment.read()

    async def collect_image_files(self, message):
        """
        Re-download every image attachment on the deleted message.

        Returns (files, unrecovered): (file, size) pairs for the images we got,
        and the filenames of images we could not fetch or re-upload.
        """
        size_limit = message.guild.filesize_limit
        files = []
        unrecovered = []
        for attachment in message.attachments:
            if not (
                attachment.content_type and attachment.content_type.startswith("image/")
            ):
                continue
            if attachment.size > size_limit:
                logger.debug(
                    f"Image attachment {attachment.filename} is too large to re-upload "
                    f"({attachment.size} > {size_limit}). Skipping."
                )
                unrecovered.append(attachment.filename)
                continue
            logger.debug(
                f"Image attachment detected in deleted message, "
                f"{attachment.filename}:{attachment.url}"
            )
            try:
                data = await self.read_deleted_attachment(attachment)
            except discord.HTTPException as err:
                logger.warning(
                    f"Could not fetch deleted attachment {attachment.filename} -> {err}"
                )
                unrecovered.append(attachment.filename)
                continue

            # Prefixed so two images with the same name can't collide in one post.
            safe_name = UNSAFE_FILENAME_CHARACTERS.sub("_", attachment.filename)
            file = discord.File(BytesIO(data), filename=f"{len(files)}_{safe_name}")
            files.append((file, len(data)))
        return files, unrecovered

    async def send_log(self, logs_channel, embed, image_files, upload_limit):
        """
        Send the log embed with the recovered images displayed inside embeds:
        the first in the log embed itself, the rest in their own embeds.
        """
        items = [(embed, None, 0)]
        for index, (file, size) in enumerate(image_files):
            image_embed = embed if index == 0 else discord.Embed(color=embed.color)
            image_embed.set_image(url=f"attachment://{file.filename}")
            if index == 0:
                items[0] = (embed, file, size)
            else:
                items.append((image_embed, file, size))

        for batch in batch_posts(items, upload_limit):
            await logs_channel.send(
                embeds=[item_embed for item_embed, _, _ in batch],
                files=[file for _, file, _ in batch if file],
            )

    @commands.Cog.listener()
    async def on_message_delete(self, message) -> None:
        """
        If a mod deletes, take the audit log event. If a user deletes, handle it normally.
        """
        if message.guild is None:
            logger.debug(">> on_message_delete fired in DMs. Ignoring event.")
            return

        if message.guild.id != int(os.getenv("MASTER_GUILD", 0)):
            logger.warning(
                ">> on_message_delete fired, but not in master guild. Ignoring event."
            )
            return

        if message.channel.id == int(self.staff_channel):
            logger.debug("Message delete in staff channel was ignored.")
            return

        if message.channel.id == int(self.verification_channel) and (
            message.author.bot or message.content == self.verification_command
        ):
            logger.debug("Message from verification process was ignored.")
            return

        if self.chat_log["status"] == "ok":
            if self.chat_log["log_setting"]["value"] == "0":
                logger.debug(
                    f"log was triggered, but logging is disabled. API: {self.chat_log}"
                )
                return

            image_files, unrecovered = await self.collect_image_files(message)

            audit_log = [entry async for entry in message.guild.audit_logs(limit=1)][0]
            logs_channel = await self.bot.fetch_channel(
                self.chat_log["log_setting"]["value"]
            )

            if str(audit_log.action) == "AuditLogAction.message_delete":
                # Then a moderator deleted a message.
                embed = embed_message_delete(
                    audit_log.target, message, audit_log.user, unrecovered
                )
            else:
                # Otherwise, the author deleted it.
                embed = embed_message_delete(
                    message.author, message, unrecovered=unrecovered
                )

            await self.send_log(
                logs_channel, embed, image_files, message.guild.filesize_limit
            )
        else:
            logger.critical(f"API error. API response not ok. -> {self.chat_log}")


async def setup(bot: commands.Bot) -> None:
    """boink"""
    await bot.add_cog(LoggingMessageDelete(bot))
