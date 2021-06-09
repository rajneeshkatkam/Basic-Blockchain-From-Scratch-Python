import calendar
import random
import socket
import sys
import threading
import time
from hashlib import sha256
from queue import Queue
import sqlite3
from datetime import datetime
import numpy as np
import pydot
from io import BytesIO
from PIL import Image
from prettytable import PrettyTable

# This is the structure which holds a peer details
class Peer:
    def __init__(self, ip, port):
        self.ip = ip
        self.port = port
        self.dead_counter = 0

        
    

def clear_out_files():
    """Clears all the output files
    """
    files = ["dead_node_list.txt", "seed_peer_list.txt",  "Severity.txt"]
    for out_file in files:
        with open(out_file, "w") as file:
            pass


# Socket Functionalities Below --------------------------
if len(sys.argv) > 1:
    port = int(sys.argv[1])
else:
    print("Please provide port number as argument for peer")
    sys.exit()

# creating object of socket

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)


def create_socket():
    """This Function Will Create and initialize socket with certain parameters
    """
    try:
        global server_socket
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.settimeout(5)
    except socket.error as msg:
        print("Socket creation error: "+str(msg))


# binding the socket
def bind_socket():
    try:
        print("Binding the port: "+str(port))
        server_socket.bind(('', port))
        server_socket.listen(10)

    except socket.error as msg:
        print("Error binding with port:"+str(port) +
              " Please exit and try other port")
        time.sleep(5)
        bind_socket()



thread_run = True
myip=''

pending_blocks_list=[]

inter_arrival_time = 2  # 20 seconds is the intially inter-arrival time
node_hash_power= 25 #will change the power of the hash node, by command


last_block_hash_pointer = "0x9e1c"  # Will point to the last myHash(coloumn) block in the DB and will get updated only when incoming block height is great then last_block_hash_pointer_height
last_block_hash_pointer_height = 0  # this is the height of the last_block_hash_pointer and will update when a incoming block points to this last_block_hash_pointer

db_lock_free=True  # Lock for accessing DB

cursor = ''
connection = ''


# Handling connections from multiple clients and saving to a list
# Closing previous connections if any
def accepting_connections():
    '''
    This is a function for a Thread which will run for the entire life or program and accept connections on the provided port.
    Then it'll also process according to the received response.
    '''
    global thread_run
    global myip
    global pending_blocks_list
    thread_run = True

    while thread_run:
        try:
            conn, address = server_socket.accept()
            client_response = str(conn.recv(1024).decode("utf-8"))

            if("New Connection Request Peer" in client_response):  # New Connection Request
                if(len(final_peer_object_list) < 4):
                    connected_peer_port = client_response[client_response.find(
                        ":")+2:]
                    peer_object = Peer(address[0], int(connected_peer_port))
                    final_peer_object_list.append(peer_object)
                    conn.send(bytes("New Connection Accepted", "utf-8"))
                else:
                    conn.send(bytes("New Connection Failed", "utf-8"))
                conn.close()

            elif("Liveness Request" in client_response):  # Liveness Message
                _, sender_ts, sender_ip = client_response.split(':')
                msg = "Liveness Reply: " + \
                    str(sender_ts)+":"+str(sender_ip)+":"+str(myip)
                conn.send(bytes(msg, "utf-8"))
                conn.close()


            elif("Blocks fetch" in client_response):  # Entire Blockchain fetch for new Block
                fwd_blockchain = threading.Thread(target=entire_blockchain_fwd_to_peer, args=(conn,))
                fwd_blockchain.daemon = True
                fwd_blockchain.start()
            
            elif("Blocks Fwd: " in client_response):  # Block fwd from peer
                pending_blocks_list.append(client_response)
                conn.send(bytes("Blocks Fwd Received", "utf-8"))
                conn.close()

            # elif("Gossip Message" in client_response):  # Gossip Message
            #     conn.send(bytes("Gossip Message Received", "utf-8"))
            #     # Thread created for gossip_forward_protocol function
            #     t4 = threading.Thread(target=gossip_forward_protocol, args=(client_response,))
            #     t4.daemon = True
            #     t4.start()
            #     conn.close()

            else:
                print("Peer request: " + client_response)
                conn.close()
            

        except socket.error as msg:
            if "timed out" not in str(msg):
                print("accepting_connections() Error: " + str(msg))
            continue

# Socket Functionalities End --------------------------


# Final Peer List Formation Functions -----------------------

# Global variables for peer functionality
message_list = []
final_peer_object_list = []
union_peer_object_list = []
final_seed_list = []


