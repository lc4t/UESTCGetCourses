# -*- coding:UTF-8 -*-
__author__ = 'lc4t'

import requests
from requests.utils import cookiejar_from_dict, dict_from_cookiejar
import re
import json
from bs4 import BeautifulSoup as bs
import lxml
import getpass
import hashlib
import time
import icalendar
import pytz
from datetime import datetime, timedelta

def generate_first_datetime(year, month, day):
    user_input = datetime(year, month, day, 0, 0)
    return user_input - timedelta(days=user_input.weekday())

def get_start_end(first, start_sort=1, course_long=2, day=1, week=1):
    '''
    first是第一周第一节课
    start_sort 第几节课开始
    course_long 上几节
    day 周几
    week 第几周
    '''
    start_time_dict = {
        1: (8, 30),
        2: (9, 20),
        3: (10, 20),
        4: (11, 10),
        5: (14, 30),
        6: (15, 20),
        7: (16, 20),
        8: (17, 10),
        9: (19, 30),
        10: (20, 20),
        11: (21, 10),
        12: (22, 00),
    }
    start_time = start_time_dict[start_sort]
    start = first + timedelta(hours=start_time[0], minutes=start_time[1], days=day - 1 + (week - 1) * 7)
    end_time = start_time_dict[start_sort + course_long - 1]
    end = first + timedelta(hours=end_time[0], minutes=end_time[1] + 45, days=day - 1 + (week - 1) * 7)
    return start, end


