import requests
from lxml import html, etree
from datetime import datetime
import random
from collections import OrderedDict

_url = "https://seatfinder.bibliothek.kit.edu/ulb_darmstadt/bargraph.php"
locs = OrderedDict([
    ("ULBSM4", "Stadtmitte 4. Stock"),
    ("ULBSM3", "Stadtmitte 3. Stock"),
    ("ULBSM2", "Stadtmitte 2. Stock"),
    ("ULBSM1", "Stadtmitte 1. Stock"),
    ("ULBLW3", "Lichtwiese 3. Stock"),
    ("ULBLW2", "Lichtwiese 2. Stock"),
    ("ULBLW1", "Lichtwiese 1. Stock")
])
person = [
    ["\U0001f468", "\U0001f469"],
    ["", "\U0001f3fb", "\U0001f3fc", "\U0001f3fd", "\U0001f3fe"],
    ["\u200D"],
    ["\U0001f4bb"]*10 + ["\U0001f52c"] + ["\U0001f3a8"]
]

def _get_workplaces_loc(location):
    response = requests.get(_url, {"location": location})
    html_doc = html.fromstring(response.content)
    class_elem = html_doc.xpath("//div[@class='seatfinder-occupied-seats']")[0]
    opened = class_elem.xpath(".//@data-status")[0] == 'open'
    total_seats = int(class_elem.xpath(".//@data-total-seats")[0])
    try:
        free_seats = int(class_elem.xpath(".//@data-free-seats")[0])
    except:
        free_seats = 0
    return opened, total_seats, free_seats

def get_workplaces():
    d = OrderedDict()
    for loc in locs:
        d[loc] = _get_workplaces_loc(loc)
    return {"data": d, "time": datetime.now()}

def get_random_person():
    p = ""
    for selection in person:
        p += random.choice(selection)
    return p

if __name__ == "__main__":
    print(get_workplaces())
