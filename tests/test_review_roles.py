"""P3：roles@v1 配置——读入 / 展开 / config.resolved.json 哈希。"""

from __future__ import annotations

import json

from witnessloop import constants as C
from witnessloop.review import roles as roles_mod


def test_default_roles_have_four_roles():
    doc = roles_mod.default_roles_doc()
    assert doc["schema"] == C.REVIEW_ROLES_SCHEMA
    assert set(doc["roles"]) == {"reviewerA", "reviewerB", "fixer", "judge"}


def test_default_base_urls_match_adapter_splicing():
    """出厂 base_url 必须与适配器的 URL 拼接**对齐**（T-075 回归）。

    - ``codex`` 拼 `/chat/completions` ⇒ base_url 停在 `…/v1`。
    - ``claude`` 拼 `/v1/messages` ⇒ base_url 不能带 `/v1`（否则打成 `/v1/v1/messages`）。
    """
    doc = roles_mod.default_roles_doc()
    assert doc["roles"]["reviewerA"]["base_url"] == "https://heyroute.ai/v1"
    assert doc["roles"]["reviewerB"]["base_url"] == "https://heyroute.ai"


def test_load_roles_falls_back_to_default_when_missing(tmp_path):
    assert roles_mod.load_roles(tmp_path)["roles"]["reviewerA"]["model"] == "gpt-6.1-terra"


def test_load_roles_merges_partial_overrides(tmp_path, monkeypatch):
    (tmp_path / C.REVIEW_ROLES_PATH).write_text(
        json.dumps({"roles": {"reviewerA": {"model": "custom-model"}}}), encoding="utf-8"
    )
    doc = roles_mod.load_roles(tmp_path)
    assert doc["roles"]["reviewerA"]["model"] == "custom-model"
    # 未覆盖的角色保持默认
    assert doc["roles"]["reviewerB"]["model"] == "glm-5.3"


def test_resolve_config_records_auth_resolved(tmp_path, monkeypatch):
    monkeypatch.setenv("WITNESSLOOP_CODEX_KEY", "k")
    monkeypatch.delenv("WITNESSLOOP_GLM_KEY", raising=False)
    resolved, warnings = roles_mod.resolve_config(tmp_path)
    assert resolved["roles"]["reviewerA"]["auth_resolved"] is True
    assert resolved["roles"]["reviewerB"]["auth_resolved"] is False
    assert any("reviewerB" in w for w in warnings)


def test_resolve_config_adapter_override_forces_all_roles(tmp_path):
    resolved, _ = roles_mod.resolve_config(tmp_path, adapter="mock")
    for name in ("reviewerA", "reviewerB", "fixer", "judge"):
        assert resolved["roles"][name]["adapter"] == "mock"


def test_config_hash_is_stable_for_same_doc(tmp_path):
    doc, _ = roles_mod.resolve_config(tmp_path, adapter="mock")
    assert roles_mod.config_hash(doc) == roles_mod.config_hash(doc)
    # 改一点 ⇒ 哈希变
    doc2, _ = roles_mod.resolve_config(tmp_path, adapter="mock", stall_rounds=3)
    assert roles_mod.config_hash(doc2) != roles_mod.config_hash(doc)


def test_write_config_lands_in_output_dir(tmp_path):
    doc, _ = roles_mod.resolve_config(tmp_path, adapter="mock")
    path = roles_mod.write_config(tmp_path, doc)
    assert path == tmp_path / C.REVIEW_OUTPUT_DIR / C.REVIEW_CONFIG_FILENAME
    assert json.loads(path.read_text(encoding="utf-8"))["schema"] == C.REVIEW_ROLES_SCHEMA
