#!/usr/bin/env python3
"""保险小红书图文方案：4 套方案 → 对比页 / 导出 / 快照。

用法：
    build_plan.py check    --plan outputs/<主题>/方案.json
    build_plan.py render   --plan outputs/<主题>/方案.json [--out ...] [--no-embed]
    build_plan.py export   --plan outputs/<主题>/方案.json --set 2 [--out ...]
    build_plan.py snapshot --plan outputs/<主题>/方案.json --label v1 [--force]

方案 JSON 字段见 references/plan-schema.md。脚本只做确定性拼装与检查，
不生成文案、不判断保险事实、不替代机构审核。
"""
from __future__ import annotations

import argparse
import base64
import html
import json
import os
import shutil
import struct
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
SHARED = ROOT / "skills" / "shared" / "scripts"
if str(SHARED) not in sys.path:
    sys.path.insert(0, str(SHARED))

from output_paths import OutputPathError, validate_output_path  # noqa: E402

SET_COUNT = 4
FACT_STATUS = {"已核", "待核实", "不适用"}
SET_STATUS = {"draft", "待确认", "已确认"}
IMAGE_SIZE_MIN = 1024


def _text(value) -> str:
    return value.strip() if isinstance(value, str) else ""


def _dict(value) -> dict:
    return value if isinstance(value, dict) else {}


def _list(value) -> list:
    return value if isinstance(value, list) else []


def _is_http(value: str) -> bool:
    return value.startswith("http://") or value.startswith("https://")


def _esc(value) -> str:
    return html.escape(str(value or ""), quote=True)


def _safe_name(value: str, fallback: str = "未命名") -> str:
    cleaned = "".join(
        char for char in (value or "")
        if char not in '\\/:*?"<>|\r\n\t' and ord(char) >= 32
    ).strip(" .")
    return (cleaned or fallback)[:60]


def _png_size(path: Path) -> tuple[int, int] | None:
    """Read PNG dimensions without Pillow; return None for other formats."""
    if path.suffix.lower() != ".png":
        return None
    try:
        with path.open("rb") as handle:
            head = handle.read(24)
    except OSError:
        return None
    if len(head) < 24 or head[:8] != b"\x89PNG\r\n\x1a\n" or head[12:16] != b"IHDR":
        return None
    return struct.unpack(">II", head[16:24])


def _guard(path: Path) -> Path:
    try:
        return validate_output_path(path)
    except OutputPathError as exc:
        raise SystemExit(f"ERROR: {exc}") from None


def load_plan(value: str) -> tuple[Path, dict]:
    path = Path(value).expanduser().resolve()
    if not path.is_file():
        raise SystemExit(f"ERROR: 方案文件不存在: {path}")
    try:
        plan = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        raise SystemExit(f"ERROR: 无法读取方案 JSON: {exc}") from None
    if not isinstance(plan, dict):
        raise SystemExit("ERROR: 方案 JSON 顶层必须是对象")
    return path, plan


