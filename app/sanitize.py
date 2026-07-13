from typing import Optional

import nh3

# Covers the formatting actually used in existing brigade descriptions
# (p, br, b/strong, i/em, headings, lists, links) plus a couple of common
# extras (u, h4, ol, blockquote) for headroom.
ALLOWED_TAGS = {
    "p", "br", "b", "strong", "i", "em", "u",
    "h2", "h3", "h4", "ul", "ol", "li", "a", "section", "blockquote",
}
ALLOWED_ATTRIBUTES = {"a": {"href"}}
ALLOWED_URL_SCHEMES = {"http", "https", "mailto"}


def sanitize_html(html: Optional[str]) -> Optional[str]:
    """Strip everything except a small allowlist of formatting tags/attributes,
    so pasted HTML can't carry <script>, event-handler attributes, or javascript: links."""
    if not html:
        return html
    return nh3.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        url_schemes=ALLOWED_URL_SCHEMES,
    )
