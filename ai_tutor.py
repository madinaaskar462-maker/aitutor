from telegram import (
    Update,
    ReplyKeyboardMarkup,
    KeyboardButton,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)
from datetime import datetime
from typing import Dict, Set

# ========== НАСТРОЙКИ ==========

# 1. Сюда вставь свой токен от BotFather:
BOT_TOKEN = "8453796805:AAG-T7bu1ju2yIx5lHJrzGjE2BOr8HrA7g4"

# 2. Сюда позже вставим свой Telegram ID (пока оставь 0, см. команду /myid)
ADMIN_ID =  7935478482

# ========== БАЗОВОЕ РАСПИСАНИЕ ГРУППЫ ПО-12 ==========

SCHEDULE: Dict[str, list[str]] = {
    "понедельник": 
                  ["08:30 – Физическая культура, с/з", 
                  "10:05 – Математика (нечетная неделя), 310 каб. /  \n Русский язык (четная неделя), 310 каб.",
                   "11:40 – Физика, 214 каб."],
    "вторник":
                 ["08:30 – Казахский язык и литература (нечетная неделя), каб.: 308/305а / \n Иностранный язык (четная неделя), каб.: 306/316",
                  "10:05 – Информатика, каб.: 204/220", 
                  "11:40 – Химия, 315 каб.",
                  "13:05 – Кураторский час"],
    "среда": 
               ["08:30 – Казахский язык и литература, каб.: 308/305а", 
                "10:05 – История Казахстана, 311 каб.",
                "11:40 – География (нечетная неделя), 303 каб. / \n Графика и проектирование (четная неделя), каб.: 204/222"],
    "четверг": 
             ["08:30 – Начальная военная и технологическая подготовка (нечетная неделя), 318 каб. / \n Глобальные компетенции(четная неделя), 320 каб.", 
              "10:05 – Биология, 303 каб.",
              "11:40 – Иностранный язык, каб.: 306/316"],
    "пятница": 
              ["08:30 – Всемирная история, 311 каб.",
               "10:05 – Русский язык, 315 каб.",
               "11:40 – Физическая культура, с/з"],
    "суббота": ["08:30 – Русский язык, 315 каб.",
                "10:05 – Математика, 310 каб.",
                "11:40 – История Казахстана (нечетная неделя), 311 каб./ \n Информатика (четная неделя),каб.: 204/220"],
    "воскресенье": ["Выходной 😎"]

}

# Список пользователей, которые писали боту (кому шлём оповещения)
USERS: Set[int] = set()

# Замены: "YYYY-MM-DD" -> {номер_пары: текст_замены}
REPLACEMENTS: Dict[str, Dict[int, str]] = {}
LAST_ANNOUNCEMENT: str | None = None

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========

