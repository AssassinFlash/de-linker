from pathlib import Path

from linker_local import server
from linker_local.checkout import Checkout
from linker_local.instance import Instance


def test_php_ini_carries_productions_limits_and_logs_into_the_instance(
    tmp_path: Path,
) -> None:
    instance = Instance("a", 8888, 8889, 8890, tmp_path)

    ini = server.php_ini(instance).splitlines()

    for key, value in server.PRODUCTION_LIMITS.items():
        assert f"{key} = {value}" in ini
    assert f'error_log = "{tmp_path / "a" / "logs" / "php-error.log"}"' in ini
    assert "display_errors = Off" in ini


def test_install_writes_the_ini_and_copies_the_router(tmp_path: Path) -> None:
    instance = Instance("a", 8888, 8889, 8890, tmp_path)
    instance.dir.mkdir()

    server.install(instance, Checkout.here())

    assert instance.php_ini.read_text() == server.php_ini(instance)
    assert not instance.router.is_symlink()
    assert instance.router.read_bytes() == Checkout.here().router.read_bytes()
