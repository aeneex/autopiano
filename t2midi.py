import os
import tkinter as tk
from tkinter import filedialog
import mido
from mido import Message, MidiFile, MidiTrack

def text_to_midi():
    # Hide the main tkinter root window
    root = tk.Tk()
    root.withdraw()
    root.attributes('-topmost', True) # Bring file picker to front

    print("Select your .txt file containing the notes...")
    txt_path = filedialog.askopenfilename(
        title="Select Notes Text File",
        filetypes=[("Text Files", "*.txt")]
    )

    if not txt_path:
        print("No file selected. Exiting.")
        return

    # Read the notes from the file
    with open(txt_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Split text by whitespace/newlines and clean it up
    raw_notes = content.upper().split()
    
    # Simple note-to-MIDI number converter mapping
    note_names = ['C', 'C#', 'D', 'D#', 'E', 'F', 'F#', 'G', 'G#', 'A', 'A#', 'B']
    midi_sequence = []

    for item in raw_notes:
        # Strip out commas, dashes, or brackets if you accidentally left them in
        clean_item = "".join(c for c in item if c.isalnum() or c == '#')
        if not clean_item:
            continue
            
        try:
            # Separate the note name from the octave (e.g., "C5" -> "C", 5)
            if clean_item[-1].isdigit():
                octave = int(clean_item[-1])
                note_part = clean_item[:-1]
            else:
                octave = 4 # Default octave if you forgot to type one
                note_part = clean_item

            note_index = note_names.index(note_part)
            midi_number = (octave + 1) * 12 + note_index
            midi_sequence.append(midi_number)
        except (ValueError, IndexError):
            print(f"⚠️ Skipping invalid note token: '{item}'")

    if not midi_sequence:
        print("❌ No valid notes found in the text file.")
        return

    # Build the MIDI File
    mid = MidiFile()
    track = MidiTrack()
    mid.tracks.append(track)
    
    # Set standard tempo (120 BPM)
    track.append(mido.MetaMessage('set_tempo', tempo=mido.bpm2tempo(120)))
    
    # 16th note duration calculation
    ticks_per_16th = 120 

    for note in midi_sequence:
        # Dynamic velocity (80) for a softer, dreamier vibe
        track.append(Message('note_on', note=note, velocity=80, time=0))
        track.append(Message('note_off', note=note, velocity=0, time=ticks_per_16th))

    # Save midi file with the same name as the text file
    output_midi_path = os.path.splitext(txt_path)[0] + ".mid"
    mid.save(output_midi_path)
    print(f"✨ Success! Saved MIDI file to: {output_midi_path}")

if __name__ == "__main__":
    text_to_midi()