def connecting_to_seeds_and_union_list():
    '''
    This function will first read the config.txt file and select floor(n/2) + 1 seeds.
    Then try to connect with them and make a union of provided peers list from those seeds.
    It'll also print terminal if a seed in config is down.
    '''
    global union_peer_object_list
    global final_peer_object_list
    global final_seed_list
    global myip
    myip = ''

    config_file = open("config.txt", "r")
    all_seeds = config_file.readlines()
    k = int(len(all_seeds)/2) + 1
    final_seed_list = random.sample(all_seeds, k)
    final_seed_list = [seed.strip("\n") for seed in final_seed_list]
    union_set_peers = set()
    print("Selected Seed List:", final_seed_list)
    for seed in final_seed_list:
        try:
            seed = str(seed).strip()  # to remove the "\n" character
            seed_address = seed.split(':')
            client_socket = socket.socket()
            # at index 0 - host, at index 1 - port.
            client_socket.connect((seed_address[0], int(seed_address[1], 10)))
            # give info to seed about the new connection of peer.
            client_socket.send(
                bytes("New Connection Request Seed: " + sys.argv[1], "utf-8"))
            client_socket_response = str(
                client_socket.recv(1024).decode("utf-8"))
            with open("seed_peer_list.txt", "a") as file:
                file.write("Seed: " + str(seed) + " => Peer List:" +
                           str(client_socket_response) + "\n\n")
            splited_response = client_socket_response.split('#')
            if "Success" in splited_response[0]:
                myip = splited_response[1]
                client_socket_response = splited_response[2]
                peers_list_of_seed = client_socket_response.strip('][').split(
                    ', ')  # considering seed will send the format as  'IP:PORT'
                if len(peers_list_of_seed) > 0:
                    for peer in peers_list_of_seed:
                        if len(str(peer)) > 0:
                            union_set_peers.add(peer)
            client_socket.close()
        except socket.error as msg:
            print("Seed =>"+str(seed)+" doesn't exist")

    if len(union_set_peers) > 0:
        union_peer_object_list = create_union_peer_object_list(union_set_peers)
    if len(union_peer_object_list) > 0:
        final_peer_object_list = creating_final_peer_object_list(
            union_peer_object_list)

    # print("Length of final_peer_object_list is: "+str(len(final_peer_object_list)))


# creating peer objects for union_peer_list
def create_union_peer_object_list(union_set_peers):
    '''
    This Function will just return Peer Objects (Class) from provided list of peers in IP:PORT format
    '''
    temp_union_peer_object_list = []
    for peer in union_set_peers:
        peer = str(peer).strip("'")
        address = peer.split(':')
        peer_object = Peer(address[0], int(address[1]))
        temp_union_peer_object_list.append(peer_object)

    return temp_union_peer_object_list

# creating final_peer_object_list


def creating_final_peer_object_list(union_peer_object_list):
    '''
    This function will try to establish connection with a selected peers from the union peer object list.
    If a peer deny to connect (Already connected with 4 peers) then it'll simply skip that peer and try with the next peer.
    And return the final coonected peers object list of atmost 4.
    '''
    temp_final_peer_object_list = []
    # generate random number between 1 and 4
    random_max_number = random.randint(1, 4)
    for peer_object in union_peer_object_list:
        try:
            client_socket = socket.socket()
            client_socket.connect((peer_object.ip, peer_object.port))
            client_socket.send(
                bytes("New Connection Request Peer: "+sys.argv[1], "utf-8"))
            client_socket_response = str(
                client_socket.recv(1024).decode("utf-8"))
            if(client_socket_response == "New Connection Failed"):
                print("Failed with Seed Response: " +
                      str(client_socket_response))
                client_socket.close()
                continue
            elif(client_socket_response == "New Connection Accepted"):
                temp_final_peer_object_list.append(peer_object)

            if(len(temp_final_peer_object_list) == random_max_number):
                client_socket.close()
                break
            client_socket.close()
        except socket.error as msg:
            print("Failed connecting with Peer =>" +
                  str(peer_object.ip)+":"+str(peer_object.port))
            delete_node_request_to_seeds(peer_object)

    return temp_final_peer_object_list


# Final Peer List Formation Functions End-----------------------


# Gossip Functions -----------------------

def get_hash(msg):
    '''
    This function will take a string msg as parameter and return it's hexdigested SHA256 hash
    '''
    return sha256(msg.encode()).hexdigest()





# Liveness Functions ---------------------------------

