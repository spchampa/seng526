'''
Last Name:  Champagne
First Name: Steven
Course:     CPSC526
Assignment: 4: Encrypted File Transfer
Tutorial:   T03
Date:       2017-11-11
Files Submitted: report.pdf, myclient4.py, myserver4.py

python version: 3.6.2

ARGS PROTOTYPE: script.py <COMMAND> <FILENAME> <HOST:PORT> <CIPHER> <SECRETKEY>

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
import sys
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import padding
import time


#parsing the args
parser = argparse.ArgumentParser(description="Encrypted File Transfer Client.")
parser.add_argument("command", type=str, help="Write to OR read from file server.")
parser.add_argument("filename", type=str, help="Name of file to read/write.")
parser.add_argument("hostport", metavar='hostname:port', type=str, help="Network address of server.")
parser.add_argument("cipher", type=str, help="aes128, or aes256, or null")
parser.add_argument("key", type=str, help="Secret key for the server.")
args = parser.parse_args()
hostport = args.hostport.split(':')

if (args.cipher == "null") or (args.cipher == "aes128") or (args.cipher == "aes256"):
    pass
else:
    print("ERROR: UNSUPPORTED CIPHER")
    quit()

#globals
IV = b''
KEY = b''
backend = default_backend()
soc = None
BUFFER_SIZE = 1024




def Main():
    #Initialize Socket
    HOST = hostport[0]
    PORT = int(hostport[1])
    global soc
    soc = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        soc.connect((HOST,PORT))
    except ConnectionRefusedError as e:
        print("Connection Refused: Probably Port Locked or Server Offline.")

    #First: Client must inform server which cipher to use and a nonce. Sent unencrypted.
    #FROM: https://stackoverflow.com/questions/2511222/efficiently-generate-a-16-character-alphanumeric-string
    nonce = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
    soc.sendall((args.cipher + "_" + nonce).encode())#remember must be bytes

    ### EVERYTHING AFTER THIS POINT MUST BE ENCRYPTED ###
    #Create IV & Session Key from secret key and nonce
    global IV, KEY
    IV = createIV(nonce)
    KEY = createKEY(nonce)

    ## Compute Server Challenge & Respond: client->server: recieve challenge & send response
    rand_alphnum_bytes = soc.recv(1024)
    data = decrypt(rand_alphnum_bytes)

    sha = hashlib.sha256()
    sha.update(data)
    sha.update(args.key.encode())
    response = encrypt(sha.digest())
    soc.sendall(response)

    ## if not right exit gracefully


    ## TELL SERVER READ OR WRITE client->server: operation & fliename
    cmd_file = (args.command + "_" + args.filename).encode()
    cmd_file_enc = encrypt(cmd_file)
    soc.sendall(cmd_file_enc)

    ## IF IT WAS WRITE SEND INFO ##
    if args.command == "write":
        send_STDIN(soc)

    ## IF IT WAS READ WAIT FOR IF FILE EXISTS, THEN RECIEVE DATA. ##
    elif args.command == "read":
        read()

    else:
        print("ERROR: IMPROPER COMMAND GIVEN")
        return



def send_STDIN(soc):
    # Confirm file is writable

    m=soc.recv(1024)
    #print(m)
    m_decrypted = decrypt(m)
    #print(m_decrypted)

    if m_decrypted != b'GOOD': #changed
        print("ERROR: FILE UNWRITABLE")
        soc.close()
        quit()

    #send file
    content = None
    while content != b'':
        content = sys.stdin.buffer.read(BUFFER_SIZE)
        if content == b'': break
        s = encrypt(content)
        soc.sendall(s)
    #transfer complete
    print("OK")



def read():
    #read a file from server and save to current dir.

    #try to open file at this dir to see if can write
    try:
        f = open(args.filename, "wb")
    except:
        print("CLIENT ERROR: CAN NOT OPEN FILE TO WRITE HERE")
        soc.close()
        quit()

    #Wait for response if file exists on server.
    this_m =soc.recv(16)
    this_m2 = decrypt(this_m)

    if ( this_m2 != b'GOOD2'):
        print("SERVER SAYS: FILE DOES NOT EXIST ON SERVER")
        soc.close()
        quit()

    #time.sleep(1)
    #recieve file
    m_decrypted=None
    m=None
    while m_decrypted != b'':
        m = soc.recv(BUFFER_SIZE+16)#+16
        if m == b'': break
        m_decrypted = decrypt(m)
        if m_decrypted != b'':
            f.write(m_decrypted)

    f.close()
    #Transfer complete
    print("OK")



def createIV(nonce):
    sha_iv = hashlib.sha256()
    sha_iv.update((args.key+nonce+"IV").encode())
    IV = sha_iv.digest()[:16]
    return IV



def createKEY(nonce):
    sha_key = hashlib.sha256()
    sha_key.update((args.key+nonce+"SK").encode())
    if args.cipher == "aes128":
        KEY = sha_key.digest()[:16]
        return KEY
    elif args.cipher == "aes256":
        KEY = sha_key.digest()
        return KEY
    else:
        #is null cipher.
        pass



def encrypt(plane_data):
    padder = padding.PKCS7(128).padder()
    padded_data = padder.update(plane_data) + padder.finalize()
    if args.cipher == "null":
        padded_cipher_data = padded_data
    elif args.cipher == "aes128" or args.cipher=="aes256":
        cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV), backend=backend)
        encryptor = cipher.encryptor()
        padded_cipher_data = encryptor.update(padded_data) + encryptor.finalize()
    else:
        print("should never get here")
        print(use_cipher)
        pass

    return padded_cipher_data



def decrypt(padded_cipher_data):
    unpadder = padding.PKCS7(128).unpadder()
    if args.cipher == "null":
        plane_data = unpadder.update(padded_cipher_data) + unpadder.finalize()
    else:
        cipher = Cipher(algorithms.AES(KEY), modes.CBC(IV), backend=backend)
        decryptor = cipher.decryptor()
        padded_data = decryptor.update(padded_cipher_data) + decryptor.finalize()
        plane_data = unpadder.update(padded_data) + unpadder.finalize()

    return plane_data


if __name__ == "__main__":
    Main()
