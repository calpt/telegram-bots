#!/usr/bin/env python3
from telegram.ext import Updater, CommandHandler, MessageHandler, InlineQueryHandler
from telegram.ext import Filters
from telegram import InlineQueryResultArticle, InputTextMessageContent
import logging
import convert

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('texubot')

# --- message handlers ---

help_text = '''
This bot can convert LaTeX formulas to formatted Unicode text.
Just type something like
<code>@texubot \\alpha^2 + \\beta^2 \\neq 0</code>
in any of your chats. You don't need to add this bot anywhere.

Bot source on GitHub:
https://github.com/cfalxp/texubot
Based on this LaTeX-Unicode converter:
https://github.com/ypsu/latex-to-unicode
'''

def info(bot, update):
    update.message.reply_html(text=help_text, disable_web_page_preview=True)

def echo_unicode(bot, update):
    formatted_text = convert.convert(update.message.text)
    update.message.reply_text(formatted_text, quote=True,
                              disable_web_page_preview=True)

def inline_query(bot, update):
    query = update.inline_query.query
    if query:
        formatted_text = convert.convert(query)
        results = [_build_answer(formatted_text)]
        bot.answer_inline_query(update.inline_query.id, results=results)

def _build_answer(content):
    return InlineQueryResultArticle(
                id=0, title=content,
                input_message_content=InputTextMessageContent(content)
            )

def error(bot, update, error):
    logger.warning('Update "%s" caused error "%s"', update, error)

# --- main ---

def main(token):
    updater = Updater(token=token)
    # add message handlers
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", info))
    dispatcher.add_handler(CommandHandler("help", info))
    dispatcher.add_handler(MessageHandler(Filters.text, echo_unicode))
    dispatcher.add_handler(InlineQueryHandler(inline_query))
    dispatcher.add_error_handler(error)
    # start
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    with open('TOKEN.txt', 'r') as f:
        bot_token = f.read().split('\n')[0]
    main(bot_token)
