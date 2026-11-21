import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
if not hasattr(sys.modules.get("aiohttp"), "__file__"):
    sys.modules.pop("aiohttp", None)

from src.bot.cogs.features.github_lines import (  # noqa: E402
    MAX_MESSAGE_LENGTH,
    format_snippet,
    parse_links,
    truncate,
)

BASE = "https://github.com/diogoscf/github-lines/blob/master/package.json"


def test_single_line():
    assert parse_links(f"look {BASE}#L3 here") == [
        ("diogoscf", "github-lines", "master/package.json", 3, 3)
    ]


def test_3to9_and_9to3():
    assert parse_links(f"{BASE}#L3-L9")[0][3:] == (3, 9)
    assert parse_links(f"{BASE}#L9-L3")[0][3:] == (3, 9)


def test_branch_with_slash():
    link = "https://github.com/a/b/blob/feature/x/src/main.py#L1"
    assert parse_links(link)[0][2] == "feature/x/src/main.py"


def test_extra_parameter():
    link = "https://github.com/a/b/blob/master/README.md?plain=1#L11-L15"
    assert parse_links(link) == [("a", "b", "master/README.md", 11, 15)]


def test_ignored_links():
    assert parse_links(BASE) == []
    assert parse_links("https://gitlab.com/a/b/blob/main/x.py#L1") == []


def test_format_snippet():
    text = "a\nb\nc\nd"
    assert (
        format_snippet("repo/x.py", text, 2, 3)
        == "**repo/x.py** L2-L3\n```py\nb\nc\n```"
    )
    assert format_snippet("repo/x.py", text, 4, 99).startswith("**repo/x.py** L4\n")
    assert format_snippet("repo/x.py", text, 10, 12) is None
    assert format_snippet("repo/Makefile", text, 1, 1).startswith(
        "**repo/Makefile** L1\n```\n"
    )


def test_backticks_escaped():
    snippet = format_snippet("r/x.md", "```evil```", 1, 1)
    assert snippet.count("```") == 2


def test_truncate():
    out = truncate("```\n" + "x" * 5000)
    assert len(out) == MAX_MESSAGE_LENGTH
    assert out.endswith("```")
