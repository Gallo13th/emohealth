#!/usr/bin/env python3
"""架构守卫 —— 把「三层解耦」变成三条**可执行**的硬契约。

契约（详见根目录 ``ARCHITECTURE.md``）
====================================
C1  前端层不得直接读 ``archive/``（必须经 ``data/**``）
      扫描：``tools/ui/**``、``ui/**`` 的非生成源码
C2  调研层不得写 ``data/**``（调研只产出报告与档案）
      扫描：``tools/survey/**``
C3  数据层不得读 ``ui/**``（数据层不依赖前端）
      扫描：``tools/build/**``、``tools/analyze/**``

为什么需要它
============
目录分层本身不产生解耦。只要没有检查，``tools/survey/`` 里某天多一行
``json.dump(..., open(ROOT/'data/x.json','w'))`` 也没人拦得住——而这一行正是
「调研污染数据层」的定义。本脚本把三条契约写成**逐行扫描**，违例即退出码 1。

迁移尚未发生时
==============
``tools/survey/``、``tools/build/`` 等目录还不存在时，对应契约**视为通过**并
明确打印「目录未建立，跳过」，**不报错**。这样守卫可以在迁移前就入库并接入 CI，
而不是等目录齐了才敢跑。

判定口径（重要，避免误解）
==========================
* 只扫源码/配置扩展名（``.py .js .mjs .cjs .ts .html .css .sh .json``），
  ``.md`` 不在扫描范围内——文档里出现 ``archive/`` 不构成依赖。
* **整行注释与 Python docstring 不计违例**（它们不产生读写）。
  行尾注释仍在扫描范围内（保守）。
* 路径必须**锚定到顶层目录**才算：``data/x.json``、``f"{ROOT}/data/x"``、
  ``os.path.join(ROOT, "data", …)``、``Path(ROOT) / "data"``、``os.makedirs("data")``，
  以及被赋值为这些字面量的变量（``OUT = os.path.join(ROOT, "data", …)``）。
  ``os.path.join(ROOT, "archive", "ipip", "data", …)`` 里的 ``"data"`` **不算**——
  那只是 ``archive/`` 下的目录名（本仓 ``fetch_hexaco_keys.py`` 正是这种写法）。
* 读写由同行的调用模式判定（``json.dump`` / ``open(...,"w")`` / ``writeFileSync`` … 为写；
  ``open()`` / ``json.load`` / ``glob`` / ``os.walk`` … 为读）。
* **日志行不计**（``print`` / ``console.log`` …，含跨行的续行）：日志里打印路径不是依赖。
  但日志里真的读了文件（``print(open(p).read())``）照样判违例。
* **把路径当标签记下不计**（``e["zh_source"] = "ui/emohealth-data.js（已核对）"``）。
* **变量绑定会被跟踪**：``P = os.path.join(ROOT, "ui", "x")`` 之后写 ``open(P)``
  照样判违例——**任何长度**的变量名都在跟踪范围内（旧版只跟长度 ≥3 或全大写的名字，
  于是 ``p = os.path.join(ROOT, "ui", "emohealth-data.js")`` 的漏检成了一条假绿）。
  跟踪是**作用域感知**的：按 Python 的 LEGB（先内层作用域，没有才看外层），
  被重新赋值、被 ``for`` 重绑、被函数参数遮蔽之后即失效——否则另一个函数里
  同名的临时变量会被误算成同一条依赖。非 Python 文件按同行赋值做启发式跟踪。
* **「未判定」单独报告，不混进绿**：以下情形脚本判不出来，会单独列出并计数，
  打印「未判定 N 处」——**未判定不是通过**：路径段被拆到跨行单独成行、
  变量只出现在既非读也非写的上下文（如 ``register(P)``）、路径藏在容器里
  再取出（弱绑定）、Python 文件无法解析（变量绑定失效）。
  宁可明说没判定完，也不给假绿。

覆盖边界（**明确没做到**的，别把绿当成全知）
============================================
* 跨文件传递：常量在 ``a.py`` 定义、``b.py`` 里使用——本脚本按文件扫描，不跨文件。
* 运行时构造：``getattr`` / 配置文件 / 环境变量 / ``importlib`` 拼出的路径。
* 经函数参数、返回值、对象属性中转的路径。
* 非 Python 文件（JS/HTML）只做同行赋值启发式绑定，不做 AST 分析。
* 行尾注释里的路径会被计入（保守，可能产生改注释就能消掉的误报）。

上述边界之外，本脚本的正反行为由 ``tools/check/verify_architecture_guard.py``
在临时沙盒里逐例验证（应命中/不应命中/未判定），改守卫后必须重跑它。

用法
====
    python tools/check_architecture.py            # 三条契约，一行一条
    python tools/check_architecture.py -v         # 附每个目录扫描的文件
    python tools/check/verify_architecture_guard.py   # 守卫本身的正反验证
退出码：全部通过 0；任一违例 1（「未判定」不改变退出码，但会打印明细）。
"""

