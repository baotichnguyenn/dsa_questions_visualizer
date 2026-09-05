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


def _count_recalled(node) -> int:
    if node.is_leaf:
        return 1 if node.is_recalled else 0
    return sum(_count_recalled(child) for child in node.children)


def find_best(node, depth, total_recalled):
    # We need to recursively inspect every child first,
    # because a deeper valid candidate may exist below us.

    best_node = None
    best_depth = -1
    best_safe_count = 0

    recalled_count = 0
    safe_count = 0

    if node.is_leaf:
        safe_count = 0 if node.is_recalled else 1
        recalled_count = 1 if node.is_recalled else 0

    else:
        for child in node.children:
            child_recalled, child_safe, child_best, child_depth, child_best_safe = \
                find_best(child, depth + 1, total_recalled)

            recalled_count += child_recalled
            safe_count += child_safe

            # Keep the deepest valid candidate found in our children, along
            # with the safe count *of that candidate's own subtree* - not
            # child_safe, which is the whole child subtree's safe count and
            # only matches when the candidate happens to be the child itself.
            if child_best is not None and child_depth > best_depth:
                best_node = child_best
                best_depth = child_depth
                best_safe_count = child_best_safe

    # Now we know how many recalled products are in THIS subtree.
    # If that equals the global total, this node contains ALL recalls.
    if recalled_count == total_recalled:
        # This node itself is valid.
        #
        # Since we are currently at `depth`, compare it against
        # the best valid node found deeper in the subtree.
        if depth > best_depth:
            best_node = node
            best_depth = depth
            best_safe_count = safe_count

    return recalled_count, safe_count, best_node, best_depth, best_safe_count


def find_recall_node(root: TreeNode) -> Tuple[str, int]:
    total_recalled = _count_recalled(root)
    _, _, best_node, _, best_safe_count = find_best(root, 0, total_recalled)
    return best_node.label, best_safe_count

