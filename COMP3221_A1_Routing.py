import sys
import threading
import socket
import signal
import time
import json
import logging
import queue
from edge import edge
from graph import graph

# I created the following program with the help of Chat-GPT for some functions and ideas.
# The bulk of the programming and ideas came from myself, however if any plagerism is detected,
# it is likely that it could be from GPT, however I imagine this would be highly unlikely as
# I changed everything that it gave me and only kept some basic ideas.

stop_event = threading.Event()

information_update_packet_lock = threading.Lock()

inbound_information = queue.Queue()

edges : list[edge] = []

edges_lock = threading.Lock()

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s [%(levelname)s] %(message)s')

update_neighbours = False

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
        create_edge(neighbour, float(neighbour_information[neighbour]["weight"]))
    create_IUP()

# ################# START THREADS ##################

    listen_thread = threading.Thread(target=listen, args=(port_no,))
    listen_thread.start()

    broadcast_thread = threading.Thread(target=broadcast, args=(node_config_file,))
    broadcast_thread.start()

    process_inbound_thread = threading.Thread(target=watch_queue, args=())
    process_inbound_thread.start()

    time.sleep(60)
    previous_info = None
    while True:
        distances, previous = dijkstra(graph.construct_graph(edges), node_id)
        previous_info = print_paths(distances, previous, previous_info)
        time.sleep(10)


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

def create_IUP() -> str:
    
    iup = []
    for edge in edges:
        temp = edge.to_dict()
        iup.append(temp)
    with information_update_packet_lock:
        with open("./IUPs/" + node_id + "-IUP.json", "w") as f:
           f.write(json.dumps(iup))
    return json.dumps(iup)

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

def broadcast(config_file_path) -> None:

    # Broadcasts the current IUP to each direct neighbour node, with each
    # neighbour recieving a custom value for the "cost_from_origin" key.

    while not stop_event.is_set():
        current_IUP = create_IUP()
        neighbour_information = check_config(config_file_path)
        for neighbour in neighbour_information:
            packet = current_IUP.encode("utf-8")
            port = int(neighbour_information.get(neighbour).get("port"))
            cost = float(neighbour_information.get(neighbour).get("weight"))
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    logging.info("trying to connect to " + neighbour + " on port " + str(port))
                    s.connect(('localhost', port))
                    update_node(neighbour, cost)
                    s.sendall(packet)
            except ConnectionRefusedError:
                logging.error(f"Connection was refused by node {neighbour}")
                update_node(neighbour, float('inf'))
            except Exception as e:
                logging.error(f"Exception in broadcast: {e}")
        time.sleep(10)

def watch_queue() -> None:
    while not stop_event.is_set():
        try:
            # Inbound dict comes as the other nodes IUP as a string
            inbound_info = inbound_information.get(block=True, timeout=5)

            # if inbound_info == "update":
            #     update_neighbours = True
            #     continue

            # Load that string as a json
            inbound_info : list = json.loads(inbound_info)

            

            for incoming_edge in inbound_info:
                incoming_edge_nodes = incoming_edge.get('nodes')
                incoming_edge_cost = float(incoming_edge.get('cost'))
                incoming_edge_seq_num = int(incoming_edge.get('sequence_number'))
                incoming_edge = edge((incoming_edge_nodes[0], incoming_edge_nodes[1]), incoming_edge_cost, incoming_edge_seq_num)
                add_incoming_edge = True
                with edges_lock:
                    for existing_edge in edges:
                        if existing_edge.same_edge(incoming_edge):
                            # Looking at edge that already exists in this nodes understanding of edges
                            priority_edge = edge.edge_priority(existing_edge, incoming_edge)
                            if priority_edge == existing_edge:
                                # If the priority edge is already the one that exists we do not need to change anything
                                add_incoming_edge = False
                                continue
                            else:
                                edges.remove(existing_edge)
                    if add_incoming_edge == True:
                        edges.append(incoming_edge)

        except queue.Empty:
            continue

def dijkstra(graph, source):
    # Initialization
    unexplored = set(graph.keys())
    distances = {node: float('inf') for node in graph}
    distances[source] = 0
    previous = {node: None for node in graph}

    while unexplored:
        # Select the unexplored node with the minimum distance
        u = min(unexplored, key=distances.get)
        unexplored.remove(u)

        # Stop if the minimum distance is infinity (i.e., unreachable)
        if distances[u] == float('inf'):
            break

        # Explore the neighbors of the current node
        for v, w in graph[u]:
            w = float(w)
            # Calculate the tentative distance to the neighbor
            tentative_distance = distances[u] + w

            # Update the distance and previous node if the tentative distance is less than the current distance
            if tentative_distance < distances[v]:
                distances[v] = tentative_distance
                previous[v] = u

    return distances, previous

def print_paths(distances, previous, previous_info=None) -> None:
    # Reads in the IUP
    # Traces back the path taken for each node, and prints out the result for each node

    if previous_info is None:
        previous_info = {}

    updated_info = {}
    has_changed = False


     # Sort the nodes in alphabetical order, excluding the starting node
    sorted_nodes = sorted([node for node in distances.keys() if node != node_id])

    for node in sorted_nodes:
        cost = round(distances[node], 1)
        path = get_path(previous, node)

        if (path, cost) != previous_info.get(node):
            has_changed = True
        updated_info[node] = (path, cost)
    
    if has_changed:
        print(f"I am Node {node_id}")
        for node, (path, cost) in updated_info.items():
            if cost >= float('inf'):
                continue
            print(f"Least cost path from {node_id} to {node}: {path}, link cost: {cost}")

    return updated_info

def get_path(previous : dict, target : str):
    path = []
    current = target
    while current is not None:
        path.append(current)
        current = previous[current]
    if path[-1] is not None:
        return "".join(reversed(path))
    else:
        return None
        
def update_node(node : str, cost : float):
    with edges_lock:
        for edge in edges:
            if edge.node_involved(node) and edge.node_involved(node_id):
                edge.change_cost(cost)
                edge.inc_sequence_number()

def quit_gracefully(signum, frame) -> None:
    logging.info(f"Received signal {signum}, quitting gracefully...")
    stop_event.set()
    sys.exit(0)

if __name__== "__main__":
    signal.signal(signal.SIGINT, quit_gracefully)
    signal.signal(signal.SIGTERM, quit_gracefully)
    start()
