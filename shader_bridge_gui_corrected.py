#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SHADER BRIDGE PLAYER - VERSIONE STABILE E FUNZIONALE
Controller Essenziale per Bonzomatic con Analisi Audio, Caricamento Shader Locale e Effetti Video.
"""

import customtkinter as ctk
import tkinter as tk
from tkinter import filedialog, messagebox
import os
import subprocess
import threading
import time
import platform
import json # Per la cache shader e scrittura parametri
import hashlib # Per hash file nella cache
import re # Per parsing metadati shader
from pathlib import Path # Per gestire i percorsi in modo robusto
from datetime import datetime # Per timestamp nella cache
import webbrowser # Per aprire link Shadertoy
import traceback # Per una migliore diagnostica degli errori

# Import requests con fallback (necessario per download da Shadertoy API)
try:
    import requests
    REQUESTS_AVAILABLE = True
    print("Libreria 'requests' caricata con successo.")
except ImportError:
    REQUESTS_AVAILABLE = False
    print("ATTENZIONE: Libreria 'requests' non disponibile. Download API Shadertoy disabilitato.")

# Import Selenium con fallback (necessario per web scraping Shadertoy, se l'API fallisce)
try:
    import selenium
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.wait import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    SELENIUM_AVAILABLE = True
    print("Libreria 'selenium' caricata con successo.")
except ImportError:
    SELENIUM_AVAILABLE = False
    print("ATTENZIONE: Libreria 'selenium' non disponibile. Funzioni web scraping Shadertoy disabilitate.")

# Import per Audio Engine (essenziali per la funzione DJ/VJ)
try:
    import pyaudio
    import numpy as np
    from scipy.fft import fft, fftfreq
    AUDIO_AVAILABLE = True
    print("Librerie audio (pyaudio, numpy, scipy) caricate con successo.")
except ImportError:
    AUDIO_AVAILABLE = False
    print("ATTENZIONE: Librerie audio non disponibili (pyaudio, numpy, scipy). Le funzioni audio saranno disabilitate.")

# Import win32gui con fallback per funzionalità specifiche di Windows (es. controllo finestre Bonzomatic)
WIN32GUI_AVAILABLE = False
if platform.system() == "Windows":
    try:
        import win32gui
        WIN32GUI_AVAILABLE = True
        print("Libreria 'pywin32' caricata con successo (per controllo finestre Windows).")
    except ImportError:
        print("ATTENZIONE: Libreria 'pywin32' non disponibile. Alcune funzioni di controllo finestra Bonzomatic su Windows saranno limitate.")

# Configurazione tema CustomTkinter
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

class ShaderBridgePlayer:
    # --- Costanti di Configurazione Generale ---
    DEFAULT_APP_WIDTH = 550
    DEFAULT_APP_HEIGHT = 700 # Aumentato per più spazio agli slider
    MIN_APP_WIDTH = 400
    MIN_APP_HEIGHT = 400

    UI_PADDING = 10
    BUTTON_PADDING = 5
    SECTION_TITLE_FONT_SIZE = 14
    SUB_LABEL_FONT_SIZE = 9
    BOLD_FONT_WEIGHT = "bold"

    # --- Costanti Bonzomatic ---
    BONZOMATIC_EXECUTABLE_NAME = "Bonzomatic_W64_DX11.exe"
    BONZOMATIC_DEFAULT_WINDOW_TITLE = "Bonzomatic"
    BONZOMATIC_WINDOW_DETECT_TIMEOUT = 10 # Secondi di timeout per trovare la finestra
    PROCESS_SCAN_SLEEP_SECONDS = 0.5 # Intervallo di sleep durante la scansione finestra/processo
    BONZOMATIC_STOP_GRACEFUL_WAIT_SECONDS = 3 # Secondi di attesa per chiusura graziosa
    BONZOMATIC_TERMINATE_TIMEOUT = 5 # Secondi di timeout per la terminazione forzata
    BONZOMATIC_MONITOR_INTERVAL_SECONDS = 1 # Intervallo di monitoraggio processo
    SUBPROCESS_CREATE_NO_WINDOW_FLAG = subprocess.CREATE_NO_WINDOW if platform.system() == "Windows" else 0
    BONZOMATIC_LIVE_SHADER_FILENAME = "live_shader.frag" # File che Bonzomatic dovrebbe ricaricare automaticamente
    BONZOMATIC_PARAMS_FILENAME = "bonzomatic_params.txt" # File per output parametri effetti

    # --- Costanti Audio Engine ---
    AUDIO_DEFAULT_SAMPLE_RATE = 44100
    AUDIO_DEFAULT_CHUNK_SIZE = 1024
    AUDIO_DEFAULT_CHANNELS = 1
    AUDIO_DEFAULT_NOISE_THRESHOLD = 0.01
    AUDIO_DEFAULT_BPM_RANGE = [60, 200]
    AUDIO_DEFAULT_BEAT_SENSITIVITY = 0.5
    AUDIO_DEFAULT_BASS_FREQ_RANGE = [20, 250]
    AUDIO_ANALYSIS_THREAD_SLEEP_SECONDS = 0.05
    AUDIO_SYNC_LOOP_SLEEP_SECONDS = 0.1 # Frequenza di aggiornamento dei parametri per Bonzomatic
    MIN_BEAT_INTERVAL_SECONDS = 0.1
    MAX_BEAT_TIMES_FOR_BPM = 8
    MIN_BEATS_FOR_BPM_CALC = 4
    MIN_TAPS_FOR_BPM_CALC = 2
    TAP_TEMPO_RESET_THRESHOLD_SECONDS = 2.0
    BPM_SMOOTHING_FACTOR = 0.2
    BASS_LEVEL_EFFECT_THRESHOLD = 0.1 # Soglia di livello bass per attivare effetti

    # --- Costanti File Manager & Shader Loading ---
    SHADER_CACHE_FILENAME = "shader_cache.json"
    SHADER_SUPPORTED_EXTENSIONS = ['.frag', '.glsl', '.fs', '.shader']
    SHADER_TITLE_TRUNCATE_LENGTH = 27
    MIN_SHADER_CODE_SIZE_KB = 0 # Usato per display info
    SHADER_CACHE_CLEANUP_THRESHOLD = 1000 # Max entry nella cache prima di pulire

    # --- Costanti Shadertoy Integration (Download) ---
    SHADERTOY_DEFAULT_URL = "https://www.shadertoy.com"
    SHADERTOY_VALID_URL_CHECK = 'shadertoy.com' # Stringa per validare se l'URL è di Shadertoy
    SHADERTOY_API_KEY_MIN_LENGTH = 10 # Lunghezza minima per la chiave API Shadertoy
    SHADERTOY_ID_MIN_LENGTH = 6 # Lunghezza minima per l'ID di uno shader su Shadertoy
    SHADERTOY_REQUEST_TIMEOUT = 15 # Timeout per le richieste API Shadertoy
    SHADERTOY_BROWSER_WAIT_SECONDS = 10 # Tempo di attesa per caricamento pagina Shadertoy
    SHADERTOY_MIN_SHADER_CODE_LENGTH = 50 # Lunghezza minima del codice shader per essere considerato valido
    
    # --- Costanti VMix / Output ---
    VMIX_DEFAULT_WINDOW_ALWAYS_ON_TOP = False # Disabilitato per default per massima compatibilità
    VMIX_DEFAULT_TRANSPARENT_BACKGROUND = False # Disabilitato per default
    MIN_SYSTEMS_FOR_INTEGRATION = 1 # Per semplicità, 1 sistema attivo basta per l'integrazione di base
    RESIZE_HANDLE_SIZE = 20 # Dimensione del handle di ridimensionamento
    VMIX_OPTIMIZE_INTERVAL_SECONDS = 1.0 # Intervallo per le ottimizzazioni performance VMix
    AUDIO_CHUNK_SIZE_MAX_OPTIMIZED = 2048 # Dimensione massima del chunk audio per ottimizzazione

    # --- Costanti Effetti Video ---
    EFFECTS_SECTION_TITLE_FONT_SIZE = 14
    # Range generico per slider Pan e Distortion
    EFFECTS_SLIDER_FROM_DEFAULT = -1.0
    EFFECTS_SLIDER_TO_DEFAULT = 1.0
    EFFECTS_SLIDER_RESOLUTION = 0.01 # Risoluzione per i passi degli slider
    
    EFFECTS_ZOOM_DEFAULT = 1.0
    EFFECTS_ZOOM_MIN = 0.5
    EFFECTS_ZOOM_MAX = 2.0
    EFFECTS_PAN_DEFAULT = 0.0
    EFFECTS_ROTATION_DEFAULT = 0.0
    EFFECTS_ROTATION_MAX = 360 # Gradi
    EFFECTS_DISTORTION_DEFAULT = 0.0
    EFFECTS_DISTORTION_MAX = 1.0


    def __init__(self):
        print("Inizio inizializzazione ShaderBridgePlayer (Fase GUI di base)...")
        self.root = ctk.CTk()
        self.root.title("Shader Bridge Player v1.0 (Essenziale)")
        self.root.geometry(f"{self.DEFAULT_APP_WIDTH}x{self.DEFAULT_APP_HEIGHT}")
        self.root.minsize(self.MIN_APP_WIDTH, self.MIN_APP_HEIGHT)
        
        # --- Variabili di Stato dell'Applicazione ---
        self.shader_folder = ""
        self.current_shader = ""
        self.bonzomatic_process = None
        self.bonzomatic_path = ""
        self.bonzomatic_window_handle = None
        self.bonzomatic_monitor_active = False
        self.audio_input = "Microfono"
        self.scale_factor = 1.0
        self.shadertoy_connected = False # Stato della connessione Selenium
        self.browser_driver = None # Istanza del browser Selenium

        # --- Configurazioni Moduli (usano costanti globali) ---
        self.bonzomatic_config = {
            "executable": self.BONZOMATIC_EXECUTABLE_NAME,
            "arguments": [],
            "working_dir": "",
            "window_title": self.BONZOMATIC_DEFAULT_WINDOW_TITLE,
            "auto_find": True,
            "live_shader_path": self.BONZOMATIC_LIVE_SHADER_FILENAME
        }
        self.file_manager_config = {
            "cache_enabled": True,
            "recursive_scan": True,
            "max_cache_size": self.SHADER_CACHE_CLEANUP_THRESHOLD
        }
        self.audio_config = {
            "sample_rate": self.AUDIO_DEFAULT_SAMPLE_RATE, "chunk_size": self.AUDIO_DEFAULT_CHUNK_SIZE,
            "channels": self.AUDIO_DEFAULT_CHANNELS, "format": pyaudio.paFloat32 if AUDIO_AVAILABLE else None,
            "input_device": None, "auto_gain": True, "noise_threshold": self.AUDIO_DEFAULT_NOISE_THRESHOLD,
            "bpm_range": self.AUDIO_DEFAULT_BPM_RANGE, "beat_sensitivity": self.AUDIO_DEFAULT_BEAT_SENSITIVITY,
            "bass_freq_range": self.AUDIO_DEFAULT_BASS_FREQ_RANGE, "enable_fft": True
        }
        self.shadertoy_config = {
            "browser_type": "chrome", "headless": False, "auto_fullscreen": True,
            "api_key": "", # <-- INSERISCI QUI LA TUA CHIAVE API DI SHADERTOY PER IL DOWNLOAD!
            "default_url": self.SHADERTOY_DEFAULT_URL
        }
        self.vmix_config = {
            "window_always_on_top": self.VMIX_DEFAULT_WINDOW_ALWAYS_ON_TOP,
            "transparent_background": self.VMIX_DEFAULT_TRANSPARENT_BACKGROUND,
            "output_resolution": (1920, 1080), "scaling_mode": "fit"
        }
        
        # --- Variabili di Stato dell'Audio Engine ---
        self.audio_stream = None; self.audio_thread = None; self.audio_recording = False
        self.current_bpm = 120; self.beat_detected = False; self.audio_level = 0.0
        self.frequency_data = []; self.bass_level = 0.0; self.tap_tempo_times = []
        self.auto_bpm_enabled = False; self.beat_sync_enabled = False; self.bass_response_enabled = False
        
        # --- Variabili di Stato Effetti Video ---
        self.effect_zoom = self.EFFECTS_ZOOM_DEFAULT
        self.effect_pan_x = self.EFFECTS_PAN_DEFAULT
        self.effect_pan_y = self.EFFECTS_PAN_DEFAULT
        self.effect_rotation = self.EFFECTS_ROTATION_DEFAULT
        self.effect_distortion = self.EFFECTS_DISTORTION_DEFAULT

        # --- Setup dell'interfaccia utente (UI) ---
        self.setup_ui()
        self.setup_resize_handle() # Handle di ridimensionamento per la finestra

        # --- Inizializzazioni Differite ---
        # Queste vengono chiamate DOPO che il mainloop della GUI è avviato e mostrato.
        self.root.after_idle(self._deferred_initialization)
        
        # --- Cleanup alla chiusura dell'applicazione ---
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
        
        print("Inizializzazione GUI di base completata. Avvio mainloop e attesa inizializzazioni differite.")

    def _deferred_initialization(self):
        """
        Esegue le inizializzazioni più pesanti o potenzialmente bloccanti
        dopo che il mainloop della GUI è avviato e la finestra è visibile.
        Questo previene blocchi all'avvio dell'interfaccia.
        """
        print("Avvio inizializzazione differita dei sistemi (audio, Bonzomatic, cache, browser driver)...")
        try:
            # File Manager: Carica cache shader
            if self.file_manager_config['cache_enabled']:
                self.load_shader_cache()
            
            # Setup Audio Engine
            self.setup_audio_engine()
            
            # Setup Bonzomatic Path (cerca eseguibile)
            self.setup_bonzomatic_path()
            
            # Setup Selenium (driver browser) - Inizializzato qui, non all'apertura di Shadertoy
            self.setup_browser_driver()
            
            # Setup VMix / integrazione finale
            self.setup_vmix_output()
            self.integrate_all_systems()
            
            print("Inizializzazione differita dei sistemi completata.")
        except Exception as e:
            print(f"Errore critico durante l'inizializzazione differita dei sistemi: {e}")
            traceback.print_exc()

    def setup_ui(self):
        """Crea l'interfaccia utente minimale e organizza le sezioni."""
        
        self.main_frame = ctk.CTkScrollableFrame(self.root)
        self.main_frame.pack(fill="both", expand=True, padx=self.UI_PADDING, pady=self.UI_PADDING)
        
        # SEZIONE: CONTROLLO BONZOMATIC
        self.create_bonzomatic_section()
        
        # SEZIONE: CARICA SHADER LOCALE E ANTEPRIMA (BONZOMATIC)
        self.create_local_shader_loader_section()

        # SEZIONE: SHADERTOY DOWNLOAD (per scaricare shader dal sito)
        self.create_shadertoy_download_section()
        
        # SEZIONE: CONTROLLO AUDIO
        self.create_audio_section()

        # SEZIONE: EFFETTI VIDEO (ZOOM, PAN, ROTAZIONE, DISTORSIONE)
        self.create_video_effects_section()

        # SEZIONE: SCALA FINESTRA (per VMix, minimal)
        self.create_resize_section()

    def create_bonzomatic_section(self):
        """Sezione UI per il controllo del processo Bonzomatic."""
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=(0, self.UI_PADDING))
        
        ctk.CTkLabel(frame, text="⚡ BONZOMATIC CONTROLLER", font=("Arial", self.SECTION_TITLE_FONT_SIZE, self.BOLD_FONT_WEIGHT)).pack(pady=(self.BUTTON_PADDING * 2, self.BUTTON_PADDING))
        
        button_frame = ctk.CTkFrame(frame)
        button_frame.pack(pady=(0, self.UI_PADDING))
        
        self.bonzo_start_btn = ctk.CTkButton(button_frame, text="Avvia Bonzomatic", command=self.start_bonzomatic)
        self.bonzo_start_btn.pack(side="left", padx=self.BUTTON_PADDING)
        
        self.bonzo_stop_btn = ctk.CTkButton(button_frame, text="Stop Bonzomatic", command=self.stop_bonzomatic, state="disabled")
        self.bonzo_stop_btn.pack(side="left", padx=self.BUTTON_PADDING)
        
        self.bonzo_show_btn = ctk.CTkButton(button_frame, text="Mostra Finestra", command=self.show_bonzomatic, state="disabled")
        self.bonzo_show_btn.pack(side="left", padx=self.BUTTON_PADDING)
        
        self.bonzo_status = ctk.CTkLabel(frame, text="Stato: Non avviato", font=("Arial", self.SUB_LABEL_FONT_SIZE))
        self.bonzo_status.pack(pady=(0, self.UI_PADDING))

    def create_local_shader_loader_section(self):
        """Sezione UI per caricare shader locali e visualizzarne un elenco semplice con anteprima tramite Bonzomatic."""
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=(0, self.UI_PADDING))
        
        ctk.CTkLabel(frame, text="📁 CARICA SHADER LOCALI", font=("Arial", self.SECTION_TITLE_FONT_SIZE, self.BOLD_FONT_WEIGHT)).pack(pady=(self.BUTTON_PADDING * 2, self.BUTTON_PADDING))
        
        button_frame = ctk.CTkFrame(frame)
        button_frame.pack(fill="x", padx=self.UI_PADDING, pady=(0, self.UI_PADDING))
        
        self.load_folder_btn = ctk.CTkButton(button_frame, text="Seleziona Cartella Shader", command=self.load_shader_folder)
        self.load_folder_btn.pack(side="left", expand=True, fill="x", padx=self.BUTTON_PADDING)
        
        self.shader_status_label = ctk.CTkLabel(frame, text="Nessuna cartella caricata.", font=("Arial", self.SUB_LABEL_FONT_SIZE))
        self.shader_status_label.pack(pady=(0, self.UI_PADDING))
        
        # Lista shader (semplice elenco con pulsante "Carica su Bonzomatic" per anteprima/uso)
        self.shader_list_frame = ctk.CTkScrollableFrame(frame, height=150)
        self.shader_list_frame.pack(fill="x", padx=self.UI_PADDING, pady=(0, self.UI_PADDING))
        self.update_shader_list() # Popola l'elenco iniziale (mostrerà "Nessun shader caricato.")

    def create_shadertoy_download_section(self):
        """Sezione UI per scaricare shader da Shadertoy.com."""
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=(0, self.UI_PADDING))
        
        ctk.CTkLabel(frame, text="🌐 DOWNLOAD SHADERTOY", font=("Arial", self.SECTION_TITLE_FONT_SIZE, self.BOLD_FONT_WEIGHT)).pack(pady=(self.BUTTON_PADDING * 2, self.BUTTON_PADDING))
        
        url_input_frame = ctk.CTkFrame(frame)
        url_input_frame.pack(fill="x", padx=self.UI_PADDING, pady=(0, self.BUTTON_PADDING))

        ctk.CTkButton(url_input_frame, text="Apri Shadertoy.com", command=self.open_shadertoy, width=150).pack(side="left", padx=self.BUTTON_PADDING)
        
        self.url_entry = ctk.CTkEntry(url_input_frame, placeholder_text="Incolla URL Shadertoy...", width=300)
        self.url_entry.pack(side="left", expand=True, fill="x", padx=self.BUTTON_PADDING)
        
        self.download_btn = ctk.CTkButton(url_input_frame, text="Download", command=self.download_shader)
        self.download_btn.pack(side="right", padx=self.BUTTON_PADDING)

        self.shadertoy_status_label = ctk.CTkLabel(frame, text="", font=("Arial", self.SUB_LABEL_FONT_SIZE))
        self.shadertoy_status_label.pack(pady=(0, self.UI_PADDING))


    def create_audio_section(self):
        """Sezione UI per il controllo dell'ingresso audio e le impostazioni BPM."""
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=(0, self.UI_PADDING))
        
        ctk.CTkLabel(frame, text="🎤 CONTROLLO AUDIO", font=("Arial", self.SECTION_TITLE_FONT_SIZE, self.BOLD_FONT_WEIGHT)).pack(pady=(self.BUTTON_PADDING * 2, self.BUTTON_PADDING))
        
        audio_frame = ctk.CTkFrame(frame)
        audio_frame.pack(fill="x", padx=self.UI_PADDING, pady=self.BUTTON_PADDING)
        
        ctk.CTkLabel(audio_frame, text="Ingresso:").pack(side="left", padx=self.BUTTON_PADDING)
        self.audio_input_var = ctk.StringVar(value="Microfono")
        self.audio_dropdown = ctk.CTkOptionMenu(audio_frame, values=["Microfono", "USB", "Esterno"], variable=self.audio_input_var, command=self.change_audio_input)
        self.audio_dropdown.pack(side="left", padx=self.BUTTON_PADDING)
        
        self.bpm_label = ctk.CTkLabel(audio_frame, text="BPM: 120", font=("Arial", self.SUB_LABEL_FONT_SIZE, self.BOLD_FONT_WEIGHT))
        self.bpm_label.pack(side="right", padx=self.BUTTON_PADDING)
        
        controls_frame = ctk.CTkFrame(frame)
        controls_frame.pack(fill="x", padx=self.UI_PADDING, pady=(0, self.UI_PADDING))

        ctk.CTkButton(controls_frame, text="Tap Tempo", command=self.tap_tempo_button_clicked).pack(side="left", padx=self.BUTTON_PADDING)
        ctk.CTkSwitch(controls_frame, text="Auto BPM", command=self.toggle_auto_bpm).pack(side="left", padx=self.BUTTON_PADDING)
        ctk.CTkSwitch(controls_frame, text="Beat Sync", command=self.toggle_beat_sync).pack(side="left", padx=self.BUTTON_PADDING)
        ctk.CTkSwitch(controls_frame, text="Bass Response", command=self.toggle_bass_response).pack(side="left", padx=self.BUTTON_PADDING)

    def create_video_effects_section(self):
        """Sezione UI per il controllo degli effetti video base (Zoom, Pan, Rotazione, Distorsione)."""
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=(0, self.UI_PADDING))
        
        ctk.CTkLabel(frame, text="🎬 EFFETTI VIDEO", font=("Arial", self.EFFECTS_SECTION_TITLE_FONT_SIZE, self.BOLD_FONT_WEIGHT)).pack(pady=(self.BUTTON_PADDING * 2, self.BUTTON_PADDING))
        
        # Zoom Control
        zoom_frame = ctk.CTkFrame(frame)
        zoom_frame.pack(fill="x", padx=self.UI_PADDING, pady=self.BUTTON_PADDING)
        ctk.CTkLabel(zoom_frame, text="Zoom:").pack(side="left", padx=self.BUTTON_PADDING)
        self.zoom_slider = ctk.CTkSlider(zoom_frame, from_=self.EFFECTS_ZOOM_MIN, to=self.EFFECTS_ZOOM_MAX, command=self.update_zoom)
        self.zoom_slider.set(self.EFFECTS_ZOOM_DEFAULT)
        self.zoom_slider.pack(side="left", expand=True, fill="x", padx=self.BUTTON_PADDING)
        self.zoom_label = ctk.CTkLabel(zoom_frame, text=f"{self.EFFECTS_ZOOM_DEFAULT:.2f}")
        self.zoom_label.pack(side="right", padx=self.BUTTON_PADDING)
        ctk.CTkSwitch(zoom_frame, text="Audio Zoom", command=self.toggle_audio_zoom_effect).pack(side="right", padx=self.BUTTON_PADDING)
        self.audio_zoom_enabled = False # Stato per il controllo audio-zoom

        # Pan X Control
        pan_x_frame = ctk.CTkFrame(frame)
        pan_x_frame.pack(fill="x", padx=self.UI_PADDING, pady=self.BUTTON_PADDING)
        ctk.CTkLabel(pan_x_frame, text="Pan X:").pack(side="left", padx=self.BUTTON_PADDING)
        self.pan_x_slider = ctk.CTkSlider(pan_x_frame, from_=self.EFFECTS_SLIDER_FROM_DEFAULT, to=self.EFFECTS_SLIDER_TO_DEFAULT, command=self.update_pan_x, number_of_steps=int((self.EFFECTS_SLIDER_TO_DEFAULT - self.EFFECTS_SLIDER_FROM_DEFAULT) / self.EFFECTS_SLIDER_RESOLUTION))
        self.pan_x_slider.set(self.EFFECTS_PAN_DEFAULT)
        self.pan_x_slider.pack(side="left", expand=True, fill="x", padx=self.BUTTON_PADDING)
        self.pan_x_label = ctk.CTkLabel(pan_x_frame, text=f"{self.EFFECTS_PAN_DEFAULT:.2f}")
        self.pan_x_label.pack(side="right", padx=self.BUTTON_PADDING)

        # Pan Y Control
        pan_y_frame = ctk.CTkFrame(frame)
        pan_y_frame.pack(fill="x", padx=self.UI_PADDING, pady=self.BUTTON_PADDING)
        ctk.CTkLabel(pan_y_frame, text="Pan Y:").pack(side="left", padx=self.BUTTON_PADDING)
        self.pan_y_slider = ctk.CTkSlider(pan_y_frame, from_=self.EFFECTS_SLIDER_FROM_DEFAULT, to=self.EFFECTS_SLIDER_TO_DEFAULT, command=self.update_pan_y, number_of_steps=int((self.EFFECTS_SLIDER_TO_DEFAULT - self.EFFECTS_SLIDER_FROM_DEFAULT) / self.EFFECTS_SLIDER_RESOLUTION))
        self.pan_y_slider.set(self.EFFECTS_PAN_DEFAULT)
        self.pan_y_slider.pack(side="left", expand=True, fill="x", padx=self.BUTTON_PADDING)
        self.pan_y_label = ctk.CTkLabel(pan_y_frame, text=f"{self.EFFECTS_PAN_DEFAULT:.2f}")
        self.pan_y_label.pack(side="right", padx=self.BUTTON_PADDING)

        # Rotation Control
        rotation_frame = ctk.CTkFrame(frame)
        rotation_frame.pack(fill="x", padx=self.UI_PADDING, pady=self.BUTTON_PADDING)
        ctk.CTkLabel(rotation_frame, text="Rotazione:").pack(side="left", padx=self.BUTTON_PADDING)
        self.rotation_slider = ctk.CTkSlider(rotation_frame, from_=0, to=self.EFFECTS_ROTATION_MAX, command=self.update_rotation)
        self.rotation_slider.set(self.EFFECTS_ROTATION_DEFAULT)
        self.rotation_slider.pack(side="left", expand=True, fill="x", padx=self.BUTTON_PADDING)
        self.rotation_label = ctk.CTkLabel(rotation_frame, text=f"{self.EFFECTS_ROTATION_DEFAULT:.0f}°")
        self.rotation_label.pack(side="right", padx=self.BUTTON_PADDING)
        
        # Distortion Control
        distortion_frame = ctk.CTkFrame(frame)
        distortion_frame.pack(fill="x", padx=self.UI_PADDING, pady=self.BUTTON_PADDING)
        ctk.CTkLabel(distortion_frame, text="Distorsione:").pack(side="left", padx=self.BUTTON_PADDING)
        self.distortion_slider = ctk.CTkSlider(distortion_frame, from_=0, to=self.EFFECTS_DISTORTION_MAX, command=self.update_distortion)
        self.distortion_slider.set(self.EFFECTS_DISTORTION_DEFAULT)
        self.distortion_slider.pack(side="left", expand=True, fill="x", padx=self.BUTTON_PADDING)
        self.distortion_label = ctk.CTkLabel(distortion_frame, text=f"{self.EFFECTS_DISTORTION_DEFAULT:.2f}")
        self.distortion_label.pack(side="right", padx=self.BUTTON_PADDING)

    def create_resize_section(self):
        """Sezione UI per il ridimensionamento della finestra principale (utile per VMix)."""
        frame = ctk.CTkFrame(self.main_frame)
        frame.pack(fill="x", pady=(0, self.UI_PADDING))
        
        ctk.CTkLabel(frame, text="🎛️ SCALA FINESTRA", font=("Arial", self.SECTION_TITLE_FONT_SIZE, self.BOLD_FONT_WEIGHT)).pack(pady=(self.BUTTON_PADDING * 2, self.BUTTON_PADDING))
        
        scale_frame = ctk.CTkFrame(frame)
        scale_frame.pack(fill="x", padx=self.UI_PADDING, pady=(0, self.UI_PADDING))
        
        ctk.CTkLabel(scale_frame, text="Fattore:").pack(side="left", padx=self.BUTTON_PADDING)
        self.scale_var = ctk.DoubleVar(value=1.0)
        ctk.CTkSlider(scale_frame, from_=0.5, to=2.0, variable=self.scale_var, command=self.update_scale).pack(side="left", expand=True, fill="x", padx=self.BUTTON_PADDING)
        self.scale_label = ctk.CTkLabel(scale_frame, text="100%")
        self.scale_label.pack(side="right", padx=self.BUTTON_PADDING)

    def setup_resize_handle(self):
        """Configura l'handle di ridimensionamento nell'angolo in basso a destra della finestra principale."""
        handle_size = self.RESIZE_HANDLE_SIZE
        self.resize_handle = ctk.CTkFrame(self.root, width=handle_size, height=handle_size, corner_radius=0)
        self.resize_handle.place(relx=1.0, rely=1.0, anchor="se")
        self.resize_handle.bind("<Button-1>", self.start_resize)
        self.resize_handle.bind("<B1-Motion>", self.do_resize)
        self.root.bind("<Configure>", self.update_resize_handle_position) # Aggiorna posizione handle al resize finestra
        
    def update_resize_handle_position(self, event=None):
        """Aggiorna la posizione dell'handle di ridimensionamento dopo un evento di configurazione della finestra."""
        try:
            if hasattr(self, 'resize_handle'):
                self.resize_handle.place(relx=1.0, rely=1.0, anchor="se")
        except Exception as e:
            print(f"Errore durante l'aggiornamento della posizione dell'handle di ridimensionamento: {e}")
            traceback.print_exc()
            
    # --- METODI PER IL CARICAMENTO E GESTIONE SHADER LOCALI ---
    def load_shader_folder(self):
        """Gestisce il caricamento di una cartella contenente file shader."""
        try:
            folder = filedialog.askdirectory(title="Seleziona cartella shader")
            if folder:
                self.shader_folder = folder
                self.scan_shader_files() # Avvia la scansione dei file nella cartella selezionata
                self.shader_status_label.configure(text=f"Cartella caricata: {os.path.basename(folder)}")
        except Exception as e:
            print(f"Errore durante il caricamento della cartella shader: {e}")
            traceback.print_exc()
            
    def scan_shader_files(self):
        """Scansiona i file shader nella cartella selezionata e li aggiunge alla libreria."""
        self.shader_files = [] # Resetta la lista dei file shader
        
        try:
            if not os.path.exists(self.shader_folder):
                self.shader_status_label.configure(text="Errore: Cartella non trovata o non valida.")
                self.update_shader_list() # Pulisce la lista se la cartella non è valida
                return
                
            found_files = self.scan_shader_directory(self.shader_folder, self.file_manager_config['recursive_scan'])
            
            if found_files:
                self.shader_files = found_files
                self.shader_status_label.configure(text="Elaborazione shader in corso...")
                # Processa i file in un thread separato per non bloccare l'UI
                threading.Thread(target=self._process_shader_files_thread, daemon=True).start()
            else:
                self.shader_status_label.configure(text="Nessun shader (.frag, .glsl, .fs, .shader) trovato nella cartella.")
                self.update_shader_list()
                
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante la scansione degli shader: {e}")
            traceback.print_exc()
            self.shader_status_label.configure(text="Errore durante la scansione.")

    def _process_shader_files_thread(self):
        """Thread separato per elaborare i file shader e aggiornare la cache."""
        try:
            processed_count = self.process_shader_files(self.shader_files)
            self.root.after(0, self.finalize_shader_scan, processed_count)
        except Exception as e:
            print(f"Errore critico nel thread di elaborazione shader: {e}")
            traceback.print_exc()
            self.root.after(0, lambda: self.shader_status_label.configure(text="Errore critico durante l'elaborazione dei file."))
            
    def finalize_shader_scan(self, processed_count):
        """Finalizza la scansione degli shader e aggiorna l'interfaccia utente."""
        try:
            self.update_shader_list()
            self.shader_status_label.configure(text=f"Caricati {processed_count} shader.")
        except Exception as e:
            print(f"Errore durante la finalizzazione della scansione shader: {e}")
            traceback.print_exc()
            
    def update_shader_list(self):
        """Aggiorna la visualizzazione della lista degli shader nell'interfaccia, includendo il pulsante per caricare su Bonzomatic."""
        try:
            for widget in self.shader_list_frame.winfo_children():
                widget.destroy()
                
            if not self.shader_files:
                ctk.CTkLabel(self.shader_list_frame, text="Nessun shader caricato.", font=("Arial", self.SUB_LABEL_FONT_SIZE)).pack(pady=self.UI_PADDING)
                return

            for i, shader_path in enumerate(self.shader_files):
                shader_item_frame = ctk.CTkFrame(self.shader_list_frame)
                shader_item_frame.pack(fill="x", pady=self.SHADER_ITEM_PADDING_Y)
                
                display_info = self.get_shader_display_info(shader_path)
                
                # Icona e titolo shader
                icon = "✅" if display_info['valid'] else "❌"
                title_text = display_info['title'] or os.path.basename(shader_path)
                if len(title_text) > self.SHADER_TITLE_TRUNCATE_LENGTH:
                    title_text = title_text[:self.SHADER_TITLE_TRUNCATE_LENGTH] + "..."

                item_label = ctk.CTkLabel(shader_item_frame, text=f"{icon} {title_text}", font=("Arial", self.SUB_LABEL_FONT_SIZE + 1, self.BOLD_FONT_WEIGHT))
                item_label.pack(side="left", padx=self.BUTTON_PADDING, expand=True, anchor="w")

                # Pulsante "Carica su Bonzomatic" per anteprima/uso
                load_bonzo_btn = ctk.CTkButton(shader_item_frame, text="Carica su Bonzomatic", command=lambda s=shader_path: self.load_shader_to_bonzomatic(s))
                load_bonzo_btn.pack(side="right", padx=self.BUTTON_PADDING)
                
        except Exception as e:
            print(f"Errore durante l'aggiornamento della lista shader: {e}")
            traceback.print_exc()
            
    def load_shader_to_bonzomatic(self, shader_path):
        """Carica lo shader selezionato su Bonzomatic salvandolo in un file live_shader.frag."""
        try:
            if not self.bonzomatic_path:
                messagebox.showwarning("Avviso", "Percorso Bonzomatic non configurato. Avvia Bonzomatic o selezionalo manualmente.")
                return

            if not self.is_bonzomatic_running():
                messagebox.showwarning("Avviso", "Bonzomatic non è in esecuzione. Avvia Bonzomatic prima di caricare uno shader.")
                return

            bonzo_working_dir = self.bonzomatic_config["working_dir"]
            live_shader_filepath = os.path.join(bonzo_working_dir, self.BONZOMATIC_LIVE_SHADER_FILENAME)

            with open(shader_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Converti anche shader locali per uniformità con Bonzomatic
            converted_code = self.convert_shadertoy_to_bonzomatic(content)

            with open(live_shader_filepath, 'w', encoding='utf-8') as f:
                f.write(converted_code)
            
            messagebox.showinfo("Shader Caricato", f"Shader '{os.path.basename(shader_path)}' caricato su Bonzomatic come '{self.BONZOMATIC_LIVE_SHADER_FILENAME}'.\nBonzomatic dovrebbe ricaricarlo automaticamente.")
            print(f"Shader '{os.path.basename(shader_path)}' scritto in '{live_shader_filepath}' per Bonzomatic.")
            
        except Exception as e:
            messagebox.showerror("Errore Caricamento Shader", f"Errore durante il caricamento dello shader su Bonzomatic: {e}")
            print(f"Errore caricamento shader su Bonzomatic: {e}")
            traceback.print_exc()

    # --- METODI PER IL CONTROLLO DI BONZOMATIC ---
    def find_bonzomatic_executable(self):
        """Trova automaticamente l'eseguibile di Bonzomatic."""
        target_exe = self.BONZOMATIC_EXECUTABLE_NAME
        found_path = None
        
        # 1. Cerca nella stessa cartella dello script Python
        try:
            script_dir = os.path.dirname(os.path.realpath(__file__))
            path = os.path.join(script_dir, target_exe)
            if os.path.isfile(path):
                print(f"✅ Bonzomatic trovato nella cartella dello script: {path}.")
                return os.path.abspath(path)
        except Exception: pass # Ignora errore NameError se __file__ non definito

        # 2. Cerca in cartelle comuni
        common_dirs = [".", "./Bonzomatic/", os.path.join(os.environ.get('PROGRAMFILES', ''), 'Bonzomatic'), os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Bonzomatic'), os.path.join(Path.home(), 'Documents', 'Bonzomatic')]
        for directory in common_dirs:
            try:
                path_to_check = os.path.join(directory, target_exe)
                if os.path.isfile(path_to_check):
                    print(f"✅ Bonzomatic trovato in: {path_to_check}.")
                    return os.path.abspath(path_to_check)
            except Exception: pass

        # 3. Cerca nella PATH di sistema (solo su Windows)
        if platform.system() == "Windows":
            try:
                result = subprocess.run(["where", target_exe], capture_output=True, text=True, check=True, creationflags=self.SUBPROCESS_CREATE_NO_WINDOW_FLAG)
                if result.stdout.strip():
                    found_path = result.stdout.strip().split('\n')[0].strip()
                    if os.path.isfile(found_path):
                        print(f"✅ Bonzomatic trovato nella PATH di sistema: {found_path}.")
                        return found_path
            except Exception: pass
            
        print(f"❌ {target_exe} non trovato automaticamente.")
        return None

    def setup_bonzomatic_path(self):
        """Configura il percorso dell'eseguibile di Bonzomatic (tentativo automatico o richiesta all'utente)."""
        try:
            if self.bonzomatic_config["auto_find"]:
                found_path = self.find_bonzomatic_executable()
                if found_path:
                    self.bonzomatic_path = found_path
                    self.bonzomatic_config["working_dir"] = os.path.dirname(found_path)
                    print(f"Percorso Bonzomatic impostato automaticamente a: {self.bonzomatic_path}.")
                    return True
            messagebox.showinfo("Bonzomatic non trovato", "Bonzomatic_W64_DX11.exe non trovato automaticamente. Per favore, selezionalo manualmente.")
            return self.prompt_bonzomatic_path()
        except Exception as e:
            print(f"Errore durante il setup del percorso Bonzomatic: {e}")
            traceback.print_exc()
            return False

    def prompt_bonzomatic_path(self):
        """Chiede all'utente di selezionare manualmente l'eseguibile di Bonzomatic."""        
        try:
            path = filedialog.askopenfilename(title=f"Seleziona l'eseguibile di {self.BONZOMATIC_EXECUTABLE_NAME}", filetypes=[(self.BONZOMATIC_EXECUTABLE_NAME, self.BONZOMATIC_EXECUTABLE_NAME), ("Tutti gli eseguibili", "*.exe")])
            if path and os.path.isfile(path):
                filename = os.path.basename(path)
                if filename == self.BONZOMATIC_EXECUTABLE_NAME:
                    self.bonzomatic_path = path
                    self.bonzomatic_config["working_dir"] = os.path.dirname(path)
                    print(f"✅ Bonzomatic selezionato manualmente: {filename}.")
                    return True
                else:
                    messagebox.showerror("Errore Selezione", f"Seleziona SOLO l'eseguibile {self.BONZOMATIC_EXECUTABLE_NAME}.")
                    return False
            elif path:
                messagebox.showerror("Errore Selezione", "File non valido o non esistente.")
            print("Selezione manuale Bonzomatic annullata o non valida.")
            return False
        except Exception as e:
            print(f"Errore nel prompt di selezione percorso Bonzomatic: {e}")
            traceback.print_exc()
            return False
            
    def is_bonzomatic_running(self):
        """Verifica se il processo di Bonzomatic è attualmente in esecuzione."""
        if self.bonzomatic_process is None: return False
        try: return self.bonzomatic_process.poll() is None
        except Exception as e:
            print(f"Errore durante la verifica dello stato del processo Bonzomatic: {e}")
            traceback.print_exc()
            return False

    def get_bonzomatic_window_handle(self):
        """Ottiene l'handle della finestra di Bonzomatic (specifico per Windows)."""
        if not WIN32GUI_AVAILABLE: return None
        try:
            def enum_windows_callback(hwnd, windows_list):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    if self.bonzomatic_config["window_title"].lower() in window_text.lower(): windows_list.append(hwnd)
                return True
            windows_found = []
            win32gui.EnumWindows(enum_windows_callback, windows_found)
            if windows_found:
                print(f"Trovata finestra Bonzomatic con handle: {windows_found[0]}.")
                return windows_found[0]
            print("Finestra Bonzomatic non trovata.")
            return None
        except Exception as e:
            print(f"Errore durante la ricerca dell'handle della finestra di Bonzomatic: {e}")
            traceback.print_exc()
            return None

    def start_bonzomatic_process(self):
        """Avvia l'eseguibile di Bonzomatic come processo separato."""
        try:
            if not self.bonzomatic_path:
                if not self.setup_bonzomatic_path():
                    messagebox.showerror("Avvio Bonzomatic", f"Eseguibile Bonzomatic ({self.BONZOMATIC_EXECUTABLE_NAME}) non trovato o non selezionato. Impossibile avviare.")
                    return False
            if self.is_bonzomatic_running():
                print("Bonzomatic è già in esecuzione.")
                self.root.after(0, self.on_bonzomatic_started)
                return True

            cmd_args = [self.bonzomatic_path] + self.bonzomatic_config["arguments"]
            working_dir = self.bonzomatic_config["working_dir"] or os.path.dirname(self.bonzomatic_path)
            print(f"Avvio Bonzomatic: Comando='{' '.join(cmd_args)}', Working Dir='{working_dir}'")
            
            self.bonzomatic_process = subprocess.Popen(cmd_args, cwd=working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=self.SUBPROCESS_CREATE_NO_WINDOW_FLAG)
            print(f"Processo Bonzomatic avviato con PID: {self.bonzomatic_process.pid}.")
            self.wait_for_bonzomatic_window()
            return True
        except FileNotFoundError as e:
            messagebox.showerror("Errore Avvio", f"Impossibile avviare Bonzomatic: file non trovato.\n{e}")
            print(f"Errore File non trovato durante avvio Bonzomatic: {e}")
            traceback.print_exc()
            return False
        except Exception as e:
            messagebox.showerror("Errore Avvio", f"Errore generico durante l'avvio di Bonzomatic: {e}")
            print(f"Errore generico avvio Bonzomatic: {e}")
            traceback.print_exc()
            return False

    def wait_for_bonzomatic_window(self):
        """Attende che la finestra di Bonzomatic sia disponibile e ne recupera l'handle."""
        def wait_thread_task():
            try:
                timeout = self.BONZOMATIC_WINDOW_DETECT_TIMEOUT
                start_time = time.time()
                handle_found = None
                while time.time() - start_time < timeout:
                    if self.is_bonzomatic_running():
                        handle_found = self.get_bonzomatic_window_handle()
                        if handle_found:
                            self.bonzomatic_window_handle = handle_found
                            self.root.after(0, self.on_bonzomatic_started)
                            print(f"Finestra Bonzomatic rilevata dopo {time.time() - start_time:.2f} secondi.")
                            return
                    time.sleep(self.PROCESS_SCAN_SLEEP_SECONDS)
                self.root.after(0, self.on_bonzomatic_started)
                if not handle_found:
                    self.root.after(0, lambda: self.bonzo_status.configure(text="Stato: Avviato (finestra non rilevata o minimizzata)."))
                    print("Avviso: Bonzomatic avviato ma handle finestra non rilevato entro il timeout.")
            except Exception as e:
                print(f"Errore critico nel thread di attesa finestra Bonzomatic: {e}")
                traceback.print_exc()
        threading.Thread(target=wait_thread_task, daemon=True).start()
        
    def stop_bonzomatic_process(self):
        """Ferma il processo di Bonzomatic, prima in modo grazioso, poi forzatamente."""
        try:
            if not self.is_bonzomatic_running():
                print("Bonzomatic non è in esecuzione, nessuna azione necessaria per fermarlo.")
                self.root.after(0, self.on_bonzomatic_stopped)
                return True
            print("Tentativo di fermare Bonzomatic...")
            if WIN32GUI_AVAILABLE and self.bonzomatic_window_handle:
                try:
                    win32gui.PostMessage(self.bonzomatic_window_handle, 0x0010, 0, 0)
                    print("Inviato messaggio WM_CLOSE alla finestra Bonzomatic.")
                    for _ in range(int(self.BONZOMATIC_STOP_GRACEFUL_WAIT_SECONDS * 10)):
                        if not self.is_bonzomatic_running():
                            print("Bonzomatic terminato graziosamente.")
                            break
                        time.sleep(0.1)
                except Exception as e:
                    print(f"Errore durante il tentativo di chiusura graziosa di Bonzomatic: {e}")
                    traceback.print_exc()
            if self.is_bonzomatic_running():
                print("Bonzomatic non ha terminato graziosamente. Tentativo di terminazione forzata...")
                self.bonzomatic_process.terminate()
                try:
                    self.bonzomatic_process.wait(timeout=self.BONZOMATIC_TERMINATE_TIMEOUT)
                    print("Bonzomatic terminato forzatamente.")
                except subprocess.TimeoutExpired:
                    print("Timeout per la terminazione forzata. Tentativo di kill...")
                    self.bonzomatic_process.kill()
                    self.bonzomatic_process.wait()
                    print("Bonzomatic killato.")
            self.bonzomatic_process = None
            self.bonzomatic_window_handle = None
            self.root.after(0, self.on_bonzomatic_stopped)
            print("Processo Bonzomatic fermato e risorse liberate.")
            return True
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'arresto di Bonzomatic: {e}")
            print(f"Errore critico durante l'arresto di Bonzomatic: {e}")
            traceback.print_exc()
            return False

    def show_bonzomatic_window(self):
        """Porta la finestra di Bonzomatic in primo piano."""
        if not self.is_bonzomatic_running():
            messagebox.showwarning("Avviso", "Bonzomatic non è in esecuzione.")
            return
        if WIN32GUI_AVAILABLE and self.bonzomatic_window_handle:
            try:
                win32gui.ShowWindow(self.bonzomatic_window_handle, 1) # SW_SHOW
                win32gui.SetForegroundWindow(self.bonzomatic_window_handle)
                print("Finestra Bonzomatic portata in primo piano.")
            except Exception as e:
                messagebox.showinfo("Info", f"Impossibile mostrare finestra Bonzomatic: {e}")
                print(f"Errore mostrando finestra Bonzomatic: {e}")
                traceback.print_exc()
        else:
            messagebox.showinfo("Info", "Funzione 'Mostra Finestra' non supportata o Bonzomatic non avviato/finestra non trovata.")

    def monitor_bonzomatic_process(self):
        """Monitora lo stato del processo Bonzomatic per rilevare terminazioni inaspettate."""
        self.bonzomatic_monitor_active = True
        def monitor_thread_task():
            try:
                while self.bonzomatic_monitor_active:
                    if self.bonzomatic_process and not self.is_bonzomatic_running():
                        self.bonzomatic_monitor_active = False
                        self.root.after(0, self.on_bonzomatic_crashed)
                        print("Bonzomatic terminato inaspettatamente.")
                        break
                    time.sleep(self.BONZOMATIC_MONITOR_INTERVAL_SECONDS)
            except Exception as e:
                print(f"Errore nel thread di monitoraggio Bonzomatic: {e}")
                traceback.print_exc()
        if self.is_bonzomatic_running():
            threading.Thread(target=monitor_thread_task, daemon=True).start()

    # --- CALLBACK UI BONZOMATIC ---
    def on_bonzomatic_started(self):
        """Callback quando Bonzomatic si avvia con successo."""
        try:
            self.bonzo_start_btn.configure(state="disabled")
            self.bonzo_stop_btn.configure(state="normal")
            self.bonzo_show_btn.configure(state="normal")
            self.bonzo_status.configure(text="Stato: In esecuzione ✓")
            self.monitor_bonzomatic_process()
            print("UI Bonzomatic aggiornata: Avviato.")
        except Exception as e:
            print(f"Errore nella callback 'Bonzomatic avviato': {e}")
            traceback.print_exc()

    def on_bonzomatic_stopped(self):
        """Callback quando Bonzomatic si ferma."""
        try:
            self.bonzomatic_monitor_active = False
            self.bonzo_start_btn.configure(state="normal")
            self.bonzo_stop_btn.configure(state="disabled")
            self.bonzo_show_btn.configure(state="disabled")
            self.bonzo_status.configure(text="Stato: Fermato.")
            print("UI Bonzomatic aggiornata: Fermato.")
        except Exception as e:
            print(f"Errore nella callback 'Bonzomatic fermato': {e}")
            traceback.print_exc()

    def on_bonzomatic_crashed(self):
        """Callback quando Bonzomatic termina inaspettatamente."""
        try:
            self.bonzomatic_monitor_active = False
            self.bonzo_start_btn.configure(state="normal")
            self.bonzo_stop_btn.configure(state="disabled")
            self.bonzo_show_btn.configure(state="disabled")
            self.bonzo_status.configure(text="Stato: Terminato inaspettatamente ⚠️")
            self.bonzomatic_process = None
            self.bonzomatic_window_handle = None
            messagebox.showwarning("Bonzomatic", "Bonzomatic è terminato inaspettatamente! Controlla il terminale per errori.")
            print("UI Bonzomatic aggiornata: Crash rilevato.")
        except Exception as e:
            print(f"Errore nella callback 'Bonzomatic crashato': {e}")
            traceback.print_exc()

    # --- METODI PER GLI EFFETTI VIDEO ---
    def update_zoom(self, value):
        """Aggiorna il fattore di zoom e il label associato."""
        self.effect_zoom = float(value)
        self.zoom_label.configure(text=f"{self.effect_zoom:.2f}")
        self.write_bonzomatic_params() # Scrive i parametri aggiornati

    def update_pan_x(self, value):
        """Aggiorna il fattore di Pan X e il label associato."""
        self.effect_pan_x = float(value)
        self.pan_x_label.configure(text=f"{self.effect_pan_x:.2f}")
        self.write_bonzomatic_params() # Scrive i parametri aggiornati

    def update_pan_y(self, value):
        """Aggiorna il fattore di Pan Y e il label associato."""
        self.effect_pan_y = float(value)
        self.pan_y_label.configure(text=f"{self.effect_pan_y:.2f}")
        self.write_bonzomatic_params() # Scrive i parametri aggiornati

    def update_rotation(self, value):
        """Aggiorna il fattore di Rotazione e il label associato."""
        self.effect_rotation = float(value)
        self.rotation_label.configure(text=f"{self.effect_rotation:.0f}°")
        self.write_bonzomatic_params() # Scrive i parametri aggiornati

    def update_distortion(self, value):
        """Aggiorna il fattore di Distorsione e il label associato."""
        self.effect_distortion = float(value)
        self.distortion_label.configure(text=f"{self.effect_distortion:.2f}")
        self.write_bonzomatic_params() # Scrive i parametri aggiornati

    def toggle_audio_zoom_effect(self):
        """Attiva/disattiva la modulazione dello zoom basata sull'audio."""
        self.audio_zoom_enabled = not self.audio_zoom_enabled
        if self.audio_zoom_enabled:
            print("Modulazione Zoom tramite Audio (Beat/Bassi) abilitata.")
            # Assicurati che la cattura audio sia avviata se l'effetto è attivo
            if not self.audio_recording and AUDIO_AVAILABLE:
                self.start_audio_capture()
        else:
            print("Modulazione Zoom tramite Audio disabilitata.")
            # Resetta lo zoom al valore di default quando disabilitato
            self.root.after(0, lambda: self.zoom_slider.set(self.EFFECTS_ZOOM_DEFAULT))

    def write_bonzomatic_params(self):
        """Scrive i parametri degli effetti e dell'audio in un file JSON per Bonzomatic."""
        try:
            if not self.bonzomatic_path:
                return # Non scrivere se Bonzomatic non è configurato

            params_filepath = os.path.join(self.bonzomatic_config["working_dir"], self.BONZOMATIC_PARAMS_FILENAME)
            
            # Parametri audio
            audio_params = {
                "bpm": self.current_bpm,
                "beat_detected": self.beat_detected,
                "audio_level": self.audio_level,
                "bass_level": self.bass_level,
                "fFreq1": float(self.frequency_data[0]) if self.frequency_data and len(self.frequency_data) >= 4 else 0.0,
                "fFreq2": float(self.frequency_data[1]) if self.frequency_data and len(self.frequency_data) >= 4 else 0.0,
                "fFreq3": float(self.frequency_data[2]) if self.frequency_data and len(self.frequency_data) >= 4 else 0.0,
                "fFreq4": float(self.frequency_data[3]) if self.frequency_data and len(self.frequency_data) >= 4 else 0.0,
            }

            # Valori degli effetti video (con modulazione audio per zoom se attiva)
            current_zoom = self.effect_zoom
            if self.audio_zoom_enabled and self.beat_detected:
                # Esempio di modulazione: zoom leggermente in base al livello audio o al beat
                current_zoom = self.EFFECTS_ZOOM_DEFAULT + (self.audio_level * (self.EFFECTS_ZOOM_MAX - self.EFFECTS_ZOOM_DEFAULT) / 0.5) # Esempio semplice
                current_zoom = max(self.EFFECTS_ZOOM_MIN, min(self.EFFECTS_ZOOM_MAX, current_zoom)) # Limita al range dello slider
            elif self.audio_zoom_enabled and self.bass_response_enabled:
                current_zoom = self.EFFECTS_ZOOM_DEFAULT + (self.bass_level * (self.EFFECTS_ZOOM_MAX - self.EFFECTS_ZOOM_DEFAULT) / self.BASS_LEVEL_EFFECT_THRESHOLD)
                current_zoom = max(self.EFFECTS_ZOOM_MIN, min(self.EFFECTS_ZOOM_MAX, current_zoom))

            effect_params = {
                "zoom": current_zoom,
                "pan_x": self.effect_pan_x,
                "pan_y": self.effect_pan_y,
                "rotation": self.effect_rotation,
                "distortion": self.effect_distortion
            }

            all_params = {"audio": audio_params, "effects": effect_params}
            
            with open(params_filepath, 'w', encoding='utf-8') as f:
                json.dump(all_params, f, indent=4)
            # print(f"Parametri Bonzomatic scritti in: {params_filepath}") # Troppo log, commentato
            
        except Exception as e:
            print(f"Errore durante la scrittura dei parametri di Bonzomatic: {e}")
            traceback.print_exc()

    # --- METODI GENERALI DELL'APP ---
    def update_scale(self, value):
        """Aggiorna il fattore di scala globale della finestra."""
        try:
            self.scale_factor = value
            percentage = int(value * 100)
            self.scale_label.configure(text=f"{percentage}%")
            new_width = int(self.DEFAULT_APP_WIDTH * value)
            new_height = int(self.DEFAULT_APP_HEIGHT * value)
            self.root.geometry(f"{new_width}x{new_height}")
            print(f"Finestra ridimensionata a {new_width}x{new_height} ({percentage}%).")
        except Exception as e:
            print(f"Errore durante l'aggiornamento della scala della finestra: {e}")
            traceback.print_exc()

    def setup_resize_handle(self):
        """Configura l'handle di ridimensionamento nell'angolo in basso a destra della finestra principale."""
        handle_size = self.RESIZE_HANDLE_SIZE
        self.resize_handle = ctk.CTkFrame(self.root, width=handle_size, height=handle_size, corner_radius=0)
        self.resize_handle.place(relx=1.0, rely=1.0, anchor="se")
        self.resize_handle.bind("<Button-1>", self.start_resize)
        self.resize_handle.bind("<B1-Motion>", self.do_resize)
        self.root.bind("<Configure>", self.update_resize_handle_position) # Aggiorna posizione handle al resize finestra
        
    def update_resize_handle_position(self, event=None):
        """Aggiorna la posizione dell'handle di ridimensionamento dopo un evento di configurazione della finestra."""
        try:
            if hasattr(self, 'resize_handle'):
                self.resize_handle.place(relx=1.0, rely=1.0, anchor="se")
        except Exception as e:
            print(f"Errore durante l'aggiornamento della posizione dell'handle di ridimensionamento: {e}")
            traceback.print_exc()
            
    def start_resize(self, event):
        """Inizia l'operazione di ridimensionamento della finestra dal handle."""
        try:
            self.start_x = event.x_root
            self.start_y = event.y_root
            self.start_width = self.root.winfo_width()
            self.start_height = self.root.winfo_height()
        except Exception as e:
            print(f"Errore in start_resize: {e}")
            traceback.print_exc()
            
    def do_resize(self, event):
        """Esegue il ridimensionamento della finestra durante il trascinamento del handle."""
        try:
            delta_x = event.x_root - self.start_x
            delta_y = event.y_root - self.start_y
            
            new_width = max(self.MIN_APP_WIDTH, self.start_width + delta_x)
            new_height = max(self.MIN_APP_HEIGHT, self.start_height + delta_y)
            
            self.root.geometry(f"{new_width}x{new_height}")
        except Exception as e:
            print(f"Errore in do_resize: {e}")
            traceback.print_exc()

    def setup_vmix_output(self):
        """Configura gli attributi della finestra principale per l'ottimizzazione con VMix (minimal)."""
        try:
            if not self.root or not self.root.winfo_exists():
                print("Avviso: self.root non è inizializzato o non esiste più in setup_vmix_output. Ignoro le impostazioni VMix.")
                return False

            if self.vmix_config["window_always_on_top"]:
                try:
                    self.root.attributes('-topmost', True)
                    print("Impostato: finestra 'sempre in primo piano'.")
                except tk.TclError as e:
                    print(f"ATTENZIONE: Impossibile impostare 'always_on_top': {e}. La funzionalità potrebbe non essere supportata dal tuo ambiente.")
                    traceback.print_exc()
                
            if self.vmix_config["transparent_background"]:
                try:
                    self.root.attributes('-alpha', 0.95) # 0.95 = 95% opacità, 5% trasparenza
                    print("Impostato: trasparenza (-alpha 0.95).")
                except tk.TclError as e:
                    print(f"ATTENZIONE: Impossibile impostare 'trasparenza' (-alpha): {e}. La funzionalità potrebbe non essere supportata dal tuo ambiente.")
                    traceback.print_exc()
                    
            print("Setup VMix output completato.")
            return True
        except Exception as e:
            print(f"Errore durante il setup di VMix: {e}")
            traceback.print_exc()
            return False
            
    def optimize_performance(self):
        """Placeholder per future ottimizzazioni delle performance (non implementato in questa versione leggera)."""
        # Questa funzione è un placeholder per future espansioni.
        pass
            
    def integrate_all_systems(self):
        """Coordina l'integrazione e la sincronizzazione tra i vari sistemi attivi (audio, Bonzomatic)."""
        try:
            systems_active = 0
            if self.is_bonzomatic_running(): systems_active += 1
            # Shadertoy non è più parte dell'integrazione core in questa versione leggera.
            if self.audio_recording:
                systems_active += 1
                # start_audio_sync_loop è ora chiamato da start_audio_capture.
                
            if systems_active >= self.MIN_SYSTEMS_FOR_INTEGRATION:
                print(f"Integrazione base attiva: {systems_active} sistemi rilevati.")
            else:
                print(f"Integrazione base disabilitata: solo {systems_active} sistemi attivi (richiesti {self.MIN_SYSTEMS_FOR_INTEGRATION}).")
                
        except Exception as e:
            print(f"Errore durante l'integrazione dei sistemi: {e}")
            traceback.print_exc()
        
    def on_closing(self):
        """Gestisce la chiusura dell'applicazione, fermando tutti i processi in background."""
        try:
            print("Chiusura dell'applicazione. Terminazione processi in background...")
            if self.bonzomatic_process: self.stop_bonzomatic_process()
            self.stop_audio_capture()
            # Non c'è browser_driver da chiudere in questa versione leggera, ma il browser potrebbe essere aperto se l'utente ha cliccato "Apri Shadertoy.com"
            # Quindi, forziamo la chiusura del driver se esiste
            if hasattr(self, 'browser_driver') and self.browser_driver:
                try:
                    self.browser_driver.quit()
                    print("Driver browser chiuso durante la chiusura dell'app.")
                except Exception as e:
                    print(f"Errore durante la chiusura del browser driver in on_closing: {e}")
                    traceback.print_exc()

            # Salva cache shader, se abilitata
            if hasattr(self, 'file_manager_config') and self.file_manager_config.get('cache_enabled', False):
                self.save_shader_cache()
            
            self.root.destroy()
            print("Applicazione chiusa con successo.")
        except Exception as e:
            print(f"Errore durante la chiusura dell'applicazione: {e}")
            traceback.print_exc()
        
    def run(self):
        """Avvia il mainloop dell'applicazione GUI."""
        try:
            print("Tentativo di avvio del mainloop di CustomTkinter...")
            self.root.mainloop()
            print("Mainloop CustomTkinter terminato.")
        except Exception as e:
            print(f"Errore durante l'esecuzione del main loop: {e}")
            traceback.print_exc()

    # --- METODI DI SUPPORTO PER FILE MANAGER E SHADER (DA VERSIONI PRECEDENTI) ---
    def load_shader_cache(self):
        """Carica i metadati degli shader dalla cache (file JSON)."""
        try:
            if os.path.exists(self.SHADER_CACHE_FILENAME):
                with open(self.SHADER_CACHE_FILENAME, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                    self.shader_metadata = cache_data.get('shaders', {})
                    print(f"Cache shader caricata da {self.SHADER_CACHE_FILENAME}.")
                    return True
            print("Nessuna cache shader trovata.")
        except Exception as e:
            print(f"Errore durante il caricamento della cache shader: {e}")
            traceback.print_exc()
        return False
        
    def save_shader_cache(self):
        """Salva i metadati degli shader nella cache (file JSON)."""
        try:
            cache_data = {
                'version': '1.0',
                'timestamp': datetime.now().isoformat(),
                'shaders': self.shader_metadata
            }
            with open(self.SHADER_CACHE_FILENAME, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            print(f"Cache shader salvata in {self.SHADER_CACHE_FILENAME}.")
            return True
        except Exception as e:
            print(f"Errore durante il salvataggio della cache shader: {e}")
            traceback.print_exc()
        return False
        
    def cleanup_shader_cache(self):
        """Pulisce la cache degli shader rimuovendo le entry obsolete o in eccesso."""
        try:
            max_size = self.file_manager_config.get('max_cache_size', self.SHADER_CACHE_CLEANUP_THRESHOLD)
            if len(self.shader_metadata) <= max_size:
                return # Non è necessario pulire se la cache non supera la dimensione massima
                
            initial_count = len(self.shader_metadata)
            files_to_remove_from_cache = [
                filepath for filepath in list(self.shader_metadata.keys())
                if not os.path.exists(filepath)
            ]
            for filepath in files_to_remove_from_cache:
                del self.shader_metadata[filepath]
            
            removed_non_existent = len(files_to_remove_from_cache)
            if removed_non_existent > 0:
                print(f"Rimosse {removed_non_existent} entry di shader non esistenti dalla cache.")

            if len(self.shader_metadata) > max_size:
                sorted_files = sorted(self.shader_metadata.items(), key=lambda item: item[1].get('modified', 0))
                to_remove_by_size = len(sorted_files) - max_size
                for i in range(to_remove_by_size):
                    filepath = sorted_files[i][0]
                    del self.shader_metadata[filepath]
                print(f"Rimosse {to_remove_by_size} entry di shader più vecchie dalla cache per ridurre la dimensione.")
                
        except Exception as e:
            print(f"Errore durante la pulizia della cache shader: {e}")
            traceback.print_exc()
        
    def calculate_file_hash(self, filepath):
        """Calcola l'hash MD5 di un file per rilevare modifiche."""
        try:
            if not os.path.exists(filepath):
                print(f"Avviso: Il file {filepath} non esiste, impossibile calcolare l'hash.")
                return None
            
            with open(filepath, 'rb') as f:
                content = f.read()
                return hashlib.md5(content).hexdigest()
        except Exception as e:
            print(f"Errore durante il calcolo dell'hash del file {filepath}: {e}")
            traceback.print_exc()
            return None
            
    def parse_shader_metadata(self, filepath):
        """Estrae i metadati (titolo, autore, tag, ecc.) da un file shader."""
        metadata = {
            'filepath': filepath, 'filename': os.path.basename(filepath),
            'size': 0, 'modified': 0, 'hash': '', 'title': '', 'author': '',
            'description': '', 'tags': [], 'uniforms': [], 'passes': 1,
            'type': 'fragment', 'shadertoy_id': '', 'valid': False, 'error': ''
        }
        try:
            filepath_obj = Path(filepath)
            stat = filepath_obj.stat()
            metadata['size'] = stat.st_size
            metadata['modified'] = stat.st_mtime
            metadata['hash'] = self.calculate_file_hash(filepath)
            
            with filepath_obj.open('r', encoding='utf-8') as f:
                content = f.read()
                
            metadata.update(self.extract_shader_info_from_content(content))
            
            validation_result = self.validate_shader_syntax(content)
            metadata['valid'] = validation_result['valid']
            metadata['error'] = validation_result.get('error', '')
            
        except Exception as e:
            metadata['error'] = str(e)
            print(f"Errore durante il parsing dei metadati dello shader per {filepath}: {e}")
            traceback.print_exc()
            
        return metadata
        
    def extract_shader_info_from_content(self, content):
        """Estrae informazioni specifiche dai commenti all'inizio del file shader."""
        info = {
            'title': '', 'author': '', 'description': '',
            'tags': [], 'uniforms': [], 'passes': 1, 'shadertoy_id': ''
        }
        patterns_to_extract = {
            'title': r'//\s*title\s*:\s*(.+?)(?:\n|$)', 'author': r'//\s*author\s*:\s*(.+?)(?:\n|$)',
            'description': r'//\s*description\s*:\s*(.+?)(?:\n|$)', 'tags': r'//\s*tags\s*:\s*(.+?)(?:\n|$)',
            'shadertoy': r'//\s*shadertoy\s*:\s*(.+?)(?:\n|$)'
        }
        for key, pattern in patterns_to_extract.items():
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                if key == 'tags': info[key] = [tag.strip() for tag in matches[0].split(',') if tag.strip()]
                elif key == 'shadertoy':
                    extracted_id = self.extract_shadertoy_id_from_url_static(matches[0].strip())
                    if extracted_id: info['shadertoy_id'] = extracted_id
                else: info[key] = matches[0].strip()
        
        uniform_pattern = r'uniform\s+(?:vec\d+|mat\d+|float|int|sampler2D|sampler3D)\s+(\w+)\s*;'
        uniforms = re.findall(uniform_pattern, content)
        info['uniforms'] = [{'type': 'auto_detected', 'name': u} for u in uniforms]
        main_count = len(re.findall(r'void\s+(?:mainImage|main)\s*\(', content))
        if main_count > 1: info['passes'] = main_count
        return info
        
    def extract_shadertoy_id_from_url_static(self, url_to_parse):
        """Versione statica di extract_shadertoy_id_from_url per l'uso nel parsing dei metadati."""
        try:
            if not url_to_parse: return None
            patterns = [
                r'shadertoy\.com/view/([a-zA-Z0-9]+)', r'shadertoy\.com/embed/([a-zA-Z0-9]+)', 
                r'view/([a-zA-Z0-9]{6,})', r'embed/([a-zA-Z0-9]{6,})',
                r'/([a-zA-Z0-9]{6,})(?:\?|$)', r'#([a-zA-Z0-9]{6,})'
            ]
            for pattern in patterns:
                match = re.search(pattern, url_to_parse)
                if match and len(match.group(1)) >= self.SHADERTOY_ID_MIN_LENGTH: return match.group(1)
            return None
        except Exception as e:
            print(f"Errore durante l'estrazione statica dell'ID shader: {e}")
            traceback.print_exc()
            return None

    def validate_shader_syntax(self, content):
        """Esegue una validazione sintattica di base per i file shader GLSL."""
        result = {'valid': True, 'error': ''}
        try:
            if 'void main(' not in content and 'void mainImage(' not in content:
                result['valid'] = False; result['error'] = 'Manca la funzione main() o mainImage().'; return result
            if 'gl_FragColor' not in content and 'fragColor' not in content and 'out vec4 fragColor' not in content:
                result['valid'] = False; result['error'] = 'Manca l\'assegnazione del colore di output (gl_FragColor o fragColor).'; return result
            open_braces = content.count('{'); close_braces = content.count('}')
            if open_braces != close_braces:
                result['valid'] = False; result['error'] = f'Parentesi graffe non bilanciate: {open_braces} aperte, {close_braces} chiuse.'; return result
        except Exception as e:
            result['valid'] = False; result['error'] = f"Errore critico durante la validazione sintattica: {e}"; traceback.print_exc()
        return result
        
    def scan_shader_directory(self, directory, recursive=True):
        """Scansiona una directory alla ricerca di file shader con estensioni supportate."""
        found_files = []
        try:
            if recursive:
                for root, dirs, files in os.walk(directory):
                    for file in files:
                        if any(file.lower().endswith(ext) for ext in self.supported_extensions):
                            found_files.append(os.path.join(root, file))
            else:
                for file in os.listdir(directory):
                    filepath = os.path.join(directory, file)
                    if os.path.isfile(filepath) and any(file.lower().endswith(ext) for ext in self.supported_extensions):
                        found_files.append(filepath)
            print(f"Trovati {len(found_files)} file shader nella directory: {directory}.")
        except (OSError, PermissionError) as e:
            messagebox.showerror("Errore Directory", f"Impossibile scansionare la directory: {e}")
            print(f"Errore OS/Permessi durante la scansione della directory {directory}: {e}")
            traceback.print_exc()
        return found_files
        
    def process_shader_files(self, file_list):
        """Elabora una lista di file shader, estraendo metadati e aggiornando la cache."""
        processed = 0; total = len(file_list)
        if self.file_manager_config['cache_enabled']: self.load_shader_cache()
        for filepath in file_list:
            try:
                need_reprocess = True
                if filepath in self.shader_metadata:
                    cached_hash = self.shader_metadata[filepath].get('hash', ''); current_hash = self.calculate_file_hash(filepath)
                    if cached_hash == current_hash: need_reprocess = False
                if need_reprocess:
                    metadata = self.parse_shader_metadata(filepath); self.shader_metadata[filepath] = metadata
                processed += 1
                if hasattr(self, 'shader_status_label') and hasattr(self, 'root'): # Usato shader_status_label
                    progress = int((processed / total) * 100)
                    try: self.root.after(0, lambda p=progress: self.shader_status_label.configure(text=f"Elaborazione shader: {p}% ({processed}/{total})"))
                    except Exception as e: print(f"Errore nell'aggiornamento della UI (progress bar): {e}"); traceback.print_exc(); pass
            except Exception as e:
                print(f"Errore durante l'elaborazione del file shader {filepath}: {e}"); traceback.print_exc()
        if self.file_manager_config['cache_enabled']: self.cleanup_shader_cache(); self.save_shader_cache()
        print(f"Elaborazione completata. Processati {processed} di {total} shader.")
        return processed
        
    def get_shader_display_info(self, filepath):
        """Ottiene le informazioni di uno shader per la visualizzazione nell'interfaccia utente."""
        try:
            if filepath not in self.shader_metadata:
                return {'title': os.path.basename(filepath), 'author': 'Unknown', 'valid': False, 'tags': [], 'description': 'Metadati non disponibili.', 'uniforms_count': 0, 'size_kb': 0}
            metadata = self.shader_metadata[filepath]
            title = metadata.get('title', '') or metadata.get('filename', os.path.basename(filepath))
            return {'title': title, 'author': metadata.get('author', 'Unknown'), 'valid': metadata.get('valid', False), 'tags': metadata.get('tags', []), 'description': metadata.get('description', ''), 'uniforms_count': len(metadata.get('uniforms', [])), 'size_kb': round(metadata.get('size', 0) / 1024, 1)}
        except Exception as e:
            print(f"Errore get_shader_display_info per {filepath}: {e}"); traceback.print_exc()
            return {'title': os.path.basename(filepath) if filepath else 'Sconosciuto', 'author': 'Errore', 'valid': False, 'tags': [], 'description': 'Errore caricamento metadati.', 'uniforms_count': 0, 'size_kb': 0}
        
    def filter_shaders_by_criteria(self, criteria):
        """Filtra la lista degli shader basandosi su criteri specificati (es. testo, validità, tag)."""
        filtered = []
        try:
            for filepath, metadata in self.shader_metadata.items():
                matches = True
                if criteria.get('text', ''):
                    text_search = criteria['text'].lower()
                    searchable_text = ' '.join([metadata.get('title', ''), metadata.get('author', ''), metadata.get('description', ''), ' '.join(metadata.get('tags', []))]).lower()
                    if text_search not in searchable_text: matches = False
                if criteria.get('valid_only', False):
                    if not metadata.get('valid', False): matches = False
                if criteria.get('tags', []):
                    shader_tags = {tag.lower() for tag in metadata.get('tags', [])}; required_tags = {tag.lower() for tag in criteria['tags']}
                    if not shader_tags.intersection(required_tags): matches = False
                if matches: filtered.append(filepath)
        except Exception as e:
            print(f"Errore durante il filtro degli shader: {e}"); traceback.print_exc()
        return filtered
        
    def convert_shadertoy_to_bonzomatic(self, content):
        """Converte il codice GLSL di uno shader da formato Shadertoy a formato Bonzomatic."""
        converted_code = content
        try:
            replacements = {'iResolution': 'v2Resolution', 'iTime': 'fGlobalTime', 'iMouse': 'v2Mouse', 'iFrame': 'iFrame', 'fragCoord': 'gl_FragCoord', 'fragColor': 'gl_FragColor', 'mainImage': 'main'}
            for old, new in replacements.items(): converted_code = converted_code.replace(old, new)
            converted_code = re.sub(r'void\s+mainImage\s*\(\s*out\s+vec4\s+\w+\s*,\s*in\s+vec2\s+\w+\s*\)', 'void main()', converted_code)
            if '#version' not in converted_code:
                header = '''#version 410 core\n\nuniform float fGlobalTime;\nuniform vec2 v2Resolution;\nuniform vec4 v4Mouse;\nout vec4 gl_FragColor;\n\n'''
                converted_code = header + converted_code
            print("Codice shader convertito per Bonzomatic.")
        except Exception as e:
            print(f"Errore durante la conversione Shadertoy a Bonzomatic: {e}"); traceback.print_exc()
        return converted_code
        
    def export_shader_for_bonzomatic(self, filepath, output_path=None):
        """Esporta uno shader in un file compatibile con Bonzomatic."""
        try:
            if filepath not in self.shader_metadata: raise ValueError("Shader non trovato nella cache. Impossibile esportare.")
            with open(filepath, 'r', encoding='utf-8') as f: content = f.read()
            converted_content = self.convert_shadertoy_to_bonzomatic(content)
            if not output_path:
                base_name = os.path.splitext(os.path.basename(filepath))[0]; output_path = os.path.join(os.path.dirname(filepath), f"{base_name}_bonzomatic.frag")
            with open(output_path, 'w', encoding='utf-8') as f: f.write(converted_content)
            print(f"Shader esportato per Bonzomatic in: {output_path}.")
            return output_path
        except Exception as e:
            messagebox.showerror("Errore Esportazione", f"Errore durante l'esportazione dello shader: {e}"); print(f"Errore esportazione shader: {e}"); traceback.print_exc(); return None
        
    # --- METODI PER IL CONTROLLO DI BONZOMATIC ---
    def find_bonzomatic_executable(self):
        """Trova automaticamente l'eseguibile di Bonzomatic."""
        target_exe = self.BONZOMATIC_EXECUTABLE_NAME
        try:
            script_dir = os.path.dirname(os.path.realpath(__file__)); path = os.path.join(script_dir, target_exe)
            if os.path.isfile(path): print(f"✅ Bonzomatic trovato nella cartella dello script: {path}."); return os.path.abspath(path)
        except Exception: pass
        common_dirs = [".", "./Bonzomatic/", os.path.join(os.environ.get('PROGRAMFILES', ''), 'Bonzomatic'), os.path.join(os.environ.get('PROGRAMFILES(X86)', ''), 'Bonzomatic'), os.path.join(Path.home(), 'Documents', 'Bonzomatic')]
        for directory in common_dirs:
            try:
                path_to_check = os.path.join(directory, target_exe)
                if os.path.isfile(path_to_check): print(f"✅ Bonzomatic trovato in: {path_to_check}."); return os.path.abspath(path_to_check)
            except Exception: pass
        if platform.system() == "Windows":
            try:
                result = subprocess.run(["where", target_exe], capture_output=True, text=True, check=True, creationflags=self.SUBPROCESS_CREATE_NO_WINDOW_FLAG)
                if result.stdout.strip():
                    found_path = result.stdout.strip().split('\n')[0].strip()
                    if os.path.isfile(found_path): print(f"✅ Bonzomatic trovato nella PATH di sistema: {found_path}."); return found_path
            except Exception: pass
        print(f"❌ {target_exe} non trovato automaticamente.")
        return None

    def setup_bonzomatic_path(self):
        """Configura il percorso dell'eseguibile di Bonzomatic (tentativo automatico o richiesta all'utente)."""
        try:
            if self.bonzomatic_config["auto_find"]:
                found_path = self.find_bonzomatic_executable()
                if found_path:
                    self.bonzomatic_path = found_path; self.bonzomatic_config["working_dir"] = os.path.dirname(found_path); print(f"Percorso Bonzomatic impostato automaticamente a: {self.bonzomatic_path}."); return True
            messagebox.showinfo("Bonzomatic non trovato", "Bonzomatic_W64_DX11.exe non trovato automaticamente. Per fare funzionare il Player, per favore, selezionalo manualmente.")
            return self.prompt_bonzomatic_path()
        except Exception as e:
            print(f"Errore durante il setup del percorso Bonzomatic: {e}"); traceback.print_exc(); return False

    def prompt_bonzomatic_path(self):
        """Chiede all'utente di selezionare manualmente l'eseguibile di Bonzomatic."""        
        try:
            path = filedialog.askopenfilename(title=f"Seleziona l'eseguibile di {self.BONZOMATIC_EXECUTABLE_NAME}", filetypes=[(self.BONZOMATIC_EXECUTABLE_NAME, self.BONZOMATIC_EXECUTABLE_NAME), ("Tutti gli eseguibili", "*.exe")])
            if path and os.path.isfile(path):
                filename = os.path.basename(path)
                if filename == self.BONZOMATIC_EXECUTABLE_NAME:
                    self.bonzomatic_path = path; self.bonzomatic_config["working_dir"] = os.path.dirname(path); print(f"✅ Bonzomatic selezionato manualmente: {filename}."); return True
                else: messagebox.showerror("Errore Selezione", f"Seleziona SOLO l'eseguibile {self.BONZOMATIC_EXECUTABLE_NAME}."); return False
            elif path: messagebox.showerror("Errore Selezione", "File non valido o non esistente."); return False
            print("Selezione manuale Bonzomatic annullata o non valida."); return False
        except Exception as e:
            print(f"Errore nel prompt di selezione percorso Bonzomatic: {e}"); traceback.print_exc(); return False
            
    def is_bonzomatic_running(self):
        """Verifica se il processo di Bonzomatic è attualmente in esecuzione."""
        if self.bonzomatic_process is None: return False
        try: return self.bonzomatic_process.poll() is None
        except Exception as e: print(f"Errore durante la verifica dello stato del processo Bonzomatic: {e}"); traceback.print_exc(); return False

    def get_bonzomatic_window_handle(self):
        """Ottiene l'handle della finestra di Bonzomatic (specifico per Windows)."""
        if not WIN32GUI_AVAILABLE: return None
        try:
            def enum_windows_callback(hwnd, windows_list):
                if win32gui.IsWindowVisible(hwnd):
                    window_text = win32gui.GetWindowText(hwnd)
                    if self.bonzomatic_config["window_title"].lower() in window_text.lower(): windows_list.append(hwnd)
                return True
            windows_found = []; win32gui.EnumWindows(enum_windows_callback, windows_found)
            if windows_found: print(f"Trovata finestra Bonzomatic con handle: {windows_found[0]}."); return windows_found[0]
            print("Finestra Bonzomatic non trovata."); return None
        except Exception as e:
            print(f"Errore durante la ricerca dell'handle della finestra di Bonzomatic: {e}"); traceback.print_exc(); return None

    def start_bonzomatic_process(self):
        """Avvia l'eseguibile di Bonzomatic come processo separato."""
        try:
            if not self.bonzomatic_path:
                if not self.setup_bonzomatic_path():
                    messagebox.showerror("Avvio Bonzomatic", f"Eseguibile Bonzomatic ({self.BONZOMATIC_EXECUTABLE_NAME}) non trovato o non selezionato. Impossibile avviare."); return False
            if self.is_bonzomatic_running():
                print("Bonzomatic è già in esecuzione."); self.root.after(0, self.on_bonzomatic_started); return True

            cmd_args = [self.bonzomatic_path] + self.bonzomatic_config["arguments"]
            working_dir = self.bonzomatic_config["working_dir"] or os.path.dirname(self.bonzomatic_path)
            print(f"Avvio Bonzomatic: Comando='{' '.join(cmd_args)}', Working Dir='{working_dir}'")
            
            self.bonzomatic_process = subprocess.Popen(cmd_args, cwd=working_dir, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=self.SUBPROCESS_CREATE_NO_WINDOW_FLAG)
            print(f"Processo Bonzomatic avviato con PID: {self.bonzomatic_process.pid}.")
            self.wait_for_bonzomatic_window()
            return True
        except FileNotFoundError as e:
            messagebox.showerror("Errore Avvio", f"Impossibile avviare Bonzomatic: file non trovato.\n{e}"); print(f"Errore File non trovato durante avvio Bonzomatic: {e}"); traceback.print_exc(); return False
        except Exception as e:
            messagebox.showerror("Errore Avvio", f"Errore generico durante l'avvio di Bonzomatic: {e}"); print(f"Errore generico avvio Bonzomatic: {e}"); traceback.print_exc(); return False

    def wait_for_bonzomatic_window(self):
        """Attende che la finestra di Bonzomatic sia disponibile e ne recupera l'handle."""
        def wait_thread_task():
            try:
                timeout = self.BONZOMATIC_WINDOW_DETECT_TIMEOUT; start_time = time.time(); handle_found = None
                while time.time() - start_time < timeout:
                    if self.is_bonzomatic_running():
                        handle_found = self.get_bonzomatic_window_handle()
                        if handle_found:
                            self.bonzomatic_window_handle = handle_found; self.root.after(0, self.on_bonzomatic_started); print(f"Finestra Bonzomatic rilevata dopo {time.time() - start_time:.2f} secondi."); return
                    time.sleep(self.PROCESS_SCAN_SLEEP_SECONDS)
                self.root.after(0, self.on_bonzomatic_started)
                if not handle_found:
                    self.root.after(0, lambda: self.bonzo_status.configure(text="Stato: Avviato (finestra non rilevata o minimizzata).")); print("Avviso: Bonzomatic avviato ma handle finestra non rilevato entro il timeout.")
            except Exception as e: print(f"Errore critico nel thread di attesa finestra Bonzomatic: {e}"); traceback.print_exc()
        threading.Thread(target=wait_thread_task, daemon=True).start()
        
    def stop_bonzomatic_process(self):
        """Ferma il processo di Bonzomatic, prima in modo grazioso, poi forzatamente."""
        try:
            if not self.is_bonzomatic_running():
                print("Bonzomatic non è in esecuzione, nessuna azione necessaria per fermarlo."); self.root.after(0, self.on_bonzomatic_stopped); return True
            print("Tentativo di fermare Bonzomatic...")
            if WIN32GUI_AVAILABLE and self.bonzomatic_window_handle:
                try:
                    win32gui.PostMessage(self.bonzomatic_window_handle, 0x0010, 0, 0); print("Inviato messaggio WM_CLOSE alla finestra Bonzomatic.")
                    for _ in range(int(self.BONZOMATIC_STOP_GRACEFUL_WAIT_SECONDS * 10)):
                        if not self.is_bonzomatic_running(): print("Bonzomatic terminato graziosamente."); break
                        time.sleep(0.1)
                except Exception as e: print(f"Errore durante il tentativo di chiusura graziosa di Bonzomatic: {e}"); traceback.print_exc()
            if self.is_bonzomatic_running():
                print("Bonzomatic non ha terminato graziosamente. Tentativo di terminazione forzata...")
                self.bonzomatic_process.terminate()
                try:
                    self.bonzomatic_process.wait(timeout=self.BONZOMATIC_TERMINATE_TIMEOUT); print("Bonzomatic terminato forzatamente.")
                except subprocess.TimeoutExpired:
                    print("Timeout per la terminazione forzata. Tentativo di kill..."); self.bonzomatic_process.kill(); self.bonzomatic_process.wait(); print("Bonzomatic killato.")
            self.bonzomatic_process = None; self.bonzomatic_window_handle = None; self.root.after(0, self.on_bonzomatic_stopped)
            print("Processo Bonzomatic fermato e risorse liberate."); return True
        except Exception as e:
            messagebox.showerror("Errore", f"Errore durante l'arresto di Bonzomatic: {e}"); print(f"Errore critico durante l'arresto di Bonzomatic: {e}"); traceback.print_exc(); return False

    def show_bonzomatic_window(self):
        """Porta la finestra di Bonzomatic in primo piano."""
        if not self.is_bonzomatic_running(): messagebox.showwarning("Avviso", "Bonzomatic non è in esecuzione."); return
        if WIN32GUI_AVAILABLE and self.bonzomatic_window_handle:
            try: win32gui.ShowWindow(self.bonzomatic_window_handle, 1); win32gui.SetForegroundWindow(self.bonzomatic_window_handle); print("Finestra Bonzomatic portata in primo piano.")
            except Exception as e: messagebox.showinfo("Info", f"Impossibile mostrare finestra Bonzomatic: {e}"); print(f"Errore mostrando finestra Bonzomatic: {e}"); traceback.print_exc()
        else: messagebox.showinfo("Info", "Funzione 'Mostra Finestra' non supportata o Bonzomatic non avviato/finestra non trovata.")

    def monitor_bonzomatic_process(self):
        """Monitora lo stato del processo Bonzomatic per rilevare terminazioni inaspettate."""
        self.bonzomatic_monitor_active = True
        def monitor_thread_task():
            try:
                while self.bonzomatic_monitor_active:
                    if self.bonzomatic_process and not self.is_bonzomatic_running():
                        self.bonzomatic_monitor_active = False; self.root.after(0, self.on_bonzomatic_crashed); print("Bonzomatic terminato inaspettatamente."); break
                    time.sleep(self.BONZOMATIC_MONITOR_INTERVAL_SECONDS)
            except Exception as e: print(f"Errore nel thread di monitoraggio Bonzomatic: {e}"); traceback.print_exc()
        if self.is_bonzomatic_running(): threading.Thread(target=monitor_thread_task, daemon=True).start()

    # --- CALLBACK UI BONZOMATIC ---
    def on_bonzomatic_started(self):
        """Callback quando Bonzomatic si avvia con successo."""
        try:
            self.bonzo_start_btn.configure(state="disabled"); self.bonzo_stop_btn.configure(state="normal"); self.bonzo_show_btn.configure(state="normal")
            self.bonzo_status.configure(text="Stato: In esecuzione ✓"); self.monitor_bonzomatic_process(); print("UI Bonzomatic aggiornata: Avviato.")
        except Exception as e: print(f"Errore nella callback 'Bonzomatic avviato': {e}"); traceback.print_exc()

    def on_bonzomatic_stopped(self):
        """Callback quando Bonzomatic si ferma."""
        try:
            self.bonzomatic_monitor_active = False; self.bonzo_start_btn.configure(state="normal"); self.bonzo_stop_btn.configure(state="disabled"); self.bonzo_show_btn.configure(state="disabled")
            self.bonzo_status.configure(text="Stato: Fermato."); print("UI Bonzomatic aggiornata: Fermato.")
        except Exception as e: print(f"Errore nella callback 'Bonzomatic fermato': {e}"); traceback.print_exc()

    def on_bonzomatic_crashed(self):
        """Callback quando Bonzomatic termina inaspettatamente."""
        try:
            self.bonzomatic_monitor_active = False; self.bonzo_start_btn.configure(state="normal"); self.bonzo_stop_btn.configure(state="disabled"); self.bonzo_show_btn.configure(state="disabled")
            self.bonzo_status.configure(text="Stato: Terminato inaspettatamente ⚠️"); self.bonzomatic_process = None; self.bonzomatic_window_handle = None
            messagebox.showwarning("Bonzomatic", "Bonzomatic è terminato inaspettatamente! Controlla il terminale per errori."); print("UI Bonzomatic aggiornata: Crash rilevato.")
        except Exception as e: print(f"Errore nella callback 'Bonzomatic crashato': {e}"); traceback.print_exc()

    # --- METODI PER GLI EFFETTI VIDEO ---
    def update_zoom(self, value):
        """Aggiorna il fattore di zoom e il label associato."""
        self.effect_zoom = float(value); self.zoom_label.configure(text=f"{self.effect_zoom:.2f}")
        self.write_bonzomatic_params() # Scrive i parametri aggiornati

    def update_pan_x(self, value):
        """Aggiorna il fattore di Pan X e il label associato."""
        self.effect_pan_x = float(value); self.pan_x_label.configure(text=f"{self.effect_pan_x:.2f}")
        self.write_bonzomatic_params()

    def update_pan_y(self, value):
        """Aggiorna il fattore di Pan Y e il label associato."""
        self.effect_pan_y = float(value); self.pan_y_label.configure(text=f"{self.effect_pan_y:.2f}")
        self.write_bonzomatic_params()

    def update_rotation(self, value):
        """Aggiorna il fattore di Rotazione e il label associato."""
        self.effect_rotation = float(value); self.rotation_label.configure(text=f"{self.effect_rotation:.0f}°")
        self.write_bonzomatic_params()

    def update_distortion(self, value):
        """Aggiorna il fattore di Distorsione e il label associato."""
        self.effect_distortion = float(value); self.distortion_label.configure(text=f"{self.effect_distortion:.2f}")
        self.write_bonzomatic_params()

    def toggle_audio_zoom_effect(self):
        """Attiva/disattiva la modulazione dello zoom basata sull'audio."""
        self.audio_zoom_enabled = not self.audio_zoom_enabled
        if self.audio_zoom_enabled:
            print("Modulazione Zoom tramite Audio (Beat/Bassi) abilitata.")
            if not self.audio_recording and AUDIO_AVAILABLE: self.start_audio_capture()
        else:
            print("Modulazione Zoom tramite Audio disabilitata.")
            self.root.after(0, lambda: self.zoom_slider.set(self.EFFECTS_ZOOM_DEFAULT))
        self.write_bonzomatic_params() # Scrive i parametri aggiornati

    def write_bonzomatic_params(self):
        """Scrive i parametri degli effetti e dell'audio in un file JSON per Bonzomatic."""
        try:
            if not self.bonzomatic_path: return

            params_filepath = os.path.join(self.bonzomatic_config["working_dir"], self.BONZOMATIC_PARAMS_FILENAME)
            
            audio_params = {
                "bpm": self.current_bpm, "beat_detected": self.beat_detected,
                "audio_level": self.audio_level, "bass_level": self.bass_level,
                "fFreq1": float(self.frequency_data[0]) if self.frequency_data and len(self.frequency_data) >= 4 else 0.0,
                "fFreq2": float(self.frequency_data[1]) if self.frequency_data and len(self.frequency_data) >= 4 else 0.0,
                "fFreq3": float(self.frequency_data[2]) if self.frequency_data and len(self.frequency_data) >= 4 else 0.0,
                "fFreq4": float(self.frequency_data[3]) if self.frequency_data and len(self.frequency_data) >= 4 else 0.0,
            }

            current_zoom = self.effect_zoom
            if self.audio_zoom_enabled:
                if self.beat_detected:
                    current_zoom = self.EFFECTS_ZOOM_DEFAULT + (self.audio_level * (self.EFFECTS_ZOOM_MAX - self.EFFECTS_ZOOM_DEFAULT) / 0.5) # Esempio semplice
                    current_zoom = max(self.EFFECTS_ZOOM_MIN, min(self.EFFECTS_ZOOM_MAX, current_zoom))
                elif self.bass_response_enabled and self.bass_level > self.BASS_LEVEL_EFFECT_THRESHOLD:
                    current_zoom = self.EFFECTS_ZOOM_DEFAULT + (self.bass_level * (self.EFFECTS_ZOOM_MAX - self.EFFECTS_ZOOM_DEFAULT) / self.BASS_LEVEL_EFFECT_THRESHOLD * 2) # Amplifica l'effetto basso
                    current_zoom = max(self.EFFECTS_ZOOM_MIN, min(self.EFFECTS_ZOOM_MAX, current_zoom))

            effect_params = {
                "zoom": current_zoom, "pan_x": self.effect_pan_x, "pan_y": self.effect_pan_y,
                "rotation": self.effect_rotation, "distortion": self.effect_distortion
            }

            all_params = {"audio": audio_params, "effects": effect_params}
            
            with open(params_filepath, 'w', encoding='utf-8') as f: json.dump(all_params, f, indent=4)
            
        except Exception as e:
            print(f"Errore durante la scrittura dei parametri di Bonzomatic: {e}"); traceback.print_exc()

    # --- METODI GENERALI DELL'APP ---
    def update_scale(self, value):
        """Aggiorna il fattore di scala globale della finestra."""
        try:
            self.scale_factor = value; percentage = int(value * 100); self.scale_label.configure(text=f"{percentage}%")
            new_width = int(self.DEFAULT_APP_WIDTH * value); new_height = int(self.DEFAULT_APP_HEIGHT * value)
            self.root.geometry(f"{new_width}x{new_height}"); print(f"Finestra ridimensionata a {new_width}x{new_height} ({percentage}%).")
        except Exception as e: print(f"Errore durante l'aggiornamento della scala della finestra: {e}"); traceback.print_exc()

    def setup_resize_handle(self):
        """Configura l'handle di ridimensionamento nell'angolo in basso a destra della finestra principale."""
        handle_size = self.RESIZE_HANDLE_SIZE
        self.resize_handle = ctk.CTkFrame(self.root, width=handle_size, height=handle_size, corner_radius=0)
        self.resize_handle.place(relx=1.0, rely=1.0, anchor="se")
        self.resize_handle.bind("<Button-1>", self.start_resize); self.resize_handle.bind("<B1-Motion>", self.do_resize)
        self.root.bind("<Configure>", self.update_resize_handle_position)
        
    def update_resize_handle_position(self, event=None):
        """Aggiorna la posizione dell'handle di ridimensionamento dopo un evento di configurazione della finestra."""
        try:
            if hasattr(self, 'resize_handle'): self.resize_handle.place(relx=1.0, rely=1.0, anchor="se")
        except Exception as e: print(f"Errore durante l'aggiornamento della posizione dell'handle di ridimensionamento: {e}"); traceback.print_exc()
            
    def start_resize(self, event):
        """Inizia l'operazione di ridimensionamento della finestra dal handle."""
        try:
            self.start_x = event.x_root; self.start_y = event.y_root
            self.start_width = self.root.winfo_width(); self.start_height = self.root.winfo_height()
        except Exception as e: print(f"Errore in start_resize: {e}"); traceback.print_exc()
            
    def do_resize(self, event):
        """Esegue il ridimensionamento della finestra durante il trascinamento del handle."""
        try:
            delta_x = event.x_root - self.start_x; delta_y = event.y_root - self.start_y
            new_width = max(self.MIN_APP_WIDTH, self.start_width + delta_x); new_height = max(self.MIN_APP_HEIGHT, self.start_height + delta_y)
            self.root.geometry(f"{new_width}x{new_height}")
        except Exception as e: print(f"Errore in do_resize: {e}"); traceback.print_exc()

    def setup_vmix_output(self):
        """Configura gli attributi della finestra principale per l'ottimizzazione con VMix (minimal)."""
        try:
            if not self.root or not self.root.winfo_exists():
                print("Avviso: self.root non è inizializzato o non esiste più in setup_vmix_output. Ignoro le impostazioni VMix."); return False
            if self.vmix_config["window_always_on_top"]:
                try: self.root.attributes('-topmost', True); print("Impostato: finestra 'sempre in primo piano'.")
                except tk.TclError as e: print(f"ATTENZIONE: Impossibile impostare 'always_on_top': {e}. La funzionalità potrebbe non essere supportata dal tuo ambiente."); traceback.print_exc()
            if self.vmix_config["transparent_background"]:
                try: self.root.attributes('-alpha', 0.95); print("Impostato: trasparenza (-alpha 0.95).")
                except tk.TclError as e: print(f"ATTENZIONE: Impossibile impostare 'trasparenza' (-alpha): {e}. La funzionalità potrebbe non essere supportata dal tuo ambiente."); traceback.print_exc()
            print("Setup VMix output completato."); return True
        except Exception as e: print(f"Errore durante il setup di VMix: {e}"); traceback.print_exc(); return False
            
    def optimize_performance(self):
        """Placeholder per future ottimizzazioni delle performance (non implementato in questa versione leggera)."""
        pass
            
    def integrate_all_systems(self):
        """Coordina l'integrazione e la sincronizzazione tra i vari sistemi attivi (audio, Bonzomatic)."""
        try:
            systems_active = 0
            if self.is_bonzomatic_running(): systems_active += 1
            if self.audio_recording: systems_active += 1
            if systems_active >= self.MIN_SYSTEMS_FOR_INTEGRATION: print(f"Integrazione base attiva: {systems_active} sistemi rilevati."); self.setup_vmix_output()
            else: print(f"Integrazione base disabilitata: solo {systems_active} sistemi attivi (richiesti {self.MIN_SYSTEMS_FOR_INTEGRATION}).")
        except Exception as e: print(f"Errore durante l'integrazione dei sistemi: {e}"); traceback.print_exc()
        
    def on_closing(self):
        """Gestisce la chiusura dell'applicazione, fermando tutti i processi in background."""
        try:
            print("Chiusura dell'applicazione. Terminazione processi in background...")
            if self.bonzomatic_process: self.stop_bonzomatic_process()
            self.stop_audio_capture()
            if hasattr(self, 'browser_driver') and self.browser_driver:
                try: self.browser_driver.quit(); print("Driver browser chiuso durante la chiusura dell'app.")
                except Exception as e: print(f"Errore durante la chiusura del browser driver in on_closing: {e}"); traceback.print_exc()
            if hasattr(self, 'file_manager_config') and self.file_manager_config.get('cache_enabled', False): self.save_shader_cache()
            self.root.destroy(); print("Applicazione chiusa con successo.")
        except Exception as e: print(f"Errore durante la chiusura dell'applicazione: {e}"); traceback.print_exc()