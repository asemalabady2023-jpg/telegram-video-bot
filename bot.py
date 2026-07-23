import telebot
import yt_dlp
import os
import threading
import time
from collections import deque
from flask import Flask, request

TOKEN = os.environ.get('TELEGRAM_BOT_TOKEN', 'YOUR_TOKEN_HERE')
ALLOWED_USERS = [7369661601]

bot = telebot.TeleBot(TOKEN)
app = Flask(__name__)

download_queue = deque()
active_downloads = {}

QUALITY_OPTIONS = {
    'best': 'best',
    '720': 'best[height<=720]',
    '480': 'best[height<=480]',
    '360': 'best[height<=360]',
    'audio': 'bestaudio',
}

user_quality = {}
user_format = {}

def is_allowed(user_id):
    return user_id in ALLOWED_USERS

@bot.message_handler(commands=['start'])
def start(message):
    if not is_allowed(message.from_user.id):
        return
    markup = telebot.types.ReplyKeyboardMarkup(row_width=2, resize_keyboard=True)
    markup.add('Video', 'Audio', 'Quality', 'Queue')
    bot.send_message(message.chat.id, '🎬 Welcome! Choose option or send link.', reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == 'Video')
def set_video(message):
    user_format[message.from_user.id] = 'video'
    bot.reply_to(message, '✅ Mode: Video')

@bot.message_handler(func=lambda m: m.text == 'Audio')
def set_audio(message):
    user_format[message.from_user.id] = 'audio'
    bot.reply_to(message, '✅ Mode: Audio (MP3)')

@bot.message_handler(func=lambda m: m.text == 'Quality')
def set_quality(message):
    markup = telebot.types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        telebot.types.InlineKeyboardButton('Best', callback_data='q_best'),
        telebot.types.InlineKeyboardButton('720p', callback_data='q_720'),
        telebot.types.InlineKeyboardButton('480p', callback_data='q_480'),
        telebot.types.InlineKeyboardButton('360p', callback_data='q_360'),
        telebot.types.InlineKeyboardButton('Audio', callback_data='q_audio')
    )
    bot.send_message(message.chat.id, '📊 Select quality:', reply_markup=markup)

@bot.callback_query_handler(func=lambda c: c.data.startswith('q_'))
def quality_callback(call):
    q = call.data.replace('q_', '')
    user_quality[call.from_user.id] = q
    bot.answer_callback_query(call.id, f'Quality: {q}')

@bot.message_handler(func=lambda m: m.text.startswith('http'))
def download(message):
    if not is_allowed(message.from_user.id):
        return
    url = message.text.strip()
    user_id = message.from_user.id
    fmt = user_format.get(user_id, 'video')
    quality = user_quality.get(user_id, 'best')
    if fmt == 'audio':
        quality = 'audio'

    item = {'user_id': user_id, 'chat_id': message.chat.id, 'url': url, 'quality': quality, 'format': fmt}
    download_queue.append(item)

    if user_id in active_downloads:
        bot.reply_to(message, f'⏳ Added to queue (#{len([q for q in download_queue if q["user_id"]==user_id])})')
    else:
        bot.reply_to(message, '📥 Downloading...')
        threading.Thread(target=process_queue, daemon=True).start()

def process_queue():
    while download_queue:
        item = download_queue.popleft()
        user_id = item['user_id']
        if user_id in active_downloads:
            download_queue.appendleft(item)
            time.sleep(2)
            continue
        active_downloads[user_id] = True
        try:
            download_and_send(item)
        except Exception as e:
            bot.send_message(item['chat_id'], f'❌ Error: {str(e)[:200]}')
        del active_downloads[user_id]
        time.sleep(1)

def download_and_send(item):
    chat_id = item['chat_id']
    url = item['url']
    quality = item['quality']
    fmt = item['format']
    msg = bot.send_message(chat_id, '⏳ Preparing...')

    os.makedirs('downloads', exist_ok=True)

    ydl_opts = {
        'format': QUALITY_OPTIONS.get(quality, 'best'),
        'outtmpl': f'downloads/{item["user_id"]}_%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }

    if fmt == 'audio':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192'
        }]

    try:
        with yt_dlp.YoutubeDL({**ydl_opts, 'skip_download': True}) as ydl:
            info = ydl.extract_info(url, download=False)
            title = info.get('title', 'No Title')
            duration = info.get('duration', 0)

        bot.edit_message_text(f'📥 Downloading: {title[:50]}...', chat_id, msg.message_id)

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if fmt == 'audio' and not filename.endswith('.mp3'):
                filename = os.path.splitext(filename)[0] + '.mp3'

        file_size = os.path.getsize(filename)
        if file_size > 50 * 1024 * 1024:
            bot.edit_message_text(f'⚠️ Too big: {file_size/1024/1024:.1f}MB (max 50MB)', chat_id, msg.message_id)
            os.remove(filename)
            return

        bot.edit_message_text('📤 Sending...', chat_id, msg.message_id)

        with open(filename, 'rb') as f:
            if fmt == 'audio':
                bot.send_audio(chat_id, f, title=title, performer='Download Bot', caption=f'🎵 {title}')
            else:
                bot.send_video(chat_id, f, caption=f'✅ {title}', supports_streaming=True, duration=duration)

        bot.delete_message(chat_id, msg.message_id)
        os.remove(filename)

    except Exception as e:
        error = str(e)
        if 'Unsupported URL' in error:
            bot.edit_message_text('❌ Unsupported URL!', chat_id, msg.message_id)
        elif 'Private' in error or 'login' in error.lower():
            bot.edit_message_text('🔒 Private content or login required!', chat_id, msg.message_id)
        elif 'not available' in error.lower():
            bot.edit_message_text('❌ Video not available!', chat_id, msg.message_id)
        else:
            bot.edit_message_text(f'❌ Error: {error[:150]}', chat_id, msg.message_id)

@app.route('/' + TOKEN, methods=['POST'])
def webhook():
    json_str = request.get_data().decode('UTF-8')
    update = telebot.types.Update.de_json(json_str)
    bot.process_new_updates([update])
    return 'OK', 200

@app.route('/')
def index():
    return 'Bot is running! ✅', 200

if __name__ == '__main__':
    bot.remove_webhook()
    time.sleep(1)
    webhook_url = os.environ.get('RAILWAY_STATIC_URL', '')
    if webhook_url:
        bot.set_webhook(url=f'{webhook_url}/{TOKEN}')
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
