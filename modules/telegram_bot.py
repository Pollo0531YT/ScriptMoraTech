#!/usr/bin/env python3
"""
Bot de Telegram - MORATECH v2.0
Sistema completo de gestión de usuarios VPN
"""

import sys
import json
import asyncio
from pathlib import Path
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher, Router
from aiogram.filters import Command
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# Agregar path de MORATECH
sys.path.insert(0, '/usr/local/lib/moratech')
from modules.users import sincronizar_usuario, ejecutar_borrado_fisico, load_users, load_token_config

# ==================== CONFIGURACIÓN ====================

CONFIG_DIR = Path.home() / '.moratech'
BOT_CONFIG_FILE = CONFIG_DIR / 'bot_config.json'

def load_bot_config():
    """Cargar configuración del bot"""
    if not BOT_CONFIG_FILE.exists():
        print("❌ Error: No hay configuración del bot")
        print(f"   Configura el bot desde el menú MORATECH")
        sys.exit(1)
    
    with open(BOT_CONFIG_FILE, 'r') as f:
        return json.load(f)

# Cargar config
config = load_bot_config()
BOT_TOKEN = config['bot_token']
ACCESS_USER = config['access_user']
ACCESS_PASSWORD = config['access_password']

# ==================== BOT SETUP ====================

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# Usuarios autorizados (en memoria)
authorized_chats = set()


# ==================== HELPERS ====================

def is_authorized(chat_id: int) -> bool:
    return chat_id in authorized_chats

# ==================== COMANDOS BÁSICOS ====================

@router.message(Command(commands=["start"], ignore_case=True))
async def start_handler(message: Message):
    if message.chat.type != "private":
        return
    
    await message.answer(
        "🚀 **Bienvenido al Bot de MORATECH**\n\n"
        "Sistema de gestión de usuarios VPN.\n\n"
        f"Para acceder, usa:\n"
        f"`/access {ACCESS_USER} ********`",
        parse_mode="Markdown"
    )

@router.message(Command(commands=["help"], ignore_case=True))
async def help_handler(message: Message):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado. Usa /access primero.")
        return
    
    await message.answer(
        "📋 **Comandos Disponibles:**\n\n"
        "**Gestión de Tokens:**\n"
        "• `/token` - Crear nuevo token\n"
        "• `/renovarM` - Renovar token (suma días)\n"
        "• `/renovar` - Reiniciar token (días exactos)\n"
        "• `/borrar` - Eliminar token\n\n"
        "**Gestión SSH:**\n"
        "• `/agregar` - Crear usuario SSH\n\n"
        "**Información:**\n"
        "• `/revisar` - Ver días restantes\n"
        "• `/help` - Ver esta ayuda\n"
        "• `/salir` - Cancelar operación",
        parse_mode="Markdown"
    )

@router.message(Command(commands=["salir"], ignore_case=True))
async def salir_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ Operación cancelada.")

@router.message(Command(commands=["access"], ignore_case=True))
async def access_handler(message: Message):
    args = message.text.split()[1:]
    
    if len(args) != 2:
        await message.answer(
            "❌ Uso incorrecto.\n\n"
            f"Formato: `/access {ACCESS_USER} password`",
            parse_mode="Markdown"
        )
        return
    
    username, password = args
    
    if username == ACCESS_USER and password == ACCESS_PASSWORD:
        authorized_chats.add(message.chat.id)
        await message.answer(
            "✅ **Acceso concedido**\n\n"
            "Usa /help para ver los comandos.",
            parse_mode="Markdown"
        )
    else:
        await message.answer("⛔ Credenciales incorrectas.")

