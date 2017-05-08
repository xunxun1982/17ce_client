# -*- coding: utf-8 -*-
import signal
import sys
import os
import json
import subprocess

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
        os.kill(SubProc, 9)
    sys.exit(0)


if __name__ == '__main__':
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
            CeDev["nickname"] = ""
            
        sys.argv = [
            '17ce_load_internal', 
            CeDev["username"], 
            CeDev["dev_uuid"], 
            CeDev["lan_ip"], 
            CeDev["dns_ip"], 
            CeDev["nickname"], 
            CeConfig["version"]
        ]
        SubProc = subprocess.Popen(['python', os.path.dirname(os.path.abspath(__file__)) + '/CeCore.py'] + sys.argv)
        SubProcList.append(SubProc.pid)

    print('Press Ctrl+C to terminal Client')
    signal.signal(signal.SIGINT, signal_handler)

    while True:
        pass