from __future__ import annotations

import argparse
import ast
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from _root import RootNotFoundError, find_root, force_utf8_io  # noqa: E402

# ---------------------------------------------------------------- 扫描范围配置

#: 参与扫描的扩展名。``.md`` 有意排除：文档提及路径不构成依赖。
SOURCE_EXTS = (".py", ".js", ".mjs", ".cjs", ".ts", ".html", ".css", ".sh", ".json")

SKIP_DIR_NAMES = {"__pycache__", ".git", "node_modules", ".venv", "venv", ".idea"}

#: C1 的「生成产物」豁免。这些文件由构建脚本产出（342 个量表包、树布局、目录清单、
#: 题面四字段包、推断参数包），其中的 ``archive/...`` 是**写入的溯源证据字符串**
#: （例如选项说明的 `meaning_source` 指向 `archive/scales/*/manual.pdf`），
#: 不是前端在读档案。
#: 新增豁免必须满足：文件由 ``tools/**`` 的脚本生成，且头部有「自动生成」标记。
#:   · `ui/items-structured/*.js`、`ui/inference/*.js`：由 `tools/ui/pack_ui_data.py`
#:     生成，头部均带「由 tools/ui/pack_ui_data.py 生成，勿手改」。
GENERATED_ARTIFACTS = (
    "ui/instruments/",
    "ui/tree-layouts/",
    "ui/items-structured/",
    "ui/inference/",
    "ui/catalog.js",
    "ui/instruments.js",
    "ui/items-structured.js",
    "ui/inference.js",
)

# ------------------------------------------------------------------ 契约定义

CONTRACTS = (
    {
        "id": "C1",
        "title": "前端层不得读 archive/",
        "scopes": ("tools/ui", "ui"),
        "mode": "any",
    },
    {
        "id": "C2",
        "title": "调研层不得写 data/",
        "scopes": ("tools/survey",),
        "mode": "write",
    },
    {
        "id": "C3",
        "title": "数据层不得读 ui/",
        "scopes": ("tools/build", "tools/analyze"),
        "mode": "read",
    },
)

# ------------------------------------------------------------------ 模式识别

#: 路径字面量识别。**关键点：必须锚定到「路径的根」，不能见到 ``"data"`` 就算**——
#: 因为 ``os.path.join(ROOT, "archive", "ipip", "data", …)`` 里的 ``"data"`` 只是
#: ``archive/`` 下的一个目录名，不是项目的 ``data/``。这不是理论问题：本仓
#: ``fetch_hexaco_keys.py`` 就是这种写法，宽松匹配会把它误报成 C2 违例。
_ROOTISH = r"[A-Za-z_$][A-Za-z0-9_$.]*"


def _path_pattern(segment: str) -> re.Pattern:
    """匹配「指向项目某顶层目录」的路径字面量。

    覆盖五种写法（本仓实测出现过的形态）：
      1. 相对写法 ``data/x.json``（前面必须是引号/空白/行首，不能是 ``/``——
         否则 ``archive/ipip/data/x`` 会被误判）
      2. f-string 形态 ``f"{ROOT}/data/x.json"``
      3. join 形态 ``os.path.join(ROOT, "data", …)`` / ``path.join(__dirname, "data")``
         （``"data"`` 必须是**第一个字面量参数**）
      4. Path 除法 ``ROOT / "data"``、``Path("data")``
      5. 建/删目录调用 ``os.makedirs("data")``、``fs.mkdirSync('data')``
    """
    q = rf"[\"']{segment}[\"']"
    return re.compile(
        rf"(?<![A-Za-z0-9_/\\]){segment}[/\\]"                     # 1
        rf"|(?:\.\.?[/\\])+{segment}[/\\]"                         # 1b  ./ui/ ../ui/
        rf"|\}}\s*/\s*{segment}[/\\]"                              # 2
        rf"|(?:os\.path\.join|path\.join)\(\s*(?:{_ROOTISH}\s*,\s*)?{q}"   # 3
        rf"|(?:[/\\])\s*{q}"                                       # 4
        rf"|Path\(\s*{q}\s*\)"                                     # 4
        rf"|(?:makedirs|mkdirSync|mkdir|rmtree|rmSync|unlinkSync)\s*\(\s*{q}"  # 5
    )