# ==================== /token ====================
@router.message(Command(commands=["token"], ignore_case=True))
async def token_handler(message: Message):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado. Usa /access primero.")
        return
    
    # /token {nombre} {token} {dias}
    args = message.text.split()[1:]
    
    if len(args) != 3:
        await message.answer(
            "❌ Uso: `/token nombre token dias`\n"
            "Ejemplo: `/token JuanPerez abc123xyz 30`",
            parse_mode="Markdown"
        )
        return
    
    nombre, token, dias_str = args
    
    try:
        dias = int(dias_str)
    except ValueError:
        await message.answer("❌ Los días deben ser un número.")
        return
    
    await message.answer("⏳ Procesando...")
    
    try:
        # Verificar si ya existe
        users = load_users()
        if token in users:
            await message.answer(
                f"⚠️ **Token ya existe**\n\n"
                f"🔑 `{token}`\n"
                f"Usa `/renovarM {token} {dias}` para renovarlo",
                parse_mode="Markdown"
            )
            return
        
        token_config = load_token_config()
        success, msg, expires = sincronizar_usuario(
            username=token,
            password=token_config['token_password'],
            dias=dias,
            operacion='crear',
            user_type='token',
            display_name=nombre
        )
        
        if success:
            await message.answer(
                f"✅ **Token creado**\n\n"
                f"👤 Nombre: `{nombre}`\n"
                f"🔑 Token: `{token}`\n"
                f"⏰ Días: `{dias}`\n"
                f"📅 Expira: `{expires.strftime('%d/%m/%Y')}`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"❌ Error: {msg}")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")

# ==================== /renovarM ====================
@router.message(Command(commands=["renovarM"], ignore_case=True))
async def renovarM_handler(message: Message):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado.")
        return
    
    # /renovarM {token} {dias}
    args = message.text.split()[1:]
    
    if len(args) != 2:
        await message.answer(
            "❌ Uso: `/renovarM token dias`\n"
            "Ejemplo: `/renovarM abc123xyz 15`",
            parse_mode="Markdown"
        )
        return
    
    token, dias_str = args
    
    try:
        dias = int(dias_str)
    except ValueError:
        await message.answer("❌ Los días deben ser un número.")
        return
    
    await message.answer("⏳ Renovando...")
    
    try:
        # Verificar que existe
        users = load_users()
        if token not in users:
            await message.answer(
                f"❌ **Token no existe**\n\n"
                f"🔑 `{token}`\n"
                f"Créalo primero con `/token nombre {token} {dias}`",
                parse_mode="Markdown"
            )
            return
        
        success, msg, new_date = sincronizar_usuario(
            username=token,
            dias=dias,
            operacion='renovar'
        )
        
        if success:
            await message.answer(
                f"✅ **Token renovado**\n\n"
                f"🔑 Token: `{token}`\n"
                f"➕ Días sumados: `{dias}`\n"
                f"📅 Expira: `{new_date.strftime('%d/%m/%Y')}`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"❌ Error: {msg}")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")

# ==================== /renovar ====================
@router.message(Command(commands=["renovar"], ignore_case=True))
async def renovar_handler(message: Message):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado.")
        return
    
    # /renovar {token} {dias}
    args = message.text.split()[1:]
    
    if len(args) != 2:
        await message.answer(
            "❌ Uso: `/renovar token dias`\n"
            "Ejemplo: `/renovar abc123xyz 30`",
            parse_mode="Markdown"
        )
        return
    
    token, dias_str = args
    
    try:
        dias = int(dias_str)
    except ValueError:
        await message.answer("❌ Los días deben ser un número.")
        return
    
    await message.answer("⏳ Reiniciando...")
    
    try:
        # Verificar que existe
        users = load_users()
        if token not in users:
            await message.answer(
                f"❌ **Token no existe**\n\n"
                f"Créalo primero con `/token nombre {token} {dias}`",
                parse_mode="Markdown"
            )
            return
        
        success, msg, new_date = sincronizar_usuario(
            username=token,
            dias=dias,
            operacion='reiniciar'
        )
        
        if success:
            await message.answer(
                f"✅ **Token reiniciado**\n\n"
                f"🔑 Token: `{token}`\n"
                f"🔄 Días: `{dias}`\n"
                f"📅 Expira: `{new_date.strftime('%d/%m/%Y')}`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"❌ Error: {msg}")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")

