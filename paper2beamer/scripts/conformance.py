"""Static ISA-conformance linter (runs after assembly, before the build).

Parses each emitted frame fragment with pylatexenc, using arg-specs generated
from the resolved ISA so custom commands parse correctly, and checks that the
deck uses only what the theme's contract declares. Conservative: anything it
cannot resolve statically becomes a warn, never a silent pass.
"""
from __future__ import annotations

import re

from pylatexenc.latexwalker import (
    LatexWalker,
    LatexMacroNode,
    LatexEnvironmentNode,
    LatexGroupNode,
    LatexCharsNode,
)
from pylatexenc.macrospec import LatexContextDb, MacroSpec, EnvironmentSpec

from scripts.isa_resolve import EffectiveISA
from scripts.latex_log import Violation

_USETHEME = re.compile(r"\\usetheme\[(?P<opts>[^\]]*)\]\{(?P<name>\w+)\}")


def _context(eff: EffectiveISA) -> LatexContextDb:
    """Build a pylatexenc context so declared custom commands parse their args."""
    db = LatexContextDb()
    macros = [MacroSpec(name, spec) for name, spec in eff.macro_argspecs.items()]
    envs = [EnvironmentSpec(name, spec) for name, spec in eff.env_argspecs.items()]
    db.add_context_category("isa", macros=macros, environments=envs, prepend=True)
    db.set_unknown_macro_spec(MacroSpec("", ""))
    db.set_unknown_environment_spec(EnvironmentSpec("", ""))
    return db


def _title_is_empty(env_node: LatexEnvironmentNode) -> bool:
    """True if a block environment's title argument is absent or blank."""
    argd = env_node.nodeargd
    if argd is None or not argd.argnlist:
        return True
    first = argd.argnlist[0]
    if first is None:
        return True
    if isinstance(first, LatexGroupNode):
        text = "".join(
            n.chars for n in first.nodelist if isinstance(n, LatexCharsNode)
        )
        return text.strip() == ""
    return False


def _walk(nodes, eff, slide_id, out):
    """Recurse the node tree collecting conformance violations."""
    for node in nodes:
        if isinstance(node, LatexMacroNode):
            name = node.macroname
            if name and name not in eff.allowed_macros:
                out.append(Violation(slide_id, "undeclared_instruction",
                                     f"\\{name} not in ISA", "error"))
        elif isinstance(node, LatexEnvironmentNode):
            env = node.environmentname
            if env not in eff.allowed_environments:
                out.append(Violation(slide_id, "undeclared_instruction",
                                     f"environment {env} not in ISA", "error"))
            elif env in eff.blocks_requiring_title and _title_is_empty(node):
                out.append(Violation(slide_id, "block_without_title",
                                     f"{env} has no title", "error"))
            if node.nodelist:
                _walk(node.nodelist, eff, slide_id, out)
        # Descend into groups so nested content is checked too.
        if isinstance(node, LatexGroupNode) and node.nodelist:
            _walk(node.nodelist, eff, slide_id, out)
        nested = getattr(node, "nodeargd", None)
        if nested is not None and nested.argnlist:
            _walk([a for a in nested.argnlist if a is not None],
                  eff, slide_id, out)


def _check_preamble(eff: EffectiveISA, preamble: str, out: list) -> None:
    """Check the \\usetheme options against the declared option contract."""
    for m in _USETHEME.finditer(preamble):
        opts = {}
        for pair in m.group("opts").split(","):
            pair = pair.strip()
            if not pair:
                continue
            k, _, v = pair.partition("=")
            opts[k.strip()] = v.strip()
        for k, v in opts.items():
            spec = eff.options.get(k)
            if spec is None:
                out.append(Violation(None, "bad_option",
                                     f"unknown \\usetheme option '{k}'", "error"))
                continue
            allowed = spec.get("values")
            if allowed and v not in allowed:
                out.append(Violation(None, "bad_option",
                                     f"option {k}={v} not in {allowed}", "error"))
        for name, spec in eff.options.items():
            req = spec.get("required_value")
            if req is not None and opts.get(name) != req:
                out.append(Violation(None, "bad_option",
                                     f"{name} must be {req}", "error"))


def check(eff: EffectiveISA, frames: dict, preamble: str = "") -> tuple:
    """Lint a deck's fragments + preamble against the effective ISA."""
    out: list = []
    db = _context(eff)
    for slide_id, text in frames.items():
        walker = LatexWalker(text, latex_context=db)
        nodelist, _, _ = walker.get_latex_nodes()
        _walk(nodelist, eff, slide_id, out)
    if preamble:
        _check_preamble(eff, preamble, out)
    return tuple(out)
