#!/usr/bin/python
#-*- coding: utf-8 -*-

import sys
import re
from time import sleep

import time

import httplib, urllib, re
import xml.dom.minidom as xmldom

import smtplib
from email.mime.text import MIMEText

reload(sys)
sys.setdefaultencoding( "utf-8" )

FROM_EMAIL_HOST = "" # the email HOST sending the notification, such as 126.com or mail.pku.edu.cn
EMAIL_USER = "" # the username for the email host
EMAIL_PASSWD = "" # the password for the email host
TO_EMAIL = "" # the email ADDRESS receiving the notification, such as user0@gmail.com

DEAN_USERNAME = "" # the username for dean.pku.edu.cn
DEAN_PASSWORD = "" # the password for dean.pku.edu.cn

from functools import wraps
import errno
import os
import signal

class TimeoutError(Exception):
    pass

def timeout(seconds=10, error_message=os.strerror(errno.ETIME)):
    def decorator(func):
        def _handle_timeout(signum, frame):
            raise TimeoutError(error_message)

        def wrapper(*args, **kwargs):
            signal.signal(signal.SIGALRM, _handle_timeout)
            signal.alarm(seconds)
            try:
                result = func(*args, **kwargs)
            finally:
                signal.alarm(0)
            return result

        return wraps(func)(wrapper)

    return decorator

class Email:
    def __init__(self):
        self.mail_host = FROM_EMAIL_HOST
        self.mail_user = EMAIL_USER
        self.mail_pass = EMAIL_PASSWD
        self.mail_postfix = FROM_EMAIL_HOST

    @timeout(100, "timeout while sending email")
    def send(self, content, To="", Me="Requiem", Subject=""):
        Me = Me + "<" + self.mail_user + "@" + self.mail_postfix + ">"
        To = TO_EMAIL if To == "" else To
        msg = MIMEText(content, _subtype='plain',_charset='utf-8')
        msg['Subject'] = "[%s] "%(time.strftime('%Y-%m-%d %H:%M:%S',time.localtime(time.time()))) + Subject
        msg['From'] = Me
        msg['To'] = To
        for i in range(0, 3):
            try:
                server = smtplib.SMTP()
                server.connect(self.mail_host)
                server.login(self.mail_user,self.mail_pass)
                server.sendmail(Me, To, msg.as_string())
                server.close()
                print "[Info] Send mail %s"%(msg['Subject'])
                return True
            except Exception, e:
                print "[Error]",str(e)
        return False

class Job:
    def __init__(self):
        self.username = DEAN_USERNAME
        self.password = DEAN_PASSWORD
        tmp = self.gen_list()
        self.init_list = {}
        self.add_class(tmp)

    def get_class_index(self, i):
        return i[2]

    def add_class(self, items):
        for i in items:
            self.init_list[self.get_class_index(i)] = i

    @timeout(100, "timeout while fetching grades")
    def fetch_grades(self):
        print "Begin fetching..."
        conn = httplib.HTTPSConnection('iaaa.pku.edu.cn')
        conn.request('POST', '/iaaa/oauth.jsp', urllib.urlencode({'appID': 'dean', 'appName': '北京大学教务部网上学生服务中心', 'redirectUrl': 'http://dean.pku.edu.cn/student/center2.php'}), {'Content-Type': 'application/x-www-form-urlencoded'})
        res = conn.getresponse()
        jsessionid = re.search(r'JSESSIONID=([^;]+)', res.getheader('Set-Cookie')).group(1)
        res.read()
        for i in range(0, 2):
            try:
                conn.request('POST', '/iaaa/oauthlogin.do', urllib.urlencode({'appid': 'dean', 'userName': self.username, 'password': self.password, 'redirUrl': 'http://dean.pku.edu.cn/student/center2.php'}), {'Cookie': 'JSESSIONID=%s' % jsessionid, 'Content-Type': 'application/x-www-form-urlencoded'})
                break
            except:
                conn.close()
                conn = httplib.HTTPSConnection('iaaa.pku.edu.cn')
        res = conn.getresponse()
        s = res.read()
        conn.close()
        if s.find('"success":true') == -1:
            err = re.search(r'"msg":"([^"]*)"', s).group(1)
            raise Exception('Dean error:%s'%(err))
        token = re.search('"token":"(\w+)"', s).group(1)
        conn = httplib.HTTPConnection('dean.pku.edu.cn')
        conn.request('GET', '/student/center2.php?token=%s' % token)
        res = conn.getresponse()
        phpsessid = re.search(r'PHPSESSID=([^;]+)', res.getheader('Set-Cookie')).group(1)
        print "[Session] %s"%(phpsessid)
        res.read()
        conn.request('GET', '/student/grade.php?PHPSESSID=%s' % phpsessid, headers = {'Cookie': 'PHPSESSID=%s' % phpsessid })
        res = conn.getresponse()
        response = res.read().decode('gbk').encode('utf-8')
        conn.request('GET', '/student/exit.php?PHPSESSID=%s' % phpsessid, headers = {'Cookie': 'PHPSESSID=%s' % phpsessid })
        conn.getresponse().read()
        conn.close()
        print "End fetching..."
        return response

    def parse_item(self, regex_obj):
        str = regex_obj.group(0)
        str = re.sub(r"(<tr>|.?)<td>([^<]*)</td>", r"\2$", str).strip("$").split("$")
        return str

    def parse_grades(self, grades):
        results = []
        for i in re.finditer(r'<tr>(<td>[^<]*</td>){8}', grades):
            item = self.parse_item(i)
            results.append(item)
        return results

    def gen_list(self):
        grades_str = self.fetch_grades()
        grades_list = self.parse_grades(grades_str)
        if grades_list == []:
            raise Exception("Fetched html format error.")
        return grades_list

    def check_class(self, cur_list):
        new_item = []
        for item in cur_list:
            if not self.init_list.has_key(self.get_class_index(item)):
                new_item.append(item)
        return new_item

    def deliver(self, items):
        content = ""
        for item in items:
            content += "%s 成绩%s分, 绩点%s。\n"%(item[5], item[3], item[7])
        m = Email()
        return m.send(content, Subject="出分啦！")

    def run(self):
        count = 0
        while True:
            if count % 60 == 0:
                m = Email()
                tmp = m.send("Count: %d"%(count), Subject = "Heartbeat!")

            count += 1
            cur_list = self.gen_list()
            news = self.check_class(cur_list)
            if news != []:
               delivered = self.deliver(news)
               if delivered:
                   self.add_class(news)
            print "Round %d..."%(count)
            sleep(120)

if __name__ == "__main__":
    while True:
        try:
            now = Job()
            now.run()
        except Exception as e:
            m = Email()
            m.send("[Exception] " + str(e), Subject = "Exception!")
            sleep(120)
