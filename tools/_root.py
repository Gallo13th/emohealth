#!/usr/bin/env python3
"""统一的项目根定位 —— 清理后所有脚本共用的一层基座。

为什么需要这个文件
==================
清理前，`tools/` 下的脚本普遍这样推导项目根：

    ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

即「从 `tools/xxx.py` 上退两层」。**这个写法把「脚本在文件系统里的深度」当成了
「到项目根的距离」。** 一旦文件移进子目录（`tools/survey/xxx.py`），上退两层就落到
`tools/`，全仓路径静默错位——脚本不会报错，只会去读一个不存在的位置然后失败或写出
错地方。本项目有 159 个脚本，逐个改成「数层数」既容易错、也经不起以后再移动。

所以这里改用**标记文件探测**：

    from _root import find_root
    ROOT = find_root()          # 无论脚本在哪一层都正确

判据是「向上找到含 ``MANIFEST.sha256`` 的目录」。选它而不是 `.git` 或 `README.md`：
``MANIFEST.sha256`` 是本项目**自己生成、且在仓库里唯一**的证据链清单元数据
（`tools/build/build_manifest.py` 产出），不会在别处偶然出现。

找不到就**抛错，不猜**。返回 cwd 或某个祖先目录会让错误延后到「读到错的文件」时才
暴露，那正是本文件要消灭的一类 bug。

API
===
``find_root(start=None)``
    向上查找项目根。``start`` 可以是文件或目录；默认取**调用方脚本**的位置
    （通过调用栈拿 ``__file__``），因此在任何子目录里都可直接用。
    找不到抛 ``RootNotFoundError``。

``find_tools_dir(start=None)``
    ``<root>/tools``。

``add_tools_to_path(*subdirs, root=None)``
    把 ``tools/`` 以及指定的子目录插到 ``sys.path`` 最前，供迁移后的脚本
    ``import`` 共享库（如 ``pdftext``、``build_scales``、``item_coding``）。
    返回实际插入的目录列表（已去重、已存在优先）。

``add_root_to_path(root=None)``
    把**项目根**插到 ``sys.path`` 最前，返回该路径。
    本仓有脚本用**带包名前缀**的写法（``from tools.item_coding import ...``、
    ``from content.facet_definitions import ...``），这种写法要求根在 ``sys.path``
    上，光加 ``tools/`` 不够。迁移后的脚本按需调用其一或两者。

``force_utf8_io()``
    把 ``stdout`` / ``stderr`` 切成 UTF-8，返回实际被重设的流名列表。
    **每个命令行入口都该在 ``main()`` 的第一行调它**，理由见下。

为什么需要 ``force_utf8_io()``
==============================
本项目的脚本普遍用 ``✅ ❌ ⚠ ✓ →`` 和中文打印结果。Windows 默认控制台代码页是
**GBK**，Python 会据此把 ``sys.stdout.encoding`` 设成 ``gbk``，于是 ``print`` 在
**输出结果的那一行**抛 ``UnicodeEncodeError``：

* 崩溃发生在**已经写完盘之后**（打包器就是"打包成功了却报错"）；
* 退出码是 **1**，与「守卫真的发现了问题」**完全不可区分**——
  也就是说，在默认控制台上，一个完好的守卫会**永远假装变红**，而人只会学会无视它。

这不是"调用者该设 ``PYTHONIOENCODING``"的问题：把修复责任推给调用者，换个人跑就又崩。
兜底必须由脚本自己做，且只做一次、只有一份实现——这就是它放在这里的原因。

**用法**（入口第一件事，早于 ``parse_args``，这样 ``--help`` 与 argparse 报错也覆盖）::

    from _root import find_root, force_utf8_io

    def main() -> int:
        force_utf8_io()
        ...

对没有 ``reconfigure`` 的流对象（被替换过的假流、某些 IDE 包装）静默跳过——
宁可打印变丑，也不能让兜底自己抛异常。

回归守卫：``tools/check/check_cli_encoding.py``（把「每轮必跑」清单用
``PYTHONIOENCODING=gbk`` 逐条跑一遍，只看有没有崩溃，不看业务性红）。

自检
====
    python tools/_root.py

打印找到的项目根，并断言 ``MANIFEST.sha256``、``ui/index.html``、
``data/instruments`` 都存在。
"""

