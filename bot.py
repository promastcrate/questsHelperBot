import logging
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.dispatcher.middlewares import BaseMiddleware
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils import executor
import requests
import os
from dotenv import load_dotenv

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
API_URL = os.getenv("API_URL")

bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)

class LoggingMiddleware(BaseMiddleware):
    async def on_pre_process_message(self, message: types.Message, data: dict):
        logger.info(f"Получено сообщение: {message.text} от пользователя {message.from_user.id}")

dp.middleware.setup(LoggingMiddleware())

main_menu = ReplyKeyboardMarkup(resize_keyboard=True).add(
    KeyboardButton("🏙️ Города"),
    KeyboardButton("🔍 Квесты"),
    KeyboardButton("📍 Локации"),
    KeyboardButton("👤 Гиды"),
    KeyboardButton("📝 Отзывы"),
    KeyboardButton("🆘 Поддержка")
)

class UserStates(StatesGroup):
    main_menu = State()
    cities = State()
    quests = State()
    locations = State()
    guides = State()
    reviews = State()
    support = State()
    add_review = State()
    add_review_quest = State()
    add_review_rating = State()
    add_review_comment = State()
    book_quest = State()

@dp.message_handler(commands=["start"], state="*")
async def start(message: types.Message):
    telegram_user_id = message.from_user.id

    response = requests.get(f"{API_URL}participants/by-telegram-id/{telegram_user_id}")
    if response.status_code != 404:
        participants = response.json()
        if participants:
            await message.answer("👋 Добро пожаловать обратно! Выберите действие:", reply_markup=main_menu)
    else:
        user_data = {
            "FirstName": message.from_user.first_name,
            "LastName": message.from_user.last_name or "",
            "TelegramUserID": telegram_user_id
        }
        response = requests.post(f"{API_URL}participants/", json=user_data)
        if response.status_code == 201:
            await message.answer("🎉 Добро пожаловать! Вы были успешно зарегистрированы. Выберите действие:",
                                 reply_markup=main_menu)
        else:
            await message.answer("❌ Произошла ошибка при регистрации. Попробуйте позже.")
            logger.error(f"Ошибка при создании участника: {response.status_code} - {response.text}")

    await UserStates.main_menu.set()

@dp.message_handler(state=UserStates.main_menu)
async def main_menu_handler(message: types.Message, state: FSMContext):
    if message.text == "🏙️ Города":
        await handle_cities(message, state)
    elif message.text == "🔍 Квесты":
        await handle_quests(message, state)
    elif message.text == "📍 Локации":
        await handle_locations(message, state)
    elif message.text == "👤 Гиды":
        await handle_guides(message, state)
    elif message.text == "📝 Отзывы":
        await handle_reviews(message, state)
    elif message.text == "🆘 Поддержка":
        await UserStates.support.set()
        await message.answer("📩 Напишите ваш вопрос:")

def paginate_text(text, chunk_size=1000):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def paginate_list(items, items_per_page=5):
    return [items[i:i + items_per_page] for i in range(0, len(items), items_per_page)]

async def get_unique_countries(api_url):
    try:
        response = requests.get(f"{api_url}cities/")
        if response.status_code != 200:
            return []
        cities = response.json()
        countries = list(set(city["Country"] for city in cities))
        return countries
    except Exception as e:
        logger.error(f"Ошибка при получении списка стран: {e}")
        return []

async def get_unique_cities(api_url):
    try:
        response = requests.get(f"{api_url}cities/")
        if response.status_code != 200:
            return []
        cities = response.json()
        unique_cities = list(set(city["CityName"] for city in cities))
        return unique_cities
    except Exception as e:
        logger.error(f"Ошибка при получении списка городов: {e}")
        return []

async def get_unique_quests(api_url):
    try:
        response = requests.get(f"{api_url}quests/")
        if response.status_code != 200:
            return []
        quests = response.json()
        unique_quests = [{'QuestID': quest['QuestID'], 'QuestName': quest['QuestName']} for quest in quests]
        return unique_quests
    except Exception as e:
        logger.error(f"Ошибка при получении списка квестов: {e}")
        return []

