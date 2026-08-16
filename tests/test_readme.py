import ast
import re
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
README = (REPOSITORY_ROOT / "README.md").read_text()
ADAPTER_SOURCE = (REPOSITORY_ROOT / "rawfilereader" / "adapter.py").read_text()


def test_all_public_adapter_methods_are_documented():
    module = ast.parse(ADAPTER_SOURCE)
    adapter = next(
        node
        for node in module.body
        if isinstance(node, ast.ClassDef) and node.name == "RawFileAdapter"
    )
    public_methods = {
        node.name
        for node in adapter.body
        if isinstance(node, ast.FunctionDef) and not node.name.startswith("_")
    }
    api_headings = "\n".join(re.findall(r"^#### (.+)$", README, re.MULTILINE))
    documented_methods = set(
        re.findall(r"`([A-Za-z_][A-Za-z0-9_]*)\s*(?:\(|->)", api_headings)
    )
    documented_methods.discard("RawFileAdapter")

    assert documented_methods == public_methods


def test_readme_python_examples_compile():
    python_blocks = re.findall(r"```python\n(.*?)```", README, re.DOTALL)

    assert python_blocks
    for index, source in enumerate(python_blocks, start=1):
        compile(source, f"README.md:python-block-{index}", "exec")


def test_is_open_is_documented_as_a_property():
    assert "is_open()" not in README
    assert "rf.is_open" in README
