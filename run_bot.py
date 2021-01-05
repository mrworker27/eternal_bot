import datetime, logging
import sqlite3

from collections import namedtuple

from telegram import Update, User
from telegram import ReplyKeyboardMarkup, KeyboardButton
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

from telegram.ext import Updater
from telegram.ext import CallbackContext, MessageHandler, CommandHandler, CallbackQueryHandler, Filters

from eternal_bot.visual import TVisualizer, get_test_plot
from eternal_bot.db import TBindedDB, TInterfaceDB
from eternal_bot.util import TBindedLogger, TDate
from eternal_bot.interaction import TBindedInlineButton, TInlineButtonManager
from eternal_bot.monitoring import TInspector, TStateController
from eternal_bot.blocks import TAskTask, TSleepChecker, TStatisticsBlock, TWorkReminder, TVisualBlock, THelpBlock

import settings

class TSleepState(TStateController.IState):
    def __init__(self, name):
        super().__init__(name)
    
    @classmethod
    def basic_keyboard(cls):
        keyboard = [
            [
                KeyboardButton(text = "Графики")
            ],
            [
                KeyboardButton(text = "Я проснулся")
            ]
        ]
        return keyboard
    
    def send_task(self, ctx):
        context = ctx.job.context
        task = TSleepChecker(context, context.user_data["config"]["sleep_manager"]["interval"])
        out = task.render(context)
        if "text" in out and out["text"] is not None:
            context.bot.send_message(context.user_data["uid"], **out)
        else:
            logger = TBindedLogger.get_logger(context.user_data["uid"])
            logger.debug("Sleep")
    
    def reset_task(self, context):
        inspector = context.user_data["inspector"]
        inspector.remove_job_by_key("sleep")
        job = context.job_queue.run_repeating(
            self.send_task,
            context.user_data["config"]["sleep_manager"]["interval"],
            context = context
        )
        inspector.add_job(TInspector.TJob(job, "sleep"))
    
    def enable(self, context):
        logger = TBindedLogger.get_logger(context.user_data["uid"])
        logger.info("Sleep enable") 
 
        block = TStatisticsBlock(context)
        out = block.render(context)
        
        reply_markup = ReplyKeyboardMarkup(
            keyboard = TSleepState.basic_keyboard(),
            resize_keyboard = True
        )
        
        context.user_data["work"]["work_list"] = []

        out["reply_markup"] = reply_markup 
        
        context.bot.send_message(context.user_data["uid"], **out)
        if context.user_data["sleep_manager"]["status"] != "sleeping":
            TSleepState.sleep(context)

    @classmethod
    def sleep_statistics(cls, context):
        db = context.user_data["db"].connection()
        (begin_raw, end_raw, _id) = TInterfaceDB.get_awake_by_end(
            db,
            uid = context.user_data["uid"],
            end = context.user_data["sleep_manager"]["begin"]
        )

        (total, useful, domestic, useless) = TInterfaceDB.calc_statistics(
            db,
            uid = context.user_data["uid"],
            begin = begin_raw,
            end = end_raw
        )

        TInterfaceDB.update_statistics_by_sleep(
            db,
            sleep_id = _id,
            total = total,
            useful = useful,
            domestic = domestic
        )
        
        
        begin_db = TDate.str_to_date(begin_raw)
        end_db = TDate.str_to_date(end_raw)
        deltatime = end_db - begin_db  
       
        text = "Время бодрствования: %s" % (str(deltatime).split(".")[0])
        context.bot.send_message(context.user_data["uid"], text = text)



    @classmethod
    def sleep(cls, context):
        context.user_data["inspector"].toogle_job_by_key("spare", enable = False)
        context.user_data["inspector"].toogle_job_by_key("sleep", enable = True) 
            
        context.user_data["sleep_manager"]["begin"] = datetime.datetime.utcnow()
        logging.info(context.user_data["sleep_manager"])
        db = context.user_data["db"].connection()         
        
        TInterfaceDB.update_awake_by_begin(
            db,
            uid = context.user_data["uid"],
            begin = context.user_data["sleep_manager"]["end"],
            end = context.user_data["sleep_manager"]["begin"],
            key_begin = context.user_data["sleep_manager"]["end"]
        )
        
        TInterfaceDB.insert_sleep(
            db,
            uid = context.user_data["uid"],
            begin = context.user_data["sleep_manager"]["begin"]
        )

        (begin_raw, end_raw, _id) = TInterfaceDB.get_sleep_by_begin(
            db,
            uid = context.user_data["uid"],
            begin = context.user_data["sleep_manager"]["begin"],
        )

        TInterfaceDB.update_user_state(
            db,
            uid = context.user_data["uid"],
            sleep_id = _id,
            state = context.user_data["state"]
        ) 
        
        try:
            TSleepState.sleep_statistics(context)
        except TypeError:
            logging.info("No awake")

    @classmethod
    def awake(cls, context):
        db = context.user_data["db"].connection()
        TInterfaceDB.insert_awake(
            db,
            uid = context.user_data["uid"],
            begin = context.user_data["sleep_manager"]["end"],
        )
        
        (begin_raw, end_raw, _id) = TInterfaceDB.get_awake_by_begin(
            db,
            uid = context.user_data["uid"],
            begin = context.user_data["sleep_manager"]["end"]
        ) 

        TInterfaceDB.insert_statistics(
            db,
            sleep_id = _id,
            total = 0,
            useful = 0,
            domestic = 0
        )
        
        context.user_data["sleep_manager"]["sleep_id"] = _id
        
        TInterfaceDB.update_user_state(
            db,
            uid = context.user_data["uid"],
            sleep_id = _id,
            state = context.user_data["state"]
        )
    
    def disable(self, context):
        logger = TBindedLogger.get_logger(context.user_data["uid"])
        logger.info("Sleep disable")
        context.user_data["sleep_manager"]["status"] = "awake"
        context.user_data["sleep_manager"]["end"] = datetime.datetime.utcnow()
        db = context.user_data["db"].connection()
        
        TInterfaceDB.update_sleep_by_begin(
            db,
            uid = context.user_data["uid"],
            key_begin = context.user_data["sleep_manager"]["begin"],
            begin = context.user_data["sleep_manager"]["begin"],
            end = context.user_data["sleep_manager"]["end"]
        )


        context.user_data["inspector"].toogle_job_by_key("sleep", enable = False)
        context.user_data["inspector"].toogle_job_by_key("spare", enable = True)
        context.user_data["inspector"].remove_job_by_key("alarm") 
        
        res = TInterfaceDB.get_sleep_by_end(
            db,
            uid = context.user_data["uid"],
            end = context.user_data["sleep_manager"]["end"]
        )

        logger.debug(res)

        begin_db = TDate.str_to_date(res[0])
        end_db = TDate.str_to_date(res[1])
        deltatime = end_db - begin_db 

        delta = str(deltatime).split(".")[0]
        text = (
                "Доброе утро\n"
                f"Ты спал\n{delta}"
        )

        context.bot.send_message(context.user_data["uid"], text = text)
        TSleepState.awake(context)

    def resolve(self, update, context):
        
        text = update.effective_message.text
       
        if text == "Я проснулся":   
            context.user_data["state_controller"].change_state("spare")
        elif text == "Графики":
            block = TVisualBlock(context)
            block.send(context)


