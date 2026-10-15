#!/usr/bin/env python3
"""Generate the #175 template and stylesheet files from the instance dumps.

Reads .scratch/175/dt-<id>.html (the four faces' LiveCanvas templates as the
blogs instance stores them) and writes the repository files into
.scratch/175/out/ for review, then (with --apply) into the plugin tree.

Transformations, and nothing else:
  - the legacy authoring comment goes; a repository comment takes its place
  - the <style> block goes (it becomes the WindPress volume file)
  - inline style= attributes go (their declarations become volume rules)
  - href="/{Field name}/" becomes href="{Field url}"
  - the instance host in absolute URLs goes: /wp-content/... stays relative,
    the JSON-LD urls become the <site url /> tag
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
INSTANCE = "http://127.0.0.1:9027"

FACES = {
    "blog_index": {
        "en": "574",
        "de": "6881",
        "meta": "is_blog_posts_index",
        "css": "blog-index.css",
        "en_comment": """<!--
  Blog posts index, English.

  LiveCanvas assigns this template with the `is_blog_posts_index` meta and
  `present` installs it (Templates::FILES); the German twin carries
  content/livecanvas/de/blog_index.html (Templates::DE_FILES). Composition is
  this file — styling is the WindPress volume file blog-index.css, installed by
  the same run; no style block belongs here.

  The face is the live blog index as the 2026-10-15 captures render it. The
  article links are `{Field url}`: the post's own permalink, which the language
  layer resolves, so a German article's card points at its /de/ address. The
  live template wrote the slug under the site root (`{Field name}` inside a
  root-relative href), which on the German face is a link out of the German
  tree and into a 404 (#175).

  The structured data is the live block, with the site address printed by
  [linker_site_url] instead of the authoring instance's host: the live template
  carried the host it was written on, which a file in this tree cannot (every
  instance renders its own), and a `<script>` block is where the template
  engine's own tags do not resolve.
-->""",
        "de_comment": """<!--
  Blog posts index, German.

  The German twin of content/livecanvas/blog_index.html, written by the same
  `present` run onto the English template's Polylang twin. Same composition,
  German words; styling is the WindPress volume file blog-index.css. The
  article links are `{Field url}` here too — the face that made the missing
  language prefix a 404 (#175).
-->""",
    },
    "search": {
        "en": "619",
        "de": "6875",
        "meta": "is_search",
        "css": "blog-search.css",
        "en_comment": """<!--
  Blog search results, English.

  LiveCanvas assigns this template with the `is_search` meta and `present`
  installs it (Templates::FILES); the German twin carries
  content/livecanvas/de/search.html (Templates::DE_FILES). Composition is this
  file — styling is the WindPress volume file blog-search.css, installed by the
  same run; no style block belongs here.

  The face is the live search results page as the 2026-10-15 captures render
  it. The result cards link `{Field url}`, the post's own permalink, so a
  German result points inside the German tree; the live template wrote the
  slug under the site root (`{Field name}` inside a root-relative href) and
  sent every German result to a 404 (#175).
-->""",
        "de_comment": """<!--
  Blog search results, German.

  The German twin of content/livecanvas/search.html, written by the same
  `present` run onto the English template's Polylang twin. Same composition,
  German words; styling is the WindPress volume file blog-search.css.
-->""",
    },
    "category_archive": {
        "en": "607",
        "de": "6879",
        "meta": "is_archive_for_tax_category",
        "css": "blog-category.css",
        "en_comment": """<!--
  Blog category archive, English.

  LiveCanvas assigns this template with the `is_archive_for_tax_category` meta
  and `present` installs it (Templates::FILES); the German twin carries
  content/livecanvas/de/category_archive.html (Templates::DE_FILES).
  Composition is this file — styling is the WindPress volume file
  blog-category.css, installed by the same run; no style block belongs here.

  The face is the live category archive as the 2026-10-15 captures render it.
  The feed cards link `{Field url}`, the post's own permalink, so an article of
  a German category links its /de/ address; the live template wrote the slug
  under the site root (`{Field name}` inside a root-relative href) and every
  card on the five German archives led to a 404 (#175).
-->""",
        "de_comment": """<!--
  Blog category archive, German.

  The German twin of content/livecanvas/category_archive.html, written by the
  same `present` run onto the English template's Polylang twin. Same
  composition, German words; styling is the WindPress volume file
  blog-category.css. The feed cards are the ten article links #175 is about.
-->""",
    },
}

# Inline declarations the templates carried, each one a rule in the face's
# volume file. Selector specificity has to reach the element the inline style
# sat on: an id-scoped path per module, the way the face's own rules are drawn.
INLINE_RULES = {
    "blog_index": """/* --- Declarations the live markup carried inline. Same selectors' elements,
   same declarations; the tree keeps styles in this volume, not in the
   template. --- */
#tv-blog-index-v1 #tv-blog-latest .tv-blog-featured-card {
  display: block; text-decoration: none;
}
#tv-blog-index-v1 #tv-blog-latest .tv-blog-featured-link svg {
  width: 0.875rem; height: 0.875rem;
}
#tv-blog-index-v1 #tv-blog-latest .tv-blog-compact-arrow svg {
  width: 1rem; height: 1rem;
}
#tv-blog-index-v1 #tv-blog-latest .tv-blog-inquiry-text {
  margin-left: 0.5rem;
}
#tv-blog-index-v1 #tv-blog-latest .tv-blog-btn-primary svg {
  width: 0.875rem; height: 0.875rem;
}
#tv-blog-index-v1 #tv-blog-practical .tv-blog-practical-arrow svg {
  width: 0.875rem; height: 0.875rem;
}
#tv-blog-index-v1 #tv-blog-practical .tv-blog-guide-card {
  display: block; text-decoration: none;
}
#tv-blog-index-v1 #tv-blog-editorial .tv-blog-editorial-link svg {
  width: 0.875rem; height: 0.875rem;
}
#tv-blog-index-v1 #tv-blog-browse .tv-blog-search-sm svg {
  width: 1.125rem; height: 1.125rem;
}
#tv-blog-index-v1 #tv-blog-resources .tv-blog-section-heading {
  margin-bottom: 1.75rem;
}
#tv-blog-index-v1 #tv-blog-resources .tv-blog-resource-link-label svg {
  width: 0.75rem; height: 0.75rem;
}
#tv-blog-index-v1 #tv-blog-final .tv-blog-btn-primary-lg svg {
  width: 1rem; height: 1rem;
}
""",
    "search": """/* --- Declarations the live markup carried inline. Same selectors' elements,
   same declarations; the tree keeps styles in this volume, not in the
   template. --- */
