"""Tests for SuperClaude Agents registry and selector modules."""

from __future__ import annotations

import pytest

yaml = pytest.importorskip("yaml", reason="PyYAML required for agent registry tests")

# --- AgentMarkdownParser Tests ---


class TestAgentMarkdownParser:
    """Tests for AgentMarkdownParser."""

    def test_parse_valid_frontmatter(self, tmp_path):
        """Should parse valid YAML frontmatter."""
        from SuperClaude.Agents.registry import AgentMarkdownParser

        md_file = tmp_path / "test-agent.md"
        md_file.write_text(
            "---\nname: test-agent\ncategory: testing\npriority: 1\n---\n\n# Test Agent\n"
        )

        parser = AgentMarkdownParser()
        result = parser.parse_file(md_file)
        assert result is not None
        assert result["name"] == "test-agent"
        assert result["category"] == "testing"

    def test_parse_no_frontmatter(self, tmp_path):
        """Should return None for markdown without frontmatter."""
        from SuperClaude.Agents.registry import AgentMarkdownParser

        md_file = tmp_path / "plain.md"
        md_file.write_text("# No Frontmatter\n\nJust text.")

        parser = AgentMarkdownParser()
        result = parser.parse_file(md_file)
        assert result is None

    def test_parse_invalid_yaml(self, tmp_path):
        """Should return None for invalid YAML in frontmatter."""
        from SuperClaude.Agents.registry import AgentMarkdownParser

        md_file = tmp_path / "bad.md"
        md_file.write_text("---\n[invalid: yaml: : :\n---\n\n# Bad\n")

        parser = AgentMarkdownParser()
        result = parser.parse_file(md_file)
        assert result is None

    def test_parse_nonexistent_file(self, tmp_path):
        """Should return None for missing file."""
        from SuperClaude.Agents.registry import AgentMarkdownParser

        parser = AgentMarkdownParser()
        result = parser.parse_file(tmp_path / "missing.md")
        assert result is None

    def test_parse_frontmatter_non_dict(self, tmp_path):
        """Should return None if frontmatter is not a dict (e.g., a list)."""
        from SuperClaude.Agents.registry import AgentMarkdownParser

        md_file = tmp_path / "list.md"
        md_file.write_text("---\n- item1\n- item2\n---\n\n# List FM\n")

        parser = AgentMarkdownParser()
        result = parser.parse_file(md_file)
        assert result is None

    def test_parse_unclosed_frontmatter(self, tmp_path):
        """Should return None if frontmatter is not closed."""
        from SuperClaude.Agents.registry import AgentMarkdownParser

        md_file = tmp_path / "unclosed.md"
        md_file.write_text("---\nname: test\nno closing marker")

        parser = AgentMarkdownParser()
        result = parser.parse_file(md_file)
        assert result is None


# --- AgentRegistry Tests ---


class TestAgentRegistryInit:
    """Tests for AgentRegistry initialization."""

    def test_init_with_custom_dir(self, tmp_path):
        """Should accept custom agents directory."""
        from SuperClaude.Agents.registry import AgentRegistry

        registry = AgentRegistry(agents_dir=tmp_path)
        assert registry.agents_dir == tmp_path

    def test_init_not_discovered(self, tmp_path):
        """Should not auto-discover on init."""
        from SuperClaude.Agents.registry import AgentRegistry

        registry = AgentRegistry(agents_dir=tmp_path)
        assert registry._discovered is False

    def test_empty_tiers_on_init(self, tmp_path):
        """Should have empty tier lists on init."""
        from SuperClaude.Agents.registry import AgentRegistry

        registry = AgentRegistry(agents_dir=tmp_path)
        assert registry._tier_agents == {"core": [], "trait": [], "extension": []}


