"""
Logging for message deletes
"""
from importlib.resources import files
from io import BytesIO
import os
import logging
import datetime
import discord
from discord.ext import commands

logger = logging.getLogger(__name__)


def embed_message_delete(some_member, some_message, some_moderator=None):
    """
    Embedding for user message deletion alerts.
    """
    embed = discord.Embed(
        title=f'<:red_circle:1043616578744357085> Deleted Message'
        ,
        description=f'{some_moderator.mention if some_moderator is not None else some_member.mention} deleted a message'
                    f'\nIn {some_message.channel}\n'
                    f'Message author: {some_member.mention}'
        , color=discord.Color.red()
        , timestamp=datetime.datetime.now(datetime.timezone.utc)
    )

    embed.set_thumbnail(
        url=some_member.avatar if some_moderator is None else some_moderator.avatar
        # the person who DELETED the message
    )
    if len(some_message.content) > 1020:
        the_message = some_message.content[0:1020] + '...'
    else:
        the_message = some_message.content
    if len(the_message) == 0:
        the_message = "*No text content*"
    else: 
        embed.add_field(
            name='Message: '
            , value=the_message
            , inline=True
        )
        
    if some_message.attachments:
        embed.add_field(
            name='Attachments: '
            , value='\n'.join([attachment.url for attachment in some_message.attachments])
            , inline=False
        )

    return embed


class LoggingMessageDelete(commands.Cog):
    """
    Simple listener to on_message_delete
    then checks the audit log for exact details
    """

    def __init__(self, bot):
        self.bot = bot
        setting = self.bot.api.get_one_setting('3')
        
        if setting['status'] != 'ok':
            raise RuntimeError("Failed to fetch staff channel setting from API.")
        else:
            self.staff_channel = setting['setting'][2]

        self.chat_log = self.bot.api.get_one_log_setting("3")  # chat_log
        if self.chat_log['status'] != 'ok':
            raise RuntimeError("Failed to fetch chat log settings from API.")
        
    async def build_image_embed(self, attachment: discord.Attachment) -> discord.File:
        """
        Return File for message to be included with the logging embed. 
        """
        data = await attachment.read()
        file = discord.File(BytesIO(data), filename=attachment.filename)
        return file 

    @commands.Cog.listener()
    async def on_message_delete(self, message) -> None:
        """
        If a mod deletes, take the audit log event. If a user deletes, handle it normally.
        """
        
        if message.author.guild.id != int(os.getenv("MASTER_GUILD", 0)) or \
                message.author.guild.id is None:
            logger.warning(">> on_message_delete fired, but not in master guild. Ignoring event.")
            return

        if message.channel.id == self.staff_channel:
            logger.debug("Message delete in staff channel was ignored.")
            return
        
        audit_log = [entry async for entry in message.guild.audit_logs(limit=1)][0]
        
        if self.chat_log["status"] == "ok":
            if self.chat_log["logging"][2] == "0":
                logger.debug(f"log was triggered, but logging is disabled. API: {self.chat_log}")
                return
            logs_channel = await self.bot.fetch_channel(self.chat_log["logging"][2])
            
            
            file_embeds = []
            if len(message.attachments) > 0:
                for attachment in message.attachments:
                    if attachment.content_type and attachment.content_type.startswith('image/'):
                        logger.debug(f"Image attachment detected in deleted message, {attachment.filename}:{attachment.url}")
                        file_embeds.append(await self.build_image_embed(attachment))
            
            if str(audit_log.action) == 'AuditLogAction.message_delete':
                # Then a moderator deleted a message.
                embed = embed_message_delete(audit_log.target, message, audit_log.user)
                await logs_channel.send(embed=embed,files=file_embeds)
                
            else:
                # Otherwise, the author deleted it.
                username = message.author
                await logs_channel.send(embed=embed_message_delete(username, message),files=file_embeds)
                
        else:
            logger.critical(f"API error. API response not ok. -> {self.chat_log}")


async def setup(bot: commands.Bot) -> None:
    """boink"""
    await bot.add_cog(LoggingMessageDelete(bot))
