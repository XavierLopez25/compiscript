"""
Integrated MIPS Generator

This module orchestrates the complete TAC to MIPS translation process,
integrating all the translator components (expressions, control flow, functions)
and applying peephole optimizations.

Usage:
    generator = IntegratedMIPSGenerator()
    mips_code = generator.generate_from_tac_file("output.tac")

    # Save to file
    with open("output.s", "w") as f:
        f.write(mips_code)
"""

from typing import List, Dict, Optional
import re

from tac.instruction import (
    AssignInstruction,
    GotoInstruction,
    ConditionalGotoInstruction,
    LabelInstruction,
    BeginFuncInstruction,
    EndFuncInstruction,
    PushParamInstruction,
    CallInstruction,
    PopParamsInstruction,
    ReturnInstruction,
    ArrayAccessInstruction,
    PropertyAccessInstruction,
    NewInstruction,
    CommentInstruction,
    AllocateArrayInstruction,
)

from .function_translator import FunctionTranslator
from .expression_translator import ExpressionTranslator
from .control_flow_translator import ControlFlowTranslator
from .class_translator import ClassTranslator
from .peephole_optimizer import PeepholeOptimizer, OptimizationStats
from .instruction import MIPSInstruction, MIPSLabel, MIPSComment, MIPSDirective
from .data_section_manager import DataSectionManager
from .runtime_library import RuntimeLibrary


