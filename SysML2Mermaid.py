import re
import json

# ----------------------------
# HTML Label Helpers for Mermaid Flowchart
# ----------------------------
def html_label_two_compartment(top_text, bottom_text, width=120, top_height=15, bottom_height=30):
    """
    Return an HTML-like label with two compartments.
    For LogicalFunction nodes: top cell shows the name and bottom cell shows the description.
    """
    return f'''<table border="1" cellspacing="0" cellpadding="2">
  <tr><td fixedsize="true" width="{width}" height="{top_height}" align="center">{top_text}</td></tr>
  <tr><td fixedsize="true" width="{width}" height="{bottom_height}" align="center">{bottom_text}</td></tr>
</table>'''

def html_label_bottom_only(text, width=150, top_height=10, bottom_height=40):
    """
    Return an HTML-like label with two compartments where the top is empty and the bottom shows the text.
    Used for LogicalComponent and LogicalActor nodes.
    """
    return f'''<table border="1" cellspacing="0" cellpadding="2">
  <tr><td fixedsize="true" width="{width}" height="{top_height}" align="center"></td></tr>
  <tr><td fixedsize="true" width="{width}" height="{bottom_height}" align="center">{text}</td></tr>
</table>'''

# ----------------------------
# Parsing SysML-like Input
# ----------------------------
def parse_indented_model(text):
    """
    Parse a SysML model based on indentation.
    
    Assumptions:
      - Lines starting with "package", "part", "actor", or "description" define model elements.
      - Indentation (leading whitespace) determines nesting.
      - Expected syntax:
            package <Name> [as <Alias>]
            part <Name> [as <Alias>] : <Type>
            actor <Name> [as <Alias>]
            description = "..."
      - Curly braces (if any) are ignored.
    """
    lines = text.splitlines()
    root = {"name": None, "parts": []}  # Dummy root.
    stack = [(0, root)]
    prev_indent = 0

    # Regex patterns
    package_pattern = re.compile(r'^\s*package\s+("?[A-Za-z0-9\s]+"?)\s*(?:as\s+(\w+))?')
    part_pattern = re.compile(r'^\s*part\s+([\w\d_\[\]]+)\s*(?:as\s+(\w+))?\s*:\s*([\w\d_]+)')
    actor_pattern = re.compile(r'^\s*actor\s+("?[A-Za-z0-9\s]+"?)\s*(?:as\s+(\w+))?')
    description_pattern = re.compile(r'^\s*description\s*=\s*"([^"]*)"')
    
    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip().rstrip("{}").strip()  # Remove trailing braces.
        if indent <= prev_indent:
            while len(stack) > 1 and stack[-1][0] >= indent:
                stack.pop()
        prev_indent = indent

        m = package_pattern.match(line)
        if m:
            name = m.group(1).strip('"').strip()
            alias = m.group(2) if m.group(2) else None
            node = {"type": "Package", "name": name, "parts": []}
            if alias:
                node["alias"] = alias
            stack[-1][1].setdefault("parts", []).append(node)
            stack.append((indent, node))
            continue
        
        m = part_pattern.match(line)
        if m:
            name = m.group(1).strip()
            alias = m.group(2) if m.group(2) else None
            part_type = m.group(3).strip()
            node = {"type": part_type, "name": name}
            if alias:
                node["alias"] = alias
            if part_type in ["LogicalComponent", "LogicalFunction", "LogicalActor"]:
                node["parts"] = []
            stack[-1][1].setdefault("parts", []).append(node)
            stack.append((indent, node))
            continue
        
        m = actor_pattern.match(line)
        if m:
            name = m.group(1).strip('"').strip()
            alias = m.group(2) if m.group(2) else None
            node = {"type": "LogicalActor", "name": name}
            if alias:
                node["alias"] = alias
            stack[-1][1].setdefault("parts", []).append(node)
            stack.append((indent, node))
            continue
        
        m = description_pattern.match(line)
        if m:
            desc = m.group(1).strip()
            stack[-1][1]["description"] = desc
            continue
        
        print("Warning: Unhandled line:", line)
    
    return root

# ----------------------------
# Building Mermaid Flowchart from the IR Tree
# ----------------------------
def build_mermaid_flowchart_from_tree(tree):
    """
    Transform the IR tree into a Mermaid flowchart.
    
    Mappings:
      - For LogicalFunction nodes: render as a node with an HTML label using html_label_two_compartment.
      - For LogicalComponent and LogicalActor nodes: render as a node with an HTML label using html_label_bottom_only.
      - For Package nodes: render as subgraphs with nested content.
      
    Only containment (hierarchical nesting) is represented.
    """
    lines = []
    lines.append("flowchart TD")
    
    # Use indentation (4 spaces per level) to produce nicely indented Mermaid code.
    def process_node(node, level=1):
        spacing = "    " * level
        node_id = node["name"].replace(" ", "_")
        typ = node.get("type")
        if typ == "Package":
            lines.append(f"{spacing}subgraph {node_id}[{node['name']}]")
            for child in node.get("parts", []):
                process_node(child, level+1)
            lines.append(f"{spacing}end")
        elif typ == "LogicalFunction":
            label = html_label_two_compartment(node["name"], node.get("description", ""), width=120, top_height=15, bottom_height=30)
            lines.append(f"{spacing}{node_id}[{label}]")
        elif typ in ["LogicalComponent", "LogicalActor"]:
            label = html_label_bottom_only(node["name"], width=150, top_height=10, bottom_height=40)
            lines.append(f"{spacing}{node_id}[{label}]")
        else:
            lines.append(f"{spacing}{node_id}[{node['name']}]")
        # Process children (if any)
        for child in node.get("parts", []):
            process_node(child, level+1)
    
    for child in tree.get("parts", []):
        process_node(child, level=1)
    
    return "\n".join(lines)

if __name__ == "__main__":
    with open("model.sysml", "r") as f:
        sysml_text = f.read()
    
    tree = parse_indented_model(sysml_text)
    
    with open("Model1.json", "w") as f:
        json.dump(tree, f, indent=4)
    print("Intermediate JSON IR written to Model1.json")
    
    mermaid_code = build_mermaid_flowchart_from_tree(tree)
    
    with open("Model1.mmd", "w") as f:
        f.write(mermaid_code)
    print("Generated Mermaid flowchart code written to Model1.mmd")
