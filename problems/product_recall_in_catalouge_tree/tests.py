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


def build_single_branch_tree():
    """Linear tree: r -> a -> b -> (leaf1, leaf2)
    Recalls: leaf1 only
    Valid recall nodes: r, a, b
    Max depth valid: b (depth 2)
    Safe in b: 1 (leaf2)
    """
    leaf1 = TreeNode("leaf1", is_leaf=True, is_recalled=True)
    leaf2 = TreeNode("leaf2", is_leaf=True, is_recalled=False)

    b = TreeNode("b")
    b.add_child(leaf1)
    b.add_child(leaf2)

    a = TreeNode("a")
    a.add_child(b)

    r = TreeNode("r")
    r.add_child(a)

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
         a*  b
        /   / \
       c*  d   e
      /   / \
    s1  s2* s3*

    Recalls: a, c, s2, s3
    Valid nodes: r, a
    Max depth valid: a (depth 1)
    Safe in a: 0
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


def build_two_branch_recall_tree():
    """Two separate branches with recalls.
          r
         / \
        a*  b*
       /     \
      s1     s2*

    Recalls: a, b, s2
    Valid: r only (needs to contain all: a, b, s2)
    Max depth valid: r (depth 0)
    Safe: 1 (s1)
    """
    s1 = TreeNode("s1", is_leaf=True, is_recalled=False)
    a = TreeNode("a")
    a.add_child(s1)

    s2 = TreeNode("s2", is_leaf=True, is_recalled=True)
    b = TreeNode("b")
    b.add_child(s2)

    r = TreeNode("r")
    r.add_child(a)
    r.add_child(b)

    return r


TEST_CASES = [
    case(
        "Example from problem - two recalls in separate branches of same parent",
        expected=("a", 2),
        events=build_example_tree(),
    ),

    case(
        "Single linear branch with one recall",
        expected=("b", 1),
        events=build_single_branch_tree(),
    ),

    case(
        "Multiple recalls spread across subtrees - valid only at root",
        expected=("r", 0),
        events=build_deep_recall_tree(),
    ),

    case(
        "All recalls localized to one deep subtree",
        expected=("a", 0),
        events=build_localized_recall_tree(),
    ),

    case(
        "Recalls on sibling branches force root as valid node",
        expected=("r", 1),
        events=build_two_branch_recall_tree(),
    ),

    case(
        "Two recalls at leaves of same parent",
        expected=("a", 0),
        events=lambda: (
            r := TreeNode("r"),
            a := TreeNode("a"),
            r.add_child(a) or None,
            a.add_child(TreeNode("x", is_leaf=True, is_recalled=True)) or None,
            a.add_child(TreeNode("y", is_leaf=True, is_recalled=True)) or None,
            r
        )[-1],
    ),

    case(
        "Large tree - recalls deep but in one branch",
        expected=("b", 0),
        events=lambda: (
            leaf1 := TreeNode("leaf1", is_leaf=True, is_recalled=True),
            leaf2 := TreeNode("leaf2", is_leaf=True, is_recalled=True),
            d := TreeNode("d"),
            d.add_child(leaf1) or None,
            d.add_child(leaf2) or None,
            c := TreeNode("c"),
            c.add_child(d) or None,
            b := TreeNode("b"),
            b.add_child(c) or None,
            a := TreeNode("a"),
            a.add_child(TreeNode("safe", is_leaf=True, is_recalled=False)) or None,
            r := TreeNode("r"),
            r.add_child(a) or None,
            r.add_child(b) or None,
            r
        )[-1],
    ),
]
