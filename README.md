# UESTCGetCourses
get course from uestc, convert it to  xxx.ics


# Usage

sudo pip3 install -r requirements.txt -i https://pypi.mirrors.ustc.edu.cn/simple/
python3 get_courses.py

1. input JSESSIONID from eams.uestc.edu.cn/eams/,
if cookies test failed, input your username and password

2. input name of you. to create `name的课程表` `name的考试`
3. input an id, to select the semester
4. input three line: `year` `month` `day` for one day of first week, eg: `2016` `9` `1`