def get_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура с днями недели + 'Сегодня'."""
    rows = [
        [KeyboardButton("Понедельник"), KeyboardButton("Вторник")],
        [KeyboardButton("Среда"), KeyboardButton("Четверг")],
        [KeyboardButton("Пятница"), KeyboardButton("Суббота")],
        [KeyboardButton("Объявления"), KeyboardButton("Сегодня")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)


def dayname_from_weekday(idx: int) -> str:
    mapping = {
        0: "понедельник",
        1: "вторник",
        2: "среда",
        3: "четверг",
        4: "пятница",
        5: "суббота",
        6: "воскресенье",
    }
    return mapping.get(idx, "понедельник")


def format_schedule_for_dayname(day_name: str) -> list[str]:
    """Вернуть список пар по названию дня недели (без учёта замен)."""
    key = day_name.lower().strip()
    return SCHEDULE.get(key, [])


def format_schedule_for_date(dt: datetime) -> str:
    """
    Сформировать расписание на конкретную дату dt с учётом замен.
    Замены берём из REPLACEMENTS["YYYY-MM-DD"].
    """
    date_key = dt.strftime("%Y-%m-%d")
    weekday = dt.weekday()
    day_name = dayname_from_weekday(weekday)

    base_lessons = format_schedule_for_dayname(day_name)
    rep_for_day = REPLACEMENTS.get(date_key, {})

    lines = [f"📅 Расписание на {dt.strftime('%d.%m.%Y')} ({day_name.capitalize()}):\n"]

    if not base_lessons and not rep_for_day:
        lines.append("Пар нет 🙂")
        return "\n".join(lines)

    # Базовые пары + пометка замен
    for i, lesson in enumerate(base_lessons, start=1):
        if i in rep_for_day:
            lines.append(f"• {i}-я пара: 🔁 ЗАМЕНА → {rep_for_day[i]}")
        else:
            lines.append(f"• {i}-я пара: {lesson}")

    # Если есть замены для пар, которых нет в обычном расписании
    for pair_num, text in rep_for_day.items():
        if pair_num > len(base_lessons):
            lines.append(f"• {pair_num}-я пара: 🔁 ЗАМЕНА → {text}")

    return "\n".join(lines)


# ========== ОБРАБОТЧИКИ КОМАНД ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие + добавление пользователя в список рассылки."""
    user_id = update.effective_user.id
    USERS.add(user_id)

    text = (
        "Привет! Я бот с расписанием группы ПО-12 📚\n\n"
        "Команды:\n"
        "/day <день> – расписание на нужный день (например, /day понедельник)\n"
        "/today – расписание на сегодня с учётом замен\n"
        "/help – помощь\n"
        "/myid – узнать свой Telegram ID\n\n"
        "Можешь также пользоваться кнопками внизу, в том числе 'Сегодня'."
    )
    await update.message.reply_text(text, reply_markup=get_keyboard())


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await start(update, context)


async def day_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /day понедельник."""
    if not context.args:
        await update.message.reply_text(
            "Формат: /day <день_недели>\nНапример: /day вторник",
            reply_markup=get_keyboard(),
        )
        return

    day = " ".join(context.args)
    weekday_name = day.lower().strip()
    lessons = format_schedule_for_dayname(weekday_name)
    if not lessons:
        await update.message.reply_text(
            "Такого дня в расписании нет. Пиши, например: понедельник, вторник...",
            reply_markup=get_keyboard(),
        )
        return

    dt = datetime.now()
    # Для /day мы пока не учитываем дату, а только день недели, без замен
    lines = [f"📅 Расписание на {weekday_name.capitalize()}:\n"]
    for i, lesson in enumerate(lessons, start=1):
        lines.append(f"• {i}-я пара: {lesson}")

    await update.message.reply_text("\n".join(lines), reply_markup=get_keyboard())


async def today_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /today — учитывает замены на сегодняшнюю дату."""
    dt = datetime.now()
    text = format_schedule_for_date(dt)
    await update.message.reply_text(text, reply_markup=get_keyboard())


