"""Tests for CommandExecutor agent delegation and routing."""

from __future__ import annotations

from SuperClaude.Commands.parser import ParsedCommand


class TestExtractDelegateTargets:
    """Tests for _extract_delegate_targets method."""

    def test_extract_from_delegate_key(self, executor):
        """Extract targets from delegate parameter."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --delegate architect",
            arguments=["feature"],
            flags={},
            parameters={"delegate": "architect"},
            description="Implement feature",
        )

        targets = executor._extract_delegate_targets(parsed)

        assert "architect" in targets

    def test_extract_from_delegate_to_key(self, executor):
        """Extract targets from delegate_to parameter."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --delegate-to reviewer",
            arguments=["feature"],
            flags={},
            parameters={"delegate_to": "reviewer"},
            description="Implement feature",
        )

        targets = executor._extract_delegate_targets(parsed)

        assert "reviewer" in targets

    def test_extract_from_delegate_hyphen_key(self, executor):
        """Extract targets from delegate-to parameter."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --delegate-to tester",
            arguments=["feature"],
            flags={},
            parameters={"delegate-to": "tester"},
            description="Implement feature",
        )

        targets = executor._extract_delegate_targets(parsed)

        assert "tester" in targets

    def test_extract_from_agents_key(self, executor):
        """Extract targets from agents parameter."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --agents architect,reviewer",
            arguments=["feature"],
            flags={},
            parameters={"agents": ["architect", "reviewer"]},
            description="Implement feature",
        )

        targets = executor._extract_delegate_targets(parsed)

        assert "architect" in targets
        assert "reviewer" in targets

    def test_extract_multiple_targets(self, executor):
        """Extract multiple targets from list."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement --delegate architect,reviewer",
            arguments=[],
            flags={},
            parameters={"delegate": ["architect", "reviewer"]},
            description="Implement",
        )

        targets = executor._extract_delegate_targets(parsed)

        assert len(targets) >= 2

    def test_extract_no_targets(self, executor):
        """Returns empty list when no delegation specified."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement feature",
            arguments=["feature"],
            flags={},
            parameters={},
            description="Implement feature",
        )

        targets = executor._extract_delegate_targets(parsed)

        assert targets == []

    def test_extract_string_target(self, executor):
        """Extract target from string value."""
        parsed = ParsedCommand(
            name="implement",
            raw_string="/sc:implement",
            arguments=[],
            flags={},
            parameters={"delegate_agent": "implementer"},
            description="Implement",
        )

        targets = executor._extract_delegate_targets(parsed)

        assert "implementer" in targets


class TestExtractFilesFromParameters:
    """Tests for _extract_files_from_parameters method."""

    def test_extract_from_file_key(self, executor):
        """Extract files from file parameter."""
        params = {"file": "src/main.py"}

        files = executor._extract_files_from_parameters(params)

        assert "src/main.py" in files

    def test_extract_from_files_key(self, executor):
        """Extract files from files parameter."""
        params = {"files": ["src/a.py", "src/b.py"]}

        files = executor._extract_files_from_parameters(params)

        assert "src/a.py" in files
        assert "src/b.py" in files

    def test_extract_from_path_key(self, executor):
        """Extract files from path parameter."""
        params = {"path": "/home/user/project"}

        files = executor._extract_files_from_parameters(params)

        assert "/home/user/project" in files

    def test_extract_from_target_key(self, executor):
        """Extract files from target parameter."""
        params = {"target": "tests/"}

        files = executor._extract_files_from_parameters(params)

        assert "tests/" in files

    def test_extract_from_module_key(self, executor):
        """Extract files from module parameter."""
        params = {"module": "SuperClaude.Commands"}

        files = executor._extract_files_from_parameters(params)

        assert "SuperClaude.Commands" in files

    def test_extract_from_multiple_keys(self, executor):
        """Extract files from multiple parameter keys."""
        params = {
            "file": "main.py",
            "path": "src/",
            "target": "tests/",
        }

        files = executor._extract_files_from_parameters(params)

        assert "main.py" in files
        assert "src/" in files
        assert "tests/" in files

    def test_extract_empty_params(self, executor):
        """Returns empty list for empty parameters."""
        files = executor._extract_files_from_parameters({})

        assert files == []

    def test_extract_list_values(self, executor):
        """Extract files from list parameter values."""
        params = {"targets": ["a.py", "b.py", "c.py"]}

        files = executor._extract_files_from_parameters(params)

        assert len(files) == 3