def check_plan(plan: dict, base: Path) -> tuple[list[str], list[str]]:
    """Return (errors, warnings). Errors block render/export."""
    errors: list[str] = []
    warnings: list[str] = []
    sets = plan.get("sets")
    if not isinstance(sets, list):
        return ["缺少 sets 数组"], warnings
    if len(sets) != SET_COUNT:
        errors.append(f"sets 必须正好 {SET_COUNT} 套（当前 {len(sets)} 套）")

    ids: list = []
    titles: list[str] = []
    headlines: list[str] = []
    skeletons: list[str] = []
    situations: list[str] = []
    ref_total = 0
    fact_total = 0
    todo_total = 0

    for index, raw_set in enumerate(sets, 1):
        label = f"第 {index} 套"
        if not isinstance(raw_set, dict):
            errors.append(f"{label} 不是对象")
            continue
        sid = raw_set.get("id", index)
        if sid in ids:
            errors.append(f"{label} id 重复: {sid}")
        ids.append(sid)
        label = f"第 {index} 套（id={sid}）"

        angle = _dict(raw_set.get("angle"))
        for key, name in (
            ("name", "角度名"),
            ("reader_situation", "读者处境"),
            ("skeleton", "内容骨架"),
        ):
            if not _text(angle.get(key)):
                errors.append(f"{label} 缺少 angle.{key}（{name}）")
        skeletons.append(_text(angle.get("skeleton")))
        situations.append(_text(angle.get("reader_situation")))

        title = _dict(raw_set.get("title"))
        title_text = _text(title.get("text"))
        if not title_text:
            errors.append(f"{label} 缺少 title.text")
        else:
            titles.append(title_text)
            if len(title_text) > 24:
                warnings.append(
                    f"{label} 标题 {len(title_text)} 字，超过 24 字精简目标（不是平台硬规则）"
                )
        _check_refs(title, f"{label} 标题", errors, warnings)
        ref_total += len(_list(title.get("refs")))

        cover = _dict(raw_set.get("cover"))
        copy = _dict(cover.get("copy"))
        headline = _text(copy.get("headline"))
        if not headline:
            errors.append(f"{label} 缺少 cover.copy.headline（封面主文案）")
        else:
            headlines.append(headline)
        image = _text(cover.get("image"))
        if not image:
            errors.append(f"{label} 缺少 cover.image（封面图路径）")
        else:
            image_path = (base / image).resolve()
            if base not in image_path.parents:
                errors.append(f"{label} cover.image 必须位于方案目录内: {image}")
            elif not image_path.is_file():
                errors.append(f"{label} 封面图不存在: {image}")
            elif image_path.stat().st_size < IMAGE_SIZE_MIN:
                errors.append(f"{label} 封面图疑似空文件: {image}")
            else:
                size = _png_size(image_path)
                if size:
                    width, height = size
                    if height and abs(width / height - 0.75) > 0.02:
                        errors.append(
                            f"{label} 封面图不是 3:4（当前 {width}×{height}）"
                        )
                    if width < 1080:
                        warnings.append(
                            f"{label} 封面图宽 {width}px，低于 1080px 规格"
                        )
        _check_refs(cover, f"{label} 封面", errors, warnings)
        ref_total += len(_list(cover.get("refs")))

        body = _dict(raw_set.get("body"))
        body_text = _text(body.get("text"))
        if not body_text:
            errors.append(f"{label} 缺少 body.text")
        elif len(body_text) < 300:
            warnings.append(f"{label} 正文只有 {len(body_text)} 字，确认是否足够兑现标题")
        _check_refs(body, f"{label} 正文", errors, warnings)
        ref_total += len(_list(body.get("refs")))

        facts = _list(raw_set.get("facts"))
        fact_total += len(facts)
        for fact_index, raw_fact in enumerate(facts, 1):
            fact = _dict(raw_fact)
            statement = _text(fact.get("statement"))
            status = _text(fact.get("status"))
            if not statement:
                errors.append(f"{label} 事实 {fact_index} 缺少 statement")
            if status not in FACT_STATUS:
                errors.append(
                    f"{label} 事实 {fact_index} status 必须是 {'/'.join(sorted(FACT_STATUS))}"
                )
            elif status == "已核" and not _text(fact.get("basis")):
                errors.append(f"{label} 事实 {fact_index} 标为已核但缺少 basis")
            elif status == "待核实":
                todo_total += 1
                if not _text(fact.get("next_step")):
                    errors.append(f"{label} 事实 {fact_index} 待核实但缺少 next_step")

        status = _text(raw_set.get("status")) or "draft"
        if status not in SET_STATUS:
            warnings.append(f"{label} status={status!r} 不在 draft/待确认/已确认 内")

    for name, values, kind in (
        ("标题", titles, "title.text"),
        ("封面主文案", headlines, "cover.copy.headline"),
    ):
        seen: list[str] = []
        for value in values:
            if value in seen:
                errors.append(f"{kind} 重复，4 套不能只换词: {value}")
            seen.append(value)

    if skeletons:
        for skeleton in set(skeletons):
            count = skeletons.count(skeleton)
            if not skeleton:
                continue
            if count >= 3:
                errors.append(f"有 {count} 套都用「{skeleton}」骨架，角度没有真正分开")
            elif count == 2:
                warnings.append(f"有 2 套都用「{skeleton}」骨架，确认是否够不同")
    if situations and len(set(situations)) == 1:
        warnings.append("4 套的读者处境完全相同，检查是否只是换了表达方式")

    selected = plan.get("selected")
    if selected is not None and selected not in ids:
        errors.append(f"selected={selected!r} 不在 sets id 内")

    for index, raw_revision in enumerate(_list(plan.get("revisions")), 1):
        revision = _dict(raw_revision)
        if not _text(revision.get("instruction")):
            errors.append(f"修改记录 {index} 缺少 instruction")
        if revision.get("set") not in ids and revision.get("set") not in (None, "all"):
            errors.append(f"修改记录 {index} 指向不存在的 set: {revision.get('set')}")
        if not _list(revision.get("changed")):
            warnings.append(f"修改记录 {index} 没有 changed 列表")

    plan["_stats"] = {
        "refs": ref_total,
        "facts": fact_total,
        "todo": todo_total,
    }
    return errors, warnings


def _check_refs(block: dict, label: str, errors: list[str], warnings: list[str]) -> None:
    if not isinstance(block, dict):
        errors.append(f"{label} 缺失")
        return
    refs = block.get("refs")
    note = _text(block.get("refs_note"))
    if refs is None:
        refs = []
    if not isinstance(refs, list):
        errors.append(f"{label} refs 必须是数组")
        return
    if not refs and not note:
        errors.append(
            f"{label} 没有溯源：refs 为空时必须写 refs_note（如“无对标样本（原创）”）"
        )
    for index, raw_ref in enumerate(refs, 1):
        ref = _dict(raw_ref)
        if not _text(ref.get("title")):
            errors.append(f"{label} 溯源 {index} 缺少 title")
        url = _text(ref.get("url"))
        if not url:
            errors.append(f"{label} 溯源 {index} 缺少 url；没有链接就写进 refs_note")
        elif not _is_http(url):
            errors.append(f"{label} 溯源 {index} url 必须是 http(s) 链接: {url}")
        if not _text(ref.get("borrowed")):
            errors.append(f"{label} 溯源 {index} 缺少 borrowed（借鉴点）")
        if not _text(ref.get("checked")):
            warnings.append(f"{label} 溯源 {index} 没写 checked（核对到哪一步）")


