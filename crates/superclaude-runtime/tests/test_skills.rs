/*!
Integration tests for the skills persistence module
*/

use superclaude_runtime::skills::*;
use std::collections::HashMap;
use tempfile::TempDir;

#[test]
fn test_skill_store_save_and_get() {
    let temp_dir = TempDir::new().unwrap();
    let skills_dir = temp_dir.path().join("skills").join("learned");
    let feedback_dir = temp_dir.path().join("feedback");

    let mut store = SkillStore::new(Some(skills_dir), Some(feedback_dir)).unwrap();

    let skill = LearnedSkill {
        skill_id: "test-skill-001".to_string(),
        name: "Test Skill".to_string(),
        description: "A test skill".to_string(),
        triggers: vec!["test".to_string(), "unit".to_string()],
        domain: "testing".to_string(),
        source_session: "session-123".to_string(),
        source_repo: "/path/to/repo".to_string(),
        learned_at: "2025-01-01T00:00:00Z".to_string(),
        patterns: vec!["Use fixtures".to_string()],
        anti_patterns: vec!["Don't hardcode".to_string()],
        quality_score: 85.0,
        iteration_count: 3,
        provenance: HashMap::new(),
        applicability_conditions: vec!["Python projects".to_string()],
        promoted: false,
        promotion_reason: String::new(),
    };

    store.save_skill(&skill).unwrap();
    let retrieved = store.get_skill(&skill.skill_id).unwrap();

    assert!(retrieved.is_some());
    let retrieved = retrieved.unwrap();
    assert_eq!(retrieved.name, skill.name);
    assert_eq!(retrieved.quality_score, skill.quality_score);
}

#[test]
fn test_skill_search() {
    let temp_dir = TempDir::new().unwrap();
    let skills_dir = temp_dir.path().join("skills").join("learned");
    let feedback_dir = temp_dir.path().join("feedback");

    let mut store = SkillStore::new(Some(skills_dir), Some(feedback_dir)).unwrap();

    let skill = LearnedSkill {
        skill_id: "test-skill-002".to_string(),
        name: "Test Skill 2".to_string(),
        description: "Another test skill".to_string(),
        triggers: vec!["pytest".to_string(), "testing".to_string()],
        domain: "testing".to_string(),
        source_session: "session-456".to_string(),
        source_repo: "/path/to/repo".to_string(),
        learned_at: "2025-01-01T00:00:00Z".to_string(),
        patterns: vec!["Mock external calls".to_string()],
        anti_patterns: vec!["Don't test internals".to_string()],
        quality_score: 90.0,
        iteration_count: 5,
        provenance: HashMap::new(),
        applicability_conditions: vec!["Has test suite".to_string()],
        promoted: false,
        promotion_reason: String::new(),
    };

    store.save_skill(&skill).unwrap();
    let results = store.search_skills("pytest", None, 50.0, false).unwrap();

    assert_eq!(results.len(), 1);
    assert_eq!(results[0].skill_id, skill.skill_id);
}

#[test]
fn test_feedback_storage() {
    let temp_dir = TempDir::new().unwrap();
    let skills_dir = temp_dir.path().join("skills").join("learned");
    let feedback_dir = temp_dir.path().join("feedback");

    let store = SkillStore::new(Some(skills_dir), Some(feedback_dir)).unwrap();

    let feedback = IterationFeedback {
        session_id: "test-session".to_string(),
        iteration: 1,
        quality_before: 50.0,
        quality_after: 75.0,
        improvements_applied: vec!["Added tests".to_string()],
        improvements_needed: vec!["Add docs".to_string()],
        changed_files: vec!["test.py".to_string()],
        test_results: HashMap::new(),
        duration_seconds: 30.0,
        success: true,
        termination_reason: "complete".to_string(),
        timestamp: chrono::Utc::now(),
    };

    store.save_feedback(&feedback).unwrap();
    let retrieved = store.get_session_feedback("test-session").unwrap();

    assert_eq!(retrieved.len(), 1);
    assert_eq!(retrieved[0].iteration, 1);
    assert_eq!(retrieved[0].quality_after, 75.0);
}

#[test]
fn test_skill_application_tracking() {
    let temp_dir = TempDir::new().unwrap();
    let skills_dir = temp_dir.path().join("skills").join("learned");
    let feedback_dir = temp_dir.path().join("feedback");

    let store = SkillStore::new(Some(skills_dir), Some(feedback_dir)).unwrap();

    store.record_skill_application(
        "skill-123",
        "session-1",
        Some(true),
        Some(10.0),
        "Very helpful",
    ).unwrap();

    store.record_skill_application(
        "skill-123",
        "session-2",
        Some(true),
        Some(5.0),
        "Somewhat helpful",
    ).unwrap();

    store.record_skill_application(
        "skill-123",
        "session-3",
        Some(false),
        Some(-2.0),
        "Not helpful",
    ).unwrap();

    let effectiveness = store.get_skill_effectiveness("skill-123").unwrap();

    assert_eq!(effectiveness.applications, 3);
    assert_eq!(effectiveness.helpful_count, 2);
    assert_eq!(effectiveness.unhelpful_count, 1);
    assert!((effectiveness.success_rate - 0.666).abs() < 0.01);
}

