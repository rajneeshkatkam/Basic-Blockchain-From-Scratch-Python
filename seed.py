import socket
import sys
import time
import threading
from queue import Queue

NUMBER_OF_THREADS = 2
JOB_NUMBER = [1, 2]
queue = Queue()
host = '0.0.0.0'

if len(sys.argv) >1:
    port = int(sys.argv[1])
else:
    print("Please provide port number as argument for seed")
    sys.exit()


peer_list = []


# shell thread functions below
def start_shell():
    '''
    This function will be run by an independent thread and act as a interactive shell.
    Supported commands are:
        list : Will list all the connected peers
        exit : Will Quit this Seed
    '''
    global thread_run
    thread_run=True

    while thread_run:
        cmd=input("shell> ")
        if cmd == 'list':
            list_connections()

        elif 'exit' in cmd:
            thread_run=False
            print("Exiting Seed...")
            break
        else:
            print("Command not recognised")


# Function to list all the connected peers
def list_connections():
    '''
    This function will list all the connected peers on  terminal.
    '''
    print("------- My Peer List ------")
    for i, address in enumerate(peer_list):
        print("  "+str(i+1) + ". "+ str(address))



# creating object of socket
def create_socket():
    try:
        global s
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(5)
    except socket.error as msg:
        print("Socket creation error: "+str(msg))


# binding the socket
def bind_socket():
    try:
        print("Binding the port: "+str(port))
        s.bind((host, port))
        s.listen(5)

    except socket.error as msg:
        print("Socket Binding error: "+str(msg))
        time.sleep(5) # Time to sleep before reattempting the bind connection
        bind_socket()


# Handling connections from multiple clients and saving to a list
# Closing previous connections if any
def accepting_connections():
    '''
    This is a function for a Thread which will run for the entire life or program and accept connections on the provided port.
    Then it'll also process according to the received response.
    '''
    global thread_run
    thread_run=True

    del peer_list[:]

    while thread_run:
        try:
            conn, address = s.accept()

            peer_response=str(conn.recv(1024).decode("utf-8"))

            if  "New Connection Request Seed" in peer_response:
                peer_port = peer_response[peer_response.find(":")+2:]
                print("peer_port:"+peer_port)
                #“Success:<peer request IP>:[<Peer List>]”
                send_message="Success#"+str(address[0])+"#"+str(peer_list)
                conn.send(str.encode(send_message))
                ip_port_str=str(address[0])+":"+peer_port
                peer_list.append(ip_port_str)
                out_string=f"Connection established with peer => {ip_port_str} \n"

                with open("outputseed.txt", "a") as file:
                    file.write(out_string)
                
                print(out_string)  # Displaying IP and Port
           
            elif "Dead Node" in peer_response:
                print("Delete the node from peer_list")
                # msg="Dead Node: "+str(peer.ip)+":"+str(peer.port)+":"+str(ts)+":"+str(myip)
                msg_split = peer_response.split(":")
                dead_node = msg_split[1] + ":" + msg_split[2]
                try:
                    peer_list.remove(dead_node)
                    msg="Dead Node Deleted Successfully =>" + dead_node
                    print(msg)
                    with open("outputseed.txt", "a") as file:
                        file.write(msg + '\n')
                except:
                    msg="Dead Node Unsuccessful"
                conn.send(bytes(msg, "utf-8"))


            conn.close()
        except socket.error as msg :
            if "timed out" not in str(msg):
                print("accepting_connections() Error: "+ str(msg))
            continue


def listening_connections():
    create_socket()
    bind_socket()
    accepting_connections()


# Cleaning / Creating output file
with open("outputseed.txt", "w") as file:
    pass



#Creating Threads for listening and other tasks

t1= threading.Thread(target=start_shell)
t1.daemon=True
t1.start()

t2=threading.Thread(target=listening_connections)
t2.daemon=True
t2.start()

t1.join()
t2.join()
