"""Test cases for product recall in catalogue tree problem."""
from harness import case
from solution import TreeNode

ENTRY_POINT = "find_recall_node"


def build_example_tree():
    """Build the example tree from the problem statement.

           r
          / \
         a   b
        / \ / \
       c  d z  w
      /| /|
     p*q x*y

    Recalled: p, x
    Expected output: (a, 2)  [a is at depth 1, safe products q and y in its subtree]
    """
    p = TreeNode("p", is_leaf=True, is_recalled=True)
    q = TreeNode("q", is_leaf=True, is_recalled=False)
    x = TreeNode("x", is_leaf=True, is_recalled=True)
    y = TreeNode("y", is_leaf=True, is_recalled=False)
    z = TreeNode("z", is_leaf=True, is_recalled=False)
    w = TreeNode("w", is_leaf=True, is_recalled=False)

    c = TreeNode("c")
    c.add_child(p)
    c.add_child(q)

    d = TreeNode("d")
    d.add_child(x)
    d.add_child(y)

    a = TreeNode("a")
    a.add_child(c)
    a.add_child(d)

    b = TreeNode("b")
    b.add_child(z)
    b.add_child(w)

    r = TreeNode("r")
    r.add_child(a)
    r.add_child(b)

    return r


def build_deep_recall_tree():
    """Deep tree where all recalls are at the deepest level.
           r
          / \
         a   b
        /     \
       c       d
      /       / \
    x1*      x2* x3*

    Recalls: x1, x2, x3
    Valid: r (contains all)
    Max depth valid: r (depth 0)
    Safe in r: 0
    """
    x1 = TreeNode("x1", is_leaf=True, is_recalled=True)
    x2 = TreeNode("x2", is_leaf=True, is_recalled=True)
    x3 = TreeNode("x3", is_leaf=True, is_recalled=True)

    c = TreeNode("c")
    c.add_child(x1)

    d = TreeNode("d")
    d.add_child(x2)
    d.add_child(x3)

    a = TreeNode("a")
    a.add_child(c)

    b = TreeNode("b")
    b.add_child(d)

    r = TreeNode("r")
    r.add_child(a)
    r.add_child(b)

    return r


def build_localized_recall_tree():
    """Recalls all in one deep subtree.
           r
          / \
         a   b
         |  / \
         c d   e
         | /|  |
        s1 s2* s3* s4

    Recalls: s2, s3 - both direct children of d
    Valid nodes: r, b, d
    Max depth valid: d (depth 2)
    Safe in d: 0
    """
    s2 = TreeNode("s2", is_leaf=True, is_recalled=True)
    s3 = TreeNode("s3", is_leaf=True, is_recalled=True)
    d = TreeNode("d")
    d.add_child(s2)
    d.add_child(s3)

    e = TreeNode("e")
    e.add_child(TreeNode("s4", is_leaf=True, is_recalled=False))

    b = TreeNode("b")
    b.add_child(d)
    b.add_child(e)

    s1 = TreeNode("s1", is_leaf=True, is_recalled=False)
    c = TreeNode("c")
    c.add_child(s1)

    a = TreeNode("a")
    a.add_child(c)

    r = TreeNode("r")
    r.add_child(a)
    r.add_child(b)

    return r


def build_same_parent_recall_tree():
    """Two recalls as leaves of the same parent.
          r
          |
          a
         / \
        x*  y*

    Recalls: x, y
    Valid: r, a
    Max depth valid: a (depth 1)
    Safe in a: 0
    """
    r = TreeNode("r")
    a = TreeNode("a")
    r.add_child(a)
    a.add_child(TreeNode("x", is_leaf=True, is_recalled=True))
    a.add_child(TreeNode("y", is_leaf=True, is_recalled=True))
    return r


def build_deep_branch_recall_tree():
    """Both recalls together, deep inside one branch.
          r
         / \
        a   b
        |   |
      safe  c
             |
             d
            / \
        leaf1* leaf2*

    Recalls: leaf1, leaf2 - both direct children of d
    Valid: r, b, c, d
    Max depth valid: d (depth 3)
    Safe in d: 0
    """
    leaf1 = TreeNode("leaf1", is_leaf=True, is_recalled=True)
    leaf2 = TreeNode("leaf2", is_leaf=True, is_recalled=True)
    d = TreeNode("d")
    d.add_child(leaf1)
    d.add_child(leaf2)

    c = TreeNode("c")
    c.add_child(d)

    b = TreeNode("b")
    b.add_child(c)

    a = TreeNode("a")
    a.add_child(TreeNode("safe", is_leaf=True, is_recalled=False))

    r = TreeNode("r")
    r.add_child(a)
    r.add_child(b)

    return r


def _catalogue_tree(n_leaves, branching=8):
    """A b-ary catalogue tree with n_leaves leaves, height O(log n) so this
    stays well clear of Python's recursion limit even at the largest size.
    Recalls exactly two leaves, the first and last generated, so the whole
    tree has to be inspected - no shortcut prunes the recursion early."""
    leaves = []

    def build(count):
        if count <= 1:
            leaf = TreeNode(f"leaf{len(leaves)}", is_leaf=True)
            leaves.append(leaf)
            return leaf
        node = TreeNode(f"node{len(leaves)}")
        base, extra = divmod(count, branching)
        for i in range(branching):
            share = base + (1 if i < extra else 0)
            if share > 0:
                node.add_child(build(share))
        return node

    root = build(n_leaves)
    leaves[0].is_recalled = True
    leaves[-1].is_recalled = True
    return root


# Used only by the complexity measurement on the results window, once every
# testcase passes. Hand it a size, get back a valid catalogue tree of n leaves.
SCALING_SIZES = [2000, 4000, 8000, 16000, 32000]


def scaling_input(n):
    return {"events": _catalogue_tree(n)}


TEST_CASES = [
    case(
        "Example from problem - two recalls in separate branches of same parent",
        expected=("a", 2),
        events=build_example_tree(),
    ),

    case(
        "Multiple recalls spread across subtrees - valid only at root",
        expected=("r", 0),
        events=build_deep_recall_tree(),
    ),

    case(
        "All recalls localized to one deep subtree",
        expected=("d", 0),
        events=build_localized_recall_tree(),
    ),

    case(
        "Two recalls at leaves of same parent",
        expected=("a", 0),
        events=build_same_parent_recall_tree(),
    ),

    case(
        "Large tree - recalls deep but in one branch",
        expected=("d", 0),
        events=build_deep_branch_recall_tree(),
    ),
]