def _pill_class(status: str) -> str:
    return {"已确认": "ok", "待确认": "todo"}.get(status, "draft")


def _refs_html(block: dict, empty_label: str) -> str:
    refs = _list(block.get("refs"))
    note = _text(block.get("refs_note"))
    if not refs:
        return f'<p class="note">{_esc(note or empty_label)}</p>'
    cards: list[str] = []
    for raw_ref in refs:
        ref = _dict(raw_ref)
        meta = " · ".join(
            part for part in (_text(ref.get("author")), _text(ref.get("date"))) if part
        )
        kind = _text(ref.get("kind")) or "案例"
        url = _text(ref.get("url"))
        title = _text(ref.get("title")) or url
        link = (
            f'<a href="{_esc(url)}" target="_blank" rel="noreferrer noopener">{_esc(title)}</a>'
            if _is_http(url)
            else _esc(title)
        )
        extra: list[str] = []
        if _text(ref.get("not_borrowed")):
            extra.append(f'<p class="dim"><span class="k">不搬</span>{_esc(ref.get("not_borrowed"))}</p>')
        if _text(ref.get("checked")):
            extra.append(f'<p class="dim"><span class="k">核对</span>{_esc(ref.get("checked"))}</p>')
        cards.append(
            '<div class="ref">'
            f'<div class="ref-top"><span class="ref-kind">{_esc(kind)}</span>{link}'
            f'<span class="ref-meta">{_esc(meta)}</span></div>'
            f'<p><span class="k">借鉴点</span>{_esc(ref.get("borrowed"))}</p>'
            + "".join(extra)
            + "</div>"
        )
    if note:
        cards.append(f'<p class="note">{_esc(note)}</p>')
    return "".join(cards)


def _facts_html(facts: list) -> str:
    if not facts:
        return (
            '<p class="note">本稿未列具体产品事实；如涉及责任、价格、核保或理赔结论，'
            "必须先补事实清单。</p>"
        )
    rows: list[str] = []
    for raw_fact in facts:
        fact = _dict(raw_fact)
        status = _text(fact.get("status")) or "待核实"
        css = {"已核": "ok", "待核实": "todo", "不适用": "na"}.get(status, "todo")
        basis = _text(fact.get("basis")) or _text(fact.get("next_step"))
        rows.append(
            "<tr>"
            f"<td>{_esc(fact.get('statement'))}</td>"
            f'<td><span class="pill {css}">{_esc(status)}</span></td>'
            f"<td>{_esc(basis)}</td>"
            f"<td>{_esc(fact.get('impact'))}</td>"
            "</tr>"
        )
    return (
        '<table class="facts"><thead><tr><th>陈述</th><th>状态</th>'
        "<th>依据 / 下一步</th><th>若为假影响哪句</th></tr></thead><tbody>"
        + "".join(rows)
        + "</tbody></table>"
    )


def _copy_html(copy: dict) -> str:
    blocks = _list(copy.get("blocks"))
    block_html = "".join(f"<li>{_esc(_block_text(item))}</li>" for item in blocks)
    return (
        '<div class="cover-copy">'
        f'<div class="cc-kicker">{_esc(copy.get("kicker"))}</div>'
        f'<div class="cc-headline">{_esc(copy.get("headline"))}</div>'
        f'<div class="cc-subline">{_esc(copy.get("subline"))}</div>'
        + (f'<ul class="cc-blocks">{block_html}</ul>' if block_html else "")
        + f'<div class="cc-footer">{_esc(copy.get("footer"))}</div>'
        "</div>"
    )


def _block_text(item) -> str:
    if isinstance(item, dict):
        return _text(item.get("text")) or _text(item.get("title"))
    return _text(item)


def _image_data(path: Path) -> str:
    mime = {
        ".png": "image/png",
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".webp": "image/webp",
    }.get(path.suffix.lower(), "image/png")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:{mime};base64,{encoded}"


