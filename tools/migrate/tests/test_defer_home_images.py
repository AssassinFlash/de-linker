"""Guard the real image set and byte-preserving homepage content update."""

import importlib.util
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "defer_home_images", Path(__file__).parents[1] / "defer-home-images.py"
)
assert spec and spec.loader
repair = importlib.util.module_from_spec(spec)
spec.loader.exec_module(repair)
SOURCES = tuple("/wp-content/uploads/" + name for name in repair.PHOTO_PATHS)


def homepage() -> str:
    tags = [f'<img alt="EN &amp; Grüße > photo" src="{src}"/>' for src in SOURCES]
    tags[-1] = tags[-1].replace("/>", ' loading="lazy"/>')
    return '<main id="home-a">\n' + "\n".join(tags) + "\n</main>"


def test_preserves_copy_scripts_styles_escapes_and_sources() -> None:
    surrounding = r"""<!-- <img src="/not-a-photo"> -->
<style>.photo { background: url('/hero.webp'); }</style>
<script>var svg='\u003csvg>'; var text=/\s+/g; var fake='<img src="/fake">';</script>
<p>Grüße, installation &amp; compatibility. `literal` $(literal)</p>"""
    before = homepage() + surrounding
    after = repair.defer_images(before)
    assert after.count('loading="lazy"') == 16
    assert after.count('decoding="async"') == 16
    assert after.endswith(surrounding)
    # Drop only the added tokens: every other byte and slash must survive.
    restored = after.replace(' decoding="async"', "")
    for width, height in repair.PHOTO_SIZES:
        restored = restored.replace(f' width="{width}" height="{height}"', "")
    for src in SOURCES[:-1]:
        restored = restored.replace(f'src="{src}" loading="lazy"', f'src="{src}"')
    assert restored == before
    assert repair.defer_images(after) == after


@pytest.mark.parametrize(
    "before",
    [
        homepage().replace('id="home-a"', 'id="other"'),
        homepage().replace(SOURCES[0], "/new-photo.webp"),
        homepage().replace(
            '<img alt="EN &amp; Grüße > photo"', '<img loading="eager"', 1
        ),
        homepage().replace(
            '<img alt="EN &amp; Grüße > photo"', '<img decoding="sync"', 1
        ),
        homepage().replace(
            '<img alt="EN &amp; Grüße > photo"', '<img src="/ambiguous"', 1
        ),
        homepage().replace('<img ', '<img width="1599" ', 1),
        homepage().replace('<img ', '<img height="0" ', 1),
        homepage().replace('<img ', '<img width="100%" ', 1),
        homepage().replace('<img ', '<img height ', 1),
        homepage().replace("</main>", '<img src="/extra.webp"></main>'),
        homepage().replace("</main>", f'<img src="{SOURCES[0]}"></main>'),
    ],
)
def test_refuses_unknown_changed_or_ambiguous_image_contract(before: str) -> None:
    with pytest.raises(ValueError):
        repair.defer_images(before)


def test_preserves_quote_case_and_self_closing_spelling() -> None:
    before = homepage().replace(
        '<img alt="EN &amp; Grüße > photo"', "<IMG alt='Grüße > photo'"
    )
    after = repair.defer_images(before)
    assert after.count("<IMG alt='Grüße > photo'") == 16
    assert repair.defer_images(after) == after


def test_intrinsic_sizes_match_each_source_and_preserve_existing_attributes() -> None:
    before = homepage().replace('<img ', "<img WIDTH='1600' ", 1)
    after = repair.defer_images(before)
    assert after.startswith('<main id="home-a">\n<img WIDTH=\'1600\' ')
    parser = repair.HomeImages(after)
    parser.feed(after)
    parser.close()
    assert parser.edits == []
    assert parser.sources == repair.PHOTO_SOURCES
    for source, (width, height) in repair.PHOTO_DIMENSIONS.items():
        assert width > 0 and height > 0
        assert source in after
    assert after.count(' height="') == 16
    assert after.count(' width="') == 15
