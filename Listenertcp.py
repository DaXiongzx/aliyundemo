import socket
#import ports
import serial
#import control
import multiprocessing as mp
import time
#import gps
import signal
import requests
import json
#import sensor
import sys
#import radar
import os
#import servo
import sqlite3
#import database
'''
# 调试的时候使用
pprint = print
def print(*args):
    pprint(args)
    pprint(sys._getframe().f_code)
'''

rtkFlag = False
ip='47.106.148.82'
port=8090
addr=(ip,port)


'''def exit(signum, frame):
    finish()
    time.sleep(0.1)
    os.system('gpio mode {} pwm'.format(control.leftEnginePort))
    os.system('gpio pwm-ms')
    os.system('gpio pwmr 9600')
    os.system('gpio pwm {} {}'.format(control.leftEnginePort,round(control.staticDutyCircle * 9600 / 100)))
    time.sleep(0.1)
    os.system('gpio mode {} pwm'.format(control.rightEnginePort))
    os.system('gpio pwm-ms')
    os.system('gpio pwmr 9600')
    os.system('gpio pwm {} {}'.format(control.rightEnginePort,round(control.staticDutyCircle * 9600 / 100)))
    print('finished')
    sys.exit()'''

def sendSensorMessage(messages):
    url = 'http://47.100.102.135:81/api/App/SendParameter'
    try:
        message = '|'.join(messages)
        #print('message:',message)
        param = {'shipId':4,'message':message}
        r = requests.get(url,params=param,timeout=internetTimeout)
        #print(r.url)
        r.raise_for_status()
    except Exception as e:
        print('error in sendSensorMessage:',e)
        return False
    else:
        return True
def sendDebugMessage(ms):
    #print('messages:',ms)
    m = '|'.join(ms)
    #print('message:',m)
    param = {'shipId':4,'message':m}
    url = 'http://47.100.102.135:81/api/App/SendMessage'
    try:
        r = requests.get(url,params=param,timeout=internetTimeout)
        r.raise_for_status()
    except Exception as e:
        print('error in sendDebugMessage:',e)
        return False
    else:
        return True

def sendMessage(data):
    debugMessage = []
    sensorMessage = []
    if isinstance(data,str):
        debugMessage.append(data)
    elif isinstance(data,list):
        for message in data:
            if len(message)>10 and message[:10]=='sensordata':
                sensorMessage.append(message[10:])
            else:
                debugMessage.append(message)
    Flag1 = True
    Flag2 = True
    if len(debugMessage)>0:
        Flag1 = sendDebugMessage(debugMessage)
    if len(sensorMessage)>0:
        Flag2 = sendSensorMessage(sensorMessage)
    return Flag1 and Flag2


def send(q):
    while True:
        queueLength = q.qsize()
        if queueLength==0:
            time.sleep(0.2)
            continue
        data = []
        for i in range(queueLength):
            data.append(q.get())
        sendMessage(data)


#finish all child process created by main process
def finish():
    for process in processList:
        if process and process.is_alive():
            process.terminate()

def testconnection():
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.connect(ip)
    if s.recv(1024):
        return True
    else:
        return False

