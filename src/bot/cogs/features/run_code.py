"""
Uses PistonAPI to run code in the server.
"""

import logging
import os

import discord
from discord import Message
from discord.ext import commands
from discord.ext.commands import Bot, Context
from ultra_piston import File, PistonClient

from src.bot.cogs import BaseCog

logger = logging.getLogger(__name__)

TRUNCATED_MESSAGE: str = "\n```\n```\nOutput too long. Message truncated.\n```"
TRUNCATED_MESSAGE_LENGTH: int = len(TRUNCATED_MESSAGE)
MAX_NEW_LINES: int = 10
MAX_CHARACTERS: int = 1000
# Discord character limit is 4096, but to prevent spamming, we reduce it to 1K


class UtilityRunCode(BaseCog):
    """Uses PistonAPI to run code in the server."""

    def __init__(self, bot: Bot):
        super().__init__(logger)

        self.bot = bot
        PISTON_API_TOKEN = os.environ.get("PISTON_API_TOKEN")
        if not PISTON_API_TOKEN:
            raise ValueError("PISTON_API_TOKEN environment variable not set")

        self.piston = PistonClient(
            api_key=f"{PISTON_API_TOKEN}",
        )

    def get_embed(
        self, title: str, output: str, is_error: bool, is_code: bool = True
    ) -> discord.Embed:
        if is_error:
            embed = discord.Embed(colour=discord.Colour.red(), title=title)
        else:
            embed = discord.Embed(colour=discord.Colour.green(), title=title)

        if is_code:
            if not output.strip():
                output = "⚠️ No Output Produced"

            else:
                output = f"```\n{output}\n```"

                if output.count("\n") > MAX_NEW_LINES:
                    output_lines = output.split("\n")
                    output = (
                        "\n".join(output_lines[: MAX_NEW_LINES + 1]) + TRUNCATED_MESSAGE
                    )

                elif len(output) > MAX_CHARACTERS:
                    output = (
                        output[: MAX_CHARACTERS - TRUNCATED_MESSAGE_LENGTH]
                        + TRUNCATED_MESSAGE
                        + ""
                    )

        embed.description = output
        return embed

    @commands.command()
    async def run(self, ctx: Context, *, codeblock: str = "") -> None:
        """
        Uses Piston-API to run code in the server.

        Parameters
        ----------
        codeblock : str
            The code you want to execute.
        """
        logger.info("%s used the %s command.", ctx.author.name, ctx.command)

        async with ctx.channel.typing():
            # Adjust iOS quotation marks “”‘’ to avoid SyntaxError: invalid character
            for i, c in enumerate("“‘”’"):
                codeblock = codeblock.replace(c, "\"'"[i % 2])

            if codeblock.startswith("```py") and "```" in codeblock[3:]:
                # Split input args from codeblock
                _, codeblock, args = codeblock.split("```")
                args = args.strip()

                # Remove py/python language indicator from codeblock
                codeblock = codeblock.removeprefix("py").removeprefix("thon").strip()

                # Check for input() args and calls to input() function
                if "input(" in codeblock and not args:
                    value = (
                        "I am happy to run your script but I do not want to interact with you. You can "
                        "remove your input() functions, however if you insist on keeping them, please "
                        "put your input values in order on separate lines after the codeblock:\n\n"
                        ">run\n"
                        r"\```py"
                        '\nx = input("What is your first input: ")'
                        '\ny = input("What is your second input: ")'
                        "\nprint(x)\nprint(y)\n"
                        r"\```"
                        "\nInput One\nInput Two"
                    )

                else:
                    version = "3.10.0"
                    code_file = File(content=codeblock)
                    executed_code = await self.piston.post_execute_async(
                        language="python3", version=version, file=code_file, stdin=args
                    )

                    # Check for EOFError
                    if all(
                        item in executed_code.run.output
                        for item in ("Traceback", "EOFError:")
                    ):
                        value = (
                            "The function input() was called more times than the number of input strings "
                            " provided. Make sure you have the correct number of input strings after the "
                            "codeblock.\n(Each input string should be separated by a new line)\n\n"
                            ">run\n"
                            r"\```py"
                            '\nx = input("What is your first input: ")'
                            '\ny = input("What is your second input: ")'
                            "\nprint(x)\nprint(y)\n"
                            r"\```"
                            "\nInput One\nInput Two"
                        )

                    # Code execution successful without EOFError
                    else:
                        embed = self.get_embed(
                            f"Executed in Python {version}",
                            executed_code.run.output,
                            bool(executed_code.run.code),
                        )
                        await ctx.reply(embed=embed)
                        return

            # Check for single quotes instead of codeblocks
            elif codeblock.startswith("'''") or codeblock.endswith("'''"):
                value = (
                    "Did you mean to use ` instead of ' ?\n\n"
                    r"\```py"
                    '\nprint("The code goes here")\n'
                    r"\```"
                )
            else:
                value = (
                    "Please place your code inside a code block like so-\n"
                    r"\```py"
                    '\nprint("The code goes here")\n'
                    r"\```"
                )

            # Output error message
            embed = self.get_embed("Formatting error", value, True, False)
            await ctx.channel.send(embed=embed)

    @commands.Cog.listener()
    async def on_message_edit(self, before: Message, after: Message) -> None:
        if before.author.bot:
            return

        if before.content.startswith(">run") or after.content.startswith(">run"):
            # Make sure we ONLY re-run messages that are /run commands
            channel = after.channel  # The channel that the edited message is in
            # Grab the last 10 (should be enough...) bot messages
            all_replies = [
                message
                async for message in channel.history(limit=20)
                if message.author == self.bot.user
            ]
            for bot_reply in all_replies:
                if bot_reply.reference.message_id == after.id:
                    await bot_reply.delete()
                    # If the reference message of the bot message is the edited message...
                    # Re-run the /run command with the new content
                    # however, we dont call the command with /run, so we need to remove the '/run' from the message
                    code = after.content.replace(">run", "").strip()
                    new_ctx = await self.bot.get_context(after)  # get a new message ctx
                    await new_ctx.command.callback(self, new_ctx, codeblock=code)
                    return


async def setup(bot: commands.Bot) -> None:
    """boink"""
    await bot.add_cog(UtilityRunCode(bot))
