#!/usr/bin/env python3
import json
import logging
import re
from datetime import datetime, date, timedelta
import emoji
import sys
from os.path import join, splitext, exists
from time import sleep
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, Filters
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, ConversationHandler, RegexHandler
from telegram.ext.dispatcher import run_async
from telegram.error import TelegramError, Unauthorized
from menu import dishtypes
from menu.menu_enums import Location
import ulb
from chatstrings.resolver import resolve

# static data
locations = {
    Location.STADT: "Stadtmitte",
    Location.LIWI: "Lichtwiese",
    Location.SCHOEFFERSTR: "Schöfferstraße"
}
day_names = ["mo", "di", "mi", "do", "fr"]

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mensabot')

# global variables initialized in main()
config = {}
dishes = {}
ulb_places = {}
database, feedback_db = None, None
job_queue = None

# patterns
pat_date = re.compile(r"^([0-3]?[0-9]\.){2}$")
pat_query = re.compile(r"^[A-Za-z]{3,}$")
pat_tag = re.compile(r"^\+[A-Za-z:_]{3,}$")
pat_exclude = re.compile(r"^![A-Za-z]{3,}$")

SIDE_DISH_LIMIT = 0.9

BANNER = "~~~ \U0001f37d\U0001f955\U0001f437\U0001f41f\U0001f331\U0001f414  ~~~\n\n"
RED_CHAR = '**'

def _lang_c(update):
    if update.message:
        return update.message.from_user.language_code
    else:
        return update.callback_query.from_user.language_code

# ---------- canteen menu ----------

# Commands: /mensa, (/heute, /morgen indirect call)
def mensa(bot, update, args):
    if database:
        database.log_update(update.message.chat, update.message.from_user)
    if not args:
        mensa_help(bot, update)
        return
    parsed_args = parse_args(args)
    result = process_query(update.message.chat.id, *parsed_args)
    if parsed_args[4]: # reduced
        keyboard = _get_reduced_mode_button(True, args, _lang_c(update))
    else:
        keyboard = None
    bot.send_message(chat_id=update.message.chat.id, text=result, parse_mode='HTML', reply_markup=keyboard)

def process_query(chat_id, loc, dates, queries, tags, reduced, error):
    text = ""
    # try to get loc and tags from db if not specified
    if not loc and database:
        loc = database.get_chat_location(chat_id)
    loc = loc or "stadt" # "stadt" as last fallback
    if len(tags) < 1 and len(queries[0]) < 1 and len(queries[1]) < 1 and database:
        tags = database.get_preferences(chat_id)
    if not error:
        if len(dates) < 1:
            dates = [datetime.strptime(ds, "%Y-%m-%d").date() for ds in dishes[loc].keys()]
        results = {}
        for date in dates:
            st = process_date(loc, date, queries, tags, reduced=reduced)
            results[date] = st
        for key in sorted(results):
            text += results[key] or ""
    # TODO translate error texts
    if error:
        text = "Fehler: Ungültige Eingabe."
    elif not text:
        text = "\nLeider habe ich keine Ergebnisse für dich gefunden. \uD83D\uDE15"
    return text

def _get_reduced_mode_button(is_reduced, args, lang):
    if is_reduced:
        caption = resolve('sidedishes_show', lang)
    else:
        caption = resolve('sidedishes_hide', lang)
    buttons = [
        [InlineKeyboardButton(caption, callback_data="red_switch {} {}".format(is_reduced, ','.join(args)))]
    ]
    return InlineKeyboardMarkup(buttons)

def reduced_mode_switch(bot, update):
    msg = update.callback_query.message
    query = update.callback_query.data.split()
    is_reduced = query[1] == 'True'
    args = query[2].split(',')
    if not is_reduced:
        args += [RED_CHAR]
    else:
        args = [a for a in args if not a == RED_CHAR]
    arg_list = parse_args(args)
    # only edit message if not all dates in past
    if max(arg_list[1]) >= date.today():
        result = process_query(msg.chat.id, *arg_list)
        bot.edit_message_text(chat_id=msg.chat.id, message_id=msg.message_id,
            text=result, parse_mode='HTML',
            reply_markup=_get_reduced_mode_button(not is_reduced, args, _lang_c(update)))
    bot.answer_callback_query(update.callback_query.id)