# ==================== /borrar ====================
@router.message(Command(commands=["borrar"], ignore_case=True))
async def borrar_handler(message: Message):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado.")
        return
    
    # /borrar {token}
    args = message.text.split()[1:]
    
    if len(args) != 1:
        await message.answer(
            "❌ Uso: `/borrar token`\n"
            "Ejemplo: `/borrar abc123xyz`",
            parse_mode="Markdown"
        )
        return
    
    token = args[0]
    await message.answer("⏳ Eliminando...")
    
    try:
        success, msg = ejecutar_borrado_fisico(token)
        
        if success:
            await message.answer(f"✅ **Eliminado**\n\n🔑 `{token}`", parse_mode="Markdown")
        else:
            await message.answer(f"❌ Error: {msg}")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")

# ==================== /agregar ====================
@router.message(Command(commands=["agregar"], ignore_case=True))
async def agregar_handler(message: Message):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado.")
        return
    
    # /agregar {user} {password} {conexiones} {dias}
    args = message.text.split()[1:]
    
    if len(args) != 4:
        await message.answer(
            "❌ Uso: `/agregar user password conexiones dias`\n"
            "Ejemplo: `/agregar juan123 Pass2026 2 30`",
            parse_mode="Markdown"
        )
        return
    
    username, password, max_conn_str, dias_str = args
    
    try:
        max_conn = int(max_conn_str)
        dias = int(dias_str)
    except ValueError:
        await message.answer("❌ Conexiones y días deben ser números.")
        return
    
    await message.answer("⏳ Creando usuario SSH...")
    
    try:
        success, msg, expires = sincronizar_usuario(
            username=username,
            password=password,
            dias=dias,
            operacion='crear',
            user_type='ssh',
            max_conn=max_conn
        )
        
        if success:
            await message.answer(
                f"✅ **Usuario SSH creado**\n\n"
                f"👤 Usuario: `{username}`\n"
                f"🔒 Contraseña: `{password}`\n"
                f"🔗 Conexiones: `{max_conn}`\n"
                f"⏰ Días: `{dias}`\n"
                f"📅 Expira: `{expires.strftime('%d/%m/%Y')}`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"❌ Error: {msg}")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")

# ==================== /revisar ====================
@router.message(Command(commands=["revisar"], ignore_case=True))
async def revisar_handler(message: Message):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado.")
        return
    
    # /revisar {token}
    args = message.text.split()[1:]
    
    if len(args) != 1:
        await message.answer(
            "❌ Uso: `/revisar token`\n"
            "Ejemplo: `/revisar abc123xyz`",
            parse_mode="Markdown"
        )
        return
    
    token = args[0]
    await message.answer("⏳ Consultando...")
    
    try:
        users = load_users()
        
        if token not in users:
            await message.answer(f"❌ Token `{token}` no encontrado.", parse_mode="Markdown")
            return
        
        expires_str = users[token].get('expires')
        CR_TZ = timezone(timedelta(hours=-6))
        expires_date = datetime.fromisoformat(expires_str)
        now_cr = datetime.now(CR_TZ)
        dias_restantes = (expires_date - now_cr).days
        
        estado = "❌ **VENCIDO**" if dias_restantes < 0 else ("⚠️ **Vence hoy**" if dias_restantes == 0 else "✅ **Activo**")
        
        await message.answer(
            f"{estado}\n\n"
            f"🔑 Token: `{token}`\n"
            f"📅 Expira: `{expires_date.strftime('%d/%m/%Y')}`\n"
            f"⏰ Días: `{dias_restantes}`",
            parse_mode="Markdown"
        )
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")

# ==================== MAIN ====================

async def main():
    dp.include_router(router)
    
    print("=" * 50)
    print("🤖 Bot MORATECH iniciado")
    print(f"📱 Usuario: {ACCESS_USER}")
    print("📡 Esperando comandos...")
    print("=" * 50)
    
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n⚠️ Bot detenido")
