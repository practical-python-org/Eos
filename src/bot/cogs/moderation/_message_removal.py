"""
Shared helpers for moderation commands that remove a member's recent messages.

Messages should always written to the moderation log before they are deleted.
"""

import asyncio
import datetime
import logging
import re
from collections import defaultdict
from io import BytesIO

import discord

logger = logging.getLogger(__name__)

MAX_MESSAGES_TO_REMOVE = 100  # Discord's bulk delete limit
HISTORY_PER_CHANNEL = 100  # How far back each channel is searched.
BULK_DELETE_MAX_AGE = datetime.timedelta(days=14)  # Discord refuses older bulk deletes.

# Discord embed limits.
EMBED_DESCRIPTION_LIMIT = 4096
EMBED_TOTAL_LIMIT = 6000  # Per embed, and across all embeds in one message.
EMBEDS_PER_MESSAGE = 10
MESSAGE_PREVIEW_LIMIT = 1024  # Longest quote shown for any one removed message.
FILES_PER_MESSAGE = 10
UNSAFE_FILENAME_CHARACTERS = re.compile(r"[^A-Za-z0-9._-]")


def _readable_channels(guild):
    """
    Every text channel and active thread the bot can read history in.
    """
    me = guild.me
    for channel in [*guild.text_channels, *guild.threads]:
        permissions = channel.permissions_for(me)
        if permissions.view_channel and permissions.read_message_history:
            yield channel


async def _channel_messages_by(channel, member):
    try:
        return [
            message
            async for message in channel.history(limit=HISTORY_PER_CHANNEL)
            if message.author.id == member.id
        ]
    except discord.HTTPException as err:
        logger.warning(f"Could not read history in {channel} -> {err}")
        return []


async def find_recent_messages(guild, member, amount, since=None):
    """
    Return the member's `amount` newest messages across all readable channels,
    newest first. With `since`, every message sent at or after it is included too.
    """
    if amount <= 0 and since is None:
        return []

    results = await asyncio.gather(
        *(
            _channel_messages_by(channel, member)
            for channel in _readable_channels(guild)
        )
    )
    messages = [message for channel_messages in results for message in channel_messages]
    messages.sort(key=lambda message: message.created_at, reverse=True)
    if since is not None:
        in_window = sum(1 for message in messages if message.created_at >= since)
        amount = max(amount, in_window)
    return messages[:amount]


def _message_header(message):
    # <t:> timestamps and <#channel> mentions only render in descriptions and
    # field values; timestamps show in each viewer's own timezone.
    sent = int(message.created_at.timestamp())
    return f"**<#{message.channel.id}>** · <t:{sent}:d> <t:{sent}:T>"


def _message_entry(message):
    """
    One removed message, as a block of embed description markdown.
    """
    header = _message_header(message)

    lines = (message.content or "*No text content*").splitlines() or [""]
    lines += [f"📎 {attachment.filename}" for attachment in message.attachments]
    quote = "\n".join(f"> {line}" for line in lines)
    if len(quote) > MESSAGE_PREVIEW_LIMIT:
        quote = quote[: MESSAGE_PREVIEW_LIMIT - 1] + "…"
    return f"{header}\n{quote}"


def add_message_entries(embed, member, messages):
    """
    Append a count and the removed messages, oldest first, to `embed`'s description.
    Returns the embeds to send: `embed`, plus continuation embeds for whatever
    would not fit within Discord's limits.
    """
    embed.description = (
        f"{embed.description or ''}\n**Messages removed:** {len(messages)}".strip()
    )
    embeds = [embed]
    for message in reversed(messages):
        entry = f"\n\n{_message_entry(message)}"
        current = embeds[-1]
        if (
            len(current.description) + len(entry) > EMBED_DESCRIPTION_LIMIT
            or len(current) + len(entry) > EMBED_TOTAL_LIMIT
        ):
            current = discord.Embed(
                title=f"Removed messages from {member} (continued)"[:256],
                description="",
                color=discord.Color.red(),
            )
            embeds.append(current)
            entry = entry.lstrip("\n")
        current.description += entry
    return embeds