def liveliness_protocol():
    '''
    This function will be run by an independent thread which will send and process liveness requests.
    '''
    global thread_run
    thread_run=True
    global myip
    while thread_run:
        for peer in final_peer_object_list:
            try:
                client_socket=socket.socket()
                ts = calendar.timegm(time.gmtime())
                client_socket.connect((peer.ip,peer.port))
                msg="Liveness Request: "+ str(ts) +":"+str(myip)
                #print(msg+":"+str(peer.port))
                client_socket.send(bytes(msg, "utf-8"))
                client_socket_response=str(client_socket.recv(1024).decode("utf-8"))
                #print(client_socket_response)
                if("Liveness Reply:" in client_socket_response):
                    client_socket.close()
                    peer.dead_counter = 0    
                    continue
                else:
                    peer.dead_counter+=1
                    if(peer.dead_counter>=3):
                        delete_node_request_to_seeds(peer)   # Removing from Seed's Peer List
                        final_peer_object_list.remove(peer) # Removing from final_peer_object_list 
                client_socket.close()

            except socket.error as msg:
                peer.dead_counter+=1 # Dead count increases if the adjacent peer didn't respond.
                print("Peer =>"+ str(peer.ip)+":"+str(peer.port)+ " didn't respond. Dead Counter value of the peer is: " +str(peer.dead_counter))
                if(peer.dead_counter>=3):
                    delete_node_request_to_seeds(peer)   # Removing from Seed's Peer List
                    final_peer_object_list.remove(peer) # Removing from final_peer_object_list 

        time.sleep(13)  # sleeps for 13 seconds and then again starts liveness again



def delete_node_request_to_seeds(peer):
    '''
    Argument: peer

    This function will broadcast this peer as dead to all the connected seeds
    '''
    global myip
    count = 0
    print("delete_node_request_to_seeds() start")
    print(final_seed_list)
    for seed in final_seed_list:
        try:
            client_socket=socket.socket()
            seed = str(seed).strip()   #to remove the "\n" character
            seed_address = seed.split(':')
            ts = calendar.timegm(time.gmtime())
            client_socket.connect((seed_address[0],int(seed_address[1],10))) # at index 0 - host, at index 1 - port.
            msg="Dead Node:"+str(peer.ip)+":"+str(peer.port)+":"+str(ts)+":"+str(myip)
            client_socket.send(bytes(msg,"utf-8"))  #give info to seed about deletion of dead peer.
            if count == 0:
                with open("dead_node_list.txt", "a") as file:
                    file.write(msg + "\n")
                count = 1
            client_socket_response=str(client_socket.recv(1024).decode("utf-8"))
            print(client_socket_response + " Seed =>" + str(seed))
            client_socket.close()
        except socket.error as msg:
            print("delete_node_request_to_seeds() Error: "+str(msg))
                
        

# Liveness Functions Ends---------------------------------


# Flooding Functions ---------------------------------
flood_thread_run = False

def flooding_protocol(peer_nos):
    '''
    This function will be run by an independent thread which will flood the connected peers.
    '''
    if peer_nos < 1 or peer_nos > len(final_peer_object_list):
        print("Please enter a number from {} to {} for flooding,\n".format(1, len(final_peer_object_list)))
        return
    peer_to_flood = random.sample(final_peer_object_list, peer_nos)
    for current_peer in peer_to_flood:
        print(current_peer.ip , ":" , current_peer.port)
    time.sleep(5)
    while flood_thread_run:
        # print("flooding_protocol() Loop")
        for peer in peer_to_flood:
            threading.Thread(target=flood_thread, args=(peer,)).start()
        time.sleep(1)  # sleeps for 1 seconds and then again starts flooding again

def flood_thread(peer):
    """Flood the peer given as argument
    """
    try:
        client_socket=socket.socket()
        client_socket.connect((peer.ip,peer.port))
        
        flood_previous_block_hash = last_block_hash_pointer # This function gives the last block hash to mine on, needs to implement it (Vipin work)
        ts = calendar.timegm(time.gmtime())
        invalid_merkel_root = "0x1111" # Invalid Merkel root value
        # new_block = last_block_hash_pointer + ";" + str(current_time) + ";" + merkel_root + ";" + str(myip) + ":" + str(port)
        block_header = "Blocks Fwd: "+str(flood_previous_block_hash)+';'+str(ts)+ ';'+str(invalid_merkel_root)+';'+myip+":"+str(port)

        # print("Flood message sent to "+ peer.ip +":"+str(peer.port)+"is :  " + block_header)
        client_socket.send(bytes(block_header, "utf-8"))
        # client_socket_response=str(client_socket.recv(1024).decode("utf-8"))
        client_socket.close()

    except socket.error as msg:
        print("flood_thread(): "+ str(msg))



