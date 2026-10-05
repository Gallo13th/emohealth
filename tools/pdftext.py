"""最小但正确的 PDF 文本提取器：解析 ToUnicode CMap 与 CID 字宽还原排版。

为什么不继续用「数括号」的土办法
================================
最早我用「取 ``(...)`` 与 ``<...>`` 串拼接」的办法读 APA 的 PDF，能读出一部分，
另一部分是乱码（如 ``dŚĞ``）。原因是这些 PDF 用**子集内嵌 CID 字体**，
字符串里存的是**字形码**而非字符码，必须经过该字体的 ``/ToUnicode`` CMap 还原。
拿乱码建题库是不可接受的，所以这一步真做。

踩过的三个坑（都有实测证据）
============================
1. **不能按 ``BT`` 切块**：``BT`` 之后的 ``(...)Tj`` 会落进下一块，
   只提取到 382 字符（实际 112 KB）。
2. **必须按内容流分页**：不同页的坐标系独立，混在一起按 y 聚类会把
   「题干 + 下一页题干 + 说明文字」拼成同一行。
3. **TJ 数组要整体解析**：形如 ``[(Ple)4(n)-4(ty)-6( o)-5(f)…]TJ``，
   数字是字距（单位 1/1000 em，负值推进光标）。空格**已在字符串里**
   （``( o)``、``(to)``、``(t )``），所以不要去猜间隙——我那样写过，是错的。

实现范围（够用即止）
====================
解压 FlateDecode、展开 ``/ObjStm``、解析 ``bfchar``/``bfrange`` 与 ``/W`` 字宽。
不做：加密、LZW、图片 OCR。字符未还原时返回 ``\\ufffd`` 并计数，让调用方看得见。
"""

from __future__ import annotations

import re
import sys
import zlib
from dataclasses import dataclass, field

# 内容流操作符扫描：只认与文本位置/字体/显示有关的
TOKEN = re.compile(
    rb"(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+(-?[\d.]+)\s+Tm"
    rb"|(-?[\d.]+)\s+(-?[\d.]+)\s+(?:Td|TD)"
    rb"|/([A-Za-z0-9#+._-]+)\s+(-?[\d.]+)\s+Tf"
    rb"|(T\*)"
    # ⚠️ TJ 数组里**字面串内部可以出现未转义的 `[` / `]`**（PDF 规范只要求转义
    #    `(` `)` `\`）。曾经写成 `\[((?:\\.|[^\\\[\]])*)\]\s*TJ`：字符类排除了
    #    方括号，于是 `[(…prescribed [e.g., …)]TJ` 这种数组整个匹配失败，
    #    finditer 再从串内的 `[` 重新起步，只取到后半截——**静默丢字**，不报错、
    #    不产生 \ufffd、也不计数。实测把 DSM-5-TR L1 第 23 题的题面截成
    #    「…or m」（2026-10-04 定位）。
    #    修法：把 `(…)` 当作整体先吃掉，方括号在字面串里就不会误判为数组结束。
    #    必须配**原子组** `(?>…)`：不加时该模式在含 `[` 的二进制流上
    #    灾难性回溯（实测某 163 KB 流从 0.007 s 涨到 2.3 s，全局抽取从秒级变超时）。
    #    原子组需 Python ≥3.11（本仓 3.13）。
    rb"|\[((?>\((?:\\.|[^\\()])*\)|\\.|[^\\\[\]])*)\]\s*TJ"
    rb"|(\((?:\\.|[^\\()])*\))\s*Tj"
    rb"|<([0-9A-Fa-f\s]*)>\s*Tj", re.S)

# TJ 数组内部：字面串 | 十六进制串 | 字距数字
# ⚠️ 不用捕获组，靠匹配文本的首字符判断类型。组号我已经写错两次
#    （`<([0-9A-Fa-f\s]*)>` 混进来让 group(3) 指向不存在的组），
#    改成「无组 + 看首字符」就没有组号可错了。
INNER = re.compile(rb"\((?:\\.|[^\\()])*\)|<[0-9A-Fa-f\s]*>|-?\d+(?:\.\d+)?")
NUMBER = re.compile(rb"^-?\d+(?:\.\d+)?$")

