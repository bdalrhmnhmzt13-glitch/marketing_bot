import telebot
import sqlite3
import threading
import datetime
import time

TOKEN = "8378560622:AAEJBfXsuCD1MjJlNdKxz9wAPj11swDgxbo"
CHANNEL_ID = "@Flix1211"
ADMIN_USERNAME = "Flixs1212"

bot = telebot.TeleBot(TOKEN)

conn = sqlite3.connect("referrals.db", check_same_thread=False)
cursor = conn.cursor()
cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id TEXT PRIMARY KEY,
    referrer_id TEXT,
    points INTEGER DEFAULT 0
)
""")
conn.commit()

def main_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("📊 نقاطي", "🔗 رابط الإحالة")
    markup.row("🏆 ترتيبي", "🛠️ لوحة التحكم")
    markup.row("🆘 الدعم الفني", "📄 سياسة الخصوصية")
    markup.row("📤 مشاركة البوت")
    return markup

def admin_menu():
    markup = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("👥 عدد المستخدمين", "⭐ مجموع النقاط")
    markup.row("📢 نشر منشور", "📷 نشر صورة")
    markup.row("🖼️ نشر صورة + نص", "🔙 رجوع")
    return markup

def is_subscribed(user_id):
    try:
        status = bot.get_chat_member(CHANNEL_ID, user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return False

@bot.message_handler(commands=['start'])
def start(message):
    user_id = str(message.from_user.id)
    referrer_id = message.text.split(" ")[1] if len(message.text.split()) > 1 else None

    if not is_subscribed(message.from_user.id):
        bot.send_message(message.chat.id, f"🔒 يجب الاشتراك في القناة أولاً: {CHANNEL_ID}")
        return

    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    if not cursor.fetchone():
        cursor.execute("INSERT INTO users (user_id, referrer_id) VALUES (?, ?)", (user_id, referrer_id))
        conn.commit()
        if referrer_id and referrer_id != user_id:
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (referrer_id,))
            if cursor.fetchone():
                cursor.execute("UPDATE users SET points = points + 1 WHERE user_id = ?", (referrer_id,))
                conn.commit()
        bot.send_message(message.chat.id, "🎉 تم تسجيلك بنجاح!", reply_markup=main_menu())
    else:
        bot.send_message(message.chat.id, "👋 أنت مسجل مسبقًا.", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "📊 نقاطي")
def my_points(message):
    user_id = str(message.from_user.id)
    cursor.execute("SELECT points FROM users WHERE user_id = ?", (user_id,))
    result = cursor.fetchone()
    points = result[0] if result else 0
    bot.send_message(message.chat.id, f"⭐ نقاطك: {points}")

@bot.message_handler(func=lambda m: m.text == "🔗 رابط الإحالة")
def my_link(message):
    user_id = str(message.from_user.id)
    link = f"https://t.me/mapr12_bot?start={user_id}"
    bot.send_message(message.chat.id, f"🔗 رابط الإحالة الخاص بك:\n{link}")

@bot.message_handler(func=lambda m: m.text == "🏆 ترتيبي")
def top(message):
    cursor.execute("SELECT user_id, points FROM users ORDER BY points DESC LIMIT 5")
    top_users = cursor.fetchall()
    text = "🏆 أفضل المحيلين:\n"
    for i, (uid, pts) in enumerate(top_users, start=1):
        text += f"{i}. {uid} – {pts} نقاط\n"
    bot.send_message(message.chat.id, text)

@bot.message_handler(func=lambda m: m.text == "🛠️ لوحة التحكم")
def admin(message):
    if message.from_user.username != ADMIN_USERNAME:
        bot.send_message(message.chat.id, "🚫 هذا الأمر للمشرف فقط.")
        return
    bot.send_message(message.chat.id, "🛠️ لوحة التحكم:", reply_markup=admin_menu())

@bot.message_handler(func=lambda m: m.text == "👥 عدد المستخدمين")
def show_users(message):
    cursor.execute("SELECT COUNT(*) FROM users")
    total = cursor.fetchone()[0]
    bot.send_message(message.chat.id, f"👥 عدد المستخدمين: {total}")

@bot.message_handler(func=lambda m: m.text == "⭐ مجموع النقاط")
def show_points(message):
    cursor.execute("SELECT SUM(points) FROM users")
    total_points = cursor.fetchone()[0] or 0
    bot.send_message(message.chat.id, f"⭐ مجموع النقاط: {total_points}")

@bot.message_handler(func=lambda m: m.text == "📢 نشر منشور")
def ask_broadcast(message):
    bot.send_message(message.chat.id, "✍️ أرسل الآن النص الذي تريد نشره:")
    bot.register_next_step_handler(message, broadcast_message)

def broadcast_message(message):
    text = message.text
    try:
        bot.send_message(CHANNEL_ID, text)
    except:
        bot.send_message(message.chat.id, "⚠️ فشل إرسال المنشور للقناة.")
    cursor.execute("SELECT user_id FROM users")
    for (uid,) in cursor.fetchall():
        try:
            bot.send_message(uid, text)
        except:
            continue
    bot.send_message(message.chat.id, "✅ تم نشر المنشور بنجاح.")

@bot.message_handler(func=lambda m: m.text == "📷 نشر صورة")
def ask_photo(message):
    bot.send_message(message.chat.id, "📤 أرسل الآن الصورة التي تريد نشرها:")
    bot.register_next_step_handler(message, broadcast_photo)

def broadcast_photo(message):
    if not message.photo:
        bot.send_message(message.chat.id, "⚠️ لم يتم إرسال صورة.")
        return
    file_id = message.photo[-1].file_id
    try:
        bot.send_photo(CHANNEL_ID, file_id)
    except:
        bot.send_message(message.chat.id, "⚠️ فشل إرسال الصورة للقناة.")
    cursor.execute("SELECT user_id FROM users")
    for (uid,) in cursor.fetchall():
        try:
            bot.send_photo(uid, file_id)
        except:
            continue
    bot.send_message(message.chat.id, "✅ تم نشر الصورة بنجاح.")

@bot.message_handler(func=lambda m: m.text == "🖼️ نشر صورة + نص")
def ask_photo_with_caption(message):
    bot.send_message(message.chat.id, "📤 أرسل الآن الصورة مع التعليق:")
    bot.register_next_step_handler(message, broadcast_photo_with_caption)

def broadcast_photo_with_caption(message):
    if not message.photo:
        bot.send_message(message.chat.id, "⚠️ لم يتم إرسال صورة.")
        return
    file_id = message.photo[-1].file_id
    caption = message.caption or "📷 صورة بدون تعليق"
    try:
        bot.send_photo(CHANNEL_ID, file_id, caption=caption)
    except:
        bot.send_message(message.chat.id, "⚠️ فشل إرسال الصورة للقناة.")
    cursor.execute("SELECT user_id FROM users")
    for (uid,) in cursor.fetchall():
        try:
            bot.send_photo(uid, file_id, caption=caption)
        except:
            continue
    bot.send_message(message.chat.id, "✅ تم نشر الصورة مع التعليق.")

@bot.message_handler(func=lambda m: m.text == "🔙 رجوع")
def back_to_main(message):
    bot.send_message(message.chat.id, "📋 رجوع إلى القائمة:", reply_markup=main_menu())

@bot.message_handler(func=lambda m: m.text == "🆘 الدعم الفني")
def support(message):
    bot.send_message(message.chat.id, "📬 للتواصل مع الدعم:\n@Flixs1212")

@bot.message_handler(func=lambda m: m.text == "📄 سياسة الخصوصية")
def privacy(message):
    bot.send_message(message.chat.id, """📄 سياسة الخصوصية:

نحن نحترم خصوصيتك. لا يتم جمع أي معلومات شخصية خارج بيانات التسجيل داخل البوت. يتم استخدام معرف المستخدم فقط لحساب النقاط والإحالات. لا يتم مشاركة أي بيانات مع أطراف خارجية.

باستخدامك لهذا البوت، فإنك توافق على هذه السياسة.

لأي استفسار: @Flixs1212""")

@bot.message_handler(func=lambda m: m.text == "📤 مشاركة البوت")
def share_bot(message):
    user_id = str(message.from_user.id)
    link = f"https://t.me/mapr12_bot?start={user_id}"
print("✅ Bot is running...")
bot.polling()
