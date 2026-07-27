"""Strips Jekyll/Liquid templating markup from Home Assistant's docs source.

The corpus is the actual Jekyll source of home-assistant.io, not rendered
HTML, so it's full of build-time tags: {% term %}, {% note %}...{% endnote %},
{% include ... %}, and so on. Left in, they pollute both the embedded text
(hurting retrieval) and anything read aloud to a caller.

The one trap: Home Assistant's own automation examples use Jinja templates
that also use {% if %}/{% endif %} syntax, shown inside ```yaml fences. Those
are real content, not Jekyll markup, and must survive untouched — so fenced
code blocks are protected before any tag stripping happens.
"""

import re

_CODE_FENCE_RE = re.compile(r"```.*?```", re.DOTALL)
_PLACEHOLDER = "\x00CODE_BLOCK_{}\x00"

# Block tags where we keep the inner content, optionally with a label.
_LABELED_BLOCKS = {
    "note": "Note",
    "important": "Important",
    "tip": "Tip",
    "warning": "Warning",
}
# Block tags whose wrapper is pure markup — inner content (config tables,
# examples) is real and kept verbatim, just unwrapped.
_TRANSPARENT_BLOCKS = ["configuration", "configuration_basic", "example"]


def _strip_block(text: str, tag: str, label: str | None) -> str:
    pattern = re.compile(
        r"\{%-?\s*" + tag + r"\s*-?%\}(.*?)\{%-?\s*end" + tag + r"\s*-?%\}", re.DOTALL
    )
    if label:
        return pattern.sub(lambda m: f"\n**{label}:** {m.group(1).strip()}\n", text)
    return pattern.sub(lambda m: m.group(1), text)


def clean_liquid_tags(text: str) -> str:
    # 0. {% raw %}/{% endraw %} is unambiguous Jekyll-only wrapper markup —
    #    it exists purely so Jekyll's own Liquid parser doesn't choke on the
    #    {{ }} inside a real Home Assistant Jinja example. Unlike {% if %}
    #    (which HA templates also use for real), "raw"/"endraw" never appear
    #    in genuine template content, so this is safe to strip even inside
    #    code fences — done before fence protection kicks in below.
    text = re.sub(r"\{%-?\s*raw\s*-?%\}", "", text)
    text = re.sub(r"\{%-?\s*endraw\s*-?%\}", "", text)

    # 1. Protect fenced code blocks so their {% %} syntax (real Jinja
    #    examples) is never touched.
    code_blocks: list[str] = []

    def stash(m: re.Match) -> str:
        code_blocks.append(m.group(0))
        return _PLACEHOLDER.format(len(code_blocks) - 1)

    text = _CODE_FENCE_RE.sub(stash, text)

    # 2. {% details "Title" %}...{% enddetails %} -> "**Title**\n\n<body>"
    text = re.sub(
        r'\{%-?\s*details\s+"([^"]*)"\s*-?%\}(.*?)\{%-?\s*enddetails\s*-?%\}',
        lambda m: f"\n**{m.group(1)}**\n\n{m.group(2).strip()}\n",
        text,
        flags=re.DOTALL,
    )

    for tag, label in _LABELED_BLOCKS.items():
        text = _strip_block(text, tag, label)
    for tag in _TRANSPARENT_BLOCKS:
        text = _strip_block(text, tag, None)

    # 3. {% term X %} / {% term "X" %} -> X (inline glossary link, keep the term)
    text = re.sub(r'\{%-?\s*term\s+"?([^"%]+?)"?\s*-?%\}', r"\1", text)

    # 4. {% if ... %} / {% endif %} outside code: drop the conditional
    #    wrapper, keep the body — losing the condition is an acceptable
    #    trade-off versus losing real content.
    text = re.sub(r"\{%-?\s*(?:end)?if\b[^%]*-?%\}", "", text)

    # 5. Tags with no useful inline content: drop entirely.
    for tag in ("include", "my", "icon"):
        text = re.sub(r"\{%-?\s*" + tag + r"\b[^%]*-?%\}", "", text)

    # 6. Anything left ({% raw %}, {% endraw %}, unknown tags) — strip the
    #    tag markers but keep whatever text was between them.
    text = re.sub(r"\{%-?\s*", "", text)
    text = re.sub(r"\s*-?%\}", "", text)

    # 7. Restore protected code blocks.
    for i, block in enumerate(code_blocks):
        text = text.replace(_PLACEHOLDER.format(i), block)

    # Collapse the blank-line runs left behind by removed block tags.
    return re.sub(r"\n{3,}", "\n\n", text).strip()
