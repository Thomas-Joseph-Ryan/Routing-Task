import sys
import socket

# Dictionary to map node ids to ports
node_ports = {chr(65 + i): 6000 + i for i in range(10)}

def load_config_file(file_path):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    num_neighbors = int(lines[0].strip())
    neighbors = {}

    for line in lines[1:]:
        node, cost, port = line.strip().split()
        neighbors[node] = (float(cost), int(port))

    return neighbors

def display_available_paths(neighbors):
    print("Available paths:")
    for node, (cost, _) in neighbors.items():
        print(f"{node}: {cost}")

def update_config_file(file_path, node_id, new_cost):
    with open(file_path, 'r') as file:
        lines = file.readlines()

    num_neighbors = int(lines[0].strip())

    with open(file_path, 'w') as file:
        file.write(f"{num_neighbors}\n")
        for line in lines[1:]:
            node, cost, port = line.strip().split()
            if node == node_id:
                file.write(f"{node} {new_cost} {port}\n")
            else:
                file.write(line)

def send_update_message(node_id, target_node_id):
    target_port = node_ports[node_id]
    message = f"update"

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.connect(('localhost', target_port))
            sock.sendall(message.encode())
        print(f"Sent update message to node {node_id}.")
    except ConnectionRefusedError:
        print(f"Node {node_id} is not currently online.")

def main():
    if len(sys.argv) != 3:
        print("Usage: python update_path_cost.py <path_to_config_file> <node_id>")
        sys.exit(1)

    config_file_path = sys.argv[1]
    node_id = sys.argv[2]

    neighbors = load_config_file(config_file_path)

    display_available_paths(neighbors)
   
    node_choice = input("What node would you like to update that is listed above? ").strip().upper()

    if node_choice not in neighbors:
        print(f"Node {node_choice} is not in the config file.")
        sys.exit(1)

    other_config_file_path = input(f"Enter the file path for the config file of node {node_choice}: ")

    new_cost = float(input(f"Enter new path cost for node {node_id} <-> {node_choice}: "))

    update_config_file(config_file_path, node_choice, new_cost)
    update_config_file(other_config_file_path, node_id, new_cost)

    # send_update_message(node_id, node_choice)
    # send_update_message(node_choice, node_id)

if __name__ == "__main__":
    main()
