import os
import re
import asyncio
from logger import logger
from dotenv import load_dotenv
from collections import defaultdict
from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand, CallbackQuery
from aiogram.fsm.storage.memory import MemoryStorage

from aiogram import types
from utils import gigachat_call, get_temp, UserData

from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup

load_dotenv()

bot = Bot(token=os.environ.get("BOT_TOKEN"))
dp = Dispatcher(storage=MemoryStorage())


async def set_commands():
    commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/help", description="Показать справку"),
        BotCommand(command="/set_profile", description="Настроить профиль"),
        BotCommand(command="/profile", description="Показать профиль"),
        BotCommand(command="/log_water", description="Логировать воду. Пример: /log_water 500"),
        BotCommand(command="/log_food", description="Логировать еду. Пример: /log_food Булочка с маком"),
        BotCommand(command="/log_workout", description="Логировать тренировку. Пример: /log_workout жим лежа 10"),
        BotCommand(command="/check_progress", description="Проверить прогресс")
    ]
    await bot.set_my_commands(commands)
    logger.info("Команды бота установлены.")


# from utils import load_test_user_data
# user_data = defaultdict(load_test_user_data)

user_profiles = {}
user_data = defaultdict(UserData)
food_info = {}

class ProfileForm(StatesGroup):
    waiting_for_sex = State()
    waiting_for_weight = State()
    waiting_for_height = State()
    waiting_for_age = State()
    waiting_for_city = State()
    waiting_for_activity = State()
    waiting_for_water = State()
    waiting_for_calories = State()
    waiting_for_food_amout = State()


@dp.message(Command('start'))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал взаимодействие с ботом.")
    await message.answer("Привет! Я бот, который поможет тебе заполнить профиль. Используй /set_profile, чтобы начать.")


@dp.message(Command('help'))
async def cmd_help(message: types.Message):
    logger.info(f"Пользователь {message.from_user.id} запросил справку.")
    await message.answer("Вот список доступных команд:\n/start - Запустить бота\n/help - Показать справку\n/set_profile - Настроить профиль")


@dp.message(Command('profile'))
async def cmd_profile(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} запросил свой профиль.")

    profile = user_profiles.get(user_id)

    if profile:
        sex = profile['sex']
        weight = profile['weight']
        height = profile['height']
        age = profile['age']
        activity = profile['activity']
        city = profile['city']
        calories = profile['calories']
        cpa = profile['cpa']
        water = profile['water']

        profile_message = (
            f"📋 Ваш профиль:\n\n"
            f"👤 Пол: {sex}\n"
            f"⚖️ Вес: {weight} кг\n"
            f"📏 Рост:  {height} см\n"
            f"🎂 Возраст: {age} лет\n"
            f"🏃‍ Активность: {activity} мин/день\n"
            f"🌍 Город: {city}\n"
            f"🍏 Цель калорий: {calories} ккал/день\n"
            f"💪🏻 Приблизительный КФА: {cpa}\n"
            f"🧊 Цель воды: {water} мл/день"
        )

        await message.answer(profile_message)
    else:
        await message.answer("Ваш профиль не настроен. Используйте команду /set_profile, чтобы настроить его.")


@dp.message(Command('set_profile'))
async def cmd_set_profile(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    logger.info(f"Пользователь {user_id} начал настройку профиля.")

    sex_choices = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="Мужской", callback_data='мужской')],
            [types.InlineKeyboardButton(text="Женский", callback_data='женский')],
    ])

    await message.answer("Давайте начнем настройку профиля. Выберите свой пол:", reply_markup=sex_choices)
    await state.set_state(ProfileForm.waiting_for_sex)


@dp.callback_query(lambda call: True, ProfileForm.waiting_for_sex)
async def process_sex(call: CallbackQuery, state: FSMContext):
    user_id = call.message.from_user.id
    # sex = message.text.lower()
    sex = call.data

    logger.info(f"Пользователь {user_id} ввел пол: {sex}")
    await state.update_data(sex=sex)
    await call.message.answer(f"Ваш пол: {sex}. Сколько вы весите в килограммах?")
    await state.set_state(ProfileForm.waiting_for_weight)


