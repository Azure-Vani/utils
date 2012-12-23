#!/usr/bin/python2
# -*- coding: utf-8 -*-
import sys

encoding = 'utf-8'

if sys.getdefaultencoding() != encoding:
    reload(sys)
    sys.setdefaultencoding(encoding)

queryWord = " ".join(sys.argv[1:])

from urllib import urlopen

f = urlopen("http://dict.cn/%s"%(queryWord))
content = f.read()

from HTMLParser import HTMLParser

class MyParser(HTMLParser):
	def __init__(self):
		self.reset()
		self.tags = []
		self.ret = []
		self.basic = False
		self.phonetic = False

	def handle_starttag(self, tag, attrs):
		self.tags.append(tag)
		if tag == "div" and ("class", "layout basic") in attrs:
			self.basic = True
		if tag == "div" and ("class", "phonetic") in attrs:
			self.phonetic = True
	
	def handle_endtag(self, tag):
		self.tags.pop()
		if tag == "div":
			self.basic = False
	
	def handle_data(self, data):
		if self.tags and self.tags[-1] == "bdo" and self.phonetic:
			self.ret.append(data)
			self.phonetic = False
		if self.tags and self.tags[-1] == "strong" and self.basic:
			self.ret.append(data)
	
	def getResult(self):
		for i in self.ret:
			print i

parser = MyParser()
parser.feed(content)
parser.getResult()