class uestc():
    def __init__(self):
        self.r = requests.Session()
        self.loginURL = "http://idas.uestc.edu.cn/authserver/login?service=http://portal.uestc.edu.cn/index.portal"
        self.indexURL = 'http://portal.uestc.edu.cn/index.portal'
        self.urlEAS = "http://eams.uestc.edu.cn/eams/"
        self.urlCurriculumManager = "http://eams.uestc.edu.cn/eams/home!childmenus.action?menu.id=844"
        self.urlMygrade = "http://eams.uestc.edu.cn/eams/teach/grade/course/person!historyCourseGrade.action?projectType=MAJOR"
        self.urlCourses = "http://eams.uestc.edu.cn/eams/courseTableForStd!courseTable.action"
        self.headers = {
            'Proxy-Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/46.0.2490.86 Safari/537.36',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Referer': 'http://portal.uestc.edu.cn/index.portal',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.8',
        }
        self.ids = None

    def login_cookies(self, cookies_dict):
        url = self.urlEAS + 'home.action'
        self.r.cookies = cookiejar_from_dict(cookies_dict, cookiejar=None, overwrite=True)
        login_r = self.r.get(url, headers=self.headers)
        result = login_r.text
        AC = re.findall('href="/eams/security/my.action"',result)
        if AC:
            print('cookie login success')
            return json.dumps(cookies_dict)
        else:
            return False


    def login_password(self, username, password):
        self.r.cookies.clear()
        loginURLCaptcha = "http://idas.uestc.edu.cn/authserver/needCaptcha.html?username=%s&_=%s" % (username, str(time.time()))
        visit_r = self.r.get(url=self.loginURL, headers=self.headers)
        check_captcha_r = self.r.get(loginURLCaptcha, headers=self.headers)
        if check_captcha_r.text == 'true':
            print(username + 'need captcha')
            return False
        params_lt = re.findall('name="lt" value="(.*)"/>',visit_r.text)[0]
        post_data = {
            'username': username,
            'password': password,
            'lt': params_lt,
            'dllt': 'userNamePasswordLogin',
            'execution': 'e1s1',
            '_eventId': 'submit',
            'rmShown': '1'
        }
        login_r = self.r.post(url=self.loginURL, data=post_data, headers=self.headers)
        result = login_r.text
        print(result)
        AC = re.findall(u'href="http://eams.uestc.edu.cn/eams/"><b>教务系统', result)
        if AC:
            res = self.get_eas()
            return json.dumps({'JSESSIONID': res})
        else:
            return False


    def get_courses(self, pretty = False):
        self.get_index()
        self.get_eas()
        self.get_curriculum_manager()
        raw_grades = self.get_my_grade()
        if pretty:
            grade = GradeAnalyzer(raw_grades)
            grade.printTotal()
            return grade.printCourses()
        else:
            return raw_grades

    #first step to login, this is index page
    def get_index(self):     # login index page
        _ = self.r.get(self.indexURL, headers=self.headers)
        return _.text



    # second step to get course, this is the page after login
    def get_eas(self):    #  click educational administration system
        _ = self.r.get(url=self.urlEAS, headers=self.headers)
        JSESSIONID = _.url.split('=')[-1]
        _ = self.r.get(url=self.urlEAS+'home.action', headers=self.headers)
        return JSESSIONID

    def get_curriculum_manager(self):  # table
        _ = self.r.get(url=self.urlCurriculumManager, headers=self.headers)
        return _.text


    def get_my_grade(self):
        _ = self.r.get(url=self.urlMygrade, headers=self.headers)
        return _.text

    def get_semester(self):
        self.r.get('http://eams.uestc.edu.cn/eams/courseTableForStd.action', headers=self.headers)
        data = {
            "tagId": "semesterBar9375549431Semester",
            "dataType": "semesterCalendar",
            "empty": "true"
        }

        _ = self.r.post('http://eams.uestc.edu.cn/eams/dataQuery.action', data)
        semester = lazyJsonParse(_.text)['semesters']
        ans = []
        for k, v in semester.items():
            for i in range(2):
                _ = {
                    'id': v[i]['id'],
                    'name': v[i]['name'],
                    'schoolYear': v[i]['schoolYear'],
                    'text': '%s学年 第%s学期' % (v[0]['schoolYear'], v[i]['name'])
                }
                ans.append(_)
        self.r.post("http://eams.uestc.edu.cn/eams/dataQuery.action", data={'dataType': "projectId"})
        self.r.post("http://eams.uestc.edu.cn/eams/dataQuery.action", data={'entityId': ""})
        return ans

    def get_course_ids(self):
        if not self.ids:
            _ = self.r.get("http://eams.uestc.edu.cn/eams/courseTableForStd.action").text
            # print(_)
            self.ids = re.findall(r'"ids"\,"(\d+?)"', _)[0]
        return self.ids

    def get_course_by_id(self, semester_id):
        data = {
            'ignoreHead': 1,
            'setting.kind': 'std',
            'startWeek': 1,
            'semesterId': semester_id,
            'ids': self.get_course_ids()
        }
        _ = dict_from_cookiejar(self.r.cookies)
        headers = {
            'Cookie': 'JSESSIONID=%s; semester.id=%d' % (_['JSESSIONID'], semester_id)
        }
        _ = requests.post('http://eams.uestc.edu.cn/eams/courseTableForStd!courseTable.action', data=data, headers=headers)
        # _ = self.r.post('http://eams.uestc.edu.cn/eams/courseTableForStd!courseTable.action', data=data, headers=self.headers)

        text = re.findall('activity\s=\snew\sTaskActivity\("(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(.*?)","(\d+)"\);\s+((index\s=\d*\*unitCount\+\d+;\s+table0\.activities\[index\]\[table0\.activities\[index\]\.length\]=activity;\s+)+)', _.text)
        ans = []
        for i in text:
            teacher_name = i[1]
            course_name = i[3]
            place = i[5]
            week_len = len(i[6])
            week = []
            for w in range(0, week_len, 1):
                if i[6][w] == '1':
                    week.append(w)
            day = []
            #
            for sort in re.findall('index\s=(\d+)\*unitCount\+(\d+)', i[7]):
                day.append({int(sort[0]) + 1: int(sort[1]) + 1})

            _ = {
                'teacher_name': teacher_name,
                'course_name': course_name,
                'place': place,
                'week': week,
                'day': day
            }
            ans.append(_)

        return ans

        '''
        1: {
            1: 2
        星期一: {
            第1节课: 持续2节课
        }
        星期k: {
            第v节课: 持续vmax-vmin + 1
            _k : _v
        }
        }
        '''

        # return new_day

    def get_exam_by_id(self, semester_id):
        _ = self.r.get('http://eams.uestc.edu.cn/eams/stdExamTable!examTable.action?semester.id=%d&examType.id=1' % (semester_id))
        html = bs(_.text, 'lxml')
        ans = []
        for one in html.select('.brightStyle') + html.select('.grayStyle'):
            i = one.select('td')
            # course_id = i[0]
            if '考试情况尚未发布' in i[2].text:
                continue
            course_name = i[1].text
            # exam_date = i[2]
            # exam_datetime = i[3].text
            week, date, timeline = re.findall('第(\d+)周\s星期.\((\d{4}-\d{2}-\d{2})\) (\d{2}:\d{2}-\d{2}:\d{2})', i[3].text)[0]
            date = date.split('-')
            timeline = timeline.split('-')
            start = timeline[0].split(':')
            end = timeline[1].split(':')
            start_time = datetime(int(date[0]), int(date[1]), int(date[2]), int(start[0]), int(start[1]))
            end_time = datetime(int(date[0]), int(date[1]), int(date[2]), int(end[0]), int(end[1]))

            location = '%s@%s' % (i[4].text, i[5].text)
            # sit = i[5].text
            # status = i[6].text
            # other = i[7].text
            _ = {

                'course_name': course_name,
                'start_time': start_time,
                'end_time': end_time,
                'week': week,
                'location': location
            }
            ans.append(_)
        # print(ans)
        return ans

    def get_course_ics(self, course_list, first, name):

        ics = icalendar.Calendar()
        ics.add('PRODID', '-//Uestc Course//lc4t.me//')
        ics.add('version', '2.0')
        ics.add('X-WR-CALNAME', '%s的课程表' % name)
        ics.add('X-WR-CALDESC', 'uestc %s的课程表' % name)
        ics.add('X-WR-TIMEZONE', "Asia/Shanghai")
        ics.add('CALSCALE', 'GREGORIAN')
        ics.add('METHOD', 'PUBLISH')

        tz = pytz.timezone('Asia/Shanghai')

        for course in course_list:
            for week in course['week']:

                day = -1
                course_start = -1
                course_long = 0
                day_list = set()
                for d in course['day']:
                    for k,v in d.items():
                        if day == -1 and day != k:
                            day = k
                            course_long += 1
                            course_start = v
                        elif day != -1 and day != k:
                            day_list.add((day, course_long))
                            course_long = 1
                            day = k
                            course_start = v
                        elif day == k:
                            course_long += 1
                        else:
                            print('error')
                day_list.add((day, course_start, course_long))

                for i in day_list:
                    e = icalendar.Event()
                    start_time, end_time = get_start_end(first, i[1], i[2], i[0], week)
                    e.add('dtstart', tz.localize(start_time))
                    e.add('dtend', tz.localize(end_time))
                    e['summary'] = '(%s)%s [%s] @%s' % (week, course['course_name'], course['teacher_name'], course['place'])
                    e['location'] = icalendar.vText(course['place'])
                    e['TRANSP'] = icalendar.vText('OPAQUE')
                    e['status'] = 'confirmed'
                    _now = datetime.now()
                    now = tz.localize(_now)
                    e.add('created', now)
                    e.add('DTSTAMP', _now)
                    md5 = hashlib.md5()
                    md5.update(('%s%s' % (str(now), course['course_name'])).encode())
                    e["UID"] = '%s@lc4t.me' % md5.hexdigest()
                    e.add('LAST-MODIFIED', _now)
                    ics.add_component(e)
                    print('%s-%s %s' % (str(start_time), str(end_time), e['summary']))
        return ics

    def get_exam_ics(self, exam_list, name):
        ics = icalendar.Calendar()
        ics.add('PRODID', '-//Uestc Exam//lc4t.me//')
        ics.add('version', '2.0')
        ics.add('X-WR-CALNAME', '%s的考试' % name)
        ics.add('X-WR-CALDESC', 'uestc %s的课程表' % name)
        ics.add('X-WR-TIMEZONE', "Asia/Shanghai")
        ics.add('CALSCALE', 'GREGORIAN')
        ics.add('METHOD', 'PUBLISH')

        tz = pytz.timezone('Asia/Shanghai')


        for i in exam_list:
            e = icalendar.Event()

            # start_time, end_time = get_start_end(first, i[1], i[2], i[0], week)
            e.add('dtstart', tz.localize(i['start_time']))
            e.add('dtend', tz.localize(i['end_time']))
            e['summary'] = '(%s)%s [%s]' % (i['week'], i['course_name'], i['location'])

            e['location'] = icalendar.vText(i['location'])
            e['TRANSP'] = icalendar.vText('OPAQUE')
            e['status'] = 'confirmed'
            _now = datetime.now()
            now = tz.localize(_now)
            e.add('created', now)
            e.add('DTSTAMP', _now)
            md5 = hashlib.md5()
            md5.update(('%s%s' % (str(now), i['course_name'])).encode())
            e["UID"] = '%s@lc4t.me' % md5.hexdigest()
            e.add('LAST-MODIFIED', _now)
            ics.add_component(e)
            print('%s-%s %s' % (str(i['start_time']), str(i['end_time']), e['summary']))
        return ics

