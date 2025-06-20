import customtkinter as ctk 
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import subprocess
import threading
import time
import platform
import json
import hashlib
import re
from pathlib import Path
from datetime import datetime
import webbrowser
import traceback
import numpy as np 
import math 

# --- Costanti di Configurazione Generale (Mantenute dal tuo file originale) ---
class Config:
    DEFAULT_APP_WIDTH = 1000  
    DEFAULT_APP_HEIGHT = 700  
    MIN_APP_WIDTH = 600       
    MIN_APP_HEIGHT = 500      

    UI_PADDING = 10         
    BUTTON_PADDING = 5      
    SECTION_TITLE_FONT_SIZE = 14 
    SUB_LABEL_FONT_SIZE = 9     
    BOLD_FONT_WEIGHT = "bold"   

    BONZOMATIC_EXECUTABLE_NAME = "Bonzomatic_W64_DX11.exe" 
    BONZOMATIC_DEFAULT_WINDOW_TITLE = "Bonzomatic"      
    BONZOMATIC_WINDOW_DETECT_TIMEOUT = 10               
    PROCESS_SCAN_SLEEP_SECONDS = 0.5                    
    BONZOMATIC_STOP_GRACEFUL_WAIT_SECONDS = 3           
    BONZOMATIC_TERMINATE_TIMEOUT = 5                    
    BONZOMATIC_MONITOR_INTERVAL_SECONDS = 1             
    SUBPROCESS_CREATE_NO_WINDOW_FLAG = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
    BONZOMATIC_LIVE_SHADER_FILENAME = "live_shader.frag" 
    BONZOMATIC_PARAMS_FILENAME = "bonzomatic_params.txt" 

    AUDIO_DEFAULT_SAMPLE_RATE = 44100   
    AUDIO_DEFAULT_CHUNK_SIZE = 1024     
    AUDIO_DEFAULT_CHANNELS = 1          
    AUDIO_DEFAULT_NOISE_THRESHOLD = 0.01 
    AUDIO_DEFAULT_BPM_RANGE = [60, 200]  
    AUDIO_DEFAULT_BEAT_SENSITIVITY = 0.5 
    AUDIO_DEFAULT_BASS_FREQ_RANGE = [20, 250] 
    AUDIO_ANALYSIS_THREAD_SLEEP_SECONDS = 0.05 
    AUDIO_SYNC_LOOP_SLEEP_SECONDS = 0.1 
    MIN_BEAT_INTERVAL_SECONDS = 0.1     
    MAX_BEAT_TIMES_FOR_BPM = 8          
    MIN_BEATS_FOR_BPM_CALC = 4          
    TAP_TEMPO_RESET_THRESHOLD_SECONDS = 2.0 
    BPM_SMOOTHING_FACTOR = 0.2          
    BASS_LEVEL_EFFECT_THRESHOLD = 0.1   

    SHADER_CACHE_FILENAME = "shader_cache.json"         
    SHADER_SUPPORTED_EXTENSIONS = ['.frag', '.glsl', '.fs', '.shader'] 
    SHADER_TITLE_TRUNCATE_LENGTH = 27                   
    MIN_SHADER_CODE_SIZE_KB = 0                         
    SHADER_CACHE_CLEANUP_THRESHOLD = 1000               

    SHADERTOY_DEFAULT_URL = "https://www.shadertoy.com"  
    SHADERTOY_VALID_URL_CHECK = 'shadertoy.com'           
    SHADERTOY_API_KEY_MIN_LENGTH = 10                     
    SHADERTOY_ID_MIN_LENGTH = 6                         
    SHADERTOY_REQUEST_TIMEOUT = 15                      
    SHADERTOY_BROWSER_WAIT_SECONDS = 10                 
    SHADERTOY_MIN_SHADER_CODE_LENGTH = 50               
    
    VMIX_DEFAULT_WINDOW_ALWAYS_ON_TOP = False
    VMIX_DEFAULT_TRANSPARENT_BACKGROUND = False
    VMIX_OUTPUT_RESOLUTION = (1920, 1080)
    VMIX_SCALING_MODE = "fit"
    MIN_SYSTEMS_FOR_INTEGRATION = 1
    RESIZE_HANDLE_SIZE = 20
    VMIX_OPTIMIZE_INTERVAL_SECONDS = 1.0
    AUDIO_CHUNK_SIZE_MAX_OPTIMIZED = 2048

    EFFECTS_SECTION_TITLE_FONT_SIZE = 14
    EFFECTS_ZOOM_DEFAULT = 1.0
    EFFECTS_ZOOM_MIN = 0.5
    EFFECTS_ZOOM_MAX = 2.0
    EFFECTS_PAN_DEFAULT = 0.0
    EFFECTS_PAN_MIN = -0.5
    EFFECTS_PAN_MAX = 0.5
    EFFECTS_ROTATION_DEFAULT = 0.0
    EFFECTS_ROTATION_MIN = 0.0
    EFFECTS_ROTATION_MAX = 1.0 # 0 a 1 per 360 gradi
    EFFECTS_DISTORTION_DEFAULT = 0.0
    EFFECTS_DISTORTION_MIN = 0.0
    EFFECTS_DISTORTION_MAX = 0.1