# Flooding Functions End =================================


def listening_connections():
    """This function will start accepting connections
    """
    create_socket()
    bind_socket()
    accepting_connections()


# Output Functions Started ==================

def print_db():
    """This function prints the whole DB of BLOCKCHAIN as a PrettyTable
    """
    global db_lock_free
    db_table=PrettyTable()
    db_table.field_names=["prev_block_hash", "block_hash", "timestamp", "blockchain_height", "ip_port"]
    while db_lock_free == False:
        print("db_lock not free")
        time.sleep(1)
    db_lock_free = False
    course_lists=cursor.execute('''select * from BLOCKCHAIN''').fetchall()

    db_lock_free = True
    for row in course_lists:
        db_table.add_row(row)
    
    print(db_table)

def print_chain():
    """ Prints the longest chain as a PrettyTable
    """
    db_table=PrettyTable()
    db_table.field_names=["prev_block_hash", "block_hash", "timestamp", "blockchain_height", "ip_port"]
    course_lists=fetch_all_blocks_from_DB()

    for row in course_lists:
        db_table.add_row(row)
    
    print(db_table)

def whole_db():
    """To Fetch all the blocks/records from table BLOCKCHAIN

    Returns:
        List of Tuples: List of all the records/blocks in the form of Tuple
    """
    global db_lock_free
    while db_lock_free == False:
        print("db_lock not free")
        time.sleep(1)
    db_lock_free = False
    all_blocks = cursor.execute('''select * from BLOCKCHAIN''').fetchall()
    db_lock_free = True
    return all_blocks

def make_graph():
    """ 
        This Function Creates a Directed Hierarchical Graph of all the blocks including forks. Apart from showing the output it also saves the graph as a PNG file.
        This Function Should be run as an independent thread as it take some time to complete
    """
    graph = pydot.Dot(graph_type="digraph") # declarind pydot object for the graph
    all_blocks = whole_db() # Getting all the blocks from the DB
    last_block_node = "Prev_Hash: " + str(all_blocks[0][0]) + "\nMy_Hash: " + str(all_blocks[0][1]) + "\nTimestamp: " + str(all_blocks[0][2])
    node = pydot.Node(label=last_block_node, style="filled", fillcolor="green", shape="box") # Genesis Block
    node.set_name(all_blocks[0][1])
    graph.add_node(node) # Adding Genesis Block in graph
    for block in all_blocks[1:]:
        name = "Prev_Hash: " + str(block[0]) + "\nMy_Hash: " + str(block[1]) + "\nTimestamp: " + str(block[2])
        node = pydot.Node(label=name, style="filled", fillcolor="yellow", shape="box")
        node.set_name(block[1])
        graph.add_node(node)
        edge = pydot.Edge(block[0], block[1])
        graph.add_edge(edge)
    name = "Chain-" + str(calendar.timegm(time.gmtime())) + ".png"
    graph.write_png(name) # Saving the graph as a PNG image
    print("A PNG file of blockchain snapshot is saved by name", name)
    Image.open(BytesIO(graph.create_png())).show() # Opening Graph To View
    return

def shell_help():
    return """Supported Commands Are:
        list : Lists all the connected peers
        db : Prints the snapshot of db on terminal
        chain : Prints the longest chain
        graph : Displays the current snapshot and saves in PNG
        severity : Calculates and prints severity at that time
        flood start [int:no_of_nodes] : Starts Flood Attack on given no_of_nodes
        flood stop : Stops flood attack and prints and save severity in Severity.txt
        time [int:New_time] : Changes Interarrival Time to New_time
        power [int:New_Power] : Changes Power to New_Power
        help : Prints this help text
        exit : Safely Exits the node by reaping all threads
    """
