#!/usr/bin/env python3
import logging
import json
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters
import tucan

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
logger = logging.getLogger('tucanbot')

# global config
config = {}
tuc_sess = None

# command: /start
def start(update, context):
    if update.message.chat.id != config['chat']:
        return
    text='Hallo {}! Dein Bot läuft.'.format(update.message.from_user.first_name)
    text+="\n\u27A1\uFE0F /ergebnisse anzeigen."
    update.message.reply_text(text)

# command: /ergebnisse
def course_results(update, context):
    if update.message.chat.id != config['chat']:
        return
    results = tuc_sess.get_course_results()
    text="<b>{}</b>\n\n".format(results['term'])
    for course in results['courses']:
        text+="<i>{}</i>\n".format(course['name'].replace('/', '/ '))
        text+="\u2022 Note: <b>{}</b>\n".format(course['grade'])
        text+="\u2022 Status: <b>{}</b>\n".format(course['status'])
    update.message.reply_html(text)

def job_callback(context):
    job = context.job
    finished = job.context
    results = tuc_sess.get_course_results()
    # TODO check matching lengths
    for i, course in enumerate(results['courses']):
        if finished[i]:
            continue
        elif course['grade']:
            # inform user of newly available grade
            text="\uD83D\uDD14 Ergebnisse für <i>{}</i> wurden veröffentlicht.".format(course['name'])
            text+="\n\u27A1\uFE0F /ergebnisse anzeigen."
            context.bot.send_message(chat_id=config['chat'], text=text, parse_mode="HTML")
            finished[i] = True
    # rerun if not all results are published yet
    if not all(finished):
        context.job_queue.run_once(job_callback, config['check_rate']*60, finished)
    logger.info("Sucessfully checked for new results.")

def setup_jobs(job_queue):
    curr_results = tuc_sess.get_course_results()
    finished=[False]*len(curr_results['courses'])
    job_queue.run_once(job_callback, 0, finished)

def main(config_file="config.json"):
    global config, tuc_sess
    with open(config_file, 'r') as f:
        config = json.load(f)
    # log in to Tucan
    tuc_sess = tucan.Tucan(config["login"]["username"], config["login"]["pass"])
    # init bot
    updater = Updater(config["token"], use_context=True)
    dp = updater.dispatcher
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("ergebnisse", course_results))
    # start checking for results
    if config['check_rate'] and isinstance(config['check_rate'], int):
        setup_jobs(updater.job_queue)
    # start running
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
