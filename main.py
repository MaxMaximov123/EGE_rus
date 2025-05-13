import telebot
from telebot import types
import random
import re
from static import tasks_dict

TOKEN = '7572421598:AAGrs8X7bJdEwdTEg1nrbmMK-pceKFsSWiE'
bot = telebot.TeleBot(TOKEN)


user_cache = {}


def normalize_text(text: str) -> str:
    text = text.lower().replace('ё', 'е')
    text = re.sub(r'\(.*?\)', '', text)
    return text.strip()


def main_menu(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    buttons = [types.KeyboardButton(f"Задание {i}") for i in ['9', '10', '11', '12', '14']]

    for i in range(0, len(buttons) - 1, 2):
        markup.add(buttons[i], buttons[i + 1])
    if len(buttons) % 2 != 0:
        markup.add(buttons[-1])

    bot.send_message(message.chat.id, "Выберите задание:", reply_markup=markup)


@bot.message_handler(commands=['start'])
def handle_start(message):
    main_menu(message)


@bot.message_handler(func=lambda m: m.text and m.text.startswith("Задание "))
def select_task(message):
    user_id = message.chat.id
    task_number = message.text.split()[-1]

    if task_number not in tasks_dict:
        bot.send_message(user_id, "Такого задания нет.")
        return

    words_pool = list(tasks_dict[task_number].keys())
    random.shuffle(words_pool)

    user_cache[user_id] = {
        "task": task_number,
        "pool": words_pool,
        "correct": 0,
        "incorrect": 0,
        "errors": [],
        "mode": "full",  # full или errors
        "total": len(words_pool),
        "current_index": 0
    }

    # Отображаем клавиатуру только при запуске режима
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Получить результаты"), types.KeyboardButton("Назад"))
    bot.send_message(user_id, f"Вы выбрали задание {task_number}", reply_markup=markup)

    send_next_question(message)


def send_next_question(message):
    user_id = message.chat.id
    user_data = user_cache.get(user_id)

    if not user_data or not user_data['pool']:
        show_results(message)
        return

    current_word = user_data['pool'].pop(0)
    user_data['current'] = current_word
    user_data['current_index'] += 1

    i = user_data['current_index']
    n = user_data['total']
    question_text = f"{i}/{n}. Как пишется: {current_word}?"

    if user_data["task"] == "14":
        # Для задания 14 показываем кнопки каждый раз
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Слитно"), types.KeyboardButton("Раздельно"))
        markup.add(types.KeyboardButton("Получить результаты"), types.KeyboardButton("Назад"))
        bot.send_message(user_id, question_text, reply_markup=markup)
    else:
        # Для других заданий — без клавиатуры
        bot.send_message(user_id, question_text)

@bot.message_handler(func=lambda m: m.text and m.text.lower() == "назад")
def back_to_main_menu(message):
    user_cache.pop(message.chat.id, None)
    main_menu(message)


@bot.message_handler(func=lambda m: m.text and m.text.lower() == "получить результаты")
def early_finish(message):
    show_results(message)


def show_results(message):
    user_id = message.chat.id
    user_data = user_cache.get(user_id)

    if not user_data:
        bot.send_message(user_id, "Нет активного задания.")
        return

    correct = user_data["correct"]
    incorrect = user_data["incorrect"]

    bot.send_message(user_id, f"✅ Правильных: {correct}\n❌ Неправильных: {incorrect}")

    if user_data["errors"]:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.add(types.KeyboardButton("Показать ошибки"), types.KeyboardButton("Назад"))
        bot.send_message(user_id, "Хотите посмотреть ошибки?", reply_markup=markup)
    else:
        bot.send_message(user_id, "Отлично! Все задания выполнены правильно ✅")
        user_cache.pop(user_id, None)
        main_menu(message)


@bot.message_handler(func=lambda m: m.text and m.text.lower() == "показать ошибки")
def show_errors(message):
    user_id = message.chat.id
    user_data = user_cache.get(user_id)

    if not user_data or not user_data["errors"]:
        bot.send_message(user_id, "Ошибок не найдено.")
        return

    msg = "\n".join(
        [f"🔻 {wrong} → {correct}" for wrong, correct in user_data["errors"]]
    )
    bot.send_message(user_id, "Ваши ошибки:\n" + msg)

    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add(types.KeyboardButton("Исправить ошибки"), types.KeyboardButton("Назад"))
    bot.send_message(user_id, "Хотите исправить ошибки?", reply_markup=markup)


@bot.message_handler(func=lambda m: m.text and m.text.lower() == "исправить ошибки")
def retry_errors(message):
    user_id = message.chat.id
    old_data = user_cache.get(user_id)

    if not old_data or not old_data["errors"]:
        bot.send_message(user_id, "Нет ошибок для исправления.")
        return

    new_pool = [e[0] for e in old_data["errors"]]
    random.shuffle(new_pool)

    user_cache[user_id] = {
        "task": old_data["task"],
        "pool": new_pool,
        "correct": 0,
        "incorrect": 0,
        "errors": [],
        "mode": "errors",
        "total": len(new_pool),
        "current_index": 0
    }

    send_next_question(message)


@bot.message_handler(func=lambda m: True)
def handle_answer(message):
    user_id = message.chat.id
    user_data = user_cache.get(user_id)

    if not user_data or 'current' not in user_data:
        bot.send_message(user_id, "Сначала выберите задание.")
        return

    current_word = user_data["current"]
    correct_answer = tasks_dict[user_data["task"]][current_word]
    normalized_correct = normalize_text(correct_answer)

    if user_data["task"] == "14":
        if message.text.lower() == "слитно" and " " not in normalized_correct:
            user_data["correct"] += 1
            bot.send_message(user_id, f"✅ Верно! Слово: {correct_answer}")
        elif message.text.lower() == "раздельно" and " " in normalized_correct:
            user_data["correct"] += 1
            bot.send_message(user_id, f"✅ Верно! Слово: {correct_answer}")
        else:
            user_data["incorrect"] += 1
            user_data["errors"].append((current_word, correct_answer))
            bot.send_message(user_id, f"❌ Неверно. Правильный ответ: {correct_answer}")
    else:
        expected_letter = None
        missing = re.search(r'\.{2,}', current_word)
        if missing:
            idx = missing.start()
            if idx < len(correct_answer):
                expected_letter = correct_answer[idx]

        normalized_user = normalize_text(message.text)

        if normalized_user == normalize_text(correct_answer):
            user_data["correct"] += 1
            bot.send_message(user_id, f"✅ Верно! Слово: {correct_answer}")
        elif expected_letter and len(normalized_user) == 1 and normalized_user == expected_letter.lower():
            user_data["correct"] += 1
            bot.send_message(user_id, f"✅ Верно! Слово: {correct_answer}")
        else:
            user_data["incorrect"] += 1
            user_data["errors"].append((current_word, correct_answer))
            if expected_letter:
                bot.send_message(user_id, f"❌ Неверно. Правильная буква: {expected_letter}, слово: {correct_answer}")
            else:
                bot.send_message(user_id, f"❌ Неверно. Правильное слово: {correct_answer}")

    send_next_question(message)


bot.polling(none_stop=True)