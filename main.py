import sys
import requests
import logging
import datetime as dt
import time
from telegram import Update
from telegram.ext import (
    Application, CommandHandler, ContextTypes, MessageHandler,
    filters, PicklePersistence
)

from config import HOST, TOKEN, UPDATE_FREQUENCY, LOG_NAME, MESSAGE_HISTORY
from constants import (ST_TRACKING, ST_PAUSED, ST_WAIT_GAME_ID, LANG_RU, LANG_EN,
                       MESSAGE_DELETE_TIMEOUT, PHASE_DRAFTING, PHASE_RESEARCH, TURN_PASS)
from game_data import GameData
from l18n import (l18n, get_turn_type_str, LK_WAIT_GAME_ID, LK_BAD_GAME_ID, LK_WILL_PASS, LK_WILL_NOT_PASS,
                  LK_PASSED, LK_START_GONE_WRONG, LK_PAUSE, LK_WILL_TAG, LK_TAG_COMMAND_ERROR, LK_WILL_NOT_TAG,
                  LK_NEVER_TAGGED, LK_DELAY_SET, LK_DELAY_COMMAND_ERROR, LK_START_COMMAND_ERROR, LK_LANG_SWITCHED,
                  LK_SETLANG_COMMAND_ERROR)
from util import build_api_url, looks_like_player_id


class TurnMaker:
    @staticmethod
    def find_pass_option_index(api_reply):
        options = api_reply['waitingFor']['options']
        for i, option in enumerate(options):
            if option['title'] == "Pass for this generation":
                return i
        raise RuntimeError("Not found passing option")

    @staticmethod
    def try_pass(game_data: GameData, ingame_player_name):
        logging.info("check pass for {}".format(ingame_player_name))
        for username, (player_name, player_id) in game_data.users_info.items():
            if player_name == ingame_player_name and game_data.scheduled_turns.get(username) == TURN_PASS:
                # prepare request param
                url = build_api_url('player', player_id)
                reply = requests.get(url).json()
                pass_idx = TurnMaker.find_pass_option_index(reply)
                post_url = f"http://{HOST}/player/input?id={player_id}"
                reply = requests.post(post_url, json={
                    'type': 'or',
                    'index': pass_idx,
                    'response': {
                        'type': 'option'
                    }
                })
                if reply.status_code != 200:
                    logging.error("Passing failed")
                    return False
                game_data.scheduled_turns.pop(username)
                return True
        return False


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.chat_data['GAME'] = GameData(ST_WAIT_GAME_ID)
    await update.message.reply_text(l18n(context, LK_WAIT_GAME_ID))


def get_game_status(game_id):
    url = build_api_url("spectator", game_id)
    try:
        return requests.get(url).json()
    except RuntimeError:
        pass


def get_current_players(reply):
    out = []
    for player in reply['players']:
        if player['timer']['running']:
            out.append((player['name'], player['timer']['startedAt']))
    if not out:
        raise RuntimeError("Cannot find current player")
    return tuple(out)


def address_player(game: GameData, player_name):
    username = game.users_tag.get(player_name)
    if username:
        return f"@{username}"
    return player_name


def address_players(game: GameData, player_names):
    return ', '.join(address_player(game, p) for p in player_names)


async def schedule_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    logging.info("Called schedule_pass()")
    # check if we already know id of the user
    user = update.message.from_user
    data: GameData = context.chat_data['GAME']
    logging.info("Current users_info = {}".format(data.users_info))
    user_info = data.users_info.get(user.username)
    # ask to retry with id if unknown and not given
    if not user_info or not all(user_info):
        try:
            name, player_id = context.args[0], context.args[1]
            assert looks_like_player_id(player_id)
            data.users_info[user.username] = [name, player_id]
            logging.info("Setting users_info, now is {}".format(data.users_info))
        except IndexError:
            # TODO l18n
            msg = ("Нужны твое имя в игре и id (12-13 символов). "
                   "Для этого скопируй id из адресной строки и скажи /pass <ник> <id>. "
                   "Потом можно будет просто писать /pass")
            await update.effective_message.reply_text(msg)
        except AssertionError:
            await update.effective_message.reply_text(l18n(context, LK_BAD_GAME_ID))
    # add to passing queue
    user_info = data.users_info.get(user.username)
    if user_info and all(user_info):
        data.scheduled_turns[user.username] = TURN_PASS
        await update.effective_message.reply_text(l18n(context, LK_WILL_PASS))


