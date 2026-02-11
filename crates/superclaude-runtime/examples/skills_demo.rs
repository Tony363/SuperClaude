//! Standalone demo of the skills persistence module

use tempfile::TempDir;

// Include the skills module directly
// This is just for demonstration; in real usage import from the lib
include!("../src/skills.rs");

fn main() -> anyhow::Result<()> {
    println!("Skills Persistence Module Demo\n");

    // Create temporary directories for testing
    let temp_dir = TempDir::new()?;
    let skills_dir = temp_dir.path().join("skills").join("learned");
    let feedback_dir = temp_dir.path().join("feedback");

    // Create a skill store
    let mut store = SkillStore::new(Some(skills_dir), Some(feedback_dir))?;
    println!("✓ Created SkillStore");

    // Create a sample skill
    let skill = LearnedSkill {
        skill_id: "demo-skill-001".to_string(),
        name: "Demo Skill".to_string(),
        description: "A demonstration skill".to_string(),
        triggers: vec!["demo".to_string(), "test".to_string()],
        domain: "testing".to_string(),
        source_session: "demo-session-123".to_string(),
        source_repo: "/path/to/repo".to_string(),
        learned_at: chrono::Utc::now().to_rfc3339(),
        patterns: vec![
            "Use clear naming conventions".to_string(),
            "Write comprehensive tests".to_string(),
        ],
        anti_patterns: vec!["Don't skip error handling".to_string()],
        quality_score: 87.5,
        iteration_count: 3,
        provenance: HashMap::new(),
        applicability_conditions: vec!["Rust projects".to_string()],
        promoted: false,
        promotion_reason: String::new(),
    };

    // Save the skill
    store.save_skill(&skill)?;
    println!("✓ Saved skill: {}", skill.name);

    // Retrieve the skill
    let retrieved = store.get_skill(&skill.skill_id)?;
    if let Some(retrieved) = retrieved {
        println!("✓ Retrieved skill: {} (quality: {:.1})", retrieved.name, retrieved.quality_score);
    }

    // Create and save feedback
    let feedback = IterationFeedback {
        session_id: "demo-session-123".to_string(),
        iteration: 1,
        quality_before: 50.0,
        quality_after: 75.0,
        improvements_applied: vec!["Added documentation".to_string()],
        improvements_needed: vec!["Add integration tests".to_string()],
        changed_files: vec!["src/main.rs".to_string()],
        test_results: HashMap::new(),
        duration_seconds: 45.0,
        success: true,
        termination_reason: "quality_threshold_met".to_string(),
        timestamp: chrono::Utc::now(),
    };

    store.save_feedback(&feedback)?;
    println!("✓ Saved feedback for iteration {}", feedback.iteration);

    // Search for skills
    let results = store.search_skills("demo", None, 50.0, false)?;
    println!("✓ Found {} skills matching 'demo'", results.len());

    // Record skill application
    store.record_skill_application(
        &skill.skill_id,
        "test-session-1",
        Some(true),
        Some(10.0),
        "Very helpful skill",
    )?;
    println!("✓ Recorded skill application");

    // Get effectiveness
    let effectiveness = store.get_skill_effectiveness(&skill.skill_id)?;
    println!("✓ Skill effectiveness:");
    println!("  - Applications: {}", effectiveness.applications);
    println!("  - Success rate: {:.1}%", effectiveness.success_rate * 100.0);

    // Generate SKILL.md
    let md = skill.to_skill_md();
    println!("\n✓ Generated SKILL.md (first 200 chars):");
    println!("{}", &md[..200.min(md.len())]);

    println!("\n✅ All operations successful!");

    Ok(())
}
