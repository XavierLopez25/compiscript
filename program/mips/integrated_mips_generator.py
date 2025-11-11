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
)

from .function_translator import FunctionTranslator
from .expression_translator import ExpressionTranslator
from .control_flow_translator import ControlFlowTranslator
from .class_translator import ClassTranslator
from .peephole_optimizer import PeepholeOptimizer, OptimizationStats
from .instruction import MIPSInstruction, MIPSLabel, MIPSComment, MIPSDirective


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

        # Create function translator (base translator)
        self.function_translator = FunctionTranslator()

        # Create other translators, passing function_translator as the base
        self.expression_translator = ExpressionTranslator(self.function_translator)
        self.control_flow_translator = ControlFlowTranslator(self.function_translator)
        self.class_translator = ClassTranslator()

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
        # Generate header
        self._generate_header()

        # Generate data section
        self._generate_data_section()

        # Generate text section
        self._generate_text_section(tac_instructions)

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

        # Assignment: x = y op z, x = op y, x = y
        elif '=' in line:
            # Try binary: x = y op z
            match = re.match(r'(\w+)\s*=\s*(\S+)\s+(\+|-|\*|/|%|==|!=|<|>|<=|>=|&&|\|\||str_concat)\s+(\S+)', line)
            if match:
                return AssignInstruction(match.group(1), match.group(2), match.group(3), match.group(4))

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

    def _generate_data_section(self):
        """Generate .data section with global variables."""
        self.function_translator.emit_data(MIPSDirective(".data", ()))
        # Global variables would be declared here
        # For now, we'll handle them dynamically as needed

    def _generate_text_section(self, tac_instructions: List):
        """Generate .text section with code."""
        self.function_translator.emit_text(MIPSDirective(".text", ()))
        self.function_translator.emit_text(MIPSDirective(".globl", ("main",)))
        self.function_translator.emit_text(MIPSComment(""))

        # Translate each TAC instruction
        for instr in tac_instructions:
            self._translate_instruction(instr)

        # Add program exit if we have a main-like structure
        if not any(isinstance(node, MIPSLabel) and node.name == "main"
                   for node in self.function_translator.text_section):
            # Create a main label
            self.function_translator.emit_label("main")

        # Add exit syscall at the end
        self.function_translator.emit_comment("Program exit")
        self.function_translator.emit_text(MIPSInstruction("li", ("$v0", "10"), comment="exit"))
        self.function_translator.emit_text(MIPSInstruction("syscall", ()))

    def _translate_instruction(self, instr):
        """Translate a single TAC instruction to MIPS."""
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