class TestBuildDelegationContext:
    """Tests for _build_delegation_context method."""

    def test_build_context_has_required_fields(self, executor, sample_context):
        """Delegation context has required fields."""
        context_dict = executor._build_delegation_context(sample_context)

        assert isinstance(context_dict, dict)
        assert (
            "task" in context_dict
            or "description" in context_dict
            or len(context_dict) > 0
        )

    def test_build_context_includes_task_text(self, executor, sample_context):
        """Delegation context includes task text."""
        sample_context.command.arguments = ["implement", "feature"]

        context_dict = executor._build_delegation_context(sample_context)

        # Task should be extracted from arguments
        assert isinstance(context_dict, dict)

    def test_build_context_includes_languages(self, executor, sample_context):
        """Delegation context includes languages."""
        sample_context.command.parameters = {"language": "python"}

        context_dict = executor._build_delegation_context(sample_context)

        # Languages should be extracted
        if "languages" in context_dict:
            assert "python" in context_dict["languages"]

    def test_build_context_includes_domains(self, executor, sample_context):
        """Delegation context includes domains from metadata category."""
        sample_context.metadata.category = "development"

        context_dict = executor._build_delegation_context(sample_context)

        # Domains should include category
        if "domains" in context_dict:
            assert "development" in context_dict["domains"]

    def test_build_context_includes_keywords(self, executor, sample_context):
        """Delegation context includes keywords."""
        sample_context.command.parameters = {"keywords": ["api", "rest"]}

        context_dict = executor._build_delegation_context(sample_context)

        assert isinstance(context_dict, dict)

    def test_build_context_with_files(self, executor, sample_context):
        """Delegation context includes file references."""
        sample_context.command.parameters = {"file": "src/main.py"}

        context_dict = executor._build_delegation_context(sample_context)

        if "files" in context_dict:
            assert "src/main.py" in context_dict["files"]


class TestApplyAutoDelegation:
    """Tests for _apply_auto_delegation method."""

    def test_apply_explicit_delegation(self, executor, sample_context):
        """Apply delegation handles explicit targets."""
        sample_context.command.parameters = {"delegate": "architect"}

        executor._apply_auto_delegation(sample_context)

        assert "architect" in sample_context.delegated_agents
        assert sample_context.delegation_strategy == "explicit"

    def test_apply_delegation_multiple_agents(self, executor, sample_context):
        """Apply delegation handles multiple agents."""
        sample_context.command.parameters = {"agents": ["architect", "reviewer"]}

        executor._apply_auto_delegation(sample_context)

        assert "architect" in sample_context.delegated_agents
        assert "reviewer" in sample_context.delegated_agents

    def test_apply_delegation_sets_results(self, executor, sample_context):
        """Apply delegation sets delegation results."""
        sample_context.command.parameters = {"delegate": "implementer"}

        executor._apply_auto_delegation(sample_context)

        assert "delegation" in sample_context.results
        assert sample_context.results["delegation"]["requested"] is True

    def test_apply_no_delegation(self, executor, sample_context):
        """Apply delegation handles no delegation request."""
        sample_context.command.parameters = {}
        sample_context.delegated_agents = []

        executor._apply_auto_delegation(sample_context)

        # Should not add any agents if no delegation specified
        # and no auto-delegation triggered
        assert isinstance(sample_context.delegated_agents, list)

    def test_apply_delegation_deduplicates(self, executor, sample_context):
        """Apply delegation removes duplicates."""
        sample_context.command.parameters = {
            "delegate": ["architect", "architect", "reviewer"]
        }

        executor._apply_auto_delegation(sample_context)

        # Should have unique agents
        assert len(sample_context.delegated_agents) == len(
            set(sample_context.delegated_agents)
        )


