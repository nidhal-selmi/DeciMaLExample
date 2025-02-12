import re
import json

def parse_indented_model(text):
    """
    Parse a SysML model based on indentation.
    
    Assumptions:
    - Lines starting with "package", "part", or "actor" (or "description") define model elements.
    - Indentation (leading whitespace) determines nesting.
    - The syntax for an element is assumed to be one of:
         package <Name> [as <Alias>] {   or   package <Name> [as <Alias>]
         part <Name> [as <Alias>] : <Type> [ { ... } ]
         actor <Name> [as <Alias>] [<<...>>]
         description = "..."
    - Curly braces may be present but we rely primarily on indentation.
    """
    lines = text.splitlines()
    # Use a dummy root to collect all top-level elements.
    root = {"name": None, "parts": []}
    # Stack: (indent level, node)
    stack = [(0, root)]
    
    # Regex patterns (allowing any indentation with ^\s*)
    package_pattern = re.compile(r'^\s*package\s+("?[A-Za-z0-9\s]+"?)\s*(?:as\s+(\w+))?')
    part_pattern = re.compile(r'^\s*part\s+([\w\d_\[\]]+)\s*(?:as\s+(\w+))?\s*:\s*([\w\d_]+)')
    actor_pattern = re.compile(r'^\s*actor\s+("?[A-Za-z0-9\s]+"?)\s*(?:as\s+(\w+))?')
    description_pattern = re.compile(r'^\s*description\s*=\s*"([^"]*)"')
    
    for line in lines:
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip())
        content = line.strip()
        
        # Pop from stack until current indent is >= top's indent.
        while stack and indent < stack[-1][0]:
            stack.pop()
        
        m = package_pattern.match(line)
        if m:
            name = m.group(1).strip('"')
            alias = m.group(2) if m.group(2) else None
            node = {"type": "Package", "name": name, "parts": []}
            if alias:
                node["alias"] = alias
            stack[-1][1].setdefault("parts", []).append(node)
            # Only push onto stack if the line ends with "{"
            if line.rstrip().endswith("{"):
                stack.append((indent + 1, node))
            continue
        
        m = part_pattern.match(line)
        if m:
            name = m.group(1)
            alias = m.group(2) if m.group(2) else None
            part_type = m.group(3)
            node = {"type": part_type, "name": name}
            if alias:
                node["alias"] = alias
            if part_type in ["LogicalComponent", "LogicalFunction", "LogicalActor"]:
                node["parts"] = []
            stack[-1][1].setdefault("parts", []).append(node)
            if line.rstrip().endswith("{"):
                stack.append((indent + 1, node))
            continue
        
        m = actor_pattern.match(line)
        if m:
            name = m.group(1).strip('"')
            alias = m.group(2) if m.group(2) else None
            node = {"type": "LogicalActor", "name": name}
            if alias:
                node["alias"] = alias
            stack[-1][1].setdefault("parts", []).append(node)
            continue
        
        m = description_pattern.match(line)
        if m:
            desc = m.group(1)
            stack[-1][1]["description"] = desc
            continue
        
        if content == '}':
            continue
        
        print("Warning: Unhandled line:", line)
    
    return root

