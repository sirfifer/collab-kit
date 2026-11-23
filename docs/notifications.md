# Push notifications (optional)

A conversation hears what is critical the moment it starts (the agenda's front page). Between
conversations, the back end can tell you on your phone: the first time a critical item (importance 1)
appears anywhere in the folder, it runs one command you configure. That covers a return it could not
file (it raises those at importance 1), a question an agent is blocked on (agents file those as
critical, `ck ask --blocks`), and anything a conversation or session marked critical. Routine work
never notifies, unless you ask for status lines too (below). A back end that has stopped cannot
notify: for that, see "When the back end itself stops" at the end of this page.

Off by default. Add to `backend.toml`:

```toml
[notify]
command = ["sh", "-c", "<one command; see below>"]
status = false     # true: also one push for each new status line
```

**Status lines, when you want to hear that work finished.** Agents report where things stand with
`ck status` ("the ablation finished: 3 of 4 runs beat the baseline"). With `status = true`, each new
status line in any project sends one push, through the same command and under the same limits,
critical items first. The push carries the line's heading: who reported, and its topic (the first
80 characters of a `ck status`). Lines that were already there when you turn it on are not sent,
and neither are lines filed under your own name (a conversation's). Leave it off if your agents
report often: every line is a push.

The command gets four environment variables, and nothing on its command line:

| Variable | Example |
|---|---|
| `COLLAB_KIT_TITLE` | `Collab Kit: critical in newsletter` (a question that blocks work: `Collab Kit: blocked in newsletter`; a status line: `Collab Kit: status in newsletter`) |
| `COLLAB_KIT_MESSAGE` | the item's title, or the status line's heading (outside text: it may be anything a return wrote) |
| `COLLAB_KIT_ITEM` | `newsletter W-012` (a status line: `newsletter status 2026-12-01 09:15 UTC`) |
| `COLLAB_KIT_KIND` | which kind of push this is: `critical`, `blocked`, or `status`; and for work sent to an agent, `unstarted` (nobody took it in time), `started`, `finished`, `failed` (`blocked` here too) |

`COLLAB_KIT_KIND` lets a phone tell the pushes apart. It is one of a few fixed words, set by the back
end and never taken from a file. The three below, and for work sent to an agent `unstarted`, `started`,
`finished` and `failed` (DESIGN-0.5 section 27; a command that does not know a kind should treat it as
ordinary):

| Kind | When | What it usually means |
|---|---|---|
| `critical` | an importance 1 item appeared | something cannot wait: a return that could not be filed, or an item marked critical |
| `blocked` | an importance 1 item that names the item it blocks (`ck ask --blocks`) | an agent has stopped and waits for your answer |
| `status` | a new status line, only with `status = true` | an agent reported: often that work finished |

A command that ignores the variable works as before.

Always use them inside double quotes (`"$COLLAB_KIT_MESSAGE"`), never pasted into a command line by
string building: a title or a status line is text from a file, and quoting keeps it from ever being
run. With curl, pass them with `--data-raw` or `--form-string`, never `-d` or `-F`: those read a
file when the text starts with `@` (the back end also strips a leading `@` or `<`). The back end
sends each item and each status line once, at most five a pass and twenty an hour (what waits goes
out with a later pass), sends nothing on its first run, and reports a failing command on the
agenda's front page.

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

**Pushover, a priority and a sound for each kind** (a blocked agent rings loudest; a status line
arrives quietly):

```toml
[notify]
command = ["sh", "-c", "case \"$COLLAB_KIT_KIND\" in blocked) p=1; s=siren ;; critical) p=1; s=persistent ;; *) p=0; s=magic ;; esac; curl -s --max-time 10 https://api.pushover.net/1/messages.json --form-string token=<your-app-token> --form-string user=<your-user-key> --form-string \"title=$COLLAB_KIT_TITLE\" --form-string \"message=$COLLAB_KIT_MESSAGE ($COLLAB_KIT_ITEM)\" --form-string \"priority=$p\" --form-string \"sound=$s\""]
status = true
```

The `case` compares the kind with fixed words and sets two values of its own; the text from the
folder still reaches curl only inside double quotes. A kind this command does not know (one a later
kit adds) falls to the last branch.

**Telling Collab Kit's pushes from everything else on the phone.** In Pushover each application has
its own name and icon, shown on every push it sends. Create one application for Collab Kit alone
(pushover.net/apps/build) and give it an icon: then a push from the kit is known at a glance, before
it is read. The kit's own icon is in this repository: `docs/images/collab-kit-icon-pushover.png`
(72 by 72, the size Pushover asks for), made from `docs/images/collab-kit-icon.svg` (a 1024 by 1024
`collab-kit-icon.png` is beside it). It is a first version and will be replaced.

**Telegram**:

```toml
[notify]
command = ["sh", "-c", "curl -s --max-time 10 https://api.telegram.org/bot<your-bot-token>/sendMessage --data-urlencode chat_id=<your-chat-id> --data-urlencode \"text=$COLLAB_KIT_TITLE: $COLLAB_KIT_MESSAGE\""]
```

Keep tokens out of any repository: `backend.toml` lives in the machine's own config folder.

## When the back end itself stops: a dead-man ping

A push tells you about the folder. It cannot tell you that the back end is down, because the back
end is what sends it. Inside the folder the silence is visible: the back end writes the time of
every check (each minute) to `agenda/00-HEARTBEAT.md`, and the start file tells a conversation to
say so first when that time is more than about ten minutes old, or has not moved between two
readings. But that needs a conversation, and one that looks. For the hours between, something
outside the machine has to notice that the checks stopped.

That is a dead-man's switch: a service you tell "still here" every few minutes, and which alerts you
when it stops hearing from you. The kit does not run one and does not need one. It can ping one.
Off by default; add to `backend.toml`:

```toml
[heartbeat]
command = ["sh", "-c", "curl -fsS --max-time 10 -o /dev/null https://hc-ping.com/<your-check-id>"]
every_minutes = 5
```

- The command runs after a check that succeeded (the folder was reached, and the heartbeat file
  written), at most every `every_minutes` (default 5). On a runner without a minute check (GitHub
  Actions, hourly) it runs after each pass.
- **Nothing from the folder reaches it.** It gets one variable, `COLLAB_KIT_CHECKED` (the time of
  the check, UTC), and nothing on its command line. There is no outside text to quote.
- It has twenty seconds. A command that fails, or is not a list of strings, is printed to the back
  end's log and listed at the top of the agenda's front page by the next full pass; it is tried
  again at the next check.
- Set the service's period to your `every_minutes` and its grace time to five or ten minutes: you
  then hear within about a quarter of an hour that the machine is off, asleep, offline, or signed
  out of the drive.

| Service | Notes |
|---|---|
| **Healthchecks.io** | Hosted, with a free tier; open source and self-hostable. One GET per ping (the example above). You set the period and the grace time, and it alerts by email or through its integrations. |
| Another dead-man service, or your own endpoint | Anything that records the last ping and alerts when it is old. The command is yours to write. |

The ping's address is a secret of the same kind as an ntfy topic: whoever has it can keep the check
quiet. It lives in `backend.toml`, never in a repository.

Sources: pushover.net/api, docs.ntfy.sh/publish, core.telegram.org/bots/api, github.com/gotify/server,
github.com/caronc/apprise, healthchecks.io/docs.
