import cv2
import tkinter as tk
from tkinter import filedialog, ttk, messagebox
from PIL import Image, ImageTk, ImageDraw
import numpy as np
import threading
import time
import json
import os
from math import cos, sin, pi, sqrt, radians, atan2
import serial
import serial.tools.list_ports

# Configuración inicial
CONFIG_FILE = "color_app_config.json"

# Intentar importar pymodbus
try:
    from pymodbus.client import ModbusTcpClient
    MODBUS_AVAILABLE = True
except ImportError:
    MODBUS_AVAILABLE = False
    print("  pymodbus no está instalado. Ejecuta: pip install pymodbus")

# Intentar importar pyserial
try:
    import serial
    SERIAL_AVAILABLE = True
except ImportError:
    SERIAL_AVAILABLE = False
    print("  pyserial no está instalado. Ejecuta: pip install pyserial")

# COMUNICACIÓN CON PLC (MODBUS TCP o SERIAL)
class PLCManager:
    def __init__(self, connection_type='none', ip='192.168.0.10', port=502, serial_port=None, baudrate=9600):
        self.connection_type = connection_type
        self.ip = ip
        self.port = port
        self.serial_port = serial_port
        self.baudrate = baudrate
        self.last_send_time = 0
        self.min_interval = 0.1  # Mínimo 100ms entre envíos
        self.enabled = False
        self.serial_connection = None
        
        # Configurar según tipo de conexión
        if connection_type == 'modbus':
            self.enabled = MODBUS_AVAILABLE
        elif connection_type == 'serial':
            self.enabled = SERIAL_AVAILABLE
            self.initialize_serial()
            
    def initialize_serial(self):
        """Inicializar conexión serial"""
        if not SERIAL_AVAILABLE or not self.serial_port:
            return
            
        try:
            self.serial_connection = serial.Serial(
                port=self.serial_port,
                baudrate=self.baudrate,
                timeout=1
            )
            print(f"✅ Conexión serial establecida en {self.serial_port}")
        except Exception as e:
            print(f"🛑 Error al conectar serial: {e}")
            self.serial_connection = None
            
    def enviar_a_plc(self, c, m, y, k, w):
        if not self.enabled:
            return False
            
        # Evitar spam de envíos
        current_time = time.time()
        if current_time - self.last_send_time < self.min_interval:
            return False
            
        self.last_send_time = current_time
        
        # Enviar en hilo separado para no bloquear la GUI
        threading.Thread(
            target=self._enviar_async, 
            args=(c, m, y, k, w),
            daemon=True
        ).start()
        
    def _enviar_async(self, c, m, y, k, w):
        """Enviar datos según el tipo de conexión"""
        if self.connection_type == 'modbus':
            self._enviar_modbus(c, m, y, k, w)
        elif self.connection_type == 'serial':
            self._enviar_serial(c, m, y, k, w)
            
    def _enviar_modbus(self, c, m, y, k, w):
        """Enviar datos via Modbus TCP"""
        try:
            client = ModbusTcpClient(self.ip, port=self.port)
            if client.connect():
                valores = [c, m, y, k, w]
                resultado = client.write_registers(0, valores)
                if resultado.isError():
                    print("❌ Error al escribir en el PLC")
                else:
                    print(f"✅ CMYKW enviado al PLC (Modbus): {valores}")
                client.close()
            else:
                print("🚫 No se pudo conectar al PLC (Modbus)")
        except Exception as e:
            print(f"🛑 Error de comunicación PLC (Modbus): {e}")
            
    def _enviar_serial(self, c, m, y, k, w):
        """Enviar datos via Serial"""
        if not self.serial_connection:
            print("🚫 No hay conexión serial establecida")
            return
            
        try:
            # Formato: "C:xxx M:xxx Y:xxx K:xxx W:xxx\n"
            data_str = f"C:{c:03d} M:{m:03d} Y:{y:03d} K:{k:03d} W:{w:03d}\n"
            self.serial_connection.write(data_str.encode('ascii'))
            print(f"✅ CMYKW enviado por Serial: {data_str.strip()}")
        except Exception as e:
            print(f"🛑 Error de comunicación Serial: {e}")
            
    def close(self):
        """Cerrar conexiones"""
        if self.serial_connection and self.serial_connection.is_open:
            self.serial_connection.close()

# ---------- FUNCIONES DE CONVERSIÓN ----------
def rgb_to_cmykw(r, g, b):
    """Convierte RGB a CMYKW"""
    if r == 255 and g == 255 and b == 255:
        return 0, 0, 0, 0, 100  # Solo blanco
    if (r, g, b) == (0, 0, 0):
        return 0, 0, 0, 100, 0  # Solo negro
    
    c = 1 - r / 255
    m = 1 - g / 255
    y = 1 - b / 255
    k = min(c, m, y)
    
    if k < 1:
        c = (c - k) / (1 - k)
        m = (m - k) / (1 - k)
        y = (y - k) / (1 - k)
    else:
        c = m = y = 0
    
    return round(c * 100), round(m * 100), round(y * 100), round(k * 100), 0

def cmykw_to_rgb(c, m, y, k, w):
    """Convierte CMYKW a RGB"""
    if w > 0:
        return 255, 255, 255
    
    c /= 100
    m /= 100
    y /= 100
    k /= 100
    
    r = round(255 * (1 - c) * (1 - k))
    g = round(255 * (1 - m) * (1 - k))
    b = round(255 * (1 - y) * (1 - k))
    
    return max(0, min(255, r)), max(0, min(255, g)), max(0, min(255, b))