try:
    import pyaudio 
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False
    print("ATTENZIONE: Librerie audio non disponibili. Le funzioni audio saranno disabilitate.")

WIN32GUI_AVAILABLE = False
if platform.system() == "Windows":
    try:
        import win32gui 
        WIN32GUI_AVAILABLE = True
    except ImportError:
        print("ATTENZIONE: Libreria 'pywin32' non disponibile. Alcune funzioni di controllo finestra Bonzomatic su Windows saranno limitate.")


ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class ShaderBridgePlayer:
    def __init__(self, root):
        print("Inizio inizializzazione ShaderBridgePlayer (Fase GUI di base)...")
        self.root = root 
        self.root.title("Shader Bridge Player v1.0 (Essenziale)") 
        self.root.geometry(f"{Config.DEFAULT_APP_WIDTH}x{Config.DEFAULT_APP_HEIGHT}")
        self.root.minsize(Config.MIN_APP_WIDTH, Config.MIN_APP_HEIGHT)
        
        # --- Variabili di Stato dell'Applicazione ---
        self.shader_folder = "" 
        self.current_shader = "" 
        self.bonzomatic_process = None 
        self.bonzomatic_path = "" 
        self.bonzomatic_window_handle = None 
        self.bonzomatic_monitor_active = False 
        self.audio_input = "Microfono" 
        self.scale_factor = 1.0 
        self.shadertoy_connected = False 
        self.browser_driver = None 

        # --- Configurazioni Moduli (usano costanti globali da Config) ---
        self.bonzomatic_config = {
            "executable": Config.BONZOMATIC_EXECUTABLE_NAME,
            "arguments": [],
            "working_dir": "",
            "window_title": Config.BONZOMATIC_DEFAULT_WINDOW_TITLE,
            "auto_find": True,
            "live_shader_path": Config.BONZOMATIC_LIVE_SHADER_FILENAME
        }
        self.file_manager_config = {
            "cache_enabled": True,
            "recursive_scan": True,
            "max_cache_size": Config.SHADER_CACHE_CLEANUP_THRESHOLD
        }
        self.audio_config = {
            "sample_rate": Config.AUDIO_DEFAULT_SAMPLE_RATE, "chunk_size": Config.AUDIO_DEFAULT_CHUNK_SIZE,
            "channels": Config.AUDIO_DEFAULT_CHANNELS, "format": pyaudio.paFloat32 if AUDIO_AVAILABLE else None,
            "input_device": None, "auto_gain": True, "noise_threshold": Config.AUDIO_DEFAULT_NOISE_THRESHOLD,
            "bpm_range": Config.AUDIO_DEFAULT_BPM_RANGE, "beat_sensitivity": Config.AUDIO_DEFAULT_BEAT_SENSITIVITY,
            "bass_freq_range": Config.AUDIO_DEFAULT_BASS_FREQ_RANGE, "enable_fft": True
        }
        self.shadertoy_config = {
            "browser_type": "chrome", "headless": False, "auto_fullscreen": True,
            "api_key": "", 
            "default_url": Config.SHADERTOY_DEFAULT_URL
        }
        self.vmix_config = {
            "window_always_on_top": Config.VMIX_DEFAULT_WINDOW_ALWAYS_ON_TOP,
            "transparent_background": Config.VMIX_DEFAULT_TRANSPARENT_BACKGROUND,
            "output_resolution": Config.VMIX_OUTPUT_RESOLUTION, "scaling_mode": Config.VMIX_SCALING_MODE
        }
        
        # --- Variabili di Stato dell'Audio Engine ---
        self.audio_stream = None
        self.audio_thread = None
        self.audio_recording = False
        self.current_bpm = 120
        self.beat_detected = False
        self.audio_level = 0.0
        self.frequency_data = []
        self.bass_level = 0.0
        self.tap_tempo_times = [] 
        self.auto_bpm_enabled = False
        self.beat_sync_enabled = False
        self.bass_response_enabled = False
        self.audio_meter_level = 0.0 

        # --- Variabili di Stato Effetti Video ---
        self.effects_config_runtime = {
            "zoom": {"value": Config.EFFECTS_ZOOM_DEFAULT, "linked": False},
            "panX": {"value": Config.EFFECTS_PAN_DEFAULT, "linked": False},
            "panY": {"value": Config.EFFECTS_PAN_DEFAULT, "linked": False},
            "rotation": {"value": Config.EFFECTS_ROTATION_DEFAULT, "linked": False},
            "distortion": {"value": Config.EFFECTS_DISTORTION_DEFAULT, "linked": False},
        }

        # --- Setup dell'interfaccia utente (UI) ---
        self.setup_ui()
        self.setup_resize_handle()

        # --- Inizializzazioni Differite ---
        self.root.after_idle(self._deferred_initialization)
        
        # --- Cleanup alla chiusura dell'applicazione ---
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        print("Inizializzazione GUI di base completata. Avvio mainloop e attesa inizializzazioni differite.")

    def _deferred_initialization(self):
        print("Avvio inizializzazione differita dei sistemi (audio, Bonzomatic, cache, browser driver)...")
        try:
            if self.file_manager_config['cache_enabled']:
                self.load_shader_cache()
            
            if AUDIO_AVAILABLE:
                self.setup_audio_engine()
            else:
                print("AVVISO: Le librerie audio non sono disponibili, le funzioni audio saranno disabilitate.")

            self.setup_bonzomatic_path()
            
            # Condizione per l'import di selenium
            try:
                import selenium
                from selenium import webdriver
                from selenium.webdriver.common.by import By
                from selenium.webdriver.support.wait import WebDriverWait
                from selenium.webdriver.support import expected_conditions as EC
                from selenium.webdriver.chrome.options import Options
                SELENIUM_AVAILABLE = True 
            except ImportError:
                SELENIUM_AVAILABLE = False
                print("ATTENZIONE: Libreria 'selenium' non disponibile. Funzioni web scraping Shadertoy disabilitate.")

            if 'SELENIUM_AVAILABLE' in globals() and SELENIUM_AVAILABLE:
                if hasattr(self, 'setup_browser_driver'):
                    self.setup_browser_driver()
                else:
                    print("AVVISO: Il metodo setup_browser_driver non è definito in questa versione.")
            else:
                print("AVVISO: Selenium non disponibile, ignorando setup browser driver.")
            
            self.setup_vmix_output()
            self.integrate_all_systems()
            
            print("Inizializzazione differita dei sistemi completata.")
        except Exception as e:
            print(f"Errore critico durante l'inizializzazione differita dei sistemi: {e}")
            traceback.print_exc()

    def setup_ui(self):
        self.main_container = ctk.CTkFrame(self.root, fg_color="transparent")
        self.main_container.pack(fill="both", expand=True, padx=Config.UI_PADDING, pady=Config.UI_PADDING)
        self.main_container.grid_columnconfigure(0, weight=1, minsize=int(Config.DEFAULT_APP_WIDTH * 0.25))
        self.main_container.grid_columnconfigure(1, weight=3, minsize=int(Config.DEFAULT_APP_WIDTH * 0.75))
        self.main_container.grid_rowconfigure(0, weight=1)

        self.left_column_frame = ctk.CTkFrame(self.main_container, fg_color="#2a2a4a", corner_radius=Config.UI_PADDING)
        self.left_column_frame.grid(row=0, column=0, sticky="nsew", padx=(0, Config.UI_PADDING))
        self.left_column_frame.grid_rowconfigure(0, weight=0)
        self.left_column_frame.grid_rowconfigure(1, weight=0)
        self.left_column_frame.grid_rowconfigure(2, weight=0)
        self.left_column_frame.grid_rowconfigure(3, weight=1)

        self.right_column_frame = ctk.CTkFrame(self.main_container, fg_color="#2a2a4a", corner_radius=Config.UI_PADDING)
        self.right_column_frame.grid(row=0, column=1, sticky="nsew")
        self.right_column_frame.grid_rowconfigure(0, weight=0)
        self.right_column_frame.grid_rowconfigure(1, weight=0)
        self.right_column_frame.grid_rowconfigure(2, weight=0)
        self.right_column_frame.grid_rowconfigure(3, weight=0)
        self.right_column_frame.grid_rowconfigure(4, weight=1)

        self.create_bonzomatic_section(self.left_column_frame)
        self.create_local_shader_loader_section(self.left_column_frame)
        self.create_shadertoy_download_section(self.left_column_frame)
        
        self.create_source_control_section(self.right_column_frame)
        self.create_mixer_effects_section(self.right_column_frame)
        self.create_audio_section(self.right_column_frame)
        self.create_video_effects_section(self.right_column_frame)

        self.status_bar = ctk.CTkLabel(self.root, text="Inizializzazione...", fg_color="#1a1a2e", text_color="#9370DB", 
                                       font=("Inter", Config.SUB_LABEL_FONT_SIZE, Config.BOLD_FONT_WEIGHT),
                                       anchor="w", padx=Config.UI_PADDING)
        self.status_bar.pack(side="bottom", fill="x", pady=(Config.UI_PADDING,0))

        self.preview_window = ctk.CTkToplevel(self.root, fg_color="black", border_width=2, border_color="#8e54e9", corner_radius=Config.UI_PADDING)
        self.preview_window.title("Anteprima Shader")
        self.preview_window.geometry("400x300+800+50")
        self.preview_window.overrideredirect(True)
        
        preview_header = ctk.CTkFrame(self.preview_window, fg_color="#8e54e9", height=30, corner_radius=0)
        preview_header.pack(fill="x", side="top")
        ctk.CTkLabel(preview_header, text="Anteprima Shader", fg_color="transparent", text_color="white", font=("Inter", 12, "bold")).pack(side="left", padx=5)
        close_btn = ctk.CTkButton(preview_header, text="X", command=self.hide_preview_window, width=20, height=20, fg_color="transparent", hover_color="#C06014", text_color="white", font=("Inter", 12, "bold"))
        close_btn.pack(side="right", padx=5)

        self.preview_canvas_widget = tk.Canvas(self.preview_window, bg="black", highlightthickness=0)
        self.preview_canvas_widget.pack(fill="both", expand=True)

        self.drag_data = {"x": 0, "y": 0, "dragging": False}
        preview_header.bind("<ButtonPress-1>", self.start_drag_preview_window)
        preview_header.bind("<ButtonRelease-1>", self.stop_drag_preview_window)
        preview_header.bind("<B1-Motion>", self.do_drag_preview_window)

        self.preview_window.withdraw()

    def create_bonzomatic_section(self, parent_frame):
        frame = ctk.CTkFrame(parent_frame, fg_color="#3a3a5a", corner_radius=Config.UI_PADDING // 2)
        frame.pack(fill="x", pady=(Config.UI_PADDING, Config.UI_PADDING), padx=Config.UI_PADDING)
        
        ctk.CTkLabel(frame, text="⚡ BONZOMATIC CONTROLLER", font=("Inter", Config.SECTION_TITLE_FONT_SIZE, Config.BOLD_FONT_WEIGHT), fg_color="transparent").pack(pady=(Config.BUTTON_PADDING * 2, Config.BUTTON_PADDING))
        
        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(pady=(0, Config.UI_PADDING))
        
        self.bonzo_start_btn = ctk.CTkButton(button_frame, text="Avvia Bonzomatic", command=self.start_bonzomatic, fg_color="#42A5F5", hover_color="#2196F3")
        self.bonzo_start_btn.pack(side="left", padx=Config.BUTTON_PADDING, fill="x", expand=True)
        
        self.bonzo_stop_btn = ctk.CTkButton(button_frame, text="Stop Bonzomatic", command=self.stop_bonzomatic, state="disabled", fg_color="#E53935", hover_color="#FF0000")
        self.bonzo_stop_btn.pack(side="left", padx=Config.BUTTON_PADDING, fill="x", expand=True)
        
        self.bonzo_show_btn = ctk.CTkButton(button_frame, text="Mostra Finestra", command=self.show_bonzomatic, state="disabled", fg_color="#673AB7", hover_color="#5E35B1")
        self.bonzo_show_btn.pack(side="left", padx=Config.BUTTON_PADDING, fill="x", expand=True)
        
        self.bonzo_status = ctk.CTkLabel(frame, text="Stato: Non avviato", font=("Inter", Config.SUB_LABEL_FONT_SIZE), fg_color="transparent")
        self.bonzo_status.pack(pady=(0, Config.UI_PADDING))

    def create_local_shader_loader_section(self, parent_frame):
        frame = ctk.CTkFrame(parent_frame, fg_color="#3a3a5a", corner_radius=Config.UI_PADDING // 2)
        frame.pack(fill="both", expand=True, pady=(0, Config.UI_PADDING), padx=Config.UI_PADDING)
        
        ctk.CTkLabel(frame, text="📁 CARICA SHADER LOCALI", font=("Inter", Config.SECTION_TITLE_FONT_SIZE, Config.BOLD_FONT_WEIGHT), fg_color="transparent").pack(pady=(Config.BUTTON_PADDING * 2, Config.BUTTON_PADDING))
        
        button_frame = ctk.CTkFrame(frame, fg_color="transparent")
        button_frame.pack(fill="x", padx=Config.UI_PADDING, pady=(0, Config.UI_PADDING))
        
        self.load_folder_btn = ctk.CTkButton(button_frame, text="Seleziona Cartella Shader", command=self.load_shader_folder)
        self.load_folder_btn.pack(side="left", expand=True, fill="x", padx=Config.BUTTON_PADDING)
        
        self.shader_status_label = ctk.CTkLabel(frame, text="Nessuna cartella caricata.", font=("Inter", Config.SUB_LABEL_FONT_SIZE), fg_color="transparent")
        self.shader_status_label.pack(pady=(0, Config.UI_PADDING))
        
        self.shader_list_frame = ctk.CTkScrollableFrame(frame, height=200, fg_color="#4a4a6a", corner_radius=Config.UI_PADDING // 2)
        self.shader_list_frame.pack(fill="both", expand=True, padx=Config.UI_PADDING, pady=(0, Config.UI_PADDING))
        self.shader_list_frame.grid_columnconfigure(0, weight=1)
        self.shader_list_frame.grid_columnconfigure(1, weight=1)
        self.update_shader_list()

    def create_shadertoy_download_section(self, parent_frame):
        frame = ctk.CTkFrame(parent_frame, fg_color="#3a3a5a", corner_radius=Config.UI_PADDING // 2)
        frame.pack(fill="x", pady=(0, Config.UI_PADDING), padx=Config.UI_PADDING)
        
        ctk.CTkLabel(frame, text="🌐 DOWNLOAD SHADERTOY", font=("Inter", Config.SECTION_TITLE_FONT_SIZE, Config.BOLD_FONT_WEIGHT), fg_color="transparent").pack(pady=(Config.BUTTON_PADDING * 2, Config.BUTTON_PADDING))
        
        url_input_frame = ctk.CTkFrame(frame, fg_color="transparent")
        url_input_frame.pack(fill="x", padx=Config.UI_PADDING, pady=(0, Config.BUTTON_PADDING))

        ctk.CTkButton(url_input_frame, text="Apri Shadertoy.com", command=self.open_shadertoy, width=150).pack(side="left", padx=Config.BUTTON_PADDING)
        
        self.url_entry = ctk.CTkEntry(url_input_frame, placeholder_text="Incolla URL Shadertoy...", width=300)
        self.url_entry.pack(side="left", expand=True, fill="x", padx=Config.BUTTON_PADDING)
        
        self.download_btn = ctk.CTkButton(url_input_frame, text="Download", command=self.download_shader)
        self.download_btn.pack(side="right", padx=Config.BUTTON_PADDING)

        self.shadertoy_status_label = ctk.CTkLabel(frame, text="", font=("Inter", Config.SUB_LABEL_FONT_SIZE), fg_color="transparent")
        self.shadertoy_status_label.pack(pady=(0, Config.UI_PADDING))

    def create_source_control_section(self, parent_frame):
        frame = ctk.CTkFrame(parent_frame, fg_color="#3a3a5a", corner_radius=Config.UI_PADDING // 2)
        frame.pack(fill="x", pady=(0, Config.UI_PADDING), padx=Config.UI_PADDING)

        ctk.CTkLabel(frame, text="Sorgente Video:", fg_color="transparent").pack(side="left", padx=Config.BUTTON_PADDING)
        self.source_var = ctk.StringVar(value="Shader")
        ctk.CTkOptionMenu(frame, values=["Shader", "Webcam (Simulata)"], variable=self.source_var, command=self.update_source).pack(side="left", padx=Config.BUTTON_PADDING, expand=True, fill="x")
        ctk.CTkButton(frame, text="Stop Sessione", command=self.stop_session, fg_color="#E53935", hover_color="#FF0000").pack(side="right", padx=Config.BUTTON_PADDING)

    def create_mixer_effects_section(self, parent_frame):
        frame = ctk.CTkFrame(parent_frame, fg_color="#3a3a5a", corner_radius=Config.UI_PADDING // 2)
        frame.pack(fill="x", pady=(0, Config.UI_PADDING), padx=Config.UI_PADDING)

        ctk.CTkLabel(frame, text="Mixer Effetti", font=("Inter", Config.SECTION_TITLE_FONT_SIZE, Config.BOLD_FONT_WEIGHT), fg_color="transparent").pack(pady=(Config.BUTTON_PADDING * 2, Config.BUTTON_PADDING))

        transparency_row = ctk.CTkFrame(frame, fg_color="transparent")
        transparency_row.pack(fill="x", pady=Config.BUTTON_PADDING, padx=Config.UI_PADDING)
        ctk.CTkLabel(transparency_row, text="Trasparenza:", fg_color="transparent").pack(side="left", padx=Config.BUTTON_PADDING)
        self.transparency_slider = ctk.CTkSlider(transparency_row, from_=0, to=1, command=self.update_transparency)
        self.transparency_slider.set(self.transparency_value)
        self.transparency_slider.pack(side="left", expand=True, fill="x", padx=Config.BUTTON_PADDING)
        self.transparency_value_label = ctk.CTkLabel(transparency_row, text=f"{self.transparency_value:.2f}", fg_color="transparent", text_color="#9370DB")
        self.transparency_value_label.pack(side="right", padx=Config.BUTTON_PADDING)

        chroma_key_row = ctk.CTkFrame(frame, fg_color="transparent")
        chroma_key_row.pack(fill="x", pady=Config.BUTTON_PADDING, padx=Config.UI_PADDING)
        self.chroma_key_var = ctk.BooleanVar(value=self.chroma_key_active)
        ctk.CTkCheckBox(chroma_key_row, text="Attiva Chroma Key (Luma)", variable=self.chroma_key_var, command=self.toggle_chroma_key).pack(anchor="w")

    def create_audio_section(self, parent_frame):
        frame = ctk.CTkFrame(parent_frame, fg_color="#3a3a5a", corner_radius=Config.UI_PADDING // 2)
        frame.pack(fill="x", pady=(0, Config.UI_PADDING), padx=Config.UI_PADDING)

        ctk.CTkLabel(frame, text="🎤 CONTROLLO AUDIO", font=("Inter", Config.SECTION_TITLE_FONT_SIZE, Config.BOLD_FONT_WEIGHT), fg_color="transparent").pack(pady=(Config.BUTTON_PADDING * 2, Config.BUTTON_PADDING))
        
        audio_input_row = ctk.CTkFrame(frame, fg_color="transparent")
        audio_input_row.pack(fill="x", pady=Config.BUTTON_PADDING, padx=Config.UI_PADDING)
        ctk.CTkLabel(audio_input_row, text="Ingresso:", fg_color="transparent").pack(side="left", padx=Config.BUTTON_PADDING)
        self.audio_input_var = ctk.StringVar(value="Microfono")
        ctk.CTkOptionMenu(audio_input_row, values=["Microfono", "USB", "Esterno"], variable=self.audio_input_var, command=self.change_audio_input).pack(side="left", padx=Config.BUTTON_PADDING, expand=True, fill="x")

        bpm_row = ctk.CTkFrame(frame, fg_color="transparent")
        bpm_row.pack(fill="x", pady=Config.BUTTON_PADDING, padx=Config.UI_PADDING)
        ctk.CTkButton(bpm_row, text="TAP", command=self.tap_tempo_button_clicked, fg_color="#FFC107", hover_color="#FFD700", text_color="#333333", font=("Inter", Config.SECTION_TITLE_FONT_SIZE, Config.BOLD_FONT_WEIGHT)).pack(side="left", padx=Config.BUTTON_PADDING)
        
        ctk.CTkLabel(bpm_row, text="BPM:", fg_color="transparent").pack(side="left", padx=Config.BUTTON_PADDING)
        self.bpm_entry = ctk.CTkEntry(bpm_row, width=50) # Larghezza più piccola
        self.bpm_entry.insert(0, str(self.current_bpm))
        self.bpm_entry.pack(side="left", padx=Config.BUTTON_PADDING)
        self.bpm_entry.bind("<Return>", self.update_bpm_from_entry)

        audio_toggles_row = ctk.CTkFrame(frame, fg_color="transparent")
        audio_toggles_row.pack(fill="x", pady=Config.BUTTON_PADDING, padx=Config.UI_PADDING)
        self.audio_react_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(audio_toggles_row, text="Audio React", variable=self.audio_react_var, command=self.toggle_audio_react).pack(side="left", padx=Config.BUTTON_PADDING)
        self.auto_bpm_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(audio_toggles_row, text="Auto BPM", variable=self.auto_bpm_var, command=self.toggle_auto_bpm).pack(side="left", padx=Config.BUTTON_PADDING)
        self.beat_sync_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(audio_toggles_row, text="Beat Sync", variable=self.beat_sync_var, command=self.toggle_beat_sync).pack(side="left", padx=Config.BUTTON_PADDING)
        self.bass_response_var = ctk.BooleanVar(value=False)
        ctk.CTkSwitch(audio_toggles_row, text="Bass Response", variable=self.bass_response_var, command=self.toggle_bass_response).pack(side="left", padx=Config.BUTTON_PADDING)


    def create_video_effects_section(self, parent_frame):
        """Crea la sezione UI per il controllo degli effetti video base (Zoom, Pan, Rotazione, Distorsione)."""
        frame = ctk.CTkFrame(parent_frame, fg_color="#3a3a5a", corner_radius=Config.UI_PADDING // 2)
        frame.pack(fill="both", expand=True, pady=(0, Config.UI_PADDING), padx=Config.UI_PADDING)
        
        ctk.CTkLabel(frame, text="🎬 EFFETTI VIDEO", font=("Inter", Config.SECTION_TITLE_FONT_SIZE, Config.BOLD_FONT_WEIGHT), fg_color="transparent").pack(pady=(Config.BUTTON_PADDING * 2, Config.BUTTON_PADDING))
        
        self.effect_widgets = {}

        effect_keys = ["zoom", "panX", "panY", "rotation", "distortion"]
        for key in effect_keys:
            # Recupera i limiti min/max e default dalle costanti Config
            min_val = getattr(Config, f"EFFECTS_{key.upper()}_MIN")
            max_val = getattr(Config, f"EFFECTS_{key.upper()}_MAX")
            default_val = getattr(Config, f"EFFECTS_{key.upper()}_DEFAULT")
            step_val = 0.01 if key == "zoom" or key == "distortion" else 0.001
            
            config = {
                "name": key.replace("X", " X").replace("Y", " Y").capitalize(), # Formatta nome
                "min": min_val,
                "max": max_val,
                "default": default_val,
                "step": step_val
            }
            # Crea una singola riga per l'effetto
            self.create_effect_slider_row(frame, key, config)

    def create_effect_slider_row(self, parent_frame, key, config):
        """Crea una singola riga per il controllo di un effetto video con slider e campi min/max."""
        effect_row = ctk.CTkFrame(parent_frame, fg_color="transparent")
        effect_row.pack(fill="x", pady=Config.BUTTON_PADDING // 2, padx=Config.UI_PADDING)

        # Etichetta nome effetto (es. Zoom:)
        ctk.CTkLabel(effect_row, text=config["name"] + ":", fg_color="transparent", width=10).pack(side="left", padx=Config.BUTTON_PADDING)

        # Slider principale
        slider = ctk.CTkSlider(effect_row, from_=config["min"], to=config["max"], command=lambda val: self.update_effect_slider(val, key))
        slider.set(config["default"])
        slider.pack(side="left", expand=True, fill="x", padx=Config.BUTTON_PADDING)

        # Label per il valore corrente dello slider
        value_label = ctk.CTkLabel(effect_row, text=f"{config['default']:.3f}", fg_color="transparent", text_color="#9370DB", width=6)
        value_label.pack(side="left", padx=Config.BUTTON_PADDING)

        # Pulsante collega audio
        link_button = ctk.CTkButton(effect_row, text="🔗", width=30, command=lambda k=key: self.toggle_audio_link_effect(k))
        link_button.pack(side="left", padx=Config.BUTTON_PADDING)
        
        # Campi Min/Max numerici
        min_label = ctk.CTkLabel(effect_row, text="Min:", fg_color="transparent", text_color="#cccccc").pack(side="left")
        min_entry = ctk.CTkEntry(min_frame, width=50) # Larghezza fissa per input numerici
        min_entry.insert(0, str(config["min"])) # Inserisce il valore minimo predefinito
        min_entry.pack(side="left", padx=Config.BUTTON_PADDING // 2)
        # Associa la funzione di aggiornamento al tasto Invio (Return)
        min_entry.bind("<Return>", lambda event, k=key, entry=min_entry: self.update_effect_min_max_from_entry(event, k, "min", entry))
        
        max_label = ctk.CTkLabel(effect_row, text="Max:", fg_color="transparent", text_color="#cccccc").pack(side="left")
        max_entry = ctk.CTkEntry(max_frame, width=50) # Larghezza fissa per input numerici
        max_entry.insert(0, str(config["max"])) # Inserisce il valore massimo predefinito
        max_entry.pack(side="left", padx=Config.BUTTON_PADDING // 2)
        # Associa la funzione di aggiornamento al tasto Invio (Return)
        max_entry.bind("<Return>", lambda event, k=key, entry=max_entry: self.update_effect_min_max_from_entry(event, k, "max", entry))

        self.effect_widgets[key] = {
            "slider": slider,
            "value_label": value_label,
            "min_entry": min_entry,
            "max_entry": max_entry,
            "link_button": link_button
        }

    # --- Metodi per la gestione delle funzionalità ---
    def button_click(self, action):
        """Aggiorna lo stato quando un pulsante generico viene cliccato."""
        self.update_status(f"Azione cliccata: {action}")
        print(f"Azione cliccata: {action}") # Stampa anche in console per debug
        if "Avvia" in action:
            self.show_preview_window() # Mostra la finestra di anteprima simulata

    def update_source(self, *args):
        """Aggiorna la sorgente video selezionata."""
        self.source_select_value = self.source_var.get()
        self.update_status(f"Sorgente video: {self.source_select_value}")
        print(f"Sorgente video selezionata: {self.source_select_value}")

    def update_transparency(self, val):
        """Aggiorna il valore della trasparenza dallo slider."""
        self.transparency_value = float(val)
        self.transparency_value_label.configure(text=f"{self.transparency_value:.2f}")
        self.update_status(f"Trasparenza: {self.transparency_value:.2f}")

    def toggle_chroma_key(self):
        """Attiva/disattiva l'effetto Chroma Key (Luma)."""
        self.chroma_key_active = self.chroma_key_var.get()
        self.update_status(f"Chroma Key: {'Attivo' if self.chroma_key_active else 'Disattivo'}")

    def tap_tempo_button_clicked(self):
        """Gestisce il tap tempo per calcolare i BPM."""
        now = time.time()
        # Se l'ultimo tap è troppo vecchio, resetta la sequenza
        if self.tap_tempo_times and (now - self.tap_tempo_times[-1]) > Config.TAP_TEMPO_RESET_THRESHOLD_SECONDS:
            self.tap_tempo_times = []
        self.tap_tempo_times.append(now)
        if len(self.tap_tempo_times) > Config.MAX_BEAT_TIMES_FOR_BPM: # Mantieni solo gli ultimi N tap
            self.tap_tempo_times.pop(0)

        if len(self.tap_tempo_times) > Config.MIN_TAPS_FOR_BPM_CALC - 1:
            total_interval = self.tap_tempo_times[-1] - self.tap_tempo_times[0]
            num_intervals = len(self.tap_tempo_times) - 1
            if num_intervals > 0:
                avg_interval = total_interval / num_intervals
                calculated_bpm = round(60 / avg_interval)
                # Applica smoothing al BPM calcolato
                self.current_bpm = int(self.current_bpm * (1 - Config.BPM_SMOOTHING_FACTOR) + calculated_bpm * Config.BPM_SMOOTHING_FACTOR)
                self.bpm_entry.delete(0, tk.END) # Aggiorna il campo di testo BPM
                self.bpm_entry.insert(0, str(self.current_bpm))
        self.update_status(f"TAP! BPM: {self.current_bpm}")

    def update_bpm_from_entry(self, event=None):
        """Aggiorna i BPM dal campo di testo (quando si preme Invio)."""
        try:
            new_bpm = int(self.bpm_entry.get())
            # Limita i BPM al range configurato
            if new_bpm < Config.AUDIO_DEFAULT_BPM_RANGE[0]: new_bpm = Config.AUDIO_DEFAULT_BPM_RANGE[0]
            if new_bpm > Config.AUDIO_DEFAULT_BPM_RANGE[1]: new_bpm = Config.AUDIO_DEFAULT_BPM_RANGE[1]
            self.current_bpm = new_bpm
            self.bpm_entry.delete(0, tk.END)
            self.bpm_entry.insert(0, str(self.current_bpm))
            self.update_status(f"BPM impostati a: {self.current_bpm}")
        except ValueError:
            self.update_status("Errore: BPM non validi.")

    def update_effect_slider(self, val, key):
        """Aggiorna il valore di uno slider effetto e il label associato.""" # Correzione: Completato il commento
        current_value = float(val)
        # Aggiorna il valore nell'oggetto di runtime degli effetti
        self.effects_config_runtime[key]["value"] = current_value
        # Aggiorna il testo dell'etichetta visualizzata accanto allo slider
        self.effect_widgets[key]["value_label"].configure(text=f"{current_value:.3f}")
        # Scrivi i parametri aggiornati per Bonzomatic (se in esecuzione)
        self.write_bonzomatic_params()
        self.update_status(f"Slider {key}: {current_value:.3f}")

    def update_effect_min_max_from_entry(self, event, key, type, entry_widget):
        """Aggiorna i campi Min/Max di un effetto dal campo di testo (quando si preme Invio)."""
        try:
            new_value = float(entry_widget.get())
            # Determina se stiamo aggiornando il minimo o il massimo
            if type == "min":
                s