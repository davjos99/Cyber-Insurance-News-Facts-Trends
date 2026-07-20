# Cron + Task Scheduler Setup

Run the cybersec briefing automatically every morning.

> **Honest caveat:** Skills do NOT auto-schedule. You need to wire ONE line of cron (Mac/Linux) or set up ONE Windows Task Scheduler entry. That's the whole "automation" — 30 seconds of one-time setup.

## macOS / Linux — cron

### Option A — crontab

```bash
crontab -e
```

Add this line (runs at 7:30 AM local time daily):

```
30 7 * * * /usr/bin/env bash ~/.claude/skills/morning-cybersec-briefing/scripts/orchestrate.sh ~/.cybersec-briefing/chain_config.json >> ~/.cybersec-briefing/cron.log 2>&1
```

Save + exit. Verify:

```bash
crontab -l
```

### Option B — launchd (macOS, more reliable than cron on modern Macs)

Create `~/Library/LaunchAgents/com.user.cybersec-briefing.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>com.user.cybersec-briefing</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/env</string>
    <string>bash</string>
    <string>/Users/YOU/.claude/skills/morning-cybersec-briefing/scripts/orchestrate.sh</string>
    <string>/Users/YOU/.cybersec-briefing/chain_config.json</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>7</integer>
    <key>Minute</key>
    <integer>30</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>/Users/YOU/.cybersec-briefing/launchd.log</string>
  <key>StandardErrorPath</key>
  <string>/Users/YOU/.cybersec-briefing/launchd.err</string>
</dict>
</plist>
```

Replace `YOU` with your username. Load it:

```bash
launchctl load ~/Library/LaunchAgents/com.user.cybersec-briefing.plist
```

Verify:

```bash
launchctl list | grep cybersec
```

### Why launchd over cron on macOS

- launchd actually runs at the scheduled time even if your Mac was asleep at that time (cron misses the run)
- launchd reads your normal shell env (cron has a stripped-down PATH)
- launchd's log paths make debugging trivial

## Linux — systemd timer (modern alternative to cron)

Create `~/.config/systemd/user/cybersec-briefing.service`:

```ini
[Unit]
Description=Cybersec briefing chain
After=network.target

[Service]
Type=oneshot
ExecStart=/usr/bin/env bash %h/.claude/skills/morning-cybersec-briefing/scripts/orchestrate.sh %h/.cybersec-briefing/chain_config.json
StandardOutput=append:%h/.cybersec-briefing/systemd.log
StandardError=append:%h/.cybersec-briefing/systemd.err
```

Create `~/.config/systemd/user/cybersec-briefing.timer`:

```ini
[Unit]
Description=Run cybersec briefing daily at 7:30 AM

[Timer]
OnCalendar=*-*-* 07:30:00
Persistent=true

[Install]
WantedBy=timers.target
```

Enable:

```bash
systemctl --user daemon-reload
systemctl --user enable --now cybersec-briefing.timer
```

Verify:

```bash
systemctl --user list-timers cybersec-briefing.timer
journalctl --user -u cybersec-briefing.service
```

## Windows — Task Scheduler

### GUI walkthrough

1. Open **Task Scheduler** (Win+R → `taskschd.msc`)
2. **Create Basic Task...**
3. Name: "Cybersec Briefing"
4. Trigger: **Daily** at 7:30 AM
5. Action: **Start a program**
   - Program: `python` (or full path: `C:\Users\YOU\AppData\Local\Programs\Python\Python311\python.exe`)
   - Arguments: `"C:\Users\YOU\.claude\skills\morning-cybersec-briefing\scripts\orchestrate.py" "C:\Users\YOU\.cybersec-briefing\chain_config.json"`
   - Start in: `C:\Users\YOU\.cybersec-briefing`
6. Finish

### PowerShell one-liner

```powershell
$Action = New-ScheduledTaskAction -Execute "python" -Argument '"C:\Users\YOU\.claude\skills\morning-cybersec-briefing\scripts\orchestrate.py" "C:\Users\YOU\.cybersec-briefing\chain_config.json"'
$Trigger = New-ScheduledTaskTrigger -Daily -At 7:30AM
Register-ScheduledTask -Action $Action -Trigger $Trigger -TaskName "CybersecBriefing" -Description "Daily cybersec news briefing chain"
```

Verify:

```powershell
Get-ScheduledTask -TaskName CybersecBriefing
```

## Honest expectations

### "Will it run if my computer is asleep?"

- **macOS launchd:** yes, wakes the Mac
- **macOS cron:** no, misses the run
- **Linux systemd:** runs on wake if `Persistent=true` is set
- **Linux cron:** no, misses the run
- **Windows Task Scheduler:** yes, with "Wake the computer to run this task" checked in the task's Conditions tab

For a laptop that's frequently asleep at 7:30 AM, prefer launchd (Mac) / systemd (Linux) / Task Scheduler with wake (Windows) over plain cron.

### "What if I want it to run on the cloud, not my machine?"

Use the GitHub Actions workflow in `references/github_actions_workflow.md`. The chain runs on GitHub's infrastructure, doesn't depend on your machine being on.

### "How do I check if it ran?"

```bash
tail -f ~/.cybersec-briefing/runs.log
```

One line per run with timestamp + outcome.

## Troubleshooting

### "Cron job doesn't run"

- Cron uses a stripped PATH. The orchestrate.sh inside this Skill uses absolute `/usr/bin/env python3` to dodge that.
- Some distros require enabling cron: `sudo systemctl enable cron` (Linux) or sign in at least once with the user (macOS).

### "Task Scheduler runs but skill fails"

- Check the **Last Run Result** column in Task Scheduler. 0x0 = success, non-zero = check the log path.
- Most common cause: Python not in PATH for the scheduled user. Use the full path to `python.exe` in the Program field.

### "launchd plist won't load"

- `plutil ~/Library/LaunchAgents/com.user.cybersec-briefing.plist` — checks XML syntax
- `Console.app` → System Reports → look for `com.user.cybersec-briefing` errors

### "I want to test it without waiting until tomorrow"

```bash
# macOS launchd
launchctl start com.user.cybersec-briefing

# Linux systemd
systemctl --user start cybersec-briefing.service

# Cron
bash ~/.claude/skills/morning-cybersec-briefing/scripts/orchestrate.sh ~/.cybersec-briefing/chain_config.json

# Windows
schtasks /run /tn "CybersecBriefing"
```
