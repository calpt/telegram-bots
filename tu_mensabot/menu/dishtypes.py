import emoji

# Maps additive codes to icons and tags according to https://www.tucan.tu-darmstadt.de/static/TUCaN-app/mensen/additives.xml
dishtypes = {
    "25" : [":fish:", "fisch"],
    "26" : [":cow_face:", ":pig_face:", "rind", "schwein"],
    "27" : [":boar:", "wild"],
    "28" : [":carrot:", "vegetarisch"],
    "29" : [":pig_face:", ":chicken:", "schwein", "gefluegel"],
    "30" : [":cow_face:", "rind"],
    "31" : [":chicken:", "gefluegel"],
    "32" : [":pig_face:", "schwein"],
    "33" : [":chicken:", ":fish:", "gefluegel", "fisch"],
    "34" : ["kalb"],
    "35" : [":seedling:", "vegan"],
    "36" : ["pasta"],
    "37" : ["lamm"],
    "38" : [":seedling:", ":pig_face:", "vegan", "schwein"],
    "39" : [":pizza:", "pizza"],
    "40" : [":fish:", ":pig_face:", "fisch", "schwein"],
    "41" : ["gans"],
    "42" : ["wurst"],
    "43" : [":sunflower:", "bio"]
}
dishicons = {emoji.emojize(t_list[0]): t_list[1] for t_list in dishtypes.values() if len(t_list) == 2}

def matches(tag, additives):
    for add in additives:
        if add in dishtypes and tag in dishtypes[add]:
            return True
    return False

def emojize(additive):
    if additive in dishtypes:
        ics = [emoji.emojize(item) for item in dishtypes[additive] if item.startswith(':')]
        return "".join(ics)
    else:
        return ""

def get_list(d_list=dishicons.keys()):
    entries = []
    for icon in d_list:
        entries.append("{}  -  {}".format(icon, dishicons[icon].title()))
    return entries