async def handle_cities(message: types.Message, state: FSMContext):
    await UserStates.cities.set()
    try:
        countries = await get_unique_countries(API_URL)
        if not countries:
            await message.answer("❌ Ошибка при получении списка стран. Попробуйте позже.")
            return
        keyboard = InlineKeyboardMarkup()
        for country in countries:
            keyboard.add(InlineKeyboardButton(country, callback_data=f"filter_country_{country}"))
        keyboard.add(InlineKeyboardButton("🌍 Показать все города", callback_data="filter_country_all"))

        await message.answer("🌍 Выберите страну для фильтрации городов:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка при обработке городов: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

async def handle_quests(message: types.Message, state: FSMContext):
    await UserStates.quests.set()
    try:
        cities = await get_unique_cities(API_URL)
        if not cities:
            await message.answer("❌ Ошибка при получении списка городов. Попробуйте позже.")
            return

        keyboard = InlineKeyboardMarkup()
        for city in cities:
            keyboard.add(InlineKeyboardButton(city, callback_data=f"filter_quest_city_{city}"))
        keyboard.add(InlineKeyboardButton("🌍 Показать все квесты", callback_data="filter_quest_city_all"))

        await message.answer("🔍 Выберите город для фильтрации квестов:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка при обработке квестов: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

async def handle_locations(message: types.Message, state: FSMContext):
    await UserStates.locations.set()
    try:
        cities = await get_unique_cities(API_URL)
        if not cities:
            await message.answer("❌ Ошибка при получении списка городов. Попробуйте позже.")
            return

        keyboard = InlineKeyboardMarkup()
        for city in cities:
            keyboard.add(InlineKeyboardButton(city, callback_data=f"filter_city_{city}"))
        keyboard.add(InlineKeyboardButton("🌍 Показать все локации", callback_data="filter_city_all"))

        await message.answer("📍 Выберите город для фильтрации локаций:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка при обработке локаций: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

async def handle_guides(message: types.Message, state: FSMContext):
    await UserStates.guides.set()
    try:
        response = requests.get(f"{API_URL}guides/")
        if response.status_code != 200:
            await message.answer("❌ Ошибка при получении списка гидов. Попробуйте позже.")
            return
        guides = response.json()
        guides_pages = paginate_list(guides)
        await state.update_data(pages=guides_pages, current_page=0, prefix="guide")
        await send_paginated_list(message.from_user.id, guides_pages[0], "guide", state)
    except Exception as e:
        logger.error(f"Ошибка при получении списка гидов: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

async def handle_reviews(message: types.Message, state: FSMContext):
    await UserStates.reviews.set()
    try:
        quests = await get_unique_quests(API_URL)
        if not quests:
            await message.answer("❌ Ошибка при получении списка квестов. Попробуйте позже.")
            return

        keyboard = InlineKeyboardMarkup()
        for quest in quests:
            keyboard.add(
                InlineKeyboardButton(quest['QuestName'], callback_data=f"filter_review_quest_{quest['QuestID']}"))
        keyboard.add(InlineKeyboardButton("🌍 Показать все отзывы", callback_data="filter_review_quest_all"))
        keyboard.add(InlineKeyboardButton("📝 Добавить отзыв", callback_data="add_review"))

        await message.answer("📝 Выберите квест для фильтрации отзывов или добавьте новый отзыв:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка при обработке отзывов: {e}")
        await message.answer("❌ Произошла ошибка. Попробуйте позже.")

async def send_paginated_list(user_id, items, prefix, state: FSMContext):
    keyboard = InlineKeyboardMarkup()
    for item in items:
        if prefix == "city":
            keyboard.add(InlineKeyboardButton(item["CityName"], callback_data=f"{prefix}_{item['CityID']}"))
        elif prefix == "quest":
            keyboard.add(InlineKeyboardButton(item["QuestName"], callback_data=f"{prefix}_{item['QuestID']}"))
        elif prefix == "location":
            keyboard.add(InlineKeyboardButton(item["LocationName"], callback_data=f"{prefix}_{item['LocationID']}"))
        elif prefix == "guide":
            keyboard.add(InlineKeyboardButton(f"{item['FirstName']} {item['LastName']}",
                                              callback_data=f"{prefix}_{item['GuideID']}"))
        elif prefix == "review":
            keyboard.add(InlineKeyboardButton(f"{item['Comment']} (Рейтинг: {item['Rating']})",
                                              callback_data=f"{prefix}_{item['ReviewID']}"))

    keyboard.row(
        InlineKeyboardButton("⬅️ Назад", callback_data=f"{prefix}_prev_page"),
        InlineKeyboardButton("Вперед ➡️", callback_data=f"{prefix}_next_page")
    )
    keyboard.add(InlineKeyboardButton("🏠 Назад в главное меню", callback_data="back_to_main_menu"))
    await bot.send_message(user_id, f"Выберите {prefix}:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.endswith("_prev_page") or c.data.endswith("_next_page"), state="*")
async def pagination_handler(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_page = data.get("current_page", 0)
    pages = data.get("pages")
    prefix = data.get("prefix")

    if callback_query.data.endswith("_prev_page"):
        current_page -= 1
    elif callback_query.data.endswith("_next_page"):
        current_page += 1

    if current_page < 0:
        current_page = 0
    elif current_page >= len(pages):
        current_page = len(pages) - 1

    await state.update_data(current_page=current_page)
    await send_paginated_list(callback_query.from_user.id, pages[current_page], prefix, state)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "back_to_main_menu", state="*")
async def back_to_main_menu_handler(callback_query: types.CallbackQuery, state: FSMContext):
    await UserStates.main_menu.set()
    await bot.send_message(callback_query.from_user.id, "🏠 Вы вернулись в главное меню.", reply_markup=main_menu)
    await callback_query.answer()

@dp.message_handler(state=UserStates.support)
async def support_message_handler(message: types.Message, state: FSMContext):
    user_message = message.text
    telegram_user_id = message.from_user.id

    participant_response = requests.get(f"{API_URL}participants/by-telegram-id/{telegram_user_id}/")
    if participant_response.status_code != 200:
        await message.answer("❌ Ошибка при получении данных пользователя. Попробуйте позже.")
        return

    participant = participant_response.json()
    participant_id = participant['ParticipantID']

    question_data = {
        "ParticipantID": participant_id,
        "QuestionText": user_message
    }
    response = requests.post(f"{API_URL}questions/", json=question_data)

    if response.status_code == 201:
        await message.answer("📩 Спасибо за ваш вопрос! Мы свяжемся с вами в ближайшее время.")
    else:
        await message.answer("❌ Произошла ошибка при отправке вопроса. Попробуйте позже.")

    await UserStates.main_menu.set()
    await message.answer("🏠 Выберите следующее действие:", reply_markup=main_menu)

@dp.callback_query_handler(lambda c: c.data.startswith("city_"), state=UserStates.cities)
async def city_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    city_id = callback_query.data.split("_")[1]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🏠 Назад в главное меню", callback_data="back_to_main_menu"))
    try:
        response = requests.get(f"{API_URL}cities/{city_id}/")
        if response.status_code != 200:
            await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении информации о городе.")
            return
        city = response.json()
        description_parts = paginate_text(city['Description'])
        await state.update_data(city_description=description_parts, current_page=0, city_name=city['CityName'])
        await send_paginated_text(callback_query.from_user.id, city['CityName'], description_parts, 0, state)
    except Exception as e:
        logger.error(f"Ошибка при получении информации о городе: {e}")
        await bot.send_message(callback_query.from_user.id, "❌ Произошла ошибка. Попробуйте позже.")
    finally:
        await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("quest_"), state=UserStates.quests)
async def quest_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    quest_id = callback_query.data.split("_")[1]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("📝 Записаться на квест", callback_data=f"book_quest_{quest_id}"))
    keyboard.add(InlineKeyboardButton("🏠 Назад в главное меню", callback_data="back_to_main_menu"))
    try:
        response = requests.get(f"{API_URL}quests/{quest_id}/")
        if response.status_code != 200:
            await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении информации о квесте.")
            return
        quest = response.json()
        description_parts = paginate_text(quest['Description'])
        await state.update_data(quest_description=description_parts, current_page=0, quest_name=quest['QuestName'])
        await send_paginated_text(callback_query.from_user.id, quest['QuestName'], description_parts, 0, state)
        await bot.send_message(callback_query.from_user.id, "Выберите действие:", reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка при получении информации о квесте: {e}")
        await bot.send_message(callback_query.from_user.id, "❌ Произошла ошибка. Попробуйте позже.")
    finally:
        await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("book_quest_"), state="*")
async def book_quest_handler(callback_query: types.CallbackQuery, state: FSMContext):
    quest_id = callback_query.data.split("_")[2]
    telegram_user_id = callback_query.from_user.id

    response = requests.get(f"{API_URL}participants/by-telegram-id/{telegram_user_id}/")
    if response.status_code != 200:
        await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении данных пользователя. Попробуйте позже.")
        return

    participant = response.json()
    participant_id = participant['ParticipantID']

    booking_data = {
        "QuestID": quest_id,
        "ParticipantID": participant_id
    }

    response = requests.post(f"{API_URL}quest-participants/", json=booking_data)
    if response.status_code == 201:
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🏠 Назад в главное меню", callback_data="back_to_main_menu"))

        await bot.send_message(callback_query.from_user.id, "✅ Вы успешно записаны на квест!", reply_markup=keyboard)
    else:
        await bot.send_message(callback_query.from_user.id, "❌ Произошла ошибка при записи на квест. Попробуйте позже.")
        logger.error(f"Ошибка при записи на квест: {response.status_code} - {response.text}")

    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("location_"), state=UserStates.locations)
async def location_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    location_id = callback_query.data.split("_")[1]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("🏠 Назад в главное меню", callback_data="back_to_main_menu"))
    try:
        response = requests.get(f"{API_URL}locations/{location_id}/")
        if response.status_code != 200:
            await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении информации о локации.")
            return
        location = response.json()
        description_parts = paginate_text(location['Description'])
        await state.update_data(location_description=description_parts, current_page=0,
                                location_name=location['LocationName'])
        await send_paginated_text(callback_query.from_user.id, location['LocationName'], description_parts, 0, state)
    except Exception as e:
        logger.error(f"Ошибка при получении информации о локации: {e}")
        await bot.send_message(callback_query.from_user.id, "❌ Произошла ошибка. Попробуйте позже.")
    finally:
        await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("guide_"), state=UserStates.guides)
