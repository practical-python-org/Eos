#!/usr/bin/env bash

export GIT_HASH=$(cat /commit_hash.txt)
uv run --frozen --no-cache --no-dev --package eos-bot python -m src.bot.main
