#!/usr/bin/env python3
"""
Skill Learning CLI for SuperClaude.

Provides commands for managing learned skills:
- list: Show learned skills and their status
- promote: Promote a skill to permanent status
- stats: Show learning statistics
- retrieve: Find relevant skills for a task
- export: Export skills to SKILL.md files

Usage:
    python skill_learn.py '{"command": "list"}'
    python skill_learn.py '{"command": "promote", "skill_id": "learned-abc123"}'
    python skill_learn.py '{"command": "stats"}'
    python skill_learn.py '{"command": "retrieve", "task": "implement auth", "domain": "backend"}'
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path
from typing import Any

# Load skill_persistence directly to avoid core/__init__.py import issues
SUPERCLAUD_ROOT = Path(__file__).parent.parent.parent.parent.parent
SKILL_PERSISTENCE_PATH = SUPERCLAUD_ROOT / "core" / "skill_persistence.py"

spec = importlib.util.spec_from_file_location("skill_persistence", SKILL_PERSISTENCE_PATH)
sp = importlib.util.module_from_spec(spec)
sys.modules["skill_persistence"] = sp
spec.loader.exec_module(sp)

LearnedSkill = sp.LearnedSkill
PromotionGate = sp.PromotionGate
SkillExtractor = sp.SkillExtractor
SkillRetriever = sp.SkillRetriever
SkillStore = sp.SkillStore


def handle_list(args: dict[str, Any]) -> dict[str, Any]:
    """List learned skills with optional filters."""
    store = SkillStore()

    domain = args.get("domain")
    promoted_only = args.get("promoted_only", False)
    min_quality = args.get("min_quality", 0.0)

    conn = store._get_connection()

    sql = "SELECT * FROM learned_skills WHERE quality_score >= ?"
    params: list[Any] = [min_quality]

    if domain:
        sql += " AND domain = ?"
        params.append(domain)

    if promoted_only:
        sql += " AND promoted = 1"

    sql += " ORDER BY quality_score DESC, learned_at DESC"

    rows = conn.execute(sql, params).fetchall()

    skills = []
    for row in rows:
        skill = store._row_to_skill(row)
        skills.append({
            "skill_id": skill.skill_id,
            "name": skill.name,
            "domain": skill.domain,
            "quality_score": skill.quality_score,
            "promoted": skill.promoted,
            "patterns_count": len(skill.patterns),
            "learned_at": skill.learned_at,
            "source_session": skill.source_session[:8] if skill.source_session else "",
        })

    return {
        "success": True,
        "count": len(skills),
        "skills": skills,
    }


def handle_promote(args: dict[str, Any]) -> dict[str, Any]:
    """Promote a skill to permanent status."""
    skill_id = args.get("skill_id")
    reason = args.get("reason", "Manual promotion")

    if not skill_id:
        return {"success": False, "error": "skill_id is required"}

    store = SkillStore()
    gate = PromotionGate(store)

    skill = store.get_skill(skill_id)
    if skill is None:
        return {"success": False, "error": f"Skill not found: {skill_id}"}

    # Check if already promoted
    if skill.promoted:
        return {"success": False, "error": "Skill already promoted"}

    # Evaluate
    can_promote, eval_reason = gate.evaluate(skill)
    if not can_promote:
        return {
            "success": False,
            "error": f"Skill does not meet promotion criteria: {eval_reason}",
            "skill_id": skill_id,
            "quality_score": skill.quality_score,
        }

    # Promote
    path = gate.promote(skill, reason)
    if path is None:
        return {"success": False, "error": "Promotion failed"}

    return {
        "success": True,
        "skill_id": skill_id,
        "name": skill.name,
        "promoted_to": str(path),
        "reason": reason,
    }


def handle_stats(args: dict[str, Any]) -> dict[str, Any]:
    """Get learning statistics."""
    store = SkillStore()
    conn = store._get_connection()

    # Skill counts
    skill_stats = conn.execute("""
        SELECT
            COUNT(*) as total,
            SUM(CASE WHEN promoted = 1 THEN 1 ELSE 0 END) as promoted,
            AVG(quality_score) as avg_quality,
            MAX(quality_score) as max_quality,
            MIN(quality_score) as min_quality
        FROM learned_skills
    """).fetchone()

    # Domain breakdown
    domain_stats = conn.execute("""
        SELECT domain, COUNT(*) as count, AVG(quality_score) as avg_quality
        FROM learned_skills
        GROUP BY domain
        ORDER BY count DESC
    """).fetchall()

    # Feedback stats
    feedback_stats = conn.execute("""
        SELECT
            COUNT(*) as total_feedback,
            COUNT(DISTINCT session_id) as sessions,
            AVG(quality_after - quality_before) as avg_improvement
        FROM iteration_feedback
    """).fetchone()

    # Application stats
    app_stats = conn.execute("""
        SELECT
            COUNT(*) as total_applications,
            SUM(CASE WHEN was_helpful = 1 THEN 1 ELSE 0 END) as helpful,
            SUM(CASE WHEN was_helpful = 0 THEN 1 ELSE 0 END) as unhelpful,
            AVG(quality_impact) as avg_impact
        FROM skill_applications
    """).fetchone()

    # Recent learning activity
    recent = conn.execute("""
        SELECT skill_id, name, quality_score, learned_at
        FROM learned_skills
        ORDER BY learned_at DESC
        LIMIT 5
    """).fetchall()

    return {
        "success": True,
        "skills": {
            "total": skill_stats["total"] or 0,
            "promoted": skill_stats["promoted"] or 0,
            "pending": (skill_stats["total"] or 0) - (skill_stats["promoted"] or 0),
            "avg_quality": round(skill_stats["avg_quality"] or 0, 1),
            "max_quality": round(skill_stats["max_quality"] or 0, 1),
            "min_quality": round(skill_stats["min_quality"] or 0, 1),
        },
        "domains": [
            {
                "domain": row["domain"] or "general",
                "count": row["count"],
                "avg_quality": round(row["avg_quality"] or 0, 1),
            }
            for row in domain_stats
        ],
        "feedback": {
            "total_records": feedback_stats["total_feedback"] or 0,
            "sessions": feedback_stats["sessions"] or 0,
            "avg_improvement": round(feedback_stats["avg_improvement"] or 0, 2),
        },
        "applications": {
            "total": app_stats["total_applications"] or 0,
            "helpful": app_stats["helpful"] or 0,
            "unhelpful": app_stats["unhelpful"] or 0,
            "success_rate": round(
                (app_stats["helpful"] or 0) / app_stats["total_applications"]
                if app_stats["total_applications"] else 0,
                2
            ),
            "avg_quality_impact": round(app_stats["avg_impact"] or 0, 2),
        },
        "recent_skills": [
            {
                "skill_id": row["skill_id"],
                "name": row["name"],
                "quality": row["quality_score"],
                "learned_at": row["learned_at"],
            }
            for row in recent
        ],
    }


def handle_retrieve(args: dict[str, Any]) -> dict[str, Any]:
    """Retrieve relevant skills for a task."""
    task = args.get("task", "")
    domain = args.get("domain")
    files = args.get("files", [])
    max_skills = args.get("max_skills", 5)
    promoted_only = args.get("promoted_only", False)

    if not task:
        return {"success": False, "error": "task is required"}

    store = SkillStore()
    retriever = SkillRetriever(store)

    results = retriever.retrieve(
        task_description=task,
        file_paths=files,
        domain=domain,
        max_skills=max_skills,
        promoted_only=promoted_only,
    )

    skills = []
    for skill, score in results:
        skills.append({
            "skill_id": skill.skill_id,
            "name": skill.name,
            "relevance": round(score, 2),
            "quality_score": skill.quality_score,
            "domain": skill.domain,
            "promoted": skill.promoted,
            "patterns": skill.patterns[:3],
            "anti_patterns": skill.anti_patterns[:2],
            "conditions": skill.applicability_conditions,
        })

    return {
        "success": True,
        "task": task,
        "domain": domain,
        "found": len(skills),
        "skills": skills,
    }


def handle_export(args: dict[str, Any]) -> dict[str, Any]:
    """Export a skill to SKILL.md format."""
    skill_id = args.get("skill_id")
    output_dir = args.get("output_dir")

    if not skill_id:
        return {"success": False, "error": "skill_id is required"}

    store = SkillStore()
    skill = store.get_skill(skill_id)

    if skill is None:
        return {"success": False, "error": f"Skill not found: {skill_id}"}

    skill_md = skill.to_skill_md()

    if output_dir:
        # Use skill_id for directory name to prevent path traversal
        output_path = Path(output_dir) / skill.skill_id / "SKILL.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(skill_md)

        return {
            "success": True,
            "skill_id": skill_id,
            "exported_to": str(output_path),
        }

    return {
        "success": True,
        "skill_id": skill_id,
        "skill_md": skill_md,
    }


def handle_pending(args: dict[str, Any]) -> dict[str, Any]:
    """List skills pending promotion."""
    store = SkillStore()
    gate = PromotionGate(store)
    pending = gate.list_pending()

    skills = []
    for skill in pending:
        can_promote, reason = gate.evaluate(skill)
        effectiveness = store.get_skill_effectiveness(skill.skill_id)

        skills.append({
            "skill_id": skill.skill_id,
            "name": skill.name,
            "quality_score": skill.quality_score,
            "domain": skill.domain,
            "can_promote": can_promote,
            "reason": reason,
            "applications": effectiveness["applications"],
            "success_rate": round(effectiveness["success_rate"], 2),
            "learned_at": skill.learned_at,
        })

    return {
        "success": True,
        "count": len(skills),
        "skills": skills,
    }


def handle_delete(args: dict[str, Any]) -> dict[str, Any]:
    """Delete a learned skill."""
    skill_id = args.get("skill_id")

    if not skill_id:
        return {"success": False, "error": "skill_id is required"}

    store = SkillStore()
    conn = store._get_connection()

    # Check if exists
    skill = store.get_skill(skill_id)
    if skill is None:
        return {"success": False, "error": f"Skill not found: {skill_id}"}

    # Delete from database
    try:
        conn.execute("DELETE FROM learned_skills WHERE skill_id = ?", (skill_id,))
        conn.execute("DELETE FROM skill_applications WHERE skill_id = ?", (skill_id,))
        conn.commit()
    except Exception as e:
        return {"success": False, "error": f"Database error: {e}"}

    # Remove files if promoted (use skill_id for directory name, not skill.name)
    if skill.promoted:
        # Use skill_id for directory name to match PromotionGate.promote()
        skill_dir = Path.home() / ".claude" / "skills" / "learned" / skill.skill_id
        if skill_dir.exists():
            import shutil
            shutil.rmtree(skill_dir)

    return {
        "success": True,
        "skill_id": skill_id,
        "name": skill.name,
        "deleted": True,
    }


HANDLERS = {
    "list": handle_list,
    "promote": handle_promote,
    "stats": handle_stats,
    "retrieve": handle_retrieve,
    "export": handle_export,
    "pending": handle_pending,
    "delete": handle_delete,
}


def main():
    """Main entry point."""
    if len(sys.argv) < 2:
        print(json.dumps({
            "success": False,
            "error": "Usage: skill_learn.py '{\"command\": \"...\", ...}'",
            "available_commands": list(HANDLERS.keys()),
        }))
        sys.exit(1)

    try:
        args = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({
            "success": False,
            "error": f"Invalid JSON: {e}",
        }))
        sys.exit(1)

    command = args.get("command")
    if not command:
        print(json.dumps({
            "success": False,
            "error": "Missing 'command' field",
            "available_commands": list(HANDLERS.keys()),
        }))
        sys.exit(1)

    handler = HANDLERS.get(command)
    if not handler:
        print(json.dumps({
            "success": False,
            "error": f"Unknown command: {command}",
            "available_commands": list(HANDLERS.keys()),
        }))
        sys.exit(1)

    try:
        result = handler(args)
        print(json.dumps(result, indent=2))
    except Exception as e:
        print(json.dumps({
            "success": False,
            "error": str(e),
            "command": command,
        }))
        sys.exit(1)


if __name__ == "__main__":
    main()