async def guide_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    guide_id = callback_query.data.split("_")[1]

    try:
        response = requests.get(f"{API_URL}guides/{guide_id}/")
        if response.status_code != 200:
            await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении информации о гиде.")
            return
        guide = response.json()
        guide_info = (
            f"Имя: {guide['FirstName']}\n"
            f"Фамилия: {guide['LastName']}\n"
            f"Телефон: {guide['Phone']}\n"
            f"Email: {guide['Email']}\n"
            f"Опыт: {guide['Experience']} лет"
        )
        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🏠 Назад в главное меню", callback_data="back_to_main_menu"))

        await bot.send_message(callback_query.from_user.id, guide_info, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка при получении информации о гиде: {e}")
        await bot.send_message(callback_query.from_user.id, "❌ Произошла ошибка. Попробуйте позже.")
    finally:
        await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("filter_country_"), state=UserStates.cities)
async def filter_cities_by_country(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        country = callback_query.data.split("_")[-1]

        if country == "all":
            response = requests.get(f"{API_URL}cities/")
        else:
            response = requests.get(f"{API_URL}cities/?Country={country}")

        if response.status_code != 200:
            await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении списка городов.")
            return

        cities = response.json()
        cities_pages = paginate_list(cities)
        await state.update_data(pages=cities_pages, current_page=0, prefix="city")
        await send_paginated_list(callback_query.from_user.id, cities_pages[0], "city", state)
    except Exception as e:
        logger.error(f"Ошибка при фильтрации городов: {e}")
        await bot.send_message(callback_query.from_user.id, "❌ Произошла ошибка. Попробуйте позже.")
    finally:
        await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("filter_city_"), state=UserStates.locations)
