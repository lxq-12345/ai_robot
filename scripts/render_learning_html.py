#!/usr/bin/env python3
"""Render a learning Markdown source into a standalone reading page."""

from __future__ import annotations

import argparse
import html
from pathlib import Path
import re

try:
    import markdown
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing Markdown renderer. Install with: "
        "/usr/bin/python3 -m pip install --user -r "
        "scripts/requirements-learning.txt"
    ) from exc


PAGE_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="color-scheme" content="light">
  <title>{title}</title>
  <style>
    :root {{
      --ink: #17212b;
      --muted: #586875;
      --line: #d9e0e5;
      --surface: #ffffff;
      --page: #f3f5f7;
      --accent: #176b87;
      --accent-soft: #e8f3f7;
      --code: #f6f8fa;
      --note: #fff7d6;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      color: var(--ink);
      background: var(--page);
      font-family: "Noto Sans CJK SC", "Microsoft YaHei", "PingFang SC",
        system-ui, -apple-system, sans-serif;
      font-size: 17px;
      line-height: 1.75;
      letter-spacing: 0;
    }}
    .topbar {{
      position: sticky;
      top: 0;
      z-index: 10;
      display: flex;
      align-items: center;
      justify-content: space-between;
      min-height: 54px;
      padding: 8px 24px;
      color: #ffffff;
      background: #243540;
      border-bottom: 3px solid #2f92a8;
    }}
    .topbar strong {{ font-size: 15px; }}
    .topbar button {{
      min-height: 36px;
      padding: 6px 12px;
      color: #ffffff;
      background: transparent;
      border: 1px solid #9eb0ba;
      border-radius: 5px;
      cursor: pointer;
      font: inherit;
      font-size: 14px;
    }}
    .layout {{
      display: grid;
      grid-template-columns: minmax(210px, 260px) minmax(0, 860px);
      gap: 32px;
      justify-content: center;
      align-items: start;
      width: min(100% - 32px, 1180px);
      margin: 28px auto 56px;
    }}
    .toc {{
      position: sticky;
      top: 82px;
      max-height: calc(100vh - 105px);
      overflow: auto;
      padding: 18px 18px 18px 6px;
      border-right: 1px solid var(--line);
      font-size: 14px;
      line-height: 1.5;
    }}
    .toc::before {{
      display: block;
      margin-bottom: 10px;
      color: var(--muted);
      font-weight: 700;
      content: "本章目录";
    }}
    .toc ul {{
      margin: 0;
      padding-left: 18px;
    }}
    .toc li {{ margin: 6px 0; }}
    .toc a {{
      color: #365260;
      text-decoration: none;
    }}
    .toc a:hover {{ color: var(--accent); text-decoration: underline; }}
    .toc-mobile {{ display: none; }}
    article {{
      min-width: 0;
      padding: 38px 52px 56px;
      background: var(--surface);
      border: 1px solid var(--line);
      border-radius: 6px;
      box-shadow: 0 4px 18px rgb(38 55 66 / 8%);
    }}
    h1, h2, h3 {{
      scroll-margin-top: 76px;
      line-height: 1.35;
      letter-spacing: 0;
    }}
    h1 {{
      margin: 0 0 24px;
      padding-bottom: 18px;
      font-size: 34px;
      border-bottom: 2px solid #2f92a8;
    }}
    h2 {{
      margin: 42px 0 18px;
      padding-bottom: 8px;
      font-size: 26px;
      border-bottom: 1px solid var(--line);
    }}
    h3 {{ margin: 30px 0 12px; font-size: 21px; }}
    p {{ margin: 12px 0; }}
    a {{ color: #086b8a; overflow-wrap: anywhere; }}
    blockquote {{
      margin: 18px 0;
      padding: 12px 18px;
      color: #394b55;
      background: var(--accent-soft);
      border-left: 4px solid var(--accent);
    }}
    blockquote p {{ margin: 3px 0; }}
    code {{
      padding: 2px 5px;
      background: var(--code);
      border: 1px solid #e4e9ed;
      border-radius: 4px;
      font-family: "Cascadia Code", "Noto Sans Mono CJK SC", monospace;
      font-size: 0.9em;
      overflow-wrap: anywhere;
    }}
    pre {{
      overflow: auto;
      margin: 18px 0;
      padding: 18px;
      background: #202b33;
      border-radius: 6px;
      line-height: 1.55;
    }}
    pre code {{
      padding: 0;
      color: #eef3f5;
      background: transparent;
      border: 0;
      overflow-wrap: normal;
    }}
    .table-wrap {{ width: 100%; overflow-x: auto; margin: 18px 0; }}
    table {{
      width: 100%;
      min-width: 620px;
      border-collapse: collapse;
      font-size: 15px;
    }}
    th, td {{
      padding: 10px 12px;
      vertical-align: top;
      text-align: left;
      border: 1px solid var(--line);
    }}
    th {{ background: #edf2f4; }}
    article img {{
      display: block;
      width: 100%;
      height: auto;
      margin: 26px auto 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #f6f8fa;
    }}
    hr {{ border: 0; border-top: 1px solid var(--line); }}
    .headerlink {{
      margin-left: 8px;
      color: #8aa0aa;
      text-decoration: none;
      font-weight: 400;
    }}
    .footer {{
      margin-top: 48px;
      padding-top: 18px;
      color: var(--muted);
      border-top: 1px solid var(--line);
      font-size: 14px;
    }}
    @media (max-width: 860px) {{
      .topbar {{ padding: 8px 14px; }}
      .layout {{
        display: block;
        width: min(100% - 20px, 760px);
        margin-top: 14px;
      }}
      .toc-desktop {{ display: none; }}
      .toc-mobile {{
        display: block;
        margin-bottom: 14px;
        padding: 13px 16px;
        background: #ffffff;
        border: 1px solid var(--line);
        border-radius: 6px;
        font-size: 14px;
      }}
      .toc-mobile summary {{
        color: #365260;
        cursor: pointer;
        font-weight: 700;
      }}
      .toc-mobile ul {{ padding-left: 20px; }}
      .toc-mobile li {{ margin: 6px 0; }}
      .toc-mobile a {{ color: #365260; text-decoration: none; }}
      article {{ padding: 28px 22px 40px; }}
      h1 {{ font-size: 29px; }}
      h2 {{ font-size: 23px; }}
      h3 {{ font-size: 19px; }}
      .headerlink {{ display: none; }}
    }}
    @media print {{
      body {{ background: #ffffff; font-size: 11pt; }}
      .topbar, .toc, .toc-mobile {{ display: none; }}
      .layout {{ display: block; width: 100%; margin: 0; }}
      article {{ padding: 0; border: 0; box-shadow: none; }}
      a {{ color: #000000; text-decoration: none; }}
      pre {{ white-space: pre-wrap; }}
      h2, h3 {{ break-after: avoid; }}
      table, img, pre {{ break-inside: avoid; }}
    }}
  </style>
</head>
<body>
  <header class="topbar">
    <strong>ROS 2仿真机器人教材</strong>
    <button type="button" onclick="window.print()">打印 / 保存为PDF</button>
  </header>
  <div class="layout">
    {desktop_toc}
    {mobile_toc}
    <article>
      {content}
      <div class="footer">源文件：{source_name} · 生成器：scripts/render_learning_html.py</div>
    </article>
  </div>
</body>
</html>
"""


def wrap_tables(document: str) -> str:
    return re.sub(
        r"(<table>.*?</table>)",
        r'<div class="table-wrap">\1</div>',
        document,
        flags=re.DOTALL,
    )


def render(source: Path, output: Path) -> None:
    source_text = source.read_text(encoding="utf-8")
    title_match = re.search(r"^#\s+(.+)$", source_text, flags=re.MULTILINE)
    title = title_match.group(1).strip() if title_match else source.stem
    render_text = re.sub(r"^\[TOC\]\s*$", "", source_text, flags=re.MULTILINE)

    converter = markdown.Markdown(
        extensions=["extra", "sane_lists", "toc"],
        extension_configs={"toc": {"permalink": True, "toc_depth": "2-3"}},
        output_format="html5",
    )
    content = wrap_tables(converter.convert(render_text))
    toc = converter.toc or "<p>本章无目录</p>"
    toc_inner = re.sub(r'^<div class="toc">|</div>$', "", toc.strip())
    desktop_toc = f'<nav class="toc toc-desktop">{toc_inner}</nav>'
    mobile_toc = (
        '<details class="toc-mobile"><summary>展开本章目录</summary>'
        f"{toc_inner}</details>"
    )

    page = PAGE_TEMPLATE.format(
        title=html.escape(title),
        desktop_toc=desktop_toc,
        mobile_toc=mobile_toc,
        content=content,
        source_name=html.escape(source.name),
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(page, encoding="utf-8", newline="\n")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render a project learning Markdown file as HTML."
    )
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    render(args.source.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