def rgb_to_hsl(r, g, b):
    """Convierte RGB a HSL"""
    r, g, b = r/255.0, g/255.0, b/255.0
    max_val = max(r, g, b)
    min_val = min(r, g, b)
    
    # Luminosidad
    l = (max_val + min_val) / 2.0
    
    if max_val == min_val:
        h = s = 0.0
    else:
        # Saturación
        if l <= 0.5:
            s = (max_val - min_val) / (max_val + min_val)
        else:
            s = (max_val - min_val) / (2.0 - max_val - min_val)
        
        # Matiz
        delta = max_val - min_val
        if max_val == r:
            h = (g - b) / delta + (6.0 if g < b else 0.0)
        elif max_val == g:
            h = (b - r) / delta + 2.0
        else:
            h = (r - g) / delta + 4.0
        h /= 6.0
    
    return h * 360, s * 100, l * 100

def hsl_to_rgb(h, s, l):
    """Convierte HSL a RGB"""
    h, s, l = h/360.0, s/100.0, l/100.0
    
    if s == 0:
        r = g = b = l
    else:
        def hue_to_rgb(p, q, t):
            if t < 0: t += 1
            if t > 1: t -= 1
            if t < 1/6: return p + (q - p) * 6 * t
            if t < 1/2: return q
            if t < 2/3: return p + (q - p) * (2/3 - t) * 6
            return p
        
        q = l * (1 + s) if l < 0.5 else l + s - l * s
        p = 2 * l - q
        
        r = hue_to_rgb(p, q, h + 1/3)
        g = hue_to_rgb(p, q, h)
        b = hue_to_rgb(p, q, h - 1/3)
    
    return round(r * 255), round(g * 255), round(b * 255)

