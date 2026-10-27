"""The de-linker checkout `linker-local` runs from: what it links and copies into an instance."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Checkout:
    root: Path

    @classmethod
    def here(cls) -> Checkout:
        """The checkout containing this package (uv installs it editable from tools/local/src)."""
        root = Path(__file__).resolve().parents[4]
        if not (root / "tools" / "local" / "pyproject.toml").is_file():
            raise RuntimeError(
                f"{root} is not a de-linker checkout; run linker-local through "
                "`just` or `uv run --project tools/local`"
            )
        return cls(root)

    def plugins(self) -> list[Path]:
        """Our plugins, `plugins/linker-*`, each symlinked into an instance."""
        return sorted(
            path for path in (self.root / "plugins").glob("linker-*") if path.is_dir()
        )

    def mu_plugins(self) -> list[Path]:
        """The local-only mu-plugins, copied into every instance."""
        return sorted((self.root / "tools" / "local" / "mu").glob("*.php"))

    def production_mu_plugins(self) -> list[Path]:
        """The production must-use plugins (`mu-plugins/*.php`), copied into every instance."""
        return sorted((self.root / "mu-plugins").glob("*.php"))

    def theme_files(self) -> list[Path]:
        """This checkout's files inside the live theme, `themes/<slug>/<file>`."""
        themes = self.root / "themes"
        if not themes.is_dir():
            return []
        return sorted(path for path in themes.rglob("*") if path.is_file())

    @property
    def router(self) -> Path:
        return self.root / "tools" / "local" / "router.php"

    def service(self, name: str) -> Path:
        return self.root / "services" / name

    @property
    def engine_compatibility(self) -> Path:
        """The common bootstrap contract; managed feeds pin their own sibling."""
        return self.root / "plugins/linker-commerce/data/compatibility.json"

    def engine_contract(self, feed: Path) -> Path:
        """Use the same complete managed generation as Services, or bootstrap."""
        generation = feed.resolve().parent
        return (
            generation / "compatibility.json"
            if (generation / "manifest.json").is_file()
            else self.engine_compatibility
        )
