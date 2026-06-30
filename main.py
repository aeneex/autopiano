import os
import sys
import time
import logging
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
from pynput.keyboard import Listener, Key

# Import Auto Piano Player Core Modules
from utils import setup_logging, set_high_precision_timer, restore_timer_precision
from config import ConfigManager
from player import Player
from mapper import KeyboardMapper
from scheduler import MidiScheduler
from midi_reader import MidiReader
from calibrator import KeyboardCalibrator

# Set up logging
setup_logging()
logger = logging.getLogger("AutoPiano.GUI")

# Core singletons
config = ConfigManager()
player = Player()
mapper = KeyboardMapper(config.get("mapping"))
scheduler = MidiScheduler(mapper, player)

# Global variables for GUI sync
loaded_events = []
loaded_midi_name = "None"
cancel_countdown = False
countdown_active = False
global_hotkeys_enabled = True

class AutoPianoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Auto Piano Player")
        self.root.geometry("450x660")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e2e")
        
        # Style variables
        self.status_var = tk.StringVar(value="STOPPED")
        self.song_var = tk.StringVar(value="No MIDI file loaded")
        self.speed_var = tk.DoubleVar(value=config.get("playback_speed"))
        self.transpose_var = tk.IntVar(value=config.get("transposition"))
        self.humanize_var = tk.BooleanVar(value=config.get("humanize"))
        delay_val = config.get("start_delay")
        if delay_val is None:
            delay_val = 5
        self.start_delay_var = tk.IntVar(value=delay_val)
        self.start_time = 0.0
        
        self.overlay = None
        
        # Build UI layout
        self.build_ui()
        
        # Start periodic GUI updates
        self.update_loop()
        
    def build_ui(self):
        # 1. Title Bar
        title_label = tk.Label(self.root, text="🎹 AUTO PIANO PLAYER 🎹", bg="#1e1e2e", fg="#cdd6f4",
                              font=("Segoe UI", 16, "bold"), pady=15)
        title_label.pack(fill="x")
        
        # 2. Status Card Frame
        status_frame = tk.Frame(self.root, bg="#252538", bd=0)
        status_frame.pack(fill="x", padx=20, pady=10)
        
        # Song Info
        song_lbl_title = tk.Label(status_frame, text="Active Song:", bg="#252538", fg="#a6adc8",
                                 font=("Segoe UI", 9))
        song_lbl_title.pack(anchor="w", padx=15, pady=(15, 2))
        
        self.song_lbl = tk.Label(status_frame, textvariable=self.song_var, bg="#252538", fg="#cdd6f4",
                                 font=("Segoe UI", 11, "bold"), wraplength=380, justify="left")
        self.song_lbl.pack(anchor="w", padx=15, pady=(0, 10))
        
        # Status Badge & Progress Text
        status_sub_frame = tk.Frame(status_frame, bg="#252538")
        status_sub_frame.pack(fill="x", padx=15, pady=5)
        
        self.status_badge = tk.Label(status_sub_frame, textvariable=self.status_var, bg="#45475a", fg="#11111b",
                                     font=("Segoe UI", 10, "bold"), width=10, pady=3)
        self.status_badge.pack(side="left")
        self.update_status_badge()
        
        self.progress_lbl = tk.Label(status_sub_frame, text="0.0s / 0.0s (0%)", bg="#252538", fg="#a6adc8",
                                     font=("Segoe UI", 10))
        self.progress_lbl.pack(side="right")
        
        # Progress Bar Canvas
        self.progress_canvas = tk.Canvas(status_frame, height=8, bg="#313244", highlightthickness=0, bd=0, cursor="hand2")
        self.progress_canvas.pack(fill="x", padx=15, pady=(10, 20))
        self.progress_canvas.bind("<Button-1>", self.on_progress_click)
        self.progress_canvas.bind("<B1-Motion>", self.on_progress_click)
        
        # 3. Control Buttons Frame
        controls_frame = tk.Frame(self.root, bg="#1e1e2e")
        controls_frame.pack(fill="x", padx=20, pady=10)
        
        # Styled button template helper
        def make_btn(parent, text, bg, fg, hover_bg, cmd, side="left", expand=True):
            btn = tk.Button(parent, text=text, bg=bg, fg=fg, activebackground=hover_bg, activeforeground=fg,
                            font=("Segoe UI", 10, "bold"), bd=0, relief="flat", cursor="hand2", command=cmd)
            btn.pack(side=side, fill="x", expand=expand, padx=5, ipady=8)
            btn.bind("<Enter>", lambda e: btn.config(bg=hover_bg))
            btn.bind("<Leave>", lambda e: btn.config(bg=bg))
            return btn
            
        row1 = tk.Frame(controls_frame, bg="#1e1e2e")
        row1.pack(fill="x", pady=5)
        self.load_btn = make_btn(row1, "📁 Load MIDI", "#89b4fa", "#11111b", "#b4befe", self.load_midi_dialog)
        self.play_btn = make_btn(row1, "▶️ Play", "#a6e3a1", "#11111b", "#a6e3a1", self.play_song_gui)
        
        row2 = tk.Frame(controls_frame, bg="#1e1e2e")
        row2.pack(fill="x", pady=5)
        self.pause_btn = make_btn(row2, "⏸️ Pause", "#fab387", "#11111b", "#f9e2af", self.pause_song_gui)
        self.stop_btn = make_btn(row2, "⏹️ Stop", "#f38ba8", "#11111b", "#f5e0dc", self.stop_song_gui)
        
        # 4. Settings Card Frame
        settings_frame = tk.Frame(self.root, bg="#252538")
        settings_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        # Speed Scale (Slider)
        speed_frame = tk.Frame(settings_frame, bg="#252538")
        speed_frame.pack(fill="x", padx=15, pady=(15, 5))
        
        speed_lbl = tk.Label(speed_frame, text="Playback Speed", bg="#252538", fg="#cdd6f4", font=("Segoe UI", 9, "bold"))
        speed_lbl.pack(side="left")
        
        self.speed_val_lbl = tk.Label(speed_frame, text=f"{self.speed_var.get():.1f}x", bg="#252538", fg="#89b4fa", font=("Segoe UI", 9, "bold"))
        self.speed_val_lbl.pack(side="right")
        
        self.speed_slider = tk.Scale(settings_frame, from_=0.1, to=5.0, resolution=0.1, orient="horizontal",
                                     variable=self.speed_var, bg="#252538", fg="#cdd6f4", highlightthickness=0, bd=0,
                                     activebackground="#89b4fa", troughcolor="#313244", showvalue=False,
                                     command=self.on_speed_slider_change)
        self.speed_slider.pack(fill="x", padx=15, pady=(0, 10))
        
        # Transpose & Humanize row
        row_settings = tk.Frame(settings_frame, bg="#252538")
        row_settings.pack(fill="x", padx=15, pady=5)
        
        # Transpose Column
        trans_frame = tk.Frame(row_settings, bg="#252538")
        trans_frame.pack(side="left", fill="y", expand=True)
        
        trans_lbl = tk.Label(trans_frame, text="Transposition", bg="#252538", fg="#cdd6f4", font=("Segoe UI", 9, "bold"))
        trans_lbl.pack(anchor="w")
        
        trans_ctrls = tk.Frame(trans_frame, bg="#252538")
        trans_ctrls.pack(anchor="w", pady=5)
        
        dec_btn = tk.Button(trans_ctrls, text="-", bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
                            activeforeground="#cdd6f4", font=("Segoe UI", 10, "bold"), bd=0, width=3, height=1,
                            command=lambda: self.adjust_transpose(-1))
        dec_btn.pack(side="left")
        
        self.trans_val_lbl = tk.Label(trans_ctrls, textvariable=self.transpose_var, bg="#252538", fg="#cdd6f4",
                                      font=("Segoe UI", 10, "bold"), width=4)
        self.trans_val_lbl.pack(side="left", padx=5)
        
        inc_btn = tk.Button(trans_ctrls, text="+", bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
                            activeforeground="#cdd6f4", font=("Segoe UI", 10, "bold"), bd=0, width=3, height=1,
                            command=lambda: self.adjust_transpose(1))
        inc_btn.pack(side="left")
        
        # Humanize Column
        hum_frame = tk.Frame(row_settings, bg="#252538")
        hum_frame.pack(side="right", fill="y", expand=True)
        
        hum_lbl = tk.Label(hum_frame, text="Humanize Mode", bg="#252538", fg="#cdd6f4", font=("Segoe UI", 9, "bold"))
        hum_lbl.pack(anchor="w")
        
        self.hum_toggle = tk.Button(hum_frame, text="OFF", bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
                                    font=("Segoe UI", 10, "bold"), bd=0, width=10, height=1, command=self.toggle_humanize)
        self.hum_toggle.pack(anchor="w", pady=5)
        self.update_humanize_button()
        
        # Start Delay (Countdown) Row
        row_delay = tk.Frame(settings_frame, bg="#252538")
        row_delay.pack(fill="x", padx=15, pady=5)
        
        delay_lbl = tk.Label(row_delay, text="Countdown Delay", bg="#252538", fg="#cdd6f4", font=("Segoe UI", 9, "bold"))
        delay_lbl.pack(side="left")
        
        delay_ctrls = tk.Frame(row_delay, bg="#252538")
        delay_ctrls.pack(side="right")
        
        dec_delay_btn = tk.Button(delay_ctrls, text="-", bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
                                  activeforeground="#cdd6f4", font=("Segoe UI", 10, "bold"), bd=0, width=3, height=1,
                                  command=lambda: self.adjust_start_delay(-1))
        dec_delay_btn.pack(side="left")
        
        self.delay_val_lbl = tk.Label(delay_ctrls, text=f"{self.start_delay_var.get()}s", bg="#252538", fg="#cdd6f4",
                                      font=("Segoe UI", 10, "bold"), width=5)
        self.delay_val_lbl.pack(side="left", padx=5)
        
        inc_delay_btn = tk.Button(delay_ctrls, text="+", bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
                                  activeforeground="#cdd6f4", font=("Segoe UI", 10, "bold"), bd=0, width=3, height=1,
                                  command=lambda: self.adjust_start_delay(1))
        inc_delay_btn.pack(side="left")
        
        # Mapping file and Calibration
        row_mapping = tk.Frame(settings_frame, bg="#252538")
        row_mapping.pack(fill="x", padx=15, pady=(10, 5))
        
        calib_btn = tk.Button(row_mapping, text="🎯 Calibrate Keyboard", bg="#f5c2e7", fg="#11111b",
                              activebackground="#f5bde6", font=("Segoe UI", 9, "bold"), bd=0, height=1,
                              command=self.open_calibration_dialog)
        calib_btn.pack(fill="x", ipady=5)
        
        # Presets Frame
        row_presets = tk.Frame(settings_frame, bg="#252538")
        row_presets.pack(fill="x", padx=15, pady=(5, 15))
        
        preset_lbl = tk.Label(row_presets, text="Quick Presets / Reset Mapping:", bg="#252538", fg="#cdd6f4",
                              font=("Segoe UI", 9, "bold"))
        preset_lbl.pack(anchor="w", pady=(0, 5))
        
        preset_btn_frame = tk.Frame(row_presets, bg="#252538")
        preset_btn_frame.pack(fill="x")
        
        btn_35 = tk.Button(preset_btn_frame, text="35-Key Flat", bg="#45475a", fg="#cdd6f4",
                           activebackground="#585b70", activeforeground="#cdd6f4",
                           font=("Segoe UI", 8, "bold"), bd=0, relief="flat", cursor="hand2",
                           command=lambda: self.apply_preset("presets/virtual_piano_35.json"))
        btn_35.pack(side="left", fill="x", expand=True, padx=(0, 5), ipady=4)
        
        btn_61 = tk.Button(preset_btn_frame, text="61-Key Shifted", bg="#45475a", fg="#cdd6f4",
                           activebackground="#585b70", activeforeground="#cdd6f4",
                           font=("Segoe UI", 8, "bold"), bd=0, relief="flat", cursor="hand2",
                           command=lambda: self.apply_preset("presets/virtual_piano_61.json"))
        btn_61.pack(side="right", fill="x", expand=True, padx=(5, 0), ipady=4)
        
        # 5. Footer (Hotkeys legend)
        legend_frame = tk.Frame(self.root, bg="#11111b", pady=8)
        legend_frame.pack(fill="x", side="bottom")
        
        legend_lbl = tk.Label(legend_frame, text="Global Hotkeys: [F6] Load | [F7] Play | [F8] Pause | [F9] Stop | [F10] Speed- | [F11] Speed+\nLocal Hotkey: [ESC] Exit (when focused)",
                              bg="#11111b", fg="#a6adc8", font=("Segoe UI", 8))
        legend_lbl.pack()

    def update_status_badge(self):
        state = self.status_var.get()
        if state == "PLAYING":
            self.status_badge.config(bg="#a6e3a1", fg="#11111b")
        elif state == "PAUSED":
            self.status_badge.config(bg="#fab387", fg="#11111b")
        else:
            self.status_badge.config(bg="#45475a", fg="#cdd6f4")
            
    def update_humanize_button(self):
        enabled = self.humanize_var.get()
        if enabled:
            self.hum_toggle.config(text="ON", bg="#a6e3a1", fg="#11111b")
        else:
            self.hum_toggle.config(text="OFF", bg="#45475a", fg="#cdd6f4")

    def load_midi_dialog(self):
        """Opens file browser to load a MIDI file."""
        filepath = filedialog.askopenfilename(
            filetypes=[("MIDI Files", "*.mid;*.midi"), ("All Files", "*.*")]
        )
        if filepath:
            self.load_midi_file(filepath)

    def load_midi_file(self, filepath):
        """Loads selected MIDI file into the app."""
        global loaded_events, loaded_midi_name
        try:
            loaded_events = MidiReader.load_midi(filepath)
            loaded_midi_name = os.path.basename(filepath)
            self.song_var.set(loaded_midi_name)
            self.start_time = 0.0
            logger.info("Song loaded: %s", loaded_midi_name)
        except Exception as e:
            messagebox.showerror("MIDI Error", f"Failed to parse MIDI file:\n{e}")

    def play_song_gui(self):
        """Starts or resumes playback."""
        if not loaded_events:
            messagebox.showwarning("Warning", "Please load a MIDI file first.")
            return

        if scheduler.state == "PAUSED":
            scheduler.resume()
            return
            
        if scheduler.state == "PLAYING":
            return
            
        # Start countdown
        threading.Thread(target=self.run_play_countdown, daemon=True).start()

    def run_play_countdown(self):
        global cancel_countdown, countdown_active
        if countdown_active:
            return
        
        countdown_active = True
        cancel_countdown = False
        
        # Visual countdown on main thread
        start_delay = self.start_delay_var.get()
        for i in range(start_delay, 0, -1):
            if cancel_countdown:
                countdown_active = False
                self.song_var.set(loaded_midi_name)
                return
            self.song_var.set(f"⏳ Focus piano window! Starting in {i}s...")
            time.sleep(1)
            
        if cancel_countdown:
            countdown_active = False
            self.song_var.set(loaded_midi_name)
            return

        countdown_active = False
        self.song_var.set(loaded_midi_name)
        
        # Start playback in background scheduler thread
        scheduler.start(
            loaded_events,
            transposition=self.transpose_var.get(),
            speed=self.speed_var.get(),
            humanize=self.humanize_var.get(),
            start_time=self.start_time
        )

    def pause_song_gui(self):
        if scheduler.state == "PAUSED":
            scheduler.resume()
        else:
            scheduler.pause()

    def stop_song_gui(self):
        global cancel_countdown
        cancel_countdown = True
        scheduler.stop()
        self.start_time = 0.0

    def update_speed_display(self, speed):
        self.speed_val_lbl.config(text=f"{speed:.1f}x")
        if self.overlay is not None and hasattr(self, 'overlay_speed_lbl'):
            self.overlay_speed_lbl.config(text=f"{speed:.1f}x")

    def on_speed_slider_change(self, val):
        speed = float(val)
        self.update_speed_display(speed)
        config.set("playback_speed", speed)
        scheduler.set_speed(speed)

    def increase_speed_gui(self):
        current_speed = self.speed_var.get()
        new_speed = min(5.0, round(current_speed + 0.1, 1))
        self.speed_var.set(new_speed)
        self.update_speed_display(new_speed)
        config.set("playback_speed", new_speed)
        scheduler.set_speed(new_speed)

    def decrease_speed_gui(self):
        current_speed = self.speed_var.get()
        new_speed = max(0.1, round(current_speed - 0.1, 1))
        self.speed_var.set(new_speed)
        self.update_speed_display(new_speed)
        config.set("playback_speed", new_speed)
        scheduler.set_speed(new_speed)

    def adjust_transpose(self, delta):
        val = self.transpose_var.get() + delta
        self.transpose_var.set(val)
        config.set("transposition", val)
        scheduler.set_transposition(val)

    def toggle_humanize(self):
        val = not self.humanize_var.get()
        self.humanize_var.set(val)
        config.set("humanize", val)
        scheduler.set_humanize(val)
        self.update_humanize_button()

    def adjust_start_delay(self, delta):
        val = max(0, self.start_delay_var.get() + delta)
        self.start_delay_var.set(val)
        config.set("start_delay", val)
        self.delay_val_lbl.config(text=f"{val}s")

    def apply_preset(self, preset_path):
        """Loads a preset mapping file and overwrites the active mapping."""
        base_dir = os.path.dirname(os.path.abspath(__file__))
        full_preset_path = os.path.join(base_dir, preset_path)
        
        if not os.path.exists(full_preset_path):
            messagebox.showerror("Error", f"Preset file not found at:\n{full_preset_path}")
            return
            
        try:
            import json
            with open(full_preset_path, 'r', encoding='utf-8') as f:
                preset_data = json.load(f)
                
            active_mapping_path = os.path.join(base_dir, config.get("mapping"))
            os.makedirs(os.path.dirname(active_mapping_path), exist_ok=True)
            
            with open(active_mapping_path, 'w', encoding='utf-8') as f:
                json.dump(preset_data, f, indent=4)
                
            mapper.load_mapping()
            messagebox.showinfo("Success", f"Applied Preset: {os.path.basename(preset_path)}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to apply preset: {e}")

    def show_overlay(self):
        """Creates the floating bottom-right controls overlay."""
        if self.overlay is not None:
            return
            
        self.overlay = tk.Toplevel(self.root)
        self.overlay.title("Auto Piano Overlay")
        
        # Borderless, always on top, semi-transparent
        self.overlay.overrideredirect(True)
        self.overlay.attributes("-topmost", True)
        self.overlay.attributes("-alpha", 0.88)
        self.overlay.configure(bg="#252538")
        
        # Position at bottom-right of primary screen
        screen_width = self.overlay.winfo_screenwidth()
        screen_height = self.overlay.winfo_screenheight()
        overlay_width = 300
        overlay_height = 125
        
        x = screen_width - overlay_width - 30
        y = screen_height - overlay_height - 60
        self.overlay.geometry(f"{overlay_width}x{overlay_height}+{x}+{y}")
        
        # Layout components
        title_frame = tk.Frame(self.overlay, bg="#252538")
        title_frame.pack(fill="x", padx=12, pady=(10, 2))
        
        self.overlay_song_lbl = tk.Label(title_frame, text="", bg="#252538", fg="#cdd6f4",
                                         font=("Segoe UI", 9, "bold"))
        self.overlay_song_lbl.pack(side="left")
        
        restore_btn = tk.Button(title_frame, text="✖", bg="#45475a", fg="#f38ba8", activebackground="#f38ba8",
                                activeforeground="#11111b", font=("Segoe UI", 8, "bold"), bd=0, relief="flat",
                                cursor="hand2", width=3, command=self.stop_song_gui)
        restore_btn.pack(side="right")
        
        self.overlay_progress_lbl = tk.Label(self.overlay, text="0.0s / 0.0s (0%)", bg="#252538", fg="#a6adc8",
                                             font=("Segoe UI", 8))
        self.overlay_progress_lbl.pack(anchor="w", padx=12)
        
        self.overlay_canvas = tk.Canvas(self.overlay, height=8, bg="#313244", highlightthickness=0, bd=0, cursor="hand2")
        self.overlay_canvas.pack(fill="x", padx=12, pady=(5, 5))
        self.overlay_canvas.bind("<Button-1>", self.on_progress_click)
        self.overlay_canvas.bind("<B1-Motion>", self.on_progress_click)
        
        # Speed changer row
        speed_frame = tk.Frame(self.overlay, bg="#252538")
        speed_frame.pack(fill="x", padx=12, pady=(2, 5))
        
        speed_lbl = tk.Label(speed_frame, text="Speed:", bg="#252538", fg="#cdd6f4", font=("Segoe UI", 8, "bold"))
        speed_lbl.pack(side="left")
        
        self.overlay_speed_dec_btn = tk.Button(speed_frame, text="-", bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
                                               activeforeground="#cdd6f4", font=("Segoe UI", 8, "bold"), bd=0, width=3, height=1,
                                               command=self.decrease_speed_gui)
        self.overlay_speed_dec_btn.pack(side="left", padx=(10, 5))
        
        self.overlay_speed_lbl = tk.Label(speed_frame, text=f"{self.speed_var.get():.1f}x", bg="#252538", fg="#89b4fa",
                                          font=("Segoe UI", 8, "bold"), width=5)
        self.overlay_speed_lbl.pack(side="left")
        
        self.overlay_speed_inc_btn = tk.Button(speed_frame, text="+", bg="#45475a", fg="#cdd6f4", activebackground="#585b70",
                                               activeforeground="#cdd6f4", font=("Segoe UI", 8, "bold"), bd=0, width=3, height=1,
                                               command=self.increase_speed_gui)
        self.overlay_speed_inc_btn.pack(side="left", padx=5)
        
        hint_lbl = tk.Label(self.overlay, text="[F8] Pause/Resume  |  [F9] Stop/Restore", bg="#252538", fg="#89b4fa",
                            font=("Segoe UI", 8, "bold"))
        hint_lbl.pack(fill="x", side="bottom", pady=(0, 8))

    def hide_overlay(self):
        """Destroys the overlay window."""
        if self.overlay is not None:
            try:
                self.overlay.destroy()
            except Exception:
                pass
            self.overlay = None


    def open_calibration_dialog(self):
        """Opens a modal calibration window."""
        global global_hotkeys_enabled
        global_hotkeys_enabled = False # Disable hotkeys
        
        calib_win = tk.Toplevel(self.root)
        calib_win.title("Keyboard Calibrator")
        calib_win.geometry("380x280")
        calib_win.resizable(False, False)
        calib_win.configure(bg="#1e1e2e")
        calib_win.transient(self.root)
        calib_win.grab_set() # Force modal focus
        
        # Layout variables
        start_note = 36
        end_note = 96
        current_note_idx = [start_note] # Mutability wrapper
        new_mapping = {}

        # Labels
        title_lbl = tk.Label(calib_win, text="🎯 Keyboard Calibration", bg="#1e1e2e", fg="#f5c2e7",
                             font=("Segoe UI", 12, "bold"), pady=10)
        title_lbl.pack()
        
        instruction_lbl = tk.Label(calib_win, text="Focus this window and press the physical key\ncorresponding to the requested note.",
                                   bg="#1e1e2e", fg="#a6adc8", font=("Segoe UI", 9), justify="center")
        instruction_lbl.pack(pady=10)

        note_lbl = tk.Label(calib_win, text="", bg="#252538", fg="#cdd6f4", font=("Segoe UI", 14, "bold"),
                            width=20, pady=10, bd=0)
        note_lbl.pack(pady=10)
        
        prompt_lbl = tk.Label(calib_win, text="Press 'ESC' at any time to cancel.", bg="#1e1e2e", fg="#a6adc8",
                              font=("Segoe UI", 8, "italic"))
        prompt_lbl.pack(side="bottom", pady=10)

        def update_prompt():
            note = current_note_idx[0]
            name = KeyboardCalibrator.midi_note_to_name(note)
            note_lbl.config(text=f"Note: {name} (MIDI {note})")

        def on_key_press(event):
            # Ignore modifier keys (Shift, Control, Alt, Caps Lock)
            if event.keysym in ("Shift_L", "Shift_R", "Control_L", "Control_R", "Alt_L", "Alt_R", "Caps_Lock", "Num_Lock"):
                return
                
            # Exit on escape
            if event.keysym == "Escape":
                cleanup(save=False)
                return
            
            # Extract key representation
            key_val = event.char
            if not key_val:
                # Capture named keysyms for special keys (like spaces)
                key_val = event.keysym.lower()
            
            # Standardize names
            if key_val == "space":
                key_val = "space"
            elif key_val == "return":
                key_val = "enter"
            
            # Save mapping
            new_mapping[str(current_note_idx[0])] = key_val
            logger.info("Mapped note %d to key '%s'", current_note_idx[0], key_val)
            
            # Advance or finish
            if current_note_idx[0] < end_note:
                current_note_idx[0] += 1
                update_prompt()
            else:
                cleanup(save=True)

        def cleanup(save=True):
            global global_hotkeys_enabled
            if save and new_mapping:
                # Save mapping
                calibrator = KeyboardCalibrator(config.get("mapping"))
                calibrator.save_mapping(new_mapping)
                mapper.load_mapping()
                messagebox.showinfo("Success", "Calibration saved successfully!")
            
            global_hotkeys_enabled = True # Enable hotkeys back
            calib_win.destroy()

        calib_win.bind("<Key>", on_key_press)
        update_prompt()

    def update_progress_display(self, curr_time, tot_time):
        pct = int((curr_time / tot_time * 100)) if tot_time > 0 else 0
        progress_text = f"{curr_time:.1f}s / {tot_time:.1f}s ({pct}%)"
        self.progress_lbl.config(text=progress_text)
        
        # Redraw custom progress bar
        self.progress_canvas.delete("bar")
        width = self.progress_canvas.winfo_width()
        ratio = min(1.0, curr_time / tot_time) if tot_time > 0 else 0.0
        fill_width = int(width * ratio)
        if fill_width > 0:
            self.progress_canvas.create_rectangle(0, 0, fill_width, 8, fill="#89b4fa", outline="", tags="bar")

    def on_progress_click(self, event):
        if not loaded_events:
            return
        
        canvas = event.widget
        width = canvas.winfo_width()
        if width <= 0:
            return
        
        ratio = max(0.0, min(1.0, event.x / width))
        total_time = loaded_events[-1]["time"] if loaded_events else 0.0
        target_time = ratio * total_time
        
        state = scheduler.state
        if state in ("PLAYING", "PAUSED"):
            scheduler.seek(target_time)
        else:
            self.start_time = target_time
            self.update_progress_display(target_time, total_time)

    def update_ui_state(self):
        """Thread-safe UI states sync polling."""
        # Update playback state
        state = scheduler.state
        if countdown_active:
            self.status_var.set("COUNTDOWN")
        else:
            self.status_var.set(state)
        self.update_status_badge()
        
        # Update progress and draw bar
        curr_time, tot_time, curr_idx, tot_notes = scheduler.get_progress()
        if state != "STOPPED":
            self.update_progress_display(curr_time, tot_time)
            ratio = min(1.0, curr_time / tot_time) if tot_time > 0 else 0.0
            progress_text = f"{curr_time:.1f}s / {tot_time:.1f}s ({int(ratio*100)}%)"
        else:
            # Stopped state: use start_time
            tot_time = loaded_events[-1]["time"] if loaded_events else 0.0
            self.update_progress_display(self.start_time, tot_time)
            ratio = min(1.0, self.start_time / tot_time) if tot_time > 0 else 0.0
            progress_text = f"{self.start_time:.1f}s / {tot_time:.1f}s ({int(ratio*100)}%)"
            
        # Manage Overlay & Minimize transition
        if state in ("PLAYING", "PAUSED") and not countdown_active:
            if self.overlay is None:
                self.show_overlay()
                self.root.iconify()
        else:
            if self.overlay is not None:
                self.hide_overlay()
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                
        # Update overlay labels if active
        if self.overlay is not None:
            # Update song text dynamically with status
            song_name = loaded_midi_name
            if len(song_name) > 22:
                song_name = song_name[:19] + "..."
            self.overlay_song_lbl.config(text=f"[{state}] {song_name}")
            
            # Progress text and bar
            self.overlay_progress_lbl.config(text=progress_text)
            self.overlay_canvas.delete("bar")
            owidth = self.overlay_canvas.winfo_width()
            ofill_width = int(owidth * ratio)
            if ofill_width > 0:
                self.overlay_canvas.create_rectangle(0, 0, ofill_width, 8, fill="#89b4fa", outline="", tags="bar")

    def update_loop(self):
        self.update_ui_state()
        self.root.after(100, self.update_loop)