def parse_args(args):
    loc = None
    dates = []
    queries = []
    queries.append([])
    queries.append([])
    tags = []
    reduced = False
    error = False
    for arg in args:
        if arg in locations:
            loc = arg
        elif arg == "heute":
            dates.append(date.today())
        elif arg == "morgen":
            dates.append(date.today() + timedelta(days=1))
        elif arg.lower() in day_names:
            weekday = day_names.index(arg.lower())
            dates.append(_next_weekday(weekday))
        elif pat_date.match(arg):
            datesplit = arg.split('.')
            dt = date.today().replace(month=int(datesplit[1]), day=int(datesplit[0]))
            dates.append(dt)
        elif pat_query.match(arg):
            queries[0].append(arg)
        elif pat_exclude.match(arg):
            queries[1].append(arg[1:])
        elif pat_tag.match(emoji.demojize(arg)):
            tags.append(emoji.demojize(arg[1:]))
        elif arg == RED_CHAR:
            reduced = True
        else:
            error = True
            break
    return loc, dates, queries, tags, reduced, error

def _next_weekday(weekday):
    delta = (weekday - date.today().weekday() + 7) % 7
    return date.today() + timedelta(delta)

def _float_price(s):
    n = s.replace('€', '').replace(',', '.')
    return float(n)

def process_date(loc, date, queries, tags, reduced=False):
    datestring = date.strftime("%Y-%m-%d")
    if datestring in dishes[loc] and date >= date.today():
        title = "\n<b>{0} - {1}</b>\n\n".format(date.strftime("%d.%m.%Y"), locations[loc])
        item_string = ""
        for dish in dishes[loc][datestring]:
            # ignore side dishes in reduced mode
            if reduced and _float_price(dish["price"]) <= SIDE_DISH_LIMIT:
                continue
            ret = process_dish(dish, queries, tags)
            if ret:
                item_string += ret
        if item_string:
            return title + item_string
    return None

def process_dish(dish, queries, tags):
    matches = len(queries[0]) < 1
    # search queries
    for query in queries[0]:
        if query.lower() in dish['name'].lower():
            matches = True
            break
    # search excludes
    for query in queries[1]:
        if query.lower() in dish['name'].lower():
            matches = False
            break
    # search tags
    tag_matches = len(tags) < 1
    for tag in tags:
        if dishtypes.matches(tag, dish['additives']):
            tag_matches = True
            break
    matches &= tag_matches
    if matches:
        text = ""
        for attr in dish['additives']:
            text += dishtypes.emojize(attr)
        text += "  <i>{0}</i>\n".format(re.sub(r"\(\S*\)", "", dish["name"]))
        text += "      \uD83D\uDCCD {0} ".format(dish["location"])
        text += " \uD83D\uDCB0 {0}\n\n".format(dish["price"])
        return text
    return None

def heute(bot, update, args):
    args.append("heute")
    mensa(bot, update, args)

def morgen(bot, update, args):
    args.append("morgen")
    mensa(bot, update, args)

def weekday(bot, update, args, day):
    args.append(day)
    mensa(bot, update, args)

def mensa_loc(bot, update, args, loc):
    if len([a for a in args if not a == RED_CHAR]) < 1:
        args.append("heute")
    args.append(loc)
    mensa(bot, update, args)

# Commands: /start
def start_bot(bot, update):
    text = resolve('intro', _lang_c(update)).format(update.message.from_user.first_name)
    update.message.reply_html(text=BANNER+text)
    loc_text, loc_keyboard = _settings_option_loc(update.message.chat.id, _lang_c(update), back=False)
    update.message.reply_html(text=loc_text, reply_markup=loc_keyboard)

