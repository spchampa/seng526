'''
Last Name:  Champagne
First Name: Steven
Course:     CPSC526
Assignment: 3
Tutorial:   T03
Date:       2017-10-27
Files Submitted: report.pdf, proxy4.py
'''

#python3.6.2

import socket
import argparse
import _thread
import select
import binascii


PROXY_SERVER_ON = True
BUFFER_SIZE = 4096


parser = argparse.ArgumentParser()
group = parser.add_mutually_exclusive_group(required=False)
group.add_argument("-raw", action="store_true")
group.add_argument("-strip", action="store_true")
group.add_argument("-hex", action="store_true")
group.add_argument("-autoN", action='store', type=int)
parser.add_argument("-replace", nargs=2, required=False)
parser.add_argument("srcPort", type=int)
parser.add_argument("dest_IP")
parser.add_argument("dstPort", type=int)
args = parser.parse_args()

def handle(proxy_server_soc, proxy_client_soc):
    inputs = [proxy_server_soc, proxy_client_soc]
    outputs = []

    while True:
        readable, writable, exception = select.select(inputs, outputs, inputs)
        for s in readable:
            msg = s.recv(BUFFER_SIZE)

            if args.replace:
                original = bytes(args.replace[0], 'utf-8')
                replacement = bytes(args.replace[1], 'utf-8')
                msg = msg.replace(original, replacement)

            if len(msg) is 0:
                proxy_client_soc.close()
                #proxy_server_soc.close()
                return
            else:
                if s is proxy_server_soc:
                    log("<--- ",msg)
                    proxy_client_soc.sendall(msg)
                else:
                    log("---> ",msg)
                    proxy_server_soc.sendall(msg)

def log(arrow, msg):
    if args.raw:
        m = msg.decode('unicode_escape')
        print (arrow + m.strip('\n'))

    elif args.strip:
        m = bytearray(msg)
        for each in range(len(m)):
            if (m[each] != 10 and (m[each] <= 32 or m[each] >= 127)):
                m[each] = 46
        s = m.decode('utf-8').splitlines()
        print (arrow, end='\n')
        print (arrow.join(s))

    elif args.hex:
        for each in range(0, len(msg), 16):
            line = msg[each:each+16]
            ascii_msg = line.decode('ascii')
            hexyline = ''.join('%.2X '%i for i in line)
            #NOTE: If just want the hex and not the direction arrow just use VV
            #print("{0:0{1}x}".format(each, 8), hexyline, '|'+str(ascii_msg)+'|')
            s = ("{0:0{1}x}".format(each, 8), hexyline, '|'+str(ascii_msg).strip('\n')+'|')
            sep = ' '
            hex_print = sep.join(s)
            print (arrow + hex_print)

    elif args.autoN:
        for each in range(0, len(msg), args.autoN):
            line = msg[each:each +args.autoN]
            l = filterLine(line)
            print(arrow + l)
    else:
        #Don't Log
        pass


def filterLine(line):
    filtered = ""
    for each in line:
        #print("CHAR: ", each)
        if each is 92:
            filtered += "\\"
        elif each is 9:
            filtered += "\\t"
        elif each is 13:
            filtered += "\\r"
        elif each is 10:
            filtered += "\\n"
        elif each >= 32 and each <= 127:
            filtered += chr(each)
        else:
            i = '%.2X'%each
            filtered += "\\" + i
    return filtered

def Main():
    PROXY_HOST = 'localhost'
    PROXY_PORT = args.srcPort

    #listen with proxy server
    proxy_server_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    proxy_server_soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    proxy_server_soc.bind((PROXY_HOST, PROXY_PORT))
    proxy_server_soc.listen()
    print("Port logger running: srcPort="+str(args.srcPort),"host="+PROXY_HOST, "dst="+str(args.dstPort))
    while PROXY_SERVER_ON:

        conn, addr = proxy_server_soc.accept()
        #connect to real server with proxy client.
        proxy_client_soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        proxy_client_soc.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        proxy_client_soc.connect((args.dest_IP, args.dstPort))

        _thread.start_new_thread(handle, (conn, proxy_client_soc))


if __name__ == "__main__":
    Main()
