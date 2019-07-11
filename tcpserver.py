import socket

ip_port=('0.0.0.0',8080)
back_log=5
buffer_size=1024
ser=socket.socket(socket.AF_INET,socket.SOCK_STREAM)
ser.setsockopt(socket.SOL_SOCKET,socket.SO_REUSEADDR,1)
ser.bind(ip_port)
ser.listen(back_log)
while True:
    con,address=ser.accept()
    print('get connected')
    try:
        msg=con.recv(buffer_size)
        if msg.decode('utf-8')=='1':
            con.close()
        #print('服务器收到消息{}'.format(msg.decode('utf-8')))
        print(msg.decode('utf-8'))
    except Exception as e:
        break
ser.close()
