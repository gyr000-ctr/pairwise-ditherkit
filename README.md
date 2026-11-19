# pairwise-ditherkit

## 题面（可直接粘贴）

导出服务做分块抖动后出现接缝：分块结果与整图不一致、同一 seed 两次导出不同、状态随行数增长导致长图内存爆掉。ditherkit/core.py 是核心，tests/test_core.py 15 个红。要修的是：同 seed 输出可复现；分块与整图逐像素一致；reset 后重放一致；状态大小与行数无关；级数小于 2、越界值抛 ValueError；输出落在合法级上。

## 运行方式

```bash
python -m pytest tests -q
```

初始结果应为 `15 failed`（全部因 `NotImplementedError` 失败，无 collection error）。

## 字段

- 所属领域：游戏、图形与多媒体
- 子方向：图像处理
- 任务类型：Bugfix
- 语言/框架：Python 3, pytest
- 环境可复现等级：无外部依赖