# Commands: /help, /hilfe
def help(bot, update):
    text = resolve('help_commands', _lang_c(update)).format(BANNER)
    bot.send_message(chat_id=update.message.chat.id, text=text)

def mensa_help(bot, update):
    text = resolve('help_search', _lang_c(update)).format(', '.join(locations))
    bot.send_message(chat_id=update.message.chat.id, text=text, parse_mode='HTML')  

# Commands: /icons
def icons_help(bot, update):
    if database:
        database.log_update(update.message.chat, update.message.from_user)
    text = resolve('help_icons', _lang_c(update))
    text += '\n'.join(dishtypes.get_list())
    update.message.reply_html(text=text)

# Only used when running in maintenance mode
def maintenance(bot, update):
    maintenance_file = "maintenance.txt"
    if exists(maintenance_file):
        with open(maintenance_file, 'r') as f:
            text = f.read()
    else:
        text = resolve('maintenance', _lang_c(update))
    bot.send_message(chat_id=update.message.chat.id, text=text, parse_mode="HTML", disable_web_page_preview=True)    

def error(bot, update, error):
    try:
        raise error
    except TelegramError as e:
        if e.message == "Message is too long":
            bot.send_message(chat_id=update.message.chat.id,
                text=resolve('error_too_many_results', _lang_c(update)))

# ---------- daily notifications ----------

def _get_newsletter_keyboard(lang):
    # inline callback queries for configuring notification
    buttons = [
        # first time in list administrative only
        [InlineKeyboardButton(time, callback_data="notify {}".format(time))] for time in config["times"][1:]
    ]
    buttons.append([InlineKeyboardButton(resolve('notification_off', lang), callback_data="notify off")])
    return InlineKeyboardMarkup(buttons)

# Commands: /newsletter
def notify(bot, update):
    database.log_update(update.message.chat, update.message.from_user)
    keyboard = _get_newsletter_keyboard(_lang_c(update))
    current_setting = database.get_user_newsletter(update.message.chat.id)
    if not current_setting:
        current_setting = 'off'    
    text = resolve('notification_intro', _lang_c(update)).format(current_setting)
    bot.send_message(chat_id=update.message.chat.id, text=text, parse_mode='HTML',
        reply_markup=keyboard)

def notify_callback(bot, update):
    query = update.callback_query
    user_id = query.message.chat.id
    data = query.data.split(' ')[1]
    if database.set_user(user_id, data):
        text = resolve('notification_success', _lang_c(update)).format(data)
        bot.delete_message(chat_id=user_id, message_id=query.message.message_id)
    else:
        text = resolve('notification_error', _lang_c(update))
    bot.answer_callback_query(callback_query_id=query.id, text=text, show_alert=True)

def run_notify(bot, job):
    time = str(job.context)
    user_data = database.get_all_users(time)
    execute_newsletter(time, bot, user_data)

@run_async
def execute_newsletter(time, bot, user_data):
    count=0
    queries = []
    queries.append([])
    queries.append([])
    # TODO readd lang-specific header
    # header = "~~~ Mensa-Menü Heute ~~~"
    for user, loc, prefs, lang in user_data:
        # TODO remove stadt as ultimate fallback?
        loc = loc or "stadt"
        prefs = prefs.split(',') if prefs else []
        reduced = len(prefs) <= 3 # TODO support arbitrary length pref.
        menu_text = process_query(user, loc, [date.today()], queries, prefs, reduced, False)
        try:
            try:
                if reduced:
                    args = [date.today().strftime("%d.%m."), loc] + ["+{}".format(p) for p in prefs]
                    keyboard = _get_reduced_mode_button(True, args, lang)
                else:
                    keyboard = None
                bot.send_message(chat_id=user, text=menu_text, parse_mode='HTML', reply_markup=keyboard)
                count+=1
                sleep(0.05)
            # specific exception handling
            except TelegramError as t_err:
                if t_err.message.startswith("Forbidden: "):
                    # unsubscribe from newsletter if blocked or kicked
                    database.set_user(user, 'off')
                raise
        # general exception handling
        except Exception as ex:
            logger.error("Failed to send newsletter to '{0}'.".format(user), exc_info=True)
            if not isinstance(ex, Unauthorized):
                job_queue.run_once(rerun_notify, 60, context=(0, (user, lang), args, menu_text))
    logger.info("Successfully sent newsletter to {} of {} users.".format(count, len(user_data)))
    database.log_exec(time, count)

