import requests
import re
from lxml import html

_DOMAIN="https://www.tucan.tu-darmstadt.de"
_URL=_DOMAIN+"/scripts/mgrqispi.dll"

class PRGNAME:
    COURSE_RESULTS="COURSERESULTS"
    EXAM_RESULTS="EXAMRESULTS"
    EXAMS="MYEXAMS"

class Tucan():
    def __init__(self, username, password):
        self.login_data=(username, password)
        self.sess = requests.Session()
        self._login(*self.login_data)

    def _login(self, username, password):
        data={
            'usrname': username, 'pass': password, 
            'APPNAME': 'CampusNet', 'PRGNAME': 'LOGINCHECK', 
            'ARGUMENTS': 'clino,usrname,pass,menuno',
            'clino': '000000000000001', 'menuno': '000344'
        }
        r = self.sess.post(_URL, data=data)
        match = re.search(r"ARGUMENTS=([\w\-]*,[\w\-]*),", r.headers["REFRESH"])
        self.arguments = match.group(1)

    def _get_page(self, prgname):
        params={'APPNAME': 'CampusNet', 'PRGNAME': prgname, 'ARGUMENTS': self.arguments}
        resp = self.sess.get(_URL, params=params)
        # check for timeout
        tree = html.fromstring(resp.text)
        title = tree.xpath("//div[@id='contentSpacer_IE']//h1/text()")[0]
        if title == "Timeout!":
            # re-login after timeout
            self._login(*self.login_data)
            resp = self.sess.get(_URL, params=params)
        resp.encoding='utf-8'
        return resp

    def _parse_float(self, s):
        try:
            return float(s.replace(",", "."))
        except ValueError:
            return None

    def get_course_results(self):
        """Retrieves the course results of the logged in user for the current semester.
        
        Returns:
            dict: dictionary including all chosen courses of this semester.
        """
        resp = self._get_page(PRGNAME.COURSE_RESULTS)
        tree = html.fromstring(resp.text)
        title = tree.xpath("//div[@id='contentSpacer_IE']//h1/text()")[0]
        title_match = re.search(r"Modulnoten (.+) für (.+)", title)
        data={'term': title_match.group(1), 'name': title_match.group(2)}
        tab_list = tree.xpath("//table[@class='nb list']/tbody")[0]
        courses=[]
        for l_row in tab_list[:-1]:
            course={}
            course['no']=l_row.xpath("./td[1]/text()")[0]
            course['name']=l_row.xpath("./td[2]/text()")[0]
            course['grade']=self._parse_float(l_row.xpath("./td[3]/text()")[0])
            course['credits']=int(l_row.xpath("./td[4]/text()")[0].split(",")[0])
            course['status']=l_row.xpath("./td[5]/text()")[0].strip()
            courses.append(course)
        data['courses']=courses
        return data


if __name__ == "__main__":
    import sys
    tuc = Tucan(sys.argv[1], sys.argv[2])
    for course in tuc.get_course_results()['courses']:
        print(course)