def doInstruction(instruction):
    global p
    global currentLeftEngineFlag
    global currentRightEngineFlag
    print('instruction:',instruction)
    if instruction.find('?starship')==0:
        if p and p.is_alive():
            p.terminate()
        p = mp.Process(target=control.ship_control, args=(
            q, location, yaw, gpsYaw, speedRatio, targetIndex,kp,ki,kd))
        p.start()
    elif instruction.find('?stopship')==0:
        if p and p.is_alive():
            p.terminate()
        control.stop()
        currentLeftEngineFlag = 0
        currentRightEngineFlag = 0
    elif instruction.find('?stopmove')==0:
        if p and p.is_alive():
            p.terminate()
        control.stop()
        currentLeftEngineFlag = 0
        currentRightEngineFlag = 0
    elif instruction.find('?getroute')==0:
        if len(instruction)<10:
            return
        if instruction[-1]!='?':
            return
        route = instruction[9:-1]
        targetIndex.value = 0
        with open('/root/route','w') as f:
            f.write(route)
    elif instruction.find('?setorder')==0:
        if len(instruction)<10:
            print('wrong instruction : {}'.format(instruction))
            return
        if instruction[-1]!='?':
            print('wrong instruction : {}'.format(instruction))
            return
        order = instruction[9:-1]
        try:
            order = int(order)
            if order>=0:
                targetIndex.value = order
        except Exception as e:
            print('wrong instruction : {} with exception:{}'.format(instruction,e))
    elif instruction.find('?setspeed')==0:
        if len(instruction)<10:
            print('wrong instruction : {}'.format(instruction))
            return
        if instruction[-1]!='?':
            print('wrong instruction : {}'.format(instruction))
            return
        try:
            s = instruction[9:-1]
            s = float(s)
            #print('s=',s)
            if s>=0 and s<=1:
                speedRatio.value = s
                control.leftEngineControl(currentLeftEngineFlag,s)
                control.rightEngineControl(currentRightEngineFlag,s)
        except Exception as e:
            print('wrong instruction : {} with exception:{}'.format(instruction,e))
    elif instruction.find('?setpidcs')==0:
        if len(instruction)<10:
            print('wrong instruction : {}'.format(instruction))
            return
        if instruction[-1]!='?':
            print('wrong instruction : {}'.format(instruction))
            return
        pidcs = instruction[9:-1]
        pidcs = pidcs.split(' ')
        try:
            pidcs = [float(i) for i in pidcs]
            assert len(pidcs)==3
            kp.value = pidcs[0]
            ki.value = pidcs[1]
            kd.value = pidcs[2]
        except Exception as e:
            print('wrong instruction : {} with exception:{}'.format(instruction,e))
    elif instruction.find('?startsensor')==0:
        sensorFlag.value = 1
    elif instruction.find('?stopsensor')==0:
        sensorFlag.value = 0
    elif instruction.find('?moveforw')==0:
        if p and p.is_alive():
            p.terminate()
        control.goForward(speedRatio.value)
        currentLeftEngineFlag = 1
        currentRightEngineFlag = 1
    elif instruction.find('?moveback')==0:
        if p and p.is_alive():
            p.terminate()
        control.goBackward(speedRatio.value)
        currentLeftEngineFlag = -1
        currentRightEngineFlag = -1
    elif instruction.find('?moverigh')==0:
        if len(instruction)<10:
            print('wrong instruction : {}'.format(instruction))
            return
        if instruction[-1]!='?':
            print('wrong instruction : {}'.format(instruction))
            return
        if p and p.is_alive():
            p.terminate()
        percent = instruction[9:-1]
        try:
            percent = float(percent)
            if percent<0 or percent>1:
                return
            control.turnRight(percent,speedRatio.value)
            currentLeftEngineFlag = percent
            currentRightEngineFlag = -percent
        except Exception as e:
            print('wrong instruction : {} with exception:{}'.format(instruction,e))
    elif instruction.find('?moveleft')==0:
        if len(instruction)<10:
            print('wrong instruction : {}'.format(instruction))
            return
        if instruction[-1]!='?':
            print('wrong instruction : {}'.format(instruction))
            return
        if p and p.is_alive():
            p.terminate()
        percent = instruction[9:-1]
        try:
            percent = float(percent)
            if percent<0 or percent>1:
                return
            control.turnLeft(percent,speedRatio.value)
            currentLeftEngineFlag = -percent
            currentRightEngineFlag = percent
        except Exception as e:
            print('wrong instruction : {} with exception:{}'.format(instruction,e))
    elif instruction.find('?pushexo')==0:
        try:
            servo.pushExo()
        except Exception as e:
            print('error at do pushexo instruction :',e)
    elif instruction.find('?pullexo')==0:
        try:
            servo.pullExo()
        except Exception as e:
            print('error at do pullexo instruction :',e)







def testconnection(s):
    #s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    #s.connect(ip)
    if s.recv(1024):
        doInstruction(s.recv(1024).decode('utf-8'))
        return True
    else:
        return False

