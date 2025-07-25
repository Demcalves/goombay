from io import StringIO
from Bio import Phylo


class NeighborJoining:
    def __init__(self, dist_matrix):
        self.dist_matrix = dist_matrix

    # // distance calculation stuff for NJ
    # returns a list of total distances for forming Distance Matrix Prime
    def _total_row_distances(self):
        n = len(self.dist_matrix)
        total_distances = []
        for i in range(n):
            total_sum = 0
            for j in range(n):
                total_sum += self.dist_matrix[i][j]
            total_distances.append(total_sum)
        return total_distances

    # adjustedDistanceFollows a different calculation instead
    def _adjusted_distance(self, divergences):
        adj_matrix = []
        mat_len = len(self.dist_matrix)
        for i in range(mat_len):
            node_row = []
            adj_matrix.append(node_row)
            for j in range(mat_len):
                if j == i:
                    node_row.append(0)
                else:
                    dIJ = self.dist_matrix[i][j]
                    dIJ_prime = ((mat_len - 2) * dIJ) - (
                        divergences[i] + divergences[j]
                    )
                    node_row.append(dIJ_prime)
        return adj_matrix

    def _pair_distance(self, nodeI, nodeJ):
        # return new calculated distances
        stored_values = []
        mat_len = len(self.dist_matrix)
        for k in range(mat_len):
            if k != nodeI and k != nodeJ:
                # dMI/dMJ
                dM = (
                    self.dist_matrix[nodeI][k]
                    + self.dist_matrix[nodeJ][k]
                    - self.dist_matrix[nodeI][nodeJ]
                ) / 2
                stored_values.append(dM)

        return stored_values

    # limb length is calculated slightly difference by taking the delta between
    # nodes A and B into consideration instead of divergences
    # calculate limb lengths for each leaf that is joined
    # return a tuple containing two values for each distance
    def _limb_length(self, nodeA, nodeB, divergences):
        n = len(self.dist_matrix)
        dAB = self.dist_matrix[nodeA][nodeB]
        divergenceA = divergences[nodeA]
        divergenceB = divergences[nodeB]
        deltaAB = (divergenceA - divergenceB) / (n - 2)
        # limb lengths
        dAZ = (dAB + deltaAB) / 2
        dBZ = (dAB - deltaAB) / 2

        return dAZ, dBZ

        # // Cluster NJ Stuff

    def _to_newick(self, tree):
        def recurse(node):
            if isinstance(tree[node], dict):
                children = []
                for child, dist in tree[node].items():
                    if child in tree:
                        children.append(f"{recurse(child)}:{dist}")
                    else:
                        children.append(f"{child}:{dist}")
                return f"({','.join(children)})"
            return node

        # Get the topmost node (root)
        root = list(tree.keys())[-1]
        return recurse(root) + ";"

    def _cluster_NJ(self, tree, nodes):
        mat_len = len(self.dist_matrix)
        if mat_len == 2:
            return self.dist_matrix, tree, nodes
        divergences = self._total_row_distances()
        adj_distance_matrix = self._adjusted_distance(divergences)
        min_val = float("inf")
        min_i, min_j = 0, 0
        # Find the pair with the minimum adjusted distance
        for i in range(mat_len):
            for j in range(mat_len):
                if i != j:
                    val = adj_distance_matrix[i][j]
                    if val < min_val:
                        min_val = val
                        min_i = i
                        min_j = j
        # Calculate limb lengths for the new node
        new_limbs = self._limb_length(min_i, min_j, divergences)
        new_limb_MI, new_limb_MJ = new_limbs[0], new_limbs[1]
        # Create new node label
        new_node = f"({nodes[min_j]}<>{nodes[min_i]})"
        # Add new node to tree
        tree[new_node] = {
            nodes[min_i]: new_limb_MI,
            nodes[min_j]: new_limb_MJ,
        }
        # Remove merged nodes and add new node
        nodes_to_remove = [nodes[min_i], nodes[min_j]]
        new_nodes = [n for n in nodes if n not in nodes_to_remove]
        new_nodes.append(new_node)
        # Calculate new distances for the new node to remaining nodes
        new_node_distances = self._pair_distance(min_i, min_j)
        # Build new distance matrix
        new_mat_len = mat_len - 1
        new_distance_matrix = [
            [0.0 for _ in range(new_mat_len)] for _ in range(new_mat_len)
        ]
        # Fill in the new distance matrix
        idx = 0
        for i in range(mat_len):
            if i == min_i or i == min_j:
                continue
            jdx = 0
            for j in range(mat_len):
                if j == min_i or j == min_j:
                    continue
                new_distance_matrix[idx][jdx] = self.dist_matrix[i][j]
                jdx += 1
            idx += 1
        # Add distances for the new node
        for i in range(new_mat_len - 1):
            dist = new_node_distances[i]
            new_distance_matrix[i][new_mat_len - 1] = dist
            new_distance_matrix[new_mat_len - 1][i] = dist
        # Recursively cluster
        self.dist_matrix = new_distance_matrix
        return self._cluster_NJ(tree, new_nodes)

    # place holder NJ algorithm formatting to Newick
    def generate_newick(self):
        # distance matrix and n x n dimensions, respectfully
        dist_matrix = self.dist_matrix
        tree = {}
        nj_nodes = [str(i) for i in range(len(dist_matrix))]
        while len(dist_matrix) != 2:
            dist_matrix, tree, nj_nodes = self._cluster_NJ(tree, nj_nodes)
            # merge remaining nodes in 2x2
        # perform merge on final 2 nodes
        node_a, node_b = nj_nodes[0], nj_nodes[1]
        dist = dist_matrix[0][1]
        limb_length = dist / 2

        # Make sure internal node is formatted correctly
        last_key = f"{node_a}<>{node_b}"
        tree[last_key] = {node_a: limb_length, node_b: limb_length}
        # clean up tree so nodes reflect <> notation
        final_tree = {}
        for key in tree:
            if key[0] == "[":
                final_tree[key[1 : len(key) - 1]] = tree[key]
            else:
                final_tree[key] = tree[key]
        return self._to_newick(final_tree)


