#!/usr/bin/env python3
from .menu_enums import *
from . import tucan, studwerk
from datetime import datetime
import json
import argparse

_scrapers = {
    MenuSource.TUCAN: tucan.TucanScraper(),
    MenuSource.STUDWERK: studwerk.StudwerkScraper()
}

def download_to_file(file, location, sources):
    for source in sources:
        scraper = _scrapers[source]
        menu = scraper.get_menu(location)
        # Check if menu contains current data
        now = datetime.now()
        if now.strftime("%Y-%m-%d") in menu["dishes"] or now.weekday() > 4:
            break
    with open(file, 'w') as f:
        json.dump(menu, f, indent=3)

if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("file", help="output file")
    arg_parser.add_argument("-s", "--source", help="the menu source",
                            choices=[MenuSource.TUCAN, MenuSource.STUDWERK], default=MenuSource.TUCAN)
    arg_parser.add_argument("--loc", help="location of the canteen",
                            choices=[Location.STADT, Location.LIWI, Location.SCHOEFFERSTR], default=Location.STADT)
    args = arg_parser.parse_args()
    download_to_file(args.file, args.loc, [args.source])
