import datetime, math

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from eternal_bot.db import TBindedDB, TInterfaceDB
from eternal_bot.util import EternalBase

from eternal_bot.interaction import TBindedInlineButton
from eternal_bot.monitoring import TInspector

class IMessageBlock(EternalBase):
    def __init__(self, context):
        super().__init__(context)
        self.created_time = datetime.datetime.utcnow()

    def render(self, context):
        pass

    def send(self, context):
        out = self.render(context)
        out["chat_id"] = context.user_data["uid"]
        context.bot.send_message(**out)

class TWorkReminder(IMessageBlock):
    class TWorkRecord:
        def __init__(self, name):
            self.name = name
            self.begin = datetime.datetime.utcnow()
            self.end = None

        def close(self):
            self.end = datetime.datetime.utcnow()
    class TWorkConfirm(IMessageBlock):
        def __init__(self, context):
            super().__init__(context)

        def reset(self, update, context):
            context.user_data["work"]["status"] = "working"
            context.bot.send_message(context.user_data["uid"], text = "ок")

        def render(self, context):
            ibm = context.user_data["inline_button_manager"]   
            
            out = dict()
            text = (
                    "Все еще занят?\n"
                    "Твоя задача: %s"
            ) % context.user_data["work"]["work_list"][-1].name
            
            button_yes = TBindedInlineButton(
                InlineKeyboardButton(text = "Да", callback_data = ""),
                self.reset
            )
            
            reply_markup = InlineKeyboardMarkup(
                inline_keyboard = [
                    [
                        button_yes.button
                    ]
                ]
            )

            ibm.add_button(button_yes)

            out["text"] = text
            out["reply_markup"] = reply_markup
            return out

    def __init__(self, context):
        super().__init__(context)

    def remind(self, ctx):
        context = ctx.job.context
        if context.user_data["work"]["status"] == "working":
            context.user_data["work"]["status"] = "nothing"
            block = TWorkReminder.TWorkConfirm(context)
            block.send(context)
        else:
            context.user_data["state_controller"].change_state("spare")

    def set_reminder(self, update, context):
        update.callback_query.message.reply_text(text = "засекаю")
        interval = int(update.callback_query.data.split("@")[1])
        r_job = context.job_queue.run_repeating(self.remind, interval, context = context)
        context.user_data["work"]["status"] = "working"
        context.user_data["inspector"].add_job(TInspector.TJob(r_job, "work"))
        context.user_data["inspector"].toogle_job_by_key("work", enable = True)
        

    def render(self, context):
        ibm = context.user_data["inline_button_manager"]
        
        out = dict()
        text = "Через сколько напомнить?"
        button_15m = TBindedInlineButton(
                InlineKeyboardButton(text = "15 мин", callback_data = str(15 * 60)),
                self.set_reminder
        )
        button_30m = TBindedInlineButton(
                InlineKeyboardButton(text = "30 мин", callback_data = str(30 * 60)),
                self.set_reminder
        )
        button_1h = TBindedInlineButton(
                InlineKeyboardButton(text = "1 час", callback_data = str(60 * 60)),
                self.set_reminder
        )
        button_2h = TBindedInlineButton(
                InlineKeyboardButton(text = "2 часа", callback_data = str(2 * 60 * 60)),
                self.set_reminder
        )

        reply_markup = InlineKeyboardMarkup(
            inline_keyboard = [
                [
                    button_15m.button, button_30m.button
                ],
                [
                    button_1h.button, button_2h.button
                ]
            ]
        )
        
        ibm.add_button(button_15m)
        ibm.add_button(button_30m)
        ibm.add_button(button_1h)
        ibm.add_button(button_2h)

        out["text"] = text
        out["reply_markup"] = reply_markup

        return out

class TVisualBlock(IMessageBlock):
    def __init__(self, context):
        super().__init__(context)

    def send(self, context):
        context.user_data["visualizer"].send_ask_task_heatmap()
        context.user_data["visualizer"].send_useful_plot()
        context.user_data["visualizer"].send_useless_plot()

class THelpBlock(IMessageBlock):
    def __init__(self, context):
        super().__init__(context)

    def render(self, context):
        out = dict()
        out["text"] = (
            "/start - запустить\n"
            "/stop  - остановить\n"
            "/help  - это сообщение\n"
        )
        return out

class TStatisticsBlock(IMessageBlock):
    def __init__(self, context):
        super().__init__(context)

    def render(self, context):
        out = dict()
        
        day_begin = context.user_data["sleep_manager"]["begin"]
        time_now = datetime.datetime.utcnow()

        db = context.user_data["db"].connection()
        (total, useful, domestic, useless) = TInterfaceDB.calc_statistics(
            db,
            uid = context.user_data["uid"],
            begin = context.user_data["sleep_manager"]["begin"],
            end = time_now
        )
        text = (
               f"Статистика:\n\n"
               f"Всего запросов: {total}\n"
               f"Занимался делом: {useful}\n"
               f"Бытовые дела: {domestic}\n"
               f"Страдал хуйней: {useless}\n"
        )

        text += "\n"
        
        if total < 1:
            text += "Я толком не поспрашивал...\n"
        else:
            text += "Процент полезных дел: %s%%\n" % round(((useful / total) * 100.0), 2)
            text += "Процент страдания хуйней: %s%%\n" % round(((useless / total) * 100.0), 2)
        
        text += "\n"
        
        total_delta = datetime.timedelta()

        for x in context.user_data["work"]["work_list"]:
            delta = x.end - x.begin
            total_delta += delta
            pretty_time = str(delta).split(".")[0]
            text += f"Делал {x.name} на протяжении\n{pretty_time}\n"
        
        text += "\n"

        text += "Общее время именованых дел:\n%s\n" % str(total_delta).split(".")[0]
        
        out["text"] = text
        
        return out

