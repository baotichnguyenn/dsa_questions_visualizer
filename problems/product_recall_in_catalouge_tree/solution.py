from typing import Tuple

class TreeNode:
    """Represents a node in the catalogue tree."""
    def __init__(self, label, is_leaf=False, is_recalled=False):
        self.label = label
        self.is_leaf = is_leaf
        self.is_recalled = is_recalled  # only meaningful for leaf nodes
        self.children = []

    def add_child(self, child):
        self.children.append(child)


def find_recall_node(root: TreeNode) -> Tuple[str, int]:
    """
    Find the valid recall node of maximum depth.

    A valid recall node's subtree contains ALL recalled products in the tree.
    Among all valid nodes, return the one with maximum depth.
    Also return the count of safe (non-recalled) leaf products in that subtree.

    Args:
        root: TreeNode representing the root of the catalogue tree

    Returns:
        Tuple[str, int]: (node_label, safe_product_count)
        where node_label is the label of the maximum-depth valid recall node
        and safe_product_count is the number of safe leaves in its subtree

    Time Complexity: O(n) where n is the number of nodes
    Space Complexity: O(h) where h is the height (recursion stack)
    """



    pass
