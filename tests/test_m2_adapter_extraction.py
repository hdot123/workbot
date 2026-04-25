"""M2 adapter extraction 必补测试。

本文件覆盖 memory_hook_impls 中 adapter 层的关键行为：
- delegate noop 响应
- CMUX_HOOK_STATE_FILE 严格注入策略
- artifact/compaction 策略
- adapter hook contract 文档约束
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from workspace.tools.memory_hook_impls import (
    ClaudeDelegate,
    CodexDelegate,
    _apply_artifact_compaction,
    _delegate_noop_response,
    _get_host_delegate,
    build_workbot_runtime_profile,
    main,
)

# ---------------------------------------------------------------------------
# 测试组 1：delegate gate 测试
# ---------------------------------------------------------------------------


class TestDelegateGate:
    """验证 Codex/Claude delegate 的 noop 响应行为。"""

    def test_codex_delegate_noop_response_returns_empty_json(self) -> None:
        """验证 CodexDelegate().noop_response() 返回 returncode=0, stdout="{}\\n", stderr=""。"""
        delegate = CodexDelegate()
        result = delegate.noop_response()
        assert result.returncode == 0
        assert result.stdout == "{}\n"
        assert result.stderr == ""

    def test_claude_delegate_noop_response_returns_empty(self) -> None:
        """验证 ClaudeDelegate().noop_response() 返回 returncode=0, stdout="", stderr=""。"""
        delegate = ClaudeDelegate()
        result = delegate.noop_response()
        assert result.returncode == 0
        assert result.stdout == ""
        assert result.stderr == ""

    def test_gateway_noop_uses_delegate_not_host_branch(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """验证 _delegate_noop_response("codex") 调用 delegate.noop_response() 而不是硬编码输出。

        monkeypatch _get_host_delegate 返回一个 mock delegate，验证其 noop_response 被调用。
        """
        mock_delegate = MagicMock()
        mock_result = subprocess.CompletedProcess(
            args=["noop"], returncode=0, stdout="{}\n", stderr=""
        )
        mock_delegate.noop_response.return_value = mock_result

        monkeypatch.setattr(
            "workspace.tools.memory_hook_impls._get_host_delegate",
            lambda host, **kwargs: mock_delegate,
        )

        result = _delegate_noop_response("codex")
        mock_delegate.noop_response.assert_called_once()
        assert result.returncode == 0

    def test_main_stdout_fallback_uses_delegate_noop(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """验证 main() 在 proc.stdout 为空时通过 delegate.noop_response() 获取输出。"""
        mock_delegate = MagicMock()
        # execute returns empty stdout
        mock_execute_result = subprocess.CompletedProcess(
            args=["cmux", "noop"], returncode=0, stdout="", stderr=""
        )
        mock_noop_result = subprocess.CompletedProcess(
            args=["noop"], returncode=0, stdout="{}\n", stderr=""
        )
        mock_delegate.execute.return_value = mock_execute_result
        mock_delegate.noop_response.return_value = mock_noop_result

        monkeypatch.setattr(
            "workspace.tools.memory_hook_impls._get_host_delegate",
            lambda host, **kwargs: mock_delegate,
        )

        result = main(host="codex")
        mock_delegate.execute.assert_called_once_with("noop", "{}", {})
        mock_delegate.noop_response.assert_called_once()
        assert result.stdout == "{}\n"

# ---------------------------------------------------------------------------
# 测试组 2：CMUX_HOOK_STATE_FILE strictness 测试
# ---------------------------------------------------------------------------


class TestStateFileStrictness:
    """验证 ClaudeDelegate 的 state_file 注入策略。"""

    def test_claude_delegate_state_file_not_read_from_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """验证 ClaudeDelegate 不从 os.environ 读取 CMUX_HOOK_STATE_FILE。

        设置 os.environ["CMUX_HOOK_STATE_FILE"]="/some/path"，创建 ClaudeDelegate(state_file=None)，
        验证 _state_file 仍为 None。
        """
        monkeypatch.setenv("CMUX_HOOK_STATE_FILE", "/some/path")
        delegate = ClaudeDelegate(state_file=None)
        assert delegate._state_file is None

    def test_claude_delegate_state_file_injected_by_constructor(self) -> None:
        """验证 ClaudeDelegate(state_file="/injected/path")._state_file == "/injected/path"。"""
        delegate = ClaudeDelegate(state_file="/injected/path")
        assert delegate._state_file == "/injected/path"

    def test_runtime_profile_resolves_state_file_from_env(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """验证 build_workbot_runtime_profile 返回的 dict 包含 CLAUDE_HOOK_STATE_FILE 键。"""
        monkeypatch.setenv("CMUX_HOOK_STATE_FILE", "/runtime/state.json")
        profile = build_workbot_runtime_profile()
        assert "CLAUDE_HOOK_STATE_FILE" in profile
        assert profile["CLAUDE_HOOK_STATE_FILE"] == "/runtime/state.json"

# ---------------------------------------------------------------------------
# 测试组 3：artifact/compaction policy 测试
# ---------------------------------------------------------------------------


class TestArtifactCompaction:
    """验证 artifact compaction 策略。"""

    def test_runtime_profile_contains_compaction_policy(self) -> None:
        """验证 build_workbot_runtime_profile 返回的 dict 包含 ARTIFACT_COMPACTION 键，
        且有 6 个 include_* 布尔开关。"""
        profile = build_workbot_runtime_profile()
        assert "ARTIFACT_COMPACTION" in profile
        compaction = profile["ARTIFACT_COMPACTION"]
        expected_keys = {
            "include_system_context",
            "include_project_context",
            "include_allowed_reads",
            "include_allowed_writes",
            "include_evidence_refs",
            "include_warnings",
        }
        assert expected_keys == set(compaction.keys())
        for v in compaction.values():
            assert isinstance(v, bool)

    def test_compaction_all_true_preserves_all_sections(self) -> None:
        """验证 _apply_artifact_compaction 在全 True 时不裁剪任何内容。"""
        package = {
            "system_context": {"key": "value"},
            "project_context": {"scope": "workbot"},
            "allowed_reads": ["path1"],
            "allowed_writes": {"kb": "path2"},
            "evidence_refs": ["ref1"],
            "warnings": ["warn1"],
            "other_field": "kept",
        }
        result = _apply_artifact_compaction(
            package,
            include_system_context=True,
            include_project_context=True,
            include_allowed_reads=True,
            include_allowed_writes=True,
            include_evidence_refs=True,
            include_warnings=True,
        )
        assert result == package

    def test_compaction_can_remove_system_context(self) -> None:
        """验证设置 include_system_context=False 后 system_context 被移除。"""
        package = {
            "system_context": {"key": "value"},
            "project_context": {"scope": "workbot"},
        }
        result = _apply_artifact_compaction(
            package,
            include_system_context=False,
        )
        assert "system_context" not in result
        assert "project_context" in result

    def test_compaction_can_remove_multiple_sections(self) -> None:
        """验证同时关闭多个 include_* 后对应字段被移除。"""
        package = {
            "system_context": {"key": "value"},
            "project_context": {"scope": "workbot"},
            "allowed_reads": ["path1"],
            "allowed_writes": {"kb": "path2"},
            "evidence_refs": ["ref1"],
            "warnings": ["warn1"],
            "other_field": "kept",
        }
        result = _apply_artifact_compaction(
            package,
            include_system_context=False,
            include_project_context=False,
            include_allowed_reads=False,
            include_allowed_writes=False,
            include_evidence_refs=False,
            include_warnings=False,
        )
        assert "system_context" not in result
        assert "project_context" not in result
        assert "allowed_reads" not in result
        assert "allowed_writes" not in result
        assert "evidence_refs" not in result
        assert "warnings" not in result
        assert result["other_field"] == "kept"

# ---------------------------------------------------------------------------
# 测试组 4：adapter hook contract 测试
# ---------------------------------------------------------------------------


class TestHookContract:
    """验证 workbot-hook-contract.md 的 adapter 合同约束。"""

    @pytest.fixture
    def contract_path(self) -> Path:
        """返回 workbot-hook-contract.md 的绝对路径。"""
        return Path(__file__).resolve().parents[1] / "workspace" / "memory" / "kb" / "global" / "workbot-hook-contract.md"

    @pytest.fixture
    def contract_text(self, contract_path: Path) -> str:
        """读取合同文件内容。"""
        assert contract_path.exists(), f"contract file not found: {contract_path}"
        return contract_path.read_text(encoding="utf-8")

    def test_hook_contract_has_adapter_scope(self, contract_text: str) -> None:
        """验证 frontmatter 包含 scope: adapter。"""
        assert "scope: adapter" in contract_text

    def test_hook_contract_title_contains_adapter(self, contract_text: str) -> None:
        """验证标题包含 'Adapter'。"""
        assert "Adapter" in contract_text

    def test_hook_contract_not_module_global_default(self, contract_text: str) -> None:
        """验证文件中包含'不是模块全局默认合同'。"""
        assert "不是模块全局默认合同" in contract_text

    def test_hook_contract_allows_other_adapters(self, contract_text: str) -> None:
        """验证文件中包含'其他 adapter 可以定义自己的合同'。"""
        assert "其他 adapter 可以定义自己的合同" in contract_text