@dp.message(ProfileForm.waiting_for_weight)
async def process_weight(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        weight = int(message.text)
        logger.info(f"Пользователь {user_id} ввел вес: {weight} кг.")
        await state.update_data(weight=weight)
        await message.answer(f"Ваш вес: {weight} кг. Какой ваш рост в сантиметрах?")
        await state.set_state(ProfileForm.waiting_for_height)
    except ValueError:
        await message.answer("Пожалуйста, укажите корректный вес в килограммах.")


@dp.message(ProfileForm.waiting_for_height)
async def process_height(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        height = int(message.text)
        logger.info(f"Пользователь {user_id} ввел рост: {height} см.")
        await state.update_data(height=height)
        await message.answer(f"Ваш рост: {height} см. Сколько вам лет?")
        await state.set_state(ProfileForm.waiting_for_age)
    except ValueError:
        await message.answer("Пожалуйста, укажите корректный рост в сантиметрах.")


@dp.message(ProfileForm.waiting_for_age)
async def process_age(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        age = int(message.text)
        logger.info(f"Пользователь {user_id} ввел возраст: {age} лет.")
        await state.update_data(age=age)
        await message.answer(f"Ваш возраст: {age} лет. В каком городе вы живете?")
        await state.set_state(ProfileForm.waiting_for_city)
    except ValueError:
        await message.answer("Пожалуйста, укажите корректный возраст.")


@dp.message(ProfileForm.waiting_for_city)
async def process_city(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    city = message.text.strip()
    logger.info(f"Пользователь {user_id} ввел город: {city}.")
    await state.update_data(city=city)
    await message.answer(f"Ваш город: {city}. Сколько минут в день вы тратите на активность? (Если активность отсутствует, укажите \"0\").")
    await state.set_state(ProfileForm.waiting_for_activity)


@dp.message(ProfileForm.waiting_for_activity)
async def process_activity(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        activity = int(message.text)
        cpa = min(1.2 + activity // 10 * 0.1, 2.4) # коэффициент физической активности, КФА
        logger.info(f"Пользователь {user_id} ввел уровень активности: {activity} минут.")
        await state.update_data(activity=activity)
        await state.update_data(cpa=cpa)
        await message.answer(f"Уровень активности: {activity} минут. Теперь укажите целевое количество воды в день в мл (или введите \"-\" для автоматического расчета).")
        await state.set_state(ProfileForm.waiting_for_water)
    except ValueError:
        await message.answer("Пожалуйста, укажите корректное количество минут активности.")


@dp.message(ProfileForm.waiting_for_water)
async def process_water(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_input = message.text

    if user_input.isdigit():
        water = int(user_input)
        logger.info(f"Пользователь {user_id} указал цель воды вручную: {water} мл.")
    else:
        logger.info(f"Пользователь {user_id} не указал цель воды, рассчитываем автоматически.")
        state_data = await state.get_data()
        weight = int(state_data.get('weight'))
        is_male = (state_data.get('sex').lower() == "мужской")
        activity = int(state_data.get('activity'))

        try:
            temperature = await get_temp(state_data.get('city'))
            logger.info(f"Температура в городе {state_data.get('city')} пользователя {user_id}: {temperature} градусов")
            is_heat = (temperature >= 25)
        except:
            logger.info(f"Для города {state_data.get('city')} пользователя {user_id} не удалось получить температуру")
            is_heat = False

        base_water = weight * 30 + 500 * is_male
        activity_water = (activity // 30) * 500
        weather_water = 500 * is_heat

        water = base_water + activity_water + weather_water

    await state.update_data(water=water)
    await message.answer(f"Ваша цель по воде: {water} мл/день.")

    await message.answer("Теперь укажите целевое количество калорий в день (введите одно число или \"-\" для автоматического расчета).")
    await state.set_state(ProfileForm.waiting_for_calories)


@dp.message(ProfileForm.waiting_for_calories)
async def process_calories(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    user_input = message.text
    state_data = await state.get_data()
    weight = int(state_data.get('weight'))
    height = int(state_data.get('height'))
    age = int(state_data.get('age'))
    sex = state_data.get('sex').lower()
    activity = int(state_data.get('activity'))
    cpa = state_data.get('cpa')

    if user_input.isdigit():
        calories = int(user_input)
        logger.info(f"Пользователь {user_id} указал цель калорий вручную: {calories}.")
    else:
        logger.info(f"Пользователь {user_id} не указал цель калорий, рассчитываем автоматически.")
        # На основе формулы Харриса-Бенедикта (добавлен КФА)
        if sex == "мужской":
            calories = int((66.5 + 13.75 * weight + 5.003 * height - 6.775 * age) * 1.1 * cpa)
        else:
            calories = int((655.1 + 9.563 * weight + 1.85 * height - 4.676 * age) * cpa)

    # Сохраняем профиль пользователя
    user_profiles[user_id] = {
        'sex': sex,
        'weight': weight,
        'height': height,
        'age': age,
        'activity': activity,
        'city': state_data.get('city'),
        'water': state_data.get('water'),
        'calories': calories,
        'cpa': cpa,
    }

    await message.answer(f"Ваша цель по калориям: {calories} ккал/день.")
    await message.answer("Ваш профиль настроен! Вы можете запросить его с помощью команды /profile.")
    await state.clear()


@dp.message(Command('log_water'))
async def cmd_log_water(message: types.Message):
    user_id = message.from_user.id
    try:
        amount = int(message.text.split()[1])
        user_data[user_id].append({"water": amount})
        profile = user_profiles.get(user_id)
        goal = profile.get("water")
        remaining = max(goal - user_data[user_id]["water"], 0)
        if remaining > 0:
            await message.answer(f"Записано: {amount} мл воды. Осталось: {remaining} мл до выполнения нормы.")
        else:
            await message.answer(f"Записано: {amount} мл воды. Поздравляю! Вы выполнили норму")
        return
    except Exception as e:
        logger.exception(f"Получено исключение:\n{e}")
        await message.answer("Пожалуйста, укажите количество воды в миллилитрах. Пример: /log_water 120")


@dp.message(Command('log_food'))
async def cmd_log_food(message: types.Message, state: FSMContext):
    try:
        food = message.text.split(maxsplit=1)[1]
        prompt = f"Сколько килокалорий содержится в 100 граммах {food}? Ответ дай только числом, без текста или единиц измерения."
        for retry in range(3):
            calories_info = await gigachat_call(prompt)
            if type(calories_info) is int:
                break

        if isinstance(calories_info, str):
            logger.exception(f"Получено исключение:\nНе удалось определить энергетическую ценность для указанного продукта: {food}")
            await message.answer(f"Не удалось определить энергетическую ценность для указанного продукта: {food}")
            return

        if food not in food_info:
            food_info[food] = calories_info
        await message.answer(f"{food.capitalize()} — {calories_info} ккал на 100 г. Сколько грамм вы употребили? (Запишите ответ одним числом)")
        await state.update_data(calories_info=calories_info, food=food)
        await state.set_state(ProfileForm.waiting_for_food_amout)

    except Exception as e:
        logger.exception(f"Получено исключение:\n{e}")
        await message.answer("Не удалось обработать ответ. Повторите вызов функции. Пример: /log_food яблоко")


@dp.message(ProfileForm.waiting_for_food_amout)
async def process_food_amount(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    state_data = await state.get_data()
    calories_info = state_data.get("calories_info")
    try:
        amount = int(message.text)
        total_calories = (calories_info * amount) / 100
        user_data[user_id].append({"calories_in": total_calories})

        profile = user_profiles.get(user_id)
        goal = profile.get("calories")
        remaining = max(goal - user_data[user_id]["calories_in"], 0)
        if remaining > 0:
            await message.answer(f"Записано: {total_calories:.2f} ккал. Осталось: {remaining} ккал до выполнения нормы.")
        else:
            await message.answer(f"Записано: {total_calories:.2f} ккал. Поздравляю! Вы выполнили норму")
        await state.clear()
        return

    except Exception as e:
        logger.exception(f"Получено исключение:\n{e}")
        await message.answer("Пожалуйста, укажите количество грамм одним числом.")


@dp.message(Command('log_workout'))
async def cmd_log_workout(message: types.Message):
    user_id = message.from_user.id
    try:
        parts = re.search(r"log_workout ([\w\s]+) (\d+)", message.text)
        action = parts.group(1).strip()
        duration = int(parts.group(2))

        prompt = f"Сколько килокалорий сжигается за 1 минуту {action}? Ответ дай только одним числом, без какого либо текста и единиц измерения."
        for retry in range(3):
            calories_info = await gigachat_call(prompt)
            if type(calories_info) is int:
                break

        if isinstance(calories_info, str):
            logger.exception(f"Получено исключение:\nНе удалось определить затраты энергии для тренировки: {action}")
            await message.answer(f"Не удалось определить затраты энергии для тренировки: {action}")
            return

        calories_burned = calories_info * duration
        user_data[user_id].append({"calories_out": calories_burned})
        additional_water = (duration // 30) * 200
        await message.answer(
            f"{action.capitalize()} {duration} минут — {calories_burned} ккал.\nДополнительно: выпейте {additional_water} мл воды."
        )
        return
    except Exception as e:
        logger.exception(f"Получено исключение:\n{e}")
        await message.answer("Пожалуйста, укажите тип тренировки и длительность в минутах. Пример: /log_workout приседания 15")


@dp.message(Command('check_progress'))
async def cmd_check_progress(message: types.Message):
    user_id = message.from_user.id
    profile = user_profiles.get(user_id, {})
    goal_water = profile.get("water")
    goal_calories = profile.get("calories")
    water_consumed = user_data[user_id]["water"]
    calories_in = user_data[user_id]["calories_in"]
    calories_out = user_data[user_id]["calories_out"]
    progress_message = (
        f"📊 Прогресс:\n\n"
        f"Вода:\n"
        f"- Выпито: {water_consumed}/{goal_water} мл.\n"
        f"- Осталось: {max(goal_water - water_consumed, 0)} мл.\n\n"
        f"Калории:\n"
        f"- Потреблено: {calories_in}/{goal_calories} ккал.\n"
        f"- Сожжено: {calories_out} ккал.\n"
        f"- Баланс: {abs(calories_in - calories_out)} ккал.\n"
    )

    img_files = user_data[user_id].draw_stat(goal_calories, goal_water)
    await message.answer(progress_message)
    for f in img_files:
        await bot.send_photo(message.chat.id, photo=types.FSInputFile(f))
        os.remove(f)

    return


@dp.message()
async def process_invalid_message(message: types.Message):
    await message.answer("Пожалуйста, используйте одну из указанных команд.")
    return


async def main():
    await set_commands()
    await dp.start_polling(bot)


if __name__ == '__main__':
    asyncio.run(main())
