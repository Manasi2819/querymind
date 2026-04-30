import re

def parse_schema_metadata(schema_text: str) -> dict:
    schema_map = {}
    for chunk in schema_text.split("\n\n"):
        table_match = re.search(r"(?i)Table:\s*(\w+)", chunk)
        cols_match = re.search(r"(?i)Columns:\s*(.*)", chunk)
        if table_match and cols_match:
            table_name = table_match.group(1)
            cols_str = cols_match.group(1)
            # Split by comma but NOT if it's inside parentheses (e.g. NUMERIC(18, 2))
            cols_raw = re.split(r",\s*(?![^()]*\))", cols_str)
            cols = [re.sub(r"\s*\(.*\)", "", c).strip() for c in cols_raw]
            schema_map[table_name] = cols
    return schema_map

with open('emp_schema.txt', 'r') as f:
    text = f.read()

table_names = re.findall(r"(?i)Table:\s*(\w+)", text)
print(f"Tables found: {table_names}")
