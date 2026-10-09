"""witnessloop —— 把 agent 写代码的证据绑进 CI 门禁。

结构：
- ``cli``        子命令路由（init / uninit / check）
- ``policy``     目标仓策略 + witnessloop 自身的不变集
- ``contract``   OpenSpec 形状的 change 目录契约 + review manifest 校验
- ``events``     ``workflow-events.jsonl`` 里的结构化解释事件
- ``gitutil``    git 读取封装（check/uninit 依赖）
- ``hashing``    确定性哈希（文件 / 目录树）
"""

__version__ = "0.1.0"