def rerun_notify(bot, job):
    count, (user, lang), args, text = job.context
    if count < 5: # retry 5 times
        try:
            bot.send_message(chat_id=user, text=text, parse_mode='HTML',
                             reply_markup=_get_reduced_mode_button(True, args, lang))
        except:
            logger.error("Failed to send newsletter to '{0}', retry {1}.".format(user, count+1), exc_info=True)
            job_queue.run_once(rerun_notify, 60, context=(count+1, user, args, text))

# ---------- feedback ----------

# Commands: /feedback
def feedback(bot, update):
    database.log_update(update.message.chat, update.message.from_user)
    text = resolve('feedback_intro', _lang_c(update)).format(update.message.from_user.first_name)
    bot.send_message(chat_id=update.message.chat.id, text=text, parse_mode='HTML')
    return 1

def feedback_accept(bot, update):
    fb_text = update.message.text
    if len(fb_text) <= 250 and feedback_db.write_feedback(update.message.chat.id, update.message.message_id, fb_text):
        text = resolve('feedback_success', _lang_c(update))
    else:
        text = resolve('feedback_error', _lang_c(update))
    bot.send_message(chat_id=update.message.chat.id, text=text, parse_mode='HTML')
    return -1

def feedback_usercancel(bot, update):
    text=resolve('feedback_cancel', _lang_c(update))
    bot.send_message(chat_id=update.message.chat.id, text=text, parse_mode='HTML')
    logger.info("User {} cancelled feedback.".format(update.message.chat.id))
    return -1

def feedback_cancel(bot, update):
    logger.info("User {} cancelled feedback.".format(update.message.chat.id))
    return -1

# ---------- ulb ----------

def _get_ulb_icon(stats):
    if not stats[0]:
        return "\u26D4\uFE0F"
    elif stats[2]/stats[1] <= 0.2:
        return "\u26A0\uFE0F"
    else:
        return "\u2705"

# Commands: /ulbplatz
def show_ulb_stats(bot, update):
    global ulb_places
    if database:
        database.log_update(update.message.chat, update.message.from_user, 1)
    now_10min = datetime.now() - timedelta(minutes=10)
    if not ulb_places or ulb_places['time'] < now_10min:
        ulb_places = ulb.get_workplaces()
    text = resolve('ulb_header', _lang_c(update))
    for loc, stats in ulb_places['data'].items():
        text += _get_ulb_icon(stats)
        text += " <i>{}</i>\n".format(ulb.locs[loc])
        text += resolve('ulb_count', _lang_c(update)).format(*stats[1:])
        if stats[0]:
            num_persons = 10-round(stats[2]/stats[1]*10)
            text += "".join([ulb.get_random_person() for i in range(num_persons)])
            text += '\n'
        text += '\n'
    text += "Stand: {}".format(ulb_places['time'].strftime("%H:%M"))
    bot.send_message(chat_id=update.message.chat.id, text=text, parse_mode='HTML')

# ---------- settings ----------

def _get_settings_keyboard(lang):
    # inline callback queries for settings
    buttons = [
        [InlineKeyboardButton(resolve('settings_location', lang), callback_data="set loc")],
        [InlineKeyboardButton(resolve('settings_preferences', lang), callback_data="set pref")]
    ]
    return InlineKeyboardMarkup(buttons)

