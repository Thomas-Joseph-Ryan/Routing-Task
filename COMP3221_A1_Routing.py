import sys
import threading
import socket
import signal
import time
import json
import logging
import queue
from edge import edge


"""
    CURRENT IDEA:

    Each process should create its own internal graph structure using nodes and edges
    (or potentially just edges)

    It will then share its initial graph structure through json to all neighbours, which
    will construct their own graph until all graph structures converge. (As long as each node
    is within a distance of 5 from eachother, it should be fine)

    Then once the graph structure is created, then run bellman-ford and print the results.

    Edges are probably the best way to do this, as when an edge is updated from any node, that new update
    will be the one taken by all other nodes.

    If there are 2 edges found to be between the same two verticies, the edge with lesser cost will be used
    and the other will be disregarded. UNLESS the edge with a higher cost also has a higher seqence number.
"""

stop_event = threading.Event()

information_update_packet_lock = threading.Lock()

inbound_information = queue.Queue()

edges : list[edge] = []

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')

def start() -> None:
    global node_id
    if len(sys.argv) != 4:
        logging.critical("Usage: python COMP3221_A1_Routing.py <Node-ID> <Port-NO> <Node-Config-File>")
        return

    node_id = sys.argv[1]
    port_no = int(sys.argv[2])
    node_config_file = sys.argv[3]

############## SETTING LOGGER ####################

    # Set so logs go to a file
    file_handler = logging.FileHandler("./logs/" + node_id + ".log", mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    # Disable the StreamHandler that is attached to the root logger by default
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            logger.removeHandler(handler)

############# GETTING INITIAL INFO ##############

# Need to create internal graph
    neighbour_information = check_config(node_config_file)
    if len(neighbour_information) == 0:
        return
    for neighbour in neighbour_information:
        create_edge(neighbour, neighbour_information[neighbour]["weight"])
    create_IUP()

# ################# START THREADS ##################

    listen_thread = threading.Thread(target=listen, args=(port_no,))
    listen_thread.start()

    broadcast_thread = threading.Thread(target=broadcast, args=(node_config_file,))
    broadcast_thread.start()

    process_inbound_thread = threading.Thread(target=watch_queue, args=())
    process_inbound_thread.start()

    while True:
        time.sleep(10)
        # print_paths()
        # stop_event.wait()


def check_config(filename: str) -> dict:

    """
        This method checks the config file

        # It ensures the number of nodes in the config file matches the number in the first line.

        # It also ensures that each node has 3 values node_id - weight - and the port number

        # it returns a dictionary of the format ie: The config file has one node B with weight
        # 3.2 and port number 6001
        # {"B" : {"weight" : 3.2, "port" : 6001}}
    """

    neighbours = {}
    with open(filename, 'r') as file:
        num_nodes = int(file.readline())
        count_nodes = 0

        for line in file:
            if line.strip():  # skip blank lines
                count_nodes += 1
            
            line = line.rstrip("\n")
            split_config_line = line.split(" ")

            if len(split_config_line) != 3:
                logging.error("Error: Error in config file node connection line")
                return {}

            neighbours[split_config_line[0]] = {"weight": split_config_line[1], "port": split_config_line[2]}
        
        if num_nodes != count_nodes:
            logging.error("Error: Number of nodes in file does not match number on first line.")
            return {}

    return neighbours
 
def create_edge(node, cost):
    new_edge = edge((node_id, node), cost)
    edges.append(new_edge)

def create_IUP() -> None:

    """
    This method creates the first information update package for each node

     The information update looks like the dictionary below and is designed
     so that the broadcast method can update the cost from origin for each
     neighbour that it is sending this package too.

     The cost_from_origin represents the weight associated with this node
     and the node this node is sending this package too.

     The origin is the node_id of the sending node

     The node_id: {} represents each row in the routing table for the RIP 
     protocol
    
    """
    
    iup = []
    for edge in edges:
        temp = edge.to_dict()
        iup.append(temp)
    with information_update_packet_lock:
        with open("./IUPs/" + node_id + "-IUP.json", "w") as f:
           f.write(json.dumps(iup))

def update_IUP(destination_node_id : str, direction : str, cost : float) -> None:

    #  Updates the routing table in the information update packet if
    #  There is no record of the destination node id
    #  OR
    #  The new cost of the destination node id is less then the previous cost of
    #  getting to the destination node id


    current_IUP = read_IUP()
    with information_update_packet_lock:
        routing_table : dict = current_IUP.get("routing_table")
        if destination_node_id not in routing_table:
            routing_table[destination_node_id] = {"dir" : direction, "cost" : cost}
        else:
            if routing_table[destination_node_id]["cost"] > cost:
                routing_table[destination_node_id] = {"dir" : direction, "cost" : cost}
            elif routing_table[destination_node_id]["dir"] == direction and routing_table[destination_node_id]["cost"] != cost:
                # Recieving an update from destination node, that the path of the route currently taken has changed
                # Must update this path cost as the cost is now different, on the iteration after this current, the most efficient
                # path will be calculated again.
                routing_table[destination_node_id] = {"dir" : direction, "cost" : cost}
        with open("./IUPs/" + node_id + "-IUP.json", "w") as f:
            f.write(json.dumps(current_IUP))

# def update_IUP(destination_node_id : str, path , cost : float) -> None:
#     current_IUP = read_IUP()
#     with information_update_packet_lock:
#         routing_table : dict = current_IUP.get("routing_table")
#         if destination_node_id not in routing_table:
#             routing_table[destination_node_id] = {"path" : path, "cost" : cost}
#         else:
#             if routing_table[destination_node_id]["cost"] > cost:
#                 routing_table[destination_node_id] = {"path" : path, "cost" : cost}
#             elif routing_table[destination_node_id]["path"] == path and routing_table[destination_node_id]["cost"] != cost:
#                 routing_table[destination_node_id] = {"path" : path, "cost" : cost}
#         with open("./IUPs/" + node_id + "-IUP.json", "w") as f:
#             f.write(json.dumps(current_IUP))



def read_IUP() -> dict :
    # Reads the current information update packet stored for this node.

    # The information update packet is saved in the IUPs directory with the filename
    # node_id-IUP.json where node-id is the id of the node saving this IUP.
    with information_update_packet_lock:
        with open("./IUPs/" + node_id + "-IUP.json", "r") as f:
            return json.loads(f.read())

def listen(port: int) -> None:
    
    # Listens for any incoming broadcasts from other nodes and places the decoded data 
    # into a queue ready for processing by another thread.

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('localhost', port))
            s.listen()
            logging.info(f"Listening on port {port}...")

            while not stop_event.is_set():
                s.settimeout(5)

                try:
                    conn, addr = s.accept()
                except socket.timeout:
                    continue

                with conn:
                    logging.info(f"Connected by {addr}")

                    while True:
                        data = conn.recv(1024)
                        if not data:
                            break
                        
                        data = data.decode('utf-8')
                        logging.debug(f"Received data: {data}")
                        inbound_information.put(data)

    except Exception as e:
        logging.error(f"Exception in listen: {e}")

    logging.info("Listen thread has finished")

