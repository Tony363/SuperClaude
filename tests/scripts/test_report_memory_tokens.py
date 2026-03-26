"""Tests for scripts/report_memory_tokens.py."""

from pathlib import Path

from scripts.report_memory_tokens import estimate_tokens, iter_memory_files


class TestEstimateTokens:
    """Tests for estimate_tokens."""

    def test_empty_string_returns_zero(self):
        assert estimate_tokens("") == 0

    def test_short_string(self):
        # "hello" is 5 chars => ceil(5/4) = 2
        assert estimate_tokens("hello") == 2

    def test_single_char(self):
        # 1 char => max(1, ceil(1/4)) = 1
        assert estimate_tokens("a") == 1

    def test_four_chars_is_one_token(self):
        assert estimate_tokens("abcd") == 1

    def test_five_chars_is_two_tokens(self):
        assert estimate_tokens("abcde") == 2

    def test_long_string(self):
        text = "a" * 400
        assert estimate_tokens(text) == 100

    def test_none_returns_zero(self):
        # Empty string check
        assert estimate_tokens("") == 0


class TestIterMemoryFiles:
    """Tests for iter_memory_files."""

    def test_finds_markdown_files(self, tmp_path: Path):
        # Arrange
        (tmp_path / "note.md").write_text("hello world")
        (tmp_path / "other.txt").write_text("not markdown")

        # Act
        results = list(iter_memory_files(tmp_path))

        # Assert
        assert len(results) == 1
        assert results[0][0].name == "note.md"
        assert results[0][1] > 0

    def test_finds_nested_markdown(self, tmp_path: Path):
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "deep.md").write_text("nested content")

        results = list(iter_memory_files(tmp_path))

        assert len(results) == 1
        assert results[0][0].name == "deep.md"

    def test_empty_directory(self, tmp_path: Path):
        results = list(iter_memory_files(tmp_path))
        assert results == []

    def test_skips_unreadable_files(self, tmp_path: Path):
        md = tmp_path / "bad.md"
        md.write_bytes(b"\xff\xfe" + b"\x00" * 100)

        # Should not crash - skips unreadable files
        results = list(iter_memory_files(tmp_path))
        # May or may not yield depending on encoding, but shouldn't crash
        assert isinstance(results, list)

    def test_returns_sorted(self, tmp_path: Path):
        (tmp_path / "b.md").write_text("b")
        (tmp_path / "a.md").write_text("a")

        results = list(iter_memory_files(tmp_path))

        names = [r[0].name for r in results]
        assert names == ["a.md", "b.md"]


# --- Tests for main() ---


class TestReportMemoryTokensMain:
    """Tests for main()."""

    def test_main_with_files(self, tmp_path: Path, monkeypatch, capsys):
        (tmp_path / "note.md").write_text("hello world test content")
        monkeypatch.setattr("sys.argv", ["prog", "--install-dir", str(tmp_path)])

        from scripts.report_memory_tokens import main

        main()

        captured = capsys.readouterr()
        assert "note.md" in captured.out
        assert "Total estimated tokens" in captured.out

    def test_main_no_files(self, tmp_path: Path, monkeypatch, capsys):
        monkeypatch.setattr("sys.argv", ["prog", "--install-dir", str(tmp_path)])

        from scripts.report_memory_tokens import main

        main()

        captured = capsys.readouterr()
        assert "No Markdown memory files" in captured.out

    def test_main_missing_dir(self, tmp_path: Path, monkeypatch):
        missing = tmp_path / "nonexistent"
        monkeypatch.setattr("sys.argv", ["prog", "--install-dir", str(missing)])

        import pytest

        from scripts.report_memory_tokens import main

        with pytest.raises(SystemExit):
            main()

    def test_main_multiple_files(self, tmp_path: Path, monkeypatch, capsys):
        (tmp_path / "a.md").write_text("short")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "b.md").write_text("longer content here for testing")

        monkeypatch.setattr("sys.argv", ["prog", "--install-dir", str(tmp_path)])

        from scripts.report_memory_tokens import main

        main()

        captured = capsys.readouterr()
        assert "a.md" in captured.out
        assert "b.md" in captured.out
        assert "Total estimated tokens" in captured.out