class TStopState(TStateController.IState):
    def __init__(self, name):
        super().__init__(name)

    def enable(self, context):
        text = (
            "Минус одно существо, плюс один золотой...\n"
            "Я буду молчать, скучать, и ждать нажатия на /start"
        )
        context.bot.send_message(context.user_data["uid"], text = text)
        inspector = context.user_data["inspector"]
        for key in inspector.get_all_keys():
            inspector.toogle_job_by_key(key, enable = False)
        
        keys = []
        for key in context.user_data:
            keys.append(key)

        for key in keys:
            context.user_data.pop(key)
        
    def disable(self, context):
        pass

class TSpareState(TStateController.IState):
    def __init__(self, name):
        super().__init__(name)
    
    def enable(self, context):
        logger = TBindedLogger.get_logger(context.user_data["uid"])
        logger.info("Spare enable")
        reply_markup = ReplyKeyboardMarkup(
            keyboard = TSpareState.basic_keyboard(),
            resize_keyboard = True
        )

        context.bot.send_message(
            context.user_data["uid"],
            text = "У тебя свободное время, я буду проверять твою занятость",
            reply_markup = reply_markup
        )
        context.user_data["inspector"].toogle_job_by_key("spare", enable = True)
    
    def disable(self, context):
        logger = TBindedLogger.get_logger(context.user_data["uid"])
        logger.info("Spare disable")
    
    def send_task(self, ctx):
        context = ctx.job.context
        task = TAskTask(context, context.user_data["config"]["ask_task"]["interval"]) 

        value = 0
        if self.active: 
            task.send(context)
        else:
            value = 2
            logger = TBindedLogger.get_logger(context.user_data["uid"])
            logger.debug("still here")
        
        db = context.user_data["db"].connection()
        TInterfaceDB.insert_ask_task(
            db,
            uid = context.user_data["uid"],
            ask_time = task.created_time,
            value = value
        ) 

    def reset_task(self, context):
        inspector = context.user_data["inspector"]
        inspector.remove_job_by_key("spare")
        job = context.job_queue.run_repeating(
            self.send_task,
            context.user_data["config"]["ask_task"]["interval"],
            context = context
        )
        inspector.add_job(TInspector.TJob(job, "spare"))
    
    @classmethod
    def basic_keyboard(cls):
        keyboard = [
            [
                KeyboardButton(text = "Начинаю дело"), 
            ],
            [
                KeyboardButton(text = "Статистика"),
                KeyboardButton(text = "Графики"), 
            ],
            [
                KeyboardButton(text = "Помощь"),
                KeyboardButton(text = "Настройки"),
            ],
            [
                KeyboardButton(text = "Иду спать"),
            ]
        ]
        return keyboard
    
    def resolve(self, update, context):

        text = update.effective_message.text

        if text == "Иду спать": 
            update.message.reply_text(text = "Иди спи!")
            context.user_data["state_controller"].change_state("sleep")
        elif text == "Статистика":
            reply_markup = ReplyKeyboardMarkup(
                keyboard = TSpareState.basic_keyboard(),
                resize_keyboard = True
            )
            block = TStatisticsBlock(context)
            out = block.render(context) 
            out["reply_markup"] = reply_markup
            context.bot.send_message(context.user_data["uid"], **out)

        elif text == "Начинаю дело":
            context.user_data["state_controller"].change_state("work")
        elif text == "Настройки":
            context.user_data["state_controller"].change_state("settings")
        elif text == "Графики":
            block = TVisualBlock(context)
            block.send(context)
        elif text == "Помощь":
            block = THelpBlock(context)
            block.send(context)

