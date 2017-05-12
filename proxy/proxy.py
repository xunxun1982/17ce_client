# -*- coding: utf-8 -*-
import sys
import os
import urllib2
import time
import threading
import bs4
import websocket
from bs4 import BeautifulSoup

reload(sys)
sys.setdefaultencoding('utf-8')

try:
    inFile = None
    outFile = None
    lock = threading.Lock()
except:
    pass

def getProxy():
    try:
        of = open(os.path.dirname(os.path.abspath(__file__)) + '/proxy.list.txt' , 'w')

        for page in range(1, 10):
            headers = { 'User-Agent' : 'Mozilla/5.0' }
            req = urllib2.Request('http://www.xicidaili.com/nt/' + str(page), None, headers)
            html_doc = urllib2.urlopen(req).read()
            soup = BeautifulSoup(html_doc, "html.parser")
            trs = soup.find('table', id='ip_list').find_all('tr')
            for tr in trs[1:]:
                tds = tr.find_all('td')
                ip = tds[1].text.strip()
                port = tds[2].text.strip()
                protocol = tds[5].text.strip()
                alive = tds[8].text.strip()
                if protocol == 'HTTP' or protocol == 'HTTPS':
                    of.write('%s=%s:%s=%s\n' % (protocol, ip, port, alive) )
                    print 'New proxy %s=%s:%s' % (protocol, ip, port)
         
        of.close()
    except:
        print 'Error: proxy list update failed.'


def testProxy():
    while True:
        lock.acquire()
        line = inFile.readline().strip()
        lock.release()
        if len(line) == 0: break
        protocol, proxy, alive = line.split('=')
        alive = alive.decode('utf-8').encode('gbk')
        try:
            options = {}
            p_host, p_port = proxy.split(':')
            options["http_proxy_host"] = p_host
            options["http_proxy_port"] = p_port
            websocket.enableTrace(False)
            ws = websocket.create_connection("ws://admin.17ce.com:9002/router_manage?ts=1494423244&key=0885ff58866e2b2c928d553aaf7817c8&r=969737151", timeout=5, **options)
            ws.send('{"Act": "Ping"}')
            result = ws.recv()
            ws.close()
            if result.find(u'Pong') > 0:
                lock.acquire()
                print 'add proxy', proxy, 'type:', protocol, 'alive:', alive
                outFile.write(proxy + ',' + protocol + ',' + alive + '\n')
                lock.release()
            else:
                print '*** ignore', proxy
        except Exception, e:
            pass


def startTest():
    global inFile, outFile
    try:
        inFile = open(os.path.dirname(os.path.abspath(__file__)) + '/proxy.list.txt', 'r')
        outFile = open(os.path.dirname(os.path.abspath(__file__)) + '/available.csv', 'w')
        all_thread = []
        outFile.write('proxy_address,protocol,alive_time\n')
        for i in range(50):
            t = threading.Thread(target=testProxy)
            all_thread.append(t)
            t.start()
            
        for t in all_thread:
            t.join()
         
        inFile.close()
        outFile.close()
    except:
        print 'Error: testing proxies failed!'


if __name__ == '__main__':
    try:
        if sys.argv[1] == "update":
            getProxy()
        if sys.argv[1] == "test":
            startTest()
    except Exception, e:
        print e
        pass
    
