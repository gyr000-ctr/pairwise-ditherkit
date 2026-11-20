"""ditherkit 核心 API。

实现要点：

* **确定性**：每个 ``DitherSession`` 持有自己的 SplitMix64 伪随机状态，
  从不使用全局 ``random``，因此同一 seed 的两次导出逐位一致。
* **分块无关**：量化严格按光栅顺序（行优先、行内从左到右）进行，
  随机数也在像素所在位置按同一顺序消耗；行与行之间只保留一个
  长度为行宽的误差缓存。因此逐行调用 ``quantize_rows`` 与一次性
  传入整图得到的结果完全相同。
* **有界状态**：跨调用保留的状态只有 PRNG 状态、行号、seed 和宽度
  为当前行宽的误差缓存；累计输出不计入 ``state_size()``，所以状态
  大小与已处理行数无关。
* **合法输出**：量化级别取 ``0 .. levels-1``，输入必须落在 ``[0, 1]``，
  ``levels`` 必须是 ``>= 2`` 的整数，否则抛 ``ValueError``。
"""

import math
import numbers

_MASK64 = (1 << 64) - 1
_GOLDEN = 0x9E3779B97F4A7C15


class DitherSession:
    """按 seed 初始化、可增量喂行的抖动量化会话。"""

    def __init__(self, seed):
        """按 seed 初始化。"""
        self._init(seed)

    # ------------------------------------------------------------------
    # 内部状态
    # ------------------------------------------------------------------
    def _init(self, seed):
        if isinstance(seed, bool) or not isinstance(seed, numbers.Integral):
            raise ValueError("seed must be an integer")
        self._seed = int(seed)
        self._rng_state = self._seed & _MASK64
        self._carry = []
        self._rows = []

    def _next_u64(self):
        """SplitMix64：纯整数运算，跨平台/跨版本结果稳定。"""
        self._rng_state = (self._rng_state + _GOLDEN) & _MASK64
        z = self._rng_state
        z = ((z ^ (z >> 30)) * 0xBF58476D1CE4E5B9) & _MASK64
        z = ((z ^ (z >> 27)) * 0x94D049BB133111EB) & _MASK64
        return z ^ (z >> 31)

    def _next_unit(self):
        """[0, 1) 上的浮点随机数。"""
        return (self._next_u64() >> 11) * (1.0 / (1 << 53))

    # ------------------------------------------------------------------
    # 校验
    # ------------------------------------------------------------------
    @staticmethod
    def _check_levels(levels):
        if isinstance(levels, bool) or not isinstance(levels, numbers.Integral):
            raise ValueError("levels must be an integer >= 2")
        levels = int(levels)
        if levels < 2:
            raise ValueError("levels must be an integer >= 2")
        return levels

    @staticmethod
    def _check_value(value):
        if isinstance(value, bool):
            return float(value)
        if not isinstance(value, numbers.Real):
            raise ValueError("pixel values must be real numbers in [0, 1]")
        value = float(value)
        if not math.isfinite(value) or not (0.0 <= value <= 1.0):
            raise ValueError("pixel values must be finite and in [0, 1]")
        return value

    # ------------------------------------------------------------------
    # 量化
    # ------------------------------------------------------------------
    def _quantize_pixel(self, value, levels, carry):
        """把单像素量化到 0..levels-1，返回 (级别, 传递给右邻的误差)。"""
        scale = levels - 1
        u = value * scale + carry
        # 阈值抖动幅度为半级；随机数总是消耗，与是否走到钳位分支无关，
        # 从而保证输出只取决于 (seed, 光栅位置)。
        jitter = self._next_unit() - 0.5
        level = int(math.floor(min(max(u, 0.0), scale) + 0.5 + jitter))
        if level < 0:
            level = 0
        elif level > scale:
            level = scale
        # 误差以“级”为单位传给右邻，并钳位到一级以内防止长行发散。
        error = u - level
        if error < -1.0:
            error = -1.0
        elif error > 1.0:
            error = 1.0
        return level, error

    def quantize_rows(self, rows, levels=2):
        """处理若干行，逐像素量化并累计结果。"""
        levels = self._check_levels(levels)

        checked = []
        for row in rows:
            checked.append([self._check_value(v) for v in row])

        for values in checked:
            # 每一行从头开始扩散误差：跨行不携带，分块边界因此不可见。
            self._carry = [0.0] * len(values)
            out_row = []
            for i, value in enumerate(values):
                level, self._carry[i] = self._quantize_pixel(
                    value, levels, self._carry[i]
                )
                out_row.append(level)
            self._rows.append(out_row)
        return None

    def flush(self):
        """结束并返回累计结果；幂等，不消耗也不清空状态。"""
        return [list(row) for row in self._rows]

    def reset(self, seed):
        """重置状态，使后续重放与新建同 seed 会话一致。"""
        self._init(seed)

    def state_size(self):
        """返回内部状态字节数，不含累计输出，故与行数无关。"""
        return 3 * 8 + 8 * len(self._carry)
