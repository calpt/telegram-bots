from .menu_enums import *
import requests
import sys
from lxml import etree
from datetime import datetime

_url = "https://www.tucan.tu-darmstadt.de/static/TUCaN-app/mensen/"
_locs = {
    Location.STADT : "dishes_0.xml",
    Location.LIWI : "dishes_1.xml"
}

class TucanScraper:
    def __init__(self):
        self.id = MenuSource.TUCAN

    def get_menu(self, loc):
        page = requests.get(_url + _locs[loc])
        if page.status_code != 200:
            print("{} - ERROR: Requested menu file not available.".format(__name__), file=sys.stderr)
            return {}
        root = etree.fromstring(page.content)
        dishes = {}
        for dish in root:
            dishdict = {}
            dishdict["name"] = dish.find("{*}name").text
            dishdict["location"] = dish.find("{*}category").text
            dishdict["price"] = dish.find("{*}priceStudent").text
            additives = []
            for add in dish.find("{*}additives"):
                additives.append(add.text)
            dishdict["additives"] = additives
            date = dish.find("{*}day").text
            if date in dishes:
                dishes[date].append(dishdict)
            else:
                dishes[date] = [dishdict]
        download = {
            'id': self.id,
            'location': loc,
            'date': datetime.now().isoformat(sep=' '),
            'dishes': dishes
        }
        return download
