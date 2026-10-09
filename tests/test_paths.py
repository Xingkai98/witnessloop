"""glob 语义：把 docs/gate.md §2 的承诺逐条钉死。

reviewer I-4：全仓原先没有 test_paths.py，两个针对性变异全部存活——
`*` 跨 `/`（正是 design §9 警告的 fnmatch 坑）与 `**/` 不匹配零层目录
都能改坏实现而无人报警。契约已经写进文档，就必须有回归防线。

每条断言都对应一处可变异点（见提交说明里的变异证据）。
"""

from __future__ import annotations

import pytest

from witnessloop import paths
from witnessloop.policy import INVARIANT_PROTECTED_PATHS


class TestStarDoesNotCrossSeparator:
    """`*` 只在**一段之内**匹配——这是 `fnmatch` 的坑，也是本模块存在的理由。"""

    @pytest.mark.parametrize(
        "path,pattern,expected",
        [
            ("a/b/c.md", "a/*/c.md", True),
            ("a/bx/c.md", "a/*/c.md", True),
            ("a/b/x/c.md", "a/*/c.md", False),  # ← `*` 跨了 `/` 就会误命中
            ("reviews/x.manifest.json", "reviews/*.manifest.json", True),
            ("reviews/sub/x.manifest.json", "reviews/*.manifest.json", False),
            ("src/app.py", "src/*.py", True),
            ("src/deep/app.py", "src/*.py", False),
        ],
    )
    def test_star_stays_within_one_segment(self, path, pattern, expected):
        assert paths.matches(path, pattern) is expected


class TestQuestionMarkDoesNotCrossSeparator:
    @pytest.mark.parametrize(
        "path,pattern,expected",
        [
            ("ab", "a?", True),
            ("a", "a?", False),
            ("a/b", "a?b", False),  # `?` 不匹配 `/`
            ("aXb", "a?b", True),
        ],
    )
    def test_question_mark_stays_within_one_segment(self, path, pattern, expected):
        assert paths.matches(path, pattern) is expected


class TestDoubleStarMatchesZeroOrMoreLevels:
    """`**/` 必须匹配**零层**——否则顶层 `reviews/x.manifest.json` 会失配。"""

    @pytest.mark.parametrize(
        "path,pattern,expected",
        [
            ("x.md", "**/x.md", True),  # ← 零层
            ("a/x.md", "**/x.md", True),
            ("a/b/c/x.md", "**/x.md", True),
            ("a/b", "a/**/b", True),  # 中间零层
            ("a/x/b", "a/**/b", True),
            ("a/x/y/b", "a/**/b", True),
            ("a/b", "**/**/b", True),
        ],
    )
    def test_double_star_slash_matches_zero_levels(self, path, pattern, expected):
        assert paths.matches(path, pattern) is expected


class TestDoubleStarAtTail:
    @pytest.mark.parametrize(
        "path,pattern,expected",
        [
            ("openspec/specs/a/spec.md", "openspec/specs/**", True),
            ("openspec/specs/a/b/spec.md", "openspec/specs/**", True),
            ("**", "**", True),
            # `a/**` 要求斜杠：`a` 自身不算「a 之内」（同 gitignore 语义）
            ("a", "a/**", False),
            ("a/b", "a/**", True),
        ],
    )
    def test_double_star_at_tail(self, path, pattern, expected):
        assert paths.matches(path, pattern) is expected


class TestAnchoring:
    """匹配是**整串锚定**，不是前缀/子串匹配。"""

    @pytest.mark.parametrize(
        "path,pattern,expected",
        [
            ("a/bc", "a/b", False),
            ("ab", "a", False),
            ("x/a/b", "a/b", False),  # 不隐式匹配中间段
            ("a/b", "a/b", True),
        ],
    )
    def test_pattern_is_anchored(self, path, pattern, expected):
        assert paths.matches(path, pattern) is expected


class TestPrefixConstraintSurvives:
    """「前缀约束」不能被通配符吃掉（design §9 点名 fnmatch 会让它失效）。"""

    @pytest.mark.parametrize(
        "path,pattern,expected",
        [
            ("openspec/specs-backup/x.md", "openspec/specs/**", False),
            ("openspec/specs/a.md", "openspec/specs/**", True),
            (".witnessloopx/policy.json", ".witnessloop/**", False),
        ],
    )
    def test_prefix_constraint(self, path, pattern, expected):
        assert paths.matches(path, pattern) is expected


class TestNormalize:
    def test_backslash_becomes_slash(self):
        assert paths.normalize(r"a\b\c.md") == "a/b/c.md"

    def test_leading_dot_slash_stripped(self):
        assert paths.normalize("./a/b") == "a/b"
        assert paths.normalize("././a/b") == "a/b"

    def test_dot_directory_names_are_not_mangled(self):
        """回归：`str.lstrip("./")` 按字符集剥离，会把 .witnessloop/x 削成 witnessloop/x。"""
        assert paths.normalize(".witnessloop/policy.json") == ".witnessloop/policy.json"
        assert paths.normalize(".github/workflows/x.yml") == ".github/workflows/x.yml"
        # 且它仍然命中不变集——这是被削掉时静默失效的那条
        assert paths.matches(
            paths.normalize(".witnessloop/policy.json"), ".witnessloop/**"
        )

    def test_tilde_is_not_expanded(self):
        """声明的边界（gate.md §2）：输入恒为 git posix 相对路径，无 `~`。"""
        assert paths.normalize("~/.claude/x") == "~/.claude/x"

    def test_case_is_significant(self):
        """同样声明的边界：不折叠大小写。"""
        assert paths.matches("OpenSpec/Specs/X.md", "openspec/specs/**") is False

    def test_normalize_is_idempotent(self):
        once = paths.normalize("./a\\b")
        assert paths.normalize(once) == once


class TestMatchesAnyOverInvariantSet:
    @pytest.mark.parametrize(
        "path,expected",
        [
            (".witnessloop/policy.json", True),
            (".witnessloop/init-manifest.json", True),
            ("openspec/changes/x/reviews/b.manifest.json", True),
            ("reviews/b.manifest.json", True),  # 零层也要命中
            ("openspec/changes/x/workflow-events.jsonl", True),
            ("workflow-events.jsonl", True),
            ("openspec/specs/a/spec.md", False),
            ("src/app.py", False),
        ],
    )
    def test_invariant_membership(self, path, expected):
        assert paths.matches_any(path, INVARIANT_PROTECTED_PATHS) is expected


class TestIsWithin:
    @pytest.mark.parametrize(
        "path,parent,expected",
        [
            ("/repo/a/b.txt", "/repo", True),
            ("/repo/../secret.txt", "/repo", False),  # `..` 展开后出界
            ("/repo/a/../../secret.txt", "/repo", False),
            ("/other/secret.txt", "/repo", False),
            ("/repo", "/repo", True),
            ("/repo/sub", "/repo", True),
            # `..` 折回界内仍是界内——按**解析后**的真实位置判定
            ("/repo/a/../b.txt", "/repo", True),
        ],
    )
    def test_is_within(self, path, parent, expected):
        assert paths.is_within(path, parent) is expected
