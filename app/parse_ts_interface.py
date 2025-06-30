import re
def parse_ts_interface(ts_code: str) -> dict:
    lines = ts_code.splitlines()
    schema_stack = []
    root = {}
    current = root
    key_stack = []

    for line in lines:
        line = line.strip().rstrip(";")

        if not line or line.startswith("interface "):
            continue

        # Case: nested object inside array
        if re.match(r"\w+:\s*{\s*$", line):  # e.g. ingredients: {
            key = line.split(":")[0].strip()
            new_obj = {}
            current[key] = new_obj
            schema_stack.append(current)
            key_stack.append(key)
            current = new_obj

        # Case: closing a nested object
        elif line == "}[]":
            # we assume it's ending an object inside an array
            last_key = key_stack.pop() if key_stack else "unknown"
            # wrap previous dict in a list
            parent = schema_stack.pop()
            parent[last_key] = [current]
            current = parent

        elif line == "}":
            if schema_stack:
                current = schema_stack.pop()
                if key_stack:
                    key_stack.pop()
            # Ignore closing brace if it's the final one for the interface

        # Case: simple field
        elif ":" in line:
            key, val_type = map(str.strip, line.split(":"))
            if val_type.endswith("[]"):
                current[key] = []
            elif val_type == "string":
                current[key] = key  # Store the field name for extraction
            elif val_type == "number":
                current[key] = 0
            elif val_type == "boolean":
                current[key] = False
            else:
                current[key] = key  # Store the field name for unknown types

    return root
