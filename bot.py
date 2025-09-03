import g4f
from g4f.client import Client
import telebot
from telebot.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
import html
import time
import requests
from datetime import datetime, timedelta
import base64
from io import BytesIO
import os
import sys
import json
import logging
import psycopg2
from psycopg2.extras import RealDictCursor
from urllib.parse import urlparse

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Настройки
BOT_TOKEN = "8285433199:AAHaVXqIF7NZIK3V62kgbGeVwCs5A7Q_y2U"
ADMIN_ID = 7328238543
VIP_PRICE = "0 рублей"

# Инициализация
bot = telebot.TeleBot(BOT_TOKEN)
g4f_client = Client()

# База данных PostgreSQL
class Database:
    def __init__(self):
        self.connection = self.get_connection()
        self.init_database()
    
    def get_connection(self):
        try:
            # Для Render.com
            database_url = os.getenv('DATABASE_URL')
            
            if database_url:
                result = urlparse(database_url)
                conn = psycopg2.connect(
                    database=result.path[1:],
                    user=result.username,
                    password=result.password,
                    host=result.hostname,
                    port=result.port
                )
            else:
                # Для локальной разработки
                conn = psycopg2.connect(
                    database="bot_database",
                    user="postgres",
                    password="password",
                    host="localhost",
                    port="5432"
                )
            
            return conn
        except Exception as e:
            logger.error(f"Ошибка подключения к PostgreSQL: {e}")
            raise
    
    def init_database(self):
        with self.connection.cursor() as cursor:
            # Таблица пользователей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    is_vip BOOLEAN DEFAULT FALSE,
                    requests_today INTEGER DEFAULT 0,
                    requests_hour INTEGER DEFAULT 0,
                    last_request_time DOUBLE PRECISION DEFAULT 0,
                    session_active BOOLEAN DEFAULT FALSE,
                    chat_history TEXT DEFAULT '[]',
                    last_reset_date TEXT,
                    image_requests_today INTEGER DEFAULT 0,
                    image_model TEXT DEFAULT 'flux',
                    text_model TEXT DEFAULT 'deepseek-v3',
                    waiting_for_image BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица админов
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS admins (
                    admin_id BIGINT PRIMARY KEY,
                    username TEXT,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Таблица тестовых моделей
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_models (
                    id SERIAL PRIMARY KEY,
                    model_name TEXT UNIQUE,
                    is_active BOOLEAN DEFAULT FALSE,
                    tested_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Вставляем основного админа если его нет
            cursor.execute('INSERT INTO admins (admin_id) VALUES (%s) ON CONFLICT (admin_id) DO NOTHING', (ADMIN_ID,))
            
            self.connection.commit()
    
    def get_user(self, user_id):
        with self.connection.cursor(cursor_factory=RealDictCursor) as cursor:
            cursor.execute('SELECT * FROM users WHERE user_id = %s', (user_id,))
            result = cursor.fetchone()
            
            if result:
                return {
                    'user_id': result['user_id'],
                    'is_vip': result['is_vip'],
                    'requests_today': result['requests_today'],
                    'requests_hour': result['requests_hour'],
                    'last_request_time': result['last_request_time'],
                    'session_active': result['session_active'],
                    'chat_history': json.loads(result['chat_history']),
                    'last_reset_date': result['last_reset_date'],
                    'image_requests_today': result['image_requests_today'],
                    'image_model': result['image_model'],
                    'text_model': result.get('text_model', 'deepseek-v3'),
                    'waiting_for_image': result.get('waiting_for_image', False)
                }
            return None
    
    def create_user(self, user_id):
        with self.connection.cursor() as cursor:
            current_date = datetime.now().date().isoformat()
            cursor.execute('''
                INSERT INTO users (user_id, last_reset_date, waiting_for_image, text_model) 
                VALUES (%s, %s, FALSE, 'deepseek-v3')
            ''', (user_id, current_date))
            self.connection.commit()
        
        return self.get_user(user_id)
    
    def update_user(self, user_id, **kwargs):
        with self.connection.cursor() as cursor:
            set_clause = ', '.join([f"{key} = %s" for key in kwargs.keys()])
            values = list(kwargs.values()) + [user_id]
            
            cursor.execute(f'''
                UPDATE users 
                SET {set_clause}, updated_at = CURRENT_TIMESTAMP 
                WHERE user_id = %s
            ''', values)
            self.connection.commit()
    
    def is_admin(self, user_id):
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT 1 FROM admins WHERE admin_id = %s', (user_id,))
            return cursor.fetchone() is not None
    
    def get_all_users(self):
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT * FROM users ORDER BY created_at DESC LIMIT 10')
            return cursor.fetchall()
    
    def get_stats(self):
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT COUNT(*) FROM users')
            total_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT COUNT(*) FROM users WHERE is_vip = TRUE')
            vip_users = cursor.fetchone()[0]
            
            cursor.execute('SELECT SUM(requests_today) FROM users')
            total_requests = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT SUM(image_requests_today) FROM users')
            total_images = cursor.fetchone()[0] or 0
            
            cursor.execute('SELECT text_model, COUNT(*) FROM users GROUP BY text_model')
            model_stats = cursor.fetchall()
            
            return {
                'total_users': total_users,
                'vip_users': vip_users,
                'total_requests': total_requests,
                'total_images': total_images,
                'model_stats': model_stats
            }
    
    def add_test_model(self, model_name):
        with self.connection.cursor() as cursor:
            cursor.execute('INSERT INTO test_models (model_name) VALUES (%s) ON CONFLICT (model_name) DO NOTHING', (model_name,))
            self.connection.commit()
    
    def get_test_models(self):
        with self.connection.cursor() as cursor:
            cursor.execute('SELECT model_name FROM test_models ORDER BY tested_at DESC')
            return [row[0] for row in cursor.fetchall()]

# Инициализация базы данных PostgreSQL
max_retries = 5
retry_delay = 2

for i in range(max_retries):
    try:
        db = Database()
        logger.info("✅ Подключение к PostgreSQL установлено")
        break
    except Exception as e:
        logger.error(f"❌ Ошибка подключения к БД (попытка {i+1}/{max_retries}): {e}")
        if i < max_retries - 1:
            time.sleep(retry_delay)
        else:
            logger.error("❌ Не удалось подключиться к PostgreSQL")
            raise

# Класс для управления пользователями
class UserManager:
    @staticmethod
    def get_user(user_id):
        user = db.get_user(user_id)
        if user:
            # Проверяем нужно ли сбросить лимиты
            current_date = datetime.now().date().isoformat()
            if user['last_reset_date'] != current_date:
                user['requests_today'] = 0
                user['image_requests_today'] = 0
                user['last_reset_date'] = current_date
                db.update_user(user_id, 
                              requests_today=0,
                              image_requests_today=0,
                              last_reset_date=current_date)
            
            # Сброс часовых лимитов если прошел час
            current_time = time.time()
            if current_time - user['last_request_time'] > 3600:
                user['requests_hour'] = 0
                db.update_user(user_id, requests_hour=0, last_request_time=current_time)
        
        return user
    
    @staticmethod
    def get_or_create_user(user_id):
        user = UserManager.get_user(user_id)
        if not user:
            user = db.create_user(user_id)
        return user
    
    @staticmethod
    def can_make_request(user_id, is_image=False):
        user = UserManager.get_or_create_user(user_id)
        
        if is_image:
            image_limit = 20 if user['is_vip'] else 5
            if user['image_requests_today'] >= image_limit:
                return False, f"Лимит генерации изображений исчерпан ({image_limit}/день)"
            return True, ""
        
        if user['is_vip']:
            return user['requests_today'] < 1000, f"Дневной лимит исчерпан (1000/1000)"
        else:
            if user['requests_hour'] >= 100:
                return False, f"Часовой лимит исчерпан (100/100)"
            if user['requests_today'] >= 500:
                return False, f"Дневной лимит исчерпан (500/500)"
            return True, ""

# Переводчик
class Translator:
    @staticmethod
    def translate_to_english(text):
        try:
            translation_prompt = f"Переведи на английский язык: '{text}'. Верни только перевод без дополнительного текста."
            
            response = g4f.ChatCompletion.create(
                model="deepseek-v3",
                messages=[{"role": "user", "content": translation_prompt}]
            )
            
            if isinstance(response, str):
                translated = response.strip()
                translated = translated.replace('"', '').replace("'", "")
                
                if translated.lower().startswith('translation:'):
                    translated = translated[12:].strip()
                if translated.lower().startswith('перевод:'):
                    translated = translated[9:].strip()
                
                return translated
            else:
                return text
                
        except Exception as e:
            logger.error(f"Ошибка перевода: {e}")
            return text

# Генератор изображений
class ImageGenerator:
    @staticmethod
    def generate_with_g4f(prompt, model_name):
        try:
            english_prompt = Translator.translate_to_english(prompt)
            
            logger.info(f"Оригинал: {prompt}")
            logger.info(f"Перевод: {english_prompt}")
            logger.info(f"Модель изображения: {model_name}")
            
            response = g4f_client.images.generate(
                model=model_name,
                prompt=english_prompt,
                response_format="url"
            )
            
            if response and hasattr(response, 'data') and len(response.data) > 0:
                image_url = response.data[0].url
                
                image_response = requests.get(image_url, timeout=30)
                if image_response.status_code == 200:
                    return image_response.content, None, english_prompt
                else:
                    return None, f"❌ Не удалось загрузить изображение: {image_response.status_code}", english_prompt
            else:
                return None, "❌ Не удалось сгенерировать изображение", english_prompt
                
        except Exception as e:
            return None, f"❌ Ошибка генерации: {str(e)}", prompt

# Клавиатуры
def get_main_keyboard(is_vip=False):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    buttons = [
        "🔄 Новая сессия",
        "📊 Мой профиль",
        "⭐ Купить VIP",
        "🖼️ Создать изображение",
        "⚙️ Настройки моделей",
        "ℹ️ Помощь"
    ]
    if is_vip:
        buttons[2] = "⭐ VIP статус"
    if db.is_admin(ADMIN_ID):
        buttons.append("👨‍💻 Админ панель")
    markup.add(*buttons)
    return markup

def get_admin_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        "👥 Статистика",
        "🔄 Сбросить лимиты",
        "⭐ Выдать VIP",
        "🧪 Тестирование моделей",
        "📊 Логи пользователей",
        "🔄 Перезагрузка бота",
        "🚪 Выйти из админки"
    )
    return markup

def get_session_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Завершить сессию")
    return markup

def get_image_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("❌ Отмена генерации")
    return markup

def get_image_models_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        "🖼️ FLUX",
        "🖼️ GPT-IMAGE",
        "🔙 Назад"
    )
    return markup