PATH_PATTERNS = {
    "archive": _path_pattern("archive"),
    "data": _path_pattern("data"),
    "ui": _path_pattern("ui"),
}

#: 写模式的 ``open()``。允许一层嵌套括号，才能覆盖 ``open(os.path.join(A,'b'), 'w')``。
#: 必须先于普通 ``open(`` 判定，否则「写」会被误判成「读」。
OPEN_WRITE_RE = re.compile(r"open\s*\((?:[^()\n]|\([^()\n]*\))*['\"][wax]['\"]")

#: 写操作。读写的优先级在 ``check_contract`` 里显式处理（见「判定口径」）。
WRITE_IND = re.compile(
    r"""
      \.write_text\b | \.write_bytes\b | \.write\s*\(
    | \bjson\.dump\b
    | \bto_csv\b | \bto_excel\b | \bto_json\b
    | \bshutil\.(?:copy2?|copyfile|move|rmtree)\b
    | \bos\.(?:makedirs|mkdir|replace|remove|rename|unlink)\b
    | \bPath\([^)\n]*\)\.(?:write_text|write_bytes|mkdir|unlink)
    | \bwriteFileSync\b | \bappendFileSync\b | \bmkdirSync\b | \brmSync\b
    | \brmdirSync\b | \bcopyFileSync\b | \brenameSync\b | \bunlinkSync\b
    | \bcreateWriteStream\b
    """,
    re.VERBOSE,
)

#: 仅 shell 脚本适用的写操作。
SH_WRITE_IND = re.compile(r">>?\s*[^\s|&]|\b(?:cp|mv|rm|mkdir|touch|install)\s")

READ_IND = re.compile(
    r"""
      \bopen\s*\(
    | \.read_text\b | \.read_bytes\b | \.read\s*\(
    | \bjson\.load\b | \bcsv\.(?:reader|DictReader)\b
    | \bos\.(?:listdir|walk|scandir|stat)\b
    | \bos\.path\.(?:exists|isfile|isdir|getsize|getmtime)\b
    | \bglob\.(?:glob|iglob)\b
    | \bPath\([^)\n]*\)\.(?:read_text|read_bytes|exists|is_file|is_dir)
    | \breadFileSync\b | \breaddirSync\b | \bglobSync\b | \bexistsSync\b
    | \bstatSync\b | \bcreateReadStream\b
    | \brequire\s*\( | \bsubprocess\b
    """,
    re.VERBOSE,
)

#: ``VAR = <表达式>``（含 JS 的 const/let/var）。用于把「路径常量」绑定到变量名。
ASSIGN_RE = re.compile(
    r"^\s*(?:const|let|var)?\s*([A-Za-z_$][A-Za-z0-9_$]*)\s*=\s*(.+?)\s*$"
)

#: 纯路径常量定义行（右侧是 path 拼接，本身不是读取、也不是写入）。
DEF_ONLY_RE = re.compile(
    r"^\s*(?:const|let|var)?\s*[A-Za-z_$][A-Za-z0-9_$]*\s*=\s*"
    r"(?:os\.path\.join|path\.join|Path|PurePath)\s*\("
)

#: 「把路径当**标签**记下来」的行（如 ``e["zh_source"] = "ui/emohealth-data.js（已人工核对）"``
#: 或字典项 ``"zh": "ui/emohealth-data.js（…）",``）。右侧是纯字符串字面量，不产生读写。
LABEL_RE = re.compile(r"(?:=|:)\s*[\"'][^\"']*[\"']\s*[,;)]?\s*$")

#: 右侧是**纯字符串字面量容器**的行（``PATHS = {"ui/x"}`` / ``["data/y"]``）：
#: 存进容器的是**标签集合**，本身不产生读写，所以判违例不合适；
#: 但它的后续使用仍会被跟踪，且判不出来时报「未判定」（见 ``BindingTable`` 的弱绑定）。
LITERAL_CONTAINER_LINE_RE = re.compile(
    r"(?:=|:)\s*[\[\(\{]\s*(?:[\"'][^\"']*[\"']\s*[,:]?\s*)*[\]\)\}]\s*[,;)]?\s*$"
)

#: 日志行。日志里打印一个路径不算依赖，但如果它同时**真的读**了文件，仍要判违例。
LOG_RE = re.compile(
    r"^\s*(?:print|console\.(?:log|info|warn|error|debug)|logger\.\w+|echo|log\.\w+)\s*\("
)

