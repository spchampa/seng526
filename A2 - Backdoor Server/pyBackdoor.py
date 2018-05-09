'''
Last Name:  Champagne
First Name: Steven
Course:     CPSC526
Assignment: 2
Tutorial:   T03
Date:       2017-10-15
Files Submitted: report.txt, pyBackdoor.py
'''

import socketserver
import socket
import threading
import sys
import os
import shutil
import hashlib
import pickle


HARDWIRED_PASSWORD = "pass"
MAX_PASSWORD_SIZE = 32
SERVER_IS_ON = True
SNAP_FILE_NAME = "snap_file"
HELP_DICT = {
        "pwd":"Prints Working Directory",
        "cd":"Changes Working Directory. eg. cd <dir>",
        "ls":"Lists Files And Permissions In Working Directory",
        "cp":"Copies A File. eg. cp <file> <copy_of_file>",
        "mv":"Renames File & | Moves It. eg. mv <file> <new_location>",
        "rm":"Deletes A File. eg. rm <file>",
        "cat":"Reads A File. eg. cat <file>",
        "snap":"Calculates Hashes & Remembers Files",
        "diff":"Compares Current State To Snap State",
        "help":"Use help [cmd] to view comands info individiaully",
        "logout":"Terminates 'This' Thread (Server Still Up)",
        "off":"Shuts Down The Backdoor Server",
        "ps":"Displays User Processes",
        "who":"Displays Who Is Logged-In"
    }


#def off_signal_handler(server):
#    server.shutdown()