# Custom Shell with some functionalities
def start_shell():
    """Supported Commands Are:
        list : Lists all the connected peers
        db : Prints the snapshot of db on terminal
        chain : Prints the longest chain
        graph : Displays the current snapshot and saves in PNG
        severity : Calculates and prints severity at that time
        flood start [int:no_of_nodes] : Starts Flood Attack on given no_of_nodes
        flood stop : Stops flood attack and prints and save severity in Severity.txt
        time [int:New_time] : Changes Interarrival Time to New_time
        power [int:New_Power] : Changes Power to New_Power
        help : Prints this help text
        exit : Safely Exits the node by reaping all threads
    """
    global thread_run
    global flood_thread_run
    global inter_arrival_time
    global node_hash_power
    thread_run=True

    while thread_run:
        cmd=input("shell> ")
        if cmd == 'list':
            list_connections()
        
        # elif( 'msgs' in cmd ):
        #     print(message_list)

        elif( 'flood start' in cmd ):
            if(flood_thread_run==False):
                cmd = cmd.split(' ')
                try:
                    peer_nos = int(cmd[2].strip())
                except:
                    print("Enter number of peerts to flood also!\n")
                    continue
                flood_thread_run=True
                threading.Thread(target=flooding_protocol, args=(peer_nos,)).start()
                print(datetime.now().strftime("%H:%M:%S"), "FLOODING ATTACK ACTIVATED...........\n\n")

        elif( 'flood stop' in cmd ):
            if(flood_thread_run==True):
                print("FLOODING ATTACK DEACTIVATED...........\n\n")
                print("CALCULATING SEVERITY......\n")
                #calculating the severity of the flood attack here.
                severity = _severity()
                print("Severity after flood attack: ", severity)
                with open("Severity.txt", 'a') as file:
                    file.write(str(peer_nos) + ";" + str(inter_arrival_time) + ";" + str(severity) + "\n")
                flood_thread_run = False
            else:
                print("Flood Attack Not Started Yet!")

        elif 'exit' in cmd:
            thread_run=False
            print("Calculating Mining Power utilizationg and Exiting Peer...")
            #calculate mining power utilisation here
            mpu = mining_power_utilization()
            print(mpu)
            break
        
        elif 'time' in cmd:
            cmd=cmd.split(' ')
            cmd=str(cmd[1]).strip()
            print("inter_arrival_time Before: "+ str(inter_arrival_time))
            inter_arrival_time = int(cmd)
            print("inter_arrival_time After: "+ str(inter_arrival_time))


        elif 'power' in cmd:
            cmd=cmd.split(' ')
            cmd=str(cmd[1]).strip()
            print("node_hash_power Before: "+ str(node_hash_power))
            node_hash_power=int (cmd)
            print("node_hash_power After: "+ str(node_hash_power))
        
        elif 'db' in cmd:
            print_db()
        
        elif 'chain' in cmd:
            print_chain()
        
        elif 'graph' in cmd:
            threading.Thread(target=make_graph).start()
        
        elif 'severity' in cmd:
            # here calculating the severity without attack
            severity = _severity()
            print("Severity without flood attack: ", severity)

        elif 'help' in cmd:
            print(shell_help())

        else:
            print("Command not recognised\n type help to see all supported commands")


def list_connections():
    '''
    This function will print all the connected peers on terminal.
    '''
    print("------- My Connected Peer List ------")
    for i, peer in enumerate(final_peer_object_list):
        print("  "+str(i+1) + ". "+ str(peer.ip)+":"+str(peer.port))


def insert_values_into_table(prev_block_hash, block_hash, timestamp, blockchain_height, ip_port):
    """This function will insert the values into the Table

    Args:
        prev_block_hash (String): Previous Block Hash
        block_hash (String): Current Block Hash
        timestamp ([String]): Timestamp for block
        blockchain_height (int): Height of block in blockchain
        ip_port (String): IP:PORT of peer which generated the block
    """
    global db_lock_free

    while db_lock_free == False:
        print("db_lock not free")
        time.sleep(2)
    db_lock_free = False

    try:
        with connection:
            cursor.execute('INSERT INTO BLOCKCHAIN VALUES (?,?,?,?,?)', (prev_block_hash, block_hash, timestamp, blockchain_height, ip_port))
    except sqlite3.Error as msg:
        print('insert_values_into_table(): '+ str(msg))

    db_lock_free = True


def fetch_block_from_table(my_hash_value):
    """Fetches block from table corresponding to my_hash coloumn value

    Args:
        my_hash_value (String): Hash of the block to fetch from DB

    Returns:
        tuple: Tuple of Block
    """
    global db_lock_free

    while db_lock_free == False:
        print("db_lock not free")
        time.sleep(1)

    db_lock_free = False

    cursor.execute('SELECT * FROM BLOCKCHAIN WHERE block_hash=(?)', (my_hash_value,))
    block_tuple=cursor.fetchone()

    db_lock_free = True

    return block_tuple



def fetch_all_blocks_from_DB():
    """Fetches longest chain from DB

    Returns:
        Blocks list will have (genesis+1)th block at index 0 and last block in main blockchain at (len(blocks)-1)th index
        List: List of all the blocks in the form of tuple
    """

    blocks=[]
    
    temp_block_pointer = last_block_hash_pointer

    for i in range(last_block_hash_pointer_height):      #  for each tuple from DB -- Starting from end node to genesis node
        fetched_block = fetch_block_from_table(temp_block_pointer)
        blocks.insert(0, fetched_block)      # --- This will insert the block at the start of the list, thus maintaining blockchain in the proper sequence
        temp_block_pointer = fetched_block[0] # Prev_hash is present a index 0 of the tuple

    
    # At the end, blocks list will have (genesis+1)th block at index 0 and last block in main blockchain at (len(blocks)-1)th index

    return blocks