from __future__ import annotations

import os
import sys

#: 项目根的标记文件。必须由 project 自己生成，且在仓库内唯一。
ROOT_MARKER = "MANIFEST.sha256"

#: 自检时一并断言的「根下必须存在」的路径。
REQUIRED_PATHS = ("MANIFEST.sha256", "ui/index.html", "data/instruments")


class RootNotFoundError(RuntimeError):
    """从起点向上找不到含 ROOT_MARKER 的目录。"""


def _caller_anchor(depth: int = 2) -> str:
    """取调用方脚本的位置。

    ``depth=1`` 是 ``find_root`` 自身，``depth=2`` 是 ``find_root`` 的调用方。
    调用方没有 ``__file__``（交互式解释器 / ``python -c``）时回退到 cwd。
    """
    try:
        frame = sys._getframe(depth)
    except ValueError:                                        # pragma: no cover
        return os.getcwd()
    caller_file = frame.f_globals.get("__file__")
    if caller_file:
        return caller_file
    return os.getcwd()


def _as_dir(path: str) -> str:
    """把「文件或目录」统一成绝对目录路径。"""
    p = os.path.abspath(path)
    if os.path.isfile(p):
        return os.path.dirname(p)
    return p


def find_root(start: str | None = None) -> str:
    """向上找到含 ``ROOT_MARKER`` 的目录，返回其绝对路径。

    Parameters
    ----------
    start:
        起点的文件或目录。默认取调用方脚本的位置（``__file__``）；
        调用方没有 ``__file__`` 时取当前工作目录。

    Raises
    ------
    RootNotFoundError
        从起点一直到文件系统根都没有找到 ``ROOT_MARKER``。
    """
    if start is None:
        start = _caller_anchor(depth=2)
    current = _as_dir(start)
    while True:
        if os.path.isfile(os.path.join(current, ROOT_MARKER)):
            return current
        parent = os.path.dirname(current)
        if parent == current:                                 # 已到盘符/根
            raise RootNotFoundError(
                f"从 {_as_dir(start)} 向上找不到含 {ROOT_MARKER} 的目录；"
                f"请确认脚本位于项目内，或显式传入 start="
            )
        current = parent


def find_tools_dir(start: str | None = None) -> str:
    """返回 ``<root>/tools`` 的绝对路径。"""
    return os.path.join(find_root(start), "tools")


def add_root_to_path(root: str | None = None) -> str:
    """把项目根插入 ``sys.path`` 最前，返回该路径。

    用于 ``from tools.item_coding import ...`` / ``from content.facet_definitions import ...``
    这类**带包名前缀**的导入：它们要求根在 ``sys.path`` 上。
    """
    project_root = os.path.abspath(root or find_root())
    if project_root in sys.path:
        sys.path.remove(project_root)
    sys.path.insert(0, project_root)
    return project_root