class TSettingsState(TStateController.IState):
    def __init__(self, name):
        super().__init__(name)
        self.status = "open"
        self.aim = None

    @classmethod
    def basic_keyboard(cls):
        keyboard = [
            [
                KeyboardButton(text = "Частота \"Че делаешь?\""), KeyboardButton(text = "Частота проверки сна")
            ],
            [
                KeyboardButton(text = "Через сколько будить"), KeyboardButton(text = "Частота \"Ержан, проснись\"")
            ],
            [
                KeyboardButton(text = "Часовой пояс")
            ],
            [
                KeyboardButton(text = "Текущие настройки")
            ]
        ]
        return keyboard

    def enable(self, context):
        logger = TBindedLogger.get_logger(context.user_data["uid"])
        logger.info("Settings enable")
        self.status = "open"
        self.aim = None

        reply_markup = ReplyKeyboardMarkup(
                keyboard = TSettingsState.basic_keyboard()
        )
        text = (
                "Что будем менять?\n\n"
                "Справка:\n"
                "Часовой пояс Москвы: 180 мин\n"
                "Часовой пояс Саратова: 240 мин\n\n"
                "Спасибо, что ебетесь с минутами"
        )
        context.bot.send_message(context.user_data["uid"], text = text, reply_markup = reply_markup)
        self.status == "waitng"

    def disable(self, context):
        
        logger = TBindedLogger.get_logger(context.user_data["uid"])
        logger.info("Settings disable")

    def resolve(self, update, context):
        
        logger = TBindedLogger.get_logger(context.user_data["uid"])
        
        text = update.effective_message.text
        
        if self.status == "open":
            if text == "Текущие настройки":
                ask_int = context.user_data["config"]["ask_task"]["interval"]
                sleep_int = context.user_data["config"]["sleep_manager"]["interval"]
                sleep_time = context.user_data["config"]["sleep_manager"]["sleep_time"]
                alarm_rate = context.user_data["config"]["sleep_manager"]["alarm_rate"]
                time_zone  = context.user_data["config"]["sleep_manager"]["time_zone"]
                db = context.user_data["db"].connection()
                time_now   = TInterfaceDB.time_cast(
                    db,
                    context.user_data["uid"],
                    datetime.datetime.utcnow()
                )
                str_time = str(time_now).split(".")[0]
                text = (
                        "Частота \"Че делаешь?\": %s мин\n"
                        "Частота проверки сна: %s мин\n"
                        "Через сколько будить: %s мин\n"
                        "Частота \"Ержан, проснись\": %s мин\n"
                        "Часовой пояс: %s мин\n"
                        "Текущее время: %s"
                ) % (ask_int / 60, sleep_int / 60, sleep_time / 60, alarm_rate / 60, time_zone, str_time)
                context.bot.send_message(context.user_data["uid"], text = text)
                context.user_data["state_controller"].change_state("spare")
                
                return

            
            if text == "Частота \"Че делаешь?\"":
                self.aim = "ask_task_interval"
            elif text == "Частота проверки сна":
                self.aim = "sleep_interval"
            elif text == "Через сколько будить":
                self.aim = "sleep_time"
            elif text == "Частота \"Ержан, проснись\"":
                self.aim = "alarm_rate"
            elif text == "Часовой пояс":
                self.aim = "time_zone"
            else:
                context.bot.send_message(context.user_data["uid"], text = "Не понял")
                context.user_data["state_controller"].change_state("spare")
                return

            self.status = "waiting"
            context.bot.send_message(context.user_data["uid"], text = "Введи значение в минутах")
        elif self.status == "waiting":
            db = context.user_data["db"].connection()
            if self.aim != "time_zone":
                value = int(float(text) * 60)
            else:
                value = int(text)
            args = (value, context.user_data["uid"])

            st = context.user_data["state_controller"]
            
            if self.aim == "ask_task_interval": 
                TInterfaceDB.update_config(
                    db,
                    uid = context.user_data["uid"],
                    ask_task_interval = value
                )
                context.user_data["config"]["ask_task"]["interval"] = value
                st.get_state("spare").reset_task(context)

            
            elif self.aim == "sleep_interval":
                TInterfaceDB.update_config(
                    db,
                    uid = context.user_data["uid"],
                    sleep_interval = value
                )
                context.user_data["config"]["sleep_manager"]["interval"] = value
                st.get_state("sleep").reset_task(context)

            elif self.aim == "sleep_time":
                TInterfaceDB.update_config(
                    db,
                    uid = context.user_data["uid"],
                    sleep_time = value
                )
                context.user_data["config"]["sleep_manager"]["sleep_time"] = value
            elif self.aim == "alarm_rate": 
                TInterfaceDB.update_config(
                    db,
                    uid = context.user_data["uid"],
                    alarm_rate = value
                )
                context.user_data["config"]["sleep_manager"]["alarm_rate"] = value
            elif self.aim == "time_zone":
                TInterfaceDB.update_config(
                    db,
                    uid = context.user_data["uid"],
                    time_zone = value
                )
                context.user_data["config"]["sleep_manager"]["time_zone"] = value

            logger.debug("%s set to %s" % (self.aim, value))
            context.bot.send_message(context.user_data["uid"], text = "Сделано")
            context.user_data["state_controller"].change_state("spare")

            

