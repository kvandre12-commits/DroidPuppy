#!/usr/bin/env python3
"""Generate docs/PLUGIN_REFERENCE.md by introspecting every plugin.

This keeps DroidPuppy's plugin docs from drifting: it walks
``code_puppy/plugins/``, parses each ``register_callbacks.py`` with the AST,
and extracts the registered agent tools plus the best available description.

Description precedence per tool:
    1. wrapper async-func docstring (register_callbacks.py)
    2. impl func docstring (tooling.py), including a ``<name>_impl`` alias
    3. a humanized version of the tool name (clearly marked as derived)

Run from the repo root:  python scripts/gen_plugin_reference.py
"""

from __future__ import annotations

import ast
import datetime
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
PLUGINS_DIR = REPO_ROOT / "code_puppy" / "plugins"
OUTPUT = REPO_ROOT / "docs" / "PLUGIN_REFERENCE.md"


def _first_line(doc: str | None) -> str:
    return (doc or "").strip().split("\n")[0].strip()


def _module_doc(path: pathlib.Path) -> str:
    if not path.is_file():
        return ""
    try:
        return _first_line(ast.get_docstring(ast.parse(path.read_text())))
    except SyntaxError:
        return ""


def _func_docs(path: pathlib.Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not path.is_file():
        return out
    try:
        tree = ast.parse(path.read_text())
    except SyntaxError:
        return out
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = _first_line(ast.get_docstring(node))
            if doc and node.name not in out:
                out[node.name] = doc
    return out


def _tool_names(rc_path: pathlib.Path) -> list[str]:
    names: list[str] = []
    tree = ast.parse(rc_path.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Attribute) and dec.attr.startswith("tool"):
                    names.append(node.name)
    return names


def _humanize(name: str) -> str:
    words = name.replace("android_", "", 1).split("_")
    return " ".join(words).capitalize() + " _(derived)_"


def _collect() -> list[tuple[str, str, list[tuple[str, str]]]]:
    plugins: list[tuple[str, str, list[tuple[str, str]]]] = []
    for plugin in sorted(PLUGINS_DIR.iterdir()):
        if not plugin.is_dir() or plugin.name.startswith(("_", ".")):
            continue
        rc = plugin / "register_callbacks.py"
        tl = plugin / "tooling.py"
        if not rc.is_file():
            continue
        desc = _module_doc(rc) or _module_doc(tl)
        rc_docs = _func_docs(rc)
        tl_docs = _func_docs(tl)
        tools: list[tuple[str, str]] = []
        for name in _tool_names(rc):
            doc = (
                rc_docs.get(name)
                or tl_docs.get(name)
                or tl_docs.get(name + "_impl")
                or _humanize(name)
            )
            tools.append((name, doc))
        plugins.append((plugin.name, desc, tools))
    return plugins


def _render(plugins: list[tuple[str, str, list[tuple[str, str]]]]) -> str:
    now = datetime.date.today().isoformat()
    total_tools = sum(len(t) for _, _, t in plugins)
    out: list[str] = [
        "# DroidPuppy Plugin Reference",
        "",
        "> Auto-generated inventory of every DroidPuppy plugin and its tools.",
        f"> Last generated: {now}. Regenerate with `python scripts/gen_plugin_reference.py`.",
        "> Descriptions marked _(derived)_ were synthesized from the tool name "
        "(the source had no docstring — a good first contribution target).",
        "",
        f"**{len(plugins)} plugins · {total_tools} tools**",
        "",
        "## Index",
        "",
    ]
    for name, desc, tools in plugins:
        anchor = name.replace("_", "-")
        out.append(f"- [`{name}`](#{anchor}) — {desc or 'Android plugin.'} ({len(tools)} tools)")
    out += ["", "---", ""]
    for name, desc, tools in plugins:
        out.append(f"## {name}")
        out.append("")
        if desc:
            out += [desc, ""]
        if tools:
            out += ["| Tool | Description |", "|------|-------------|"]
            out += [f"| `{tname}` | {tdoc} |" for tname, tdoc in tools]
        else:
            out.append("_No agent tools (passive/startup plugin)._")
        out.append("")
    return "\n".join(out) + "\n"


def main() -> None:
    plugins = _collect()
    OUTPUT.write_text(_render(plugins))
    total = sum(len(t) for _, _, t in plugins)
    print(f"Wrote {OUTPUT.relative_to(REPO_ROOT)}: {len(plugins)} plugins, {total} tools")


if __name__ == "__main__":
    main()