def build_plantuml_from_tree(tree):
    """
    Transform the IR tree into PlantUML code.
    Mapping:
      - Package nodes -> PlantUML package.
      - LogicalComponent -> rectangle with stereotype <<logicalComponent>>.
      - LogicalFunction -> class with stereotype <<logicalFunction>> and with description attribute.
      - LogicalActor -> rectangle with stereotype <<logicalActor>>.
      
    Additionally, for a package that contains both the functions and the logical architecture,
    we reorder the children so that the functions package (name starting with "DroneFunctions")
    is output before the logical architecture package.
    """
    def reorder_children(children):
        # Pull out functions packages first, then others.
        functions = [child for child in children if child.get("name", "").strip().startswith("DroneFunctions")]
        others = [child for child in children if not child.get("name", "").strip().startswith("DroneFunctions")]
        return functions + others

    def generate_plantuml(node, indent=1):
        lines = []
        indent_str = "    " * indent
        node_type = node.get("type")
        alias = node.get("alias")
        
        # Helper: format element name with alias using 'as' syntax.
        def format_element(name, alias):
            return f'"{name}"' + (f' as {alias}' if alias else '')
        
        if node_type == "Package":
            # If this package has children, reorder them if needed.
            children = node.get("parts", [])
            # For example, if the package name is "DroneDevelopment", we reorder its children.
            if node.get("name", "").strip().startswith("DroneDevelopment"):
                children = reorder_children(children)
            if "alias" in node:
                lines.append(f'{indent_str}package {format_element(node["name"], node["alias"])} {{')
            else:
                lines.append(f'{indent_str}package "{node["name"]}" {{')
            for child in children:
                lines.extend(generate_plantuml(child, indent + 1))
            lines.append(f'{indent_str}}}')
        elif node_type == "LogicalComponent":
            # Use rectangle for logical components.
            text = format_element(node["name"], alias)
            text = f'{text} <<logicalComponent>>'
            if node.get("parts"):
                lines.append(f'{indent_str}rectangle {text} {{')
                for child in node.get("parts", []):
                    lines.extend(generate_plantuml(child, indent + 1))
                lines.append(f'{indent_str}}}')
            else:
                lines.append(f'{indent_str}rectangle {text}')
        elif node_type == "LogicalFunction":
            # Use class for logical functions.
            text = format_element(node["name"], alias)
            text = f'{text} <<logicalFunction>>'
            desc = node.get("description", "")
            lines.append(f'{indent_str}class {text} {{')
            lines.append(f'{indent_str}    description = "{desc}"')
            lines.append(f'{indent_str}}}')
        elif node_type == "LogicalActor":
            # Use rectangle for logical actors.
            text = format_element(node["name"], alias)
            text = f'{text} <<logicalActor>>'
            lines.append(f'{indent_str}rectangle {text}')
        else:
            lines.append(f'{indent_str}package "{node["name"]}"')
        return lines

    header = [
        "@startuml",
        "'==================================================",
        "' Define Profile Styles with Stereotypes",
        "'==================================================",
        "",
        "allowmixing",
        "' Class for Logical Functions with custom formatting",
        "skinparam class {",
        "  BackgroundColor<<logicalFunction>> LightGreen",
        "  BorderColor<<logicalFunction>> DarkGreen",
        "  FontStyle<<logicalFunction>> Bold",
        "  FontColor<<logicalFunction>> Black",
        "}",
        "",
        "' Rectangle for Logical Components",
        "skinparam rectangle {",
        "  BackgroundColor<<logicalComponent>> LightSteelBlue",
        "  BorderColor<<logicalComponent>> DarkBlue",
        "  FontStyle<<logicalComponent>> Bold",
        "  FontColor<<logicalComponent>> Black",
        "}",
        "",
        "' Rectangle for Logical Actors",
        "skinparam rectangle {",
        "  BackgroundColor<<logicalActor>> LightBlue",
        "  BorderColor<<logicalActor>> Blue",
        "  FontStyle<<logicalActor>> Bold",
        "  FontColor<<logicalactor>> Black",
        "}",
        "",
        "'==================================================",
        "' Generated SysML Diagram",
        "'==================================================",
    ]
    body = []
    # Iterate over all top-level parts from the dummy root.
    for part in tree.get("parts", []):
        body.extend(generate_plantuml(part, indent=0))
    footer = ["@enduml"]
    return "\n".join(header + body + footer)

if __name__ == "__main__":
    with open("model.sysml", "r") as f:
        sysml_text = f.read()
    
    tree = parse_indented_model(sysml_text)
    
    with open("Model1.json", "w") as f:
        json.dump(tree, f, indent=4)
    print("Intermediate JSON IR written to Model1.json")
    
    plantuml_code = build_plantuml_from_tree(tree)
    
    with open("Model1.plantuml", "w") as f:
        f.write(plantuml_code)
    print("Generated PlantUML code written to Model1.plantuml")