class TWorkState(TStateController.IState):
    def __init__(self, name):
        super().__init__(name)
        self.status = "open"

    @classmethod
    def basic_keyboard(cls):
        keyboard = [
            [
                KeyboardButton(text = "Закончил дело")
            ]
        ]
        return keyboard
    
    def enable(self, context):
        logger = TBindedLogger.get_logger(context.user_data["uid"])
        logger.info("Work enable")
        self.status = "open"
        context.bot.send_message(context.user_data["uid"], text = "Чем будешь заниматься?")
    
    def disable(self, context):
        logger = TBindedLogger.get_logger(context.user_data["uid"])
        logger.info("Work disable")
        context.user_data["work"]["work_list"][-1].close()
        task = context.user_data["work"]["work_list"][-1]
        
        delta = task.end - task.begin 

        text = "Задача заняла:\n%s" % str(delta).split('.')[0]
        context.bot.send_message(context.user_data["uid"], text = text)
        context.user_data["inspector"].remove_job_by_key("work")

    def resolve(self, update, context):
        text = update.effective_message.text
        if self.status == "open":
            reply_markup = ReplyKeyboardMarkup(
                keyboard = TWorkState.basic_keyboard(),
                resize_keyboard = True
            )
            
            context.bot.send_message(
                context.user_data["uid"],
                text = "ок",
                reply_markup = reply_markup
            )

            context.user_data["work"]["work_list"].append(TWorkReminder.TWorkRecord(text))
            
            self.status = "waiting"
            
            block = TWorkReminder(context)
            out = block.render(context)
            context.bot.send_message(context.user_data["uid"], **out)

        elif self.status == "waiting":
            if text == "Закончил дело":
                context.user_data["state_controller"].change_state("spare")
            else:
                context.bot.send_message(context.user_data["uid"], text = "Не понял")
        