class TSleepChecker(IMessageBlock):
    def __init__(self, context, interval):
        super().__init__(context)

    def still_awake(self, update, context):
        if context.user_data["sleep_manager"]["status"] != "sleepy":
            self.logger.debug("not sleepy")
            return
        self.logger.debug("pressed well")
        context.user_data["sleep_manager"]["status"] = "awake"
        time_now = datetime.datetime.utcnow()
        db = context.user_data["db"].connection()
        TInterfaceDB.update_sleep_by_begin(
            db,
            uid = context.user_data["uid"],
            key_begin = context.user_data["sleep_manager"]["begin"],
            begin = time_now,
            end = time_now
        )
        context.user_data["sleep_manager"]["begin"] = time_now
        context.bot.send_message(context.user_data["uid"], "понятно") 
    
    def wake_up(self, ctx):
        context = ctx.job.context
        context.bot.send_message(context.user_data["uid"], "Ержан, проснись")

    def render(self, context):
        ibm = context.user_data["inline_button_manager"]
        out = dict()
        if context.user_data["sleep_manager"]["status"] == "awake":
            context.user_data["sleep_manager"]["status"] = "sleepy"
            out["text"] = "Спишь?"

            button_no = TBindedInlineButton(
                InlineKeyboardButton(text = "Нет", callback_data = ""),
                self.still_awake
            )

            ibm.add_button(button_no)

            reply_markup = InlineKeyboardMarkup(
                inline_keyboard = [
                    [
                        button_no.button
                    ]
                ],
                resize_keyboard = True
            )

            out["reply_markup"] = reply_markup

            self.logger.debug("Well, we will wait")
        elif context.user_data["sleep_manager"]["status"] == "sleepy":
            context.user_data["sleep_manager"]["status"] = "sleeping" 
            context.user_data["inspector"].toogle_job_by_key("sleep", enable = False)

            out["text"] = None
            alarm = context.job_queue.run_repeating(
                self.wake_up,
                context.user_data["config"]["sleep_manager"]["alarm_rate"],

                context = context,
                first = context.user_data["config"]["sleep_manager"]["sleep_time"]
            )
            
            context.user_data["inspector"].add_job(TInspector.TJob(alarm, "alarm"))
            context.user_data["inspector"].toogle_job_by_key("alarm", enable = True)
            
            self.logger.debug("You are done...")
        return out

class TAskTask(IMessageBlock):
    def __init__(self, context, interval): 
        super().__init__(context)
        self.used = False 
        
        self.interval = interval

    def common(self, update, context, result):
        if not self.used:
            time_now = datetime.datetime.utcnow()
            delta = time_now - self.created_time
            
            if delta.seconds >= self.interval:
                text = "Поздно..."
            else:
                if result == 2:
                    text = "заебок"
                elif result == 1:
                    text = "норм"
                elif result == 0:
                    text = "хуево"

                db = context.user_data["db"].connection()
                TInterfaceDB.update_ask_task_by_time(
                    db,
                    uid = context.user_data["uid"],
                    key_time = self.created_time,
                    ask_time = time_now,
                    value = result
                )
                
                (total, useful, domestic, useless) = TInterfaceDB.calc_statistics(
                    db,
                    uid = context.user_data["uid"],
                    begin = context.user_data["sleep_manager"]["end"],
                    end = time_now
                )

                TInterfaceDB.update_statistics_by_sleep(
                    db,
                    sleep_id = context.user_data["sleep_manager"]["sleep_id"],
                    total = total,
                    useful = useful,
                    domestic = domestic
                )
                

            self.used = True

            update.effective_message.reply_text(
                text = text
            )
        else:
           self.logger.debug("ask task used") 
        

    def useful_callback(self, update, context):
        self.common(update, context, 2)

    def domestic_callback(self, update, context):
        self.common(update, context, 1)
    def useless_callback(self, update, context):
        self.common(update, context, 0)

    def render(self, context):
        out = dict()
        
        out["text"] = "Че делаешь?"
        
        ibm = context.user_data["inline_button_manager"] 

        button_useful = TBindedInlineButton(
            InlineKeyboardButton(text = "Полезное", callback_data = ""),
            self.useful_callback
        )

        button_domestic = TBindedInlineButton(
            InlineKeyboardButton(text = "Бытовое", callback_data = ""),
            self.domestic_callback
        )
        
        button_useless = TBindedInlineButton(
            InlineKeyboardButton(text = "Хуйню", callback_data = ""),
            self.useless_callback
        )

        ibm.add_button(button_useful)
        ibm.add_button(button_useless)
        ibm.add_button(button_domestic)

        reply_markup = InlineKeyboardMarkup(
            inline_keyboard = [
                [
                    button_useful.button,
                    button_domestic.button,
                    button_useless.button
                ]
            ],
            resize_keyboard = True
        ) 

        out["reply_markup"] = reply_markup

        return out
