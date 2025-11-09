import os
import tempfile
import unittest
from pathlib import Path

from SuperClaude.Core.unified_store import UnifiedStore
from SuperClaude.WorktreeManager.state import WorktreeStateManager


class TestWorktreeStateManager(unittest.TestCase):
    def setUp(self) -> None:
        self.repo_dir = tempfile.TemporaryDirectory()
        self.db_file = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        self.db_file.close()
        self.store = UnifiedStore(self.db_file.name)
        self.manager = WorktreeStateManager(
            repo_path=self.repo_dir.name,
            store=self.store,
        )

    def tearDown(self) -> None:
        self.manager.cleanup()
        self.repo_dir.cleanup()
        if os.path.exists(self.db_file.name):
            os.remove(self.db_file.name)

    def test_update_and_load_state(self):
        state = self.manager.update_state(
            "wt-demo",
            task_id="demo",
            branch="feature/demo",
            status="active",
        )
        self.assertEqual(state.task_id, "demo")

        # Simulate new process loading from disk + store
        reloaded_store = UnifiedStore(self.db_file.name)
        reloaded_manager = WorktreeStateManager(
            repo_path=self.repo_dir.name,
            store=reloaded_store,
        )
        try:
            loaded = reloaded_manager.get_state("wt-demo")
            self.assertIsNotNone(loaded)
            self.assertEqual(loaded.branch, "feature/demo")
        finally:
            reloaded_manager.cleanup()

    def test_remove_state_cleans_store(self):
        self.manager.update_state("wt-demo", task_id="demo")
        self.assertIn("worktree_wt-demo", self.store.list_memories(prefix="worktree_"))

        self.manager.remove_state("wt-demo")
        self.assertNotIn("worktree_wt-demo", self.store.list_memories(prefix="worktree_"))

    def test_duplicate_updates_overwrite_previous_state(self):
        self.manager.update_state("wt-demo", task_id="demo", status="active")
        self.manager.update_state("wt-demo", task_id="demo", status="complete")

        loaded = self.manager.get_state("wt-demo")
        self.assertEqual(loaded.status, "complete")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
