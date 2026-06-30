import time
import logging
import threading

logger = logging.getLogger("AutoPiano.Scheduler")

class MidiScheduler:
    def __init__(self, mapper, player):
        self.mapper = mapper
        self.player = player
        self.events = []
        
        self.current_index = 0
        self.virtual_time = 0.0  # Current position in the MIDI track in seconds
        
        self.state = "STOPPED"  # Can be "STOPPED", "PLAYING", "PAUSED"
        self.playback_speed = 1.0
        self.transposition = 0
        self.humanize = False
        
        self.thread = None
        self.lock = threading.Lock()

    def start(self, events, transposition=0, speed=1.0, humanize=False, start_time=0.0):
        """Starts playback in a background thread."""
        with self.lock:
            if self.state != "STOPPED":
                logger.warning("Playback already in progress or paused. Call stop() first.")
                return False
            
            self.events = events
            self.transposition = transposition
            self.playback_speed = speed
            self.humanize = humanize
            self.state = "PLAYING"
            
            # Seek to start_time
            total_time = self.events[-1]["time"] if self.events else 0.0
            self.virtual_time = max(0.0, min(total_time, start_time))
            new_index = 0
            for idx, event in enumerate(self.events):
                if event["time"] >= self.virtual_time:
                    new_index = idx
                    break
            else:
                new_index = len(self.events)
            self.current_index = new_index
            
            logger.info("Starting playback from %.2fs. Note count: %d, Speed: %.2f, Transposition: %d, Humanize: %s",
                        self.virtual_time, len(events), speed, transposition, humanize)
            
            self.thread = threading.Thread(target=self._run_loop, name="PlaybackThread", daemon=True)
            self.thread.start()
            return True

    def pause(self):
        """Pauses playback."""
        with self.lock:
            if self.state == "PLAYING":
                self.state = "PAUSED"
                self.player.release_all()  # Prevent stuck notes while paused
                logger.info("Playback paused.")
                return True
            return False

    def resume(self):
        """Resumes playback."""
        with self.lock:
            if self.state == "PAUSED":
                self.state = "PLAYING"
                logger.info("Playback resumed.")
                return True
            return False

    def stop(self):
        """Stops playback completely."""
        with self.lock:
            if self.state != "STOPPED":
                self.state = "STOPPED"
                logger.info("Playback stopped.")
                # The thread will clean up and release keys
                if self.thread and self.thread.is_alive():
                    # Wait briefly for thread to exit, but don't block indefinitely
                    self.thread.join(timeout=0.5)
                self.player.release_all()
                return True
            return False

    def set_speed(self, speed):
        """Updates the playback speed multiplier dynamically."""
        with self.lock:
            self.playback_speed = max(0.1, min(5.0, speed))
            logger.info("Playback speed updated to: %.2f", self.playback_speed)

    def set_transposition(self, transposition):
        """Updates the transposition dynamically."""
        with self.lock:
            self.transposition = transposition
            logger.info("Transposition updated to: %d semitones", self.transposition)

    def set_humanize(self, humanize):
        """Updates the humanize setting dynamically."""
        with self.lock:
            self.humanize = humanize
            logger.info("Humanize mode updated to: %s", self.humanize)

    def get_progress(self):
        """Returns the current playback progress as a tuple: (current_time, total_time, current_index, total_notes)."""
        with self.lock:
            total_time = self.events[-1]["time"] if self.events else 0.0
            return (self.virtual_time, total_time, self.current_index, len(self.events))

    def seek(self, target_time):
        """Seeks to a specific target time in seconds."""
        with self.lock:
            if not self.events:
                return
            
            total_time = self.events[-1]["time"] if self.events else 0.0
            target_time = max(0.0, min(total_time, target_time))
            self.virtual_time = target_time
            
            # Find the new index in events where event["time"] >= target_time
            new_index = 0
            for idx, event in enumerate(self.events):
                if event["time"] >= target_time:
                    new_index = idx
                    break
            else:
                new_index = len(self.events)
                
            self.current_index = new_index
            logger.info("Seeked to %.2fs (index %d/%d)", target_time, self.current_index, len(self.events))
            
            # Release all currently active keys
            self.player.release_all()

    def _run_loop(self):
        """Main execution loop for playing MIDI notes with high precision."""
        logger.info("Playback thread loop running.")
        last_real_time = time.perf_counter()
        
        # Set Windows timer resolution to 1ms
        from utils import set_high_precision_timer, restore_timer_precision
        set_high_precision_timer()
        
        try:
            while True:
                # Check for stop state
                with self.lock:
                    if self.state == "STOPPED":
                        break
                    if self.current_index >= len(self.events):
                        logger.info("All events played. Stopping playback.")
                        self.state = "STOPPED"
                        break
                    
                    # Read current settings inside lock
                    current_state = self.state
                    speed = self.playback_speed
                    transposition = self.transposition
                    humanize = self.humanize
 
                if current_state == "PAUSED":
                    time.sleep(0.01)
                    last_real_time = time.perf_counter()
                    continue
                
                # Calculate time elapsed
                now = time.perf_counter()
                real_dt = now - last_real_time
                last_real_time = now
                
                # Advance virtual time
                virtual_dt = real_dt * speed
                with self.lock:
                    self.virtual_time += virtual_dt
                
                # Gather all events due up to current virtual_time
                due_events = []
                with self.lock:
                    while self.current_index < len(self.events) and self.events[self.current_index]["time"] <= self.virtual_time:
                        due_events.append(self.events[self.current_index])
                        self.current_index += 1
                
                # Execute due events
                if due_events:
                    keys_to_press = []
                    keys_to_release = []
                    
                    for event in due_events:
                        note = event["note"]
                        key = self.mapper.get_key(note, transposition)
                        if key:
                            if event["type"] == "on":
                                keys_to_press.append(key)
                            elif event["type"] == "off":
                                keys_to_release.append(key)
                    
                    if keys_to_release or keys_to_press:
                        if humanize:
                            import random
                            # Release keys with a minor random roll
                            for k in keys_to_release:
                                self.player.release_key(k)
                                time.sleep(random.uniform(0.001, 0.005))
                            # Press keys with a minor random roll
                            for k in keys_to_press:
                                self.player.press_key(k)
                                time.sleep(random.uniform(0.002, 0.010))
                        else:
                            # Standard chord press (instant sequential)
                            if keys_to_release:
                                self.player.release_multiple(keys_to_release)
                            if keys_to_press:
                                self.player.press_multiple(keys_to_press)

                # Precision hybrid sleep calculation
                with self.lock:
                    if self.current_index < len(self.events):
                        next_event_time = self.events[self.current_index]["time"]
                        virtual_to_next = next_event_time - self.virtual_time
                        real_to_next = virtual_to_next / speed
                    else:
                        real_to_next = 0.0
                
                if real_to_next > 0:
                    target_real_time = now + real_to_next
                    # Sleep for the bulk of time (leaving 1.2ms for precision spinning)
                    if real_to_next > 0.002:
                        time.sleep(real_to_next - 0.0012)
                    
                    # Spin wait for the exact moment
                    while time.perf_counter() < target_real_time:
                        with self.lock:
                            if self.state == "STOPPED" or self.state == "PAUSED":
                                break
                            
        except Exception as e:
            logger.exception("Error occurred in playback loop: %s", e)
        finally:
            self.player.release_all()
            restore_timer_precision()
            with self.lock:
                self.state = "STOPPED"
            logger.info("Playback thread loop ended.")