def entire_blockchain_fwd_to_peer(conn):
    """Forwards the longest chain to the peer

    Args:
        conn (Sockets Connection): Connection Object of the destination peer
    """
    try:
        conn.send(bytes("Sending blocks", "utf-8"))
        client_response = str(conn.recv(1024).decode("utf-8"))
        send_blocks_list=fetch_all_blocks_from_DB()   # List of tuples where each tuple represents a block

        while len(send_blocks_list):
            block=send_blocks_list.pop(0)  
            message="Block: "+str(block)    # Sending tuple directly so the receiver will extract the values of block directly from tuple using parser
            conn.send(bytes(message, "utf-8"))
            client_response = str(conn.recv(1024).decode("utf-8"))   # client_response = "Block OK" will be received

        conn.send(bytes("End Blockchain", "utf-8"))   # End of blocks i.e. send_blocks_list becomes empty
        conn.close()

    except socket.error as msg:
        print("entire_blockchain_fwd_to_peer(): "+ str(msg))




def fetch_entire_blockchain():
    """
    To Fetch and insert the whole chain from connected peers
    """
    global cursor
    global connection
    global last_block_hash_pointer
    global last_block_hash_pointer_height
    
    connection = sqlite3.connect('BLOCKCHAIN_DB.db', check_same_thread=False)
    cursor = connection.cursor()

    #(prev_block_hash, block_hash, timestamp,  blockchain_height, ip_port)  

    cursor.execute('DROP TABLE IF EXISTS BLOCKCHAIN')
    create_table_command=""" 
    CREATE TABLE IF NOT EXISTS BLOCKCHAIN(prev_block_hash TEXT, block_hash TEXT, timestamp TEXT, blockchain_height TEXT, ip_port TEXT) 
    """
    cursor.execute(create_table_command)



    #Adding genesis block to the chain in the begining:
    insert_values_into_table("0x0000", "0x9e1c", "1020100300", "0", "0.0.0.0:8888")



    if len(final_peer_object_list) == 0:
        return
    
    blocks_to_fetch_from_peer = final_peer_object_list[random.randint(0,len(final_peer_object_list) - 1)]

    try:
        client_socket=socket.socket()
        client_socket.connect((blocks_to_fetch_from_peer.ip,blocks_to_fetch_from_peer.port))
        client_socket.send(bytes("Blocks fetch", "utf-8"))
        #print("Blocks fetch:"+str(blocks_to_fetch_from_peer.ip)+" : "+str(blocks_to_fetch_from_peer.port))
        client_socket_response=str(client_socket.recv(1024).decode("utf-8"))
        if "Sending blocks" in client_socket_response:
            client_socket.send(bytes("OK", "utf-8"))
            client_socket_response=str(client_socket.recv(1024).decode("utf-8"))   # This response will contain the (genesis+1)th block
            received_blocks_list=[]
            
            while "End Blockchain" not in client_socket_response:
                received_blocks_list.append(client_socket_response)
                client_socket.send(bytes("Block OK", "utf-8"))
                client_socket_response=str(client_socket.recv(1024).decode("utf-8"))
            
            
            client_socket.close()
            
            # received_blocks_list   will have (genesis+1)th block at index 0 and last block in main blockchain at (len(received_blocks_list)-1)th index

            while len(received_blocks_list):
                block=received_blocks_list.pop(0)   
                
                # Parse    block= "Block: (prev_hash, time_stamp, height, IP:PORT, my_hash)" and extract values from tuple   --- Sagar
                parameters_list = block.split(': ')[1].strip('()').split(',')
                #print(parameters_list)
                prev_hash= parameters_list[0].strip(" '")
                my_hash=parameters_list[1].strip(" '")
                time_stamp= parameters_list[2].strip(" '")  # Maybe int or str in the DB. Confirm from Vipin, how is he storing the height i.e. string or as integer in DB, (if string I'll just cast.)
                height= parameters_list[3].strip(" '")
                ip_port=parameters_list[4].strip(" '")


                insert_values_into_table(prev_hash, my_hash, time_stamp, height, ip_port)
                last_block_hash_pointer=my_hash
                last_block_hash_pointer_height=int(height)
            
            print_db()

                
    except socket.error as msg:
        print("fetch_entire_blockchain(): "+ str(msg))