#tv-blog-search-v1 #tv-blog-search-masthead .tv-blog-search-form svg {
  width: 1.25rem; height: 1.25rem;
}
#tv-blog-search-v1 #tv-blog-search-cta .tv-blog-search-btn-cta-secondary svg {
  width: 1rem; height: 1rem;
}
""",
    "category_archive": """/* --- Declarations the live markup carried inline. Same selectors' elements,
   same declarations; the tree keeps styles in this volume, not in the
   template. --- */
#tv-blog-category-v1 #tv-blog-cat-feed .tv-blog-feed-arrow svg {
  width: 0.75rem; height: 0.75rem;
}
#tv-blog-category-v1 #tv-blog-resources .tv-blog-section-heading {
  margin-bottom: 2.5rem;
}
#tv-blog-category-v1 #tv-blog-resources .tv-blog-resource-link-label svg {
  width: 0.75rem; height: 0.75rem;
}
""",
}

CSS_COMMENT = """/*
 * {title} (content/livecanvas/{file} and its German twin).
 *
 * The rules are the {face} as the live site carries it: every selector is
 * scoped to #{root}, so they reach that one template and nothing else on the
 * site. They came out of the template's own style block so that the face
 * follows this tree's rule — the template owns composition, this volume owns
 * component styling (the same split as blog.css for the blog single face).
{extra} */
"""

CSS_TITLES = {
    "blog_index": (
        "The blog posts index's styles",
        "blog_index.html",
        "blog index",
        "tv-blog-index-v1",
        "",
    ),
    "search": (
        "The blog search face's styles",
        "search.html",
        "search results page",
        "tv-blog-search-v1",
        "",
    ),
    "category_archive": (
        "The blog category archive's styles",
        "category_archive.html",
        "category archive",
        "tv-blog-category-v1",
        " * The one background image the face draws is root-relative here, so every\n * instance serves its own uploads.\n",
    ),
}

CSS_BANNER = """/* ============================================================
   The face's own rules. Every selector is scoped to
   #{root}; none reaches another face of the site.
============================================================ */"""

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}


def swap_webkit_pairs(css: str) -> str:
    """Put every `-webkit-` declaration before its standard twin.

    Lightning CSS (the WindPress compile) keeps the pair only in that order:
    with the standard declaration first it drops it and ships the prefixed one
    alone, and Chromium then computes `backdrop-filter: none` — the frosted
    panel loses its blur. The blog single face hit the same trap (its context
    card's pair was reordered when it moved into the volume).
    """
    pattern = re.compile(
        r"^([ \t]*)(?P<prop>[a-z-]+):(?P<value>[^;\n]*);\n"
        r"(?P<indent>[ \t]*)-webkit-(?P=prop):(?P<value2>[^;\n]*);$",
        re.M,
    )

    def swap(match: re.Match[str]) -> str:
        if match.group("value").strip() != match.group("value2").strip():
            return match.group(0)
        return (
            f"{match.group('indent')}-webkit-{match.group('prop')}:{match.group('value2')};\n"
            f"{match.group(1)}{match.group('prop')}:{match.group('value')};"
        )

    return pattern.sub(swap, css)


def dedent(css: str) -> str:
    """Drop the style block's own leading indentation, the way blog.css sits.

    Whitespace-insensitive for CSS: every line loses the same prefix, so the
    relative shape of blocks and media queries survives.
    """
    lines = css.split("\n")
    widths = [len(line) - len(line.lstrip(" ")) for line in lines if line.strip()]
    common = min(widths) if widths else 0
    return "\n".join(line[common:] if line.strip() else "" for line in lines)


def read_dump(template_id: str) -> str:
    return (HERE / f"dt-{template_id}.html").read_text(encoding="utf-8")


def style_block(html: str) -> str:
    match = re.search(r"<style[^>]*>(.*?)</style>", html, re.S)
    assert match, "no style block"
    return match.group(1)


def transform(html: str, german: bool) -> str:
    # The legacy authoring comment goes with its "Deploy:" instructions.
    html = html[html.index("<tangible") :]
    # The style block becomes the volume file.
    html = re.sub(r"\n?\s*<style[^>]*>.*?</style>", "", html, count=1, flags=re.S)
    # The article links become the post's own, language-resolved permalink.
    html = html.replace('href="/{Field name}/"', 'href="{Field url}"')
    # Inline declarations move to the volume; the attributes go.
    html = re.sub(r' style="[^"]*"', "", html)
    # The instance host cannot live in a repository file: uploads stay
    # root-relative (the engine and the browser both resolve them against the
    # site), the structured data names the site with the tag.
    html = html.replace(f'"{INSTANCE}/blog/"', '"[linker_site_url]blog/"')
    html = html.replace(f'"{INSTANCE}/"', '"[linker_site_url]"')
    html = html.replace(f"{INSTANCE}/wp-content/", "/wp-content/")
    assert INSTANCE not in html, "instance host left in the markup"
    # Keep the file's own line shape: no trailing blank lines, one newline.
    return html.rstrip() + "\n"


def main() -> int:
    apply = "--apply" in sys.argv
    out = HERE / "out"
    out.mkdir(exist_ok=True)
    for face, spec in FACES.items():
        for language, key in (("en", spec["en"]), ("de", spec["de"])):
            html = transform(read_dump(key), german=language == "de")
            comment = spec["en_comment" if language == "en" else "de_comment"]
            body = comment + "\n" + html
            name = "de/" + face if language == "de" else face
            target = out / f"{name}.html"
            target.parent.mkdir(exist_ok=True)
            target.write_text(body, encoding="utf-8")
            print(f"wrote {target.relative_to(REPO)} ({len(body)} bytes)")

        css = style_block(read_dump(spec["en"]))
        css = css.replace(f"{INSTANCE}/wp-content/", "/wp-content/")
        assert INSTANCE not in css, "instance host left in the stylesheet"
        # The legacy banner (and the design-system note it carried) is design
        # history; the face's own rules start at the banner this tree writes.
        banner = re.search(r"^(\s*/\* =+\s*\n(?:.*?\n)*?\s*=+ \*/)\n", css, re.M)
        assert banner, "no banner found"
        css = css[banner.end() :]
        css = css.replace(
            "--- shared typography (DS v1 eyebrow pattern; JetBrains Mono retired) ---",
            "--- shared typography ---",
        )
        # The band's design-system tag names a lineage, not the band. The
        # volume files describe what the rules draw.
        css = css.replace(
            "Linker DS v1 CTA band: navy -> deep-teal gradient, ring motif.",
            "The final CTA band: navy -> deep-teal gradient, ring motif.",
        )
        css = dedent(swap_webkit_pairs(css))
        title, file, face_label, root, extra = CSS_TITLES[face]
        header = CSS_COMMENT.format(title=title, file=file, face=face_label, root=root, extra=extra)
        styled = (
            header
            + "\n"
            + CSS_BANNER.format(root=root)
            + "\n"
            + css.strip()
            + "\n\n"
            + INLINE_RULES[face]
        )
        (out / spec["css"]).write_text(styled, encoding="utf-8")
        print(f"wrote {(out / spec['css']).relative_to(REPO)} ({len(styled)} bytes)")

    if apply:
        for path in sorted(out.rglob("*")):
            if not path.is_file():
                continue
            relative = path.relative_to(out)
            if relative.suffix == ".css":
                target = REPO / "plugins/linker-commerce/content/windpress" / relative.name
            else:
                target = REPO / "plugins/linker-commerce/content/livecanvas" / relative
            target.write_text(path.read_text(encoding="utf-8"), encoding="utf-8")
            print(f"applied {target.relative_to(REPO)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
