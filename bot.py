import os
import sqlite3
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, MessageHandler, Filters

TOKEN = "8449814367:AAGG4iTNI_0rC8Hga9ctTokNrjXK18YEZFk"

# ================== БАЗА ДАНИХ ==================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(BASE_DIR, "game.db")
conn = sqlite3.connect(db_path, check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS score (
    user_id INTEGER PRIMARY KEY,
    empathy_points INTEGER DEFAULT 0,
    stereotype_points INTEGER DEFAULT 0
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    text TEXT NOT NULL,
    image_path TEXT
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    card_id INTEGER NOT NULL,
    text TEXT NOT NULL,
    FOREIGN KEY(card_id) REFERENCES cards(id)
)
""")

conn.commit()

# ================== КЛЮЧОВІ СЛОВА ==================

# 🔹 Емпатія
empathy_roots = [
    # підтримка / допомога / дії
    "підтрим", "допомог", "допомаг", "поруч", "захищ", "оберіг", "стою", "співчув", "обійми",
    "обійняв", "обійняла", "обійняв би", "обійняла би", "порад", "підтримав", "підтримала",
    "підтримав би", "підтримала би", "допоміг", "допомогла", "допоміг би", "допомогла би",
    "підтримує", "підтримую", "підтримувати", "підтримаю", "підтримаємо",
    
    # емоції / розуміння / співпереживання
    "розум", "шкода", "чую", "важко", "співпережив", "турб", "сум", "страх", "бол", "співчуття",
    "турбуюсь", "чуй", "вболіва", "біль", "печаль", "піклуюсь", "турбота", "зрозумів", "зрозуміла",
    
    # мотивація / прийняття / цінність
    "ціную", "важлив", "вірю", "не один", "не одна", "разом", "повага", "добро", "прийма",
    "єдність", "підтримка", "любов", "дружба", "розуміння", "допомога", "увага", "захист"
]

# 🔹 Стереотипи / осуд
stereotype_roots = [
    "сам вин", "перебільш", "дурниц", "не ний", "вигад", "слабк", "смішн", "забий", 
    "драматиз", "нереал", "поганий", "дивн", "дивак", "слаб", "глуп", "сором", "відстій", 
    "нормальн", "смішно", "безглуздо", "дур", "незрозум", "стереотип", "упереджен"
]

# 🔹 Небезпечні слова (одразу стереотип/токс)
danger_words = [
    "вбити", "самогуб", "помирати", "застрелитись", "убити", "порізат", "травмуватись"
]

# ================== ФУНКЦІЇ ==================
def get_random_card(user_data):
    used_ids = user_data.get('used_cards', [])
    cursor.execute("SELECT id, text, image_path FROM cards WHERE id NOT IN ({seq}) ORDER BY RANDOM() LIMIT 1"
                   .format(seq=','.join('?'*len(used_ids))) if used_ids else "SELECT id, text, image_path FROM cards ORDER BY RANDOM() LIMIT 1",
                   used_ids if used_ids else ())
    row = cursor.fetchone()
    if row:
        return {"id": row[0], "text": row[1], "image_path": row[2]}
    return None

def get_tasks_for_card(card_id):
    cursor.execute("SELECT text FROM tasks WHERE card_id=?", (card_id,))
    rows = cursor.fetchall()
    return [r[0] for r in rows] if rows else []

def check_answer(answer_text):
    text = answer_text.lower()

    if any(word in text for word in danger_words):
        return "STEREOTYPE"

    empathy_score = sum(1 for root in empathy_roots if root in text)
    stereotype_score = sum(1 for root in stereotype_roots if root in text)

    # якщо є стереотипи — вони важливіші
    if stereotype_score > empathy_score:
        return "STEREOTYPE"
    elif empathy_score > stereotype_score:
        return "EMPATHY"
    else:
        return "STEREOTYPE"

# ================== HANDLERИ ==================
def start(update, context):
    keyboard = [
        [InlineKeyboardButton("📜 Правила", callback_data='rules')],
        [InlineKeyboardButton("🎮 Почати гру", callback_data='start_game')]
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "🎲 Вітаємо гравця у грі «Взуй мої черевики»!\n\n"
        "Ця гра була створена з метою припинення булінгу серед дітей та підлітків. "
        "Ми хочемо допомогти краще зрозуміти, як можуть почуватися інші у скрутних "
        "та неприємних ситуаціях. Також наша гра спрямована на те, щоб знищити "
        "будь-які стереотипи!\n\n"
        "Перед початком у вас є вибір: або спочатку прочитати правила, "
        "або одразу починати гру. Оберіть відповідну кнопку знизу👇"
    )

    update.message.reply_text(text, reply_markup=reply_markup)


def button(update, context):
    query = update.callback_query
    query.answer()

    if query.data == "rules":

        text = (
            "📜 *Правила та інструкція до гри*\n\n"

            ">> Хід гри🤔 <<\n"
            "• Гравець читає ситуацію на картці (бот надсилає її як зображення або текст).\n"
            "• Гравець пропонує рішення – як підтримати героя.\n"
            "• Бот визначає: емпатичне це рішення чи стереотипне мислення.\n\n"

            ">> Як працюють фішки💜 <<\n"
            "• Фішка емпатії додається до лічильника.\n"
            "• Якщо відповідь стереотипна — додається фішка стереотипів.\n\n"

            ">> Прогрес у грі🗒️ <<\n"
            "• Гравець стартує на малому колі.\n"
            "• Коли гравець набирає 3 фішки емпатії:\n"
            "  «Ви перейшли на велике коло!»\n\n"

            ">> Команди гри👾 <<\n"
            "📊 /score — переглянути результати\n"
            "▶️ /next_card — наступна картка\n\n"

            ">> Завершення гри📊 <<\n"
            "Гра завершується, коли закінчуються всі картки.\n\n"

            ">> Ключові слова👁️ <<\n"
            "Використайте хоча б одне слово:\n"
            "💜 підтримка, допомога, розуміння, співчуття, турбота\n"
            "⚫ сам винен, перебільшення, дурниці, не ний\n\n"

            "Дякуємо за прочитання! Гарної гри 🎮"
        )
        query.message.reply_text(text)

def start_game(update, context):
    query = update.callback_query
    try:
        query.answer()
    except:
        pass
    send_card(update, context)

def send_card(update, context):
    card = get_random_card(context.user_data)
    if not card:
        # Кінець гри
        user_id = update.effective_user.id
        cursor.execute("SELECT empathy_points, stereotype_points FROM score WHERE user_id=?", (user_id,))
        row = cursor.fetchone()
        empathy, stereotype = row if row else (0, 0)

        # Текст кінця гри
        text = (
            "🎉 Гра завершена!\n\n"
            "Дякуємо за проходження гри «Взуй мої черевики».\n\n"
            f"💜 Емпатія: {empathy}\n"
            f"⚫ Стереотипи: {stereotype}\n\n"
            "Кожен вибір показує, як важливо розуміти інших.\n"
            "Дякуємо за участь 💜"
        )

        # Кнопки: рестарт та посилання на канал
        keyboard = [
            [InlineKeyboardButton("🔄 Почати знову", callback_data="restart_game")],
            [InlineKeyboardButton("🔥 Почни гру. Вийди з вогню", url="https://t.me/Labirint_istini")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # Відправка повідомлення
        if update.callback_query:
            update.callback_query.message.reply_text(text, reply_markup=reply_markup)
        else:
            update.message.reply_text(text, reply_markup=reply_markup)

        # Очистити використані картки та рахунок
        context.user_data['used_cards'] = []
        cursor.execute("UPDATE score SET empathy_points=0, stereotype_points=0 WHERE user_id=?", (user_id,))
        conn.commit()
        return


    # Зберігаємо картку як використану
    used = context.user_data.get('used_cards', [])
    used.append(card['id'])
    context.user_data['used_cards'] = used
    context.user_data['current_card'] = card

    # Відправка картки
    tasks = get_tasks_for_card(card['id'])
    context.user_data['current_tasks'] = tasks

    if card.get('image_path') and os.path.exists(os.path.join(BASE_DIR, card['image_path'])):
        photo_path = os.path.join(BASE_DIR, card['image_path'])
        caption = f"📖 Історія:\n\n{card['text']}"
        if update.callback_query:
            update.callback_query.message.reply_photo(photo=open(photo_path, 'rb'), caption=caption)
        else:
            update.message.reply_photo(photo=open(photo_path, 'rb'), caption=caption)
    else:
        text_msg = f"📖 Історія:\n\n{card['text']}"
        if update.callback_query:
            update.callback_query.message.reply_text(text_msg)
        else:
            update.message.reply_text(text_msg)

    if tasks:
        for t in tasks:
            if update.callback_query:
                update.callback_query.message.reply_text(f"❓ Завдання:\n{t}")
            else:
                update.message.reply_text(f"❓ Завдання:\n{t}")
                
def end_game(update, context):

    user_id = update.effective_user.id

    cursor.execute(
        "SELECT empathy_points, stereotype_points FROM score WHERE user_id=?",
        (user_id,)
    )

    row = cursor.fetchone()
    empathy = row[0] if row else 0
    stereotype = row[1] if row else 0

    text = (
        "🎉 Гра завершена!\n\n"
        "Дякуємо за проходження гри «Взуй мої черевики».\n\n"
        f"💜 Емпатія: {empathy}\n"
        f"⚫ Стереотипи: {stereotype}\n\n"
        "Кожен вибір показує, як важливо розуміти інших.\n"
        "Дякуємо за участь 💜"
    )

    keyboard = [
        [InlineKeyboardButton("🔄 Почати знову", callback_data="restart_game")],
        [InlineKeyboardButton("🔥 Почни гру. Вийди з вогню",
         url="https://t.me/Labirint_istini")]
    ]



    reply_markup = InlineKeyboardMarkup(keyboard)

    if update.callback_query:
        update.callback_query.message.reply_text(text, reply_markup=reply_markup)
    else:
        update.message.reply_text(text, reply_markup=reply_markup)

def restart_game(update, context):

    query = update.callback_query
    query.answer()

    user_id = query.from_user.id

    cursor.execute(
        "UPDATE score SET empathy_points=0, stereotype_points=0 WHERE user_id=?",
        (user_id,)
    )

    conn.commit()

    context.user_data["used_cards"] = []

    query.message.reply_text("🎮 Нова гра починається!")

    send_card(update, context)

def handle_answer(update, context):
    user_id = update.message.from_user.id
    answer = update.message.text

    if 'current_card' not in context.user_data:
        update.message.reply_text("Спочатку отримайте картку командою /start або /next_card")
        return

    result = check_answer(answer)

    cursor.execute("INSERT OR IGNORE INTO score (user_id) VALUES (?)", (user_id,))

    if result == "EMPATHY":
        cursor.execute("UPDATE score SET empathy_points = empathy_points + 1 WHERE user_id=?", (user_id,))
        update.message.reply_text("💜 Ваша відповідь проявляє емпатію!")
    else:
        cursor.execute("UPDATE score SET stereotype_points = stereotype_points + 1 WHERE user_id=?", (user_id,))
        update.message.reply_text("⚫ Ваша відповідь проявляє стереотип!")

    conn.commit()
    send_card(update, context)

def show_score(update, context):
    user_id = update.message.from_user.id
    cursor.execute("SELECT empathy_points, stereotype_points FROM score WHERE user_id=?", (user_id,))
    row = cursor.fetchone()
    empathy_points, stereotype_points = row if row else (0, 0)
    update.message.reply_text(f"💜 {empathy_points} | ⚫ {stereotype_points}")

# ================== ЗАПУСК ==================
updater = Updater(TOKEN, use_context=True)
dp = updater.dispatcher

dp.add_handler(CommandHandler("start", start))
dp.add_handler(CallbackQueryHandler(start_game, pattern='start_game'))
dp.add_handler(CommandHandler("score", show_score))
dp.add_handler(CommandHandler("next_card", send_card))
dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_answer))
dp.add_handler(CallbackQueryHandler(button))
dp.add_handler(CallbackQueryHandler(restart_game, pattern="restart_game"))

print("Бот запущений...")
updater.start_polling()
updater.idle()