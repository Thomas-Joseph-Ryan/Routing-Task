# Routing-Task

## Before starting the program
Ensure that you have these files and directories in one directory
### files
    - COMP3221_A1_Routing.py
    - edge.py
    - graph.py
    - update_path_cost.py
### directories
    - IUPs (can be empty)
    - logs (can be empty)

You will also need to ensure that the config files are reachable by the program by the path you specify

## To run the program, use the run command as specified in the specs:
python COMP3221_A1_Routing.py Node-ID Port-NO Node-Config-File

## What to expect From program
After 60 seconds, each node will print out the path cost to every other ONLINE node in the network.

For a node to be online, it must be reachable on the port specified in the config files, thus it must be an active
process.

In order to do this, you must run the COMP3221_A1_Routing.py program for each node on a unique terminal.

When a path cost changes, or a node disconnects, you must give the program time to let this change propegate through the network.
Since broadcasts only occur once every 10 seconds, this means it can take quite a while for nodes to be updated, just give the program
time and it will print out the updated path costs and relevent connections. 

## How to change path costs
In order to change pathcosts, run the update_path_cost.py program
Usage: python update_path_cost.py path_to_config_file node_id

node_id is the node that you would like to change a path cost from, and path to config file is the path to that respective nodes config file.

You will then select the edge cost you would like to change by selecting the other node involved in this edge.

You then need to provide the path to the config file of that respective node.

After this, the program will prompt you to provide the new cost of this path, which will be reflected either the next time you run that node, 
or if that node is currently running.

## How to disconnect a node
Simply press ctrl+c or the mac equivalent of sending the SIG_INT signal to the process, this will end the process making it unreachable by other nodes
thus making it offline.
