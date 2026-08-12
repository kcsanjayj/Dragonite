from __future__ import annotations

import ast
import operator


# ============================================================
# CALCULATOR
# ============================================================

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def _evaluate(node: ast.AST) -> float:

    if isinstance(node, ast.Constant):

        if isinstance(
            node.value,
            (int, float),
        ):
            return node.value

        raise ValueError(
            "Only numeric values are allowed."
        )

    if isinstance(
        node,
        ast.UnaryOp,
    ):

        operation = _ALLOWED_OPERATORS.get(
            type(node.op)
        )

        if operation is None:
            raise ValueError(
                "Unsupported unary operator."
            )

        return operation(
            _evaluate(node.operand)
        )

    if isinstance(
        node,
        ast.BinOp,
    ):

        operation = _ALLOWED_OPERATORS.get(
            type(node.op)
        )

        if operation is None:
            raise ValueError(
                "Unsupported binary operator."
            )

        left = _evaluate(
            node.left
        )

        right = _evaluate(
            node.right
        )

        return operation(
            left,
            right,
        )

    raise ValueError(
        "Unsupported expression."
    )


def calculator(
    expression: str,
) -> dict:

    """
    Safely evaluate basic arithmetic.
    """

    tree = ast.parse(
        expression,
        mode="eval",
    )

    result = _evaluate(
        tree.body
    )

    return {
        "expression": expression,
        "result": result,
    }


# ============================================================
# TEXT
# ============================================================

def text_length(
    text: str,
) -> dict:

    return {
        "length": len(text),
        "characters": len(text),
        "words": len(
            text.split()
        ),
    }


# ============================================================
# TOOL REGISTRATION
# ============================================================

def register_builtin_tools(
    registry,
) -> None:

    registry.register(
        name="calculator",
        description=(
            "Evaluate a basic arithmetic expression."
        ),
        function=calculator,
    )

    registry.register(
        name="text_length",
        description=(
            "Count characters and words in text."
        ),
        function=text_length,
    )