def add_tools_to_path(*subdirs: str, root: str | None = None) -> list[str]:
    """把 ``tools/`` 及指定子目录插入 ``sys.path``，返回实际插入的目录。

    迁移后 ``tools/survey/foo.py`` 需要 ``import pdftext``（共享库留在 ``tools/``
    平铺），检查脚本需要 ``import engine`` 之外的跨类库——都由这里统一处理，
    免去每个子目录各自算相对层数。

    Parameters
    ----------
    *subdirs:
        相对 ``tools/`` 的子目录名，如 ``"survey"``、``"build"``。
        传入不存在的目录会在返回值里如实体现（不插入、不报错），
        这样同一个脚本在「迁移前 / 迁移后」两种布局下都能跑。
    root:
        显式指定项目根；默认 ``find_root()``。
    """
    tools_dir = os.path.join(root or find_root(), "tools")
    added: list[str] = []
    for candidate in (tools_dir, *(os.path.join(tools_dir, s) for s in subdirs)):
        candidate = os.path.abspath(candidate)
        if not os.path.isdir(candidate):
            continue
        if candidate in sys.path:
            # 已在 path 里：移到最前，保证本地模块优先于同名的第三方包。
            sys.path.remove(candidate)
        sys.path.insert(0, candidate)
        added.append(candidate)
    return added


def _check(label: str, path: str) -> bool:
    ok = os.path.exists(path)
    print(f"  {label:<22} {'✅ 存在' if ok else '❌ 缺失'}   {path}")
    return ok


def force_utf8_io() -> list[str]:
    """把 ``stdout`` / ``stderr`` 切成 UTF-8，返回实际被重设的流名。

    为什么必须由脚本自己做、而不是靠调用者设 ``PYTHONIOENCODING``：
    Windows 默认控制台代码页是 GBK，``sys.stdout.encoding`` 随之变成 ``gbk``，
    于是任何含 ``✅``/``❌``/``→`` 或中文的 ``print`` 都会抛 ``UnicodeEncodeError``。
    崩溃点在**输出结果那一行**，所以：① 可能发生在写盘之后（"成功了却报错"）；
    ② 退出码是 1，与「守卫真的发现了问题」**不可区分**——在默认控制台上，
    一个完好的守卫会永远假装变红。把修复责任推给调用者，换个人跑就又崩。

    实现细节：只对**编码不是 utf-8 且支持 ``reconfigure``** 的流动手；
    不支持的对象（被替换过的假流、某些 IDE 包装）静默跳过——宁可让打印难看，
    也不能让兜底自己抛异常。

    调用位置：``main()`` 的第一行，**早于** ``parse_args``，
    这样 ``--help`` 与 argparse 的报错路径也被覆盖。
    """
    changed: list[str] = []
    for name, stream in (("stdout", sys.stdout), ("stderr", sys.stderr)):
        current = (getattr(stream, "encoding", "") or "").lower().replace("-", "")
        if current == "utf8":
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except Exception:                                     # pragma: no cover
            continue
        changed.append(name)
    return changed


def main() -> int:
    """``python tools/_root.py`` 自检：定位 + 断言根下关键路径。"""
    force_utf8_io()          # 本文件自己也打印 ✅/❌，自检不能死在 GBK 上
    print("tools/_root.py 自检")
    print(f"  起点（本文件）          {os.path.abspath(__file__)}")
    try:
        root = find_root(__file__)
    except RootNotFoundError as exc:
        print(f"❌ 定位失败：{exc}")
        return 1
    print(f"  项目根                  {root}")
    print(f"  标记                    {ROOT_MARKER}")
    print()

    ok = True
    for rel in REQUIRED_PATHS:
        kind = "目录" if rel == "data/instruments" else "文件"
        ok &= _check(f"{rel}（{kind}）", os.path.join(root, rel))

    # add_tools_to_path：迁移前 survey/ 不存在也不应报错，只如实反映。
    probe = add_tools_to_path("survey", "build", "analyze", "check", "ui", "legacy")
    print()
    print(f"  add_root_to_path 插入      {add_root_to_path(root)}")
    print(f"  add_tools_to_path 插入 {len(probe)} 个目录：")
    for p in probe:
        print(f"    - {os.path.relpath(p, root)}")
    ok &= os.path.join(root, "tools") in probe

    print()
    if ok:
        print("✅ 自检通过：项目根定位正确，根下关键路径齐备。")
        return 0
    print("❌ 自检失败：见上方缺失项。")
    return 1


if __name__ == "__main__":
    sys.exit(main())
