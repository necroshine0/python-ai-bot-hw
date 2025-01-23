import os
import re
import aiohttp
import datetime
import pandas as pd
import seaborn as sns
from typing import Union
from logger import logger
from dotenv import load_dotenv
import matplotlib.pyplot as plt
from collections import defaultdict

from langchain_gigachat import GigaChat
from langchain.schema import SystemMessage

load_dotenv()

chat = GigaChat(credentials=os.environ.get("API_TOKEN"), verify_ssl_certs=False)


def get_today():
    return datetime.date.today().strftime("%Y-%m-%d")


class UserData(object):
    def __init__(self):
        self.data = defaultdict(
            lambda: {
                "water": [],
                "calories_in": [],
                "calories_out": [],
            }
        )
        self.sum_data = defaultdict(
            lambda: {
                "water": 0,
                "calories_in": 0,
                "calories_out": 0,
            }
        )
        self.last_date = None

    def append(self, d: dict, date=None):
        self.last_date = get_today()
        if date is None:
            date = self.last_date

        for key in ["water", "calories_in", "calories_out"]:
            val = d.get(key, 0)
            self.data[date][key].append(val)
            self.sum_data[date][key] += val

    def __getitem__(self, key: Union[int, str]):
        if key == -1:
            return self.data[self.last_date]
        elif key in ["water", "calories_in", "calories_out"]:
            return self.sum_data[self.last_date][key]
        else: # можно будет удалить
            assert isinstance(key, str)
            return self.data[key]

    def draw_stat(self, cal_food_norm, water_norm):
        last_df_cs = pd.DataFrame.from_dict(self[-1]).cumsum()
        sum_df = pd.DataFrame.from_dict(self.sum_data).T.rename_axis("date").reset_index()
        os.makedirs("img", exist_ok=True)

        # Накопительный график за последний день
        fig, ax1 = plt.subplots(figsize=(8, 4))
        sns.barplot(last_df_cs["calories_in"], ax=ax1, label="Потреблено ккал", color="crimson")
        sns.barplot(last_df_cs["calories_out"], ax=ax1, label="Сожжено ккал", color="maroon")
        ax1.axhline(cal_food_norm, color="red", label="Норма потребления в день", linestyle="--")
        ax1.set_xlabel("Номер записи в истории")

        ax2 = ax1.twinx()
        sns.lineplot(last_df_cs["water"], ax=ax2, linewidth=3, label="Потреблено воды", color="royalblue")
        ax2.axhline(water_norm, color="royalblue", label="Норма воды в день", linestyle="--", zorder=1)

        ax1.set_ylabel("ккал", color="maroon")
        ax2.set_ylabel("мл", color="navy")
        ax1.tick_params(axis='y', labelcolor="maroon")
        ax2.tick_params(axis='y', labelcolor="navy")

        lines_labels = [ax.get_legend_handles_labels() for ax in fig.axes]
        lines, labels = [sum(lol, []) for lol in zip(*lines_labels)]
        plt.title(f"Накопительная динамика прогресса за сегодня ({self.last_date})")
        plt.legend(lines, labels)

        plt.savefig("img/today_plot.png", bbox_inches="tight")
        files = ["img/today_plot.png"]

        if len(sum_df["date"]) > 1:
            fig, ax1 = plt.subplots(figsize=(8, 4))
            sns.barplot(sum_df, x="date", y="calories_in", ax=ax1, label="Потреблено ккал", color="crimson")
            sns.barplot(sum_df, x="date", y="calories_out", ax=ax1, label="Сожжено ккал", color="maroon")
            ax1.axhline(cal_food_norm, color="red", label="Норма потребления в день", linestyle="--")
            ax1.set_xlabel("Дата")
            ax1.tick_params(axis='x', labelrotation=15 * (len(sum_df["date"]) // 6))

            ax2 = ax1.twinx()
            sns.lineplot(sum_df, x="date", y="water", ax=ax2, linewidth=3, label="Потреблено воды", color="royalblue")
            ax2.axhline(water_norm, color="royalblue", label="Норма воды в день", linestyle="--", zorder=1)

            ax1.set_ylabel("ккал", color="maroon")
            ax2.set_ylabel("мл", color="navy")
            ax1.tick_params(axis='y', labelcolor="maroon")
            ax2.tick_params(axis='y', labelcolor="navy")

            lines_labels = [ax.get_legend_handles_labels() for ax in fig.axes]
            lines, labels = [sum(lol, []) for lol in zip(*lines_labels)]
            plt.title(f"Суммарная динамика прогресса за все время")
            plt.legend(lines, labels)

            plt.savefig("img/history_plot.png", bbox_inches="tight")
            files.append("img/history_plot.png")

        return files


async def gigachat_call(prompt):
    try:
        logger.info(f"Запрос к GigaChat: {prompt}")
        messages = [SystemMessage(content=prompt)]
        response = chat.invoke(messages)
        logger.info(f"Ответ от GigaChat: {response}")

        calories = re.search(r"(\d+)", response.content).group(1)
        return int(calories)

    except Exception as e:
        error_message = f"Ошибка при запросе GigaChat. Получен ответ:\n- {response}"
        logger.exception(error_message)
        return error_message


async def get_temp(city):
    api_key = os.environ.get("OWM_API_KEY")
    async with aiohttp.ClientSession() as session:
        payload = {"q": city}
        if api_key is not None:
            payload["appid"] = api_key

        async with session.get("http://api.openweathermap.org/geo/1.0/direct", params=payload) as response:
            response_data = await response.json()
            lat, lon = response_data[0]["lat"], response_data[0]["lon"]

        payload = {"lat": lat, "lon": lon, "units": "metric"}
        if api_key is not None:
            payload["appid"] = api_key

        async with session.get("https://api.openweathermap.org/data/2.5/weather", params=payload) as response:
            weather_data = await response.json()
            return weather_data["main"]["temp"]
