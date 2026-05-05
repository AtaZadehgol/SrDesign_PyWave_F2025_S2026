"""
Safe equation evaluator for user-defined expressions on field data.

Uses Python's ast module to validate expressions against a whitelist
before evaluation. Prevents code injection by restricting allowed
node types and identifiers.
"""

import ast
import numpy as np
from typing import Dict, Tuple, List, Optional, Set


class EquationEngine:
    """
    Safely evaluates mathematical expressions over named numpy arrays.

    Usage:
        engine = EquationEngine({"Ex": ex_array, "Hz": hz_array})
        result = engine.evaluate("-Ex/Hz")
    """

    ALLOWED_FUNCTIONS = {
        "abs": np.abs,
        "real": np.real,
        "imag": np.imag,
        "angle": np.angle,
        "conj": np.conj,
        "sqrt": np.sqrt,
        "log": np.log,
        "log10": np.log10,
        "exp": np.exp,
        "sin": np.sin,
        "cos": np.cos,

        "mean": np.mean,
        "max": np.max,
        "min": np.min,
        "sum": np.sum,
        "std": np.std,
    }

    ALLOWED_CONSTANTS = {
        "pi": np.pi,
        "e": np.e,
    }

    _OPTIONAL_SUBSCRIPT_NODES = tuple(
        node_type
        for node_type in (getattr(ast, "Index", None), getattr(ast, "ExtSlice", None))
        if node_type is not None
    )

    ALLOWED_NODE_TYPES = (
        ast.Expression,
        ast.BinOp,
        ast.UnaryOp,
        ast.Call,
        ast.Name,
        ast.Constant,
        ast.Add,
        ast.Sub,
        ast.Mult,
        ast.Div,
        ast.Pow,
        ast.USub,
        ast.UAdd,
        ast.Load,

        ast.Subscript,
        ast.Slice,
        ast.Tuple,
    ) + _OPTIONAL_SUBSCRIPT_NODES

    def __init__(
        self,
        variables: Dict[str, np.ndarray],
        unavailable_variables: Optional[Set[str]] = None,
    ):
        self.variables = dict(variables)
        self.unavailable_variables = set(unavailable_variables or set())

    def validate(self, expression: str) -> Tuple[bool, str]:
        """
        Validate that an expression is safe to evaluate.

        Returns:
            (True, "") if valid, (False, reason) if invalid.
        """
        if not expression or not expression.strip():
            return False, "Expression is empty"

        try:
            tree = ast.parse(expression, mode="eval")
        except SyntaxError as exc:
            return False, f"Syntax error: {exc}"

        allowed_names = (
            set(self.variables.keys())
            | set(self.ALLOWED_FUNCTIONS.keys())
            | set(self.ALLOWED_CONSTANTS.keys())
        )

        for node in ast.walk(tree):
            if not isinstance(node, self.ALLOWED_NODE_TYPES):
                return False, f"Disallowed operation: {type(node).__name__}"

            if isinstance(node, ast.Name) and node.id not in allowed_names:
                if node.id in self.unavailable_variables:
                    return False, f"Variable unavailable (not selected): '{node.id}'"
                return False, f"Unknown variable or function: '{node.id}'"

            if isinstance(node, ast.Call):
                if not isinstance(node.func, ast.Name):
                    return False, "Only direct function calls are allowed"
                if node.func.id not in self.ALLOWED_FUNCTIONS:
                    return False, f"Unknown function: '{node.func.id}'"

            # Validate subscript operations (array indexing)
            if isinstance(node, ast.Subscript):
                # Only allow subscripting on variable names
                if not isinstance(node.value, ast.Name):
                    return False, "Only variables can be indexed"
                if node.value.id not in self.variables:
                    return False, f"Cannot index non-variable: '{node.value.id}'"

                var_name = node.value.id
                var_data = np.asarray(self.variables[var_name])
                if var_data.ndim > 1:
                    slice_node = node.slice
                    if hasattr(ast, "Index") and isinstance(slice_node, ast.Index):
                        slice_node = slice_node.value

                    # For 2D measurement arrays we store data as [point, time].
                    # Accept Var[i] or Var[i, :] and block time-first patterns.
                    if isinstance(slice_node, ast.Tuple) and len(slice_node.elts) == 2:
                        first_axis = slice_node.elts[0]
                        second_axis = slice_node.elts[1]

                        if hasattr(ast, "Index") and isinstance(first_axis, ast.Index):
                            first_axis = first_axis.value
                        if hasattr(ast, "Index") and isinstance(second_axis, ast.Index):
                            second_axis = second_axis.value

                        # Disallow selecting along time axis directly for plotting.
                        if isinstance(first_axis, ast.Slice):
                            return (
                                False,
                                f"For 2D variable '{var_name}', use '{var_name}[point_index]' or '{var_name}[point_index, :]'.",
                            )

        return True, ""

    def evaluate(self, expression: str) -> np.ndarray:
        """
        Validate and evaluate the expression, returning a numpy array.

        Raises:
            ValueError: if the expression is invalid or unsafe.
        """
        valid, reason = self.validate(expression)
        if not valid:
            raise ValueError(f"Invalid expression '{expression}': {reason}")

        # Provide a minimal __builtins__ dict. Numpy operations internally
        # need __import__ (for warnings) so we cannot set it to {}.
        # The AST validation above already ensures only safe identifiers
        # are referenced in the expression itself.
        safe_builtins = (
            {"__import__": __builtins__["__import__"]}
            if isinstance(__builtins__, dict)
            else {"__import__": __builtins__.__dict__["__import__"]}
        )

        namespace = {"__builtins__": safe_builtins}
        namespace.update(self.ALLOWED_FUNCTIONS)
        namespace.update(self.ALLOWED_CONSTANTS)
        namespace.update(self.variables)

        code = compile(expression, "<equation>", "eval")

        with np.errstate(divide="ignore", invalid="ignore"):
            result = eval(code, namespace)  # noqa: S307

        result = np.asarray(result, dtype=complex)

        # Mask division-by-zero artifacts
        result = np.where(np.isinf(result), np.nan, result)

        return result

    def get_available_names(self) -> List[str]:
        """Return list of variable names available for equations."""
        return sorted(self.variables.keys())

    def get_available_functions(self) -> List[str]:
        """Return list of function names available for equations."""
        return sorted(self.ALLOWED_FUNCTIONS.keys())