#: 「强读」信号：出现在日志行里也照样算依赖。
STRONG_READ_RE = re.compile(
    r"""(?:
      \bopen\s*\(
    | \.read_text\b | \.read_bytes\b
    | \breadFileSync\b | \bcreateReadStream\b
    | \bjson\.load\b | \bcsv\.(?:reader|DictReader)\b
    | \bos\.(?:listdir|walk|scandir)\b | \bglob\.(?:glob|iglob)\b | \bglobSync\b
    | \brequire\s*\( | \bpandas?\.read_ | \bpd\.read_
    )""",
    re.VERBOSE,
)

#: 弱信号：只「看一眼」路径本身（大小/时间/存在性），不读内容。
#: 典型形态是脚本报告自己刚写出的文件有多大——不构成对 ``ui/`` 的内容依赖。
WEAK_STAT_RE = re.compile(
    r"^\s*(?:[A-Za-z_$][\w$\[\].]*\s*=\s*)?"
    r"os\.path\.(?:getsize|getmtime|exists|isfile|isdir|stat)\s*\("
)


# ------------------------------------------------------------------ 工具函数

def _lang_of(rel_path: str) -> str:
    return os.path.splitext(rel_path)[1].lower().lstrip(".")


def is_generated(rel_path: str) -> bool:
    """C1 的生成产物豁免。路径统一用 ``/``。"""
    rel = rel_path.replace("\\", "/")
    return any(rel.startswith(p) if p.endswith("/") else rel == p
               for p in GENERATED_ARTIFACTS)


def iter_sources(root: str, scope: str) -> list[tuple[str, str]] | None:
    """列出 scope 下的源码文件；目录不存在时返回 ``None``（=跳过，不报错）。"""
    base = os.path.join(root, *scope.split("/"))
    if not os.path.isdir(base):
        return None
    found: list[tuple[str, str]] = []
    for dirpath, dirnames, filenames in os.walk(base):
        dirnames[:] = sorted(d for d in dirnames if d not in SKIP_DIR_NAMES)
        for fn in sorted(filenames):
            if not fn.lower().endswith(SOURCE_EXTS):
                continue
            full = os.path.join(dirpath, fn)
            rel = os.path.relpath(full, root).replace("\\", "/")
            if is_generated(rel):
                continue
            found.append((rel, full))
    return found