# ---------- APLICACIÓN GUI ----------
class ColorConverterApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Sensor de Color Avanzado")
        self.root.geometry("1200x800")
        self.load_config()
        
        # Variables
        self.image = None
        self.camera_frame = None
        self.cap = None
        self.running_camera = False
        self.updating_sliders = False
        self.dark_mode = self.config.get('dark_mode', False)
        self.history = []
        self.max_history = 10
        
        # Inicializar PLC
        self.plc = PLCManager(
            connection_type=self.config.get('connection_type', 'none'),
            ip=self.config.get('plc_ip', '192.168.0.10'),
            port=self.config.get('plc_port', 502),
            serial_port=self.config.get('serial_port'),
            baudrate=self.config.get('baudrate', 9600)
        )
        
        # Paleta de colores predefinidos
        self.color_palettes = {
            'Básicos': [
                ('Rojo', (255, 0, 0)),
                ('Verde', (0, 255, 0)),
                ('Azul', (0, 0, 255)),
                ('Amarillo', (255, 255, 0)),
                ('Cian', (0, 255, 255)),
                ('Magenta', (255, 0, 255)),
                ('Blanco', (255, 255, 255)),
                ('Negro', (0, 0, 0))
            ],
            'Materiales': [
                ('Oro', (212, 175, 55)),
                ('Plata', (192, 192, 192)),
                ('Bronce', (205, 127, 50)),
                ('Cobre', (184, 115, 51)),
                ('Acero', (168, 169, 173))
            ]
        }
        
        # Crear interfaz
        self.setup_styles()
        self.create_widgets()
        self.update_color_preview()
        
        # Cargar historial si existe
        if os.path.exists('color_history.json'):
            try:
                with open('color_history.json', 'r') as f:
                    self.history = json.load(f)
                    self.update_history_ui()
            except:
                self.history = []

    def load_config(self):
        """Cargar configuración desde archivo"""
        self.config = {}
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r') as f:
                    self.config = json.load(f)
            except:
                pass

    def save_config(self):
        """Guardar configuración en archivo"""
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f)
        except:
            pass

    def setup_styles(self):
        """Configurar estilos según modo oscuro/claro"""
        self.style = ttk.Style()
        self.style.theme_use('clam')
        
        bg_color = '#333333' if self.dark_mode else '#f0f0f0'
        fg_color = '#ffffff' if self.dark_mode else '#000000'
        entry_bg = '#555555' if self.dark_mode else '#ffffff'
        entry_fg = '#ffffff' if self.dark_mode else '#000000'
        
        self.root.configure(bg=bg_color)
        
        self.style.configure('.', background=bg_color, foreground=fg_color)
        self.style.configure('Title.TLabel', font=('Arial', 12, 'bold'))
        self.style.configure('Header.TLabel', font=('Arial', 10, 'bold'))
        self.style.configure('Info.TLabel', font=('Arial', 9))
        self.style.configure('TFrame', background=bg_color)
        self.style.configure('TLabelFrame', background=bg_color)
        self.style.configure('TEntry', fieldbackground=entry_bg, foreground=entry_fg)
        self.style.configure('TButton', padding=5)

    def create_widgets(self):
        """Crear widgets de la interfaz"""
        # Frame principal
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # Configurar expansión
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
        # Barra de menú
        self.create_menu_bar()
        
        # Título
        title_label = ttk.Label(main_frame, text="Sensor de Color Avanzado", 
                               style='Title.TLabel')
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 15))
        
        # Estado del PLC
        connection_status = "🔴 Sin conexión"
        if self.plc.connection_type == 'modbus' and MODBUS_AVAILABLE:
            connection_status = f"🟢 Modbus TCP - {self.plc.ip}:{self.plc.port}"
        elif self.plc.connection_type == 'serial' and SERIAL_AVAILABLE and self.plc.serial_connection:
            connection_status = f"🟢 Serial - {self.plc.serial_port} @ {self.plc.baudrate} baud"
        
        self.plc_status_label = ttk.Label(main_frame, text=connection_status, style='Info.TLabel')
        self.plc_status_label.grid(row=0, column=1, sticky='e', pady=(0, 15))
        
        # Frame izquierdo: Imagen y controles
        left_frame = ttk.LabelFrame(main_frame, text="Imagen y Captura", padding="10")
        left_frame.grid(row=1, column=0, sticky="nsew", padx=(0, 10))
        left_frame.columnconfigure(0, weight=1)
        left_frame.columnconfigure(1, weight=1)
        left_frame.columnconfigure(2, weight=1)
        
        # Canvas para imagen
        self.canvas = tk.Canvas(left_frame, width=450, height=350, bg='white', 
                               relief='sunken', borderwidth=2, cursor="cross")
        self.canvas.grid(row=0, column=0, columnspan=3, pady=(0, 10))
        self.canvas.bind("<Button-1>", self.pick_color)
        
        # Instrucciones
        instruction_label = ttk.Label(left_frame, text="Haz clic en la imagen para seleccionar un color",
                                     style='Info.TLabel')
        instruction_label.grid(row=1, column=0, columnspan=3, pady=(0, 10))
        
        # Botones de control
        self.btn_load = ttk.Button(left_frame, text="📁 Cargar Imagen", command=self.load_image)
        self.btn_load.grid(row=2, column=0, padx=(0, 5), pady=5, sticky="ew")
        
        self.btn_camera = ttk.Button(left_frame, text="📷 Iniciar Cámara", command=self.toggle_camera)
        self.btn_camera.grid(row=2, column=1, padx=5, pady=5, sticky="ew")
        
        self.btn_snapshot = ttk.Button(left_frame, text="📸 Tomar Foto", command=self.snapshot)
        self.btn_snapshot.grid(row=2, column=2, padx=(5, 0), pady=5, sticky="ew")
        
        # Selector HSL
        hsl_frame = ttk.LabelFrame(left_frame, text="Selector HSL", padding="10")
        hsl_frame.grid(row=3, column=0, columnspan=3, sticky="ew", pady=(10, 0))
        
        # Círculo cromático
        self.hue_circle = tk.Canvas(hsl_frame, width=200, height=200, bg='white')
        self.hue_circle.grid(row=0, column=0, rowspan=3, padx=(0, 10))
        self.draw_hue_circle()
        self.hue_circle.bind("<B1-Motion>", self.pick_hue)
        self.hue_circle.bind("<Button-1>", self.pick_hue)
        
        # Sliders HSL
        self.hsl_sliders = {}
        for i, (name, letter) in enumerate(zip(['Matiz', 'Saturación', 'Luminosidad'], ['H', 'S', 'L'])):
            frame = ttk.Frame(hsl_frame)
            frame.grid(row=i, column=1, sticky='ew', pady=2)
            
            ttk.Label(frame, text=f"{name}:").pack(side='left')
            slider = tk.Scale(frame, from_=0, to=100 if letter != 'H' else 360, 
                            orient="horizontal", command=lambda v, l=letter: self.on_hsl_change(l, v))
            slider.pack(side='left', fill='x', expand=True)
            label = ttk.Label(frame, text="0", width=4)
            label.pack(side='left', padx=5)
            
            self.hsl_sliders[letter] = {
                'slider': slider,
                'label': label
            }
        
        # Frame derecho: Control de color
        right_frame = ttk.LabelFrame(main_frame, text="Control de Color", padding="10")
        right_frame.grid(row=1, column=1, sticky="nsew")
        right_frame.columnconfigure(1, weight=1)
        
        # Previsualización del color
        preview_frame = ttk.Frame(right_frame)
        preview_frame.grid(row=0, column=0, columnspan=3, pady=(0, 15))
        
        ttk.Label(preview_frame, text="Color Seleccionado:", style='Header.TLabel').pack()
        self.color_preview = tk.Label(preview_frame, text="", bg="white", width=20, height=3,
                                     relief='ridge', borderwidth=2)
        self.color_preview.pack(pady=5)
        
        # Sliders CMYKW
        self.sliders = {}
        colors = [
            ('C', 'Cyan', '#00FFFF'),
            ('M', 'Magenta', '#FF00FF'),
            ('Y', 'Yellow', '#FFFF00'),
            ('K', 'Black', '#000000'),
            ('W', 'White', '#FFFFFF')
        ]
        
        for idx, (letter, name, color) in enumerate(colors):
            # Frame para cada slider
            slider_frame = ttk.Frame(right_frame)
            slider_frame.grid(row=idx + 1, column=0, columnspan=3, sticky='ew', pady=3)
            slider_frame.columnconfigure(2, weight=1)
            
            # Indicador de color
            color_indicator = tk.Label(slider_frame, bg=color, width=3, height=1, relief='solid')
            color_indicator.grid(row=0, column=0, padx=(0, 5))
            
            # Etiqueta
            label = ttk.Label(slider_frame, text=f"{name} ({letter}):", width=12)
            label.grid(row=0, column=1, sticky='w', padx=(0, 5))
            
            # Slider
            slider = tk.Scale(slider_frame, from_=0, to=100, orient="horizontal",
                            command=lambda val, c=letter: self.on_slider_change(c, val))
            slider.grid(row=0, column=2, sticky='ew', padx=(0, 5))
            
            # Valor
            value_label = ttk.Label(slider_frame, text="0%", width=5)
            value_label.grid(row=0, column=3)
            
            self.sliders[letter] = {'slider': slider, 'label': value_label}
        
        # Paleta de colores
        palette_frame = ttk.LabelFrame(right_frame, text="Paletas de Color", padding="10")
        palette_frame.grid(row=6, column=0, columnspan=3, sticky='ew', pady=(10, 0))
        
        self.palette_selector = ttk.Combobox(palette_frame, values=list(self.color_palettes.keys()))
        self.palette_selector.current(0)
        self.palette_selector.pack(fill='x')
        self.palette_selector.bind("<<ComboboxSelected>>", self.update_palette_colors)
        
        self.palette_colors_frame = ttk.Frame(palette_frame)
        self.palette_colors_frame.pack(fill='x', pady=(5, 0))
        self.update_palette_colors()
        
        # Historial de colores
        history_frame = ttk.LabelFrame(right_frame, text="Historial de Colores", padding="10")
        history_frame.grid(row=7, column=0, columnspan=3, sticky='ew', pady=(10, 0))
        
        self.history_frame = ttk.Frame(history_frame)
        self.history_frame.pack(fill='x')
        self.update_history_ui()
        
        # Información de valores
        info_frame = ttk.LabelFrame(right_frame, text="Valores Actuales", padding="10")
        info_frame.grid(row=8, column=0, columnspan=3, sticky='ew', pady=(10, 0))
        
        self.rgb_label = ttk.Label(info_frame, text="RGB: 255, 255, 255", style='Info.TLabel')
        self.rgb_label.grid(row=0, column=0, sticky='w', pady=2)
        
        self.cmykw_label = ttk.Label(info_frame, text="CMYKW: 0, 0, 0, 0, 100", style='Info.TLabel')
        self.cmykw_label.grid(row=1, column=0, sticky='w', pady=2)
        
        self.hsl_label = ttk.Label(info_frame, text="HSL: 0°, 0%, 100%", style='Info.TLabel')
        self.hsl_label.grid(row=2, column=0, sticky='w', pady=2)
        
        # Botones de acción
        action_frame = ttk.Frame(right_frame)
        action_frame.grid(row=9, column=0, columnspan=3, pady=(10, 0))
        
        ttk.Button(action_frame, text="🔄 Resetear", command=self.reset_values).pack(side='left', padx=(0, 5))
        ttk.Button(action_frame, text="📋 Copiar RGB", command=self.copy_rgb).pack(side='left', padx=5)
        ttk.Button(action_frame, text="📋 Copiar CMYKW", command=self.copy_cmykw).pack(side='left', padx=5)
        ttk.Button(action_frame, text="🔧 Config System", command=self.config_plc).pack(side='left', padx=5)
        ttk.Button(action_frame, text="🚀 Enviar Datos", command=self.send_to_plc).pack(side='left', padx=5)

    def create_menu_bar(self):
        """Crear barra de menú"""
        menubar = tk.Menu(self.root)
        
        # Menú Archivo
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Cargar Imagen", command=self.load_image)
        file_menu.add_command(label="Guardar Configuración", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="Salir", command=self.on_closing)
        menubar.add_cascade(label="Archivo", menu=file_menu)
        
        # Menú Vista
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(
            label="Modo Oscuro" if not self.dark_mode else "Modo Claro",
            command=self.toggle_dark_mode
        )
        menubar.add_cascade(label="Vista", menu=view_menu)
        
        self.root.config(menu=menubar)

    def draw_hue_circle(self):
        """Dibuja el círculo cromático HSL"""
        size = 200
        center = size // 2
        radius = size // 2 - 10
        
        # Crear imagen PIL
        img = Image.new("RGB", (size, size), "white")
        draw = ImageDraw.Draw(img)
        
        # Dibujar círculo cromático
        for y in range(size):
            for x in range(size):
                dx = x - center
                dy = y - center
                distance = sqrt(dx*dx + dy*dy)
                
                if distance <= radius:
                    angle = (180 + (180 / pi) * -atan2(dy, dx)) % 360
                    saturation = distance / radius
                    r, g, b = hsl_to_rgb(angle, saturation * 100, 50)
                    draw.point((x, y), fill=(r, g, b))
        
        # Convertir a PhotoImage y mostrar
        self.hue_circle_img = ImageTk.PhotoImage(img)
        self.hue_circle.create_image(0, 0, anchor="nw", image=self.hue_circle_img)
        
        # Dibujar marcador
        self.hue_marker = self.hue_circle.create_oval(
            center-5, center-5, center+5, center+5,
            outline="black", width=2, fill=""
        )

    def pick_hue(self, event):
        """Seleccionar matiz y saturación del círculo cromático"""
        size = 200
        center = size // 2
        radius = size // 2 - 10
        
        dx = event.x - center
        dy = event.y - center
        distance = sqrt(dx*dx + dy*dy)
        
        if distance <= radius:
            # Calcular HSL
            angle = (180 + (180 / pi) * -atan2(dy, dx)) % 360
            saturation = distance / radius * 100
            lightness = self.hsl_sliders['L']['slider'].get()
            
            # Actualizar controles
            self.updating_sliders = True
            self.hsl_sliders['H']['slider'].set(angle)
            self.hsl_sliders['S']['slider'].set(saturation)
            self.updating_sliders = False
            
            # Mover marcador
            self.hue_circle.coords(
                self.hue_marker,
                event.x-5, event.y-5,
                event.x+5, event.y+5
            )
            
            # Convertir a RGB y actualizar
            self.update_from_hsl()

    def on_hsl_change(self, channel, value):
        """Manejar cambios en los sliders HSL"""
        if self.updating_sliders:
            return
            
        # Actualizar etiqueta
        self.hsl_sliders[channel]['label'].config(text=str(round(float(value))))
        
        # Actualizar marcador en círculo cromático
        if channel == 'H' or channel == 'S':
            h = self.hsl_sliders['H']['slider'].get()
            s = self.hsl_sliders['S']['slider'].get() / 100.0
            size = 200
            center = size // 2
            radius = size // 2 - 10
            
            angle = radians(-h + 180)
            distance = s * radius
            
            x = center + distance * cos(angle)
            y = center + distance * sin(angle)
            
            self.hue_circle.coords(
                self.hue_marker,
                x-5, y-5,
                x+5, y+5
            )
        
        self.update_from_hsl()

    def update_from_hsl(self):
        """Actualizar todo desde valores HSL"""
        h = self.hsl_sliders['H']['slider'].get()
        s = self.hsl_sliders['S']['slider'].get()
        l = self.hsl_sliders['L']['slider'].get()
        
        # Convertir a RGB
        r, g, b = hsl_to_rgb(h, s, l)
        
        # Convertir a CMYKW
        c, m, y, k, w = rgb_to_cmykw(r, g, b)
        
        # Actualizar sliders CMYKW
        self.updating_sliders = True
        self.sliders['C']['slider'].set(c)
        self.sliders['M']['slider'].set(m)
        self.sliders['Y']['slider'].set(y)
        self.sliders['K']['slider'].set(k)
        self.sliders['W']['slider'].set(w)
        self.updating_sliders = False
        
        # Actualizar vista
        self.update_color_preview()

    def update_palette_colors(self, event=None):
        """Actualizar los colores mostrados en la paleta"""
        # Limpiar frame
        for widget in self.palette_colors_frame.winfo_children():
            widget.destroy()
        
        # Obtener paleta seleccionada
        palette_name = self.palette_selector.get()
        colors = self.color_palettes.get(palette_name, [])
        
        # Mostrar colores
        for name, (r, g, b) in colors:
            color_hex = f'#{r:02x}{g:02x}{b:02x}'
            btn = ttk.Button(
                self.palette_colors_frame,
                text=name,
                command=lambda r=r, g=g, b=b: self.set_color_from_rgb(r, g, b)
            )
            btn.pack(side='left', padx=2, pady=2, fill='x', expand=True)

    def set_color_from_rgb(self, r, g, b):
        """Establecer color desde valores RGB"""
        # Convertir a CMYKW
        c, m, y, k, w = rgb_to_cmykw(r, g, b)
        
        # Actualizar sliders
        self.updating_sliders = True
        self.sliders['C']['slider'].set(c)
        self.sliders['M']['slider'].set(m)
        self.sliders['Y']['slider'].set(y)
        self.sliders['K']['slider'].set(k)
        self.sliders['W']['slider'].set(w)
        self.updating_sliders = False
        
        # Actualizar HSL
        h, s, l = rgb_to_hsl(r, g, b)
        self.updating_sliders = True
        self.hsl_sliders['H']['slider'].set(h)
        self.hsl_sliders['S']['slider'].set(s)
        self.hsl_sliders['L']['slider'].set(l)
        self.updating_sliders = False
        
        # Actualizar vista
        self.update_color_preview()
        
        # Actualizar marcador en círculo cromático
        size = 200
        center = size // 2
        radius = size // 2 - 10
        
        angle = radians(-h + 180)
        distance = (s / 100.0) * radius
        
        x = center + distance * cos(angle)
        y = center + distance * sin(angle)
        
        self.hue_circle.coords(
            self.hue_marker,
            x-5, y-5,
            x+5, y+5
        )

    def update_history_ui(self):
        """Actualizar la interfaz del historial"""
        # Limpiar frame
        for widget in self.history_frame.winfo_children():
            widget.destroy()
        
        # Mostrar miniaturas
        for i, (rgb, _) in enumerate(self.history[-self.max_history:]):
            color_hex = f'#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}'
            btn = tk.Button(
                self.history_frame,
                bg=color_hex,
                width=3,
                height=1,
                relief='solid',
                command=lambda r=rgb: self.set_color_from_rgb(r[0], r[1], r[2])
            )
            btn.pack(side='left', padx=2, pady=2)

    def add_to_history(self, rgb, cmykw):
        """Agregar color al historial"""
        # Evitar duplicados
        if not any(h[0] == rgb for h in self.history):
            self.history.append((rgb, cmykw))
            
            # Mantener tamaño máximo
            if len(self.history) > self.max_history:
                self.history.pop(0)
            
            # Actualizar UI
            self.update_history_ui()
            
            # Guardar historial
            try:
                with open('color_history.json', 'w') as f:
                    json.dump(self.history, f)
            except:
                pass

    def toggle_dark_mode(self):
        """Cambiar entre modo oscuro y claro"""
        self.dark_mode = not self.dark_mode
        self.config['dark_mode'] = self.dark_mode
        self.save_config()
        
        # Reconfigurar estilos
        self.setup_styles()
        
        # Actualizar texto del menú
        self.create_menu_bar()
        
        # Redibujar círculo cromático
        self.draw_hue_circle()

    def load_image(self):
        """Cargar imagen desde archivo"""
        file_path = filedialog.askopenfilename(
            title="Seleccionar imagen",
            filetypes=[
                ("Imágenes", "*.jpg *.jpeg *.png *.bmp *.gif *.tiff"),
                ("Todos los archivos", "*.*")
            ]
        )
        
        if file_path:
            try:
                # Cargar imagen
                img = Image.open(file_path)
                
                # Redimensionar manteniendo proporción
                canvas_width = 450
                canvas_height = 350
                img.thumbnail((canvas_width, canvas_height), Image.Resampling.LANCZOS)
                
                # Convertir a formato compatible
                if img.mode != 'RGB':
                    img = img.convert('RGB')
                
                self.image = img
                self.display_image()
                
            except Exception as e:
                messagebox.showerror("Error", f"No se pudo cargar la imagen: {str(e)}")

    def display_image(self):
        """Mostrar imagen en el canvas"""
        if self.image:
            # Convertir a PhotoImage
            photo = ImageTk.PhotoImage(self.image)
            
            # Limpiar canvas
            self.canvas.delete("all")
            
            # Centrar imagen
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            img_width, img_height = self.image.size
            
            x = (canvas_width - img_width) // 2
            y = (canvas_height - img_height) // 2
            
            # Mostrar imagen
            self.canvas.create_image(x, y, anchor="nw", image=photo)
            self.canvas.image = photo  # Mantener referencia

    def toggle_camera(self):
        """Iniciar/detener cámara"""
        if not self.running_camera:
            self.start_camera()
        else:
            self.stop_camera()
            

    def start_camera(self):
        """Iniciar captura de cámara"""
        try:
            self.cap = cv2.VideoCapture(0)
            
            if not self.cap.isOpened():
                messagebox.showerror("Error", "No se pudo acceder a la cámara")
                return
            
            self.running_camera = True
            self.btn_camera.config(text="⏹️ Detener Cámara")
            self.update_camera_frame()
            
        except Exception as e:
            messagebox.showerror("Error", f"Error al iniciar cámara: {str(e)}")

    def stop_camera(self):
        """Detener captura de cámara"""
        self.running_camera = False
        if self.cap:
            self.cap.release()
            self.cap = None
        self.btn_camera.config(text="📷 Iniciar Cámara")

    def update_camera_frame(self):
        """Actualizar frame de cámara"""
        if self.running_camera and self.cap:
            ret, frame = self.cap.read()
            if ret:
                # Redimensionar frame
                frame = cv2.resize(frame, (450, 350))
                
                # Convertir BGR a RGB
                frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                
                # Convertir a PIL Image
                img = Image.fromarray(frame_rgb)
                self.camera_frame = img
                
                # Mostrar en canvas
                photo = ImageTk.PhotoImage(img)
                self.canvas.delete("all")
                self.canvas.create_image(0, 0, anchor="nw", image=photo)
                self.canvas.image = photo
                
                # Programar siguiente actualización
                self.root.after(30, self.update_camera_frame)

    def snapshot(self):
        """Tomar foto de la cámara"""
        if self.camera_frame:
            self.image = self.camera_frame.copy()
            self.stop_camera()
            self.display_image()

    def pick_color(self, event):
        """Seleccionar color de la imagen"""
        if self.image:
            # Obtener posición en la imagen
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()
            img_width, img_height = self.image.size
            
            # Calcular offset de la imagen centrada
            x_offset = (canvas_width - img_width) // 2
            y_offset = (canvas_height - img_height) // 2
            
            # Coordenadas en la imagen
            img_x = event.x - x_offset
            img_y = event.y - y_offset
            
            # Verificar que esté dentro de la imagen
            if 0 <= img_x < img_width and 0 <= img_y < img_height:
                # Obtener color del píxel
                r, g, b = self.image.getpixel((img_x, img_y))
                
                # Establecer color
                self.set_color_from_rgb(r, g, b)
                
                # Agregar al historial
                c, m, y, k, w = rgb_to_cmykw(r, g, b)
                self.add_to_history((r, g, b), (c, m, y, k, w))
        
        elif self.camera_frame:
            # Similar para frame de cámara
            r, g, b = self.camera_frame.getpixel((event.x, event.y))
            self.set_color_from_rgb(r, g, b)
            
            c, m, y, k, w = rgb_to_cmykw(r, g, b)
            self.add_to_history((r, g, b), (c, m, y, k, w))

    def on_slider_change(self, component, value):
        """Manejar cambios en los sliders CMYKW"""
        if self.updating_sliders:
            return
        
        # Actualizar etiqueta
        self.sliders[component]['label'].config(text=f"{value}%")
        
        # Obtener valores actuales
        c = self.sliders['C']['slider'].get()
        m = self.sliders['M']['slider'].get()
        y = self.sliders['Y']['slider'].get()
        k = self.sliders['K']['slider'].get()
        w = self.sliders['W']['slider'].get()
        
        # Convertir a RGB
        r, g, b = cmykw_to_rgb(c, m, y, k, w)
        
        # Actualizar HSL
        h, s, l = rgb_to_hsl(r, g, b)
        self.updating_sliders = True
        self.hsl_sliders['H']['slider'].set(h)
        self.hsl_sliders['S']['slider'].set(s)
        self.hsl_sliders['L']['slider'].set(l)
        self.updating_sliders = False
        
        # Actualizar marcador en círculo cromático
        size = 200
        center = size // 2
        radius = size // 2 - 10
        
        angle = radians(-h + 180)
        distance = (s / 100.0) * radius
        
        x = center + distance * cos(angle)
        y = center + distance * sin(angle)
        
        self.hue_circle.coords(
            self.hue_marker,
            x-5, y-5,
            x+5, y+5
        )
        
        # Actualizar vista
        self.update_color_preview()

    def send_to_plc(self):
        """Enviar valores actuales al PLC"""
        c = self.sliders['C']['slider'].get()
        m = self.sliders['M']['slider'].get()
        y = self.sliders['Y']['slider'].get()
        k = self.sliders['K']['slider'].get()
        w = self.sliders['W']['slider'].get()
        self.plc.enviar_a_plc(c, m, y, k, w)
        messagebox.showinfo("PLC", "Valores enviados al PLC.")

    def update_color_preview(self):
        """Actualizar previsualización del color"""
        # Obtener valores actuales
        c = self.sliders['C']['slider'].get()
        m = self.sliders['M']['slider'].get()
        y = self.sliders['Y']['slider'].get()
        k = self.sliders['K']['slider'].get()
        w = self.sliders['W']['slider'].get()
        
        # Actualizar etiquetas de valores
        for letter in ['C', 'M', 'Y', 'K', 'W']:
            value = self.sliders[letter]['slider'].get()
            self.sliders[letter]['label'].config(text=f"{value}%")
        
        # Actualizar etiquetas HSL
        for letter in ['H', 'S', 'L']:
            value = self.hsl_sliders[letter]['slider'].get()
            self.hsl_sliders[letter]['label'].config(text=str(round(value)))
        
        # Convertir a RGB
        r, g, b = cmykw_to_rgb(c, m, y, k, w)
        
        # Actualizar información
        self.rgb_label.config(text=f"RGB: {r}, {g}, {b}")
        self.cmykw_label.config(text=f"CMYKW: {c}, {m}, {y}, {k}, {w}")
        
        h, s, l = rgb_to_hsl(r, g, b)
        self.hsl_label.config(text=f"HSL: {h:.0f}°, {s:.0f}%, {l:.0f}%")
        
        # Actualizar previsualización
        color_hex = f'#{r:02x}{g:02x}{b:02x}'
        self.color_preview.config(bg=color_hex)
        
        # Texto contrastante
        brightness = (r * 0.299 + g * 0.587 + b * 0.114)
        text_color = 'white' if brightness < 128 else 'black'
        self.color_preview.config(fg=text_color, text=color_hex)

    def reset_values(self):
        """Resetear todos los valores"""
        self.updating_sliders = True
        
        # Resetear sliders CMYKW
        for letter in ['C', 'M', 'Y', 'K']:
            self.sliders[letter]['slider'].set(0)
        self.sliders['W']['slider'].set(100)
        
        # Resetear sliders HSL
        self.hsl_sliders['H']['slider'].set(0)
        self.hsl_sliders['S']['slider'].set(0)
        self.hsl_sliders['L']['slider'].set(100)
        
        self.updating_sliders = False
        
        # Actualizar vista
        self.update_color_preview()
        
        # Centrar marcador en círculo cromático
        size = 200
        center = size // 2
        self.hue_circle.coords(
            self.hue_marker,
            center-5, center-5,
            center+5, center+5
        )

    def copy_rgb(self):
        """Copiar valores RGB al portapapeles"""
        c = self.sliders['C']['slider'].get()
        m = self.sliders['M']['slider'].get()
        y = self.sliders['Y']['slider'].get()
        k = self.sliders['K']['slider'].get()
        w = self.sliders['W']['slider'].get()
        
        r, g, b = cmykw_to_rgb(c, m, y, k, w)
        rgb_text = f"RGB({r}, {g}, {b})"
        
        self.root.clipboard_clear()
        self.root.clipboard_append(rgb_text)
        messagebox.showinfo("Copiado", f"RGB copiado: {rgb_text}")

    def copy_cmykw(self):
        """Copiar valores CMYKW al portapapeles"""
        c = self.sliders['C']['slider'].get()
        m = self.sliders['M']['slider'].get()
        y = self.sliders['Y']['slider'].get()
        k = self.sliders['K']['slider'].get()
        w = self.sliders['W']['slider'].get()
        
        cmykw_text = f"CMYKW({c}, {m}, {y}, {k}, {w})"
        
        self.root.clipboard_clear()
        self.root.clipboard_append(cmykw_text)
        messagebox.showinfo("Copiado", f"CMYKW copiado: {cmykw_text}")

    def config_plc(self):
        """Configurar conexión PLC (Modbus o Serial)"""
        dialog = PLCConfigDialog(self.root, self.config)
        if dialog.result:
            self.config.update(dialog.result)
            self.save_config()
            
            # Cerrar conexión anterior si existe
            if hasattr(self, 'plc'):
                self.plc.close()
            
            # Actualizar PLC manager con nueva configuración
            self.plc = PLCManager(
                connection_type=self.config.get('connection_type', 'none'),
                ip=self.config.get('plc_ip', '192.168.0.10'),
                port=self.config.get('plc_port', 502),
                serial_port=self.config.get('serial_port'),
                baudrate=self.config.get('baudrate', 9600)
            )
            
            # Actualizar estado en la UI
            connection_status = "🔴 Sin conexión"
            if self.plc.connection_type == 'modbus' and MODBUS_AVAILABLE:
                connection_status = f"🟢 Modbus TCP - {self.plc.ip}:{self.plc.port}"
            elif self.plc.connection_type == 'serial' and SERIAL_AVAILABLE:
                if self.plc.serial_connection and self.plc.serial_connection.is_open:
                    connection_status = f"🟢 Serial - {self.plc.serial_port} @ {self.plc.baudrate} baud"
                else:
                    connection_status = f"🔴 Serial - {self.plc.serial_port} (no conectado)"
            
            self.plc_status_label.config(text=connection_status)
            messagebox.showinfo("Configuración", "Configuración de comunicación actualizada")

    def on_closing(self):
        """Manejar cierre de aplicación"""
        self.stop_camera()
        if hasattr(self, 'plc'):
            self.plc.close()
        self.save_config()
        self.root.destroy()

