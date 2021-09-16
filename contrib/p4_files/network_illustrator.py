import networkx as nx
import matplotlib.pyplot as plt
import os
import json


class NetworkIllustrator(object):
    def __init__(self) -> None:
        self.network_file = None
        self.graph = nx.Graph()
        self.color_mapping = {}

        # Colors
        self.set_colors()

    def load_file(self, path: str):
        """
        Loads the configuration file for drawing

        Args:
            path (str): Path to config file
        """
        if os.path.exists(path):
            self.network_file = path

        with open(path) as f:
            self.network_conf = json.load(f)

    def draw(self, path=""):
        """
        Draws the configuration and plots it. If a path is given, save the image. Otherwise
        just plots the image.
        """
        if len(self.network_conf) != 0:
            links, labels_1, labels_2 = self.__get_link_config()

            self.graph.add_edges_from(links)
            node_sizes = self.get_node_size(500, 1500)

            pos = nx.spring_layout(self.graph, weight="myweight", iterations=150)

            colors = [self.color_mapping[node] for node in self.graph.nodes()]

            nx.draw(
                self.graph,
                pos,
                nodelist=dict(self.graph.nodes).keys(),
                node_size=node_sizes,
                with_labels=True,
                node_color=colors,
            )

            # Draw labels
            nx.draw_networkx_edge_labels(
                self.graph, pos, edge_labels=labels_1, label_pos=0.7
            )
            nx.draw_networkx_edge_labels(
                self.graph, pos, edge_labels=labels_2, label_pos=0.3
            )

        if path:
            plt.savefig(path)
        else:
            plt.show()

    def set_colors(self):
        """
        Update the colors of nodes and switches
        """
        self.node_color = "limegreen"
        self.switch_color = "#00b4d9"

    def get_node_size(self, node_size, switch_size):
        node_sizes = []
        for node in self.graph.nodes:
            if self.color_mapping[node] == self.node_color:
                node_sizes.append(node_size)
            else:
                node_sizes.append(switch_size)
        return node_sizes

    def __get_link_config(self):
        labels_1 = {}
        labels_2 = {}
        links = []
        for link in self.network_conf["links"]:
            dev1_port = link["device1_port"]
            dev2_port = link["device2_port"]

            labels_1[link["device1"], link["device2"]] = f"{dev1_port}"
            labels_2[link["device1"], link["device2"]] = f"{dev2_port}"
            if link["type"] == "Node_to_Switch":
                if not link["device1"] in self.color_mapping:
                    links.append((link["device1"], link["device2"], {"myweight": 10}))

                    self.color_mapping[link["device1"]] = self.node_color
                    self.color_mapping[link["device2"]] = self.switch_color
            elif link["type"] == "Switch_to_Switch":
                self.color_mapping[link["device1"]] = self.switch_color
                self.color_mapping[link["device2"]] = self.switch_color
                links.append((link["device1"], link["device2"], {"myweight": 20}))
            else:
                links.append((link["device1"], link["device2"], {"myweight": 20}))
                self.color_mapping[link["device1"]] = self.node_color
                self.color_mapping[link["device2"]] = self.node_color
        return links, labels_1, labels_2


def main():
    print("Start test")

    ill = NetworkIllustrator()

    ill.load_file("/home/p4/Drawing_Test/4_nodes_3_switch.json")
    ill.draw()


if __name__ == "__main__":
    main()
