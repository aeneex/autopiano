import logging
import mido

logger = logging.getLogger("AutoPiano.MidiReader")

class MidiReader:
    @staticmethod
    def load_midi(filepath):
        """
        Reads a MIDI file and returns a list of dictionaries containing note events
        sorted by absolute time in seconds.
        
        Example note event:
        {
            "time": 0.45,       # Absolute time in seconds from start
            "note": 60,         # MIDI note number
            "type": "on"|"off", # Note action
            "velocity": 100     # Note velocity
        }
        """
        logger.info("Loading MIDI file: %s", filepath)
        try:
            mid = mido.MidiFile(filepath, clip=True)
        except Exception as e:
            logger.error("Failed to load MIDI file '%s': %s", filepath, e)
            raise
        
        ticks_per_beat = mid.ticks_per_beat
        logger.info("MIDI file loaded. Type: %s, Tracks: %d, Ticks per beat: %d", mid.type, len(mid.tracks), ticks_per_beat)
        
        # MIDI default tempo is 500,000 microseconds per beat (120 BPM)
        current_tempo = 500000
        absolute_time = 0.0
        events = []
        
        # Merge all tracks into a single timeline
        merged_messages = mido.merge_tracks(mid.tracks)
        
        for msg in merged_messages:
            delta_ticks = msg.time
            
            # Convert ticks to seconds based on current tempo
            seconds_per_tick = (current_tempo / 1000000.0) / ticks_per_beat
            delta_seconds = delta_ticks * seconds_per_tick
            absolute_time += delta_seconds
            
            # Track tempo changes in the MIDI file
            if msg.type == 'set_tempo':
                current_tempo = msg.tempo
                bpm = mido.tempo2bpm(current_tempo)
                logger.debug("Tempo changed to %d ms/beat (BPM: %.2f) at %.3f seconds", current_tempo, bpm, absolute_time)
            
            # Identify note_on / note_off events
            is_on = (msg.type == 'note_on' and msg.velocity > 0)
            is_off = (msg.type == 'note_off' or (msg.type == 'note_on' and msg.velocity == 0))
            
            if is_on:
                events.append({
                    "time": round(absolute_time, 6),
                    "note": msg.note,
                    "type": "on",
                    "velocity": msg.velocity
                })
            elif is_off:
                events.append({
                    "time": round(absolute_time, 6),
                    "note": msg.note,
                    "type": "off",
                    "velocity": getattr(msg, 'velocity', 0)
                })
        
        # Sort events by absolute time.
        # CRITICAL: If note_off and note_on happen at the exact same timestamp,
        # note_off MUST be processed first to prevent the note from being immediately silenced after press.
        events.sort(key=lambda x: (x["time"], 0 if x["type"] == "off" else 1))
        
        logger.info("Extracted %d note events from MIDI.", len(events))
        return events