def query_handler(update, context):
    context.user_data["inline_button_manager"].handle_callback(update, context)

def check_user(context, db):
    uid = context.user_data["uid"]
    username = context.user_data["username"]
    first_name = context.user_data["first_name"]
    last_name = context.user_data["last_name"]

    logger = TBindedLogger.get_logger(uid)
    c = db.cursor()
    c.execute("SELECT * FROM users WHERE uid = ?", (uid, ))
    res = c.fetchone()
    return res is not None

def create_user(context, db):
    uid = context.user_data["uid"]
    username = context.user_data["username"]
    first_name = context.user_data["first_name"]
    last_name = context.user_data["last_name"]

    logger = TBindedLogger.get_logger("eternal")
    c = db.cursor()
    
    c.execute(
            """
            INSERT INTO users (uid, username, first_name, last_name) VALUES (?, ?, ?, ?);
            """, (uid, username, first_name, last_name)
    )
    c.execute(
            """
            INSERT INTO settings (uid) VALUES (?);
            """, (uid, )
    )
    c.execute(
            """
            INSERT INTO state(uid, state, sleep_id) VALUES (?, NULL, NULL);
            """, (uid, )
    )

    db.commit()

def get_config(context, db):
    logger = TBindedLogger.get_logger(context.user_data["uid"])
    (ask_task_interval, sleep_time, alarm_rate, sleep_interval, time_zone) = TInterfaceDB.get_config(db, context.user_data["uid"]) 
    context.user_data["config"] = {
        "ask_task": {
            "interval": ask_task_interval
        },
        "sleep_manager": {
            "interval": sleep_interval,
            "sleep_time": sleep_time,
            "alarm_rate": alarm_rate,
            "time_zone": time_zone
        }
    }

    logger.debug(context.user_data["config"])
    