CSS = """
:root{
  --paper:#f6f2ea; --surface:#fffdf8; --ink:#221f1b; --muted:#6b645b;
  --line:#ded6c8; --accent:#a64b36; --ok:#2f5a3f; --ok-bg:#e7efe6;
  --todo:#8a5c12; --todo-bg:#f7edd6; --na:#5f5a52; --na-bg:#eeeae2;
}
*{box-sizing:border-box}
body{
  margin:0;background:var(--paper);color:var(--ink);line-height:1.75;
  font-family:"Noto Sans CJK SC","Source Han Sans SC","PingFang SC","Microsoft YaHei",sans-serif;
  -webkit-font-smoothing:antialiased;
}
a{color:var(--accent);text-decoration:none;border-bottom:1px solid rgba(166,75,54,.35)}
a:hover{border-bottom-color:var(--accent)}
.wrap{max-width:1240px;margin:0 auto;padding:46px 28px 84px}
.kicker{letter-spacing:.26em;font-size:12px;color:var(--accent);font-weight:600}
h1,h2,h3{font-family:"Noto Serif CJK SC","Source Han Serif SC","Songti SC",serif;font-weight:600}
h1{font-size:42px;line-height:1.22;margin:12px 0 14px;letter-spacing:.01em}
h2{font-size:26px;margin:0 0 4px}
h3{font-size:15px;margin:0 0 10px;letter-spacing:.08em;color:var(--muted);font-weight:600}
.meta{display:flex;flex-wrap:wrap;gap:8px 20px;color:var(--muted);font-size:13px}
.meta b{color:var(--ink);font-weight:600}
.brief{margin:26px 0 8px;padding:18px 20px;background:var(--surface);border:1px solid var(--line);border-radius:4px}
.brief p{margin:4px 0;font-size:14px}
.brief .label{color:var(--muted);margin-right:8px}
.overview{width:100%;border-collapse:collapse;margin:26px 0 8px;background:var(--surface);border:1px solid var(--line)}
.overview th,.overview td{padding:11px 14px;border-bottom:1px solid var(--line);text-align:left;font-size:13px;vertical-align:top}
.overview th{background:#fbf8f1;color:var(--muted);font-weight:600;letter-spacing:.06em}
.overview tr:last-child td{border-bottom:none}
.set{background:var(--surface);border:1px solid var(--line);border-radius:4px;margin:34px 0;overflow:hidden}
.set.selected{border-color:var(--accent);box-shadow:0 0 0 1px var(--accent)}
.selected-mark{display:inline-block;margin-left:8px;padding:2px 9px;border-radius:999px;background:#f3e3dd;color:var(--accent);font-size:11px;letter-spacing:.06em}
.set-head{display:flex;align-items:center;gap:16px;padding:18px 24px;border-bottom:1px solid var(--line);background:#fbf8f1}
.set-no{font-family:"Noto Serif CJK SC",serif;font-size:30px;color:var(--accent);line-height:1;min-width:44px}
.set-head .grow{flex:1}
.set-head p{margin:2px 0 0;color:var(--muted);font-size:13px}
.set-body{display:grid;grid-template-columns:330px minmax(0,1fr);gap:28px;padding:26px}
.cover-wrap{margin:0;align-self:start}
.cover-wrap img{width:100%;display:block;border:1px solid var(--line);border-radius:2px;background:#efe9dd}
.cover-wrap figcaption{margin-top:8px;color:var(--muted);font-size:12px;line-height:1.6}
.content{min-width:0}
.block{padding:0 0 22px;margin-bottom:22px;border-bottom:1px dashed var(--line)}
.block:last-child{border-bottom:none;margin-bottom:0;padding-bottom:0}
.title-line{font-size:24px;line-height:1.45;margin:0 0 6px;font-weight:600}
.dim{color:var(--muted);font-size:13px}
.cover-copy{border:1px solid var(--line);background:#fbf8f1;padding:16px 18px;border-radius:3px}
.cc-kicker{font-size:11px;letter-spacing:.18em;color:var(--accent);margin-bottom:4px}
.cc-headline{font-family:"Noto Serif CJK SC",serif;font-size:24px;line-height:1.35;font-weight:600}
.cc-subline{font-size:14px;color:var(--muted);margin-top:4px}
.cc-blocks{margin:10px 0 0;padding-left:20px;font-size:13px}
.cc-blocks li{margin:2px 0}
.cc-footer{margin-top:10px;font-size:11px;color:var(--muted);letter-spacing:.08em}
.body-text{white-space:pre-wrap;word-break:break-word;font-size:14px;line-height:1.95}
.tags{margin:10px 0 0}
.tag{display:inline-block;margin:0 6px 6px 0;padding:2px 8px;border:1px solid var(--line);border-radius:999px;font-size:12px;color:var(--muted)}
.trace{margin-top:10px;border:1px solid var(--line);border-radius:3px;background:#fdfaf3}
.trace summary{cursor:pointer;padding:8px 12px;font-size:12px;color:var(--muted);letter-spacing:.06em}
.trace .refs{padding:0 12px 12px}
.ref{padding:10px 0;border-top:1px dashed var(--line)}
.ref-top{font-size:13px;line-height:1.7}
.ref-kind{display:inline-block;margin-right:8px;padding:1px 6px;background:#efe8da;color:#7a5a42;font-size:11px;border-radius:2px}
.ref-meta{color:var(--muted);font-size:12px;margin-left:8px}
.ref p{margin:5px 0 0;font-size:13px}
.k{display:inline-block;margin-right:8px;color:var(--muted);font-size:11px;letter-spacing:.08em}
.note{margin:8px 0 0;padding:8px 10px;background:#f4efe4;border-left:2px solid var(--accent);font-size:12px;color:var(--muted)}
.facts{width:100%;border-collapse:collapse;margin-top:4px;font-size:12.5px}
.facts th,.facts td{padding:8px 10px;border:1px solid var(--line);text-align:left;vertical-align:top}
.facts th{background:#fbf8f1;color:var(--muted);font-weight:600}
.pill{display:inline-block;padding:1px 8px;border-radius:999px;font-size:11px;white-space:nowrap}
.pill.ok{background:var(--ok-bg);color:var(--ok)}
.pill.todo{background:var(--todo-bg);color:var(--todo)}
.pill.na{background:var(--na-bg);color:var(--na)}
.pill.draft{background:#eeeae2;color:#5f5a52}
.revisions{margin-top:44px;padding-top:22px;border-top:1px solid var(--line)}
.rev{padding:12px 0;border-bottom:1px dashed var(--line);font-size:13px}
.rev:last-child{border-bottom:none}
.rev .round{display:inline-block;margin-right:10px;color:var(--accent);font-weight:600}
.foot{margin-top:40px;color:var(--muted);font-size:12px;line-height:1.8}
@media (max-width:880px){
  .wrap{padding:28px 16px 60px}
  h1{font-size:30px}
  .set-body{grid-template-columns:1fr;gap:20px}
  .cover-wrap{max-width:360px}
}
@media print{
  body{background:#fff}
  .wrap{max-width:none;padding:0}
  .set{break-inside:avoid;box-shadow:none}
  a{color:inherit;border-bottom:none}
}
"""


