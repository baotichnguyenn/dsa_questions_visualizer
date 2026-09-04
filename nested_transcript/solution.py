from typing import List, Tuple, Union

def check_transcript(events: List[Tuple[str, int]]) -> Union[str, Tuple[str, int]]:
    opening_stack = []
    nested_depth = 0
    for i in events:
        if i[0] == "open":
            opening_stack.append(i[1])
            nested_depth +=1
        else:
            if opening_stack[-1] == i[1]:
                opening_stack.pop()
            else:
                return ("invalid", i.index())

    if opening_stack:
        return "incomplete"
    return ("valid", nested_depth)