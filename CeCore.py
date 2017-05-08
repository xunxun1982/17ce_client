# -*- coding: utf-8 -*-
import sys
import os
import hashlib
import time
import json
import uuid
import pyping
import random
import pycurl
import base64
from StringIO import StringIO

from twisted.internet import reactor, task, threads
from autobahn.twisted.websocket import WebSocketClientFactory, \
    WebSocketClientProtocol, \
    connectWS

try:
    CeVersion = sys.argv[7]
except:
    CeVersion = "3.0.10"
try:
    CeProxy = sys.argv[8]
except:
    CeProxy = ""

class CeClientProtocol(WebSocketClientProtocol):
    def __init__(self):
        global CeConfig, CeLoadIndex
        self.handlers = {
            "LoginRt": self.onLoginRt,
            "Pong": self.onPong_,
            "TaskList": self.onTaskList
        }
        
        self.USERNAME = sys.argv[2]
        self.UUID = sys.argv[3]
        self.LOCALIP = sys.argv[4]
        self.DNSIP = sys.argv[5]
        self.NICKNAME = sys.argv[6]
        self.USERID = 0
        self.NODEID = 0
        self.MONITORRESULT = []
        self.REQTASK = 0
        self.FINISHTASK = 0
        WebSocketClientProtocol.__init__(self)

    def sendMessage(self,
                    payload,
                    isBinary=False,
                    fragmentSize=None,
                    sync=False,
                    doNotCompress=False):
        payload = json.dumps(payload, ensure_ascii=False).encode('utf8')
        return WebSocketClientProtocol.sendMessage(self, payload, isBinary, fragmentSize, sync, doNotCompress)

    def onOpen(self):
        global CeVersion
        print "Connected"
        self.sendMessage({
            "Act": "Login",
            "DnsIp": self.DNSIP,
            "LocalIp": self.LOCALIP,
            "UUID": self.USERNAME + self.UUID,
            "Username": self.USERNAME,
            "Version": CeVersion
        })

    def onClose(self, wasClean, code, reason):
        print "[" + self.NICKNAME + "] Disconnected"
        pass

    def onMessage(self, payload, isBinary):
        if isBinary:
            print "[" + self.NICKNAME + "] Binary data not support"
        else:
            data = json.loads(payload.decode('utf8'))
            act = data["Act"]
            if act in self.handlers:
                self.handlers[act](data)
            else:
                print "[" + self.NICKNAME + "] Unknown Act:", act
                print "[" + self.NICKNAME + "] Unknown Act Data:", data

    def sendPing(self):
        self.sendMessage({"Act": "Ping"})

    def getTask(self):
        self.sendMessage({"Act": "GetTask", "UserId": self.USERID, "NodeId": self.NODEID})

    def monitorResult(self):
        print "[" + self.NICKNAME + "] Submitting Task: ", len(self.MONITORRESULT)
        if len(self.MONITORRESULT) == 0:
            return
        self.sendMessage({"Act": "MonitorResult", "UserId": self.USERID, "NodeId": self.NODEID,
                          "TaskType": "Cycle",
                          "MonitorResult": self.MONITORRESULT
                          })
        self.MONITORRESULT = []
        print "[" + self.NICKNAME + "] Req Task: ", self.REQTASK, "Finished Task:", self.FINISHTASK

    def onLoginRt(self, data):
        try:
            self.USERID = data["UserId"]
            self.NODEID = data["NodeId"]
            if self.NICKNAME == "":
                self.NICKNAME = "NODE-" + str(data["NodeId"])
            print "[" + self.NICKNAME + "] Logged in", "UserId:", self.USERID, "NodeId:", self.NODEID
            # Start Ping/Pong
            pingpongservice = task.LoopingCall(self.sendPing)
            pingpongservice.start(1)
            # Start GetTask
            gettaskservice = task.LoopingCall(self.getTask)
            gettaskservice.start(30)
            # Start MonitorResult
            monitorresultservice = task.LoopingCall(self.monitorResult)
            monitorresultservice.start(30)
        except:
            pass

    def onPong_(self, data):
        pass

    def onTaskList(self, data):
        tasktype = data["TaskType"]
        if tasktype == "Cycle":
            tasklist = data["TaskList"]
            for task in tasklist:
                taskid = task["TaskId"]
                print "[" + self.NICKNAME + "] New TaskId:", taskid, "TestType", task["TestType"], "Host", task["Host"]
                self.REQTASK += 1
                if task["TestType"] == "PING":
                    d = threads.deferToThread(self.doPingAsyncTask, task)
                    d.addCallback(self.doPingAsyncTaskResult)
                elif task["TestType"] == "HTTP":
                    d = threads.deferToThread(self.doHttpAsyncTask, task)
                    d.addCallback(self.doHttpAsyncTaskResult)
                else:
                    print "[" + self.NICKNAME + "] Unknown TestType:", task["TestType"]

        else:
            print "[" + self.NICKNAME + "] Unknown TaskType:", tasktype

    def doPingAsyncTask(self, task):
        host = task["Host"]
        try:
            p = pyping.ping(host, count=task["PingCount"])
            print "[" + self.NICKNAME + "] Ping..." + host
            return [True, task, p.avg_rtt, p.min_rtt, p.max_rtt, p.packet_lost, p.destination_ip]
        except:
            print "[" + self.NICKNAME + "] Ping..." + host + "...Err"
            return [False, task]

    def doPingAsyncTaskResult(self, result):
        if result[0]:
            if result[2] is None:
                result[2] = 0
            if result[3] is None:
                result[3] = 0
            if result[4] is None:
                result[4] = 0
            data = {
                "Avg": int(float(result[2]) * 1000),
                "ErrMsg": "",
                "Invalid": 0,
                "Max": int(float(result[4]) * 1000),
                "Min": int(float(result[3]) * 1000),
                "PacketsLost": result[5],
                "PacketsSent": result[1]["PingCount"],
                "PingInfo": [],
                "PingSize": result[1]["PingSize"],
                "SrcIP": result[6],
                "TaskId": result[1]["TaskId"],
                "TestType": "PING"
            }
            for x in range(0, data["PacketsLost"]):
                data["PingInfo"].append({"TTL": 0, "Time": -1})
            for x in range(0, data["PacketsSent"] - data["PacketsLost"]):
                data["PingInfo"].append({"TTL": 55, "Time": data["Avg"]})
            self.MONITORRESULT.append(data)
        else:
            self.MONITORRESULT.append({
                "Avg": 0,
                "ErrMsg": "resolv " + result[1]["Host"] + " err:",
                "Invalid": 0,
                "Max": 0,
                "Min": 0,
                "PacketsLost": 0,
                "PacketsSent": 0,
                "PingInfo": None,
                "PingSize": 0,
                "SrcIP": "",
                "TaskId": result[1]["TaskId"],
                "TestType": "PING"
            })
        self.FINISHTASK += 1

    def doHttpAsyncTask(self, task):
        def callback_progress(download_total, downloaded, upload_total, uploaded):
            if downloaded > task["MaxDown"]:
                return 1

        header = StringIO()
        body = StringIO()
        url = task["Url"].encode('utf-8')
        c = pycurl.Curl()
        c.setopt(c.URL, url)
        c.setopt(c.NOPROGRESS, False)
        c.setopt(c.HEADERFUNCTION, header.write)
        c.setopt(c.WRITEFUNCTION, body.write)
        c.setopt(c.XFERINFOFUNCTION, callback_progress)
        c.setopt(c.TIMEOUT, task["TimeOut"])
        c.setopt(c.USERAGENT, task["UserAgent"])
        c.setopt(c.FOLLOWLOCATION, True)
        c.setopt(c.MAXREDIRS, 5)
        try:
            c.perform()
        except Exception as e:
            if e != 42:
                print "[" + self.NICKNAME + "] Http..." + url + "...Err"
                return [False, task, c]
        header = header.getvalue()
        body = body.getvalue()
        body = body[:task["MaxDown"]]
        print "[" + self.NICKNAME + "] Http..." + url
        return [True, task, c, header, body]

    def doHttpAsyncTaskResult(self, result):
        task = result[1]
        c = result[2]
        if result[0]:
            head = result[3]
            body = result[4]
            data = {
                "ConnectTime": c.getinfo(c.CONNECT_TIME),
                "ContentLength": int(c.getinfo(c.CONTENT_LENGTH_DOWNLOAD)),
                "DownLoadSize": len(body),
                "DownTime": c.getinfo(c.TOTAL_TIME) - c.getinfo(c.STARTTRANSFER_TIME),
                "ErrMsg": "",
                "HttpBodyMd5Str": "",
                "HttpCode": c.getinfo(c.RESPONSE_CODE),
                "HttpHead": "",
                "Invalid": 0,
                "NsLookup": c.getinfo(c.NAMELOOKUP_TIME),
                "SrcIP": c.getinfo(c.PRIMARY_IP),
                "TTFBTime": c.getinfo(c.STARTTRANSFER_TIME),
                "TaskId": task["TaskId"],
                "TestType": "HTTP",
                "TotalTime": c.getinfo(c.TOTAL_TIME)
            }
            md5 = hashlib.md5()
            md5.update(body)
            data["HttpBodyMd5Str"] = md5.hexdigest()
            data["HttpHead"] = base64.b64encode(head)
            self.MONITORRESULT.append(data)
        else:
            self.MONITORRESULT.append({
                "ConnectTime": -1,
                "ContentLength": 0,
                "DownLoadSize": 0,
                "DownTime": -1,
                "ErrMsg": "resolv shoudonghuaji err:",
                "HttpBodyMd5Str": "",
                "HttpCode": 0,
                "HttpHead": "",
                "Invalid": 0,
                "NsLookup": -1,
                "SrcIP": "",
                "TTFBTime": -1,
                "TaskId": task["TaskId"],
                "TestType": "HTTP",
                "TotalTime": c.getinfo(c.TOTAL_TIME)
            })
        self.FINISHTASK += 1
        c.close()



def createNewCeClient():
    global CeProxy
    ts = str(int(time.time()))
    md5 = hashlib.md5()
    r = random.Random()
    r = str(r.randint(0, int(time.time())))
    key = r + "8e2d642abac4bfbZxETNk0DL1EjN3RWC" + ts
    md5.update(key[::-1])
    key = md5.hexdigest()
    
    factory = WebSocketClientFactory("ws://admin.17ce.com:9002/router_manage?ts=%s&key=%s&r=%s" % (ts, key, r))
    factory.protocol = CeClientProtocol
    factory.origin = "admin.17ce.com"
    factory.useragent = ""
    if CeProxy == "":
        factory.proxy = None
    else:
        factory.proxy = {'host': CeProxy.split(':')[0], 'port': int(CeProxy.split(':')[1])}
    connectWS(factory)
    
    reactor.run()


if __name__ == '__main__':
    try:
        if sys.argv[1] != "17ce_load_internal":
            print "Error: Please load by parent process!"
            sys.exit(-1)
    except:
        print "Error: Please load by parent process!"
        sys.exit(-1)
    
    createNewCeClient()