def lazyJsonParse(j):
    j = re.sub(r"{\s*'?(\w)", r'{"\1', j)
    j = re.sub(r",\s*'?(\w)", r',"\1', j)
    j = re.sub(r"(\w)'?\s*:", r'\1":', j)
    j = re.sub(r":\s*'(\w+)'\s*([,}])", r':"\1"\2', j)
    return json.loads(j)

a = uestc()
jessionid = input('give me sessionid:')
if not a.login_cookies({"JSESSIONID": jessionid}):
    username = input('give me username:')
    password = getpass.getpass('give me password:')
    if not a.login_password(username, password):
        print('login failed')
        exit()

name = input('your name:')
for i in a.get_semester():
    print(i['id'], i['text'])
s_id = int(input('give me id:'))

# get courses
s = a.get_course_by_id(s_id)
print('give me one day in first week in the following 3 lines')
year = input('year:')
month = input('month:')
day = input('day:')
first = generate_first_datetime(int(year), int(month), int(day))
ics = a.get_course_ics(s, first, name).to_ical()
open('%s的课程表.ics' % (name), 'wb').write(ics)

# get exam
s = a.get_exam_by_id(s_id)
ics = a.get_exam_ics(s, name).to_ical()
open('%s的考试.ics' % (name), 'wb').write(ics)