async def myid_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Узнать свой Telegram ID (чтобы вписать в ADMIN_ID)."""
    user_id = update.effective_user.id
    await update.message.reply_text(f"Твой Telegram ID: {user_id}")


async def set_replace_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Команда для администратора:
    /замена ДД.ММ номер_пары текст_замены

    Пример:
    /замена 09.12 2 Информатика (вместо МДК)
    """
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("Эту команду может использовать только преподаватель.")
        return

    if len(context.args) < 3:
        await update.message.reply_text(
            "Формат: /замена ДД.ММ номер_пары текст_замены\n"
            "Например:\n"
            "/замена 09.12 2 Информатика (вместо МДК)"
        )
        return

    date_str = context.args[0]   # "09.12"
    pair_str = context.args[1]   # "2"
    try:
        pair_num = int(pair_str)
    except ValueError:
        await update.message.reply_text("Номер пары должен быть числом. Пример: /замена 09.12 2 Информатика")
        return

    replacement_text = " ".join(context.args[2:])

    year = datetime.now().year
    try:
        dt = datetime.strptime(f"{date_str}.{year}", "%d.%m.%Y")
    except ValueError:
        await update.message.reply_text("Неверный формат даты. Пример: /замена 09.12 2 Информатика")
        return

    date_key = dt.strftime("%Y-%m-%d")

    if date_key not in REPLACEMENTS:
        REPLACEMENTS[date_key] = {}
    REPLACEMENTS[date_key][pair_num] = replacement_text

    # Формируем текст обновлённого расписания
    msg = format_schedule_for_date(dt)

    # Подтверждение тебе
    await update.message.reply_text(
        "✅ Замена сохранена. Обновлённое расписание на этот день:\n\n" + msg,
        reply_markup=get_keyboard(),
    )

    # Рассылка студентам
    notify_text = "🔔 Обновление расписания:\n\n" + msg
    for uid in list(USERS):
        try:
            await context.bot.send_message(chat_id=uid, text=notify_text)
        except Exception:
            # если пользователь заблокировал бота или ошибка — просто пропускаем
            continue
async def announce_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global LAST_ANNOUNCEMENT

    if update.effective_user.id != ADMIN_ID:
        await update.message.reply_text("Эту команду может использовать только преподаватель.")
        return

    if not context.args:
        await update.message.reply_text("Формат: /news текст_объявления\nПример: /news Завтра 2 пара отменена.")
        return

    text = " ".join(context.args)
    LAST_ANNOUNCEMENT = text

    msg = "📢 *Объявление:*\n" + text

    # подтверждение педагогу
    await update.message.reply_text("✅ Объявление сохранено и отправлено студентам.")

    # рассылка студентам
    for uid in list(USERS):
        try:
            await context.bot.send_message(chat_id=uid, text=msg, parse_mode="Markdown")
        except Exception:
            continue


# ========== ОБРАБОТКА ТЕКСТА (КНОПКИ) ==========

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    USERS.add(user_id)

    msg = update.message.text.strip()

    # 🔔 КНОПКА «ОБЪЯВЛЕНИЯ»
    if msg.lower() == "объявления":
        if LAST_ANNOUNCEMENT:
            await update.message.reply_text(
                "📢 Последнее объявление:\n" + LAST_ANNOUNCEMENT,
                reply_markup=get_keyboard()
            )
        else:
            await update.message.reply_text(
                "Пока объявлений нет 🙂",
                reply_markup=get_keyboard()
            )
        return

    # 👇 КНОПКА «СЕГОДНЯ»
    if msg.lower() == "сегодня":
        dt = datetime.now()
        text = format_schedule_for_date(dt)
        await update.message.reply_text(text, reply_markup=get_keyboard())
        return

    # 👇 ДНИ НЕДЕЛИ
    low = msg.lower()
    if low in SCHEDULE:
        lessons = format_schedule_for_dayname(low)
        lines = [f"📅 Расписание на {low.capitalize()}:\n"]
        for i, lesson in enumerate(lessons, start=1):
            lines.append(f"• {i}-я пара: {lesson}")
        await update.message.reply_text("\n".join(lines), reply_markup=get_keyboard())
        return

    # 👇 ВСЁ ОСТАЛЬНОЕ
    await update.message.reply_text(
        "Я понимаю дни недели, кнопку «Сегодня» и «Объявления».",
        reply_markup=get_keyboard(),
    )



# ========== ЗАПУСК БОТА ==========

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    # Команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("day", day_cmd))
    app.add_handler(CommandHandler("today", today_cmd))
    app.add_handler(CommandHandler("myid", myid_cmd))
    app.add_handler(CommandHandler("zamena", set_replace_cmd))
    app.add_handler(CommandHandler("news", announce_cmd))

    # Любой текст (кнопки и прочее)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    print("Бот запущен. Нажми Ctrl+C, чтобы остановить.")
    app.run_polling()


if __name__ == "__main__":
    main()












