import json
import os
import logging

logger = logging.getLogger("AutoPiano.Mapper")

class KeyboardMapper:
    def __init__(self, mapping_filepath="mappings/virtual_piano.json"):
        self.mapping_filepath = mapping_filepath
        self.mapping = {}
        self.load_mapping()

    def load_mapping(self):
        """Loads keyboard mappings from the specified JSON file."""
        if not os.path.exists(self.mapping_filepath):
            logger.error("Mapping file not found at: %s", self.mapping_filepath)
            self.mapping = {}
            return False
        
        try:
            with open(self.mapping_filepath, 'r', encoding='utf-8') as f:
                raw_mapping = json.load(f)
                # Normalize keys to integers for exact MIDI note matching
                self.mapping = {int(k): v for k, v in raw_mapping.items()}
            logger.info("Loaded %d key mappings from %s", len(self.mapping), self.mapping_filepath)
            return True
        except Exception as e:
            logger.exception("Failed to load or parse mapping file %s", self.mapping_filepath)
            self.mapping = {}
            return False

    def get_key(self, midi_note, transposition=0):
        """
        Translates a MIDI note number to its mapped keyboard key,
        applying transposition before mapping.
        """
        transposed_note = midi_note + transposition
        key = self.mapping.get(transposed_note)
        if key is None:
            # Using debug log to prevent spamming the console for out-of-range notes
            logger.debug("No keyboard mapping found for MIDI note %d (transposed: %d)", midi_note, transposed_note)
        return key