def stop_handler(update, context):
    logger = TBindedLogger.get_logger(context.user_data["uid"])
    logger.info("stop...")
    context.user_data["state_controller"].change_state("stop")

def help_handler(update, context):
    block = THelpBlock(context)
    block.send(context)

def start_handler(update, context):
    context.user_data["uid"] = update.effective_user.id
    context.user_data["username"] = update.effective_user.username
    context.user_data["first_name"] = update.effective_user.first_name
    context.user_data["last_name"]  = update.effective_user.last_name
    
    if TBindedLogger.get_logger(context.user_data["uid"]).logger is None: 
        logger = logging.getLogger("logger_%s" % context.user_data["uid"])
        logger.setLevel(settings.get_eternal_logger_level())

        e_logger = TBindedLogger.get_logger(context.user_data["uid"])
        e_logger.bind_logger(logger)
        e_logger.bind_context(context)
        e_logger.debug(context)
        
    logger = TBindedLogger.get_logger(context.user_data["uid"])
    
    if "started" in context.user_data:
        logger.warning("/start can be used only once")
        return

    logger.info("/start") 

    db_base = TBindedDB(context, "eternal_base.db")
    db = db_base.connection()
    if check_user(context, db):
        logger.info("%s joined" % context.user_data["username"])
    else:
        create_user(context, db)
        logger.info("new user %s" % context.user_data["username"])
    
    
    context.user_data["db"] = db_base

    ibm = TInlineButtonManager(context)
    inspector = TInspector(context)
    state_controller = TStateController(context) 
    visualizer = TVisualizer("tmp", context)

    context.user_data["inline_button_manager"] = ibm
    context.user_data["inspector"] = inspector
    context.user_data["state_controller"] = state_controller 
    context.user_data["visualizer"] = visualizer 
    get_config(context, db)
   
    context.user_data["state"] = None
    
    context.user_data["work"] = {
        "work_list": [],
        "status": "nothing", # working, nothing
    }

    context.user_data["sleep_manager"] = {
        "status": "awake", # awake, sleepy, sleeping
        "begin": datetime.datetime.utcnow(),
        "end"  : datetime.datetime.utcnow(),
        "sleep_id": None
    }   

    cur_state = "spare"
    if "emulated" not in context.user_data or not context.user_data["emulated"]:  
        TSleepState.awake(context) 
    else:
        (_, db_state, sleep_id) = TInterfaceDB.get_user_state(
            db,
            uid = context.user_data["uid"]
        )
        
        logger.info((db_state, sleep_id))

        if db_state is not None:
            cur_state = db_state

        if cur_state == "stop":
            return
        
        if sleep_id is not None:
            context.user_data["sleep_manager"]["sleep_id"] = sleep_id
            begin_raw, end_row, _id = None, None, None
            
            if cur_state == "spare" or cur_state == "work": 
                (begin_raw, end_row, _id) = TInterfaceDB.get_awake_by_id(
                    db,
                    uid = context.user_data["uid"],
                    sleep_id = sleep_id
                )    

            elif cur_state == "sleep":
                context.user_data["sleep_manager"]["status"] = "sleeping"
                (begin_raw, end_row, _id) = TInterfaceDB.get_sleep_by_id(
                    db,
                    uid = context.user_data["uid"],
                    sleep_id = sleep_id
                )

            str_begin = TDate.str_to_date(begin_raw)
            new_begin = TInterfaceDB.time_to_utc(
                db,
                context.user_data["uid"],
                str_begin
            )

            context.user_data["sleep_manager"]["begin"] = new_begin
            context.user_data["sleep_manager"]["end"] = new_begin
            print(context.user_data["sleep_manager"])
            
        else:
            context.bot.send_message(context.user_data["uid"], text = "Впервые\n%s" % context.user_data["sleep_manager"]["end"])
            TSleepState.awake(context)
    
    logger.info(context.user_data["sleep_manager"])
    spare_state = TSpareState("spare")
    spare_state.reset_task(context)

    sleep_state = TSleepState("sleep")
    sleep_state.reset_task(context)

    state_controller.add_state(spare_state)
    state_controller.add_state(sleep_state)
    state_controller.add_state(TWorkState("work"))
    state_controller.add_state(TSettingsState("settings")) 
    state_controller.add_state(TStopState("stop"))

    state_controller.change_state(cur_state)

    context.dispatcher.add_handler(CallbackQueryHandler(query_handler))
    context.dispatcher.add_handler(MessageHandler(Filters.text, message_handler))  
    context.user_data["started"] = True

