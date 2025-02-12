import re
import json

# ----------------------------
# HTML Label Helpers
# ----------------------------
def html_label_two_compartment(top_text, bottom_text, width=120, top_height=15, bottom_height=30):
    """
    Create an HTML label with two compartments.
    For LogicalFunction nodes: top cell shows the name and bottom shows the description.
    """
    return f'''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="2">
  <TR><TD FIXEDSIZE="true" WIDTH="{width}" HEIGHT="{top_height}" ALIGN="CENTER">{top_text}</TD></TR>
  <TR><TD FIXEDSIZE="true" WIDTH="{width}" HEIGHT="{bottom_height}" ALIGN="CENTER">{bottom_text}</TD></TR>
</TABLE>>'''

def html_label_bottom_only(text, width=120, top_height=10, bottom_height=40):
    """
    Create an HTML label with two compartments where the top is empty and the bottom contains the text.
    Used for LogicalActor nodes.
    """
    return f'''<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="2">
  <TR><TD FIXEDSIZE="true" WIDTH="{width}" HEIGHT="{top_height}" ALIGN="CENTER"></TD></TR>
  <TR><TD FIXEDSIZE="true" WIDTH="{width}" HEIGHT="{bottom_height}" ALIGN="CENTER">{text}</TD></TR>
</TABLE>>'''

