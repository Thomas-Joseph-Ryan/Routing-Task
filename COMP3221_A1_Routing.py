import sys
import threading
import socket
import signal
import time

stop_event = threading.Event()

def start():
    if len(sys.argv) != 4:
        print("Usage: python COMP3221_A1_Routing.py <Node-ID> <Port-NO> <Node-Config-File>")
        return
    node_id = sys.argv[1]
    port_no = int(sys.argv[2])
    node_config_file = sys.argv[3]

    # Dictionary to store config values as {letter : {weight: w, port: p}} eg. {"A" : {"weight": 3.1, "port": 6000}} 
    neighbours = {}
    config_information = check_config(node_config_file, neighbours)
    if config_information == False:
        return

    # spawn thread for listen function
    thread = threading.Thread(target=listen, args=(port_no,))
    thread.start()

    print("Main thread is still running...")

    # wait for the thread to finish before continuing
    # thread.join()
    while True:
        time.sleep(2)

    print("Main thread has finished.")


def check_config(filename, neighbours):
    with open(filename, 'r') as file:
        # read the first line and extract the number of nodes
        num_nodes = int(file.readline())
        
        # count the number of nodes listed in the file
        count_nodes = 0
        for line in file:
            if line.strip():  # skip blank lines
                count_nodes += 1
            line = line.rstrip("\n")
            split_config_line = line.split(" ")
            if (len(split_config_line) != 3):
                print("Error: Error in config file node connection line")
                return False
            neighbours[split_config_line[0]] = {"weight" : split_config_line[1], "port" : split_config_line[2]}
        
        # check if the number of nodes in the file matches the number on the first line
        if num_nodes != count_nodes:
            print("Error: Number of nodes in file does not match number on first line.")
            return False;   

    return neighbours
 
def listen(port):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(('localhost', port))
                s.listen()
                print(f"Listening on port {port}...")

                while not stop_event.is_set():  # loop until stop event is set
                    conn, addr = s.accept()
                    with conn:
                        print(f"Connected by {addr}")
                        while True:
                            data = conn.recv(1024)
                            if not data:
                                break
                            print(f"Received data: {data}")

        except Exception as e:
            print(f"Exception in listen: {e}")

        print("Listen thread has finished.")

def quit_gracefully(signum, frame):
    print(f"Received signal {signum}, quitting gracefully...")
    stop_event.set()
    sys.exit(0)

if __name__== "__main__":
    signal.signal(signal.SIGINT, quit_gracefully)
    signal.signal(signal.SIGTERM, quit_gracefully)
    start()
