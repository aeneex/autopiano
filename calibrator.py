import os
import json
import logging
from pynput.keyboard import Listener, Key

logger = logging.getLogger("AutoPiano.Calibrator")

class KeyboardCalibrator:
    def __init__(self, mapping_filepath="mappings/virtual_piano.json"):
        self.mapping_filepath = mapping_filepath

    def calibrate(self):
        """Runs the interactive calibration CLI."""
        print("\n" + "=" * 50)
        print("🎹 AUTO PIANO KEYBOARD CALIBRATOR 🎹")
        print("=" * 50)
        print("This utility helps you map your computer keyboard to MIDI note numbers.")
        print("For each prompt, press the corresponding key on your keyboard.")
        print("Press 'ESC' at any time to finish or abort.")
        print("-" * 50)

        # Ask user for range
        try:
            start_note_str = input("Enter starting MIDI note number [Default: 60 (C4)]: ").strip()
            start_note = int(start_note_str) if start_note_str else 60
            
            end_note_str = input("Enter ending MIDI note number [Default: 84 (C6)]: ").strip()
            end_note = int(end_note_str) if end_note_str else 84
        except ValueError:
            print("❌ Invalid input. Defaulting to C4 (60) to C6 (84).")
            start_note = 60
            end_note = 84

        if start_note > end_note:
            start_note, end_note = end_note, start_note

        new_mapping = {}
        cancelled = False

        print(f"\nReady to calibrate {end_note - start_note + 1} notes ({start_note} to {end_note}).")
        print("Focus this terminal window and press the key for each note.")

        for note in range(start_note, end_note + 1):
            note_name = self.midi_note_to_name(note)
            print(f"👉 Press key for MIDI {note} ({note_name}) [ESC to stop]: ", end="", flush=True)
            
            # Read single keypress
            key_pressed = self._wait_for_keypress()
            
            if key_pressed is None:
                print("\n🛑 Calibration stopped early.")
                cancelled = True
                break
                
            print(f"'{key_pressed}'")
            new_mapping[str(note)] = key_pressed

        if new_mapping:
            save_prompt = "Save this mapping? (y/n): " if cancelled else "Calibration complete! Save this mapping? (y/n): "
            save = input(save_prompt).strip().lower() == 'y'
            
            if save:
                if self.save_mapping(new_mapping):
                    print(f"✅ Mapping successfully saved to '{self.mapping_filepath}'.")
                else:
                    print("❌ Error: Failed to save mapping.")
            else:
                print("⚠️ Mapping discarded.")
        else:
            print("⚠️ No notes were calibrated.")

    def _wait_for_keypress(self):
        """Blocks until a key is pressed, then returns its string representation."""
        pressed_key = None
        
        def on_press(key):
            nonlocal pressed_key
            try:
                # Normal character keys
                pressed_key = key.char
            except AttributeError:
                # Special keys (e.g. Esc, Shift, Space)
                if key == Key.esc:
                    pressed_key = None
                else:
                    pressed_key = key.name
            return False  # Stops the listener thread
            
        with Listener(on_press=on_press) as listener:
            listener.join()
            
        return pressed_key

    @staticmethod
    def midi_note_to_name(note_num):
        """Helper to convert a MIDI number to a standard note name (e.g. 60 -> C4)."""
        note_names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
        octave = (note_num // 12) - 1
        name = note_names[note_num % 12]
        return f"{name}{octave}"

    def save_mapping(self, mapping_data):
        """Saves custom keyboard mapping to JSON file."""
        try:
            # Load existing mapping if any, to merge or overwrite
            existing_mapping = {}
            if os.path.exists(self.mapping_filepath):
                try:
                    with open(self.mapping_filepath, 'r', encoding='utf-8') as f:
                        existing_mapping = json.load(f)
                except Exception:
                    pass
            
            # Merge: update existing mapping with new calibration
            existing_mapping.update(mapping_data)
            
            # Ensure the output directory exists
            os.makedirs(os.path.dirname(os.path.abspath(self.mapping_filepath)), exist_ok=True)
            
            with open(self.mapping_filepath, 'w', encoding='utf-8') as f:
                json.dump(existing_mapping, f, indent=4)
            return True
        except Exception as e:
            logger.exception("Failed to save calibration data to %s", self.mapping_filepath)
            return False
