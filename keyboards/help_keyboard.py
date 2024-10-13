from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

def build_help_keyboard() -> ReplyKeyboardMarkup:
    button_register = KeyboardButton(text = 'register')
    button_leave = KeyboardButton(text = 'leave')
    button_list = KeyboardButton(text = 'list')
    row_general: list[KeyboardButton] = [button_register,
                                         button_leave,
                                         button_list]

    button_put_up = KeyboardButton(text = 'put_up')
    button_vote = KeyboardButton(text = 'vote')
    button_display = KeyboardButton(text = 'display')
    row_day: list[KeyboardButton] = [button_put_up,
                                     button_vote,
                                     button_display]

    button_kill = KeyboardButton(text = 'kill')
    button_heal = KeyboardButton(text = 'heal')
    button_check = KeyboardButton(text = 'check')
    button_visit = KeyboardButton(text = 'visit')
    button_mute = KeyboardButton(text = 'mute')
    row_night: list[KeyboardButton] = [button_kill,
                                       button_heal,
                                       button_check,
                                       button_visit,
                                       button_mute]

    rows: list[list[KeyboardButton]] = [row_general, row_day, row_night]
    markup = ReplyKeyboardMarkup(keyboard = rows, resize_keyboard = True,
                                 one_time_keyboard = True)
    return markup