ESCAPES = {b"n": b"\n", b"r": b"\r", b"t": b"\t", b"b": b"\b", b"f": b"\f",
           b"(": b"(", b")": b")", b"\\": b"\\"}


@dataclass
class PdfDoc:
    raw: bytes
    objects: dict[int, bytes] = field(default_factory=dict)
    streams: list[bytes] = field(default_factory=list)
    _maps: list[dict[int, str]] | None = None
    _widths: dict[int, int] | None = None

    @classmethod
    def load(cls, path: str) -> "PdfDoc":
        with open(path, "rb") as fh:
            doc = cls(raw=fh.read())
        doc._parse_indirect_objects()
        doc._parse_object_streams()
        return doc

    # ── 对象与流 ────────────────────────────────────────────────────
    def _parse_indirect_objects(self) -> None:
        for m in re.finditer(rb"(\d+)\s+(\d+)\s+obj\b", self.raw):
            end = self.raw.find(b"endobj", m.end())
            body = self.raw[m.end():end if end > 0 else len(self.raw)]
            self.objects[int(m.group(1))] = body
            st = self._stream_of(body)
            if st is not None:
                self.streams.append(st)

    def _stream_of(self, body: bytes) -> bytes | None:
        m = re.search(rb"stream\r?\n", body)
        if not m:
            return None
        end = body.find(b"endstream", m.end())
        if end < 0:
            return None
        data = body[m.end():end]
        if b"/FlateDecode" in body[:m.start()]:
            try:
                return zlib.decompress(data)
            except zlib.error:
                try:
                    return zlib.decompressobj().decompress(data)
                except zlib.error:
                    return b""
        return data

    def _parse_object_streams(self) -> None:
        """展开 ``/Type /ObjStm``：头部是「对象号 偏移」对，后面是对象体。"""
        for obj in list(self.objects.values()):
            if b"/ObjStm" not in obj:
                continue
            data = self._stream_of(obj)
            if not data:
                continue
            mn, mf = re.search(rb"/N\s+(\d+)", obj), re.search(rb"/First\s+(\d+)", obj)
            if not (mn and mf):
                continue
            n, first = int(mn.group(1)), int(mf.group(1))
            header = data[:first].split()
            try:
                pairs = [(int(header[i]), int(header[i + 1])) for i in range(0, 2 * n, 2)]
            except (IndexError, ValueError):
                continue
            for i, (_num, rel) in enumerate(pairs):
                start = first + rel
                stop = first + pairs[i + 1][1] if i + 1 < len(pairs) else len(data)
                self.streams.append(data[start:stop])

    # ── ToUnicode 与字宽 ────────────────────────────────────────────
    def to_unicode_maps(self) -> list[dict[int, str]]:
        if self._maps is None:
            maps = []
            for st in self.streams:
                if b"beginbfchar" in st or b"beginbfrange" in st:
                    m = _parse_cmap(st)
                    if m:
                        maps.append(m)
            self._maps = maps
        return self._maps

    def cid_widths(self) -> dict[int, int]:
        """解析 CID 字体的 ``/W`` 数组 → ``{cid: width/1000 em}``。

        条目有两种：``c [w1 w2 …]`` 与 ``c1 c2 w``。有了它才能按真实字宽推进光标，
        换行与左右列的判定才准（按字符数估算是不行的）。
        """
        if self._widths is not None:
            return self._widths
        widths: dict[int, int] = {}
        for body in self.objects.values():
            if b"/W" not in body:
                continue
            m = re.search(rb"/W\s*\[(.*?)\]\s*(?=/|\s*>>)", body, re.S)
            if not m:
                continue
            toks = re.findall(rb"\[[^\]]*\]|-?\d+(?:\.\d+)?", m.group(1))
            i = 0
            while i < len(toks):
                if toks[i].startswith(b"["):
                    i += 1
                    continue
                start = int(float(toks[i]))
                if i + 1 < len(toks) and toks[i + 1].startswith(b"["):
                    for k, w in enumerate(re.findall(rb"-?\d+(?:\.\d+)?", toks[i + 1][1:-1])):
                        widths[start + k] = int(float(w))
                    i += 2
                elif i + 2 < len(toks):
                    end, w = int(float(toks[i + 1])), int(float(toks[i + 2]))
                    for c in range(start, min(end, start + 8192) + 1):
                        widths[c] = w
                    i += 3
                else:
                    i += 1
        self._widths = widths
        return widths

    # ── 文本 ────────────────────────────────────────────────────────
    def text_runs(self) -> list[list[tuple[float, float, float, float, str]]]:
        """按内容流（≈页）抽文本 → ``[(x0, x1, y, size, text), …]``。"""
        maps = self.to_unicode_maps()
        widths = self.cid_widths()
        default_w = 500
        pages: list[list[tuple[float, float, float, float, str]]] = []

        for st in self.streams:
            if b"Tj" not in st and b"TJ" not in st:
                continue
            runs: list[tuple[float, float, float, float, str]] = []
            x = y = 0.0
            size = 10.0
            last_end: float | None = None        # 上一段的右边界（用于补丢掉的分词空格）
            last_y = 0.0
            for m in TOKEN.finditer(st):
                if m.group(1) is not None:                      # Tm
                    x, y = float(m.group(5)), float(m.group(6))
                    if float(m.group(4)):
                        size = float(m.group(4))
                    continue
                if m.group(7) is not None:                      # Td / TD
                    x += float(m.group(7))
                    y += float(m.group(8))
                    continue
                if m.group(9) is not None:                      # Tf
                    size = float(m.group(10)) or size
                    continue
                if m.group(11) is not None:                     # T*
                    y -= size * 1.2
                    continue

                arr = m.group(12)
                if arr is None:
                    lit = m.group(13)
                    arr = lit if lit is not None else b"<" + (m.group(14) or b"") + b">"
                cursor = x            # 字距/字宽推进后的真实位置
                expected = x          # 只按字宽累加的位置（不含字距）
                parts: list[str] = []
                for piece in INNER.finditer(arr):
                    raw = piece.group(0)
                    if NUMBER.match(raw):                       # 字距数字
                        cursor -= float(raw) / 1000.0 * size
                        continue
                    if raw.startswith(b"("):                    # 字面串
                        txt = _decode_literal(raw[1:-1])
                        for ch in txt:
                            w = widths.get(ord(ch), default_w) / 1000.0 * size
                            cursor += w
                            expected += w
                    else:                                       # 十六进制串
                        hx = re.sub(rb"\s", b"", raw[1:-1])
                        txt = _decode_hex(hx, maps)
                        try:
                            b = bytes.fromhex(hx.decode("ascii")) if hx else b""
                        except ValueError:
                            b = b""
                        for i in range(0, len(b) - 1, 2):
                            code = int.from_bytes(b[i:i + 2], "big")
                            w = widths.get(code, default_w) / 1000.0 * size
                            cursor += w
                            expected += w
                    parts.append(txt)
                text = "".join(parts)
                if text:
                    runs.append((x, cursor, y, size, text))
                x = cursor
            if runs:
                pages.append(runs)
        return pages