async def unschedule_pass(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # NOTE: in fact unschedules any actions
    data: GameData = context.chat_data['GAME']
    username = update.message.from_user.username
    data.scheduled_turns.pop(username)
    await update.effective_message.reply_text(l18n(context, LK_WILL_NOT_PASS))


async def callback_timer(context: ContextTypes.DEFAULT_TYPE):
    data: GameData = context.job.data
    logging.info("Timer event: gamedata = {}".format(data))
    status = get_game_status(data.game_id)
    if not status:
        return

    if ans := data.tft.check(status):
        oceans, oxygen, temp = ans
        await context.bot.send_message(chat_id=context.job.chat_id,
                                       parse_mode='Markdown',
                                       text=data.tft.make_message(context, oceans, oxygen, temp))

    phase = status['game']['phase']
    if phase == PHASE_DRAFTING:
        data.scheduled_turns = {}
    players = get_current_players(status)
    turn_type_str = get_turn_type_str(context, phase, len(players) > 1)
    if players != data.last_ping:
        passed = False
        if len(players) == 1 and phase not in (PHASE_DRAFTING, PHASE_RESEARCH):
            passed = TurnMaker.try_pass(data, players[0][0])
        if passed:
            reply_text = l18n(context, LK_PASSED) + players[0][0]
            await context.bot.send_message(chat_id=context.job.chat_id,
                                           text=reply_text)
        else:
            last_turn = max([dt.datetime.fromtimestamp(p[1] // 1000) for p in players])
            if (dt.datetime.now() - last_turn) > dt.timedelta(minutes=data.ping_delay_min):
                who = address_players(context.chat_data['GAME'], [p[0] for p in players])
                reply_text = f"{who}, {turn_type_str}"
                data.last_ping = players
                msg = await context.bot.send_message(chat_id=context.job.chat_id,
                                               text=reply_text)
                data.message_ids_queue.append((msg.message_id, time.time()))
                while len(data.message_ids_queue) > MESSAGE_HISTORY:
                    hmsg = data.message_ids_queue.pop(0)
                    if (time.time() - hmsg[1]) < MESSAGE_DELETE_TIMEOUT:
                        await context.bot.delete_message(chat_id=context.job.chat_id,
                                                         message_id=hmsg[0])




async def start_tracking(chat_id, game_id, context: ContextTypes.DEFAULT_TYPE, do_restore=True):
    st = get_game_status(game_id)
    if st:
        players = get_current_players(st)
        whose = (f"ходит {players[0][0]}"
                 if st["game"]["phase"] not in (PHASE_DRAFTING, PHASE_RESEARCH)
                 else "драфт")
        reply_text = f"Ок, слежу за игрой id={game_id}, сейчас {whose}"  # TODO l18n
        if do_restore:
            context.chat_data['GAME'].restore()
        context.chat_data['GAME'].state = ST_TRACKING
        context.job_queue.run_repeating(
            callback_timer, UPDATE_FREQUENCY,
            data=context.chat_data['GAME'],
            chat_id=chat_id
        )
    else:
        reply_text = l18n(context, LK_START_GONE_WRONG)
    await context.bot.send_message(chat_id=chat_id, text=reply_text)


async def pause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'GAME' in context.chat_data:
        context.chat_data['GAME'].state = ST_PAUSED
        await context.job_queue.stop()
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=l18n(context, LK_PAUSE))
    else:
        await start(update, context)


async def unpause(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if 'GAME' in context.chat_data:
        game_id = context.chat_data['GAME'].game_id
        await context.job_queue.start()
        await start_tracking(update.effective_chat.id, game_id, context)
    else:
        await start(update, context)


async def turn_on_tagging(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    assert 'GAME' in context.chat_data
    try:
        ingame_name = context.args[0]
        data: GameData = context.chat_data['GAME']
        data.users_tag[ingame_name] = user.username
        if user.username not in data.users_info:
            data.users_info[user.username] = [ingame_name, None]
        else:
            data.users_info[user.username][0] = ingame_name
        await update.effective_message.reply_text(l18n(context, LK_WILL_TAG))
    except IndexError:
        await update.effective_message.reply_text(l18n(context, LK_TAG_COMMAND_ERROR))
    except KeyError:
        await start(update, context)


async def turn_off_tagging(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    found = context.chat_data['GAME'].users_info.get(user.username)
    if found:
        context.chat_data['GAME'].users_tag.pop(found[0])
        await update.effective_message.reply_text(l18n(context, LK_WILL_NOT_TAG))
    else:
        await update.effective_message.reply_text(l18n(context, LK_NEVER_TAGGED))


async def set_delay(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        v = int(context.args[0])
        context.chat_data['GAME'].ping_delay_min = v
        await update.effective_message.reply_text(l18n(context, LK_DELAY_SET).format(v))
    except (IndexError, ValueError):
        await update.effective_message.reply_text(l18n(context, LK_DELAY_COMMAND_ERROR))


async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if context.chat_data['GAME'].state == ST_WAIT_GAME_ID:
        if looks_like_player_id(text):
            await set_id(update, context, text)


async def set_id(update: Update, context: ContextTypes.DEFAULT_TYPE, game_id):
    assert context.chat_data['GAME'].state == ST_WAIT_GAME_ID
    try:
        context.chat_data['GAME'] = GameData(game_id=game_id, state=None)
        await start_tracking(update.effective_chat.id, game_id, context, do_restore=False)
    except RuntimeError:
        reply_text = l18n(context, LK_START_COMMAND_ERROR)
        await context.bot.send_message(chat_id=update.effective_chat.id,
                                       text=reply_text)


async def set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        lang = context.args[0]
        assert lang in (LANG_EN, LANG_RU)
        context.chat_data['LANG'] = lang
        await update.effective_message.reply_text(l18n(context, LK_LANG_SWITCHED))
    except (IndexError, AssertionError):
        await update.effective_message.reply_text(l18n(context, LK_SETLANG_COMMAND_ERROR))


def main():
    persistence = PicklePersistence(filepath='persistence.pickle', update_interval=30)
    app = Application.builder() \
        .token(TOKEN) \
        .get_updates_http_version('1.1') \
        .http_version('1.1') \
        .persistence(persistence=persistence) \
        .build()

    msg_handler = MessageHandler(filters.TEXT & (~filters.COMMAND), handle_msg)
    app.add_handler(msg_handler)

    app.add_handler(CommandHandler(["start"], start))
    app.add_handler(CommandHandler(["pause"], pause))
    app.add_handler(CommandHandler(["restart", "unpause"], unpause))
    app.add_handler(CommandHandler(["delay"], set_delay))
    app.add_handler(CommandHandler(["tagme"], turn_on_tagging))
    app.add_handler(CommandHandler(["tagmenot"], turn_off_tagging))
    app.add_handler(CommandHandler(["pass"], schedule_pass))
    app.add_handler(CommandHandler(["nopass"], unschedule_pass))
    app.add_handler(CommandHandler(["setlang"], set_lang))
    app.run_polling()


if __name__ == "__main__":
    log_level = int(sys.argv[1]) if len(sys.argv) > 1 else 10
    logging.basicConfig(filename=LOG_NAME, format='%(asctime)s %(message)s', level=log_level)
    main()
