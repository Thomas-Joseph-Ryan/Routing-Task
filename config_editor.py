import sys
import os
import signal


def start():
    if (len(sys.argv) != 2):
        print("Usage: python config_editor.py <path to config file>")
    neighbours = check_config(sys.argv[1])
    if neighbours == None:
        return
    print("The neighbours to this node ar:e")
    print("node - cost")
    for node in neighbours:
        print(node + " - " + neighbours[node].get("weight"))
    while True:
        node_id = input("Please enter the node id of the edge cost you would like to change: ")
        if neighbours.get(node_id) == None:
            print("Node must exist in this config file.")
            continue
        new_cost = input("Please enter the new cost of the path: ")
        if type(float(new_cost)) != float:
            print("please enter a floating point number")
            continue
        new_cost = float(new_cost)
        if new_cost <= 0:
            print("The new cost must be greater then zero")
            continue

        confirmation = input(f"Confirm: Node {node_id}, New cost {new_cost} (y/n)")
        if confirmation == "y":
            edit_config(sys.argv[1], node_id, new_cost)
            break
        else:
            continue
    print("Config file updated with new value")


def edit_config(filename, node, cost):
    # Open the file for reading
    with open(filename, 'r') as file:
        # Read the contents of the file into a list of lines
        lines = file.readlines()

    # Loop through the lines in the list and modify the line with the specified letter
    for i in range(len(lines)):
        if lines[i].startswith(node):
            parts = lines[i].split()
            parts[1] = str(cost)
            lines[i] = ' '.join(parts) + '\n'

    # Open the file for writing and write the modified data back to it
    with open(filename, 'w') as file:
        file.writelines(lines)


def check_config(filename: str) -> dict:

    # This method checks the config file

    # It ensures the number of nodes in the config file matches the number in the first line.

    # It also ensures that each node has 3 values node_id - weight - and the port number

    # it returns a dictionary of the format ie: The config file has one node B with weight
    # 3.2 and port number 6001
    # {"B" : {"weight" : 3.2, "port" : 6001}}

    neighbours = {}
    try:
        with open(filename, 'r') as file:
            file.readline()

            for line in file:
                
                line = line.rstrip("\n")
                split_config_line = line.split(" ")

                if len(split_config_line) != 3:
                    print("Error: Error in config file node connection line")
                    return {}

                neighbours[split_config_line[0]] = {"weight": split_config_line[1], "port": split_config_line[2]}
    except FileNotFoundError:
        print("Given file does not exist")
        return
    return neighbours

def quit_gracefully(signum, frame) -> None:
    sys.exit(0)


if __name__ == "__main__":
    signal.signal(signal.SIGINT, quit_gracefully)
    signal.signal(signal.SIGTERM, quit_gracefully)
    start()