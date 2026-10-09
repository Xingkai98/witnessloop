"""witnessloop —— 把 agent 写代码的证据绑进 CI 门禁。

单二进制，3 个门禁动词 + 1 个证据产出动词（design §5.1）：

- ``init``            接入目标仓：幂等 / 只增不改 / 不 auto-commit / ``--dry-run``
- ``uninit``          依 init 台账精确回滚：文件被改过则拒绝删除并报 diff
- ``check``           CI 入口，fail-closed：change 契约 / 审阅证据 / 受保护写入 / 不变集
- ``manifest build``  产出 check 认的 review manifest（与 check 共用同一套哈希）

模块：

- ``cli``       子命令路由
- ``constants`` 跨模块契约字面量（v1 硬编码 OpenSpec 形状，无 spec 适配器）
- ``policy``    目标仓策略 + witnessloop 自身的不变集
- ``contract``  change 目录契约 + review manifest 校验
- ``events``    ``workflow-events.jsonl`` 的结构化解释事件
- ``paths``     路径归一化与 ``**`` 感知的 glob 匹配
- ``hashing``   确定性哈希（文件 / 目录树）
- ``gitutil``   只读 git 读取封装
"""

__version__ = "0.1.0"
