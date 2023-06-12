from telegram.ext import ContextTypes

from constants import LANG_EN, LANG_RU, PHASE_DRAFTING, PHASE_RESEARCH
from config import DEFAULT_LANG

LK_WAIT_GAME_ID = "wait_game_id"
LK_BAD_GAME_ID = "bad_message_id"
LK_WILL_PASS = "will_pass"
LK_WILL_NOT_PASS = "will_not_pass"
LK_TF_STATUS = "tf_status"
LK_PASSED = "passed"
LK_START_GONE_WRONG = "start_gone_wrong"
LK_PAUSE = "pause"
LK_WILL_TAG = "will_tag"
LK_WILL_NOT_TAG = "will_not_tag"
LK_TAG_COMMAND_ERROR = "tag_command_error"
LK_NEVER_TAGGED = "never_tagged"
LK_DELAY_SET = "delay_set"
LK_DELAY_COMMAND_ERROR = "delay_command_error"
LK_START_COMMAND_ERROR = "start_command_error"
LK_LANG_SWITCHED = "lang_switched"
LK_SETLANG_COMMAND_ERROR = "setlang_command_error"
LK_UNEXPECTED_MESSAGE = "unexpected_message"

MESSAGES = {
    LK_WAIT_GAME_ID: {
        LANG_RU: "Привет, дайте мне id наблюдателя игры",
        LANG_EN: "Hi, give me the spectator id",
    },
    LK_BAD_GAME_ID: {
        LANG_RU: "Это не похоже на id, попробуй ещё раз",
        LANG_EN: "That doesn't look like a valid id, try again",
    },
    LK_WILL_PASS: {
        LANG_RU: "Ок, сделаю за тебя пас!",
        LANG_EN: "Ok, will pass for you!",
    },
    LK_WILL_NOT_PASS: {
        LANG_RU: "Хорошо, не буду делать за тебя пас!",
        LANG_EN: "Ok, will not pass for you!",
    },
    LK_TF_STATUS: {
        LANG_RU: "*Марс терраформирован на {}%*: океанов {}, кислород {}%, температура {}",
        LANG_EN: "*Mars is terraformed by {}%*: {} oceans, {}% oxygen, temperature {}",
    },
    LK_PASSED: {
        LANG_RU: "Я спасовал за игрока ",
        LANG_EN: "I passed for player ",
    },
    LK_START_GONE_WRONG: {
        LANG_RU: "Что-то пошло не так, возможно, ошибка сети",
        LANG_EN: "Something went wrong, probably network error"
    },
    LK_PAUSE: {
        LANG_RU: "Ок, пока не буду вас беспокоить",
        LANG_EN: "Ok, not disturbing you for now",
    },
    LK_WILL_TAG: {
        LANG_RU: "Хорошо, буду тегать тебя",
        LANG_EN: "Ok, I will tag you from now on"
    },
    LK_TAG_COMMAND_ERROR: {
        LANG_RU: "Используй так: /tagme <имя в игре>",
        LANG_EN: "Use like this: /tagme <player name>"
    },
    LK_WILL_NOT_TAG: {
        LANG_RU: "Хорошо, больше не буду тегать тебя",
        LANG_EN: "Ok, I will not tag you anymore"
    },
    LK_NEVER_TAGGED: {
        LANG_RU: "И не собирался тебя тегать",
        LANG_EN: "I wasn't going to tag you anyway"
    },
    LK_DELAY_SET: {
        LANG_RU: "Хорошо, буду сообщать через {} минут после начала хода",
        LANG_EN: "Ok, I'll report in {} minutes after a turn starts"
    },
    LK_DELAY_COMMAND_ERROR: {
        LANG_RU: "Используй так: /delay <минуты>",
        LANG_EN: "Use like this: /delay <minutes>"
    },
    LK_START_COMMAND_ERROR: {
        LANG_RU: "Похоже, вы дали мне id неактивной игры, попробуйте ещё",
        LANG_EN: "Looks like you gave me an inactive game id, try again"
    },
    LK_LANG_SWITCHED: {
        LANG_RU: "Хорошо, переключил язык на русский",
        LANG_EN: "Ok, switched the language to English"
    },
    LK_SETLANG_COMMAND_ERROR: {
        LANG_RU: f"Используй так: /setlang <{LANG_RU}|{LANG_EN}>",
        LANG_EN: f"Use like this: /setlang <{LANG_RU}|{LANG_EN}>"
    },
    LK_UNEXPECTED_MESSAGE: {
        LANG_RU: "Не знаю, что делать с этим сообщением. Возможно, игра не начата",
        LANG_EN: "I don't know what to do with this message, maybe you should start the game"
    }
}


def l18n(context: ContextTypes.DEFAULT_TYPE, l18n_key):
    return MESSAGES.get(l18n_key, {}).get(context.chat_data.get('LANG', DEFAULT_LANG), "")


def get_turn_type_str(context, phase, plural):
    lang = context.chat_data.get('LANG', DEFAULT_LANG)
    if lang == LANG_RU:
        your_str_m = "ваш" if plural else "твой"
        your_str_f = "ваша" if plural else "твоя"

        if phase == PHASE_DRAFTING:
            return f"{your_str_m} драфт"
        if phase == PHASE_RESEARCH:
            return f"{your_str_f} покупка карт"
        return f"{your_str_m} ход"
    elif lang == LANG_EN:
        pref = "it's your "
        if phase == PHASE_DRAFTING:
            return pref + "draft"
        if phase == PHASE_RESEARCH:
            return pref + "research"
        return pref + "turn"
    else:
        raise Exception("Unknown lang")
