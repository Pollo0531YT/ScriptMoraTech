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

# ==================== ESTADOS FSM ====================

class TokenState(StatesGroup):
    waiting_for_nombre = State()
    waiting_for_token = State()
    waiting_for_dias = State()

class RenovarMState(StatesGroup):
    waiting_for_token = State()
    waiting_for_dias = State()

class RenovarState(StatesGroup):
    waiting_for_token = State()
    waiting_for_dias = State()

class BorrarState(StatesGroup):
    waiting_for_token = State()

class AgregarState(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()
    waiting_for_dias = State()

class RevisarState(StatesGroup):
    waiting_for_token = State()

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
async def token_handler(message: Message, state: FSMContext):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado. Usa /access primero.")
        return
    
    await message.answer("📝 Ingresa el **nombre del cliente**:", parse_mode="Markdown")
    await state.set_state(TokenState.waiting_for_nombre)

@router.message(TokenState.waiting_for_nombre)
async def token_nombre(message: Message, state: FSMContext):
    await state.update_data(nombre=message.text.strip())
    await message.answer("📱 Ahora ingresa el **token**:", parse_mode="Markdown")
    await state.set_state(TokenState.waiting_for_token)

@router.message(TokenState.waiting_for_token)
async def token_token(message: Message, state: FSMContext):
    await state.update_data(token=message.text.strip())
    await message.answer("⏰ Ingresa los **días de servicio**:", parse_mode="Markdown")
    await state.set_state(TokenState.waiting_for_dias)

@router.message(TokenState.waiting_for_dias)
async def token_dias(message: Message, state: FSMContext):
    try:
        dias = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Debe ser un número.")
        return
    
    data = await state.get_data()
    await message.answer("⏳ Creando token...")
    
    try:
        token_config = load_token_config()
        success, msg, expires = sincronizar_usuario(
            username=data['token'],
            password=token_config['token_password'],
            dias=dias,
            operacion='crear',
            user_type='token',
            display_name=data['nombre']
        )
        
        if success:
            await message.answer(
                f"✅ **Token creado**\n\n"
                f"👤 Nombre: `{data['nombre']}`\n"
                f"🔑 Token: `{data['token']}`\n"
                f"⏰ Días: `{dias}`\n"
                f"📅 Expira: `{expires.strftime('%d/%m/%Y')}`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"❌ Error: {msg}")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== /renovarM ====================

@router.message(Command(commands=["renovarM"], ignore_case=True))
async def renovarM_handler(message: Message, state: FSMContext):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado.")
        return
    
    await message.answer("🔑 Ingresa el **token** a renovar:", parse_mode="Markdown")
    await state.set_state(RenovarMState.waiting_for_token)

@router.message(RenovarMState.waiting_for_token)
async def renovarM_token(message: Message, state: FSMContext):
    await state.update_data(token=message.text.strip())
    await message.answer("⏰ Ingresa los **días a sumar**:", parse_mode="Markdown")
    await state.set_state(RenovarMState.waiting_for_dias)

@router.message(RenovarMState.waiting_for_dias)
async def renovarM_dias(message: Message, state: FSMContext):
    try:
        dias = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Debe ser un número.")
        return
    
    data = await state.get_data()
    await message.answer("⏳ Renovando...")
    
    try:
        success, msg, new_date = sincronizar_usuario(
            username=data['token'],
            dias=dias,
            operacion='renovar'
        )
        
        if success:
            await message.answer(
                f"✅ **Token renovado**\n\n"
                f"🔑 Token: `{data['token']}`\n"
                f"➕ Días sumados: `{dias}`\n"
                f"📅 Expira: `{new_date.strftime('%d/%m/%Y')}`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"❌ Error: {msg}")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== /renovar ====================

@router.message(Command(commands=["renovar"], ignore_case=True))
async def renovar_handler(message: Message, state: FSMContext):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado.")
        return
    
    await message.answer("🔑 Ingresa el **token**:", parse_mode="Markdown")
    await state.set_state(RenovarState.waiting_for_token)

@router.message(RenovarState.waiting_for_token)
async def renovar_token(message: Message, state: FSMContext):
    await state.update_data(token=message.text.strip())
    await message.answer("⏰ Ingresa los **días totales** (reinicia):", parse_mode="Markdown")
    await state.set_state(RenovarState.waiting_for_dias)

@router.message(RenovarState.waiting_for_dias)
async def renovar_dias(message: Message, state: FSMContext):
    try:
        dias = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Debe ser un número.")
        return
    
    data = await state.get_data()
    await message.answer("⏳ Reiniciando...")
    
    try:
        success, msg, new_date = sincronizar_usuario(
            username=data['token'],
            dias=dias,
            operacion='reiniciar'
        )
        
        if success:
            await message.answer(
                f"✅ **Token reiniciado**\n\n"
                f"🔑 Token: `{data['token']}`\n"
                f"🔄 Días: `{dias}`\n"
                f"📅 Expira: `{new_date.strftime('%d/%m/%Y')}`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"❌ Error: {msg}")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== /borrar ====================

@router.message(Command(commands=["borrar"], ignore_case=True))
async def borrar_handler(message: Message, state: FSMContext):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado.")
        return
    
    await message.answer("🔑 Ingresa el **token** a eliminar:", parse_mode="Markdown")
    await state.set_state(BorrarState.waiting_for_token)

@router.message(BorrarState.waiting_for_token)
async def borrar_token(message: Message, state: FSMContext):
    token = message.text.strip()
    await message.answer("⏳ Eliminando...")
    
    try:
        success, msg = ejecutar_borrado_fisico(token)
        
        if success:
            await message.answer(f"✅ **Token eliminado**\n\n🔑 `{token}`", parse_mode="Markdown")
        else:
            await message.answer(f"❌ Error: {msg}")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== /agregar ====================

@router.message(Command(commands=["agregar"], ignore_case=True))
async def agregar_handler(message: Message, state: FSMContext):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado.")
        return
    
    await message.answer("👤 Ingresa el **nombre de usuario**:", parse_mode="Markdown")
    await state.set_state(AgregarState.waiting_for_username)

@router.message(AgregarState.waiting_for_username)
async def agregar_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text.strip())
    await message.answer("🔒 Ingresa la **contraseña**:", parse_mode="Markdown")
    await state.set_state(AgregarState.waiting_for_password)

@router.message(AgregarState.waiting_for_password)
async def agregar_password(message: Message, state: FSMContext):
    await state.update_data(password=message.text.strip())
    await message.answer("⏰ Ingresa los **días**:", parse_mode="Markdown")
    await state.set_state(AgregarState.waiting_for_dias)

@router.message(AgregarState.waiting_for_dias)
async def agregar_dias(message: Message, state: FSMContext):
    try:
        dias = int(message.text.strip())
    except ValueError:
        await message.answer("❌ Debe ser un número.")
        return
    
    data = await state.get_data()
    await message.answer("⏳ Creando usuario SSH...")
    
    try:
        success, msg, expires = sincronizar_usuario(
            username=data['username'],
            password=data['password'],
            dias=dias,
            operacion='crear',
            user_type='ssh',
            max_conn=1
        )
        
        if success:
            await message.answer(
                f"✅ **Usuario SSH creado**\n\n"
                f"👤 Usuario: `{data['username']}`\n"
                f"🔒 Contraseña: `{data['password']}`\n"
                f"⏰ Días: `{dias}`\n"
                f"📅 Expira: `{expires.strftime('%d/%m/%Y')}`",
                parse_mode="Markdown"
            )
        else:
            await message.answer(f"❌ Error: {msg}")
    except Exception as e:
        await message.answer(f"❌ Error: {str(e)}")
    
    await state.clear()

# ==================== /revisar ====================

@router.message(Command(commands=["revisar"], ignore_case=True))
async def revisar_handler(message: Message, state: FSMContext):
    if not is_authorized(message.chat.id):
        await message.answer("⛔ No autorizado.")
        return
    
    await message.answer("🔑 Ingresa el **token**:", parse_mode="Markdown")
    await state.set_state(RevisarState.waiting_for_token)

@router.message(RevisarState.waiting_for_token)
async def revisar_token(message: Message, state: FSMContext):
    token = message.text.strip()
    await message.answer("⏳ Consultando...")
    
    try:
        users = load_users()
        
        if token not in users:
            await message.answer(f"❌ Token `{token}` no encontrado.", parse_mode="Markdown")
            await state.clear()
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
    
    await state.clear()

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