def calculate_new_waiting_time():
    """Calculates New Waiting Time to generate the block

    Returns:
        New Waiting Time
    """
    global inter_arrival_time
    global node_hash_power

    global_lamda = 1/inter_arrival_time
    expo_lamda = node_hash_power * (global_lamda/100)
    waiting_time =  np.random.exponential()/expo_lamda   # Will update it after finding the function
    print("New Waiting Time:"+str(waiting_time))
    return waiting_time


block_forward_list = []     #list contain hash of forwarded block.

def block_forward_protocol(message):
    """This Function check and forward the block to all connected peers
    """
    message_hash = get_hash(message)
    if message_hash not in block_forward_list:
        block_forward_list.append(message_hash)
        if(len(final_peer_object_list) == 0):
            connecting_to_seeds_and_union_list()
        for peer in final_peer_object_list:
            try:
                client_socket = socket.socket()
                client_socket.connect((peer.ip, peer.port))
                client_socket.send(bytes(message, "utf-8"))
                client_socket_response = str(client_socket.recv(1024).decode("utf-8"))
                #print(client_socket_response)
                client_socket.close()
            except socket.error as msg:
                print("block_forward_protocol(): " + str(msg))


def pending_blocks_validator_and_miner():
    """This function validates pending blocks and mine blocks
    """
    global thread_run
    global pending_blocks_list
    global last_block_hash_pointer
    global last_block_hash_pointer_height

    merkel_root = "0xffff"

   # print("\n\nlast_block_hash_pointer"+str(last_block_hash_pointer)+"\n\n")
   # print("\n\last_block_hash_pointer_height"+str(last_block_hash_pointer_height)+"\n\n")


    total_waiting_time = calendar.timegm(time.gmtime()) + calculate_new_waiting_time()

    while thread_run:
        
        current_time=calendar.timegm(time.gmtime())
        if (current_time > total_waiting_time and len(pending_blocks_list)==0):
            
            new_block = last_block_hash_pointer + ";" + str(current_time) + ";" + merkel_root + ";" + str(myip) + ":" + str(port)
            hash_value = get_hash(new_block)
            my_hash="0x"+str(hash_value)[60:]

            
            # Inserting new block into the table
            insert_values_into_table(last_block_hash_pointer, my_hash, current_time, last_block_hash_pointer_height+1, str(str(myip) + ":" + str(port)))
            
            print("\n\nNew block generated :"+last_block_hash_pointer +" "+ my_hash +" "+ str(current_time) +" "+ str(last_block_hash_pointer_height+1) +" "+ str(str(myip) + ":" + str(port)))
            print_db()
            # Updating the last_block_hash_pointer and last_block_hash_pointer_height values to new generated block
            last_block_hash_pointer_height+=1
            last_block_hash_pointer = my_hash

            #reset the timer to new value
            total_waiting_time = calendar.timegm(time.gmtime()) + calculate_new_waiting_time()

            # Forward the new block to the connected peers
            new_block = "Blocks Fwd: "+new_block
            fwd_block_thread=threading.Thread(target=block_forward_protocol, args=(new_block,))
            fwd_block_thread.daemon=True
            fwd_block_thread.start()

            #print("New block Forwad :"+str(new_block))


        elif len(pending_blocks_list):

            reset_timer_flag = False

            for block in pending_blocks_list:

                # print("\n\n\nHash oustide validation:"+get_hash(block)+"\n\n\n")

                if get_hash(block) not in block_forward_list:

                    #Parse the block, extract values of the block and assign it to the respective variables below 
                    # Block Format in pending_blocks_list ---> "Blocks Fwd: prev_hash;time_stamp;fwd_merkelroot;ip:port"

                    # print("Block :"+str(block))
                    parameters_list = block.split(': ')[1].split(';')
                    prev_hash= parameters_list[0].strip()
                    time_stamp= int(parameters_list[1].strip()) #we need to cast this time stamp in future
                    fwd_merkelroot= parameters_list[2].strip()
                    ip_port= parameters_list[3].strip()   # Trim the string while parsing to remove whitespaces if any at the end
                    
                    # print("Received block :"+prev_hash +"#"+ str(time_stamp) +"#"+ fwd_merkelroot +"#"+ ip_port)
                    
                    if fwd_merkelroot == "0xffff":  # Validation of Merkel Root. For adversary sending invalid blocks, will have merkel root as 0x1111

                        # Query to Fetch the block tuple from table where (coloumn)my_hash = prev_hash 
                        block_tuple=None
                        block_tuple = fetch_block_from_table(prev_hash)
                        
                        if block_tuple !=None:         # Validation of block that it points to some geniune previous block
                            curr_time_max_limit = calendar.timegm(time.gmtime()) + 3600  # 1 hour ahead of current time
                            curr_time_min_limit = calendar.timegm(time.gmtime()) - 3600  # 1 hour behind of current time

                            if (time_stamp >= curr_time_min_limit and time_stamp <= curr_time_max_limit):  # Time validation

                                fwd_block = prev_hash + ";" + str(time_stamp) + ";" + fwd_merkelroot + ";" + ip_port
                                hash_value = get_hash(fwd_block)
                               
                                my_hash="0x"+str(hash_value)[60:]

                                #Parse the tuple and extract the height from the tuple and store it in prev_block_height
                                table_prev_block_height = int(block_tuple[3]) # This height we got from the table
                                # Inserting  block into the table
                                insert_values_into_table(prev_hash, my_hash, time_stamp, table_prev_block_height+1, ip_port)

                                print("\n\nReceived block Valid block :"+prev_hash +" "+ my_hash +" "+ str(time_stamp) +" "+ str(table_prev_block_height+1) +" "+ ip_port)
                                print_db()

                                if(table_prev_block_height == last_block_hash_pointer_height):
                                    # print("Height and block pointer updating")
                                    reset_timer_flag = True   # Block creates a chain longer than the longest chain currently
                                    last_block_hash_pointer = my_hash
                                    last_block_hash_pointer_height +=1
                                

                                # Forward the new block to the connected peers
                                fwd_block = "Blocks Fwd: "+fwd_block
                                #print("\n\n\nHash inside validation:"+get_hash(fwd_block)+"\n\n\n")
                                
                                fwd_block_thread=threading.Thread(target=block_forward_protocol, args=(fwd_block,))
                                fwd_block_thread.daemon=True
                                fwd_block_thread.start()

                                #print("Valid block Forward :"+str(fwd_block))
                    else:
                        print("Flooding attack")

                #print("\n\n\n Before block deletion"+ str(pending_blocks_list))
                pending_blocks_list.remove(block) # Removes the block from the pending_blocks_list once processed
                #print("\n\n\n After block deletion"+ str(pending_blocks_list))

            # This means blocks added created a longer chain than the longest chain currently and pending queue is empty, reset the timer for next block waiting time.
            if(reset_timer_flag): 
                # print("Timer reseted")
                total_waiting_time = calendar.timegm(time.gmtime()) + calculate_new_waiting_time()
    

        time.sleep(1)  #Thread sleep for 1 sec