class TestAgentRegistryDiscovery:
    """Tests for agent discovery."""

    def _create_agent(self, directory, name, category="general", priority=None):
        """Helper to create a test agent markdown file."""
        directory.mkdir(parents=True, exist_ok=True)
        content = f"---\nname: {name}\ncategory: {category}\n"
        if priority is not None:
            content += f"priority: {priority}\n"
        content += f"---\n\n# {name}\n"
        (directory / f"{name}.md").write_text(content)

    def test_discover_core_agents(self, tmp_path):
        """Should discover agents from core/ directory."""
        from SuperClaude.Agents.registry import AgentRegistry

        self._create_agent(tmp_path / "core", "general-purpose")
        self._create_agent(tmp_path / "core", "code-writer")

        registry = AgentRegistry(agents_dir=tmp_path)
        count = registry.discover_agents()
        assert count == 2
        assert "general-purpose" in registry.get_all_agents()
        assert "code-writer" in registry.get_all_agents()

    def test_discover_extensions(self, tmp_path):
        """Should discover agents from extensions/ directory."""
        from SuperClaude.Agents.registry import AgentRegistry

        self._create_agent(tmp_path / "extensions", "database-expert")

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        assert "database-expert" in registry.get_all_agents()

    def test_discover_traits(self, tmp_path):
        """Should discover traits from traits/ directory (not selectable)."""
        from SuperClaude.Agents.registry import AgentRegistry

        self._create_agent(tmp_path / "traits", "minimal-changes")

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        assert "minimal-changes" not in registry.get_all_agents()  # Not selectable
        assert "minimal-changes" in registry.get_all_traits()

    def test_discover_sets_tier_info(self, tmp_path):
        """Discovered agents should have tier information."""
        from SuperClaude.Agents.registry import AgentRegistry

        self._create_agent(tmp_path / "core", "test-agent")

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        config = registry.get_agent_config("test-agent")
        assert config is not None
        assert config["tier"] == "core"
        assert config["is_core"] is True

    def test_discover_default_priorities(self, tmp_path):
        """Core agents should get priority 1, extensions priority 2."""
        from SuperClaude.Agents.registry import AgentRegistry

        self._create_agent(tmp_path / "core", "core-agent")
        self._create_agent(tmp_path / "extensions", "ext-agent")

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        assert registry.get_agent_config("core-agent")["priority"] == 1
        assert registry.get_agent_config("ext-agent")["priority"] == 2

    def test_discover_skip_already_discovered(self, tmp_path):
        """Second call without force should skip discovery."""
        from SuperClaude.Agents.registry import AgentRegistry

        self._create_agent(tmp_path / "core", "agent1")

        registry = AgentRegistry(agents_dir=tmp_path)
        count1 = registry.discover_agents()
        # Add another agent after first discovery
        self._create_agent(tmp_path / "core", "agent2")
        count2 = registry.discover_agents()  # Should skip
        assert count2 == count1  # Same count, no re-scan

    def test_discover_force_rediscovery(self, tmp_path):
        """force=True should re-discover even if already discovered."""
        from SuperClaude.Agents.registry import AgentRegistry

        self._create_agent(tmp_path / "core", "agent1")

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        self._create_agent(tmp_path / "core", "agent2")
        count = registry.discover_agents(force=True)
        assert count == 2

    def test_discover_nonexistent_dirs(self, tmp_path):
        """Empty agents dir should return 0."""
        from SuperClaude.Agents.registry import AgentRegistry

        registry = AgentRegistry(agents_dir=tmp_path)
        count = registry.discover_agents()
        assert count == 0

    def test_get_agents_by_tier(self, tmp_path):
        """Should return agents for a specific tier."""
        from SuperClaude.Agents.registry import AgentRegistry

        self._create_agent(tmp_path / "core", "c1")
        self._create_agent(tmp_path / "extensions", "e1")

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        assert "c1" in registry.get_agents_by_tier("core")
        assert "e1" in registry.get_agents_by_tier("extension")
        assert registry.get_agents_by_tier("nonexistent") == []

    def test_get_agents_by_category(self, tmp_path):
        """Should return agents in a category."""
        from SuperClaude.Agents.registry import AgentRegistry

        self._create_agent(tmp_path / "core", "writer", category="code")
        self._create_agent(tmp_path / "core", "reviewer", category="review")

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        assert "writer" in registry.get_agents_by_category("code")
        assert "reviewer" not in registry.get_agents_by_category("code")

    def test_is_valid_trait(self, tmp_path):
        """Should check if trait name exists."""
        from SuperClaude.Agents.registry import AgentRegistry

        self._create_agent(tmp_path / "traits", "careful")

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        assert registry.is_valid_trait("careful") is True
        assert registry.is_valid_trait("nonexistent") is False

    def test_get_agent_returns_none_for_missing(self, tmp_path):
        """get_agent for non-existent name should return None."""
        from SuperClaude.Agents.registry import AgentRegistry

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        assert registry.get_agent("missing") is None

    def test_get_trait_config_returns_none_for_missing(self, tmp_path):
        """get_trait_config for non-existent trait should return None."""
        from SuperClaude.Agents.registry import AgentRegistry

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        assert registry.get_trait_config("missing") is None


