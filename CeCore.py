# -*- coding: utf-8 -*-
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


class CeClientProtocol(WebSocketClientProtocol):
    def __init__(self):
        self.handlers = {
            "LoginRt": self.onLoginRt,
            "Pong": self.onPong_,
            "TaskList": self.onTaskList
        }
        self.USERNAME = "xxx@xxx.com"  # modify to your username(email)
        self.UUID = hex(uuid.getnode())[2:-1]  # modify to your uuid or keep default
        self.LOCALIP = "192.168.1.1"  # modify to your local ip (optional)
        self.DNSIP = "127.0.0.1"  # modify to your dns ip (optional)
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
        print "Connected"
        self.sendMessage({
            "Act": "Login",
            "DnsIp": self.DNSIP,
            "LocalIp": self.LOCALIP,
            "UUID": self.USERNAME + self.UUID,
            "Username": self.USERNAME,
            "Version": "3.0.10"
        })

    def onClose(self, wasClean, code, reason):
        print "Disconnected"
        pass

    def onMessage(self, payload, isBinary):
        if isBinary:
            print "Binary data not support"
        else:
            data = json.loads(payload.decode('utf8'))
            act = data["Act"]
            if act in self.handlers:
                self.handlers[act](data)
            else:
                print "Unknown Act:", act
                print "Unknown Act Data:", data

    def sendPing(self):
        self.sendMessage({"Act": "Ping"})

    def getTask(self):
        self.sendMessage({"Act": "GetTask", "UserId": self.USERID, "NodeId": self.NODEID})

    def monitorResult(self):
        print "Submitting Task: ", len(self.MONITORRESULT)
        if len(self.MONITORRESULT) == 0:
            return
        self.sendMessage({"Act": "MonitorResult", "UserId": self.USERID, "NodeId": self.NODEID,
                          "TaskType": "Cycle",
                          "MonitorResult": self.MONITORRESULT
                          })
        self.MONITORRESULT = []
        print "Req Task: ", self.REQTASK, "Finished Task:", self.FINISHTASK

    def onLoginRt(self, data):
        self.USERID = data["UserId"]
        self.NODEID = data["NodeId"]
        print "Logged in", "UserId:", self.USERID, "NodeId:", self.NODEID
        # Start Ping/Pong
        pingpongservice = task.LoopingCall(self.sendPing)
        pingpongservice.start(30)
        # Start GetTask
        gettaskservice = task.LoopingCall(self.getTask)
        gettaskservice.start(30)
        # Start MonitorResult
        monitorresultservice = task.LoopingCall(self.monitorResult)
        monitorresultservice.start(30)

    def onPong_(self, data):
        pass

    def onTaskList(self, data):
        tasktype = data["TaskType"]
        if tasktype == "Cycle":
            tasklist = data["TaskList"]
            for task in tasklist:
                taskid = task["TaskId"]
                print "New TaskId:", taskid, "TestType", task["TestType"], "Host", task["Host"]
                self.REQTASK += 1
                if task["TestType"] == "PING":
                    d = threads.deferToThread(self.doPingAsyncTask, task)
                    d.addCallback(self.doPingAsyncTaskResult)
                elif task["TestType"] == "HTTP":
                    d = threads.deferToThread(self.doHttpAsyncTask, task)
                    d.addCallback(self.doHttpAsyncTaskResult)
                else:
                    print "Unknown TestType:", task["TestType"]

        else:
            print "Unknown TaskType:", tasktype

    def doPingAsyncTask(self, task):
        host = task["Host"]
        try:
            p = pyping.ping(host, count=task["PingCount"])
            print "Ping..." + host
            return [True, task, p.avg_rtt, p.min_rtt, p.max_rtt, p.packet_lost, p.destination_ip]
        except:
            print "Ping..." + host + "...Err"
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
                print "Http..." + url + "...Err"
                return [False, task, c]
        header = header.getvalue()
        body = body.getvalue()
        body = body[:task["MaxDown"]]
        print "Http..." + url
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


if __name__ == '__main__':
    ts = str(int(time.time()))
    md5 = hashlib.md5()
    r = random.Random()
    r = str(r.randint(0, int(time.time())))
    key = r + "8e2d642abac4bfbZxETNk0DL1EjN3RWC" + ts
    md5.update(key[::-1])
    key = md5.hexdigest()
    headers = {'Origin': 'admin.17ce.com'}
    factory = WebSocketClientFactory("ws://admin.17ce.com:9002/router_manage?ts=%s&key=%s&r=%s" % (ts, key, r), headers=headers, useragent="")
    factory.protocol = CeClientProtocol
    connectWS(factory)

    reactor.run()
