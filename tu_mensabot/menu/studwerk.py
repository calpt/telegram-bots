from .menu_enums import *
import requests
import re
from lxml import html, etree
import json
from time import strftime, strptime, time

_url = "http://studierendenwerkdarmstadt.de/hochschulgastronomie/speisekarten/"
_locs = {
    Location.STADT : "stadtmitte",
    Location.LIWI : "lichtwiese",
    Location.SCHOEFFERSTR: "schoefferstrasse"
}
# infers appropriate attributes from svg path
_icon_dict = { 
    "M44.162" : "35",
    "M39.611" : "28",
    "M61.57" : "31",
    "M16.818" : "32",
    "M11.588" : "30",
    "M103.08" : "25",
    "M98.422" : "29",
    "M117.674" : "26"
}

class StudwerkScraper:
    def __init__(self):
        self.id = MenuSource.STUDWERK

    def _extract_data(self, menu_item):
        dict_meal = {}
        dict_meal['name'] = menu_item.xpath(".//span[@class='fmc-item-title']/text()")[0]
        dict_meal['location'] = menu_item.xpath(".//span[@class='fmc-item-location']/text()")[0]
        dict_meal['price'] = re.sub('\s+', '', menu_item.xpath(".//span[@class='fmc-item-price']/text()")[0])
        type_ident = menu_item.xpath(".//svg//path/@d")[0]
        dict_meal['additives'] = []
        for ident, type_name in _icon_dict.items():
            if type_ident.startswith(ident):
                dict_meal['additives'].append(type_name)
        return dict_meal

    def _get_menu(self, content, xpath):
        menu = {}
        tree = html.fromstring(content)
        section_day = tree.xpath(xpath)[0]
        menu_list = section_day.xpath(".//ul[@class='fmc-items']/li")
        items = []    
        for menu_item in menu_list:
            items.append(self._extract_data(menu_item))
        date_string = section_day.xpath(".//div[@class='fmc-head']/span/text()")[0]
        date = strptime(date_string, "%d.%m.%Y")
        menu[strftime("%Y-%m-%d", date)] = items
        return menu

    def get_menu(self, loc):
        canteen = _locs[loc]
        days = {}
        page = requests.get("{0}/{1}".format(_url, canteen))
        for i in range(1, 6):
            days.update(self._get_menu(page.content, "//section[@class='fmc-day ' or @class='fmc-day fmc-today'][{0}]".format(i)))
        download = {
            'id': self.id,
            'location': loc,
            'date': strftime('%Y-%m-%d %T'),
            'dishes': days
        }
        return download
