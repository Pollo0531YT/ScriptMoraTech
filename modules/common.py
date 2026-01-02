#!/usr/bin/env python3
"""
Módulo común - Constantes y utilidades compartidas
"""
import os
from pathlib import Path

# Colores
class Color:
    PURPLE = '\033[95m'
    CYAN = '\033[96m'
    BLUE = '\033[94m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'
    WHITE = '\033[97m'     
    MAGENTA = '\033[35m'    
    GRAY = '\033[90m'     

# Configuración
CONFIG_DIR = Path.home() / '.moratech'
PROTOCOLS_FILE = CONFIG_DIR / 'protocols.json'

def clear_screen():
    os.system('clear')

def print_line():
    print(f"{Color.CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━{Color.END}")

def print_banner():
    banner = f"""
{Color.PURPLE}{Color.BOLD}
    ███╗   ███╗ ██████╗ ██████╗  █████╗ ████████╗███████╗
    ████╗ ████║██╔═══██╗██╔══██╗██╔══██╗╚══██╔══╝██╔════╝
    ██╔████╔██║██║   ██║██████╔╝███████║   ██║   █████╗  
    ██║╚██╔╝██║██║   ██║██╔══██╗██╔══██║   ██║   ██╔══╝  
    ██║ ╚═╝ ██║╚██████╔╝██║  ██║██║  ██║   ██║   ███████╗
    ╚═╝     ╚═╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝   ╚═╝   ╚══════╝
{Color.END}"""
    print(banner)