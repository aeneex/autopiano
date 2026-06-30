# 🎹 Auto Piano Player

### Project Specification for IDE AI

---

# Project Overview

Build a Python application capable of automatically playing songs on a virtual piano by reading MIDI files and simulating keyboard input.

The application should be modular, highly extensible, and accurate enough to play complex songs containing chords, sustained notes, and rapid passages.

The goal is to create an architecture that allows future expansion into reading Synthesia videos, sheet music, or audio while keeping the playback engine unchanged.

---

# Objectives

The application should:

* Load any standard `.mid` or `.midi` file.
* Parse all note events.
* Schedule notes with millisecond accuracy.
* Simulate keyboard input.
* Support simultaneous key presses (chords).
* Hold keys for the correct duration.
* Allow playback speed adjustment.
* Support hotkeys.
* Save keyboard mappings.
* Be easy to extend.

---

# Project Structure

```
AutoPiano/

│
├── main.py
├── midi_reader.py
├── player.py
├── mapper.py
├── calibrator.py
├── scheduler.py
├── config.py
├── utils.py
│
├── mappings/
│      virtual_piano.json
│
├── midis/
│      song.mid
│
├── assets/
│      keyboard_reference.png
│
└── logs/
```

---

# Application Flow

```
          MIDI File
               │
               ▼
        MIDI Reader
               │
               ▼
      Parse Note Events
               │
               ▼
        Keyboard Mapper
               │
               ▼
      Playback Scheduler
               │
               ▼
     Keyboard Input Engine
               │
               ▼
        Virtual Piano
```

---

# Module Responsibilities

---

## main.py

Responsible for:

* Loading configuration
* Selecting MIDI
* Starting playback
* Handling hotkeys
* Initializing all modules

---

## midi_reader.py

Responsibilities:

* Read MIDI files using `mido`
* Extract:

  * note_on
  * note_off
  * velocity
  * timestamps
  * tempo
* Convert delta time into absolute playback timestamps.

Output should be a chronological list of note events.

Example output:

```python
[
    {
        "time":0.00,
        "note":60,
        "velocity":100,
        "type":"on"
    },

    {
        "time":0.45,
        "note":60,
        "type":"off"
    }
]
```

---

## mapper.py

Responsible for converting MIDI note numbers into keyboard keys.

Example:

```python
60 -> q
61 -> 2
62 -> w
63 -> 3
64 -> e
65 -> r
66 -> 5
67 -> t
68 -> 6
69 -> y
```

Mappings should be loaded from:

```
mappings/virtual_piano.json
```

Never hardcode mappings inside playback logic.

---

## scheduler.py

The scheduler is the heart of the application.

Responsibilities:

* Wait until event timestamps
* Trigger keyboard actions
* Handle simultaneous events
* Ensure timing accuracy
* Support playback speed multiplier

Playback should remain synchronized even for thousands of notes.

---

## player.py

Responsible only for keyboard simulation.

Example operations:

```
press("q")

release("q")
```

The module should expose functions such as:

```
press_key()

release_key()

press_multiple()

release_multiple()
```

The implementation should support chords naturally.

---

## calibrator.py

Purpose:

Automatically create keyboard mappings.

Workflow:

1. User enters calibration mode.
2. Application asks user to click or identify the first piano key.
3. User presses the keyboard key corresponding to that note.
4. Mapping is stored.
5. Repeat until all playable keys are mapped.
6. Save as JSON.

Example output:

```json
{
    "60":"q",
    "61":"2",
    "62":"w",
    "63":"3",
    "64":"e"
}
```

Calibration should only be required once unless the user chooses to recalibrate.

---

# Configuration

Store user preferences inside a configuration file.

Example:

```json
{
    "playback_speed":1.0,
    "humanize":false,
    "hotkeys":true,
    "mapping":"virtual_piano.json"
}
```

---

# Playback Features

Implement:

* Play
* Pause
* Resume
* Stop
* Restart
* Playback speed

Suggested hotkeys:

```
F6 -> Load MIDI

F7 -> Play

F8 -> Pause

F9 -> Stop

ESC -> Exit
```

---

# Keyboard Mapping

The supplied virtual piano uses a keyboard layout similar to:

White keys:

```
q w e r t y u i o p
z x c v b n m , . /
```

Black keys:

```
2 3
5 6 7
9 0

s d f
h j
l ; '
```

The mapping system should remain configurable and not depend on this specific layout.

---

# Chord Support

The application must correctly play multiple notes that begin at the exact same timestamp.

Example:

```
Press:
q
e
t

Hold

Release:
q
e
t
```

Sequential presses should not be used for simultaneous notes.

---

# Timing Accuracy

The playback engine should:

* Maintain millisecond precision.
* Avoid cumulative timing drift.
* Use high-resolution timers.
* Handle tempo changes contained within MIDI files.

---

# Error Handling

Gracefully handle:

* Missing MIDI files
* Invalid MIDI format
* Missing mapping files
* Invalid mappings
* Unsupported notes
* Keyboard simulation failures

Errors should be logged.

---

# Logging

Create logs for:

* Playback start
* Playback stop
* Loaded MIDI
* Loaded mappings
* Timing issues
* Exceptions

---

# Future Expansion

The architecture should make it easy to add additional input sources without modifying playback logic.

Potential future modules:

## Synthesia Reader

```
Video
↓

Detect Falling Notes

↓

Generate Note Events

↓

Playback Scheduler
```

---

## Sheet Music OCR

```
Image

↓

OCR

↓

Music Parser

↓

Generate Note Events
```

---

## Audio to MIDI

```
Audio

↓

Pitch Detection

↓

MIDI Conversion

↓

Playback
```

---

## Live MIDI Input

```
MIDI Keyboard

↓

Real-Time Events

↓

Keyboard Output
```

---

# Design Principles

* Modular architecture
* Single responsibility per module
* Configurable mappings
* Easy maintenance
* High timing precision
* Minimal coupling between components
* Extensible for future input methods

---

# Suggested Python Libraries

```
mido
keyboard
time
threading
json
logging
pathlib
```

Additional optional libraries:

```
pygame
python-rtmidi
pyautogui
pynput
```

---

# Deliverables

The completed project should:

* Load MIDI files.
* Parse note events.
* Convert notes into keyboard keys.
* Play songs automatically on the virtual piano.
* Support chords.
* Maintain accurate timing.
* Save and load mappings.
* Be modular enough to support future extensions such as Synthesia video parsing, sheet music OCR, and audio transcription without major architectural changes.