from typing import List, Tuple, Union

def check_transcript(events: List[Tuple[str, int]]) -> Union[str, Tuple[str, int]]:
    opening_stack = []
    if len(events) == 0:
        return "valid", 0
    current_nested_depth = 0
    for index, item in enumerate(events):
        if item[0] == "open":
            opening_stack.append(item[1])
            current_nested_depth = max(current_nested_depth, len(opening_stack))
        else:
            if not opening_stack:
                return ("invalid", index)
            else:
                if opening_stack[-1] == item[1]:
                    opening_stack.pop()
                else:
                    return ("invalid", index)

    if opening_stack:
        return "incomplete"
    return ("valid", current_nested_depth)