async def filter_locations_by_city(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        city = callback_query.data.split("_")[-1]

        if city == "all":
            response = requests.get(f"{API_URL}locations/")
        else:
            cities_response = requests.get(f"{API_URL}cities/")
            if cities_response.status_code != 200:
                await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении списка городов.")
                return

            cities = cities_response.json()
            city_id = None
            for c in cities:
                if c["CityName"] == city:
                    city_id = c["CityID"]
                    break

            if not city_id:
                await bot.send_message(callback_query.from_user.id, "❌ Город не найден.")
                return

            response = requests.get(f"{API_URL}locations/?CityID={city_id}")

        if response.status_code != 200:
            await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении списка локаций.")
            return

        locations = response.json()
        locations_pages = paginate_list(locations)
        await state.update_data(pages=locations_pages, current_page=0, prefix="location")
        await send_paginated_list(callback_query.from_user.id, locations_pages[0], "location", state)
    except Exception as e:
        logger.error(f"Ошибка при фильтрации локаций: {e}")
        await bot.send_message(callback_query.from_user.id, "❌ Произошла ошибка. Попробуйте позже.")
    finally:
        await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("filter_quest_city_"), state=UserStates.quests)
async def filter_quests_by_city(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        city = callback_query.data.split("_")[-1]

        if city == "all":
            response = requests.get(f"{API_URL}quests/")
        else:
            cities_response = requests.get(f"{API_URL}cities/")
            if cities_response.status_code != 200:
                await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении списка городов.")
                return

            cities = cities_response.json()
            city_id = None
            for c in cities:
                if c["CityName"] == city:
                    city_id = c["CityID"]
                    break

            if not city_id:
                await bot.send_message(callback_query.from_user.id, "❌ Город не найден.")
                return

            response = requests.get(f"{API_URL}quests/?CityID={city_id}")

        if response.status_code != 200:
            await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении списка квестов.")
            return

        quests = response.json()
        quests_pages = paginate_list(quests)
        await state.update_data(pages=quests_pages, current_page=0, prefix="quest")
        await send_paginated_list(callback_query.from_user.id, quests_pages[0], "quest", state)
    except Exception as e:
        logger.error(f"Ошибка при фильтрации квестов: {e}")
        await bot.send_message(callback_query.from_user.id, "❌ Произошла ошибка. Попробуйте позже.")
    finally:
        await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("review_"), state=UserStates.reviews)