class IntegratedMIPSGenerator:
    """
    Main MIPS code generator that integrates all translation phases.

    Architecture:
    1. Parse TAC instructions from file or list
    2. Translate to MIPS using specialized translators
    3. Apply peephole optimizations
    4. Generate final MIPS assembly code
    """

    def __init__(self, enable_optimization: bool = True):
        """
        Initialize the MIPS generator.

        Args:
            enable_optimization: Whether to apply peephole optimizations
        """
        self.enable_optimization = enable_optimization

        # Create data section manager
        self.data_manager = DataSectionManager()

        # Create function translator (base translator)
        self.function_translator = FunctionTranslator(data_section_manager=self.data_manager)

        # Create other translators, passing function_translator as the base
        self.expression_translator = ExpressionTranslator(self.function_translator)
        self.control_flow_translator = ControlFlowTranslator(self.function_translator)
        self.class_translator = ClassTranslator(
            base_translator=self.function_translator,
            expression_translator=self.expression_translator
        )

        # Create optimizer
        self.optimizer = PeepholeOptimizer()

        # Statistics
        self.optimization_stats: Optional[OptimizationStats] = None

    def generate_from_tac_file(self, tac_file_path: str) -> str:
        """
        Generate MIPS code from a TAC file.

        Args:
            tac_file_path: Path to the TAC file

        Returns:
            Complete MIPS assembly code as string
        """
        # Read TAC file
        with open(tac_file_path, 'r') as f:
            tac_lines = f.readlines()

        # Parse TAC instructions
        tac_instructions = self._parse_tac_lines(tac_lines)

        # Generate MIPS
        return self.generate_from_tac(tac_instructions)

    def generate_from_tac(self, tac_instructions: List) -> str:
        """
        Generate MIPS code from parsed TAC instructions.

        Args:
            tac_instructions: List of TAC instruction objects

        Returns:
            Complete MIPS assembly code as string
        """
        # Pre-process: extract string literals from TAC
        self._extract_string_literals(tac_instructions)

        # Pre-process: register classes from TAC comments
        self._register_classes_from_tac(tac_instructions)

        # Generate header
        self._generate_header()

        # Generate data section with strings and runtime support
        self._generate_data_section()

        # Generate text section
        self._generate_text_section(tac_instructions)

        # Add runtime library functions
        self._generate_runtime_functions()

        # Get all generated MIPS nodes
        all_nodes = (
            self.function_translator.data_section +
            self.function_translator.text_section
        )

        # Apply optimizations if enabled
        if self.enable_optimization:
            all_nodes = self.optimizer.optimize(all_nodes)
            self.optimization_stats = self.optimizer.get_stats()

        # Convert to string
        return self._nodes_to_string(all_nodes)

    def _parse_tac_lines(self, tac_lines: List[str]) -> List:
        """
        Parse TAC lines into instruction objects.

        This is a simplified parser that recognizes common TAC patterns.
        For a production system, you'd want a more robust parser.
        """
        instructions = []

        for line in tac_lines:
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith('#'):
                if line.startswith('#'):
                    instructions.append(CommentInstruction(line[1:].strip()))
                continue

            # Try to parse the instruction
            instr = self._parse_tac_instruction(line)
            if instr:
                instructions.append(instr)

        return instructions

    def _parse_tac_instruction(self, line: str):
        """Parse a single TAC instruction line."""
        # BeginFunc
        if line.startswith('BeginFunc'):
            # Try with frame_size and params: BeginFunc name, count, frame_size=N, params=[a,b,c]
            match = re.match(r'BeginFunc\s+(\w+),\s*(\d+),\s*frame_size=(\d+),\s*params=\[([^\]]*)\]', line)
            if match:
                param_names = [p.strip() for p in match.group(4).split(',') if p.strip()]
                return BeginFuncInstruction(match.group(1), int(match.group(2)), int(match.group(3)), param_names)
            # Try with frame_size only: BeginFunc name, params, frame_size=N
            match = re.match(r'BeginFunc\s+(\w+),\s*(\d+),\s*frame_size=(\d+)', line)
            if match:
                return BeginFuncInstruction(match.group(1), int(match.group(2)), int(match.group(3)))
            # Try with params only: BeginFunc name, count, params=[a,b,c]
            match = re.match(r'BeginFunc\s+(\w+),\s*(\d+),\s*params=\[([^\]]*)\]', line)
            if match:
                param_names = [p.strip() for p in match.group(3).split(',') if p.strip()]
                return BeginFuncInstruction(match.group(1), int(match.group(2)), 0, param_names)
            # Try without frame_size or params: BeginFunc name, params
            match = re.match(r'BeginFunc\s+(\w+),\s*(\d+)', line)
            if match:
                return BeginFuncInstruction(match.group(1), int(match.group(2)))

        # EndFunc
        elif line.startswith('EndFunc'):
            match = re.match(r'EndFunc\s+(\w+)', line)
            if match:
                return EndFuncInstruction(match.group(1))

        # PushParam
        elif line.startswith('PushParam'):
            match = re.match(r'PushParam\s+(.+)', line)
            if match:
                return PushParamInstruction(match.group(1).strip())

        # PopParams
        elif line.startswith('PopParams'):
            match = re.match(r'PopParams\s+(\d+)', line)
            if match:
                return PopParamsInstruction(int(match.group(1)))

        # Call with assignment: t1 = call func, 2
        elif '=' in line and 'call' in line:
            match = re.match(r'(\w+)\s*=\s*call\s+(\w+),\s*(\d+)', line)
            if match:
                return CallInstruction(match.group(2), int(match.group(3)), match.group(1))

        # Call without assignment: call func, 2
        elif line.startswith('call'):
            match = re.match(r'call\s+(\w+),\s*(\d+)', line)
            if match:
                return CallInstruction(match.group(1), int(match.group(2)), None)

        # Return
        elif line.startswith('return'):
            match = re.match(r'return\s+(.+)', line)
            if match:
                return ReturnInstruction(match.group(1).strip())
            else:
                return ReturnInstruction(None)

        # Label (ends with :)
        elif line.endswith(':'):
            return LabelInstruction(line[:-1])

        # Goto
        elif line.startswith('goto'):
            match = re.match(r'goto\s+(\w+)', line)
            if match:
                return GotoInstruction(match.group(1))

        # Conditional goto: if x goto L or if x op y goto L
        elif line.startswith('if'):
            # Try relational: if x op y goto L
            match = re.match(r'if\s+(\S+)\s+(==|!=|<|>|<=|>=)\s+(\S+)\s+goto\s+(\w+)', line)
            if match:
                return ConditionalGotoInstruction(
                    match.group(1), match.group(4), match.group(3), match.group(2)
                )
            # Try simple: if x goto L
            match = re.match(r'if\s+(\S+)\s+goto\s+(\w+)', line)
            if match:
                return ConditionalGotoInstruction(match.group(1), match.group(2))

        # Property assignment: obj.property = value (check BEFORE array operations)
        elif '.' in line and '=' in line:
            match = re.match(r'(\w+)\.(\w+)\s*=\s*(.+)', line)
            if match:
                return PropertyAccessInstruction(match.group(3).strip(), match.group(1), match.group(2), is_assignment=True)

        # Array operations: Check for array assignment first (x[y] = z)
        # If it's not array assignment, fall through to check for array read (x = y[z])
        elif '[' in line and ']' in line and '=' in line:
            bracket_pos = line.index('[')
            equals_pos = line.index('=')
            # Array write: x[i] = val (bracket before equals)
            if bracket_pos < equals_pos:
                match = re.match(r'(\w+)\[(\w+)\]\s*=\s*(.+)', line)
                if match:
                    return ArrayAccessInstruction(match.group(3).strip(), match.group(1), match.group(2), is_assignment=True)
            # If bracket comes AFTER equals, it might be array read - continue to assignment block

        # Assignment: x = y op z, x = op y, x = y
        if '=' in line:
            # Try allocate_array: x = allocate_array size, elem_size
            match = re.match(r'(\w+)\s*=\s*allocate_array\s+(\S+),\s*(\d+)', line)
            if match:
                return AllocateArrayInstruction(match.group(1), match.group(2), int(match.group(3)))

            # Try binary with str_concat (needs special handling for string literals)
            match = re.match(r'(\w+)\s*=\s*(.+?)\s+(str_concat)\s+(.+)', line)
            if match:
                return AssignInstruction(match.group(1), match.group(2).strip(), match.group(3), match.group(4).strip())

            # Try binary: x = y op z
            match = re.match(r'(\w+)\s*=\s*(\S+)\s+(\+|-|\*|/|%|==|!=|<|>|<=|>=|&&|\|\|)\s+(\S+)', line)
            if match:
                return AssignInstruction(match.group(1), match.group(2), match.group(3), match.group(4))

            # Try array access read: x = y[z]
            match = re.match(r'(\w+)\s*=\s*(\w+)\[(\w+)\]', line)
            if match:
                return ArrayAccessInstruction(match.group(1), match.group(2), match.group(3), is_assignment=False)

            # Try new operator: x = new ClassName
            match = re.match(r'(\w+)\s*=\s*new\s+(\w+)', line)
            if match:
                return NewInstruction(match.group(1), match.group(2))

            # Try property access read: x = obj.property
            match = re.match(r'(\w+)\s*=\s*(\w+)\.(\w+)', line)
            if match:
                return PropertyAccessInstruction(match.group(1), match.group(2), match.group(3), is_assignment=False)

            # Try len operator: x = len y
            match = re.match(r'(\w+)\s*=\s*len\s+(\w+)', line)
            if match:
                # Treat as unary operation with 'len' operator
                return AssignInstruction(match.group(1), match.group(2), 'len')

            # Try unary: x = op y
            match = re.match(r'(\w+)\s*=\s*(-|!)\s*(\S+)', line)
            if match:
                return AssignInstruction(match.group(1), match.group(3), match.group(2))

            # Try simple assignment: x = y
            match = re.match(r'(\w+)\s*=\s*(.+)', line)
            if match:
                return AssignInstruction(match.group(1), match.group(2).strip())

        return None

    def _generate_header(self):
        """Generate MIPS file header."""
        self.function_translator.emit_comment("=" * 60)
        self.function_translator.emit_comment("MIPS Assembly Code")
        self.function_translator.emit_comment("Generated by CompilScript Compiler")
        self.function_translator.emit_comment("=" * 60)
        self.function_translator.emit_comment("")

    def _extract_string_literals(self, tac_instructions: List):
        """
        Pre-process TAC instructions to extract string literals.
        Adds them to data_manager and replaces in-place references.
        """
        for instr in tac_instructions:
            if isinstance(instr, PushParamInstruction):
                # Check if parameter is a string literal
                if self.data_manager.is_string_literal(instr.param):
                    # Add to data section and get label
                    label = self.data_manager.add_string_literal(instr.param)
                    # Replace with label reference
                    instr.param = label
            elif isinstance(instr, AssignInstruction):
                # Check for string operands in assignments
                if instr.operand1 and self.data_manager.is_string_literal(instr.operand1):
                    label = self.data_manager.add_string_literal(instr.operand1)
                    instr.operand1 = label
                if instr.operand2 and self.data_manager.is_string_literal(instr.operand2):
                    label = self.data_manager.add_string_literal(instr.operand2)
                    instr.operand2 = label
            elif isinstance(instr, ReturnInstruction):
                # Check if return value is a quoted string literal (not a variable)
                if (instr.value and
                    isinstance(instr.value, str) and
                    instr.value.startswith('"') and
                    instr.value.endswith('"')):
                    # Add to data section and get label
                    label = self.data_manager.add_string_literal(instr.value)
                    # Replace with label reference
                    instr.value = label

    def _register_classes_from_tac(self, tac_instructions: List):
        """
        Pre-process TAC comments to register class layouts.

        Looks for patterns like:
        # Class: ClassName
        # Field: fieldName
        # Field: fieldName2
        # Extends: ParentClass

        Classes can inherit fields from parent classes.
        """
        current_class = None
        current_fields = []
        current_parent = None
        all_classes = {}  # Store class info: {name: {'fields': [...], 'parent': '...'}}

        for instr in tac_instructions:
            if isinstance(instr, CommentInstruction):
                comment = instr.comment.strip()

                # Check for "# Class: ClassName"
                if comment.startswith("Class:"):
                    # Save previous class
                    if current_class is not None:
                        all_classes[current_class] = {
                            'fields': current_fields,
                            'parent': current_parent
                        }

                    # Start new class
                    current_class = comment.split(":", 1)[1].strip()
                    current_fields = []
                    current_parent = None

                # Check for "# Field: fieldName"
                elif comment.startswith("Field:") and current_class:
                    field_name = comment.split(":", 1)[1].strip()
                    current_fields.append(field_name)

                # Check for "# Extends: ParentClass"
                elif comment.startswith("Extends:") and current_class:
                    current_parent = comment.split(":", 1)[1].strip()

        # Save last class
        if current_class is not None:
            all_classes[current_class] = {
                'fields': current_fields,
                'parent': current_parent
            }

        # Now register classes with inheritance
        for class_name, class_info in all_classes.items():
            fields = class_info['fields'][:]  # Copy fields
            parent = class_info['parent']

            # Inherit fields from parent
            if parent and parent in all_classes:
                parent_fields = all_classes[parent]['fields']
                # Add parent fields at the beginning
                fields = parent_fields + fields

            # Register the class
            self.class_translator.register_class(class_name, fields)

    def _generate_data_section(self):
        """Generate .data section with string literals and arrays."""
        # Generate data section from data_manager
        data_nodes = self.data_manager.generate_data_section()
        for node in data_nodes:
            self.function_translator.data_section.append(node)

    def _generate_text_section(self, tac_instructions: List):
        """Generate .text section with code."""
        self.function_translator.emit_text(MIPSDirective(".text", ()))
        self.function_translator.emit_text(MIPSDirective(".globl", ("main",)))
        self.function_translator.emit_text(MIPSComment(""))

        # Separate global code from function definitions
        global_code = []
        function_code = []
        in_function = False

        for instr in tac_instructions:
            if isinstance(instr, BeginFuncInstruction):
                in_function = True
                function_code.append(instr)
            elif isinstance(instr, EndFuncInstruction):
                function_code.append(instr)
                in_function = False  # Exit function mode after EndFunc
            elif in_function:
                function_code.append(instr)
            else:
                global_code.append(instr)

        # Emit main label first
        self.function_translator.emit_label("main")
        self.function_translator.emit_comment("Main program")

        # Initialize stack pointer (required for SPIM)
        # MIPS convention: stack grows downward from high memory
        # Set $sp to a safe high address (e.g., 0x7fffeffc)
        self.function_translator.emit_text(
            MIPSInstruction("li", ("$sp", "0x7fffeffc"), comment="initialize stack pointer")
        )

        # Allocate frame for main (for variable spills)
        # Use a fixed size large enough for most programs
        # Variables in main will be spilled relative to $fp
        main_frame_size = 2048  # Conservative size for main
        self.function_translator.emit_text(
            MIPSInstruction("addi", ("$sp", "$sp", f"-{main_frame_size}"),
                          comment=f"allocate frame for main ({main_frame_size} bytes)")
        )

        self.function_translator.emit_text(
            MIPSInstruction("move", ("$fp", "$sp"), comment="set frame pointer")
        )

        # Translate global code (inside main)
        for instr in global_code:
            self._translate_instruction(instr)

        # Add exit syscall
        self.function_translator.emit_comment("Program exit")
        self.function_translator.emit_text(MIPSInstruction("li", ("$v0", "10"), comment="exit"))
        self.function_translator.emit_text(MIPSInstruction("syscall", ()))

        # Now translate function definitions
        self.function_translator.emit_comment("")
        self.function_translator.emit_comment("User-defined functions")
        for instr in function_code:
            self._translate_instruction(instr)

    def _generate_runtime_functions(self):
        """Generate runtime library functions."""
        runtime_nodes = RuntimeLibrary.generate_all_runtime_functions()
        for node in runtime_nodes:
            self.function_translator.text_section.append(node)

    def _translate_instruction(self, instr):
        """Translate a single TAC instruction to MIPS."""
        # Debug: print instruction type
        # print(f"Translating: {type(instr).__name__}: {instr}")

        if isinstance(instr, BeginFuncInstruction):
            self.function_translator.translate_begin_func(instr)

        elif isinstance(instr, EndFuncInstruction):
            self.function_translator.translate_end_func(instr)

        elif isinstance(instr, PushParamInstruction):
            self.function_translator.translate_push_param(instr)

        elif isinstance(instr, CallInstruction):
            self.function_translator.translate_call(instr)

        elif isinstance(instr, PopParamsInstruction):
            self.function_translator.translate_pop_params(instr)

        elif isinstance(instr, ReturnInstruction):
            self.function_translator.translate_return(instr)

        elif isinstance(instr, LabelInstruction):
            self.function_translator.emit_label(instr.label)

            # CRITICAL FOR LOOPS: Clear register associations after labels to force
            # variables to be reloaded from memory. This ensures loop variables maintain
            # consistent values across iterations, especially after jumps from loop updates.
            # Labels like for_cond, while_start, do_start are loop entry points where
            # we need to reload spilleaded variables to get updated values.
            label_name = instr.label.lower()
            is_loop_header = any(keyword in label_name for keyword in [
                'for_cond', 'while_start', 'do_start', 'foreach_start'
            ])

            if is_loop_header:
                # For loop headers, clear ALL register associations to force reloads
                # This is conservative but ensures correctness
                for reg in list(self.function_translator.register_allocator.register_descriptor.registers()):
                    state = self.function_translator.register_allocator.register_descriptor.state(reg)
                    for var in list(state.variables):
                        # Don't clear constants and labels
                        if not (var.startswith('_const_') or var.startswith('_label_') or var.startswith('_ctrl_temp')):
                            self.function_translator.address_descriptor.unbind_register(var, reg)
                    # Keep the register itself available but clear variable associations
                    if not state.pinned:
                        self.function_translator.register_allocator.register_descriptor.dissociate(reg)

        elif isinstance(instr, GotoInstruction):
            self.control_flow_translator.translate_goto(instr)

        elif isinstance(instr, ConditionalGotoInstruction):
            self.control_flow_translator.translate_conditional_goto(instr)

        elif isinstance(instr, AssignInstruction):
            self.expression_translator.translate_assignment(instr)

        elif isinstance(instr, NewInstruction):
            self.class_translator.translate_new_object(instr)

        elif isinstance(instr, PropertyAccessInstruction):
            self.class_translator.translate_property_access(instr)

        elif isinstance(instr, CommentInstruction):
            self.function_translator.emit_comment(instr.comment)

        elif isinstance(instr, AllocateArrayInstruction):
            self.expression_translator.translate_allocate_array(instr)

        elif isinstance(instr, ArrayAccessInstruction):
            self.expression_translator.translate_array_access(instr)

    def _nodes_to_string(self, nodes: List) -> str:
        """Convert MIPS nodes to assembly string."""
        lines = []

        # Separate data and text sections
        data_nodes = []
        text_nodes = []
        current_section = None

        for node in nodes:
            if isinstance(node, MIPSDirective):
                if node.directive == ".data":
                    current_section = "data"
                    data_nodes.append(node)
                elif node.directive == ".text":
                    current_section = "text"
                    text_nodes.append(node)
                else:
                    if current_section == "data":
                        data_nodes.append(node)
                    else:
                        text_nodes.append(node)
            else:
                if current_section == "data":
                    data_nodes.append(node)
                else:
                    text_nodes.append(node)

        # Generate data section
        if data_nodes:
            lines.append(".data")
            for node in data_nodes:
                if not (isinstance(node, MIPSDirective) and node.directive == ".data"):
                    lines.append(str(node))
            lines.append("")

        # Generate text section
        if text_nodes:
            lines.append(".text")
            for node in text_nodes:
                if not (isinstance(node, MIPSDirective) and node.directive == ".text"):
                    lines.append(str(node))

        return "\n".join(lines)

    def get_optimization_stats(self) -> Optional[OptimizationStats]:
        """Get statistics about applied optimizations."""
        return self.optimization_stats

    def get_statistics(self) -> Dict:
        """Get comprehensive statistics about code generation."""
        stats = {
            "optimization_enabled": self.enable_optimization,
        }

        if self.optimization_stats:
            stats["optimizations"] = {
                "total": self.optimization_stats.total_optimizations(),
                "redundant_loads_removed": self.optimization_stats.redundant_loads_removed,
                "dead_stores_removed": self.optimization_stats.dead_stores_removed,
                "algebraic_simplifications": self.optimization_stats.algebraic_simplifications,
                "strength_reductions": self.optimization_stats.strength_reductions,
                "constants_folded": self.optimization_stats.constants_folded,
                "jumps_optimized": self.optimization_stats.jumps_optimized,
                "unreachable_removed": self.optimization_stats.unreachable_removed,
                "redundant_moves_removed": self.optimization_stats.redundant_moves_removed,
                "passes_executed": self.optimization_stats.passes_executed,
            }

        return stats