async def collect_images(messages, upload_limit):
    """
    Download every image attached to the messages, and wrap each
    one in an embed that displays it. Must run before the messages are deleted:
    Discord purges the CDN copy very quickly.

    Returns (embed, file, size) tuples for send_to_mod_log.
    """
    images = []
    for message in reversed(messages):
        for attachment in message.attachments:
            if not (attachment.content_type or "").startswith("image/"):
                continue
            if attachment.size > upload_limit:
                logger.info(
                    f"Image {attachment.filename} is too large to re-upload "
                    f"({attachment.size} > {upload_limit}). Skipping."
                )
                continue
            try:
                data = await attachment.read()
            except discord.HTTPException as err:
                logger.warning(f"Could not fetch image {attachment.filename} -> {err}")
                continue

            safe_name = UNSAFE_FILENAME_CHARACTERS.sub("_", attachment.filename)
            file = discord.File(BytesIO(data), filename=f"{len(images)}_{safe_name}")
            embed = discord.Embed(
                description=f"{_message_header(message)}\n📎 {attachment.filename}"[
                    :EMBED_DESCRIPTION_LIMIT
                ],
                color=discord.Color.red(),
            )
            embed.set_image(url=f"attachment://{file.filename}")
            images.append((embed, file, len(data)))
    return images


def batch_posts(items, upload_limit):
    """
    Group (embed, file, size) items into batches that fit in a single Discord message.
    """
    batch, characters, uploaded = [], 0, 0
    for embed, file, size in items:
        files_in_batch = sum(1 for _, batch_file, _ in batch if batch_file)
        if batch and (
            len(batch) >= EMBEDS_PER_MESSAGE
            or characters + len(embed) > EMBED_TOTAL_LIMIT
            or (file and files_in_batch >= FILES_PER_MESSAGE)
            or uploaded + size > upload_limit
        ):
            yield batch
            batch, characters, uploaded = [], 0, 0
        batch.append((embed, file, size))
        characters += len(embed)
        uploaded += size
    if batch:
        yield batch


async def send_to_mod_log(bot, *embeds, images=(), upload_limit=0):
    """
    Post embeds to the moderation log.
    `images` are (embed, file, size) tuples from collect_images.

    """
    mod_log_setting = bot.api.get_one_log_setting("5")  # mod_log
    if mod_log_setting["status"] != "ok":
        logger.critical(f"API error. API response not ok. -> {mod_log_setting}")
        return
    if mod_log_setting["log_setting"]["value"] == "0":
        logger.warning("Moderation log is disabled; removed messages were not logged.")
        return

    try:
        channel = await bot.fetch_channel(mod_log_setting["log_setting"]["value"])
        items = [(embed, None, 0) for embed in embeds] + list(images)
        for batch in batch_posts(items, upload_limit):
            await channel.send(
                embeds=[embed for embed, _, _ in batch],
                files=[file for _, file, _ in batch if file],
            )
    except discord.HTTPException:
        logger.exception("Failed to post to the moderation log.")


async def delete_messages(messages):
    """
    Delete the messages, bulk-deleting per channel where Discord allows it.
    Returns how many were deleted.
    """
    by_channel = defaultdict(list)
    for message in messages:
        by_channel[message.channel].append(message)

    cutoff = discord.utils.utcnow() - BULK_DELETE_MAX_AGE
    deleted = 0
    for channel, channel_messages in by_channel.items():
        recent = [
            message for message in channel_messages if message.created_at > cutoff
        ]
        old = [message for message in channel_messages if message.created_at <= cutoff]

        if len(recent) > 1:
            try:
                await channel.delete_messages(recent)
                deleted += len(recent)
                recent = []
            except discord.HTTPException as err:
                logger.warning(
                    f"Bulk delete failed in {channel}, falling back -> {err}"
                )

        for message in [*recent, *old]:
            try:
                await message.delete()
                deleted += 1
            except discord.HTTPException as err:
                # NotFound and Forbidden are subclasses; keep deleting the rest.
                logger.warning(
                    f"Could not delete message {message.id} in {channel} -> {err}"
                )

    return deleted


async def remove_and_log_messages(bot, guild, member, amount, embed):
    """
    Find the member's last `amount` messages, log them to the moderation log
    with `embed`, then delete them. Returns how many were deleted.
    """
    messages = await find_recent_messages(guild, member, amount)
    upload_limit = guild.filesize_limit
    images = await collect_images(messages, upload_limit)

    await send_to_mod_log(
        bot,
        *add_message_entries(embed, member, messages),
        images=images,
        upload_limit=upload_limit,
    )

    return await delete_messages(messages)