def Main():
    HOST, PORT = "localhost", int(sys.argv[1])
    server = socketserver.ThreadingTCPServer((HOST, PORT), MyTCPHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()

class MyTCPHandler(socketserver.BaseRequestHandler):
    BUFFER_SIZE = 4096 #50 bytes is one char and other stuff sent like /r/n... 51 bytes is 2 char... etc.

    #function that gets password. if incorrect password should drop connection.
    def check_password(self):
        self.request.sendall(bytes("Enter Password:", 'utf-8'))
        user_pass = self.request.recv(MAX_PASSWORD_SIZE).decode('utf-8').rstrip()
        if user_pass == HARDWIRED_PASSWORD :
            #print to server stdout
            print("%s (%s) login SUCCESS: password: %s" % (self.client_address[0],threading.currentThread().getName(), user_pass.strip()))
            #send to connected user
            self.request.sendall( bytearray( "Welcome User!\n", "utf-8"))
            return True
        else:
            self.request.sendall( bytearray( "GOODBYE\n", "utf-8"))
            print("%s (%s) login FAILURE: %s" % (self.client_address[0],threading.currentThread().getName(), user_pass.strip()))
            return False

    #Functions to handle transmissions
    def to_client_format1(self, cmd):
        self.request.sendall(bytes(cmd, 'utf-8'))
    def to_client_format2(self, cmd):
        self.request.sendall(bytes(cmd + '\n', 'utf-8'))
    def debug_to_terminal_format1(self, cmd):
        print("%s (%s): %s" % (self.client_address[0],threading.currentThread().getName(), cmd.strip()))
    def debug_to_terminal_format2(self, cmd):
        print("%s (%s): %s" % (self.client_address[0],threading.currentThread().getName(), cmd.rstrip('\n')))
    def from_client_format(self):
        return self.request.recv(self.BUFFER_SIZE).decode('utf-8').rstrip('\n')
    def print_dict_to_client(self, this_dict):
        for key, value in this_dict.items():
            self.to_client_format2(key + ':\t\t' + value)


    #function that reads lines from popen commands and returns a non-stripped string.
    def popen_wrapper(self, cmd):
        opened = os.popen(cmd, "r")
        read_line = opened.readline()
        lines = read_line
        while read_line:
            read_line = opened.readline()
            lines += read_line
        return lines

    def make_snap(self):
        snap_dict = {}
        opened = os.popen("ls -p | grep -v /", "r")
        read_line = opened.readline().rstrip('\n')
        while read_line:
            if read_line == SNAP_FILE_NAME:
                pass
            else:
                sha_hash = self.compute_hash(read_line)
                snap_dict[read_line] = sha_hash
            read_line = opened.readline().rstrip('\n')
        return snap_dict

    def save_snap(self, d):
        self.save_obj(d, SNAP_FILE_NAME)

    def compute_hash(self, line):
        f = open(line, "rb")
        sha = hashlib.sha256()
        while True:
            data = f.read(self.BUFFER_SIZE)
            if not data:
                break
            sha.update(data)
        f.close()
        return sha.hexdigest()

    #serializes and saves the snap to filesystem
    def save_obj(self, obj, name ):
        with open(name, 'wb') as f:
            pickle.dump(obj, f)
        f.close()

    #loads the snap as a dictionary
    def load_obj(self, name):
        with open(name, 'rb') as f:
            return pickle.load(f)

    def compare_snaps(self, current_d):
        try:
            snapped_d = self.load_obj(SNAP_FILE_NAME)
        except FileNotFoundError:
            self.to_client_format2("NO Snap In this directory yet.")
            return

        for c_key, c_val in current_d.items():
            if c_key not in snapped_d.keys():
                if c_val not in snapped_d.values():
                    self.to_client_format2(c_key + "\t\t - WAS ADDED")
                if c_val in snapped_d.values():
                    self.to_client_format2(c_key + "\t\t - WAS CHANGED")
            if c_key in snapped_d.keys():
                if c_val not in snapped_d.values():
                    self.to_client_format2(c_key + "\t\t - WAS MODIFIED")
        for s_key, s_val in snapped_d.items():
            if s_key not in current_d.keys():
                if s_val not in current_d.values():
                    self.to_client_format2(s_key + "\t\t - WAS DELETED")
                if s_val in current_d.values():
                    self.to_client_format2(s_key + "\t\t - WAS MOVED")


    # ELIFS to handle commands
    def run_cmd(self, cmd):

        cmd_split = cmd.split()
        if len(cmd_split) == 0:
            return

        #check that the request is smaller than the buffer size
        if sys.getsizeof(cmd) > self.BUFFER_SIZE:
            self.to_client_format2("BUFFER EXCEEDED")
            del cmd
        elif cmd == 'secretHiddenTestCommand':
            self.to_client_format1("RETURN TEST 1")
            self.to_client_format2("RETURN TEST 2")
            self.debug_to_terminal_format1("TF TEST 1")
            self.debug_to_terminal_format2("TF TEST 2")
            self.debug_to_terminal_format1("TF TEST 3")
        elif cmd == 'pwd':
            self.to_client_format2(os.getcwd())
        elif cmd_split[0] == 'cd':
            try:
                os.chdir( cmd_split[1])
                self.to_client_format2(os.getcwd())
            except:
                self.to_client_format2("Could not change directory")
        elif cmd == 'ls':
            self.to_client_format2(self.popen_wrapper('ls -la'))
        elif cmd_split[0] == 'cp':
            try:
                shutil.copyfile(os.getcwd() + '/' + cmd_split[1], os.getcwd() + '/' + cmd_split[2])
                self.to_client_format2("OK")
            except FileNotFoundError:
                self.to_client_format2("File Not Found")
        elif cmd_split[0] == 'mv':
            try:
                shutil.move(os.getcwd() + '/' + cmd_split[1], os.getcwd() + '/' + cmd_split[2])
                self.to_client_format2("OK")
            except FileNotFoundError:
                self.to_client_format2("File Not Found")
        elif cmd_split[0] == 'rm':
            try:
                os.remove(os.getcwd() + '/' + cmd_split[1])
                self.to_client_format2("OK")
            except FileNotFoundError:
                self.to_client_format2("File Not Found")
        elif cmd_split[0] == "cat":
            try:
                self.to_client_format2(open(cmd_split[1], 'r').read())
            except:
                self.to_client_format2("File Not Found")
        elif cmd == "snap":
            dictionary = self.make_snap()
            self.save_snap(dictionary)
            self.to_client_format2("OK")
        elif cmd == "diff":
            dictionary = self.make_snap()
            self.compare_snaps(dictionary)
            self.to_client_format2("OK")
        elif cmd_split[0] == "help":
            if cmd == "help":
                self.print_dict_to_client(HELP_DICT)
            elif cmd_split[1] in HELP_DICT.keys():
                self.to_client_format2(cmd_split[1] + ':\t' + HELP_DICT[cmd_split[1]])
            pass
        elif cmd == "logout":
            self.to_client_format2("BYE")
            #need to break out of the self.handle loop
            return "escape"
        elif cmd == "off":
            SERVER_IS_ON = False
            self.to_client_format2("BYE -- Still Doesn't Work")
            #set global variable SERVER_IS_ON to False and break the handle while loop.
            #signal.signal(signal.SIG_DFL, off_signal_handler)
            return "escape"
        elif cmd == "ps":
            self.to_client_format2(self.popen_wrapper('ps -u'))
        elif cmd == "who":
            self.to_client_format2(self.popen_wrapper('who'))
        else:
            pass

    def handle(self):
        returned_pwd = self.check_password()
        #check for input
        while returned_pwd:
            # make a prompt to enter cmds that has username and filepath like terminal
            cmd = self.request.recv(self.BUFFER_SIZE).decode('utf-8').rstrip('\n')
            print("%s (%s) said: %s" % (self.client_address[0],threading.currentThread().getName(), cmd.strip()))
            output = self.run_cmd(cmd)
            if output == "escape":
                break


if __name__ == "__main__":
    Main()