def _severity():
    """Calculates Severity

    Returns:
        float: Severity
    """
    main_chain = fetch_all_blocks_from_DB()
    count = 0
    for block_tuple in main_chain:
        if str(myip)+':'+str(port) == block_tuple[4]:
            count = count + 1
    calculated_severity = count / len(main_chain)
    return calculated_severity


def mining_power_utilization():
    """ To calculate mining power utilization

    Returns:
        float: MPU
    """
    main_chain = fetch_all_blocks_from_DB()
    length_main_chain = len(main_chain) + 1      # +1 is for genesis block.

    cursor.execute('SELECT COUNT(*) FROM BLOCKCHAIN')
    length_total_blockchain_including_fork  = cursor.fetchone()[0]

    mpu = (length_main_chain)/length_total_blockchain_including_fork 
    return mpu


# Cleaning / Ceating all the output files
clear_out_files()

# This is the first task to be executed. After this final_peer_object_list is loaded with peer objects that are connected to this peer.
connecting_to_seeds_and_union_list()

if myip != '':

    # Custom shell Thread
    t1= threading.Thread(target=start_shell)
    t1.daemon=True
    t1.start()


    # Peer Listening Thread
    t2=threading.Thread(target=listening_connections)
    t2.daemon=True
    t2.start()
    
    
    print("Fetching entire Blockchain")
    fetch_entire_blockchain()
    print("Entire Blockchain fetched...Starting with mining thread")


    # mining_thread  starting after fetch_entire_blockchain() so that DB gets filed with the entire blockchain before parsing blocks from the pending_blocks_list[]
    mining_thread=threading.Thread(target=pending_blocks_validator_and_miner)
    mining_thread.daemon=True
    mining_thread.start()

    print("Started mining thread")

    # Liveness Thread
    t3=threading.Thread(target=liveliness_protocol)
    t3.daemon=True
    t3.start()


    mining_thread.join()
    t3.join()
    t1.join()
    t2.join()

else:
    print("No seed available to connect\nExiting...")




