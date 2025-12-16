"""Tests for CommandExecutor workflow step generation."""

from __future__ import annotations


class TestGenerateWorkflowSteps:
    """Tests for _generate_workflow_steps method."""

    def test_generate_steps_returns_list(self, executor, sample_context):
        """Generate workflow steps returns list."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        assert isinstance(steps, list)

    def test_generate_steps_has_entries(self, executor, sample_context):
        """Generate workflow steps has multiple entries."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        assert len(steps) >= 1

    def test_step_has_id(self, executor, sample_context):
        """Each step has unique ID."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        ids = [step["id"] for step in steps]
        assert len(ids) == len(set(ids))

    def test_step_has_phase(self, executor, sample_context):
        """Each step has phase field."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        for step in steps:
            assert "phase" in step
            assert isinstance(step["phase"], str)

    def test_step_has_title(self, executor, sample_context):
        """Each step has title field."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        for step in steps:
            assert "title" in step
            assert isinstance(step["title"], str)

    def test_step_has_owner(self, executor, sample_context):
        """Each step has owner field."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        for step in steps:
            assert "owner" in step
            assert isinstance(step["owner"], str)

    def test_step_has_dependencies(self, executor, sample_context):
        """Each step has dependencies list."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        for step in steps:
            assert "dependencies" in step
            assert isinstance(step["dependencies"], list)

    def test_step_has_deliverables(self, executor, sample_context):
        """Each step has deliverables list."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        for step in steps:
            assert "deliverables" in step
            assert isinstance(step["deliverables"], list)


class TestWorkflowPhases:
    """Tests for workflow phase progression."""

    def test_has_analysis_phase(self, executor, sample_context):
        """Workflow includes Analysis phase."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )
        phases = {step["phase"] for step in steps}

        assert "Analysis" in phases

    def test_has_architecture_phase(self, executor, sample_context):
        """Workflow includes Architecture phase."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )
        phases = {step["phase"] for step in steps}

        assert "Architecture" in phases

    def test_has_planning_phase(self, executor, sample_context):
        """Workflow includes Planning phase."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )
        phases = {step["phase"] for step in steps}

        assert "Planning" in phases

    def test_has_implementation_phase(self, executor, sample_context):
        """Workflow includes Implementation phase."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )
        phases = {step["phase"] for step in steps}

        assert "Implementation" in phases

    def test_has_quality_phase(self, executor, sample_context):
        """Workflow includes Quality phase."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )
        phases = {step["phase"] for step in steps}

        assert "Quality" in phases

    def test_has_release_phase(self, executor, sample_context):
        """Workflow includes Release phase."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )
        phases = {step["phase"] for step in steps}

        assert "Release" in phases


class TestWorkflowStrategy:
    """Tests for different workflow strategies."""

    def test_agile_strategy(self, executor, sample_context):
        """Agile strategy adjusts planning title."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="agile",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        planning_steps = [s for s in steps if s["phase"] == "Planning"]
        assert len(planning_steps) >= 1

    def test_scrum_strategy(self, executor, sample_context):
        """Scrum strategy adjusts planning title."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="scrum",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        planning_steps = [s for s in steps if s["phase"] == "Planning"]
        assert len(planning_steps) >= 1

    def test_enterprise_strategy(self, executor, sample_context):
        """Enterprise strategy adds governance phase."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="enterprise",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )
        phases = {step["phase"] for step in steps}

        assert "Governance" in phases

    def test_default_strategy(self, executor, sample_context):
        """Default strategy generates basic workflow."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        assert len(steps) >= 5


class TestWorkflowDepth:
    """Tests for workflow depth levels."""

    def test_deep_depth_adds_security(self, executor, sample_context):
        """Deep depth adds security review step."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="deep",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        owners = {step["owner"] for step in steps}
        assert "security-engineer" in owners

    def test_deep_depth_adds_performance(self, executor, sample_context):
        """Deep depth adds performance validation step."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="deep",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        owners = {step["owner"] for step in steps}
        assert "performance-engineer" in owners

    def test_enterprise_depth_adds_security(self, executor, sample_context):
        """Enterprise depth adds security review step."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="enterprise",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        owners = {step["owner"] for step in steps}
        assert "security-engineer" in owners


class TestWorkflowFeatures:
    """Tests for workflow feature handling."""

    def test_single_feature(self, executor, sample_context):
        """Handles single feature."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["User Authentication"],
        )

        impl_steps = [s for s in steps if s["phase"] == "Implementation"]
        assert len(impl_steps) >= 1

    def test_multiple_features(self, executor, sample_context):
        """Handles multiple features."""
        features = ["User Auth", "Payment Processing", "Notifications"]
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=features,
        )

        impl_steps = [s for s in steps if s["phase"] == "Implementation"]
        assert len(impl_steps) >= 3


class TestWorkflowParallelization:
    """Tests for workflow parallelization."""

    def test_parallel_flag_disabled(self, executor, sample_context):
        """Parallel flag disabled removes parallel marking."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=False,
            sections=["Overview"],
            features=["Feature 1"],
        )

        for step in steps:
            assert step.get("parallel", False) is False


class TestWorkflowOwners:
    """Tests for workflow owner assignments."""

    def test_analysis_owner(self, executor, sample_context):
        """Analysis phase has requirements-analyst owner."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        analysis_steps = [s for s in steps if s["phase"] == "Analysis"]
        for step in analysis_steps:
            assert step["owner"] == "requirements-analyst"

    def test_architecture_owner(self, executor, sample_context):
        """Architecture phase has system-architect owner."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        arch_steps = [s for s in steps if s["phase"] == "Architecture"]
        for step in arch_steps:
            assert step["owner"] == "system-architect"

    def test_quality_owner(self, executor, sample_context):
        """Quality phase has quality-engineer owner for QA step."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        quality_steps = [s for s in steps if s["phase"] == "Quality"]
        owners = {s["owner"] for s in quality_steps}
        assert "quality-engineer" in owners

    def test_release_owner(self, executor, sample_context):
        """Release phase has devops-architect owner."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        release_steps = [s for s in steps if s["phase"] == "Release"]
        for step in release_steps:
            assert step["owner"] == "devops-architect"

    def test_planning_owner(self, executor, sample_context):
        """Planning phase has project-manager owner."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        planning_steps = [s for s in steps if s["phase"] == "Planning"]
        for step in planning_steps:
            assert step["owner"] == "project-manager"


class TestWorkflowStepIds:
    """Tests for workflow step ID generation."""

    def test_step_ids_formatted(self, executor, sample_context):
        """Step IDs follow expected format."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        for step in steps:
            step_id = step["id"]
            assert step_id.startswith("S")
            assert len(step_id) == 3

    def test_step_ids_sequential(self, executor, sample_context):
        """Step IDs are sequential."""
        steps = executor._generate_workflow_steps(
            sample_context,
            strategy="default",
            depth="standard",
            parallel=True,
            sections=["Overview"],
            features=["Feature 1"],
        )

        ids = [int(step["id"][1:]) for step in steps]
        expected = list(range(1, len(ids) + 1))
        assert ids == expected


class TestSelectFeatureOwner:
    """Tests for _select_feature_owner method."""

    def test_select_owner_returns_string(self, executor):
        """Select feature owner returns string."""
        owner = executor._select_feature_owner("User Authentication")

        assert isinstance(owner, str)
        assert len(owner) > 0

    def test_select_owner_empty_feature(self, executor):
        """Select owner handles empty feature."""
        owner = executor._select_feature_owner("")

        assert isinstance(owner, str)
