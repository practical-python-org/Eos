# Eos
A Discord.py bot, utilizing docker.

Discord.py bot  **<->**  Flask API  **<->**  Postgres DB

What it does:
- **Verification** — on-join DM flow and an "are you a robot" dropdown that gates new members.
- **Moderation** — ban, kick, mute, purge, quarantine/release, and server-wide lockdown/unlock.
- **Points** — points awarded automatically per message, with a leaderboard.
- **Logging** — audit events posted to configured log channels.
- **Fun / utility** — cat facts, "let me Google that" links, an in-Discord Python runner, and support tickets.

---
# Quick Start

**Prerequisites:** Docker (with Docker Compose) installed, and a Discord bot token.

1. Copy the example env file: `cd src/ && cp .env.EXAMPLE .env`
2. Replace "YOUR_DISCORD_BOT_TOKEN_HERE" with your Discord Bot token and `MASTER_GUILD` with the ID of the main guild that your bot will be active in.
3. `docker compose up -d`
4. The bot should come online. You can use the `>hc` command to run a healthcheck on the system.

## Configuration

If you already have postgres installed on your system then you may have conflicting ports, in that case change
the `POSTGRES_PORT_HOST` to a free port in the `.env`, usually `5433`. (Clarification:`POSTGRES_PORT` env variable is only used within the container environment). Then rebuild by using following command:
```
docker compose up -d --build
```

---
# Infrastructure
### Postgres Database
- Currently using Postgres 17.5
- The default port is defined in your `.env`

Postgres data is stored in a named Docker volume (`postgres-data`). Do not remove it if you want the data to persist.

To reset the database, remove the volume:
```
docker compose down -v
```

The init script at `src/db/init.sql` runs on the initial startup.

A migration service (`Dockerfile-migration`) runs automatically before the API starts on every `docker compose up`, applying any changes in `src/db/migrations.sql`.

### Flask API
The Flask API is located at `src/api/`. It runs on `http://127.0.0.1:5000` unless you've changed the Flask settings in `.env`.

The functions that connect the API to the database are at `src/api/core/db_helper.py` and serve as an abstraction over the psycopg functions.

A `.postman` directory is included, which contains a postman collection if you feel like messing about with the API locally in postman. 

### Discord.py Bot
The Bot is running using Discord.py with cog-based commands.
- While not recommended, you may also run the bot manually for debugging using `python main.py` if your token is in the `.env`, however the bot depends on the API being reachable.

Cogs are located at `src/bot/cogs/` and are separated by their purpose: `admin/`, `features/`, `logging/`, `moderation/`, `verification/`.

The functions that connect the bot to the API are at `src/bot/core/api_helper.py` and serve as an abstraction over the HTTP requests happening in the background.

---
# Contributing
See [CONTRIBUTING.md](CONTRIBUTING.md) for branch naming, the PR workflow, pre-commit setup, and local development with uv.

---
# Commands

Commands use one of two invocation styles:
- **`>`** — prefix commands (e.g. `>hc`). Some also work as slash commands if you run `>sync` first.
- **`/`** — slash-only commands, registered via Discord's application command system.

Permission levels referenced below:
- **Admin** — requires Discord administrator permission
- **Moderator** — requires the ban_members Discord permission
- **Master guild only** — command only runs in the guild set as `MASTER_GUILD`

---

## Healthchecks

### `>hc`
- **Description**: Checks the health of the API and the database and reports their status.
- **Arguments**: None.
- **Permissions**: None.
- **Output**: An embedded message showing the status and response code for both the API and the database.

---

## Points

Points are awarded automatically per word when a member sends a message, and deducted when a message is deleted.

### `>sync`
- **Description**: Syncs all slash commands with Discord. Run this after deploying changes that add or modify slash commands.
- **Arguments**: None.
- **Permissions**: Admin, master guild only.
- **Output**: A message reporting how many commands were synced.

### `>sync_users`
- **Description**: Adds all current guild members to the points table. Members already in the database are skipped.
- **Arguments**: None.
- **Permissions**: Admin, master guild only.
- **Output**: An embedded message showing how many users were added.

### `>get_points @user`
- **Description**: Retrieves and displays the points of a specific guild member.
- **Arguments**:
  - `user`: A mention or reference to a Discord member.
- **Permissions**: None.
- **Output**: An embedded message displaying the mentioned user's current points.

### `>update_points @user <amount>`
- **Description**: Adds or subtracts points from a specific user.
- **Arguments**:
  - `user`: A mention or reference to a Discord member.
  - `amount`: Integer. Positive to add, negative to subtract.
- **Permissions**: Admin, master guild only.
- **Usage**:
  - Add points: `>update_points @user 100`
  - Remove points: `>update_points @user -50`
- **Output**: An embedded message confirming the change.

### `>top_10`
- **Description**: Displays the top 10 users with the most points in the guild.
- **Arguments**: None.
- **Permissions**: None.
- **Output**: An embedded leaderboard showing usernames and their points.

---

## Settings

### `>settings`
- **Description**: Displays all current guild settings and logging settings.
- **Arguments**: None.
- **Permissions**: Admin, master guild only.
- **Output**: An embedded message listing all settings and their current values.

### `>update_settings`
- **Description**: Interactive dropdown menu for changing guild settings. Covers logging channel assignments, role mappings, and server settings.
- **Arguments**: None.
- **Permissions**: Admin, master guild only.
- **Output**: A dropdown prompt asking which category to edit, followed by per-item dropdowns for each setting.

