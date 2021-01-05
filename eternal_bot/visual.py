import numpy as np
import seaborn as sb
import pandas as pd
import matplotlib.pyplot as plt
import datetime, logging

from eternal_bot.util import EternalBase
from eternal_bot.db import TBindedDB, TInterfaceDB

sb.set()

class TVisualizer(EternalBase):
    def __init__(self, workdir, context):
        super().__init__(context)
        self.workdir = workdir
        self.context = context

    def get_path(self, name):
        return self.workdir + "/%s%s.png" % (name, str(self.context.user_data["uid"]))

    def send_useless_plot(self):
        db = self.context.user_data["db"].connection()

        res = TInterfaceDB.get_all_statistics(db, uid = self.context.user_data["uid"])

        val = []
        param = []

        frmt = "%Y-%m-%d %H:%M:%S.%f"

        for (total, useful, domestic, sleep_id, begin, end) in res:
            if total != 0:
                useless = (total - useful - domestic)
                val.append(round(useless / total * 100.0, 1))
            else:
                val.append(100.0)
            tm = datetime.datetime.strptime(begin, frmt)
            y = "%02d.%02d" % (tm.month, tm.day)
            param.append(y)

        ax_size = (11.7,8.27)
        fig, ax = plt.subplots(figsize = ax_size)
        rate = max(1, len(param) // 7)
        x_rate = [i for i in range(len(param)) if i % rate  == 0]

        ax.xaxis.set_ticks(x_rate)

        lp = sb.lineplot(ax = ax, x = param, y = val)

        raw_time_now = datetime.datetime.utcnow()
        time_now = TInterfaceDB.time_cast(
            db,
            uid = self.context.user_data["uid"],
            t = raw_time_now
        )
        lp.set_title("Занимался хуйней %% \nот %02d.%02d.%04d\n" % (time_now.day, time_now.month, time_now.year))


        path = self.get_path("useless_plot")
        lp.get_figure().savefig(path)
        plt.close(fig)
        self.context.bot.send_photo(self.context.user_data["uid"], photo = open(path, "rb"))

    def send_useful_plot(self):
        db = self.context.user_data["db"].connection()

        res = TInterfaceDB.get_all_statistics(db, uid = self.context.user_data["uid"])

        val = []
        param = []

        frmt = "%Y-%m-%d %H:%M:%S.%f"

        for (total, useful, domestic, sleep_id, begin, end) in res:
            if total != 0:
                val.append(round(useful / total * 100.0, 1))
            else:
                val.append(0.0)
            tm = datetime.datetime.strptime(begin, frmt)
            y = "%02d.%02d" % (tm.month, tm.day)
            param.append(y)


        ax_size = (11.7,8.27)
        fig, ax = plt.subplots(figsize = ax_size)
        lp = sb.lineplot(ax = ax, x = param, y = val)

        rate = max(1, len(param) // 7)
        x_rate = [i for i in range(len(param)) if i % rate  == 0]

        ax.xaxis.set_ticks(x_rate)

        raw_time_now = datetime.datetime.utcnow()
        time_now = TInterfaceDB.time_cast(
            db,
            uid = self.context.user_data["uid"],
            t = raw_time_now
        )
        lp.set_title("Занимался полезными делами %% \nот %02d.%02d.%04d\n" % (time_now.day, time_now.month, time_now.year))

        path = self.get_path("useful_plot")
        lp.get_figure().savefig(path)
        plt.close(fig)
        self.context.bot.send_photo(self.context.user_data["uid"], photo = open(path, "rb"))

    def send_ask_task_heatmap(self):
        db = self.context.user_data["db"].connection()
        res = TInterfaceDB.get_all_ask_tasks(db, uid = self.context.user_data["uid"])
        frmt = "%Y-%m-%d %H:%M:%S.%f"
        cnt = dict()
        for i in range(0, 24):
            t = datetime.time(hour = i)
            cnt[t] = 0
        for x in res:
            ask_time = datetime.datetime.strptime(x[0], frmt).time()
            new_time = datetime.time(hour = ask_time.hour)
            #minute = ask_time.minute - ask_time.minute % 15)

            value = 1 if x[1] == 2 else 0
            if new_time in cnt:
                cnt[new_time] += value
            else:
                cnt[new_time] = value

        path = self.get_path("heatmap")

        frame = pd.DataFrame({
            "time": [str(date) for date in cnt],
            "value": [cnt[date] for date in cnt],
            "fake": [0 for x in cnt]
        })

        test = frame.pivot(index = "fake", columns = "time", values = "value")
        ax_size = (11.7,8.27)
        fig, ax = plt.subplots(figsize = ax_size)
        hm = sb.heatmap(test, fmt="g", cmap='viridis', ax = ax)
        ax.set_ylabel("")
        ax.set_xlabel("")

        raw_time_now = datetime.datetime.utcnow()
        time_now = TInterfaceDB.time_cast(
            db,
            uid = self.context.user_data["uid"],
            t = raw_time_now
        )
        hm.set_title("Распределение полезных дел по часам\nот %02d.%02d.%04d\n" % (time_now.day, time_now.month, time_now.year))

        hm.get_figure().savefig(path)
        plt.close(fig)
        self.context.bot.send_photo(self.context.user_data["uid"], photo = open(path, "rb"))

def get_test_plot(name):
    ax_size = (11.7,8.27)
    x = [0, 1, 2]
    y = [1, 2, 1]
    _, ax = plt.subplots(figsize = ax_size)
    plot = sb.lineplot(ax = ax, x = x, y = y)

    plot.get_figure().savefig(name)
