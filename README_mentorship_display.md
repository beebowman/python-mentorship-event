# Speed Mentorship Event Display
### Raspberry Pi Touchscreen Kiosk

---

## Quick Start

```bash
# 1. Install dependencies
pip3 install pygame numpy

# 2. Run the display
python3 speed_mentorship_display.py

# 3. To run fullscreen on boot (optional — see "Auto-start" below)
```

---

## What This Does

A touchscreen kiosk display that replaces your event volunteers by:

| Problem | Solution |
|---|---|
| Volunteers drew arrows wrong | Animated directional map always correct |
| Attendees didn't know where to sit | Visual room layout with color-coded seats |
| Volunteers kept asking questions | FAQ screen answers everything |
| Leader had to manage timing AND questions | Timer runs itself, beeps automatically |
| Late arrivals / early leavers disrupted flow | Instructions for this are in the FAQ |
| Layout on PPT didn't match the room | Dedicated Map screen shows actual snake layout |

---

## Screens

### 🏠 Home
- Shows event name, venue, and live timer status strip
- Three large buttons: FAQ, Map, Timer
- Rotation reminder banner (with pulsing animation)
- Quick FAQ preview that cycles on tap

### ❓ FAQ
- Expandable question list — tap to reveal answer
- Pre-loaded with 8 common questions (fully editable in config)
- Covers: rotation rules, late arrivals, early leavers, seating, restrooms, food

### 🗺 Room Map
- Animated snake-table layout
- Mentor seats (blue, fixed) vs Mentee seats (teal, rotating)
- Animated arrows show rotation direction
- START and END positions labeled
- Color legend at the bottom

### ⏱ Timer
- Giant countdown clock with circular progress arc
- Color changes: green → amber → red as time runs out
- START / PAUSE / RESUME / NEXT SESSION buttons
- Auto-plays rotation beep + flash when session ends
- 1-minute warning beep
- Long final beep when event end time is reached

### ⚙ Settings
- Session duration (minute + second fields, or tap quick presets: 3:00, 3:30, 4:00, 4:30, 5:00)
- Event end time (HH:MM format) — triggers final long beep automatically
- Rotation direction (LEFT or RIGHT)
- On-screen number pad for touchscreens
- Physical keyboard also works (Tab to move between fields)

---

## Corner Quick-Access Buttons (always visible)

| Position | Button | What it does |
|---|---|---|
| Top-right | ⚙ | Settings |
| Bottom-left | MAP | Room layout |
| Bottom-right | TMR | Timer |
| Bottom-center | HOME | Home screen |

---

## Beep Reference

| Beep | What it means |
|---|---|
| Short beep (880 Hz, 0.25s) | Event started |
| Warning beep (1100 Hz, 0.18s) | 1 minute remaining |
| Rotation beep (660 Hz, 0.8s) | Rotate now! Move seats. |
| End beep (440 Hz, 3s long) | Event over — final bell |

---

## Customizing FAQ & Event Info

Edit `mentorship_config.json` (created on first run) to change:
- Event name and venue
- Session duration defaults
- FAQ questions and answers
- Rotation direction

Or just use the Settings screen on the device.

### Sample config snippet
```json
{
  "session_minutes": 4,
  "session_seconds": 0,
  "end_time": "18:30",
  "event_name": "Speed Mentorship",
  "venue_name": "Main Hall, Building B",
  "move_direction": "right",
  "faq": [
    {
      "q": "What do I do when the bell rings?",
      "a": "Move one seat to the RIGHT."
    }
  ]
}
```

---

## Multiple Raspberry Pi Displays

Run the same script on multiple Pi's around the room.
Each Pi independently runs the timer — sync them by:
1. Setting the same **event end time** in Settings on each device
2. Pressing **START** on each device at the same moment

> **Tip:** Put one Pi on the Timer screen, one on the Map screen, one on the Home/FAQ screen. Use the corner buttons to switch between modes.

---

## Auto-start on Boot (Raspberry Pi OS)

### Method 1 — systemd service
```bash
sudo nano /etc/systemd/system/mentorship.service
```
Paste:
```ini
[Unit]
Description=Speed Mentorship Display
After=graphical.target

[Service]
User=pi
Environment=DISPLAY=:0
WorkingDirectory=/home/pi/mentorship
ExecStart=/usr/bin/python3 /home/pi/mentorship/speed_mentorship_display.py
Restart=always

[Install]
WantedBy=graphical.target
```
Then:
```bash
sudo systemctl enable mentorship
sudo systemctl start mentorship
```

### Method 2 — autostart file
```bash
mkdir -p ~/.config/autostart
nano ~/.config/autostart/mentorship.desktop
```
Paste:
```ini
[Desktop Entry]
Type=Application
Name=Speed Mentorship
Exec=python3 /home/pi/mentorship/speed_mentorship_display.py
```

---

## Keyboard Shortcuts

| Key | Action |
|---|---|
| Escape | Go back / exit |
| F11 | Toggle fullscreen |
| Tab (in Settings) | Move to next field |
| Enter (in Settings) | Save |

---

## Requirements

- Raspberry Pi 3B+ or newer (Pi 4 recommended)
- Raspberry Pi OS with desktop (Bullseye or Bookworm)
- Touchscreen display (any resolution — tested at 1280×800)
- Python 3.7+
- `pygame` — display engine
- `numpy` — audio beep generation (optional but recommended)
- Bluetooth speaker, EWA A106 Pro or equivalent

```bash
pip3 install pygame numpy
```

---

## Troubleshooting

**No audio?**
```bash
pip3 install numpy
# Also check: amixer set Master 100%
```

**Wrong screen resolution?**
Edit line in the script:
```python
SCREEN_W, SCREEN_H = 1280, 800  # change to your display size
```

**Touch not working?**
Ensure your touch driver is installed. For official Raspberry Pi displays this is automatic. For third-party displays, check manufacturer docs.

**Text too small/large?**
Change font sizes in `_init_fonts()` in the script.