async def review_callback_handler(callback_query: types.CallbackQuery, state: FSMContext):
    review_id = callback_query.data.split("_")[1]

    try:
        response = requests.get(f"{API_URL}reviews/{review_id}/")
        if response.status_code != 200:
            await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении информации об отзыве.")
            return

        review = response.json()

        participant_id = review['ParticipantID']
        participant_response = requests.get(f"{API_URL}participants/{participant_id}/")
        if participant_response.status_code != 200:
            await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении информации об участнике.")
            return

        participant = participant_response.json()

        quest_id = review['QuestID']
        quest_response = requests.get(f"{API_URL}quests/{quest_id}/")
        if quest_response.status_code != 200:
            await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении информации о квесте.")
            return

        quest = quest_response.json()

        review_info = (
            f"Отзыв от: {participant['FirstName']} {participant['LastName']}\n"
            f"Квест: {quest['QuestName']}\n" 
            f"Рейтинг: {review['Rating']}\n"
            f"Комментарий: {review['Comment']}\n"
            f"Дата: {review['ReviewDate']}"
        )

        keyboard = InlineKeyboardMarkup()
        keyboard.add(InlineKeyboardButton("🏠 Назад в главное меню", callback_data="back_to_main_menu"))

        await bot.send_message(callback_query.from_user.id, review_info, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Ошибка при получении информации об отзыве: {e}")
        await bot.send_message(callback_query.from_user.id, "❌ Произошла ошибка. Попробуйте позже.")
    finally:
        await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("filter_review_quest_"), state=UserStates.reviews)
async def filter_reviews_by_quest(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        quest_id = callback_query.data.split("_")[-1]

        if quest_id == "all":
            response = requests.get(f"{API_URL}reviews/")
        else:
            response = requests.get(f"{API_URL}reviews/?QuestID={quest_id}")

        if response.status_code != 200:
            await bot.send_message(callback_query.from_user.id, "❌ Ошибка при получении списка отзывов.")
            return

        reviews = response.json()
        reviews_pages = paginate_list(reviews)
        await state.update_data(pages=reviews_pages, current_page=0, prefix="review")
        await send_paginated_list(callback_query.from_user.id, reviews_pages[0], "review", state)
    except Exception as e:
        logger.error(f"Ошибка при фильтрации отзывов: {e}")
        await bot.send_message(callback_query.from_user.id, "❌ Произошла ошибка. Попробуйте позже.")
    finally:
        await callback_query.answer()

async def send_paginated_text(user_id, title, text_parts, current_page, state: FSMContext):
    total_pages = len(text_parts)
    current_page = max(0, min(current_page, total_pages - 1))

    text = text_parts[current_page]
    keyboard = InlineKeyboardMarkup()
    if current_page > 0:
        keyboard.add(InlineKeyboardButton("⬅️ Назад", callback_data="prev_page"))
    if current_page < total_pages - 1:
        keyboard.add(InlineKeyboardButton("Вперед ➡️", callback_data="next_page"))
    keyboard.add(InlineKeyboardButton("🏠 Назад в главное меню", callback_data="back_to_main_menu"))

    if current_page == 0:
        message = await bot.send_message(user_id, f"{title}\n\n{text}", reply_markup=keyboard)
        await state.update_data(message_id=message.message_id)
    else:
        try:
            message_id = (await state.get_data()).get("message_id")
            await bot.edit_message_text(
                chat_id=user_id,
                message_id=message_id,
                text=f"{title}\n\n{text}",
                reply_markup=keyboard
            )
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            message = await bot.send_message(user_id, f"{title}\n\n{text}", reply_markup=keyboard)
            await state.update_data(message_id=message.message_id)

    await state.update_data(current_page=current_page)

@dp.callback_query_handler(lambda c: c.data in ["prev_page", "next_page"], state="*")
async def text_pagination_handler(callback_query: types.CallbackQuery, state: FSMContext):
    data = await state.get_data()
    current_page = data.get("current_page", 0)
    text_parts = data.get("city_description") or data.get("quest_description") or data.get("location_description")
    title = data.get("city_name") or data.get("quest_name") or data.get("location_name")

    if text_parts is None:
        await callback_query.answer("❌ Данные недоступны. Попробуйте ещё раз.")
        return

    if callback_query.data == "prev_page":
        current_page -= 1
    elif callback_query.data == "next_page":
        current_page += 1

    if current_page < 0:
        current_page = 0
    elif current_page >= len(text_parts):
        current_page = len(text_parts) - 1

    await send_paginated_text(callback_query.from_user.id, title, text_parts, current_page, state)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data == "add_review", state=UserStates.reviews)
