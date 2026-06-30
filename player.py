import logging
import threading
from pynput.keyboard import Controller, Key

logger = logging.getLogger("AutoPiano.Player")

class Player:
    def __init__(self):
        self.keyboard = Controller()
        self.pressed_keys = set()
        self.lock = threading.Lock()
        self.shifted_symbols = {
            '!': '1', '@': '2', '#': '3', '$': '4', '%': '5',
            '^': '6', '&': '7', '*': '8', '(': '9', ')': '0',
            '_': '-', '+': '=', '{': '[', '}': ']', '|': '\\',
            ':': ';', '"': "'", '<': ',', '>': '.', '?': '/'
        }

    def _get_pynput_key(self, key_str):
        """Converts string representation of a key to a pynput key object or character."""
        if not key_str:
            return None
        
        if len(key_str) == 1:
            return key_str

        # Handle common special key words
        key_lower = key_str.lower()
        if key_lower == "space":
            return Key.space
        elif key_lower == "enter":
            return Key.enter
        elif key_lower == "tab":
            return Key.tab
        elif key_lower in ("shift", "shift_l", "shift_r"):
            return Key.shift
        elif key_lower in ("ctrl", "ctrl_l", "ctrl_r"):
            return Key.ctrl
        elif key_lower in ("alt", "alt_l", "alt_r"):
            return Key.alt
        elif key_lower == "backspace":
            return Key.backspace
        
        return key_str

    def press_key(self, key_str):
        """Simulate pressing a key down, simulating shift if necessary."""
        pkey = self._get_pynput_key(key_str)
        if not pkey:
            return
        
        requires_shift = False
        base_key = pkey
        
        if isinstance(pkey, str) and len(pkey) == 1:
            if pkey.isupper():
                requires_shift = True
                base_key = pkey.lower()
            elif pkey in self.shifted_symbols:
                requires_shift = True
                base_key = self.shifted_symbols[pkey]
        
        try:
            with self.lock:
                if key_str not in self.pressed_keys:
                    if requires_shift:
                        self.keyboard.press(Key.shift)
                        self.keyboard.press(base_key)
                        self.keyboard.release(Key.shift)
                    else:
                        self.keyboard.press(base_key)
                    self.pressed_keys.add(key_str)
                    logger.debug("Pressed key: %s", key_str)
        except Exception as e:
            logger.error("Failed to press key '%s': %s", key_str, e)

    def release_key(self, key_str):
        """Simulate releasing a key, using base key representation."""
        pkey = self._get_pynput_key(key_str)
        if not pkey:
            return

        base_key = pkey
        if isinstance(pkey, str) and len(pkey) == 1:
            if pkey.isupper():
                base_key = pkey.lower()
            elif pkey in self.shifted_symbols:
                base_key = self.shifted_symbols[pkey]

        try:
            with self.lock:
                if key_str in self.pressed_keys:
                    self.keyboard.release(base_key)
                    self.pressed_keys.discard(key_str)
                    logger.debug("Released key: %s", key_str)
        except Exception as e:
            logger.error("Failed to release key '%s': %s", key_str, e)

    def press_multiple(self, keys):
        """Simulate pressing multiple keys simultaneously (chords)."""
        for k in keys:
            self.press_key(k)

    def release_multiple(self, keys):
        """Simulate releasing multiple keys simultaneously."""
        for k in keys:
            self.release_key(k)

    def release_all(self):
        """Release all currently pressed keys to avoid stuck notes."""
        with self.lock:
            if not self.pressed_keys:
                return
            
            logger.info("Releasing all active keys (count: %d)...", len(self.pressed_keys))
            for key_str in list(self.pressed_keys):
                pkey = self._get_pynput_key(key_str)
                if pkey:
                    base_key = pkey
                    if isinstance(pkey, str) and len(pkey) == 1:
                        if pkey.isupper():
                            base_key = pkey.lower()
                        elif pkey in self.shifted_symbols:
                            base_key = self.shifted_symbols[pkey]
                    try:
                        self.keyboard.release(base_key)
                        logger.debug("Cleaned up key: %s", key_str)
                    except Exception as e:
                        logger.error("Failed to release key '%s' during cleanup: %s", key_str, e)
            self.pressed_keys.clear()
