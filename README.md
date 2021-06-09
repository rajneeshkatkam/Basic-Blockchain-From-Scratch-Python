# CS765 Blockchain : Assignment - II

* Team Members:

|     Name             |
|:--------------------:|
|   Sagar Tyagi        |
|   Rajneesh Katkam    |
|   Vipin Mahawar      |

* Disclaimer
    1. Please use different ports for each seed and peer if running on a single system.
    2. If running on a single system make sure that no two peers or seed are running in same directory otherwise Output files will conflict

----------------------------------------------------------------------------------------------------------------------------------------------

* Steps to run the programs
1. To install dependencies run  
    `pip3 install -r requirements.txt`
2.  First run the seeds using following syntax
    `python3 seed.py <port_number>`
    (eg. `python3 seed.py 9999`)

3.  After running required no of seeds (>=1), Create a `config.txt` file which will have seeds information one at each line in following format  
    IP1:PORT1  
    IP2:PORT2  
    eg.  
        192.168.0.100:9999  
        192.168.0.101:9999  

4.  Now run the required number of peers using following command
    `python3 peer.py <port_number>`
    (eg. `python3 peer.py 9998`)

----------------------------------------------------------------------------------------------------------------------------------------------

# Files Information:

* Input Files
    config.txt          -- this file contains the information of seeds seperated by lines (IP:PORT)

* Output Files Created.
    * Every Seed will create the following files in current working directory
        1. outputseed.txt       --contain the information about the peers the seed is connected to.

    * Every Peer will create the following files in current working directory
        1. dead_node_list.txt   --contain the information of dead nodes the peer have.
        2. seed_peer_list.txt   --contains the seed reply (peer list of seed) while connecting to the seed.
        3. Severity.txt  --contains severity after flood attack stopped in the format (no_of_peer;inter_arrival_time;severity)
        4. BLOCKCHAIN_DB.db  --sqlite3 database file in which all blocks are stored
        5. Chain-[timestamp].png --graphical representation of database store when graph command is run

----------------------------------------------------------------------------------------------------------------------------------------------

# Additional Features

* Interactive Shell
Both Seed and Peer have a interactive shell which will be invocked automatically when executed.
Below are commands supported by these shells:  
    list : Lists all the connected peers   <br>
    db : Prints the snapshot of db on terminal<br>
    chain : Prints the longest chain  <br>
    graph : Displays the current snapshot and saves in PNG  <br>
    severity : Calculates and prints severity at that time  <br>
    flood start [int:no_of_nodes] : Starts Flood Attack on given no_of_nodes  <br>
    flood stop : Stops flood attack and prints and save severity in Severity.txt  <br>
    time [int:New_time] : Changes Interarrival Time to New_time  <br>
    power [int:New_Power] : Changes Power to New_Power  <br>
    help : Prints this help text  <br>
    exit : Safely Exits the node by reaping all threads  <br>


----------------------------------------------------------------------------------------------------------------------------------------------
# Description of Code

1. Peer  
    This is the structure which holds a peer details
2. clear_out_files():  
    Clears all the output files
3. create_socket():  
    This Function Will Create and initialize socket with certain parameters
4. bind_socket():  
    binding the socket
5. accepting_connections():  
    This is a function for a Thread which will run for the entire life or program and accept connections on the provided port.
    Then it'll also process according to the received response.
6. connecting_to_seeds_and_union_list():  
    This function will first read the config.txt file and select floor(n/2) + 1 seeds.
    Then try to connect with them and make a union of provided peers list from those seeds.
    It'll also print terminal if a seed in config is down.
7. create_union_peer_object_list(union_set_peers):  
        This Function will just return Peer Objects (Class) from provided list of peers in IP:PORT format
8. creating_final_peer_object_list(union_peer_object_list):  
        This function will try to establish connection with a selected peers from the union peer object list.
        If a peer deny to connect (Already connected with 4 peers) then it'll simply skip that peer and try with the next peer.
        And return the final coonected peers object list of atmost 4.
9. get_hash(msg):  
        This function will take a string msg as parameter and return it's hexdigested SHA256 hash
10. liveliness_protocol():  
        This function will be run by an independent thread which will send and process liveness requests.
11. delete_node_request_to_seeds(peer):  
        This function will broadcast this peer as dead to all the connected seeds
12. flooding_protocol(peer_nos):  
        This function will be run by an independent thread which will flood the connected peers.
13. flood_thread(peer):  
        Flood the peer given as argument
14. listening_connections():  
        This function will start accepting connections
15. print_db():  
        This function prints the whole DB of BLOCKCHAIN as a PrettyTable
16. print_chain():  
        Prints the longest chain as a PrettyTable    
17. whole_db():  
        To Fetch all the blocks/records from table BLOCKCHAIN
    Returns:   
        List of Tuples: List of all the records/blocks in the form of Tuple
18. make_graph():  
        This Function Creates a Directed Hierarchical Graph of all the blocks including forks. Apart from showing the output it also saves the graph as a PNG file.
        This Function Should be run as an independent thread as it take some time to complete
19. shell_help():  
    returns Commands Supported by shell as help text
20. start_shell():  
    Custom Shell with some functionalities.  
    Supported Commands Are: <br>
        list : Lists all the connected peers   <br>
        db : Prints the snapshot of db on terminal<br>
        chain : Prints the longest chain  <br>
        graph : Displays the current snapshot and saves in PNG  <br>
        severity : Calculates and prints severity at that time  <br>
        flood start [int:no_of_nodes] : Starts Flood Attack on given no_of_nodes  <br>
        flood stop : Stops flood attack and prints and save severity in Severity.txt  <br>
        time [int:New_time] : Changes Interarrival Time to New_time  <br>
        power [int:New_Power] : Changes Power to New_Power  <br>
        help : Prints this help text  <br>
        exit : Safely Exits the node by reaping all threads  <br>
21. list_connections():  
    This function will print all the connected peers on terminal.
22. insert_values_into_table(prev_block_hash, block_hash, timestamp, blockchain_height, ip_port):  
    This function will insert the values into the Table
    Args:
        prev_block_hash (String): Previous Block Hash
        block_hash (String): Current Block Hash
        timestamp ([String]): Timestamp for block
        blockchain_height (int): Height of block in blockchain
        ip_port (String): IP:PORT of peer which generated the block
23. fetch_block_from_table(my_hash_value):  
    Fetches block from table corresponding to my_hash coloumn value
    Args:
        my_hash_value (String): Hash of the block to fetch from DB
    Returns:   
        tuple: Tuple of Block
24. fetch_all_blocks_from_DB():  
    Fetches longest chain from DB
    Returns:   
        Blocks list will have (genesis+1)th block at index 0 and last block in main blockchain at (len(blocks)-1)th index
        List: List of all the blocks in the form of tuple    
25. entire_blockchain_fwd_to_peer(conn):  
    Forwards the longest chain to the peer
    Args:
        conn (Sockets Connection): Connection Object of the destination peer
26. fetch_entire_blockchain():  
    To Fetch and insert the whole chain from connected peers
27. calculate_new_waiting_time():  
    Calculates New Waiting Time to generate the block
    Returns:   
        New Waiting Time
28. block_forward_protocol(message):  
    This Function check and forward the block to all connected peers
29. pending_blocks_validator_and_miner():  
    This function validates pending blocks and mine blocks
30. _severity():  
    Calculates Severity
    Returns:   
        float: Severity
31. mining_power_utilization():  
    To calculate mining power utilization
    Returns:   
        float: MPU
