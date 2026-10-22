"""Reject drift and preserve content around the Installer tab-only correction."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "installer_scroll", Path(__file__).parents[1] / "repair-installer-initial-scroll.py"
)
assert spec and spec.loader
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)

CONTROLLER = """<script>
function tabSet(tabSelector, panelSelector, activeAttr) {
    function show(index) {
      if (tabs[index]) tabs[index].scrollIntoView({block:'nearest',inline:'nearest'});
    }
    tabs.forEach((tab, i) => {
      tab.addEventListener('click', () => show(i));
      tab.addEventListener('keydown', event => {
        show(next);
        tabs[next].focus();
      });
    });
    show(0);
}
</script>"""
BEFORE = (
    '<main id="installer-journal"><p>Current copy. Grüße. \\u003c</p>'
    + CONTROLLER
    + "</main>"
)


def test_preserves_copy_other_scripts_and_initial_selection() -> None:
    surrounding = "<script>unrelated.show(0);</script><style>p{color:green}</style>"
    fixed = installer.repair(BEFORE + surrounding)
    assert fixed.split("<script>", 1)[0] == BEFORE.split("<script>", 1)[0]
    assert fixed.endswith("</main>" + surrounding)
    assert "    show(0);" in fixed
    assert "tabs[next].focus();" in fixed
    assert fixed.count("\\") == BEFORE.count("\\")
    assert installer.repair(fixed) == fixed


@pytest.mark.parametrize(
    "content",
    [
        BEFORE.replace('id="installer-journal"', 'id="other-page"'),
        BEFORE.replace("function tabSet(", "function otherTabs("),
        BEFORE.replace("    show(0);", "    show(1);"),
        BEFORE.replace("show(next);", "show(next, true);"),
        BEFORE + CONTROLLER,
        BEFORE.replace("tab.addEventListener('click', () => show(i));", ""),
    ],
)
def test_rejects_unrelated_partial_or_ambiguous_controller(content: str) -> None:
    with pytest.raises(ValueError):
        installer.repair(content)
