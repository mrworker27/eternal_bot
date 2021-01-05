import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from eternal_bot.db import TInterfaceDB
from eternal_bot.util import EternalBase
from eternal_bot.interaction import TBindedInlineButton, TInlineButtonManager

class TStateController:
    class IState:
        def __init__(self, name):
            super().__init__()
            self.name = name
            self.active = False

        def enable(self, context):
            pass
        
        def disable(self, context):
            pass

        def resolve(self, update, context):
            pass

    def __init__(self, context):
        self.context = context
        self.states = dict()
        self.active = None

    def add_state(self, state):
        self.states[state.name] = state
    
    def change_state(self, name):
        if name not in self.states:
            return

        if self.active is not None: 
            self.active.disable(self.context)
            self.active.active = False
        
        db = self.context.user_data["db"].connection()
        
        TInterfaceDB.update_user_state(
            db,
            uid = self.context.user_data["uid"],
            state = name,
            sleep_id = self.context.user_data["sleep_manager"]["sleep_id"]
        )
        
        self.context.user_data["state"] = name
        self.states[name].enable(self.context) 
        self.active = self.states[name]
        self.active.active = True

    def get_state(self, name):
        return self.states[name]

    def handle_callback(self, update, context):
        if self.active is not None:
            name = self.active.name
            self.states[name].resolve(update, context)

class TInspector(EternalBase):

    class TJob:
        def __init__(self, job, key, job_id = 0):
            self.job = job
            self.key = key
            self.id = job_id
    
    def __init__(self, context): 
        super().__init__(context)
        self.context = context

        self.task_key = dict()
        
        self.modulo = 107
        self.task_id = [None] * self.modulo
        self.free_id = 0
        


    def add_job(self, job):
        if job.key not in self.task_key: 
            self.task_key[job.key] = []

        job.id = self.free_id
        job.job.enabled = False 
        self.task_id[job.id] = job

        self.free_id = (self.free_id + 1) % self.modulo
        
        self.task_key[job.key].append(job)

        return job.id

    def remove_job_by_key(self, key):
        if key not in self.task_key:
            self.logger.debug("No key in task_key")
            return

        for job in self.task_key[key]:
            job.job.schedule_removal()

    def remove_job_by_id(self, job_id):
        self.task_id[job_id].job.schedule_removal()

    def toogle_job_by_key(self, key, enable):
        for job in self.task_key[key]:
            job.job.enabled = enable

    def toogle_job_by_id(self, job_id, enable):
       self.task_id[job_id].job.enabled = enable

    def get_all_keys(self):
        return self.task_key