def _get_loc_keyboard(back, lang):
    app = ' d' if not back else ''
    buttons = [
        [InlineKeyboardButton(name, callback_data="change_loc " + loc + app)] for loc, name in locations.items()
    ]
    if back:
        buttons.append([InlineKeyboardButton(resolve('back', lang), callback_data="set main")])
    return InlineKeyboardMarkup(buttons)

def _get_pref_keyboard(prefs, lang):
    buttons = [
        [InlineKeyboardButton(resolve('preferences_edit', lang),
            switch_inline_query_current_chat="Meine Präferenzen: {}".format("".join(prefs)))],
        [InlineKeyboardButton(resolve('preferences_reset', lang), callback_data="delete_pref")],
        [InlineKeyboardButton(resolve('back', lang), callback_data="set main")]
    ]
    return InlineKeyboardMarkup(buttons)

# Commands: /settings, /einstellungen
def settings(bot, update):
    if database:
        database.log_update(update.message.chat, update.message.from_user)
    keyboard = _get_settings_keyboard(_lang_c(update))
    text = resolve('settings_intro', _lang_c(update))
    update.message.reply_html(text=BANNER+text, reply_markup=keyboard)

def _settings_option_main(lang):
    text = resolve('settings_intro', lang)
    return text, _get_settings_keyboard(lang)

def _settings_option_loc(user_id, lang, back=True):
    current_setting = database.get_chat_location(user_id)
    loc_descr = locations[current_setting] if current_setting else resolve('none', lang)
    text = resolve('settings_location_descr', lang).format(loc_descr)
    return text, _get_loc_keyboard(back, lang)

def _settings_option_pref(user_id, lang):
    text = resolve('settings_preferences_descr', lang)
    text += '\n'.join(dishtypes.get_list())
    prefs = database.get_preferences(user_id)
    prefs_em = [emoji.emojize(em) for em in prefs]
    return text, _get_pref_keyboard(prefs_em, lang)

def settings_callback(bot, update):
    query = update.callback_query
    message_id = query.message.message_id
    user_id = query.message.chat.id
    option = query.data.split(' ')[1]
    lang = _lang_c(update)
    if option == 'loc':
        text, keyboard = _settings_option_loc(user_id, lang)
    elif option == 'pref':
        text, keyboard = _settings_option_pref(user_id, lang)
    else:
        text, keyboard = _settings_option_main(lang)
    bot.edit_message_text(chat_id=user_id, message_id=message_id, text=BANNER+text,
        parse_mode='HTML', reply_markup=keyboard)

def execute_change_loc(bot, update):
    query = update.callback_query
    user_id = query.message.chat.id
    data = query.data.split(' ')
    loc = data[1]
    do_del = len(data) > 2
    if database.set_chat_location(user_id, loc):
        text = resolve('settings_location_success', _lang_c(update)).format(locations[loc])
    else:
        text = resolve('settings_location_error', _lang_c(update))
    bot.answer_callback_query(callback_query_id=query.id, text=text, show_alert=True)
    if do_del:
        bot.delete_message(chat_id=user_id, message_id=query.message.message_id)

def execute_change_pref(bot, update, groups):
    tags_em = emoji.get_emoji_regexp().findall(groups[0])
    tags_em = [em for em in tags_em if em in dishtypes.dishicons]
    tags = [emoji.demojize(em) for em in tags_em]
    if len(tags) < 1:
        text = resolve('settings_preferences_none', _lang_c(update))
    elif database.set_preferences(update.message.chat.id, tags):
        text = resolve('settings_preferences_success', _lang_c(update))
        text += '\n'.join(dishtypes.get_list(tags_em))
    else:
        text = resolve('settings_preferences_error', _lang_c(update))
    update.message.reply_text(text=text)

