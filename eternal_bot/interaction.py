import logging

class TInlineButtonManager:
    
    def __init__(self, context):
        self.modulo = 1000
        self.buttons = [None] * self.modulo
        self.free_id = 0
        self.context = context

    def handle_callback(self, update, context):
        data = update.callback_query.data
        button_id = int(data.split('@')[0])
 
        if self.buttons[button_id].button.callback_data != data:
            logging.debug("Wrong button")
        else: 
            self.buttons[button_id].callback(update, context)
        
        update.callback_query.answer() 
    
    def add_button(self, button):

        if "uid" not in self.context.user_data:
            logging.debug("add_button no uid")
            return

        button.id = self.free_id
        uid = self.context.user_data["uid"] 
        button.button.callback_data = str(button.id) + "@" + button.button.callback_data

        self.buttons[button.id] = button 
        self.free_id = (self.free_id + 1) % self.modulo

class TBindedInlineButton:
    
    def __init__(self, button, callback):
        self.button = button
        self.callback = callback
        self.id = 0
