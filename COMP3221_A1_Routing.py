import sys
import threading
import socket
import signal
import time
import json
import logging
import queue

stop_event = threading.Event()

information_update_packet_lock = threading.Lock()

inbound_information = queue.Queue()

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
    file_handler = logging.FileHandler(node_id + ".log", mode='w')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger = logging.getLogger()
    logger.addHandler(file_handler)
    # Disable the StreamHandler that is attached to the root logger by default
    for handler in logger.handlers:
        if isinstance(handler, logging.StreamHandler):
            logger.removeHandler(handler)

#################################################

############# GETTING INITIAL INFO ##############

    create_IUP()
    initial_information = check_config(node_config_file)
    neighbours = initial_information.copy()
    if len(initial_information) == 0:
        return
    # for node in initial_information:
    #     update_IUP(node_id, node, initial_information[node].get("weight"))

#################################################

    listen_thread = threading.Thread(target=listen, args=(port_no,))
    listen_thread.start()

    broadcast_thread = threading.Thread(target=broadcast, args=(neighbours,))
    broadcast_thread.start()

    process_inbound_thread = threading.Thread(target=watch_queue, args=())
    process_inbound_thread.start()

    while True:
        time.sleep(10)


def check_config(filename: str) -> dict:

    # This method checks the config file

    # It ensures the number of nodes in the config file matches the number in the first line.

    # It also ensures that each node has 3 values node_id - weight - and the port number

    # it returns a dictionary of the format ie: The config file has one node B with weight
    # 3.2 and port number 6001
    # {"B" : {"weight" : 3.2, "port" : 6001}}

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
 
def create_IUP() -> None:
    #This method creates the first information update package for each node

    # The information update looks like the dictionary below and is designed
    # so that the broadcast method can update the cost from origin for each
    # neighbour that it is sending this package too.

    # The cost_from_origin represents the weight associated with this node
    # and the node this node is sending this package too.

    # The origin is the node_id of the sending node

    # The node_id: {} represents each row in the routing table for the RIP 
    # protocol
    
    IUP_format = {"cost_from_origin": 0, "origin": node_id, "routing_table" : {node_id : {"dir": "local", "cost": 0}}}
    with information_update_packet_lock:
        with open("./IUPs/" + node_id + "-IUP.json", "w") as f:
           f.write(json.dumps(IUP_format))

def update_IUP(updated_node_id : str, direction : str, cost : float) -> None:

    #  Updates the routing table in the information update packet if
    #  There is no record of the updated node id
    #  OR
    #  The new cost of the updated node id is less then the previous cost of
    #  getting to the updated node id


    current_IUP = read_IUP()
    with information_update_packet_lock:
        routing_table : dict = current_IUP.get("routing_table")
        if updated_node_id not in routing_table:
            routing_table[updated_node_id] = {"dir" : direction, "cost" : cost}
        else:
            if routing_table[updated_node_id]["cost"] > cost:
                routing_table[updated_node_id] = {"dir" : direction, "cost" : cost}
        with open("./IUPs/" + node_id + "-IUP.json", "w") as f:
            f.write(json.dumps(current_IUP))

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

def broadcast(neighbours: dict) -> None:

    # Broadcasts the current IUP to each direct neighbour node, with each
    # neighbour recieving a custom value for the "cost_from_origin" key.

    while not stop_event.is_set():
        current_IUP = read_IUP()
        for neighbour in neighbours:
            current_IUP["cost_from_origin"] = neighbours.get(neighbour).get("weight")
            packet = json.dumps(current_IUP).encode("utf-8")
            port = int(neighbours.get(neighbour).get("port"))
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    logging.info("trying to connect to " + neighbour + " on port " + str(port))
                    s.connect(('localhost', port))
                    s.sendall(packet)
            except Exception as e:
                logging.error(f"Exception in broadcast: {e}")
        time.sleep(10)

def watch_queue() -> None:
    while not stop_event.is_set():
        try:
            # Inbound dict comes as the other nodes IUP as a string
            inbound_dict = inbound_information.get(block=True, timeout=5)
            # Load that string as a json
            inbound_dict : dict = json.loads(inbound_dict)
            # The first node in the inbound dict will be the node id of the process
            # that sent this data due to the way the IUP is initialised and added to.
            sender_id = inbound_dict.get("origin")
            cost_from_sender = float(inbound_dict.get("cost_from_origin"))
            for node in inbound_dict.get("routing_table"):
                        node_dict : dict = inbound_dict.get("routing_table").get(node)
                        direction = node_dict.get("dir")
                        cost = float(node_dict.get("cost"))

                        if (direction == "local"):
                            # This node is a neighbour node, so its direction is itself and its cost is equal
                            # to the cost from the sender
                            update_IUP(node, sender_id, cost_from_sender)
                        elif (direction == node):
                            # This node is a direct neighbour to the sending node. So its direction is in the 
                            # direction of this neighbouring node and its cost is equal to the cost of going to
                            # this neighbour, then from this neighbour to it.
                            update_IUP(node, sender_id, cost_from_sender + cost)
                        else:
                            # This node is connected to the sending node indirectly (not a neighbour). 
                            # So do not change its direction as the sending node has already done this if 
                            # necessary
                            update_IUP(node, direction, cost_from_sender + cost)
        except queue.Empty:
            continue

def quit_gracefully(signum, frame) -> None:
    logging.info(f"Received signal {signum}, quitting gracefully...")
    stop_event.set()
    sys.exit(0)

if __name__== "__main__":
    signal.signal(signal.SIGINT, quit_gracefully)
    signal.signal(signal.SIGTERM, quit_gracefully)
    start()