async def add_review_start(callback_query: types.CallbackQuery, state: FSMContext):
    await UserStates.add_review_quest.set()

    quests = await get_unique_quests(API_URL)
    if not quests:
        await callback_query.message.answer("❌ Ошибка при получении списка квестов. Попробуйте позже.")
        return

    keyboard = InlineKeyboardMarkup()
    for quest in quests:
        keyboard.add(InlineKeyboardButton(quest['QuestName'], callback_data=f"select_quest_{quest['QuestID']}"))

    await callback_query.message.answer("📝 Выберите квест, для которого хотите оставить отзыв:", reply_markup=keyboard)
    await callback_query.answer()

@dp.callback_query_handler(lambda c: c.data.startswith("select_quest_"), state=UserStates.add_review_quest)
async def select_quest_for_review(callback_query: types.CallbackQuery, state: FSMContext):
    quest_id = callback_query.data.split("_")[2]
    await state.update_data(selected_quest_id=quest_id)
    await UserStates.add_review_rating.set()

    await callback_query.message.answer("📊 Введите рейтинг от 1 до 5:")
    await callback_query.answer()

@dp.message_handler(state=UserStates.add_review_rating)
async def enter_review_rating(message: types.Message, state: FSMContext):
    try:
        rating = int(message.text)
        if rating < 1 or rating > 5:
            await message.answer("📊 Рейтинг должен быть от 1 до 5. Попробуйте ещё раз.")
            return
    except ValueError:
        await message.answer("📊 Пожалуйста, введите число от 1 до 5.")
        return

    await state.update_data(rating=rating)
    await UserStates.add_review_comment.set()

    await message.answer("📝 Введите комментарий к отзыву:")

@dp.message_handler(state=UserStates.add_review_comment)
async def enter_review_comment(message: types.Message, state: FSMContext):
    comment = message.text
    data = await state.get_data()
    quest_id = data.get("selected_quest_id")
    rating = data.get("rating")

    telegram_user_id = message.from_user.id

    response = requests.get(f"{API_URL}participants/by-telegram-id/{telegram_user_id}/")
    if response.status_code != 200:
        await message.answer("❌ Ошибка при получении данных пользователя. Попробуйте позже.")
        return

    participant = response.json()
    participant_id = participant['ParticipantID']

    review_data = {
        "QuestID": quest_id,
        "ParticipantID": participant_id,
        "Rating": rating,
        "Comment": comment
    }

    response = requests.post(f"{API_URL}reviews/", json=review_data)
    if response.status_code == 201:
        await message.answer("✅ Отзыв успешно добавлен!")
    else:
        await message.answer("❌ Произошла ошибка при добавлении отзыва. Попробуйте позже.")
        logger.error(f"Ошибка при добавлении отзыва: {response.status_code} - {response.text}")

    await UserStates.main_menu.set()
    await message.answer("🏠 Выберите следующее действие:", reply_markup=main_menu)

if __name__ == "__main__":
    logger.info("Запуск бота...")
    executor.start_polling(dp, skip_updates=True)