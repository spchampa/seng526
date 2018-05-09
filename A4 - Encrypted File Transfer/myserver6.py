'''
Last Name:  Champagne
First Name: Steven
Course:     CPSC526
Assignment: 4: Encrypted File Transfer
Tutorial:   T03
Date:       2017-11-11
Files Submitted: report.pdf, myclient4.py, myserver4.py

python version: 3.6.2

ARGS PROTOTYPE: script.py <PORT##> <SECRETKEY>

HOW TO RUN (EXAMPLE):
    RUN SERVER FIRST: $ python3.6 myserver4.py 5555 mysecret

    RUN CLIENT SECOND:
        READ:
            $ python3.6 myclient4.py read a.txt localhost:5555 null mysecret
        WRITE:
            $ cat test.txt | python3.6 myclient3.py write a.txt localhost:5555 null mysecret

'''
import argparse
import socket
import random
import string
import hashlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import datetime
import time

parser = argparse.ArgumentParser(description="Encrypted File Transfer Server.")
parser.add_argument("port", type=int, help="Server Listining Port (Always localhost).")
parser.add_argument("key", type=str, help="Secret key for the server.")
args = parser.parse_args()

#globals
BUFFER_SIZE = 1024
nonce = ''                          #nonce sent from client
use_cipher = ''                     #cipher sent from client
csoc = None                         #client connection
IV = b''                            #initialization vector
KEY = b''                           #one time key
backend = default_backend()         #backend is global for eaze of use
FILE = ''                           #filename requested by client
CMD = ''                            #Operation to be done for client


def handle(csoc):
    #recieve cipher and nonce
    cipher_nonce = csoc.recv(1024).decode('UTF-8')
    global nonce, use_cipher
    nonce = cipher_nonce.split('_')[1]
    use_cipher = cipher_nonce.split('_')[0]

    printlog("new connection from " + csoc.getsockname()[0] + " cipher=" + use_cipher)

    #Set IV and Key based on recieved nonce
    global IV, KEY
    IV = createIV(nonce, use_cipher)
    KEY = createKEY(nonce, use_cipher)

    printlog("nonce="+nonce)
    printlog("IV="+str(IV))
    printlog("SK="+str(KEY))

    ### EVERYTHING AFTER THIS POINT MUST BE ENCRYPTED ###

    #send challenge
    sucess = challenge()
    if not sucess:
        #send failed response: Log attempt: terminate connection
        #csoc.sendall(encrypt(b'FAIL'))
        csoc.close()
        csoc=None
        return
    elif sucess:
        #send sucess response: Log attempt: proceede to filetransfer
        pass
    else:
        #should not be possible
        print("ERROR: SHOULD NOT HAVE REACHED HERE")
        pass



    ## GET FILENAME AND OPERATION FROM CLIENT ##
    cmd_file = csoc.recv(1024)
    plane_cmd_file = decrypt(cmd_file).decode("UTF-8")
    global CMD, FILE
    CMD = plane_cmd_file.split('_')[0]
    FILE = plane_cmd_file.split('_')[1]

    printlog("command:"+CMD+", filename:"+FILE)


    ## DO THE THING THAT THE CLIENT WANTS ##
    if CMD == "write":
        #write to that file in server folder
        writefile(csoc) #writes file FROM client

    elif CMD == "read":
        #if the file is readable read it to socket encrypted
        readfile() #reads file TO client

    else:
        printlog("INVALID COMMAND: "+CMD)
        #csoc.sendall(encrypt(b'FAIL'))
        csoc.close()
        csoc=None
        return

    ## EVERYTHING DONE FOR THIS TRANSACTION ##
    csoc.close()
    csoc=None
    return


def writefile(csoc):
    status = 'sucess'
    try:
        f = open(FILE, "wb")
        m = encrypt(b'GOOD')
        csoc.sendall(m)
    except:
        e = encrypt(b'FAIL')
        csoc.sendall(e)
        csoc.close()
        csoc=None
        status = 'failed'
        return

    time.sleep(1)
    #recieve file
    m_decrypted=None
    m=None
    while m_decrypted != b'':
        m = csoc.recv(BUFFER_SIZE + 16) #for some reason my client padder always adds 16 bytes to the message.... messed things up for 2 days!!!!
        if m == b'': break
        m_decrypted = decrypt(m)
        if m_decrypted != b'':
            f.write(m_decrypted)

    f.close()
    #log success
    printlog("status = "+status)

def readfile():
    status = 'sucess'
    try:
        f = open(FILE, "rb")
    except:
        e = encrypt(b'FILE NOT READABLE')
        csoc.sendall(e)
        status = 'failure'
        return

    sendit = b'GOOD2'
    m = encrypt(sendit)
    csoc.sendall(m)

    #SEND FILE
    data=None
    data = f.read(BUFFER_SIZE)
    while data != b'':
        padded_encrypted_data = encrypt(data)
        csoc.sendall(padded_encrypted_data)
        data = f.read(BUFFER_SIZE)

    #log success
    printlog("status: " + status)
    csoc.close()
    return


def createIV(nonce, cipher):
    sha_iv = hashlib.sha256()
    sha_iv.update((args.key+nonce+"IV").encode())
    IV = sha_iv.digest()[:16]
    return IV


def createKEY(nonce, cipher):
    sha_key = hashlib.sha256()
    sha_key.update((args.key+nonce+"SK").encode())
    if cipher == "aes128":
        KEY = sha_key.digest()[:16]
        return KEY
    elif cipher == "aes256":
        KEY = sha_key.digest()
        return KEY
    else:
        #is null cipher.
        pass

def printlog(message):
    print((datetime.datetime.now()).strftime("%H:%M:%S") + ": " + message)


def challenge():

    #challenge must be encrypted
    rand_alphnum = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(256))
    rand_alphnum_bytes = rand_alphnum.encode()
    sha = hashlib.sha256()
    sha.update(rand_alphnum_bytes)
    sha.update(args.key.encode()) #must be encoded before hashing

    data = encrypt(rand_alphnum_bytes)
    csoc.sendall(data)

    response = csoc.recv(1024)
    response = decrypt(response)

    if response != sha.digest():
        printlog("error - bad key")
        return False
    elif response == sha.digest():
        return True


def encrypt(plane_data):
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plane_data) + padder.finalize()
    if use_cipher == "null":
        padded_cipher_data = padded_data
    elif use_cipher == "aes128" or use_cipher=="aes256":
        cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV), backend=backend)
        encryptor = cipher.encryptor()
        padded_cipher_data = encryptor.update(padded_data) + encryptor.finalize()
    else:
        print("should never get here")
        print(use_cipher)

    return padded_cipher_data



def decrypt(padded_cipher_data):
    unpadder = padding.PKCS7(128).unpadder()
    if use_cipher == "null":
        plane_data = unpadder.update(padded_cipher_data) + unpadder.finalize()
    else:
        cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV), backend=backend)
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(padded_cipher_data) + decryptor.finalize()
        plane_data = unpadder.update(padded_data) + unpadder.finalize()

    return plane_data


def Main():
#Server should run forever.

    ssoc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    HOST = "localhost"
    PORT = args.port
    ssoc.bind((HOST,PORT))
    ssoc.listen()
    #print some connection stuff here with timedate
    print("Listening on port: "+str(PORT))
    print("Using Secret Key: "+args.key)

    while True:
        global csoc
        csoc, addr = ssoc.accept()
        #ssoc.listen()
        #print some stuff here about accepting a connection

        #doesn't need to be threaded this time.
        handle(csoc)
        csoc.close()


if __name__ == "__main__":
    Main()
