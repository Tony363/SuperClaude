from SuperClaude.Agents import usage_tracker


def test_usage_tracker_records_and_reports(tmp_path, monkeypatch):
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(tmp_path))
    usage_tracker.reset_usage_stats(for_tests=True)

    usage_tracker.record_load("demo-agent", source="extended")
    usage_tracker.record_execution("demo-agent")

    snapshot = usage_tracker.get_usage_snapshot()
    assert snapshot["demo-agent"]["loaded"] == 1
    assert snapshot["demo-agent"]["executed"] == 1
    assert snapshot["demo-agent"]["source"] == "extended"

    registry_summary = {
        "demo-agent": {"source": "extended"},
        "other-agent": {"source": "core"},
    }
    buckets = usage_tracker.classify_agents(registry_summary)
    assert "demo-agent" in buckets["active"]
    assert "other-agent" in buckets["planned"]

    report_path = usage_tracker.write_markdown_report(registry_summary)
    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "demo-agent" in content
    assert "other-agent" in content

    # Clean up the generated files for isolation
    usage_tracker.reset_usage_stats(for_tests=True)
    if report_path.exists():
        report_path.unlink()


def test_usage_tracker_handles_missing_metrics_dir(tmp_path, monkeypatch):
    missing_root = tmp_path / "missing"
    monkeypatch.setenv("SUPERCLAUDE_METRICS_DIR", str(missing_root))
    usage_tracker.reset_usage_stats(for_tests=True)

    registry_summary = {"agent": {"source": "core"}}
    report_path = usage_tracker.write_markdown_report(registry_summary)

    assert report_path.exists()
    content = report_path.read_text(encoding="utf-8")
    assert "agent" in content