# ----------------------------
# Parsing SysML-like Input
# ----------------------------
def parse_indented_model(text):
    """
    Parse a SysML model based on indentation.
    
    Assumptions:
      - Lines starting with "package", "part", "actor", or "description" define model elements.
      - Indentation (leading whitespace) determines nesting.
      - The syntax for an element is assumed to be one of:
            package <Name> [as <Alias>]
            part <Name> [as <Alias>] : <Type>
            actor <Name> [as <Alias>]
            description = "..."
      - Curly braces, if present, are ignored.
    """
    lines = text.splitlines()
    root = {"name": None, "parts": []}  # Dummy root.
    stack = [(0, root)]
    prev_indent = 0
    
    # Regex patterns (allowing leading whitespace)
    package_pattern = re.compile(r'^\s*package\s+("?[A-Za-z0-9\s]+"?)\s*(?:as\s+(\w+))?')
    part_pattern = re.compile(r'^\s*part\s+([\w\d_\[\]]+)\s*(?:as\s+(\w+))?\s*:\s*([\w\d_]+)')
    actor_pattern = re.compile(r'^\s*actor\s+("?[A-Za-z0-9\s]+"?)\s*(?:as\s+(\w+))?')
    description_pattern = re.compile(r'^\s*description\s*=\s*"([^"]*)"')
    
    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip().rstrip("{}").strip()  # Remove trailing braces.
        # Adjust parent solely based on indentation.
        # Ensure we never pop the dummy root.
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
# Building Graphviz DOT from the IR Tree
# ----------------------------
def build_dot_from_tree(tree):
    """
    Transform the IR tree into Graphviz DOT code.
    
    Mappings (all elements are now wrapped in subgraphs):
      - LogicalFunction: Render as a subgraph containing a node with an HTML label (two compartments: name and description), fillcolor=lightgreen.
      - LogicalComponent: 
            If it has children, render as a subgraph (with label, margin, style and fillcolor=lightblue)
            that first creates a representative (invisible) node and then nests its children subgraphs.
            If empty, render as a subgraph enclosing a single node (with an HTML label).
      - LogicalActor: Render as a subgraph containing a node with an HTML label (two compartments: top empty, bottom with name), fixed size.
      - Package: Render as a subgraph (with label) that encloses a representative node and nests children subgraphs.
      
    An invisible edge is added between top-level packages "DroneFunctions" and "DroneLogicalArchitecture" to force vertical ordering.
    Global graph attributes are set for a fixed size and ratio, and the osage layout engine is used.
    """
    lines = []
    lines.append('digraph G {')
    lines.append('    graph [layout=osage, splines=ortho, rankdir=TB, compound=true, size="8,4!", ratio=0.5, stylesheet="mystyle.css"];')
    lines.append('    node [fontname="Helvetica", fontsize=10];')
    lines.append("")
    
    node_counter = 0
    def next_id():
        nonlocal node_counter
        node_counter += 1
        return f"id{node_counter}"
    
    def generate_dot(node, indent):
        dot_lines = []
        spacing = " " * indent
        # Every element becomes a subgraph (cluster) with its own representative node.
        cluster_id = f"cluster_{next_id()}"
        rep_node = next_id()  # The node inside the subgraph used for connections
        
        dot_lines.append(f'{spacing}subgraph {cluster_id} {{')
        # Depending on type, style the subgraph and the node inside.
        typ = node.get("type")
        if typ == "LogicalFunction":
            label = html_label_two_compartment(node.get("name"), node.get("description", ""),
                                                width=120, top_height=15, bottom_height=30)
            dot_lines.append(f'{spacing}    {rep_node} [shape=none, style=filled, fillcolor=lightgreen, label={label}];')
        elif typ == "LogicalComponent":
            if node.get("parts"):
                # Container LogicalComponent: set cluster styling and label, add a rep node, then add children.
                dot_lines.append(f'{spacing}    label = "{node.get("name")}";')
                dot_lines.append(f'{spacing}    style=filled;')
                dot_lines.append(f'{spacing}    fillcolor=lightblue;')
                dot_lines.append(f'{spacing}    margin=10;')
                dot_lines.append(f'{spacing}    {rep_node} [shape=none, label=""];')
                for child in node.get("parts", []):
                    child_rep, child_lines = generate_dot(child, indent + 4)
                    dot_lines.extend(child_lines)
            else:
                # Leaf LogicalComponent: render its own node with an HTML label.
                label = html_label_bottom_only(node.get("name"), width=150, top_height=10, bottom_height=40)
                dot_lines.append(f'{spacing}    {rep_node} [shape=none, style=filled, fillcolor=lightblue, label={label}];')
        elif typ == "LogicalActor":
            label = html_label_bottom_only(node.get("name"), width=120, top_height=10, bottom_height=40)
            dot_lines.append(f'{spacing}    {rep_node} [shape=none, style=filled, fillcolor=lightblue, fixedsize=true, label={label}];')
        elif typ == "Package":
            # Package: use the cluster's label and add a representative node, then nest children.
            dot_lines.append(f'{spacing}    label = "{node.get("name")}";')
            dot_lines.append(f'{spacing}    {rep_node} [shape=none, label=""];')
            for child in node.get("parts", []):
                child_rep, child_lines = generate_dot(child, indent + 4)
                dot_lines.extend(child_lines)
        else:
            dot_lines.append(f'{spacing}    {rep_node} [label="{node.get("name")}"];')
        dot_lines.append(f'{spacing}}}')
        return rep_node, dot_lines
    
    # Record the representative nodes for top-level packages for reordering.
    top_functions = None
    top_architecture = None
    for child in tree.get("parts", []):
        rep, child_lines = generate_dot(child, 4)
        child_name = child.get("name", "").strip()
        if child_name == "DroneFunctions":
            top_functions = rep
        elif child_name == "DroneLogicalArchitecture":
            top_architecture = rep
        lines.extend(child_lines)
    
    if top_functions and top_architecture:
        lines.append(f'    {top_functions} -> {top_architecture} [style=invis];')
    
    lines.append("}")
    return "\n".join(lines)

if __name__ == "__main__":
    with open("model.sysml", "r") as f:
        sysml_text = f.read()
    
    tree = parse_indented_model(sysml_text)
    
    with open("Model1.json", "w") as f:
        json.dump(tree, f, indent=4)
    print("Intermediate JSON IR written to Model1.json")
    
    dot_code = build_dot_from_tree(tree)
    
    with open("Model1.dot", "w") as f:
        f.write(dot_code)
    print("Generated Graphviz DOT code written to Model1.dot")