# takes a matrix from a clustering algorithm and outputs a newick tree, can also parse newicks?
class NewickFormatter:
    def __init__(self, dist_matrix):
        self.dist_matrix = dist_matrix

    # in order for parse to work there needs to have been a tree object that is inserted into the class
    def parse_newick(self, newick):
        """takes a newick string and converts it into a simple binary tree with Biopythons phylo module"""
        tree = Phylo.read(StringIO(newick), "newick")
        return tree

        # place holder NJ algorithm formatting to Newick

    def generate_newick(self):
        # distance matrix and n x n dimensions, respectfully
        # dist_matrix = self.matrix
        tree = {}
        nj_nodes = [str(i) for i in range(len(self.dist_matrix))]
        while len(self.dist_matrix) != 2:
            self.dist_matrix, tree, nj_nodes = NeighborJoining._cluster_NJ(
                tree, nj_nodes
            )
            # merge remaining nodes in 2x2
        # perform merge on final 2 nodes
        node_a, node_b = nj_nodes[0], nj_nodes[1]
        dist = self.dist_matrix[0][1]
        limb_length = dist / 2

        # Make sure internal node is formatted correctly
        last_key = f"{node_a}<>{node_b}"
        tree[last_key] = {node_a: limb_length, node_b: limb_length}
        # clean up tree so nodes reflect <> notation
        final_tree = {}
        for key in tree:
            if key[0] == "[":
                final_tree[key[1 : len(key) - 1]] = tree[key]
            else:
                final_tree[key] = tree[key]
        return self._to_newick(final_tree)

    def _to_newick(self, tree):
        def recurse(node):
            if isinstance(tree[node], dict):
                children = []
                for child, dist in tree[node].items():
                    if child in tree:
                        children.append(f"{recurse(child)}:{dist}")
                    else:
                        children.append(f"{child}:{dist}")
                return f"({','.join(children)})"
            return node

        # Get the topmost node (root)
        root = list(tree.keys())[-1]
        return recurse(root) + ";"
