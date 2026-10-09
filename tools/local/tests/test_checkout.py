from linker_local.checkout import Checkout


def test_finds_the_checkout_and_what_it_puts_into_an_instance() -> None:
    checkout = Checkout.here()

    assert (checkout.root / "AGENTS.md").is_file()
    assert [plugin.name for plugin in checkout.plugins()] == [
        "linker-commerce",
        "linker-i18n",
        "linker-tools",
    ]
    assert [mu.name for mu in checkout.mu_plugins()] == [
        "000-linker-local-isolation.php",
        "001-linker-local-login.php",
        "002-linker-local-rewrites.php",
    ]
    assert checkout.router.is_file()
    assert (checkout.service("genie") / "pyproject.toml").is_file()
