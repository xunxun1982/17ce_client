# -*- coding: utf-8 -*-
import signal
import sys
import os
import json
import subprocess
from time import time, sleep

reload(sys)
sys.setdefaultencoding("utf-8")

# Loading Config.Json and Initization Loop variable
try:
    with open(os.path.dirname(os.path.abspath(__file__)) + '/config.json') as data_file: 
        CeConfig = json.load(data_file)
except:
    print "Error: config.json file not found or cannot be decode."
    sys.exit(-1)


SubProcList = []

def signal_handler(signal, frame):
    global SubProcList
    for _ in range(0,60):
        sys.stdout.write('-')
    print "\nYou pressed Ctrl+C! 17ce Client Exited"
    
    for SubProc in SubProcList:
        try:
            os.kill(SubProc, 9)
            os.kill(SubProc, 15)
            os.kill(SubProc, 17)
        except:
            pass
    sys.exit(0)

def start_newtask():
    global SubProcList
    try:
        if sys.argv[1] == "proxytest":
            subprocess.call(['python', os.path.dirname(os.path.abspath(__file__)) + '/proxy/proxy.py', 'update'])
            subprocess.call(['python', os.path.dirname(os.path.abspath(__file__)) + '/proxy/proxy.py', 'test'])
            sys.exit(0)
    except Exception, e:
        pass
    
    CeLoadIndex = 0
    for CeDev in CeConfig["devices"]:
        try:
            CeDev["username"]
        except:
            print "Error: the " + str(CeLoadIndex+1) + "th device missing username! abort."
            break
        try:
            CeDev["dev_uuid"]
        except:
            CeDev["dev_uuid"] = hex(uuid.getnode())[2:-2] + str(index)
        try:
            CeDev["lan_ip"]
        except:
            CeDev["lan_ip"] = "192.168.1." + str(random.randint(1,254))
        try:
            CeDev["dns_ip"]
        except:
            CeDev["dns_ip"] = "114.114.114.114"
        try:
            CeDev["nickname"]
        except:
            CeDev["nickname"] = "DEVICE-" + str(CeLoadIndex+1)
        try:
            CeDev["proxy"]
        except:
            CeDev["proxy"] = ""
        CeLoadIndex += 1
        
        sys.argv = [
            '17ce_load_internal', 
            CeDev["username"], 
            CeDev["dev_uuid"], 
            CeDev["lan_ip"], 
            CeDev["dns_ip"], 
            CeDev["nickname"], 
            CeConfig["version"],
            CeDev["proxy"]
        ]
        SubProc = subprocess.Popen(['python', os.path.dirname(os.path.abspath(__file__)) + '/CeCore.py'] + sys.argv)
        SubProcList.append(SubProc.pid)
        sleep(30)

if __name__ == '__main__':
    print('Press Ctrl+C to terminal Client')
    signal.signal(signal.SIGINT, signal_handler)
    
    start_newtask() # start new threading
    
    UpTime = 0
    while True:
        MemFree = os.popen("free | grep Mem | awk '{print ($2-$4-$6-$7)/$2 * 100.0}'").read() # get memory usage
        if UpTime >= 3600 or int(float(MemFree)) >= 80: # if over 1 hour or memory leak
            # kill old process
            for SubProc in SubProcList:
                try:
                    os.kill(SubProc, 9)
                    os.kill(SubProc, 15)
                    os.kill(SubProc, 17)
                except:
                    pass
            
            # output information
            print "************"
            print('[SYSTEM] ** timeout restart threading to protect memory leak **')
            print "[SYSTEM]" ,"Uptime(second):", UpTime, "Memory Usage(%):" ,float(MemFree)
            print "************"
            # reset var and restart threading
            SubProcList = []
            UpTime = 0
            # restart new threading
            sleep(10)
            start_newtask()
            
        
        # timer add
        UpTime += 1
        sleep(1)
        