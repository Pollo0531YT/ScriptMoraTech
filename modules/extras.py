#!/usr/bin/env python3
"""
Módulo Extras - Configuraciones adicionales
"""
import subprocess
from modules.common import Color, clear_screen, print_banner, print_line
import moratech

def menu_extras():
    """Menú de extras y configuraciones"""
    while True:
        clear_screen()
        print_banner()
        print_line()
        print(f" {Color.CYAN}EXTRAS Y CONFIGURACIONES{Color.END}")
        print_line()
        
        # Mostrar zona horaria actual
        try:
            result = subprocess.run(['timedatectl', 'show', '--property=Timezone', '--value'], 
                                  capture_output=True, text=True)
            current_tz = result.stdout.strip()
            print(f" {Color.YELLOW}Zona horaria actual: {Color.GREEN}{current_tz}{Color.END}")
        except:
            print(f" {Color.YELLOW}Zona horaria actual: {Color.RED}Desconocida{Color.END}")
        
        print_line()
        print(f" {Color.GREEN}[1]{Color.END} ➮ Configurar zona horaria")
        print(f" {Color.GREEN}[2]{Color.END} ➮ Optimizar sistema")
        print(f" {Color.GREEN}[3]{Color.END} ➮ Limpieza y mantenimiento")
        print_line()
        print(f" {Color.RED}[0]{Color.END} ⇦ {Color.YELLOW}Volver{Color.END}")
        print_line()
        
        choice = input(f" {Color.CYAN}►{Color.END} Opción: ").strip()
        
        if choice == '1':
            configurar_zona_horaria()
        elif choice == '2':
            print(f"\n {Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '3':
            print(f"\n {Color.YELLOW}Función en desarrollo...{Color.END}")
            input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")
        elif choice == '0':
            break


def configurar_zona_horaria():
    """Configurar zona horaria del sistema"""
    clear_screen()
    print_banner()
    print_line()
    print(f" {Color.CYAN}CONFIGURAR ZONA HORARIA{Color.END}")
    print_line()
    
    # Mostrar zona horaria actual
    try:
        result = subprocess.run(['timedatectl', 'show', '--property=Timezone', '--value'], 
                              capture_output=True, text=True)
        current_tz = result.stdout.strip()
        
        result_time = subprocess.run(['date', '+%Y-%m-%d %H:%M:%S'], 
                                    capture_output=True, text=True)
        current_time = result_time.stdout.strip()
        
        print(f"\n {Color.YELLOW}Configuración actual:{Color.END}")
        print(f" {Color.CYAN}Zona horaria: {Color.GREEN}{current_tz}{Color.END}")
        print(f" {Color.CYAN}Hora actual: {Color.GREEN}{current_time}{Color.END}")
    except:
        print(f"\n {Color.RED}✗ No se pudo obtener la zona horaria actual{Color.END}")
    
    print(f"\n {Color.YELLOW}Selecciona la zona horaria:{Color.END}\n")
    print(f" {Color.GREEN}[1]{Color.END} Costa Rica / México (America/Costa_Rica)")
    print(f" {Color.GREEN}[2]{Color.END} Mantener zona horaria actual")
    print_line()
    
    choice = input(f"\n {Color.CYAN}►{Color.END} Opción: ").strip()
    
    if choice == '1':
        timezone = 'America/Costa_Rica'
        
        print(f"\n {Color.YELLOW}Configurando zona horaria a {timezone}...{Color.END}")
        
        try:
            # Configurar zona horaria
            result = subprocess.run(['timedatectl', 'set-timezone', timezone], 
                                  capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f" {Color.GREEN}✓ Zona horaria configurada correctamente{Color.END}")
                
                # Mostrar nueva hora
                result_time = subprocess.run(['date', '+%Y-%m-%d %H:%M:%S'], 
                                           capture_output=True, text=True)
                new_time = result_time.stdout.strip()
                
                print(f"\n {Color.CYAN}Nueva configuración:{Color.END}")
                print(f" {Color.CYAN}Zona horaria: {Color.GREEN}{timezone}{Color.END}")
                print(f" {Color.CYAN}Hora actual: {Color.GREEN}{new_time}{Color.END}")
                
                moratech.log_action("admin", f"Zona horaria cambiada a {timezone}")
            else:
                print(f" {Color.RED}✗ Error configurando zona horaria: {result.stderr}{Color.END}")
                
        except Exception as e:
            print(f" {Color.RED}✗ Error: {e}{Color.END}")
    
    elif choice == '2':
        print(f"\n {Color.YELLOW}Zona horaria sin cambios{Color.END}")
    
    input(f"\n {Color.CYAN}Presiona Enter...{Color.END}")