def build_html(plan: dict, base: Path, out_path: Path, embed: bool = True) -> str:
    brief = _dict(plan.get("brief"))
    style = _dict(plan.get("style"))
    sets = _list(plan.get("sets"))

    summary_rows: list[str] = []
    sections: list[str] = []
    for index, raw_set in enumerate(sets, 1):
        s = _dict(raw_set)
        sid = s.get("id", index)
        angle = _dict(s.get("angle"))
        title = _dict(s.get("title"))
        cover = _dict(s.get("cover"))
        copy = _dict(cover.get("copy"))
        body = _dict(s.get("body"))
        facts = _list(s.get("facts"))
        status = _text(s.get("status")) or "draft"
        is_selected = plan.get("selected") == sid
        image = _text(cover.get("image"))
        image_path = (base / image).resolve() if image else None
        if image_path and image_path.is_file():
            src = _image_data(image_path) if embed else os.path.relpath(
                image_path, out_path.parent
            ).replace("\\", "/")
            size = _png_size(image_path)
            size_label = f"{size[0]}×{size[1]}" if size else "3:4"
            cover_html = (
                f'<figure class="cover-wrap"><img src="{_esc(src)}" alt="第 {index} 套封面">'
                f"<figcaption>第 {index} 套封面 · {size_label}</figcaption></figure>"
            )
        else:
            cover_html = '<p class="note">封面图缺失，请先重渲染。</p>'

        summary_rows.append(
            "<tr>"
            f"<td>{_esc(sid)}</td>"
            f"<td>{_esc(angle.get('name'))}</td>"
            f"<td>{_esc(angle.get('skeleton'))}</td>"
            f"<td>{_esc(title.get('text'))}</td>"
            f'<td><span class="pill {_pill_class(status)}">{_esc(status)}</span>'
            + ('<span class="selected-mark">已选定</span>' if is_selected else "")
            + "</td>"
            "</tr>"
        )

        alternatives = _list(title.get("alternatives"))
        alt_html = (
            '<p class="dim">备选：' + " ／ ".join(_esc(x) for x in alternatives if _text(x)) + "</p>"
            if alternatives
            else ""
        )
        tags = _list(body.get("tags"))
        tag_html = "".join(f'<span class="tag">{_esc(tag)}</span>' for tag in tags if _text(tag))

        sections.append(
            f'<section class="set{" selected" if is_selected else ""}" id="set-{_esc(sid)}">'
            '<div class="set-head">'
            f'<div class="set-no">{index:02d}</div>'
            '<div class="grow"><h2>' + _esc(angle.get("name")) + "</h2>"
            "<p>" + _esc(angle.get("reader_situation")) + " · " + _esc(angle.get("search_intent")) + "</p></div>"
            f'<span class="pill {_pill_class(status)}">{_esc(status)}</span>'
            + ('<span class="selected-mark">已选定</span>' if is_selected else "")
            + "</div>"
            '<div class="set-body">'
            + cover_html
            + '<div class="content">'
            '<div class="block"><h3>标题</h3>'
            f'<p class="title-line">{_esc(title.get("text"))}</p>{alt_html}'
            f'<details class="trace" open><summary>标题溯源 · {len(_list(title.get("refs")))} 条</summary>'
            f'<div class="refs">{_refs_html(title, "无对标样本（原创）")}</div></details></div>'
            '<div class="block"><h3>封面文案</h3>'
            + _copy_html(copy)
            + f'<details class="trace" open><summary>封面溯源 · {len(_list(cover.get("refs")))} 条</summary>'
            f'<div class="refs">{_refs_html(cover, "无对标样本（原创）")}</div></details></div>'
            '<div class="block"><h3>正文</h3>'
            f'<div class="body-text">{_esc(body.get("text"))}</div>'
            f'<div class="tags">{tag_html}</div>'
            f'<details class="trace" open><summary>正文溯源 · {len(_list(body.get("refs")))} 条</summary>'
            f'<div class="refs">{_refs_html(body, "无对标样本（原创）")}</div></details></div>'
            '<div class="block"><h3>事实清单</h3>' + _facts_html(facts) + "</div>"
            "</div></div></section>"
        )

    brief_bits: list[str] = []
    if _text(brief.get("must_include")):
        brief_bits.append(f'<p><span class="label">必须包含</span>{_esc(brief.get("must_include"))}</p>')
    if _text(brief.get("audience")):
        brief_bits.append(f'<p><span class="label">目标人群</span>{_esc(brief.get("audience"))}</p>')
    if _text(brief.get("scenario")):
        brief_bits.append(f'<p><span class="label">使用场景</span>{_esc(brief.get("scenario"))}</p>')
    if _text(brief.get("tone")):
        brief_bits.append(f'<p><span class="label">语气</span>{_esc(brief.get("tone"))}</p>')
    assumptions = _list(brief.get("assumptions"))
    if assumptions:
        brief_bits.append(
            f'<p><span class="label">假设</span>{_esc("；".join(_text(x) for x in assumptions if _text(x)))}</p>'
        )

    revision_html = ""
    revisions = _list(plan.get("revisions"))
    if revisions:
        items: list[str] = []
        for raw_revision in revisions:
            revision = _dict(raw_revision)
            changed = "、".join(_text(x) for x in _list(revision.get("changed")) if _text(x))
            items.append(
                '<div class="rev">'
                f'<span class="round">第 {_esc(revision.get("round", "?"))} 轮</span>'
                f'方案 {_esc(revision.get("set"))} · {_esc(revision.get("instruction"))}'
                f'<div class="dim">改动：{_esc(changed or "未记录")}'
                f' · 快照：{_esc(revision.get("snapshot") or "未记录")}'
                f' · 状态：{_esc(revision.get("status") or "待确认")}</div>'
                "</div>"
            )
        revision_html = '<section class="revisions"><h2>修改记录</h2>' + "".join(items) + "</section>"
    else:
        revision_html = '<section class="revisions"><h2>修改记录</h2><p class="dim">尚未修改，当前为第 1 版。</p></section>'

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    style_name = _text(style.get("style_name"))
    route = _text(style.get("route"))
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_esc(plan.get("topic"))} · 4 套图文方案</title>
<style>{CSS}</style>
</head>
<body>
<div class="wrap">
<header>
  <div class="kicker">小红书图文方案 · 四选一</div>
  <h1>{_esc(plan.get("topic"))}</h1>
  <div class="meta">
    <span>生成 <b>{now}</b></span>
    <span>画像 <b>{_esc(plan.get("profile") or "通用")}</b></span>
    <span>视觉 <b>{_esc(style_name or route or "未登记")}</b></span>
    <span>状态 <b>工作草稿 · 待人工确认</b></span>
  </div>