def get_text_models_keyboard(is_vip=False):
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    if is_vip:
        markup.add(
            "📝 GPT-4 (VIP)",
            "📝 DEEPSEEK-V3",
            "🔙 Назад"
        )
    else:
        markup.add(
            "📝 DEEPSEEK-V3",
            "🔙 Назад"
        )
    return markup

def get_settings_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        "🖼️ Модель изображений",
        "📝 Модель текста",
        "🔙 Назад"
    )
    return markup

def get_test_models_keyboard():
    markup = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    markup.add(
        "📋 Список моделей",
        "➕ Добавить модель",
        "🔙 Назад"
    )
    return markup

# Команды
@bot.message_handler(commands=['start'])
def start_command(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    
    welcome_text = (
        "🤖 Добро пожаловать в GPT-бот!\n\n"
        "🔹 Обычные пользователи:\n"
        "• DeepSeek-V3 модель\n• 100 запросов в час\n• 500 в день\n• 5 изображений в день\n\n"
        "⭐ VIP пользователи:\n"
        "• GPT-4 модель\n• 1000 запросов в день\n• 20 изображений в день\n• Приоритетная очередь\n\n"
        "Ваши текущие настройки:\n"
        f"• 🖼️ Модель изображений: {user['image_model']}\n"
        f"• 📝 Модель текста: {user['text_model']}\n\n"
        "Настройки индивидуальны для каждого пользователя!\n\n"
        "Нажмите '🔄 Новая сессия' чтобы начать!\n\n"
        "Данный бот разработан @Arkadarootfurry\n\n"
        "В боте могут быть баги!"
    )
    
    if db.is_admin(message.from_user.id):
        bot.send_message(message.chat.id, welcome_text, reply_markup=get_admin_keyboard())
    else:
        bot.send_message(message.chat.id, welcome_text, reply_markup=get_main_keyboard(user['is_vip']))

@bot.message_handler(func=lambda message: message.text == "👨‍💻 Админ панель")
def admin_panel_command(message):
    if db.is_admin(message.from_user.id):
        bot.send_message(message.chat.id, "👨‍💻 Добро пожаловать в админ панель!", reply_markup=get_admin_keyboard())
    else:
        bot.send_message(message.chat.id, "❌ У вас нет доступа к админ панели")

# ОБРАБОТЧИКИ АДМИН-КОМАНД
@bot.message_handler(func=lambda message: db.is_admin(message.from_user.id) and message.text == "👥 Статистика")
def admin_stats_command(message):
    stats = db.get_stats()
    stats_text = (
        f"📊 Статистика бота:\n\n"
        f"👥 Всего пользователей: {stats['total_users']}\n"
        f"⭐ VIP пользователей: {stats['vip_users']}\n"
        f"📨 Всего запросов сегодня: {stats['total_requests']}\n"
        f"🎨 Всего изображений сегодня: {stats['total_images']}\n\n"
        f"🤖 Используемые модели текста:\n"
    )
    
    for model, count in stats['model_stats']:
        stats_text += f"• {model}: {count} пользователей\n"
    
    stats_text += "\n💾 База данных сохраняет: ✅ Статистику, ✅ VIP статусы, ✅ Индивидуальные настройки"
    bot.send_message(message.chat.id, stats_text)

@bot.message_handler(func=lambda message: db.is_admin(message.from_user.id) and message.text == "🔄 Сбросить лимиты")
def admin_reset_limits_command(message):
    with db.connection.cursor() as cursor:
        cursor.execute('UPDATE users SET requests_today = 0, requests_hour = 0, image_requests_today = 0')
        db.connection.commit()
    bot.send_message(message.chat.id, "✅ Лимиты всех пользователей сброшены!")

@bot.message_handler(func=lambda message: db.is_admin(message.from_user.id) and message.text == "⭐ Выдать VIP")
def admin_grant_vip_command(message):
    msg = bot.send_message(message.chat.id, "Введите ID пользователя для выдачи VIP:")
    bot.register_next_step_handler(msg, grant_vip_step)

def grant_vip_step(message):
    try:
        user_id = int(message.text)
        user = UserManager.get_or_create_user(user_id)
        db.update_user(user_id, is_vip=True)
        bot.send_message(message.chat.id, f"✅ Пользователю {user_id} выдан VIP статус!")
        try:
            bot.send_message(user_id, "🎉 Вам выдан VIP статус! Теперь доступен GPT-4 и 1000 запросов в день!")
        except Exception as e:
            logger.error(f"Не удалось отправить сообщение пользователю {user_id}: {e}")
    except ValueError:
        bot.send_message(message.chat.id, "❌ Неверный ID пользователя!")

@bot.message_handler(func=lambda message: db.is_admin(message.from_user.id) and message.text == "🧪 Тестирование моделей")
def admin_test_models_command(message):
    bot.send_message(message.chat.id, "🧪 Меню тестирования моделей:", reply_markup=get_test_models_keyboard())

@bot.message_handler(func=lambda message: db.is_admin(message.from_user.id) and message.text == "📋 Список моделей")
def admin_models_list_command(message):
    models = db.get_test_models()
    if models:
        models_text = "📋 Список тестовых моделей:\n\n" + "\n".join([f"• {model}" for model in models])
    else:
        models_text = "📋 Список тестовых моделей пуст."
    bot.send_message(message.chat.id, models_text)

@bot.message_handler(func=lambda message: db.is_admin(message.from_user.id) and message.text == "➕ Добавить модель")
def admin_add_model_command(message):
    msg = bot.send_message(message.chat.id, "Введите название модели для тестирования:")
    bot.register_next_step_handler(msg, add_model_step)

def add_model_step(message):
    model_name = message.text.strip()
    if model_name:
        db.add_test_model(model_name)
        bot.send_message(message.chat.id, f"✅ Модель '{model_name}' добавлена в список для тестирования!")
        
        # Тестируем модель сразу
        bot.send_message(message.chat.id, f"🧪 Тестирую модель '{model_name}'...")
        try:
            # Пробуем сделать простой запрос к модели
            test_response = g4f.ChatCompletion.create(
                model=model_name,
                messages=[{"role": "user", "content": "Привет! Ответь коротко: 'Тест пройден'"}],
                stream=False
            )
            
            if isinstance(test_response, str):
                bot.send_message(message.chat.id, f"✅ Модель '{model_name}' работает! Ответ: {test_response[:100]}...")
            else:
                bot.send_message(message.chat.id, f"⚠️ Модель '{model_name}' ответила не текстом: {type(test_response)}")
                
        except Exception as e:
            bot.send_message(message.chat.id, f"❌ Ошибка тестирования модели '{model_name}': {str(e)}")
    else:
        bot.send_message(message.chat.id, "❌ Название модели не может быть пустым!")

@bot.message_handler(func=lambda message: db.is_admin(message.from_user.id) and message.text == "📊 Логи пользователей")
def admin_users_log_command(message):
    users = db.get_all_users()
    log_text = "📋 Последние 10 пользователей:\n\n"
    for user in users:
        status = "VIP" if user[1] else "Обычный"
        text_model = user[10] if len(user) > 10 else 'deepseek-v3'
        log_text += f"👤 {user[0]} ({status}): {user[2]} запросов, {user[8]} изображений, модель: {text_model}\n"
    bot.send_message(message.chat.id, log_text)

@bot.message_handler(func=lambda message: db.is_admin(message.from_user.id) and message.text == "🔄 Перезагрузка бота")
def admin_restart_command(message):
    bot.send_message(message.chat.id, "🔄 Перезагрузка бота...")
    os.execv(sys.executable, ['python'] + sys.argv)

@bot.message_handler(func=lambda message: db.is_admin(message.from_user.id) and message.text == "🚪 Выйти из админки")
def admin_exit_command(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    bot.send_message(message.chat.id, "👋 Вы вышли из админ-панели", reply_markup=get_main_keyboard(user['is_vip']))

# Остальные команды
@bot.message_handler(func=lambda message: message.text == "📊 Мой профиль")
def profile_command(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    
    status = "⭐ VIP" if user['is_vip'] else "👤 Обычный"
    model = user['text_model']
    text_limits = f"1000/день" if user['is_vip'] else f"100/час, 500/день"
    image_limits = f"20/день" if user['is_vip'] else f"5/день"
    
    profile_text = (
        f"👤 Ваш профиль:\n\n"
        f"🆔 ID: {message.from_user.id}\n"
        f"🎖️ Статус: {status}\n"
        f"🤖 Модель текста: {model}\n"
        f"🎨 Модель изображений: {user['image_model']}\n"
        f"📊 Лимиты текста: {text_limits}\n"
        f"🎨 Лимиты изображений: {image_limits}\n"
        f"📅 За сегодня: {user['requests_today']}\n"
        f"🖼️ Изображений сегодня: {user['image_requests_today']}\n"
        f"⏰ За час: {user['requests_hour']}\n"
        f"💬 Сессия: {'Активна' if user['session_active'] else 'Неактивна'}\n\n"
        f"💾 Индивидуальные настройки сохранены"
    )
    
    bot.send_message(message.chat.id, profile_text)

@bot.message_handler(func=lambda message: message.text == "⚙️ Настройки моделей")
def settings_command(message):
    bot.send_message(message.chat.id, "⚙️ Выберите настройку:", reply_markup=get_settings_keyboard())

@bot.message_handler(func=lambda message: message.text == "🖼️ Модель изображений")
def image_models_command(message):
    bot.send_message(message.chat.id, "🎨 Выберите модель для генерации изображений:", reply_markup=get_image_models_keyboard())

@bot.message_handler(func=lambda message: message.text == "📝 Модель текста")
def text_models_command(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    bot.send_message(message.chat.id, "📝 Выберите модель для текстовых запросов:", reply_markup=get_text_models_keyboard(user['is_vip']))

@bot.message_handler(func=lambda message: message.text in ["🖼️ FLUX", "🖼️ GPT-IMAGE"])
def set_image_model_command(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    
    if message.text == "🖼️ FLUX":
        db.update_user(message.from_user.id, image_model='flux')
        bot.send_message(message.chat.id, "✅ Модель изображений установлена: FLUX", reply_markup=get_main_keyboard(user['is_vip']))
    elif message.text == "🖼️ GPT-IMAGE":
        db.update_user(message.from_user.id, image_model='gpt-image')
        bot.send_message(message.chat.id, "✅ Модель изображений установлена: GPT-IMAGE", reply_markup=get_main_keyboard(user['is_vip']))

@bot.message_handler(func=lambda message: message.text in ["📝 GPT-4 (VIP)", "📝 DEEPSEEK-V3"])
def set_text_model_command(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    
    if message.text == "📝 GPT-4 (VIP)":
        if user['is_vip']:
            db.update_user(message.from_user.id, text_model='gpt-4')
            bot.send_message(message.chat.id, "✅ Модель текста установлена: GPT-4", reply_markup=get_main_keyboard(user['is_vip']))
        else:
            bot.send_message(message.chat.id, "❌ GPT-4 доступен только VIP пользователям!", reply_markup=get_main_keyboard(user['is_vip']))
    elif message.text == "📝 DEEPSEEK-V3":
        db.update_user(message.from_user.id, text_model='deepseek-v3')
        bot.send_message(message.chat.id, "✅ Модель текста установлена: DEEPSEEK-V3", reply_markup=get_main_keyboard(user['is_vip']))

@bot.message_handler(func=lambda message: message.text == "🔙 Назад")
def back_command(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    bot.send_message(message.chat.id, "🔙 Возврат в главное меню", reply_markup=get_main_keyboard(user['is_vip']))

# ИСПРАВЛЕННАЯ КНОПКА СОЗДАНИЯ ИЗОБРАЖЕНИЯ
@bot.message_handler(func=lambda message: message.text == "🖼️ Создать изображение")
def create_image_command(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    
    can_request, error_msg = UserManager.can_make_request(message.from_user.id, is_image=True)
    if not can_request:
        bot.send_message(message.chat.id, f"❌ {error_msg}")
        return
    
    # Используем безопасное обновление
    db.update_user(message.from_user.id, waiting_for_image=True)
    
    msg = bot.send_message(message.chat.id, 
                         "🎨 Опишите изображение, которое хотите создать:\n\nПример: 'Кот на фоне леса с красивыми цветами'",
                         reply_markup=get_image_keyboard())
    bot.register_next_step_handler(msg, process_image_generation)

def process_image_generation(message):
    if message.text == "❌ Отмена генерации":
        db.update_user(message.from_user.id, waiting_for_image=False)
        user = UserManager.get_or_create_user(message.from_user.id)
        bot.send_message(message.chat.id, "❌ Генерация отменена", reply_markup=get_main_keyboard(user['is_vip']))
        return
    
    prompt = message.text.strip()
    if len(prompt) < 5:
        bot.send_message(message.chat.id, "❌ Описание слишком короткое. Минимум 5 символов.")
        return
    
    user = UserManager.get_or_create_user(message.from_user.id)
    db.update_user(message.from_user.id, 
                  image_requests_today=user['image_requests_today'] + 1,
                  waiting_for_image=False)
    
    bot.send_chat_action(message.chat.id, 'typing')
    translating_msg = bot.send_message(message.chat.id, f"🔤 Перевод запроса на английский (модель: {user['image_model']})...")
    
    try:
        image_data, error, english_prompt = ImageGenerator.generate_with_g4f(prompt, user['image_model'])
        
        try:
            bot.delete_message(message.chat.id, translating_msg.message_id)
        except:
            pass
        
        if image_data:
            translation_info = f"🔤 Перевод: '{english_prompt}'\n🎨 Модель: {user['image_model']}"
            bot.send_message(message.chat.id, translation_info)
            
            bot.send_photo(message.chat.id, image_data, 
                          caption=f"🎨 Создано по запросу: '{prompt}'")
        else:
            bot.send_message(message.chat.id, f"❌ {error}")
            
    except Exception as e:
        error_msg = f"❌ Ошибка при генерации: {str(e)}"
        bot.send_message(message.chat.id, error_msg)
    
    finally:
        user = UserManager.get_or_create_user(message.from_user.id)
        bot.send_message(message.chat.id, "Готово! Что дальше?", reply_markup=get_main_keyboard(user['is_vip']))

@bot.message_handler(func=lambda message: message.text == "⭐ Купить VIP")
def buy_vip_command(message):
    vip_text = (
        f"⭐ Приобретите VIP статус всего за {VIP_PRICE}!\n\n"
        "Преимущества VIP:\n"
        "• Доступ к GPT-4 для текста\n"
        "• 1000 запросов в день\n"
        "• 20 изображений в день\n"
        "• Приоритетная обработка\n"
        "• Поддержка 24/7\n\n"
        "Для покупки обратитесь к @Arkadaroot"
    )
    
    bot.send_message(message.chat.id, vip_text)

@bot.message_handler(func=lambda message: message.text == "⭐ VIP статус")
def vip_status_command(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    
    if user['is_vip']:
        vip_text = (
            "🎉 У вас активен VIP статус!\n\n"
            "Ваши преимущества:\n"
            "• ✅ Доступ к GPT-4\n"
            "• ✅ 1000 запросов в день\n"
            "• ✅ 20 изображений в день\n"
            "• ✅ Приоритетная обработка\n"
            "• ✅ Поддержка 24/7\n\n"
            f"📊 Использовано сегодня: {user['requests_today']}/1000\n"
            f"🎨 Изображений: {user['image_requests_today']}/20\n"
            f"🤖 Текущая модель: {user['text_model']}\n\n"
            f"💾 Индивидуальные настройки сохранены"
        )
    else:
        vip_text = "❌ У вас нет VIP статуса. Нажмите '⭐ Купить VIP' для получения доступа."
    
    bot.send_message(message.chat.id, vip_text)

@bot.message_handler(func=lambda message: message.text == "🔄 Новая сессия")
def new_session_command(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    
    can_request, error_msg = UserManager.can_make_request(message.from_user.id)
    if not can_request:
        bot.send_message(message.chat.id, f"❌ {error_msg}")
        return
    
    db.update_user(message.from_user.id, 
                  session_active=True,
                  chat_history=json.dumps([{
                      "role": "system", 
                      "content": "Ты полезный AI ассистент. Отвечай четко и по делу."
                  }]))
    
    bot.send_message(message.chat.id, 
                    f"💬 Сессия начата! Ваша модель: {user['text_model']}\nЗадавайте ваш вопрос...",
                    reply_markup=get_session_keyboard())

# ИСПРАВЛЕННЫЙ ОБРАБОТЧИК ЗАВЕРШЕНИИ СЕССИИ
@bot.message_handler(func=lambda message: message.text == "❌ Завершить сессия")
def end_session_command(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    db.update_user(message.from_user.id, 
                  session_active=False,
                  chat_history=json.dumps([]))
    
    bot.send_message(message.chat.id, 
                    "✅ Сессия завершена! История очищена.",
                    reply_markup=get_main_keyboard(user['is_vip']))

@bot.message_handler(func=lambda message: message.text == "ℹ️ Помощь")
def help_command(message):
    help_text = (
        "ℹ️ Помощь по боту:\n\n"
        "🔄 Новая сессия - начать новый диалог\n"
        "📊 Мой профиль - посмотреть статистику\n"
        "⭐ Купить VIP - получить премиум доступ\n"
        "🖼️ Создать изображение - генерация картинок (с автоматическим переводом)\n"
        "⚙️ Настройки моделей - выбор моделей для текста и изображений\n"
        "❌ Завершить сессию - закончить текущий диалог\n\n"
        "📞 Техподдержка: @Arkadaroot"
    )
    bot.send_message(message.chat.id, help_text)

# Обработка обычных сообщений
@bot.message_handler(func=lambda message: True)
def handle_message(message):
    user = UserManager.get_or_create_user(message.from_user.id)
    
    # Проверка специальных команд
    special_commands = [
        "⭐ VIP статус", "ℹ️ Помощь", "🚪 Выйти из админки", 
        "🖼️ Создать изображение", "❌ Отмена генерации",
        "⚙️ Настройки моделей", "🖼️ Модель изображений",
        "📝 Модель текста", "🖼️ FLUX", "🖼️ GPT-IMAGE",
        "📝 GPT-4 (VIP)", "📝 DEEPSEEK-V3", "🔙 Назад",
        "👨‍💻 Админ панель", "🔄 Перезагрузка бота",
        "👥 Статистика", "🔄 Сбросить лимиты", "⭐ Выдать VIP",
        "🧪 Тестирование моделей", "📋 Список моделей", "➕ Добавить модель",
        "📊 Логи пользователей", "❌ Завершить сессию"
    ]
    
    if message.text in special_commands:
        return
    
    # Проверка сессии
    if not user['session_active']:
        bot.send_message(message.chat.id, "❌ Сначала начните сессию!")
        return
    
    # Проверка лимитов
    can_request, error_msg = UserManager.can_make_request(message.from_user.id)
    if not can_request:
        bot.send_message(message.chat.id, f"❌ {error_msg}")
        db.update_user(message.from_user.id, session_active=False)
        bot.send_message(message.chat.id, "Сессия завершена.", reply_markup=get_main_keyboard(user['is_vip']))
        return
    
    # Обновление лимитов
    current_time = time.time()
    db.update_user(message.from_user.id,
                  requests_today=user['requests_today'] + 1,
                  requests_hour=user['requests_hour'] + 1,
                  last_request_time=current_time)
    
    # Добавление сообщения в историю
    chat_history = user['chat_history']
    chat_history.append({"role": "user", "content": message.text})
    db.update_user(message.from_user.id, chat_history=json.dumps(chat_history))
    
    # Отправка статуса "печатает"
    bot.send_chat_action(message.chat.id, 'typing')
    
    # Генерация ответа
    try:
        model = user['text_model']
        
        response = g4f.ChatCompletion.create(
            model=model,
            messages=chat_history,
            stream=False
        )
        
        if isinstance(response, str):
            assistant_message = response
            import re
            assistant_message = re.sub(r'Thought:.*?End of Thought.*?\)', '', assistant_message, flags=re.DOTALL)
            assistant_message = assistant_message.strip()
        else:
            assistant_message = str(response)
        
        # Добавление ответа в историю
        chat_history.append({"role": "assistant", "content": assistant_message})
        db.update_user(message.from_user.id, chat_history=json.dumps(chat_history))
        
        # Отправка ответа
        decoded_response = html.unescape(assistant_message)
        if len(decoded_response) > 4096:
            for i in range(0, len(decoded_response), 4096):
                bot.send_message(message.chat.id, decoded_response[i:i+4096])
        else:
            bot.send_message(message.chat.id, decoded_response)
            
    except Exception as e:
        error_msg = f"❌ Ошибка: {str(e)}"
        bot.send_message(message.chat.id, error_msg)

# Запуск бота
if __name__ == "__main__":
    logger.info("🤖 Бот запущен!")
    logger.info("🎨 Генерация изображений с автоматическим переводом на английский")
    logger.info("📝 Основная модель: DeepSeek-V3")
    logger.info("💾 База данных PostgreSQL инициализирована")
    logger.info("🧪 Добавлена функция тестирования моделей для админов")
    logger.info("✅ Индивидуальные настройки для каждого пользователя")
    
    try:
        bot.infinity_polling()
    except Exception as e:
        logger.error(f"Ошибка при запуске бота: {e}")