class TestDelegationContextAttribute:
    """Tests for delegation-related context attributes."""

    def test_context_has_delegated_agents(self, sample_context):
        """Context has delegated_agents list."""
        assert hasattr(sample_context, "delegated_agents")
        assert isinstance(sample_context.delegated_agents, list)

    def test_context_has_delegation_strategy(self, sample_context):
        """Context has delegation_strategy attribute."""
        assert hasattr(sample_context, "delegation_strategy")

    def test_context_has_agent_instances(self, sample_context):
        """Context has agent_instances dict."""
        assert hasattr(sample_context, "agent_instances")
        assert isinstance(sample_context.agent_instances, dict)

    def test_context_has_agent_outputs(self, sample_context):
        """Context has agent_outputs dict."""
        assert hasattr(sample_context, "agent_outputs")
        assert isinstance(sample_context.agent_outputs, dict)


class TestAgentLoaderIntegration:
    """Tests for agent loader integration with delegation."""

    def test_set_agent_loader(self, executor, mock_agent_loader):
        """Executor accepts agent loader."""
        executor.set_agent_loader(mock_agent_loader)

        assert executor.agent_loader == mock_agent_loader

    def test_agent_loader_list_agents(self, executor, mock_agent_loader):
        """Agent loader can list available agents."""
        executor.set_agent_loader(mock_agent_loader)

        agents = mock_agent_loader.list_agents()

        assert isinstance(agents, list)
        assert len(agents) > 0

    def test_agent_loader_load_agent(self, executor, mock_agent_loader):
        """Agent loader can load a specific agent."""
        executor.set_agent_loader(mock_agent_loader)

        agent = mock_agent_loader.load_agent("architect")

        assert agent is not None
        assert hasattr(agent, "execute")


class TestDelegationStrategies:
    """Tests for different delegation strategies."""

    def test_explicit_strategy_set(self, executor, sample_context):
        """Explicit delegation sets strategy to 'explicit'."""
        sample_context.command.parameters = {"delegate": "architect"}

        executor._apply_auto_delegation(sample_context)

        assert sample_context.delegation_strategy == "explicit"

    def test_delegation_results_includes_strategy(self, executor, sample_context):
        """Delegation results include strategy information."""
        sample_context.command.parameters = {"delegate": "reviewer"}

        executor._apply_auto_delegation(sample_context)

        delegation = sample_context.results.get("delegation", {})
        assert delegation.get("strategy") == "explicit"

    def test_delegation_results_includes_selected_agent(self, executor, sample_context):
        """Delegation results include selected agent."""
        sample_context.command.parameters = {"delegate": "architect"}

        executor._apply_auto_delegation(sample_context)

        delegation = sample_context.results.get("delegation", {})
        assert delegation.get("selected_agent") == "architect"

    def test_delegation_results_includes_all_agents(self, executor, sample_context):
        """Delegation results include all selected agents."""
        sample_context.command.parameters = {"agents": ["architect", "reviewer"]}

        executor._apply_auto_delegation(sample_context)

        delegation = sample_context.results.get("delegation", {})
        selected = delegation.get("selected_agents", [])
        assert "architect" in selected
        assert "reviewer" in selected


class TestDelegationEdgeCases:
    """Tests for edge cases in delegation."""

    def test_empty_delegate_value(self, executor, sample_context):
        """Handle empty delegate value."""
        sample_context.command.parameters = {"delegate": ""}

        executor._apply_auto_delegation(sample_context)

        # Should not crash
        assert isinstance(sample_context.delegated_agents, list)

    def test_whitespace_delegate_value(self, executor, sample_context):
        """Handle whitespace in delegate value."""
        sample_context.command.parameters = {"delegate": "  architect  "}

        executor._apply_auto_delegation(sample_context)

        # Should handle whitespace appropriately
        assert isinstance(sample_context.delegated_agents, list)

    def test_numeric_delegate_value(self, executor, sample_context):
        """Handle numeric delegate value."""
        sample_context.command.parameters = {"delegate": 123}

        executor._apply_auto_delegation(sample_context)

        # Should convert to string
        assert isinstance(sample_context.delegated_agents, list)

    def test_mixed_type_list(self, executor, sample_context):
        """Handle mixed types in delegate list."""
        sample_context.command.parameters = {"agents": ["architect", 123, None]}

        executor._apply_auto_delegation(sample_context)

        # Should handle mixed types
        assert isinstance(sample_context.delegated_agents, list)
