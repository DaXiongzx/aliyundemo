import socket

p=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
p.connect(('127.0.0.1'.6666))
while True:
    msg=input('please input')
    if not msg:
        continue
    p.send(msg.decode('utf-8'))
    if msg=='1':
        break
p.close()