# Global variables to handle GUI reference for hotkeys
app_ref = None

def trigger_play_safe():
    if app_ref:
        app_ref.root.after(0, app_ref.play_song_gui)

def trigger_pause_safe():
    if app_ref:
        app_ref.root.after(0, app_ref.pause_song_gui)

def trigger_stop_safe():
    if app_ref:
        app_ref.root.after(0, app_ref.stop_song_gui)

def trigger_load_safe():
    if app_ref:
        app_ref.root.after(0, app_ref.load_midi_dialog)

def trigger_speed_up_safe():
    if app_ref:
        app_ref.root.after(0, app_ref.increase_speed_gui)

def trigger_speed_down_safe():
    if app_ref:
        app_ref.root.after(0, app_ref.decrease_speed_gui)

def trigger_exit_safe():
    if app_ref:
        app_ref.root.after(0, app_ref.root.destroy)

def on_hotkey_press(key):
    """pynput global hotkeys listener callback."""
    if not global_hotkeys_enabled:
        return True

    try:
        if key == Key.f6:
            trigger_load_safe()
        elif key == Key.f7:
            trigger_play_safe()
        elif key == Key.f8:
            trigger_pause_safe()
        elif key == Key.f9:
            trigger_stop_safe()
        elif key == Key.f10:
            trigger_speed_down_safe()
        elif key == Key.f11:
            trigger_speed_up_safe()
    except Exception as e:
        logger.error("Error in hotkey handler: %s", e)
    return True

if __name__ == "__main__":
    # Configure Windows high resolution timer
    set_high_precision_timer()
    
    # Initialize Tkinter Window
    root = tk.Tk()
    app = AutoPianoApp(root)
    app_ref = app
    
    # Bind Escape key locally so it only triggers exit when the window is active/focused
    root.bind("<Escape>", lambda event: trigger_exit_safe())
    
    # Start background global hotkeys listener
    hotkey_listener = Listener(on_press=on_hotkey_press)
    hotkey_listener.start()
    
    try:
        # Run standard Tkinter event loop
        root.mainloop()
    finally:
        # Stop playback, cleanup hotkeys and restore timer precision on exit
        scheduler.stop()
        hotkey_listener.stop()
        restore_timer_precision()
        logger.info("Application shut down cleanly.")
