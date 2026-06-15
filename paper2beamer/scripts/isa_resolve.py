"""Compose a theme's effective ISA from its declared extensions + the base set.

A theme file is thin: it declares which versioned extensions it `provides:`.
This module loads those extension specs and the shared base-primitive allowlist
and unions them into one EffectiveISA that both the agent (to generate) and the
conformance linter (to verify) consume. Pure, deterministic, no LLM.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import jsonschema
import yaml


@dataclass(frozen=True)
class EffectiveISA:
    """The fully-composed contract for one theme."""

    theme: str
    aspectratio: str
    engine: str
    allowed_macros: frozenset
    allowed_environments: frozenset
    macro_argspecs: dict  # name -> pylatexenc args spec, e.g. "{" or "[["
    env_argspecs: dict
    blocks_requiring_title: frozenset
    options: dict  # name -> option record
    structural_idioms: tuple = ()
    capacity: dict = field(default_factory=dict)
    lowering: dict = field(default_factory=dict)
    prose: str = ""


def _argspec(instr: dict) -> str:
    """Translate an instruction's arg counts into a pylatexenc spec string."""
    return "[" * int(instr.get("optional_args", 0)) + "{" * int(instr.get("args", 0))


def _load_yaml(path: Path) -> dict:
    if not path.is_file():
        raise FileNotFoundError(f"ISA file not found: {path}")
    return yaml.safe_load(path.read_text())


def _validate(instance, schema: dict, defname: str) -> None:
    """Validate against a named $def while keeping $defs reachable for $ref."""
    jsonschema.validate(
        instance,
        {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$ref": f"#/$defs/{defname}",
            "$defs": schema["$defs"],
        },
    )


def resolve(theme: str, isa_dir) -> EffectiveISA:
    """Build the EffectiveISA for `theme` from files under `isa_dir`."""
    isa_dir = Path(isa_dir)
    schema = json.loads((isa_dir / "isa.schema.json").read_text())

    theme_data = _load_yaml(isa_dir / f"{theme}.yaml")
    _validate(theme_data, schema, "theme")

    base = _load_yaml(isa_dir / "_base_latex.yaml")
    _validate(base, schema, "base_allowlist")

    macros: set = set(base["allowed_macros"])
    envs: set = set(base["allowed_environments"])
    macro_argspecs: dict = {}
    env_argspecs: dict = {}
    blocks_requiring_title: set = set()
    lowering: dict = {}

    for token in theme_data["provides"]:
        name = token.split("@")[0]
        ext = _load_yaml(isa_dir / "extensions" / f"{name}.yaml")
        _validate(ext, schema, "extension")
        lowering.update(ext.get("lowering", {}))
        for instr in ext.get("instructions", []):
            macros.add(instr["cmd"])
            macro_argspecs[instr["cmd"]] = _argspec(instr)
        for env in ext.get("environments", []):
            envs.add(env["env"])
            env_argspecs[env["env"]] = _argspec(env)
            if env.get("requires_title"):
                blocks_requiring_title.add(env["env"])

    for instr in theme_data.get("custom_instructions", []):
        macros.add(instr["cmd"])
        macro_argspecs[instr["cmd"]] = _argspec(instr)

    options = {o["name"]: o for o in theme_data.get("options", [])}

    return EffectiveISA(
        theme=theme_data["meta"]["theme"],
        aspectratio=theme_data["meta"]["aspectratio"],
        engine=theme_data["meta"]["engine"],
        allowed_macros=frozenset(macros),
        allowed_environments=frozenset(envs),
        macro_argspecs=macro_argspecs,
        env_argspecs=env_argspecs,
        blocks_requiring_title=frozenset(blocks_requiring_title),
        options=options,
        structural_idioms=tuple(theme_data.get("structural_idioms", [])),
        capacity=theme_data.get("capacity", {}),
        lowering=lowering,
        prose=theme_data.get("prose", ""),
    )
