#!/usr/bin/env python2
# -*- coding: utf-8 -*-

from sys import argv

queryWord = argv[1]

from urllib import urlopen, urlencode

queryString = urlencode({
    'utf8': 'true',
    'q': queryWord,
})
handler = urlopen("http://dict.cn/ws.php?%s" %queryString)
content = handler.read()

from HTMLParser import HTMLParser

class MyParser(HTMLParser):
    def __init__(self):
        self.reset()
        self.tag = []
        self.result = []

    def handle_starttag(self, tag, attrs):
        self.tag.append(tag)
    
    def handle_data(self, data):
        if self.tag:
            if self.tag[-1] in ["def"]:
                self.result.append(data)

    def handle_endtag(self, tag):
        self.tag.pop()

    def getResult(self):
        for i in self.result:
            print i

    
parser = MyParser()
parser.feed(content)
parser.getResult()