def execute_delete_pref(bot, update):
    query = update.callback_query
    user_id = query.message.chat.id
    if database.set_preferences(user_id, []):
        text = resolve('settings_preferences_reset', _lang_c(update))
    else:
        text = resolve('settings_preferences_reset_error', _lang_c(update))
    bot.answer_callback_query(callback_query_id=query.id, text=text, show_alert=True)

# ---------- start ----------

def main(config_file="config.json"):
    # probably should have been a class
    global config, dishes, database, feedback_db, job_queue
    
    # read config
    with open(config_file, 'r') as f:
        config = json.load(f)
    maintenance_mode=config.get("maintenance_mode")
    db_config=config.get("db_config")
    # load menu and connect to databases
    if not maintenance_mode:
        for loc, file in config.get("menu_locations").items():
            dishes[loc] = json.load(open(file, 'r'))['dishes']
    if db_config:
        from db.sqlitedb import SqliteDB
        from db.feedbackdb import FeedbackDB
        database = SqliteDB(db_config.get("main"))
        feedback_db = FeedbackDB(db_config.get("feedback"))
    # bot updater
    updater = Updater(token=config["token"])
    job_queue = updater.job_queue
    # add common command handlers
    dispatcher = updater.dispatcher
    if maintenance_mode:
        dispatcher.add_handler(MessageHandler(Filters.all, maintenance))
    else:
        dispatcher.add_handler(CommandHandler(["help", "hilfe"], help))
        dispatcher.add_handler(CommandHandler("icons", icons_help))
        dispatcher.add_handler(CommandHandler("start", start_bot))
        dispatcher.add_handler(CommandHandler("mensa", mensa, pass_args=True))
        dispatcher.add_handler(CommandHandler("heute", heute, pass_args=True))
        dispatcher.add_handler(CommandHandler("morgen", morgen, pass_args=True))
        for loc in locations:
            callback = lambda b, u, args, loc=loc: mensa_loc(b, u, args, loc)
            dispatcher.add_handler(CommandHandler(loc, callback, pass_args=True))
        dispatcher.add_handler(CommandHandler("ulbplatz", show_ulb_stats))
        for day in day_names:
            callback = lambda b, u, args, day=day: weekday(b, u, args, day)
            dispatcher.add_handler(CommandHandler(day, callback, pass_args=True))
        dispatcher.add_handler(CallbackQueryHandler(reduced_mode_switch, pattern="red_switch .*"))
    dispatcher.add_error_handler(error)
    # features only available with db
    if not maintenance_mode and db_config:
        dispatcher.add_handler(CommandHandler("newsletter", notify))
        dispatcher.add_handler(CallbackQueryHandler(notify_callback, pattern="notify .*"))
        dispatcher.add_handler(CommandHandler(["settings", "einstellungen"], settings))
        dispatcher.add_handler(CallbackQueryHandler(settings_callback, pattern="set .*"))
        dispatcher.add_handler(CallbackQueryHandler(execute_change_loc, pattern="change_loc .*"))
        dispatcher.add_handler(RegexHandler(r"(?:@.*)?Meine Präferenzen:(.*)", execute_change_pref, pass_groups=True))
        dispatcher.add_handler(CallbackQueryHandler(execute_delete_pref, pattern="delete_pref"))
        for t in config.get("times"):
            job_queue.run_daily(run_notify, datetime.strptime(t, '%H:%M').time(), days=tuple(range(5)), context=t)
    # feedback
    if db_config:
        feedback_handler = ConversationHandler(
            entry_points=[CommandHandler('feedback', feedback)],
            states={
                1: [MessageHandler(Filters.text & ~Filters.command, feedback_accept)]
            },
            fallbacks=[CommandHandler('nein', feedback_usercancel), MessageHandler(Filters.all, feedback_cancel)]
        )
        dispatcher.add_handler(feedback_handler, group=1)
    # start running
    updater.start_polling()
    updater.idle()


if __name__ == "__main__":
    main()
