from edge import edge

class graph:
    @staticmethod
    def construct_graph(edges: list[edge]) -> dict:
        graph_dict = {}
        for e in edges:
            if e.nodes[0] not in graph_dict:
                graph_dict[e.nodes[0]] = []
            if e.nodes[1] not in graph_dict:
                graph_dict[e.nodes[1]] = []
            graph_dict[e.nodes[0]].append((e.nodes[1], e.cost))
            graph_dict[e.nodes[1]].append((e.nodes[0], e.cost))
        return graph_dict
