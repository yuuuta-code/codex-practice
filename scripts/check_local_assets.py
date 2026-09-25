#!/usr/bin/env python3
"""Check local asset references in HTML and CSS files in one batch."""

import argparse
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit


CSS_URL = re.compile(r"url\(\s*(['\"]?)(.*?)\1\s*\)", re.IGNORECASE)
SKIP_SCHEMES = {"http", "https", "data", "mailto", "tel", "javascript"}


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.items = []

    def handle_starttag(self, tag, attrs):
        for key, value in attrs:
            if key in {"src", "href", "poster"} and value:
                self.items.append((self.getpos()[0], value))


def local_target(source, value, root):
    parsed = urlsplit(value.strip())
    if parsed.scheme.lower() in SKIP_SCHEMES or parsed.netloc or not parsed.path:
        return None
    path = unquote(parsed.path)
    if path.startswith("//"):
        return None
    return (root / path.lstrip("/") if path.startswith("/") else source.parent / path).resolve()


def check(root):
    errors = []
    files = sorted(p for p in root.rglob("*") if p.suffix.lower() in {".html", ".css"} and p.is_file() and ".git" not in p.parts)
    for source in files:
        content = source.read_text(encoding="utf-8")
        if source.suffix.lower() == ".html":
            parser = References()
            parser.feed(content)
            references = parser.items
        else:
            references = [(content.count("\n", 0, match.start()) + 1, match.group(2)) for match in CSS_URL.finditer(content)]
        for line, value in references:
            target = local_target(source, value, root)
            if target is not None and not target.is_file():
                errors.append(f"{source.relative_to(root)}:{line}: {value} が見つかりません")
    return files, errors


def main():
    arg_parser = argparse.ArgumentParser(description="HTML/CSS 内のローカルファイル参照を一括確認します")
    arg_parser.add_argument("directory", nargs="?", type=Path, default=Path(__file__).resolve().parents[1])
    args = arg_parser.parse_args()
    root = args.directory.resolve()
    if not root.is_dir():
        arg_parser.error(f"ディレクトリがありません: {root}")
    files, errors = check(root)
    for error in errors:
        print(error, file=sys.stderr)
    print(f"{len(files)} ファイルを確認、参照切れ {len(errors)} 件")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
