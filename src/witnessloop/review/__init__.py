"""``witnessloop review``：多模型复审闭环（change review-loop / T-071）。

这是**证据产出**一侧的新动词，与 ``check`` 的门禁判定正交——不重写
``contract`` / ``evidence`` / ``checkcmd`` 里的任何判据。闭环把两个零记忆 reviewer
的 findings 合并去重、交给 fixer 修、直到收敛 / 停滞升级 / 成本止损；
每轮 manifest 绑 ``actors[]`` 与 ``config.resolved.json`` 的哈希，``review report --md`` 读回。

模块：

- ``revision``  两种 revision 锚点（Git / Digest）+ ``mode: auto`` 探测
- ``roles``     roles@v1 配置：读入、展开成 ``config.resolved.json``
- ``adapters``  ``claude`` / ``codex`` / ``mock`` 三种通路，统一接口
- ``orchestrator`` ``review run``：并发审 → 合并去重 → fixer → 收敛判定
- ``report``    ``review report --md`` 读回 + 四条负样本验证
"""
