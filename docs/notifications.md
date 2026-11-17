# Push notifications (optional)

A conversation hears what is critical the moment it starts (the agenda's front page). Between
conversations, the back end can tell you on your phone: the first time a critical item (importance 1)
appears anywhere in the folder, it runs one command you configure. That covers a return it could not
file (it raises those at importance 1), a question an agent is blocked on, and anything a conversation
or session marked critical. Routine work never notifies. A back end that has stopped cannot notify:
the agenda's front page says so at the start of the next conversation.

Off by default. Add to `backend.toml`:

```toml
[notify]
command = ["sh", "-c", "<one command; see below>"]
```

The command gets three environment variables, and nothing on its command line:

| Variable | Example |
|---|---|
| `COLLAB_KIT_TITLE` | `Collab Kit: critical in garden-planner` |
| `COLLAB_KIT_MESSAGE` | the item's title (outside text: it may be anything a return wrote) |
| `COLLAB_KIT_ITEM` | `garden-planner W-012` |

Always use them inside double quotes (`"$COLLAB_KIT_MESSAGE"`), never pasted into a command line by
string building: a title is text from a file, and quoting keeps it from ever being run. With curl,
pass them with `--data-raw` or `--form-string`, never `-d` or `-F`: those read a file when the text
starts with `@` (the back end also strips a leading `@` or `<`). The back end sends each item once,
at most five a pass and twenty an hour (what waits goes out with a later pass), sends nothing on its
first run, and reports a failing command on the agenda's front page.

## Which service

| Service | Phones | Cost | Notes |
|---|---|---|---|
| **ntfy** (default) | iOS, Android, web | free hosted (fair use); self-hostable | One POST, no account. On the public server the topic name is the only secret: make it long and random, and send the item reference, not its title. |
| **Pushover** | iOS, Android, desktop | about $5 once per platform | Emergency priority repeats until you acknowledge it. Content is seen by Pushover. |
| **Telegram bot** | iOS, Android | free | Needs a bot (BotFather) and your chat id; the token sits in the URL. |
| Gotify | Android only | free, self-hosted | No iOS app. |
| Apprise | a layer over 100+ services | free | Use its command line as your command if you like; the kit does not depend on it. |

Slack or Discord webhooks work too, but a push there mixes with chat and cannot break through Do Not
Disturb. Facts as of November 2026.

## Examples

**ntfy** (sends the reference only, safe on a public topic):

```toml
[notify]
command = ["sh", "-c", "curl -s --max-time 10 -H \"Title: $COLLAB_KIT_TITLE\" -H 'Priority: 5' --data-raw \"$COLLAB_KIT_ITEM\" https://ntfy.sh/<your-long-random-topic>"]
```

**Pushover**:

```toml
[notify]
command = ["sh", "-c", "curl -s --max-time 10 https://api.pushover.net/1/messages.json --form-string token=<your-app-token> --form-string user=<your-user-key> --form-string \"title=$COLLAB_KIT_TITLE\" --form-string \"message=$COLLAB_KIT_MESSAGE ($COLLAB_KIT_ITEM)\" --form-string priority=1"]
```

**Telegram**:

```toml
[notify]
command = ["sh", "-c", "curl -s --max-time 10 https://api.telegram.org/bot<your-bot-token>/sendMessage --data-urlencode chat_id=<your-chat-id> --data-urlencode \"text=$COLLAB_KIT_TITLE: $COLLAB_KIT_MESSAGE\""]
```

Keep tokens out of any repository: `backend.toml` lives in the machine's own config folder.

Sources: pushover.net/api, docs.ntfy.sh/publish, core.telegram.org/bots/api, github.com/gotify/server,
github.com/caronc/apprise.
