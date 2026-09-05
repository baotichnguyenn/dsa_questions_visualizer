Product recall in a catalogue tree 
A retailer organises its products using a rooted catalogue tree T containing n nodes. Every node has a distinct label. 
Each leaf represents one product. Every leaf is marked either safe or recalled. Internal nodes represent product categories and do not have a mark. At least two leaves are recalled. 
Issuing a recall at a node v removes every product represented by a leaf in the subtree rooted at v. 
A node v is a valid recall node if the subtree rooted at v contains every recalled product in the entire catalogue. 
The depth of a node is the number of edges on the path from the root to that node. Among all valid recall nodes, the retailer chooses the node of maximum depth. This keeps the recall within the smallest possible part of the catalogue. 
The algorithm must return an ordered pair (v, s), where 
1. v is the valid recall node of maximum depth 
2. s is the number of safe product leaves in the subtree rooted at v 
The value “s” may be 0. 
## Example

In the following tree, a star ★ marks a recalled product:

```
           r
          / \
         a   b
        / \ / \
       c  d z  w
      /| /|
     p*q x*y
```

Where:
- **Leaves (products)**: p, q, x, y, z, w
- **Recalled products**: p★, x★ (safe products: q, y, z, w)
- **Internal nodes**: r, a, b, c, d

**Analysis:**
- The subtree rooted at `a` contains both recalled products (p and x via its children c and d).
- The subtree rooted at `c` contains only p (not x) — **not valid**.
- The subtree rooted at `d` contains only x (not p) — **not valid**.
- The subtree rooted at `b` contains neither p nor x — **not valid**.
- The subtree rooted at `r` is valid but shallower than `a`.

Therefore, `a` is the valid recall node of **maximum depth** (depth 1 from root).

The safe products in the subtree rooted at `a` are `q` (in c) and `y` (in d).

**Output:** `(a, 2)` 
The tree is not assumed to be binary. The children of a node may be examined using the Tree ADT operations from the lecture. The label of any node and the mark of any leaf can be inspected in O(1) time. 
Design an algorithm that produces the required output in O(n) worst case time. 
(a) Describe the algorithm in plain English. 
(b) Prove correctness, that the returned node is the valid recall node of maximum depth. Also prove that the returned number of safe products is correct. 
(c) Analyse the worst case running time and additional space used by the algorithm. 