def message_handler(update, context):
    context.user_data["state_controller"].handle_callback(update, context) 

def emulate_start(updater, uid):
    d = updater.dispatcher

    update = Update(0)
    update._effective_user = User(uid, "fake", False)
    
    context = CallbackContext.from_update(update, d)
    context.user_data["emulated"] = True

    logging.info("Emulate start for %s" % update.effective_user.id)
    logging.info(context)
    start_handler(update, context)
    context.user_data["emulated"] = False

def main():
    if settings.stdout_log(): 
        logging.basicConfig(
            format = settings.get_logger_format(),
            level = settings.get_default_logger_level()
        )
    else:
        logging.basicConfig(
            format = settings.get_logger_format(),
            level = settings.get_default_logger_level(),
            filename = settings.get_log_file()
        ) 
    
    logging.warning("it is ok")
    if settings.need_proxy(): 
        updater = Updater (
            settings.get_token(),
            base_url = settings.get_proxy(),
            use_context = True
        )
    else:
        updater = Updater (
            settings.get_token(),
            use_context = True
        )

    db = sqlite3.connect("eternal_base.db")
    c = db.cursor()
    c.execute("SELECT uid FROM users;")
    text = (
            "Список изменений:\n\n"
            "1. Бот теперь персистентный. Как это нахуй? Теперь он должен работать бесперебойно\n\n"
            "При перезапуске бот сообразит, в каком он был состоянии до отключения и возобновит свою работу автоматически в нужном режиме\n"
            "Да, теперь не нужно лишний раз тыкать на /start\n\n"
            "2. У бота есть команда /help - не поверишь для чего\n\n"
            "3. Но я напишу еще и тут: бота теперь можно /stop, а после этого вручную /start\n\n"
            "4. Поправил косяки с графиками (некоторые неправильно рисовались по времени)\n\n"
            "5. Эти же злоебучие графики теперь строятся прямо на ходу, а не в конце дня\n\n"
            "6. Теперь в режиме сна есть кнопка просмотра графиков - чтобы перед сном подрочить на свою продуктивность\n\n"
            "7. Куча всякой хуйни, которая скрыта от глаз обычных пользователей\n\n"
            "Сейчас бот остановлен, но после нажатия /start он начнет работу. Напомню, что теперь бота можно будет остановить написав /stop"
    ) 
    
    users = c.fetchall()

    updater.dispatcher.add_handler(CommandHandler("start", start_handler)) 
    updater.dispatcher.add_handler(CommandHandler("stop", stop_handler))
    updater.dispatcher.add_handler(CommandHandler("help", help_handler)) 
    
    updater.start_polling()

    for user in users:
        print("User:", user)
        emulate_start(updater, user[0]) 
        if False:
            updater.dispatcher.bot.send_message(user[0], text = text)

    updater.idle()

if __name__ == "__main__":
    main()