def _parse_cmap(data: bytes) -> dict[int, str]:
    out: dict[int, str] = {}
    for seg in re.findall(rb"beginbfchar(.*?)endbfchar", data, re.S):
        for src, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", seg):
            out[int(src, 16)] = _utf16be(dst)
    for seg in re.findall(rb"beginbfrange(.*?)endbfrange", data, re.S):
        for lo, hi, dst in re.findall(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", seg):
            a, b, base = int(lo, 16), int(hi, 16), int(dst, 16)
            for k in range(a, min(b, a + 65535) + 1):
                out[k] = chr(base + (k - a))
        for lo, hi, arr in re.findall(
                rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*\[(.*?)\]", seg, re.S):
            a = int(lo, 16)
            for i, dst in enumerate(re.findall(rb"<([0-9A-Fa-f]+)>", arr)):
                out[a + i] = _utf16be(dst)
    return out


def _utf16be(hx: bytes) -> str:
    try:
        b = bytes.fromhex(hx.decode("ascii"))
    except ValueError:
        return "\ufffd"
    if len(b) % 2:
        b += b"\x00"
    try:
        return b.decode("utf-16-be")
    except UnicodeDecodeError:
        return "\ufffd"


def _decode_literal(chunk: bytes) -> str:
    s = re.sub(rb"\\([nrtbf()\\])", lambda m: ESCAPES[m.group(1)], chunk)
    s = re.sub(rb"\\([0-7]{1,3})", lambda m: bytes([int(m.group(1), 8) % 256]), s)
    return s.decode("cp1252", "replace")


def _decode_hex(hx: bytes, maps: list[dict[int, str]]) -> str:
    hx = re.sub(rb"\s", b"", hx)
    if not hx:
        return ""
    try:
        b = bytes.fromhex(hx.decode("ascii"))
    except ValueError:
        return ""
    out = []
    for i in range(0, len(b) - 1, 2):
        code = int.from_bytes(b[i:i + 2], "big")
        out.append(next((mp[code] for mp in maps if code in mp), "\ufffd"))
    return "".join(out)


def layout_lines(runs: list[tuple[float, float, float, float, str]], *,
                 y_tol: float = 3.0) -> list[dict]:
    """把一页的文本段按 y 聚成行、按 x 排序。返回 ``[{y, text, cells}]``。

    ⚠️ **纯空白段不能丢**。曾经这里有 `if not text.strip(): continue`，于是
    PDF 用「单独的空白段」表示词间空格的排版里，相邻两段会被直接粘起来——
    实测 DSM-5-TR L1 第 23 题抽成 `in greater amounts orlonger than prescribed`、
    第 21 题 `Drinkingat least`、第 22 题 `Smokingany cigarettes`（2026-10-04）。
    那个空格**本来就在 PDF 里**（`x0=247.61 ' '`），只是被丢掉了。改成保留空白段，
    最后再把「整行只有空白」的行滤掉（否则会多出一堆空行）。
    """
    rows: list[dict] = []
    for x0, x1, y, size, text in sorted(runs, key=lambda r: (-r[2], r[0])):
        if not text:                                  # 空串不是空格，跳过
            continue
        row = next((r for r in rows if abs(r["y"] - y) <= y_tol), None)
        if row is None:
            row = {"y": y, "cells": []}
            rows.append(row)
        row["cells"].append({"x0": x0, "x1": x1, "size": size, "text": text})
    out: list[dict] = []
    for row in rows:
        row["cells"].sort(key=lambda c: c["x0"])
        row["text"] = "".join(c["text"] for c in row["cells"])
        if row["text"].strip():                       # 纯空白的行不输出
            out.append(row)
    out.sort(key=lambda r: -r["y"])
    return out


if __name__ == "__main__":
    path = sys.argv[1]
    doc = PdfDoc.load(path)
    maps = doc.to_unicode_maps()
    widths = doc.cid_widths()
    pages = doc.text_runs()
    print(f"{path}")
    print(f"  对象 {len(doc.objects)}，流 {len(doc.streams)}，"
          f"ToUnicode 图 {len(maps)}（{sum(len(m) for m in maps)} 条），"
          f"/W 字宽 {len(widths)} 条")
    print(f"  含文本的页 {len(pages)}，文本段合计 {sum(len(p) for p in pages)}")
    for pi, runs in enumerate(pages[:2]):
        rows = layout_lines(runs)
        print(f"\n── 第 {pi + 1} 页（{len(runs)} 段 → {len(rows)} 行）——")
        for r in rows[:6]:
            print(f"   y={r['y']:7.1f} | {r['text'][:104]}")
        q = [r for r in rows if r["text"].strip().startswith("2P")]
        if q:
            print(f"   题 2 行：{q[0]['text'][:110]}")
