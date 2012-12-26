import socket, sys, select, SocketServer, struct, time, os

def gettable(fpath):
	fp = open(fpath, 'rU')
	ret = []
	for s in fp.readlines():
		s = s.rstrip('\r\n')
		if len(s) == 0 or s[0] == '#': continue
		cur = filter(lambda x: len(x) > 0, s.replace('\t', ' ').split(' '))
		if len(cur) > 0: ret.append(cur)
	fp.close()
	return ret
def getconf():
	fp = open('proxy.conf', 'rU')
	ret = []
	cur = dict()
	for s in fp.readlines():
		s = s.rstrip('\r\n')
		if len(s) == 0 or s[0] == '#': continue
		if s[0: 5] == 'type=':
			if len(cur) > 0:
				ret.append(cur)
				cur = dict()
		pos = s.find('=')
		if pos != -1:
			tmp = s[pos + 1: ]
			if tmp[0] == '%': tmp = gettable(tmp[1: ])
			cur[s[0: pos]] = tmp
	if len(cur) > 0: ret.append(cur)
	fp.close()
	return ret

class ProxyException(Exception):
	def __init__(self, value):
		self.value = value
	def __str__(self):
		return repr(self.value)
def parsedns(domain, flag1, server, flag2, conf):
	if flag2:
		sock = socket.socket(socket.AF_INET6, socket.SOCK_DGRAM)
	else:
		sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	if flag1:
		ch = '\x1c'
	else:
		ch = '\x01'
	msg = '\x05\x16\x01\x00\x00\x01\x00\x00\x00\x00\x00\x00'
	msg += reduce(lambda x, y: x + chr(len(y)) + y, ('.' + domain).split('.'))
	msg += '\x00\x00' + ch + '\x00\x01'
	msgr = None
	for i in range(0,int(conf['dnsattempt'])):
		sock.sendto(msg, (server, 53))
		if select.select([sock], [], [], int(conf['dnstimeout']))[0]:
			msgr = sock.recv(65536)
			break
	sock.close()
	if msgr == None: raise ProxyException('cannot connect to dns server')
	if ord(msgr[3]) % 16 != 0: raise ProxyException('cannot get host')
	num = struct.unpack('>H', msgr[6: 8])[0]
	msgr = msgr[len(msg): ]
	while num > 0:
		pos = msgr.find('\x00')
		if msgr[pos + 1] == ch:
			if flag1:
				return socket.inet_ntop(socket.AF_INET6, msgr[pos + 10: pos + 26])
			else:
				return socket.inet_ntop(socket.AF_INET, msgr[pos + 10: pos + 14])
		else:
			msgr = msgr[pos + 10 + ord(msgr[pos + 9]): ]
		num -= 1
	raise ProxyException('cannot get host')

