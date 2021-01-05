import logging, datetime
from inspect import getframeinfo, stack

import os, psutil

class TDate:
    @staticmethod
    def str_to_date(string): 
        frmt = "%Y-%m-%d %H:%M:%S.%f"
        return datetime.datetime.strptime(string, frmt)

class TBindedLogger:
    
    loggers = dict()
    
    @classmethod
    def get_logger(cls, name):
        if name not in cls.loggers:
            cls.loggers[name] = TBindedLogger()
        
        return cls.loggers[name]

    def __init__(self):
        self.context = None
        self.logger = None
    
    def bind_context(self, context):
        self.context = context

    def bind_logger(self, logger):
        self.logger = logger
    
    def get_prefix(self):
        prefix = "[user %s] " % self.context.user_data["uid"]
        return prefix

    def format(self, msg):
        # print(psutil.virtual_memory)
        used_mem = 0.0
        try:
            process = psutil.Process(os.getpid())
            used_mem = (process.memory_info().rss / (1024 * 1024))
        except Exception:
            pass

        caller = getframeinfo(stack()[2][0])
        
        cmd_line = ("\nin %s:%d\n" % (caller.filename, caller.lineno))
        mem_line = ("Memory used: %f Mb\n" % round(used_mem, 2))
        
        fmsg = self.get_prefix() + str(msg) + cmd_line + mem_line
        
        return fmsg

    def error(self, msg, *args, **kwargs):
        fmsg = self.format(msg)
        self.logger.error(fmsg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        fmsg = self.format(msg)
        self.logger.warning(fmsg, *args, **kwargs)
    
    def info(self, msg, *args, **kwargs):
        fmsg = self.format(msg)
        self.logger.info(fmsg, *args, **kwargs)
    
    def debug(self, msg, *args, **kwargs):
        fmsg = self.format(msg)
        self.logger.debug(fmsg, *args, **kwargs)

class EternalBase:
    def __init__(self, context):
        self.logger = TBindedLogger.get_logger(context.user_data["uid"])
