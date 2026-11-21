"""
When someone posts a GitHub link with line numbers (like #L3 or #L3-L9),
the bot replies with those lines in a code block.
"""

import logging
import re

import aiohttp
from discord.ext import commands

from src.bot.cogs import BaseCog

logger = logging.getLogger(__name__)

# This monster matches links like https://github.com/owner/repo/blob/branch/file.py#L3-L9
# Thx uncle
GITHUB_LINK_PATTERN = r"https://github\.com/([\w.-]+)/([\w.-]+)/blob/([^\s?#]+)(?:\?[^\s#]*)?#L(\d+)(?:-L(\d+))?"
MAX_LINKS = 3
MAX_MESSAGE_LENGTH = 2000
TRUNCATED_TEXT = "\n... (truncated)\n```"


def parse_links(content):
    """
    Finds GitHub line links in a message.
    Returns a list of (owner, repo, path, start, end).
    """
    links = []
    dat_match = re.findall(GITHUB_LINK_PATTERN, content)

    for bleh in dat_match:
        owner = bleh[0]
        repo = bleh[1]
        path = bleh[2]
        start = int(bleh[3])

        # A link like #L3 has no end line, so the end is the same as the start
        if bleh[4] == "":
            end = start
        else:
            end = int(bleh[4])

        # Someone might write #L9-L3, so swap them
        if start > end:
            temp = start
            start = end
            end = temp

        links.append((owner, repo, path, start, end))

        if len(links) == MAX_LINKS:
            break

    return links


def format_snippet(header, text, start, end):
    """Builds the message for one link."""
    all_lines = text.splitlines()

    # The link might ask for more lines than the file has
    if end > len(all_lines):
        end = len(all_lines)

    # The link starts after the last line of the file, so there is nothing to show
    if start > end:
        return None

    # Line numbers dont index at 0
    wanted_lines = all_lines[start - 1 : end]
    code = "\n".join(wanted_lines)

    # Stop the file's own ``` from ending our code block early
    code = code.replace("```", "`​``")

    # Use the file extension for syntax highlighting
    file_name = header.split("/")[-1]
    language = ""
    if "." in file_name:
        language = file_name.split(".")[-1]

    if start == end:
        line_text = f"L{start}"
    else:
        line_text = f"L{start}-L{end}"

    return f"**{header}** {line_text}\n```{language}\n{code}\n```"


def truncate(content):
    """Discord messages can only be 2000 characters"""
    if len(content) <= MAX_MESSAGE_LENGTH:
        # lol so sry
        return content

    keep = MAX_MESSAGE_LENGTH - len(TRUNCATED_TEXT)
    return content[:keep] + TRUNCATED_TEXT


class GithubLines(BaseCog):
    """Shows the code from GitHub line links in chat."""

    def __init__(self, bot):
        super().__init__(logger)

        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        # Ignore other bots and DMs
        if message.author.bot:
            return
        if message.guild is None:
            return

        links = parse_links(message.content)
        if len(links) == 0:
            return

        snippets = []
        timeout = aiohttp.ClientTimeout(total=10)

        async with aiohttp.ClientSession(timeout=timeout) as session:
            for owner, repo, path, start, end in links:
                url = (
                    "https://raw.githubusercontent.com/"
                    + owner
                    + "/"
                    + repo
                    + "/"
                    + path
                )

                try:
                    async with session.get(url) as response:
                        # For anything that isn't 200, private repo or wrong link, just skip it
                        if response.status != 200:
                            continue
                        text = await response.text()
                except (aiohttp.ClientError, TimeoutError):
                    logger.warning("Failed to fetch %s", url)
                    continue

                # path is "branch/folder/file.py", so drop the branch for the header
                path_parts = path.split("/", 1)
                header = repo + "/" + path_parts[-1]

                snippet = format_snippet(header, text, start, end)
                if snippet is not None:
                    snippets.append(snippet)

        if len(snippets) == 0:
            return

        logger.info(
            "Previewing %d GitHub link(s) for %s", len(snippets), message.author.name
        )
        reply_text = "\n".join(snippets)
        await message.reply(truncate(reply_text), mention_author=False)


async def setup(bot):
    """
    Required.
    """
    await bot.add_cog(GithubLines(bot))