class ThreadingTCPServer(SocketServer.ThreadingMixIn, SocketServer.TCPServer): pass
class Socks5Server(SocketServer.StreamRequestHandler):
	def handle_tcp(self, sock, remote):
		fdset = [sock, remote]
		while True:
			r, w, e = select.select(fdset, [], [])
			if sock in r:
				msg = sock.recv(4096)
				#fp.write('\n==================begin of message=============\n')
				#fp.write(msg)
				#fp.write('\n===================end of message==============\n')
				time.sleep(0.0001)
				if len(msg) == 0 or remote.sendall(msg) != None: break
			if remote in r:
				msg = remote.recv(4096)
				#fp.write('\n++++++++++++++++++begin of message+++++++++++++\n')
				#fp.write(msg)
				#fp.write('\n+++++++++++++++++++end of message++++++++++++++\n')
				time.sleep(0.0001)
				if len(msg) == 0 or sock.sendall(msg) != None: break
	def recvall(self, sock, count):
		data = ''
		while len(data) < count:
			d = sock.recv(count - len(data))
			if not d: raise ProxyException('connection closed unexpectedly')
			data = data + d
		return data
	def reply(self, remote, flag):
		local = remote.getsockname()
		if flag:
			return '\x05\x00\x00\x04' + socket.inet_pton(socket.AF_INET6, local[0]) + struct.pack('>H', local[1])
		else:
			return '\x05\x00\x00\x01' + socket.inet_pton(socket.AF_INET, local[0]) + struct.pack('>H', local[1])
	def tcp_ipv6(self, addr, port, conf):
		if self.addrtype == 1: raise ProxyException('addrtype not supported by this method')
		remote = socket.socket(socket.AF_INET6, socket.SOCK_STREAM)
		try:
			remote.settimeout(int(conf['timeout']))
		except: pass
		remote.connect((addr, port))
		remote.settimeout(None)
		return (remote, self.reply(remote, True))
	def tcp_nat64(self, addr, port, conf):
		addrtype = self.addrtype
		if self.addrtype == 1:
			try:
				for row in conf['nat64hosts']:
					if row[1] == addr:
						self.addrtype = 3
						addr = row[0]
						break
			except: pass
		if self.addrtype != 3: raise ProxyException('addrtype not supported by this method')
		res = self.tcp_ipv6(parsedns(addr, True, conf['server'], True, conf), port, conf)
		self.addrtype = addrtype
		return res
	def tcp_ipv4(self, addr, port, conf):
		if self.addrtype == 4: raise ProxyException('addrtype not supported by this method')
		remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		try:
			remote.settimeout(int(conf['timeout']))
		except: pass
		remote.connect((addr, port))
		remote.settimeout(None)
		return (remote, self.reply(remote, False))
	def tcp_socks5(self, addr, port, conf):
		remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		remote.connect((conf['server'], int(conf['port'])))
		remote.sendall('\x05\x00')
		if self.recvall(remote, 2)[1] != '\x00': raise ProxyException('socks5 connection failed')
		remote.sendall(data)
		reply = remote.recv(4096)
		if reply[1] != '\x00': raise ProxyException('socks5 connection failed')
		return (remote, self.reply(remote, False))
	def tcp_socks4(self, addr, port, conf):
		ip = socket.gethostbyname(addr)
		remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		remote.connect((conf['server'], int(conf['port'])))
		remote.sendall('\x04\x01' + struct.pack('>H', port) + socket.inet_pton(socket.AF_INET, ip) + 'vani\x00')
		if self.recvall(remote, 8)[1] != 'Z': raise ProxyException('socks4 connection failed')
		return (remote, self.reply(remote, False))
	def tcp_http(self, addr, port, conf):
		remote = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		remote.connect((conf['server'], int(conf['port'])))
		ip = socket.gethostbyname(addr)
		remote.sendall('CONNECT ' + ip + ':' + str(port) + ' HTTP/1.1\r\n\r\n')
		tmp = remote.recv(4096).split(' ')
		if len(tmp) < 2 or tmp[1] != '200': raise ProxyException('http tunnel connection failed')
		return (remote, self.reply(remote, False))
	def handle(self):
		try:
			print 'socks connection from ', self.client_address
			sock = self.connection
			# 1. Version
			sock.recv(512)
			sock.sendall('\x05\x00');
			# 2. Request
			if not select.select([sock], [], [], 5)[0]: return
			data = self.recvall(sock, 4)
			mode = ord(data[1])
			self.addrtype = ord(data[3])
			if self.addrtype == 1:  # IPv4
				data += self.recvall(sock, 4)
				addr = socket.inet_ntop(socket.AF_INET, data[4: ])
			elif self.addrtype == 3:	 # Domain name
				addr = self.recvall(sock, ord(self.recvall(sock, 1)[0]))
				data += addr
				try:
					socket.inet_pton(socket.AF_INET, addr)
					self.addrtype = 1
				except socket.error:
					try:
						socket.inet_pton(socket.AF_INET6, addr)
						self.addrtype = 4
					except socket.error: pass
			elif self.addrtype == 4:	 # IPv6
				data += self.recvall(sock, 16)
				addr = socket.inet_ntop(socket.AF_INET6, data[4: ])
			port = struct.unpack('>H', self.recvall(sock, 2))[0]
			try:
				if mode == 1:  # 1. Tcp connect
					flag = False
					for conf in config:
						try:
							if conf['type'] == 'ipv4':
								(remote, reply) = self.tcp_ipv4(addr, port, conf)
							elif conf['type'] == 'ipv6':
								(remote, reply) = self.tcp_ipv6(addr, port, conf)
							elif conf['type'] == 'nat64':
								(remote, reply) = self.tcp_nat64(addr, port, conf)
							elif conf['type'] == 'http':
								(remote, reply) = self.tcp_http(addr, port, conf)
							elif conf['type'] == 'socks4':
								(remote, reply) = self.tcp_socks4(addr, port, conf)
							elif conf['type'] == 'socks5':
								(remote, reply) = self.tcp_socks5(addr, port, conf)
							else: continue
							flag = True
							break
						except (socket.error, ProxyException): pass
					if not flag: raise ProxyException('cannot connect to host')
					print 'Tcp connect to', addr, port
				else:
					reply = '\x05\x07\x00' + data[3] # Command not supported
			except (socket.error, ProxyException):
				# Connection refused
				reply = '\x05\x05\x00' + data[3] + '\x00\x00\x00\x00\x00\x00'
			sock.sendall(reply)
			# 3. Transfering
			if reply[1] == '\x00':  # Success
				if mode == 1:  # 1. Tcp connect
					self.handle_tcp(sock, remote)
		except (socket.error, ProxyException):
			print 'socket error'
def main():
	global fp
	#fp = open('report', 'w')
	server = ThreadingTCPServer(('', 1080), Socks5Server)
	try:
		server.serve_forever()
	except KeyboardInterrupt:
		server.shutdown()

config = getconf()
if __name__ == '__main__':
	main()