def main():
    tcpmessage=b''
    connectflag=0
    ot = time.time()
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.connect((addr))
    connectflag=1
    #s.send(tcpmessage)
    while True:
        if time.time() - ot > 2:
            ot = time.time()
            lat = location[0]
            lon = location[1]
            q.put('latitude:' + str(lat) + ' longitude:' + str(lon) + ' yaw:' + str(yaw.value) + ' speed:' + str(
                speed.value))
        # print('start call function receiveInstructions')
        Instruction=s.recv(1024)
        instruction=Instruction.decode()
        if instruction:
            #print('this is instruction:'+instruction)
            doInstruction(instruction)
        else:
            while True:
                if(testconnection(s)):
                    break
                else:
                    #control.stop()
                    time.sleep(1)
                    s.connect(ip)
            #continue


def sendlocation(location):
    s=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    s.connect(addr)
    while True:
        latitude=location[0]
        logitude=location[1]
        latitudevalue='latitude'+latitude
        logitudevalue='logitude'+logitude
        s.send(latitudevalue.encode('utf-8'))
        s.send(logitudevalue.encode('utf-8'))



if __name__ == '__main__':
    p = None  # navigation process
    q = mp.Queue()  # message queue

    kp = mp.Value('d', 0.05)  # pid parameters
    ki = mp.Value('d', 0.0001)
    kd = mp.Value('d', 0.05)
    oldInstructions = set()  # set to identify new and old instructions
    internetTimeout = 1  # timeout for internet to prevent from waiting too long
    targetIndex = mp.Value('i')  # to tag which navigation point the boat is heading to,count from 0
    targetIndex.value = 0  # initilized with 0, the first navigation point

    location = mp.Array('d', [0 for i in range(2)])  # location=[latitude,longitude]
    yaw = mp.Value('f')  # yaw [0,360)
    gpsYaw = mp.Value('f')  # yaw by gps [0,360)
    speed = mp.Value('f')

    processList = [p]

    '''sendlocationProcess=mp.process(target=sendlocation,args=(location,))
    sendlocationProcess.daemon=True
    sendlocationProcess.start()
    processList.append(sendlocationProcess)

    locationProcess = mp.Process(target=gps.getLocation,
                                 args=(location, yaw, gpsYaw, speed))  # create process to get location,yaw and gpsYaw
    locationProcess.daemon = True
    locationProcess.start()
    processList.append(locationProcess)'''

    speedRatio = mp.Value('f', 1)
    currentLeftEngineFlag = 0
    currentRightEngineFlag = 0

    sensorFlag = mp.Value('i', 1)  # create process to get and send water quality data fro msensors
    '''sensorProcess = mp.Process(target=sensor.sendSensorData, args=(
    location, q, sensorFlag))  # sensorFlag 1:send water quality data 0:not send water quality data
    sensorProcess.daemon = True
    sensorProcess.start()
    processList.append(sensorProcess)'''

    '''sendProcess = mp.Process(target=send, args=(q,))
    sendProcess.daemon = True
    sendProcess.start()
    processList.append(sendProcess)'''

    if rtkFlag:
        rtcmProcess = mp.Process(target=gps.activateRTCM, args=(q,))
        rtcmProcess.daemon = True
        rtcmProcess.start()
        processList.append(rtcmProcess)

    signal.signal(signal.SIGINT, exit)

    '''os.system('gpio mode {} pwm'.format(control.leftEnginePort))
    os.system('gpio pwm-ms')
    os.system('gpio pwmr 9600')
    os.system('gpio pwm {} {}'.format(control.leftEnginePort, round(control.staticDutyCircle * 9600 / 100)))

    os.system('gpio mode {} pwm'.format(control.rightEnginePort))
    os.system('gpio pwm-ms')
    os.system('gpio pwmr 9600')
    os.system('gpio pwm {} {}'.format(control.rightEnginePort, round(control.staticDutyCircle * 9600 / 100)))'''

    #conn = sqlite3.connect('logInternet.db')
    main()