#[test]
fn test_skill_to_md() {
    let skill = LearnedSkill {
        skill_id: "md-test".to_string(),
        name: "Markdown Test".to_string(),
        description: "Test skill for markdown generation".to_string(),
        triggers: vec!["test".to_string()],
        domain: "testing".to_string(),
        source_session: "session-abc".to_string(),
        source_repo: "/repo".to_string(),
        learned_at: "2025-01-01T00:00:00Z".to_string(),
        patterns: vec!["Pattern 1".to_string()],
        anti_patterns: vec!["Anti-pattern 1".to_string()],
        quality_score: 85.0,
        iteration_count: 3,
        provenance: HashMap::new(),
        applicability_conditions: vec!["Condition 1".to_string()],
        promoted: false,
        promotion_reason: String::new(),
    };

    let md = skill.to_skill_md();

    assert!(md.contains("---"));
    assert!(md.contains("name: Markdown Test"));
    assert!(md.contains("Pattern 1"));
    assert!(md.contains("Anti-pattern 1"));
}

#[test]
fn test_skill_extractor() {
    let temp_dir = TempDir::new().unwrap();
    let skills_dir = temp_dir.path().join("skills").join("learned");
    let feedback_dir = temp_dir.path().join("feedback");

    let store = SkillStore::new(Some(skills_dir), Some(feedback_dir)).unwrap();
    let extractor = SkillExtractor::new(&store);

    // Create feedback for a successful session
    let feedback1 = IterationFeedback {
        session_id: "extract-session".to_string(),
        iteration: 1,
        quality_before: 50.0,
        quality_after: 70.0,
        improvements_applied: vec!["Added type hints".to_string()],
        improvements_needed: vec![],
        changed_files: vec!["main.py".to_string()],
        test_results: HashMap::new(),
        duration_seconds: 30.0,
        success: true,
        termination_reason: String::new(),
        timestamp: chrono::Utc::now(),
    };

    let feedback2 = IterationFeedback {
        session_id: "extract-session".to_string(),
        iteration: 2,
        quality_before: 70.0,
        quality_after: 85.0,
        improvements_applied: vec!["Added tests".to_string()],
        improvements_needed: vec![],
        changed_files: vec!["test_main.py".to_string()],
        test_results: HashMap::new(),
        duration_seconds: 20.0,
        success: true,
        termination_reason: "complete".to_string(),
        timestamp: chrono::Utc::now(),
    };

    store.save_feedback(&feedback1).unwrap();
    store.save_feedback(&feedback2).unwrap();

    let skill = extractor.extract_from_session("extract-session", "/repo", "backend").unwrap();

    assert!(skill.is_some());
    let skill = skill.unwrap();
    assert_eq!(skill.domain, "backend");
    assert!(skill.quality_score >= 70.0);
    assert_eq!(skill.iteration_count, 2);
}

#[test]
fn test_skill_retriever() {
    let temp_dir = TempDir::new().unwrap();
    let skills_dir = temp_dir.path().join("skills").join("learned");
    let feedback_dir = temp_dir.path().join("feedback");

    let mut store = SkillStore::new(Some(skills_dir), Some(feedback_dir)).unwrap();

    let skill = LearnedSkill {
        skill_id: "retrieve-test".to_string(),
        name: "Retrieval Test".to_string(),
        description: "Test skill for retrieval".to_string(),
        triggers: vec!["authentication".to_string(), "login".to_string()],
        domain: "backend".to_string(),
        source_session: "session-xyz".to_string(),
        source_repo: "/repo".to_string(),
        learned_at: "2025-01-01T00:00:00Z".to_string(),
        patterns: vec!["Use JWT".to_string()],
        anti_patterns: vec!["Don't hardcode keys".to_string()],
        quality_score: 88.0,
        iteration_count: 4,
        provenance: HashMap::new(),
        applicability_conditions: vec!["Backend API".to_string()],
        promoted: false,
        promotion_reason: String::new(),
    };

    store.save_skill(&skill).unwrap();

    let mut retriever = SkillRetriever::new(&mut store);
    let results = retriever.retrieve(
        "implement authentication and login",
        None,
        Some("backend"),
        3,
        false,
    ).unwrap();

    assert!(!results.is_empty());
    assert_eq!(results[0].0.skill_id, skill.skill_id);
}

#[test]
fn test_promotion_gate() {
    let temp_dir = TempDir::new().unwrap();
    let skills_dir = temp_dir.path().join("skills").join("learned");
    let feedback_dir = temp_dir.path().join("feedback");

    let store = SkillStore::new(Some(skills_dir.clone()), Some(feedback_dir)).unwrap();

    let mut skill = LearnedSkill {
        skill_id: "promo-test".to_string(),
        name: "Promotion Test".to_string(),
        description: "Test skill for promotion".to_string(),
        triggers: vec!["test".to_string()],
        domain: "testing".to_string(),
        source_session: "session-promo".to_string(),
        source_repo: "/repo".to_string(),
        learned_at: "2025-01-01T00:00:00Z".to_string(),
        patterns: vec!["Pattern 1".to_string()],
        anti_patterns: vec!["Anti 1".to_string()],
        quality_score: 90.0,
        iteration_count: 5,
        provenance: HashMap::new(),
        applicability_conditions: vec!["Condition 1".to_string()],
        promoted: false,
        promotion_reason: String::new(),
    };

    // Add applications to meet threshold
    for i in 0..3 {
        store.record_skill_application(
            &skill.skill_id,
            &format!("session-{}", i),
            Some(true),
            Some(5.0),
            "Helpful",
        ).unwrap();
    }

    let gate = PromotionGate::new(&store, Some(skills_dir));
    let (can_promote, _reason) = gate.evaluate(&skill).unwrap();

    assert!(can_promote);

    let path = gate.promote(&mut skill, Some("Test promotion")).unwrap();
    assert!(path.is_some());
    assert!(skill.promoted);
}