def broadcast(node_config_file: str) -> None:

    # Broadcasts the current IUP to each direct neighbour node, with each
    # neighbour recieving a custom value for the "cost_from_origin" key.

    while not stop_event.is_set():
        current_IUP = read_IUP()
        neighbours = check_config(node_config_file)
        for neighbour in neighbours:
            packet = json.dumps(current_IUP).encode("utf-8")
            port = int(neighbours.get(neighbour).get("port"))
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    logging.info("trying to connect to " + neighbour + " on port " + str(port))
                    s.connect(('localhost', port))
                    s.sendall(packet)
            except ConnectionRefusedError:
                logging.error(f"Connection was refused by node {neighbour}")
                # update_IUP(neighbour, neighbour, sys.maxsize)
            except Exception as e:
                logging.error(f"Exception in broadcast: {e}")
        time.sleep(10)

def watch_queue() -> None:
    while not stop_event.is_set():
        try:
            # Inbound dict comes as the other nodes IUP as a string
            inbound_info = inbound_information.get(block=True, timeout=5)
            # Load that string as a json
            inbound_info : list = json.loads(inbound_info)

            for incoming_edge in inbound_info:
                incoming_edge_nodes = incoming_edge.get('nodes')
                incoming_edge_cost = incoming_edge.get('cost')
                incoming_edge = edge((incoming_edge_nodes[0], incoming_edge_nodes[1]), incoming_edge_cost)
                already_exists = False
                for existing_edge in edges:
                    if existing_edge.same_edge(incoming_edge):
                        priority_edge = edge.edge_priority(existing_edge, incoming_edge)
                        if priority_edge == existing_edge:
                            continue
                        
                
            # The first node in the inbound dict will be the node id of the process
            # that sent this data due to the way the IUP is initialised and added to.
            # sender_id = inbound_info.get("origin")
            # cost_from_sender = float(inbound_info.get("cost_from_origin"))
            # for node in inbound_info.get("routing_table"):
            #             node_dict : dict = inbound_info.get("routing_table").get(node)
            #             direction = node_dict.get("dir")
            #             cost = float(node_dict.get("cost"))

            #             if (direction == "local"):
            #                 # This node is a neighbour node, so its direction is itself and its cost is equal
            #                 # to the cost from the sender
            #                 update_IUP(node, sender_id, cost_from_sender)
            #             elif (direction == node):
            #                 # This node is a direct neighbour to the sending node. So its direction is in the 
            #                 # direction of this neighbouring node and its cost is equal to the cost of going to
            #                 # this neighbour, then from this neighbour to it.
            #                 update_IUP(node, sender_id, cost_from_sender + cost)
            #             else:
            #                 # This node is connected to the sending node indirectly (not a neighbour). 
            #                 # So do not change its direction as the sending node has already done this if 
            #                 # necessary
            #                 update_IUP(node, direction, cost_from_sender + cost)
        except queue.Empty:
            continue



def print_paths() -> None:
    # Reads in the IUP
    # Traces back the path taken for each node, and prints out the result for each node

    current_IUP :dict = read_IUP()

    for node in current_IUP.get("routing_table"):
        if (node == node_id):
            print("I am Node " + node)
            continue
        cost = round(current_IUP.get("routing_table").get(node).get("cost"), 1)
        if cost >= sys.maxsize:
            continue
        path = traceback_path(node)
        print(f"Least cost path from {node_id} to {node}: {path}, link cost: {cost}")

def traceback_path(node : str, path : str = '') -> str:
    current_IUP :dict = read_IUP()
    routing_table : dict = current_IUP.get("routing_table")
    direction : str = routing_table.get(node).get("dir")
    if direction == node:
        # This node is a neighbour
        path += node
        path += node_id
        path = reverse_string(path)
        return path
    else:
        path += node
        # print(f"currently getting traceback for node {node}, the direction of this node is {direction}, current path is {path}")
        return traceback_path(direction, path)
        
def reverse_string(string : str) -> str:
    string = string[::-1]
    return string

def quit_gracefully(signum, frame) -> None:
    logging.info(f"Received signal {signum}, quitting gracefully...")
    stop_event.set()
    sys.exit(0)

if __name__== "__main__":
    signal.signal(signal.SIGINT, quit_gracefully)
    signal.signal(signal.SIGTERM, quit_gracefully)
    start()