def py_docstring_lines(text: str) -> set[int]:
    """模块/类/函数 docstring 覆盖的行号（这些行不参与违例判定）。"""
    covered: set[int] = set()
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return covered
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not body or not isinstance(node, (ast.Module, ast.FunctionDef,
                                             ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        first = body[0]
        if isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant) \
                and isinstance(first.value.value, str):
            end = getattr(first, "end_lineno", first.lineno) or first.lineno
            covered.update(range(first.lineno, end + 1))
    return covered


def is_full_line_comment(line: str, lang: str) -> bool:
    s = line.strip()
    if not s:
        return False
    if lang in ("py", "sh", "ps1"):
        return s.startswith("#")
    if lang in ("js", "mjs", "cjs", "ts", "css"):
        return s.startswith(("//", "/*", "*", "*/"))
    if lang in ("html", "htm"):
        return s.startswith("<!--")
    if lang == "json":
        return False
    return False


def is_write(line: str, lang: str) -> bool:
    return bool(WRITE_IND.search(line) or OPEN_WRITE_RE.search(line)
                or (lang == "sh" and SH_WRITE_IND.search(line)))


def is_read(line: str) -> bool:
    # 先摘掉「写模式的 open(...)」，否则 json.dump(x, open(p,'w')) 会被误判成读。
    scrubbed = OPEN_WRITE_RE.sub("OPEN_WRITE_MODE(", line)
    return bool(READ_IND.search(scrubbed))


def _paren_delta(line: str) -> int:
    """粗略的括号配平量：用于判断一条 ``print(...)`` 是否跨行。"""
    return line.count("(") - line.count(")")


def _log_read_free(line: str) -> bool:
    """该日志行没有**真的读**文件（``print(open(p).read())`` 里读是真的，仍判违例）。"""
    return not STRONG_READ_RE.search(OPEN_WRITE_RE.sub("OPEN_WRITE_MODE(", line))


def _neutral_line(line: str) -> bool:
    """既非读也非写、也不构成依赖的行：路径常量定义、把路径当标签/标签集合记下。"""
    return bool(DEF_ONLY_RE.match(line) or LABEL_RE.search(line)
                or LITERAL_CONTAINER_LINE_RE.search(line))



#: 单独成行的**路径段**（跨行拼接被拆开后的形态）：``"ui",`` / ``/ "ui"`` / ``+ "ui"``。
#: 这类行没有上下文，判不出是「路径段」还是「标签」——所以**不判违例，也不放过**：
#: 计入「未判定」并打印。旧版对这类行完全看不见（既不算违例也不计入任何计数）。
BARE_SEGMENT_PATTERNS = {
    seg: re.compile(rf"^\s*(?:[+/(]|os\.path\.join\()?\s*[\"']{seg}[\"']\s*[+,)]?\s*$")
    for seg in ("archive", "data", "ui")
}

#: JS 的 ``for (const x of …)`` / ``for (let x in …)``。
JS_FOR_TARGET_RE = re.compile(r"^\s*for\s*\(\s*(?:const|let|var)?\s*([A-Za-z_$][A-Za-z0-9_$]*)")


def _bare_segment(line: str, kind: str) -> bool:
    return bool(BARE_SEGMENT_PATTERNS[kind].match(line))


class BindingTable:
    """同文件内的「路径常量 → 变量」绑定表，**作用域感知**。

    为什么必须有作用域：旧版按「该变量名在本文件出现过路径字面量」就全局生效，
    于是 ``load_neo_zh()`` 里绑到 ``ui/`` 的 ``p`` 会把 ``main()`` 里读
    ``data/instruments/*.json`` 的同名循环变量也算成依赖（误报）；
    反过来旧版又因为「单字母不跟」漏掉了真实违例。两头都错，因为**名字不是身份**。
    这里按绑定所在的作用域解析：使用点从最内层作用域往外找，最近的一层说了算，
    与 Python 的 LEGB 一致；重绑/``for`` 目标/参数遮蔽即失效。
    """

    def __init__(self) -> None:
        self.scopes: list[tuple[int, int, int]] = []      # (start, end, scope_id)
        self.parents: dict[int, int] = {}                 # scope_id -> 外层 scope_id
        self.binds: dict[str, list[tuple[int, int, bool]]] = {}   # name -> [(scope, line, weak)]
        self.invals: dict[str, list[tuple[int, int]]] = {}
        self.text_based = False                           # 非 Python：退化为扁平跟踪

    # -- 构建 ---------------------------------------------------------------
    def add_scope(self, start: int, end: int, sid: int, parent: int | None = None) -> None:
        self.scopes.append((start, end, sid))
        if parent is not None:
            self.parents[sid] = parent

    def add_bind(self, name: str, lineno: int, sid: int, weak: bool = False) -> None:
        self.binds.setdefault(name, []).append((sid, lineno, weak))

    def add_inval(self, name: str, lineno: int, sid: int) -> None:
        self.invals.setdefault(name, []).append((sid, lineno))

    # -- 查询 ---------------------------------------------------------------
    def scope_at(self, lineno: int) -> int:
        best: tuple[int, int, int] | None = None
        for s in self.scopes:
            if s[0] <= lineno <= s[1] and (best is None or (s[1] - s[0]) < (best[1] - best[0])):
                best = s
        return best[2] if best else 0

    def _chain(self, lineno: int) -> list[int]:
        if self.text_based:
            return [0]
        chain = [self.scope_at(lineno)]
        while chain[-1] in self.parents:
            parent = self.parents[chain[-1]]
            if parent in chain:
                break
            chain.append(parent)
        return chain

    def _resolve(self, lineno: int) -> dict[str, bool]:
        """该行可见的「路径变量」→ 是否为**弱绑定**（值在容器/标签里，证据更弱）。"""
        chain = self._chain(lineno)
        out: dict[str, bool] = {}
        for name, binds in self.binds.items():
            invals = self.invals.get(name, ())
            for sc in chain:
                candidates = [(bl, weak) for bsc, bl, weak in binds
                              if bsc == sc and bl < lineno]
                if not candidates:
                    # 本作用域里只重绑过、没有绑过路径 → 遮蔽外层（Python 语义）
                    if any(isc == sc for isc, _ in invals):
                        break
                    continue
                last, weak = max(candidates, key=lambda x: x[0])
                if any(isc == sc and last < il < lineno for isc, il in invals):
                    continue                     # 本层最后一次绑定已被重绑，看外层
                out[name] = weak
                break
        return out

    def active_names(self, lineno: int) -> set[str]:
        """该行可见的**强绑定**路径变量（值就是路径）。"""
        return {n for n, weak in self._resolve(lineno).items() if not weak}

    def active_weak_names(self, lineno: int) -> set[str]:
        """该行可见的**弱绑定**路径变量（值疑在容器/标签集合里）。"""
        return {n for n, weak in self._resolve(lineno).items() if weak}


def _target_names(node: ast.AST) -> list[str]:
    if isinstance(node, ast.Name):
        return [node.id]
    if isinstance(node, (ast.Tuple, ast.List)):
        names: list[str] = []
        for elt in node.elts:
            names.extend(_target_names(elt))
        return names
    return []


#: 拼路径的调用：只有它们的返回值「本身是路径」，其余调用的返回值是内容。
_PATH_CALLS = ("os.path.join", "path.join", "Path", "PurePath")


def _calls_dotted(func: ast.AST) -> str:
    parts: list[str] = []
    node = func
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
    return ".".join(reversed(parts))


def _is_path_expr(node: ast.AST, pattern: re.Pattern, text: str) -> bool:
    """右侧表达式**本身是路径**吗（而不是「读写路径的结果」）。

    ``os.path.join(ROOT, "ui", "x")`` → 是；``json.load(open(<路径>))`` → 不是
    （那绑的是**内容**，把它当路径跟踪会把之后所有 ``db[...]`` 都误算成依赖——
    实测 ``list_missing_batches.py:18`` 就是这种误判）。
    """
    if isinstance(node, ast.Constant):
        return isinstance(node.value, str) and bool(pattern.search(node.value))
    seg = ast.get_source_segment(text, node) or ""
    if isinstance(node, (ast.JoinedStr, ast.BinOp)):
        return bool(pattern.search(seg))
    if isinstance(node, ast.Call):
        return _calls_dotted(node.func) in _PATH_CALLS and bool(pattern.search(seg))
    return False


def _is_literal_container(node: ast.AST, pattern: re.Pattern, text: str) -> bool:
    """右侧是**纯字符串字面量容器**吗（``{"ui/x"}`` / ``["data/y"]``）——弱绑定。"""
    if not isinstance(node, (ast.Set, ast.List, ast.Tuple, ast.Dict)):
        return False
    seg = ast.get_source_segment(text, node) or ""
    if not pattern.search(seg):
        return False
    leaves = [sub.value for sub in ast.walk(node) if isinstance(sub, ast.Constant)]
    return bool(leaves) and all(isinstance(v, str) for v in leaves)


def py_binding_table(text: str, pattern: re.Pattern) -> BindingTable | None:
    """用 AST 建「路径常量 → 变量」绑定表；语法错误时返回 ``None``（判定力失效）。"""
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return None

    parent: dict[ast.AST, ast.AST] = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parent[child] = node

    scoped = (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef,
              ast.ClassDef, ast.Lambda)

    def sid_of(node: ast.AST) -> int:
        cur: ast.AST | None = node
        while cur is not None and not isinstance(cur, scoped):
            cur = parent.get(cur)
        return id(cur) if cur is not None else 0

    tbl = BindingTable()
    for node in ast.walk(tree):
        if not isinstance(node, scoped):
            continue
        if isinstance(node, ast.Module):
            start, end = 1, 10 ** 9
        else:
            start = node.lineno
            end = getattr(node, "end_lineno", None) or start
        outer = parent.get(node)
        tbl.add_scope(start, end, id(node), sid_of(outer) if outer is not None else None)

    # 函数参数在函数体内遮蔽同名常量
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            args = node.args
            names = [a.arg for a in list(args.posonlyargs) + list(args.args)
                     + list(args.kwonlyargs)]
            if args.vararg:
                names.append(args.vararg.arg)
            if args.kwarg:
                names.append(args.kwarg.arg)
            for nm in names:
                tbl.add_inval(nm, node.lineno, id(node))

    for node in ast.walk(tree):
        rhs: ast.AST | None = None
        targets: list[ast.AST] = []
        if isinstance(node, ast.Assign):
            targets, rhs = list(node.targets), node.value
        elif isinstance(node, ast.AnnAssign):
            targets, rhs = [node.target], node.value
        elif isinstance(node, ast.AugAssign):
            targets = [node.target]
        elif isinstance(node, (ast.For, ast.AsyncFor)):
            targets = [node.target]
        elif isinstance(node, ast.Delete):
            targets = list(node.targets)
        else:
            continue
        if rhs is not None and _is_path_expr(rhs, pattern, text):
            strength: str | None = "strong"
        elif rhs is not None and _is_literal_container(rhs, pattern, text):
            strength = "weak"
        else:
            strength = None
        for target in targets:
            for nm in _target_names(target):
                if strength == "strong":
                    tbl.add_bind(nm, node.lineno, sid_of(node))
                elif strength == "weak":
                    tbl.add_bind(nm, node.lineno, sid_of(node), weak=True)
                else:
                    tbl.add_inval(nm, node.lineno, sid_of(node))
    return tbl


def text_binding_table(text: str, pattern: re.Pattern) -> BindingTable:
    """非 Python（或解析失败）的退化跟踪：同行赋值 + ``for`` 目标重绑，扁平作用域。

    只看「赋值行的右侧含锚定路径字面量」，不做数据流——所以它比 AST 版弱：
    这也是「未判定」计数存在的理由之一。
    """
    tbl = BindingTable()
    tbl.text_based = True
    tbl.add_scope(1, 10 ** 9, 0)
    for lineno, line in enumerate(text.splitlines(), start=1):
        m = ASSIGN_RE.match(line)
        if m:
            name, rhs = m.group(1), m.group(2)
            if pattern.search(rhs):
                tbl.add_bind(name, lineno, 0)
            else:
                tbl.add_inval(name, lineno, 0)
        m2 = JS_FOR_TARGET_RE.match(line)
        if m2:
            tbl.add_inval(m2.group(1), lineno, 0)
    return tbl


def _uses_name(line: str, name: str) -> bool:
    return bool(re.search(rf"(?<![A-Za-z0-9_$]){re.escape(name)}(?![A-Za-z0-9_$])", line))


# ------------------------------------------------------------------ 契约执行

def check_contract(root: str, contract: dict) -> tuple[bool, list[str], list[str], list[str], list[str]]:
    """返回 (通过?, 每行摘要, 违例明细, 扫描到的文件列表, 未判定明细)。"""
    kind = {"any": "archive", "write": "data", "read": "ui"}[contract["mode"]]
    pattern = PATH_PATTERNS[kind]
    summary: list[str] = []
    violations: list[str] = []
    undetermined: list[str] = []
    scanned: list[str] = []
    ok = True

    for scope in contract["scopes"]:
        files = iter_sources(root, scope)
        if files is None:
            summary.append(f"{scope}/：目录未建立，跳过")
            continue
        scope_hits = 0
        scope_writes = 0
        scope_undet = 0
        for rel, full in files:
            try:
                text = open(full, encoding="utf-8", errors="replace").read()
            except OSError as exc:                             # pragma: no cover
                summary.append(f"{scope}/：{rel} 读取失败（{exc}）")
                continue
            lang = _lang_of(rel)
            skip_lines = py_docstring_lines(text) if lang == "py" else set()

            table = py_binding_table(text, pattern) if lang == "py" else None
            if table is None:
                if lang == "py":
                    undetermined.append(
                        f"{rel}:1  [未判定] Python 无法解析（语法错误），"
                        f"本文件变量绑定判定失效")
                    scope_undet += 1
                table = text_binding_table(text, pattern)

            in_log = 0                       # >0 表示仍在一条跨行的日志语句里

            for lineno, line in enumerate(text.splitlines(), start=1):
                if lineno in skip_lines or is_full_line_comment(line, lang):
                    continue
                # 日志语句可能跨多行：按括号配平把延续行也标成日志
                if LOG_RE.match(line):
                    in_log = max(0, _paren_delta(line))
                    is_log = True
                elif in_log > 0:
                    in_log = max(0, in_log + _paren_delta(line))
                    is_log = True
                else:
                    is_log = False

                literal = bool(pattern.search(line))
                via_var = any(_uses_name(line, n) for n in table.active_names(lineno))
                via_weak = (not literal) and any(
                    _uses_name(line, n) for n in table.active_weak_names(lineno))
                bare = (not literal) and _bare_segment(line, kind)

                if not (literal or via_var or via_weak or bare):
                    continue

                # 跨行拼接被拆到单独成行的路径段：判不出，登记为「未判定」。
                if bare:
                    scope_undet += 1
                    undetermined.append(
                        f"{rel}:{lineno}  [未判定] 单独成行的路径段，"
                        f"无法确认是路径还是标签：{line.strip()[:110]}")
                    continue

                # 弱绑定（值疑在容器/标签集合里）被使用：证据不足，不判违例也不放过。
                if via_weak:
                    scope_undet += 1
                    undetermined.append(
                        f"{rel}:{lineno}  [未判定] 路径/标签容器变量被使用，"
                        f"无法确认这次用到的是路径：{line.strip()[:110]}")
                    continue

                if contract["mode"] == "any":
                    bad: bool | None = True
                else:
                    read_hit = is_read(line) and not (is_log and _log_read_free(line))
                    write_hit = is_write(line, lang)
                    if literal:
                        if contract["mode"] == "write":
                            bad = write_hit
                        else:
                            weak_stat = (bool(WEAK_STAT_RE.match(line))
                                         and not STRONG_READ_RE.search(line))
                            if weak_stat:
                                bad = False     # 只是报一句「刚写出的文件多大」
                            elif read_hit:
                                bad = True
                            elif write_hit:
                                bad = False     # 数据层产出前端包：写不算「读 ui/」
                            else:
                                bad = not (_neutral_line(line) or is_log)
                    else:
                        # 仅由变量绑定推得：绑定本身不在这行，判读/写要靠这行的上下文。
                        # 两者都判不出时**不猜**——登记为「未判定」。
                        if contract["mode"] == "write":
                            if write_hit:
                                bad = True
                            elif read_hit or is_log or _neutral_line(line):
                                bad = False
                            else:
                                bad = None
                        else:
                            if read_hit:
                                bad = True
                            elif write_hit:
                                bad = False
                            elif is_log or _neutral_line(line):
                                bad = False
                            else:
                                bad = None

                if bad is None:
                    scope_undet += 1
                    undetermined.append(
                        f"{rel}:{lineno}  [未判定] 变量绑定的路径用在既非读也非写的上下文："
                        f"{line.strip()[:110]}")
                elif bad:
                    scope_hits += 1
                    violations.append(
                        f"{rel}:{lineno}  {line.strip()[:140]}"
                    )
                elif contract["mode"] == "read" and is_write(line, lang):
                    # 数据层「写 ui/」不是 C3 定义的违例（C3 只管读），
                    # 但它是迁移期最值得看见的一类跨层动作，所以计数并报出来。
                    scope_writes += 1
        if scope_hits:
            ok = False
        scanned.extend(rel for rel, _ in files)
        note = f"，{scope_writes} 处写入 {kind}/（不计违例）" if scope_writes else ""
        note += f"，未判定 {scope_undet} 处" if scope_undet else "，未判定 0 处"
        summary.append(f"{scope}/：{len(files)} 文件，{scope_hits} 违例"
                       + ("" if scope_hits else " ✅") + note)

    return ok, summary, violations, scanned, undetermined


def main() -> int:
    force_utf8_io()          # 入口第一件事：GBK 控制台下不许崩（见 tools/_root.py）
    parser = argparse.ArgumentParser(
        description="守卫三层解耦契约 C1/C2/C3（无违例退出码 0）")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="列出每个目录下实际扫描的文件")
    args = parser.parse_args()

    try:
        root = find_root(__file__)
    except RootNotFoundError as exc:
        print(f"❌ 无法定位项目根：{exc}")
        return 1

    print(f"架构守卫（项目根：{root}）")
    print(f"扫描扩展名：{' '.join(SOURCE_EXTS)}（.md 不计）")
    print("生成产物豁免：" + "、".join(GENERATED_ARTIFACTS))
    print("变量跟踪：作用域感知（任何长度；重绑/for 目标/参数遮蔽后失效）")
    print()

    all_ok = True
    pending_details: list[str] = []
    undet_by_contract: dict[str, list[str]] = {}
    results: dict[str, tuple[bool, list[str], list[str], list[str], list[str]]] = {}
    for contract in CONTRACTS:
        res = check_contract(root, contract)
        results[contract["id"]] = res
        ok, summary, violations, scanned, undetermined = res
        all_ok &= ok
        undet_by_contract[contract["id"]] = undetermined
        mark = "✅" if ok else "❌"
        print(f"{mark} {contract['id']}  {contract['title']}")
        for s in summary:
            print(f"     · {s}")
        if args.verbose and scanned:
            for rel in scanned:
                print(f"       ├ {rel}")
        if violations:
            pending_details.append(contract["id"])
        print()

    total_undet = sum(len(v) for v in undet_by_contract.values())
    if total_undet:
        print(f"未判定明细（{total_undet} 处；**未判定 ≠ 通过**，只是脚本没能判定）")
        for contract in CONTRACTS:
            items = undet_by_contract[contract["id"]]
            if not items:
                continue
            print(f"── {contract['id']}  {contract['title']}（{len(items)} 处）")
            for v in items:
                print(f"   {v}")
        print()

    if pending_details:
        print("违例明细（文件:行号）")
        for contract in CONTRACTS:
            if contract["id"] not in pending_details:
                continue
            _, _, violations, _, _ = results[contract["id"]]
            print(f"── {contract['id']}  {contract['title']}（{len(violations)} 条）")
            for v in violations:
                print(f"   {v}")
        print()
        print("❌ 架构契约未通过：上面的每一行都是一处跨层依赖，"
              "请改为经 data/ 中转（C1）、改写到 research/ 或 archive/（C2）、"
              "或把前端产物交给 tools/ui/ 生成（C3）。")
        return 1

    print("✅ 三条契约全部通过。")
    print(f"   未判定 {total_undet} 处"
          + ("（明细见上，逐一确认后才算收敛）" if total_undet else "（本次没有判不出来的引用）"))
    print("   口径：路径按静态字面量 + 同文件变量绑定判定；"
          "运行时构造（getattr/配置/环境变量）与跨文件传递不在覆盖范围内。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