# --- SelectionResult Tests ---


class TestSelectionResult:
    """Tests for SelectionResult dataclass."""

    def test_defaults(self):
        """Should have sensible defaults."""
        from SuperClaude.Agents.selector import SelectionResult

        result = SelectionResult(agent_name="test", confidence=0.5)
        assert result.breakdown == {}
        assert result.matched_criteria == []
        assert result.alternatives == []
        assert result.traits_applied == []
        assert result.agent_path == ""
        assert result.trait_paths == []


# --- AgentSelector Tests ---


class TestAgentSelector:
    """Tests for AgentSelector."""

    def _setup_registry(self, tmp_path):
        """Create a registry with test agents."""
        from SuperClaude.Agents.registry import AgentRegistry

        core_dir = tmp_path / "core"
        core_dir.mkdir(parents=True, exist_ok=True)

        (core_dir / "general-purpose.md").write_text(
            "---\nname: general-purpose\ncategory: general\n"
            "triggers:\n  - implement\n  - build\n  - create\n---\n"
        )
        (core_dir / "code-reviewer.md").write_text(
            "---\nname: code-reviewer\ncategory: review\n"
            "triggers:\n  - review\n  - audit\n  - security\n---\n"
        )
        (core_dir / "test-writer.md").write_text(
            "---\nname: test-writer\ncategory: testing\n"
            "triggers:\n  - test\n  - coverage\n  - pytest\n---\n"
        )

        traits_dir = tmp_path / "traits"
        traits_dir.mkdir(parents=True, exist_ok=True)
        (traits_dir / "minimal-changes.md").write_text(
            "---\nname: minimal-changes\ncategory: modifier\n---\n"
        )
        (traits_dir / "rapid-prototype.md").write_text(
            "---\nname: rapid-prototype\ncategory: modifier\n---\n"
        )

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        return registry

    def test_select_matching_agent(self, tmp_path):
        """Should select the best matching agent."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        result = selector.select_agent("review the security of this code")
        assert result.agent_name == "code-reviewer"
        assert result.confidence > 0

    def test_select_test_writer(self, tmp_path):
        """Should select test-writer for testing context."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        result = selector.select_agent("write tests for the auth module using pytest")
        assert result.agent_name == "test-writer"

    def test_select_with_category_hint(self, tmp_path):
        """Category hint should influence selection."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        result = selector.select_agent("do something", category_hint="review")
        assert result.agent_name == "code-reviewer"

    def test_select_with_exclude(self, tmp_path):
        """Excluded agents should not be selected."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        result = selector.select_agent("review code", exclude_agents=["code-reviewer"])
        assert result.agent_name != "code-reviewer"

    def test_fallback_to_default(self, tmp_path):
        """Unrecognized context should fallback to general-purpose."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        result = selector.select_agent("zzz completely unknown task qqq")
        # Should still return something
        assert result.agent_name is not None
        assert result.confidence >= 0

    def test_alternatives_populated(self, tmp_path):
        """Selection result should include alternatives."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        result = selector.select_agent("implement and test something")
        # With 3 agents, should have some alternatives
        assert isinstance(result.alternatives, list)

    def test_find_best_match(self, tmp_path):
        """find_best_match should return name and confidence."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        name, score = selector.find_best_match("review this code")
        assert name is not None
        assert isinstance(score, float)

    def test_get_agent_suggestions(self, tmp_path):
        """get_agent_suggestions should return top N suggestions."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        suggestions = selector.get_agent_suggestions("implement feature", top_n=3)
        assert len(suggestions) <= 3
        assert all(isinstance(s, tuple) and len(s) == 2 for s in suggestions)

    def test_dict_context(self, tmp_path):
        """Should handle dict context with task and files."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        result = selector.select_agent(
            {
                "task": "review security",
                "description": "audit the auth module",
                "files": ["auth/login.py"],
            }
        )
        assert result.agent_name is not None
        assert result.confidence > 0


class TestTraitProcessing:
    """Tests for trait conflict and tension detection."""

    def test_trait_conflicts_detected(self, tmp_path):
        """Conflicting traits should be detected."""
        from SuperClaude.Agents.selector import TRAIT_CONFLICTS

        assert "rapid-prototype" in TRAIT_CONFLICTS["minimal-changes"]
        assert "minimal-changes" in TRAIT_CONFLICTS["rapid-prototype"]

    def test_trait_tensions_detected(self, tmp_path):
        """Tension traits should be detected."""
        from SuperClaude.Agents.selector import TRAIT_TENSIONS

        assert "cloud-native" in TRAIT_TENSIONS["legacy-friendly"]
        assert "legacy-friendly" in TRAIT_TENSIONS["cloud-native"]

    def test_process_traits_validates(self, tmp_path):
        """Should separate valid and invalid traits."""
        from SuperClaude.Agents.registry import AgentRegistry
        from SuperClaude.Agents.selector import AgentSelector

        traits_dir = tmp_path / "traits"
        traits_dir.mkdir(parents=True, exist_ok=True)
        (traits_dir / "valid-trait.md").write_text("---\nname: valid-trait\n---\n")

        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        selector = AgentSelector(registry)

        valid, invalid, conflicts, tensions = selector._process_traits(
            ["valid-trait", "nonexistent-trait"]
        )
        assert "valid-trait" in valid
        assert "nonexistent-trait" in invalid


class TestScoreCalculation:
    """Tests for score calculation components."""

    def _setup_registry(self, tmp_path):
        from SuperClaude.Agents.registry import AgentRegistry

        core_dir = tmp_path / "core"
        core_dir.mkdir(parents=True, exist_ok=True)
        (core_dir / "test-agent.md").write_text(
            "---\nname: test-agent\ncategory: testing\n"
            "triggers:\n  - test\n  - coverage\n"
            "file_patterns:\n  - test_\n  - spec_\n---\n"
        )
        registry = AgentRegistry(agents_dir=tmp_path)
        registry.discover_agents()
        return registry

    def test_trigger_matching(self, tmp_path):
        """Trigger words in context should boost score."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        config = registry.get_agent_config("test-agent")
        score_match, breakdown, matched = selector._calculate_score("run test coverage", config)
        score_no, _, _ = selector._calculate_score("unrelated task", config)
        assert score_match > score_no

    def test_file_pattern_matching(self, tmp_path):
        """File pattern matching should contribute to score."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        config = registry.get_agent_config("test-agent")
        score_files, _, _ = selector._calculate_score(
            {"task": "something", "files": ["test_auth.py"]}, config
        )
        score_no_files, _, _ = selector._calculate_score({"task": "something", "files": []}, config)
        assert score_files > score_no_files

    def test_category_hint_matching(self, tmp_path):
        """Category hint should boost matching category."""
        from SuperClaude.Agents.selector import AgentSelector

        registry = self._setup_registry(tmp_path)
        selector = AgentSelector(registry)
        config = registry.get_agent_config("test-agent")
        score_hint, _, matched = selector._calculate_score("task", config, category_hint="testing")
        score_no_hint, _, _ = selector._calculate_score("task", config, category_hint=None)
        assert score_hint > score_no_hint
        assert any("category" in m for m in matched)
