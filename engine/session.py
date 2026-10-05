#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""统一会话引擎 —— 经典模式与情景模式共用同一套接口。

**为什么需要它**：原本经典模式走 `engine/assess.py`、情景模式走 `engine/scene.py`，
两者各有各的进度、门控、结果结构。这会导致同一件事（比如「k≤2 不给分」）
要维护两遍，迟早漂移。

统一后的约定：

| 阶段 | 两个模式**完全一致**的规则 |
|---|---|
| 作答中 | `progress()` 只给完成度，**不含任何分值**（`PLAN.md` §2.5） |
| 门控 | `unlock_status()` 按**实际题集**查精度表，k≤2 一律不展示（`PLAN.md` §2.5） |
| 结果 | 只有跨过精度门的面向才出现；每条都带 `must_say` 声明 |

两个模式的**差异只体现在三处**：
  1. 呈现顺序（经典＝官方交错序；情景＝按情景分组）
  2. 情景模式额外有「情景结果」面板 A/B
  3. 情景模式的结果以情景为单位交付

用法：
    s = Session("scene")
    s.submit(order, value)
    s.progress()      # 答题中
    s.results()       # 出了精度门之后
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field

from .assess import BANDS, Reference, _load_record, assess_profile, quality_gate

from .scene import (  # noqa: E402
    SceneReference, progress as scene_progress, scene_result, unlock_status,
)

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

MODES = ("classic", "scene")

# 经典模式下，全部面向达到「初步倾向」所需的轮数（30-facet 交错循环）
CLASSIC_MIN_ROUNDS = 3


@dataclass
class Session:
    mode: str = "scene"
    age: str = "18-29"
    responses: dict[int, int] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.mode not in MODES:
            raise ValueError(f"mode 必须是 {MODES} 之一，收到 {self.mode!r}")
        self.ref = Reference()
        self.sref = SceneReference()

    # ───────────────────────────────────────────── 呈现顺序
    def order(self) -> list[int]:
        """完整呈现顺序。"""
        if self.mode == "classic":
            return [i["order"] for i in
                    sorted(self.ref.canonical["items"], key=lambda x: x["order"])]
        out: list[int] = []
        for s in self.sref.scenes():
            out.extend(self.sref.by_scene[s])
        return out

    def next_items(self, n: int = 1) -> list[int]:
        done = set(self.responses)
        return [o for o in self.order() if o not in done][:n]

    def current_scene(self) -> str | None:
        if self.mode != "scene":
            return None
        done = set(self.responses)
        for s in self.sref.scenes():
            if any(o not in done for o in self.sref.by_scene[s]):
                return s
        return None

    # ───────────────────────────────────────────── 作答
    def submit(self, order: int, value: int) -> None:
        if not (1 <= value <= 5):
            raise ValueError(f"作答必须是 1–5，收到 {value!r}")
        self.responses[int(order)] = int(value)

    def submit_many(self, pairs: dict[int, int]) -> None:
        for o, v in pairs.items():
            self.submit(o, v)

    # ───────────────────────────────────────────── 答题中：只有完成度
    def progress(self) -> dict:
        """**唯一可在作答过程中展示的东西。不含任何分值（`PLAN.md` §2.5）。**"""
        if self.mode == "scene":
            return scene_progress(self.sref, set(self.responses))
        n = len(self.responses)
        total = len(self.order())
        rounds = n // 30
        return {
            "items_answered": n, "items_total": total,
            "pct": round(n / total * 100, 1),
            "rounds_done": rounds, "rounds_total": 10,
            "can_show_results": rounds >= CLASSIC_MIN_ROUNDS,
            "note": "答题过程只展示完成度，不展示分值",
        }

    # ───────────────────────────────────────────── 门控
    def unlock(self) -> dict:
        """逐面向判定能展示到什么精度。两个模式**同一套规则**。"""
        return unlock_status(self.sref, set(self.responses))

    # ───────────────────────────────────────────── 结果
    def results(self) -> dict:
        base = {
            "mode": self.mode,
            "items_answered": len(self.responses),
            "must_say_common": "只有跨过精度门的面向才会出现；"
                               "每条都基于**实际答过的题集**查精度表，不做线性外推。",
        }
        if self.mode == "scene":
            return {**base, **self._scene_results()}
        return {**base, **self._classic_results()}

    # ---- 情景模式的结果
    def _scene_results(self) -> dict:
        done = set(self.responses)
        scenes = []
        for s in self.sref.scenes():
            orders = self.sref.by_scene[s]
            if not all(o in done for o in orders):
                continue
            scenes.append(scene_result(s, self.responses, self.sref, done))
        return {"scenes": scenes,
                "n_scenes_complete": len(scenes),
                "unlock": self.unlock()}

    # ---- 经典模式的结果
    def _classic_results(self) -> dict:
        n = len(self.responses)
        rounds = n // 30
        if rounds < CLASSIC_MIN_ROUNDS:
            return {
                "status": "NEEDS_MORE",
                "rounds_done": rounds, "rounds_needed": CLASSIC_MIN_ROUNDS,
                "why": f"经典模式下每个面向需要至少 {CLASSIC_MIN_ROUNDS} 道题"
                       f"（即 {CLASSIC_MIN_ROUNDS * 30} 题）才跨过精度门。",
            }
        # 经典模式的作答以 order 为键；assess_profile 以 id 为键
        by_id = {self.ref.by_order[o]["id"]: v for o, v in self.responses.items()}
        unlock = self.unlock()
        showable = [f for f, u in unlock.items() if u["show_score"]]
        prof = assess_profile(sorted(showable), by_id, self.ref, self.age)

        # 把逐面向的精度一并附上——剖面本身不含这一层
        for row in prof.get("rows", []):
            u = unlock.get(row["facet"], {})
            row["precision"] = {"k": u.get("k"), "r": u.get("r"),
                                "tier": u.get("tier"), "advice": u.get("advice")}
        return {"status": "OK", "profile": prof,
                "withheld": sorted(f for f, u in unlock.items() if not u["show_score"]),
                "rounds_done": rounds}

    # ───────────────────────────────────────────── 导出给界面
    def to_ui_state(self) -> dict:
        """一次性给出界面渲染所需的全部状态。"""
        return {
            "mode": self.mode,
            "progress": self.progress(),
            "unlock": self.unlock(),
            "results": self.results(),
        }