# ---------- DIÁLOGO DE CONFIGURACIÓN PLC (MODIFICADO) ----------
class PLCConfigDialog:
    def __init__(self, parent, config):
        self.result = None
        
        # Crear ventana
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Configuración de Comunicación")
        self.dialog.geometry("400x300")
        self.dialog.resizable(False, False)
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Variables
        self.connection_type = tk.StringVar(value=config.get('connection_type', 'none'))
        self.ip_var = tk.StringVar(value=config.get('plc_ip', '192.168.0.10'))
        self.port_var = tk.StringVar(value=str(config.get('plc_port', 502)))
        self.serial_port_var = tk.StringVar(value=config.get('serial_port', ''))
        self.baudrate_var = tk.StringVar(value=str(config.get('baudrate', 9600)))
        
        # Crear widgets
        main_frame = ttk.Frame(self.dialog, padding="20")
        main_frame.pack(fill='both', expand=True)
        
        # Tipo de conexión
        ttk.Label(main_frame, text="Tipo de conexión:").grid(row=0, column=0, sticky='w', pady=5)
        connection_frame = ttk.Frame(main_frame)
        connection_frame.grid(row=0, column=1, sticky='ew', pady=5)
        
        ttk.Radiobutton(connection_frame, text="Ninguna", variable=self.connection_type, value='none').pack(side='left')
        ttk.Radiobutton(connection_frame, text="Modbus TCP", variable=self.connection_type, value='modbus').pack(side='left', padx=10)
        ttk.Radiobutton(connection_frame, text="Serial", variable=self.connection_type, value='serial').pack(side='left')
        
        # Configuración Modbus
        self.modbus_frame = ttk.LabelFrame(main_frame, text="Configuración Modbus TCP", padding=10)
        self.modbus_frame.grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)
        
        ttk.Label(self.modbus_frame, text="IP del PLC:").grid(row=0, column=0, sticky='w', pady=5)
        ttk.Entry(self.modbus_frame, textvariable=self.ip_var, width=20).grid(row=0, column=1, pady=5, padx=(10, 0))
        
        ttk.Label(self.modbus_frame, text="Puerto:").grid(row=1, column=0, sticky='w', pady=5)
        ttk.Entry(self.modbus_frame, textvariable=self.port_var, width=20).grid(row=1, column=1, pady=5, padx=(10, 0))
        
        # Configuración Serial
        self.serial_frame = ttk.LabelFrame(main_frame, text="Configuración Serial", padding=10)
        self.serial_frame.grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)
        
        ttk.Label(self.serial_frame, text="Puerto:").grid(row=0, column=0, sticky='w', pady=5)
        self.serial_combobox = ttk.Combobox(self.serial_frame, textvariable=self.serial_port_var, width=18)
        self.serial_combobox.grid(row=0, column=1, pady=5, padx=(10, 0))
        
        ttk.Label(self.serial_frame, text="Baudrate:").grid(row=1, column=0, sticky='w', pady=5)
        baudrates = ['9600', '19200', '38400', '57600', '115200']
        ttk.Combobox(self.serial_frame, textvariable=self.baudrate_var, values=baudrates, width=18).grid(
            row=1, column=1, pady=5, padx=(10, 0))
        
        # Estado
        self.status_label = ttk.Label(main_frame, text="")
        self.status_label.grid(row=3, column=0, columnspan=2, pady=10)
        
        # Botones
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=4, column=0, columnspan=2, pady=10)
        
        ttk.Button(button_frame, text="Aceptar", command=self.accept).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Cancelar", command=self.cancel).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Probar", command=self.test_connection).pack(side='left', padx=5)
        ttk.Button(button_frame, text="Buscar Puertos", command=self.detect_serial_ports).pack(side='left', padx=5)
        
        # Actualizar visibilidad de frames según tipo de conexión
        self.update_connection_frames()
        self.connection_type.trace('w', self.update_connection_frames)
        
        # Detectar puertos seriales disponibles
        self.detect_serial_ports()
        
        # Centrar ventana
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (self.dialog.winfo_width() // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (self.dialog.winfo_height() // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Esperar hasta que se cierre
        self.dialog.wait_window()
        
    def update_connection_frames(self, *args):
        """Mostrar/ocultar frames según tipo de conexión"""
        connection_type = self.connection_type.get()
        
        if connection_type == 'modbus':
            self.modbus_frame.grid()
            self.serial_frame.grid_remove()
        elif connection_type == 'serial':
            self.modbus_frame.grid_remove()
            self.serial_frame.grid()
        else:
            self.modbus_frame.grid_remove()
            self.serial_frame.grid_remove()
            
        # Actualizar estado
        self.update_status_label()
        
    def update_status_label(self):
        """Actualizar etiqueta de estado según conexión seleccionada"""
        connection_type = self.connection_type.get()
        
        if connection_type == 'modbus':
            if MODBUS_AVAILABLE:
                self.status_label.config(text="🟢 pymodbus instalado")
            else:
                self.status_label.config(text="🔴 pymodbus no instalado")
        elif connection_type == 'serial':
            if SERIAL_AVAILABLE:
                self.status_label.config(text="🟢 pyserial instalado")
            else:
                self.status_label.config(text="🔴 pyserial no instalado")
        else:
            self.status_label.config(text="🔴 Sin conexión activa")
            
    def detect_serial_ports(self):
        """Detectar puertos seriales disponibles"""
        if not SERIAL_AVAILABLE:
            messagebox.showerror("Error", "pyserial no está instalado")
            return
            
        ports = [port.device for port in serial.tools.list_ports.comports()]
        self.serial_combobox['values'] = ports
        if ports and not self.serial_port_var.get():
            self.serial_port_var.set(ports[0])
            
    def accept(self):
        """Aceptar configuración"""
        try:
            self.result = {
                'connection_type': self.connection_type.get(),
                'plc_ip': self.ip_var.get(),
                'plc_port': int(self.port_var.get()),
                'serial_port': self.serial_port_var.get(),
                'baudrate': int(self.baudrate_var.get())
            }
            self.dialog.destroy()
        except ValueError as e:
            messagebox.showerror("Error", f"Configuración inválida: {e}")
            
    def cancel(self):
        """Cancelar"""
        self.dialog.destroy()
        
    def test_connection(self):
        """Probar conexión seleccionada"""
        connection_type = self.connection_type.get()
        
        if connection_type == 'modbus':
            self.test_modbus_connection()
        elif connection_type == 'serial':
            self.test_serial_connection()
        else:
            messagebox.showinfo("Información", "No hay conexión configurada para probar")
            
    def test_modbus_connection(self):
        """Probar conexión Modbus"""
        if not MODBUS_AVAILABLE:
            messagebox.showerror("Error", "pymodbus no está instalado")
            return
            
        try:
            ip = self.ip_var.get()
            port = int(self.port_var.get())
            
            client = ModbusTcpClient(ip, port=port)
            if client.connect():
                messagebox.showinfo("Éxito", "Conexión Modbus exitosa")
                client.close()
            else:
                messagebox.showerror("Error", "No se pudo conectar al PLC via Modbus")
        except Exception as e:
            messagebox.showerror("Error", f"Error de conexión Modbus: {e}")
            
    def test_serial_connection(self):
        """Probar conexión Serial"""
        if not SERIAL_AVAILABLE:
            messagebox.showerror("Error", "pyserial no está instalado")
            return
            
        port = self.serial_port_var.get()
        baudrate = int(self.baudrate_var.get())
        
        if not port:
            messagebox.showerror("Error", "Selecciona un puerto serial")
            return
            
        try:
            ser = serial.Serial(port, baudrate, timeout=1)
            if ser.is_open:
                messagebox.showinfo("Éxito", f"Conexión serial establecida en {port}")
                ser.close()
            else:
                messagebox.showerror("Error", f"No se pudo abrir el puerto {port}")
        except Exception as e:
            messagebox.showerror("Error", f"Error al conectar serial: {e}")

# ---------- FUNCIÓN PRINCIPAL ----------
def main():
    root = tk.Tk()
    app = ColorConverterApp(root)
    
    # Manejar cierre
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    
    # Iniciar aplicación
    root.mainloop()

if __name__ == "__main__":
    main()