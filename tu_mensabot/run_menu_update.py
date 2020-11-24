#!/usr/bin/env python3

# -- run_menu_update.py --
# This script fetches new menu data from the sources specified in the configuration.
# It downloads menus to the files configured in the section 'menu_locations' of the
# config file.
# Usage: `python run_menu_update.py [config_file]`
# 

import sys
import json
from menu import menudownload

# use 'config.json' as default config file
if len(sys.argv) > 1:
    config_file = sys.argv[1]
else:
    config_file = "config.json"
with open(config_file, 'r') as f:
    config = json.load(f)

# download menus
sources = config.get("menu_sources")
for location, file in config.get("menu_locations").items():
    menudownload.download_to_file(file, location, sources)
