"""ditherkit 核心 API（初始未实现）。"""


class DitherSession:
    def __init__(self, seed):
        """按 seed 初始化"""
        raise NotImplementedError

    def quantize_rows(self, rows, levels):
        """处理若干行"""
        raise NotImplementedError

    def flush(self):
        """结束并返回累计结果"""
        raise NotImplementedError

    def reset(self, seed):
        """重置状态"""
        raise NotImplementedError

    def state_size(self):
        """返回内部状态字节数"""
        raise NotImplementedError
