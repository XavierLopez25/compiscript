"""Label management utilities for TAC generation."""

from __future__ import annotations

from typing import Dict, List, Optional


class LabelManager:
    """Manage label creation, scope stacks, and resolution tracking."""

    def __init__(self, generate_label_callback):
        """Initialize the manager with a label generator callback."""
        self._generate_label = generate_label_callback
        self._label_definitions: Dict[str, bool] = {}
        self._label_references: Dict[str, int] = {}
        self._context_stack: List[Dict[str, Optional[str]]] = []

    # ------------------------------------------------------------------
    # Label lifecycle
    # ------------------------------------------------------------------
    def new_label(self, prefix: str = "L", hint: Optional[str] = None) -> str:
        """Produce a unique label name with optional semantic hint."""
        base = prefix
        if hint:
            sanitized = ''.join(ch if ch.isalnum() or ch == '_' else '_' for ch in hint)
            sanitized = sanitized.strip('_') or prefix
            base = f"{prefix}_{sanitized}"

        label = self._generate_label(base)
        self._label_definitions.setdefault(label, False)
        return label

    def define_label(self, label: str) -> None:
        """Mark a label as defined in the instruction stream."""
        self._label_definitions[label] = True

    def reference_label(self, label: str) -> None:
        """Track that a label is the target of a jump."""
        self._label_references[label] = self._label_references.get(label, 0) + 1
        self._label_definitions.setdefault(label, False)

    def unresolved_labels(self) -> List[str]:
        """Return any referenced labels that were never defined."""
        return [label for label, defined in self._label_definitions.items()
                if not defined and self._label_references.get(label, 0) > 0]

    # ------------------------------------------------------------------
    # Control-flow context helpers
    # ------------------------------------------------------------------
    def push_loop(self, break_label: str, continue_label: str) -> None:
        """Register entry into a loop context."""
        self._context_stack.append({
            'type': 'loop',
            'break': break_label,
            'continue': continue_label
        })
        self.reference_label(break_label)
        self.reference_label(continue_label)

    def pop_loop(self) -> None:
        """Remove the current loop context."""
        if not self._context_stack or self._context_stack[-1]['type'] != 'loop':
            raise RuntimeError("Attempted to pop loop context when none active")
        self._context_stack.pop()

    def push_switch(self, break_label: str) -> None:
        """Register entry into a switch statement context."""
        self._context_stack.append({
            'type': 'switch',
            'break': break_label,
            'continue': None
        })
        self.reference_label(break_label)

    def pop_switch(self) -> None:
        """Remove the current switch context."""
        if not self._context_stack or self._context_stack[-1]['type'] != 'switch':
            raise RuntimeError("Attempted to pop switch context when none active")
        self._context_stack.pop()

    def current_break_label(self) -> str:
        """Obtain the nearest break label in scope."""
        for ctx in reversed(self._context_stack):
            label = ctx['break']
            if label:
                return label
        raise RuntimeError("Break statement outside of loop/switch context")

    def current_continue_label(self) -> str:
        """Obtain the nearest continue label in scope."""
        for ctx in reversed(self._context_stack):
            if ctx['type'] == 'loop':
                label = ctx['continue']
                if label:
                    return label
        raise RuntimeError("Continue statement outside of loop context")

    def has_loop_context(self) -> bool:
        """Check if a loop context is currently active."""
        return any(ctx['type'] == 'loop' for ctx in self._context_stack)

    def reset(self) -> None:
        """Reset all label and context tracking information."""
        self._label_definitions.clear()
        self._label_references.clear()
        self._context_stack.clear()

    def get_statistics(self) -> Dict[str, int]:
        """Return basic usage statistics useful for debugging."""
        return {
            'contexts': len(self._context_stack),
            'labels_tracked': len(self._label_definitions),
            'labels_referenced': len([label for label, count in self._label_references.items() if count > 0]),
            'unresolved_labels': len(self.unresolved_labels()),
        }
