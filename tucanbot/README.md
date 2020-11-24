# tucanbot

Automatically check for course results in TUCaN.

### Quick Start

1. Clone this repo and install required Python dependencies:
```
python3 -m pip install -r requirements.txt
```
2. Create your own Telegram bot by contacting [@BotFather](https://t.me/BotFather).
3. Rename the included file `config.sample.json` to `config.json` and fill in the required config values. (You can retrieve your personal chat ID by using [@echo_id_bot](https://t.me/echo_id_bot).)  
_Note: If `check_rate` is set to a number x greater 0, the bot will check for new results every x minutes._
3. Run the bot:
```
python3 bot.py
```

(c) 2019 cfalxp
