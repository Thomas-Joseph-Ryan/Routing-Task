
class edge:
    """
        node_ids: a tuple of the 2 nodes this edge connects
        cost: the cost of going along this edge
    """
    def __init__(self, nodes : tuple[str, str], cost : float) -> None:
        self.nodes = nodes
        self.cost = cost
        self.sequence_number = 1

    def change_cost(self, cost : float):
        self.cost = cost

    def inc_sequence_number(self):
        self.sequence_number += 1

    def node_involved(self, node : str):
        if (node in self.nodes):
            return True
        else:
            return False
        
    def same_edge(self, edge : 'edge'):
        if self.node_involved(edge.nodes[0]) and self.node_involved(edge.nodes[1]):
            return True
        return False

    def edge_priority(edge1 : 'edge', edge2 : 'edge'):
        """
            If edge sequence numbers are equal, lowest cost edge returned.
            otherwise highest sequence number edge is returned.
        """

        if edge1.sequence_number == edge2.sequence_number:
            if edge1.cost <= edge2.cost:
                return edge1
            else:
                return edge2

        if edge1.sequence_number > edge2.sequence_number:
            return edge1
        else:
            return edge2
        
    def to_dict(self):
        ret = {}
        ret["cost"] = self.cost
        ret["nodes"] = self.nodes
        return ret