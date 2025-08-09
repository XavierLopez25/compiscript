from AST.ast_nodes import ASTNode

class DotExporter:
    def __init__(self):
        self.lines = ["digraph AST {", "  node [shape=box];"]
        self._next_id = 0
        self._ids = {}
        self._emitted = set()

    def _new_id(self):
        i = self._next_id
        self._next_id += 1
        return f"n{i}"

    def export(self, root):
        self._emit(root)
        self.lines.append("}")
        return "\n".join(self.lines)

    def _id(self, node):
        key = id(node)
        if key not in self._ids:
            self._ids[key] = self._new_id()
        return self._ids[key]

    def _emit_node(self, node):
        key = id(node)
        if key in self._emitted:
            return
        nid = self._id(node)
        label = self._label(node)
        self.lines.append(f'  {nid} [label="{label}"];')
        self._emitted.add(key)

    def _emit(self, node):
        if node is None:
            return
        nid = self._id(node)
        self._emit_node(node)
        for child in self._children(node):
            cid = self._id(child)
            self._emit_node(child)
            self.lines.append(f'  {nid} -> {cid};')
            self._emit(child)

    def _label(self, node):
        parts = [node.__class__.__name__]
        for key in ("name", "op", "property"):
            if hasattr(node, key):
                parts.append(f"{key}={getattr(node, key)}")
        if hasattr(node, "type") and getattr(node, "type") is not None:
            parts.append(f"type={getattr(node, 'type')}")
        if hasattr(node, "type_node") and getattr(node, "type_node") is not None:
            tn = getattr(node, "type_node")
            base = getattr(tn, "base", "?")
            dims = getattr(tn, "dimensions", 0)
            parts.append(f"TN={base}[{dims}]")
        return "\\n".join(parts).replace('"', '\\"')

    def _iter_attrs(self, node):
        if hasattr(node, "__dataclass_fields__"):
            for f in node.__dataclass_fields__.values():
                yield f.name, getattr(node, f.name)
            return

        if hasattr(node, "__dict__"):
            yield from vars(node).items()

    def _children(self, node):
        if not isinstance(node, ASTNode):
            return []
        out = []
        for _, v in self._iter_attrs(node):
            if isinstance(v, ASTNode):
                out.append(v)
            elif isinstance(v, (list, tuple)):
                out.extend(x for x in v if isinstance(x, ASTNode))
        return out

def write_dot(root, path="ast.dot"):
    exp = DotExporter()
    dot = exp.export(root)
    with open(path, "w") as f:
        f.write(dot)
