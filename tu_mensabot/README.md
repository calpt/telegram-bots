<p align="center">
<img src="resources/mensabot_icon.png" width="100px"/>
</p>

# tu_mensabot

__On Telegram: https://t.me/tu_mensabot__

## Setup

1. Clone this repository and install required Python dependencies:
    ```
    python -m pip install -r requirements.txt
    ```
2. Create your own Telegram bot by contacting [@BotFather](https://t.me/BotFather).
3. Copy the file `config.sample.json` and rename it to `config.json`.
   Then, insert the token of your bot in the field `token`.
   For more configuration options, see [->Configuration](#Configuration).
4. Fetch the latest menu data (for more, see [->Menu Data](#Menu%20Data)):
    ```
    python run_menu_update.py
    ```
5. Run the bot:  
    ```
    python mensabot.py
    ```

## Configuration

All configuration should be stored in a main `config.json` file. A template file showing the structure is included in the file `config.sample.json`.
The relevant configuration options are:

- **token**: The Telegram Bot API token of the bot.
- **maintenance_mode**: If set to `true`, the bot will answer all requests with a generic maintenance message.
- **menu_sources**: Specifies the common names of the menu data sources in the order they will be queried (see [->Menu Data](#Menu%20Data)).
- **menu_locations**: A dictionary mapping separat canteens (specified by their common names) to the files containing the corresponding menu data.
- **times**: List of times the newsletter should execute (first time is administrative).
- **db_config**: Database configuration. Requires db submodule. To activate database usage, e.g. use the following settings:
```json
"db_config": {
    "main": "mensabot.db",
    "feedback": "feedback.db"
}
```

## Menu Data

The modules related to retrieving and extracting menu data can be found in the folder `menu/`. To simply fetch the latest menu data with the options specified in the [->Configuration](#Configuration), run `python run_menu_update.py`. The output files are JSON dictionaries. 
Advanced topics are described below:

#### Menu Sources
Menu data can be scraped from different web sources. A custom scraper class needs to be implemented for every source. The currently supported menu data sources are listed in `menu/menu_enums.py`.

#### Locations
You can use the module `menu/menudownload.py` to download menu data from a specified source and for a specified canteen (type `python -m menu.menudownload -h` for more). One data dictionary will be created for each canteen location.

## Copyright

© 2018-2020, calpt.
Released under MIT License.
