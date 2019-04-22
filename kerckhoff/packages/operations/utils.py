from bleach.sanitizer import Cleaner
from html5lib.filters.base import Filter
from urllib.parse import parse_qs, urlparse
import re

TAGS = ["a", "p", "span", "em", "strong"]
ATTRS = {"span": ["style"], "a": ["href"]}
STYLES = ["font-weight", "font-style", "text-decoration"]


class KeepOnlyInterestingSpans(Filter):
    drop_next_close = False

    def _style_is_boring(self, prop, value):
        boring_styles = {
            "font-weight": ["400", "normal"],
            "text-decoration": ["none"],
            "font-style": ["normal"],
        }

        return value in boring_styles.get(prop, [])

    def _reduce_to_interesting_styles(self, token):
        styles = token["data"].get((None, "style"))
        if styles is not None:
            final_styles = ""
            for prop, value in re.findall(r"([-\w]+)\s*:\s*([^:;]*)", styles):
                if not self._style_is_boring(prop, value):
                    final_styles += "%s:%s;" % (prop, value)
            token["data"][(None, "style")] = final_styles
            return final_styles
        return ""

    def __iter__(self):
        for token in Filter.__iter__(self):
            if token["type"] == "StartTag" and token["name"] == "span":
                if not token["data"]:
                    drop_next_close = True
                    continue

                reduced_styles = self._reduce_to_interesting_styles(token)
                # print("final:", token)
                if reduced_styles == "":
                    drop_next_close = True
                    continue
            elif (
                token["type"] == "EndTag"
                and token["name"] == "span"
                and drop_next_close
            ):
                drop_next_close = False
                continue
            yield (token)


class ConvertPTagsToNewlines(Filter):
    NEWLINE_TOKEN = {"type": "Characters", "data": "\n"}

    def __iter__(self):
        for token in Filter.__iter__(self):
            if token["type"] == "StartTag" and token["name"] == "p":
                continue
            elif token["type"] == "EndTag" and token["name"] == "p":
                yield (self.NEWLINE_TOKEN)
                continue
            yield (token)


class RemoveGoogleTrackingFromHrefs(Filter):
    def __iter__(self):
        for token in Filter.__iter__(self):
            if token["type"] == "StartTag" and token["name"] == "a" and token["data"]:
                url = token["data"].get((None, "href"))
                if url is not None:
                    actual_url = parse_qs(urlparse(url).query).get("q")
                    if actual_url is not None and len(actual_url) > 0:
                        token["data"][(None, "href")] = actual_url[0]
            yield (token)


GoogleDocHTMLCleaner: Cleaner = Cleaner(
    tags=TAGS,
    attributes=ATTRS,
    styles=STYLES,
    strip=True,
    filters=[
        KeepOnlyInterestingSpans,
        ConvertPTagsToNewlines,
        RemoveGoogleTrackingFromHrefs,
    ],
)