---

## Features

### `>catfact`
- **Description**: Fetches and displays a random cat fact from the catfact.ninja API.
- **Arguments**: None.
- **Permissions**: None.
- **Output**: A cat fact as a plain message.

### `>google <question>`
- **Description**: Replies with a "Let me Google that for you" link for the given question.
- **Arguments**:
  - `question`: The search term or question.
- **Permissions**: None.
- **Output**: A message with the lmgtfy link.

### `>run`
- **Description**: Executes a Python 3.10 code block via the Piston API and replies with the output. Re-running the command by editing your message will re-execute the code.
- **Arguments**: A fenced Python code block immediately after the command.
- **Permissions**: None.
- **Usage**:
  ````
  >run
  ```py
  print("hello world")
  ```
  ````
  For scripts using `input()`, place the input values on separate lines after the closing fence.
- **Output**: An embedded message containing the program output, truncated to 1000 characters or 10 lines if necessary.

### `/ticket`
- **Description**: Opens an ephemeral message with a button to create a private support thread, staffed with all members holding the Staff role.
- **Arguments**: None.
- **Permissions**: None (slash command only).
- **Output**: An ephemeral prompt with an "Open a support Ticket" button. On click, creates a private thread and notifies staff.

---

## Moderation

### `/ban_member @target <reason> [messages_to_remove] [delete_last_minutes]`
- **Description**: Bans the target member. DMs them the reason before executing. Cannot ban bots or admins. Optionally removes their recent messages, logging them to the mod log first.
- **Arguments**:
  - `target`: The member to ban.
  - `reason`: The reason for the ban.
  - `messages_to_remove`: Number of recent messages from this user to delete (optional, defaults to 0).
  - `delete_last_minutes`: Delete everything this user sent in the last X minutes (optional, defaults to 0, max 10080 = 7 days). Only the newest 100 messages per channel are scanned for the mod log, so Discord may delete more than is logged.
- **Permissions**: Moderator, master guild only, requires `ban_members` Discord permission.
- **Output**: A public embedded message confirming who was banned and why.

### `/kick_member @target <reason>`
- **Description**: Kicks the target member. DMs them the reason before executing. Cannot kick bots or admins.
- **Arguments**:
  - `target`: The member to kick.
  - `reason`: The reason for the kick.
- **Permissions**: Moderator, master guild only, requires `kick_members` Discord permission.
- **Output**: A public embedded message confirming who was kicked and why.

### `/mute_member @target <time> <reason>`
- **Description**: Times out the target member for the specified duration. DMs them the reason.
- **Arguments**:
  - `target`: The member to mute.
  - `time`: Duration in minutes (float).
  - `reason`: The reason for the mute.
- **Permissions**: Moderator, master guild only, requires `moderate_members` Discord permission.
- **Output**: A public embedded message confirming who was muted and for how long.

### `/purge_messages <amount>`
- **Description**: Deletes the specified number of messages from the current channel. Logs the action to the chat log channel if logging is configured.
- **Arguments**:
  - `amount`: Number of messages to delete (max 100 per Discord API).
- **Permissions**: Moderator, master guild only.
- **Output**: Messages are deleted silently. A log entry is sent to the chat log channel if enabled.

### `/quarantine @target <messages_to_remove>`
- **Description**: Quarantines the target user by removing their verified role and assigning the quarantine role. Optionally removes their recent messages from the current channel.
- **Arguments**:
  - `target`: The member to quarantine.
  - `messages_to_remove`: Number of recent messages from this user to delete (0 to skip).
- **Permissions**: Moderator, master guild only, requires `moderate_members` Discord permission.
- **Output**: An ephemeral confirmation and a mod log entry.

### `/release @target`
- **Description**: Releases a quarantined member by restoring their verified role and removing the quarantine role.
- **Arguments**:
  - `target`: The member to release.
- **Permissions**: Moderator, master guild only, requires `moderate_members` Discord permission.
- **Output**: An ephemeral confirmation and a mod log entry.

### `>lockdown`
- **Description**: Removes send message permissions from `@everyone` in all text channels, effectively locking the entire server.
- **Arguments**: None.
- **Permissions**: Admin, master guild only.
- **Output**: A lockdown notice sent in every channel.

### `>unlock`
- **Description**: Restores send message permissions to `@everyone` in all text channels, lifting the lockdown.
- **Arguments**: None.
- **Permissions**: Admin, master guild only.
- **Output**: An unlock notice sent in every channel.

---

## Verification

### `>verify`
- **Description**: Presents a dropdown asking the user to confirm they are not a robot. Selecting "I'm not a robot" assigns the verified role. Selecting a robot option kicks the user.
- **Arguments**: None.
- **Permissions**: None (must be used in the configured verification channel).
- **Output**: A verification prompt that auto-deletes after 15 seconds.

---

## Automatic Behaviours

These are not commands but run in the background:

| Behaviour | Trigger | Action |
|-----------|---------|--------|
| **Points — award** | Member sends a message | Awards points equal to the word count of the message |
| **Points — deduct** | Member deletes a message | Deducts points equal to the word count of the deleted message |
| **Points — join** | Member joins the guild | Adds member to the points table |
| **Points — leave** | Member leaves/is kicked/banned | Removes member from the points table |
| **Spam detection** | Member sends the same message ≥3 times (leaky bucket) | Warns at 3 occurrences, quarantines at 4; deletes spam messages |
| **Verification — on join** | Member joins the guild | Sends a welcome DM with instructions to verify |