</header>
<div class="brief">{''.join(brief_bits) or '<p class="dim">未登记创作简报。</p>'}</div>
<table class="overview">
<thead><tr><th>#</th><th>切入角度</th><th>骨架</th><th>标题</th><th>状态</th></tr></thead>
<tbody>{''.join(summary_rows)}</tbody>
</table>
{''.join(sections)}
{revision_html}
<p class="foot">本页由方案 JSON 生成，用于比较与人工确认，不是发布稿。参考案例只证明表达方式，不证明其中的保险结论、身份或转化；标为“待核实”的事实须在发布前补齐依据。封面文案与正文须一起核对，发布前按机构要求报备与审核。</p>
</div>
</body>
</html>
"""


def _md_refs(block: dict, label: str) -> list[str]:
    refs = _list(block.get("refs"))
    note = _text(block.get("refs_note"))
    lines = [f"### {label}"]
    if not refs:
        lines.append(f"- {note or '无对标样本（原创）'}")
        return lines
    for raw_ref in refs:
        ref = _dict(raw_ref)
        meta = "｜".join(
            part for part in (
                _text(ref.get("author")), _text(ref.get("date")), _text(ref.get("kind"))
            ) if part
        )
        title = _text(ref.get("title")) or _text(ref.get("url"))
        url = _text(ref.get("url"))
        lines.append(f"- [{title}]({url})" + (f"｜{meta}" if meta else ""))
        lines.append(f"  - 借鉴点：{_text(ref.get('borrowed')) or '未记录'}")
        if _text(ref.get("not_borrowed")):
            lines.append(f"  - 不搬：{_text(ref.get('not_borrowed'))}")
        if _text(ref.get("checked")):
            lines.append(f"  - 核对：{_text(ref.get('checked'))}")
    if note:
        lines.append(f"- 备注：{note}")
    return lines


def _md_cell(value) -> str:
    return _text(value).replace("|", "\\|").replace("\n", " ")


def build_markdown(plan: dict, selected: dict) -> str:
    sid = selected.get("id")
    angle = _dict(selected.get("angle"))
    title = _dict(selected.get("title"))
    cover = _dict(selected.get("cover"))
    copy = _dict(cover.get("copy"))
    body = _dict(selected.get("body"))
    facts = _list(selected.get("facts"))
    status = _text(selected.get("status")) or "draft"

    lines: list[str] = [
        f"# {_text(title.get('text'))}",
        "",
        f"> 方案 {sid} · {_text(angle.get('name'))} · 状态：{status}（工作草稿，待人工确认）",
        "",
        "## 切入角度",
        "",
        f"- 读者处境：{_text(angle.get('reader_situation'))}",
        f"- 搜索意图：{_text(angle.get('search_intent'))}",
        f"- 内容骨架：{_text(angle.get('skeleton'))}",
        f"- 证据类型：{_text(angle.get('evidence'))}",
        "",
        "## 封面文案",
        "",
    ]
    if _text(copy.get("kicker")):
        lines.append(f"- 系列标签：{_text(copy.get('kicker'))}")
    lines.append(f"- 主文案：{_text(copy.get('headline'))}")
    if _text(copy.get("subline")):
        lines.append(f"- 副文案：{_text(copy.get('subline'))}")
    for item in _list(copy.get("blocks")):
        lines.append(f"- {_text(_block_text(item))}")
    if _text(copy.get("footer")):
        lines.append(f"- 页脚：{_text(copy.get('footer'))}")
    lines += ["", "## 标题", "", _text(title.get("text")), ""]
    alternatives = _list(title.get("alternatives"))
    if alternatives:
        lines += ["备选：" + " ／ ".join(_text(x) for x in alternatives if _text(x)), ""]
    lines += ["## 正文", "", _text(body.get("text")), ""]
    tags = _list(body.get("tags"))
    if tags:
        lines += ["标签：" + " ".join(f"#{_text(tag).lstrip('#')}" for tag in tags if _text(tag)), ""]
    lines += ["## 事实清单", ""]
    if facts:
        lines += ["| 陈述 | 状态 | 依据 / 下一步 | 若为假影响哪句 |", "|---|---|---|---|"]
        for raw_fact in facts:
            fact = _dict(raw_fact)
            basis = _text(fact.get("basis")) or _text(fact.get("next_step"))
            lines.append(
                f"| {_md_cell(fact.get('statement'))} | {_md_cell(fact.get('status'))} | "
                f"{_md_cell(basis)} | {_md_cell(fact.get('impact'))} |"
            )
    else:
        lines.append("本稿未列具体产品事实；如涉及责任、价格、核保或理赔结论，必须先补。")
    lines += ["", "## 分项溯源", ""]
    lines += _md_refs(title, "标题")
    lines += [""] + _md_refs(cover, "封面")
    lines += [""] + _md_refs(body, "正文")
    lines += ["", "## 修改记录", ""]
    revisions = [
        _dict(item) for item in _list(plan.get("revisions"))
        if _dict(item).get("set") in (sid, "all", None)
    ]
    if not revisions:
        lines.append("尚无修改，当前为第 1 版。")
    else:
        for revision in revisions:
            changed = "、".join(_text(x) for x in _list(revision.get("changed")) if _text(x))
            lines.append(
                f"- 第 {revision.get('round', '?')} 轮｜{_text(revision.get('instruction'))}"
                f"｜改动：{changed or '未记录'}"
                f"｜快照：{_text(revision.get('snapshot')) or '未记录'}"
                f"｜状态：{_text(revision.get('status')) or '待确认'}"
            )
    lines += [
        "",
        "---",
        "",
        "封面图见同目录 `封面.png`。本文件是工作草稿，发布前须补齐待核实事实，并按机构要求完成合规与报备。",
        "",
    ]
    return "\n".join(lines)


def cmd_check(args) -> int:
    path, plan = load_plan(args.plan)
    errors, warnings = check_plan(plan, path.parent)
    for warning in warnings:
        print(f"[WARN] {warning}")
    for error in errors:
        print(f"[ERROR] {error}")
    stats = _dict(plan.get("_stats"))
    if errors:
        print(f"FAIL: {len(errors)} 个问题；修好后再 render/export")
        return 1
    print(
        f"OK: {len(_list(plan.get('sets')))} 套结构完整，"
        f"{stats.get('refs', 0)} 条表达溯源，{stats.get('facts', 0)} 条事实"
        f"（待核实 {stats.get('todo', 0)}）"
    )
    return 0


def cmd_render(args) -> int:
    path, plan = load_plan(args.plan)
    base = path.parent
    errors, warnings = check_plan(plan, base)
    for warning in warnings:
        print(f"[WARN] {warning}")
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        print("FAIL: 先修方案 JSON，再渲染对比页")
        return 1
    out = Path(args.out).expanduser().resolve() if args.out else base / "方案对比.html"
    _guard(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build_html(plan, base, out, embed=not args.no_embed), encoding="utf-8")
    size_kb = out.stat().st_size / 1024
    print(f"OK: {out}（{size_kb:.0f} KB，{'内嵌' if not args.no_embed else '外链'}封面）")
    return 0


def cmd_export(args) -> int:
    path, plan = load_plan(args.plan)
    base = path.parent
    errors, warnings = check_plan(plan, base)
    for warning in warnings:
        print(f"[WARN] {warning}")
    if errors:
        for error in errors:
            print(f"[ERROR] {error}")
        print("FAIL: 先修方案 JSON，再导出")
        return 1
    selected = next(
        (_dict(item) for item in _list(plan.get("sets")) if _dict(item).get("id") == args.set),
        None,
    )
    if selected is None:
        print(f"ERROR: 找不到 set={args.set}")
        return 1
    out_dir = Path(args.out).expanduser().resolve() if args.out else base
    title = _text(_dict(selected.get("title")).get("text"))
    md_path = out_dir / f"选定方案_{_safe_name(title, f'方案{args.set}')}.md"
    _guard(md_path)
    out_dir.mkdir(parents=True, exist_ok=True)
    md_path.write_text(build_markdown(plan, selected), encoding="utf-8")

    image = _text(_dict(selected.get("cover")).get("image"))
    if image:
        source = (base / image).resolve()
        if source.is_file():
            target = out_dir / "封面.png"
            _guard(target)
            shutil.copy2(source, target)

    record_path = base / "修改记录.md"
    _guard(record_path)
    revisions = _list(plan.get("revisions"))
    if revisions:
        lines = ["# 修改记录", ""]
        for raw_revision in revisions:
            revision = _dict(raw_revision)
            changed = "、".join(_text(x) for x in _list(revision.get("changed")) if _text(x))
            lines += [
                f"## 第 {revision.get('round', '?')} 轮 · 方案 {revision.get('set')}",
                "",
                f"- 意见：{_text(revision.get('instruction'))}",
                f"- 改动：{changed or '未记录'}",
                f"- 保留：{'、'.join(_text(x) for x in _list(revision.get('preserved')) if _text(x)) or '未记录'}",
                f"- 快照：{_text(revision.get('snapshot')) or '未记录'}",
                f"- 状态：{_text(revision.get('status')) or '待确认'}",
                f"- 说明：{_text(revision.get('note')) or '无'}",
                "",
            ]
        record_path.write_text("\n".join(lines), encoding="utf-8")
    else:
        record_path.write_text("# 修改记录\n\n尚无修改，当前为第 1 版。\n", encoding="utf-8")

    print(f"OK: {md_path}")
    if image:
        print(f"OK: {out_dir / '封面.png'}")
    print(f"OK: {record_path}")
    return 0


def cmd_snapshot(args) -> int:
    path, plan = load_plan(args.plan)
    base = path.parent
    label = _safe_name(args.label, "v1")
    target = base / "history" / f"{label}.json"
    _guard(target)
    if target.exists() and not args.force:
        print(f"ERROR: 快照已存在: {target}（换 --label，或确认后加 --force）")
        return 1
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, target)
    print(f"OK: {target}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="保险小红书 4 套图文方案：确定性检查、对比页渲染、导出与快照"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_check = sub.add_parser("check", help="检查方案 JSON 的结构、溯源与事实状态")
    p_check.add_argument("--plan", required=True, help="方案 JSON 路径")
    p_check.set_defaults(func=cmd_check)

    p_render = sub.add_parser("render", help="生成 4 套方案对比页 HTML")
    p_render.add_argument("--plan", required=True, help="方案 JSON 路径")
    p_render.add_argument("--out", help="输出 HTML 路径，默认与方案 JSON 同目录")
    p_render.add_argument("--no-embed", action="store_true", help="封面用相对路径，不内嵌 base64")
    p_render.set_defaults(func=cmd_render)

    p_export = sub.add_parser("export", help="导出选定方案为 Markdown 并复制封面")
    p_export.add_argument("--plan", required=True, help="方案 JSON 路径")
    p_export.add_argument("--set", type=int, required=True, help="选定的套号 id")
    p_export.add_argument("--out", help="导出目录，默认方案目录根（成品放根）")
    p_export.set_defaults(func=cmd_export)

    p_snapshot = sub.add_parser("snapshot", help="改稿前保存一份方案快照")
    p_snapshot.add_argument("--plan", required=True, help="方案 JSON 路径")
    p_snapshot.add_argument("--label", required=True, help="快照名，如 v1")
    p_snapshot.add_argument("--force", action="store_true", help="覆盖同名快照")
    p_snapshot.set_defaults(func=cmd_snapshot)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
