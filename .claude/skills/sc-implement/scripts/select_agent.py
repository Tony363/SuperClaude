#!/usr/bin/env python3
"""
Agent Selection Script for SuperClaude Skills.

Deterministic agent selection based on weighted scoring algorithm.
Ported from SuperClaude/Agents/extended_loader.py

Usage:
    python select_agent.py '{"task": "build react component", "files": ["*.tsx"]}'

Input (JSON):
    {
        "task": "task description",
        "files": ["file1.py", "file2.tsx"],
        "languages": ["python", "typescript"],
        "domains": ["frontend", "api"],
        "keywords": ["react", "component"],
        "imports": ["react", "express"]
    }

Output (JSON):
    {
        "selected_agent": "frontend-architect",
        "confidence": "high",
        "score": 0.75,
        "breakdown": {...},
        "matched_criteria": [...],
        "alternatives": [...]
    }
"""

import fnmatch
import json
import sys
from dataclasses import asdict, dataclass
from typing import Any


@dataclass
class AgentMetadata:
    """Agent metadata from SKILL.md or agent registry."""

    id: str
    name: str
    priority: int = 2
    domains: list[str] = None
    languages: list[str] = None
    keywords: list[str] = None
    file_patterns: list[str] = None
    imports: list[str] = None

    def __post_init__(self):
        self.domains = self.domains or []
        self.languages = self.languages or []
        self.keywords = self.keywords or []
        self.file_patterns = self.file_patterns or []
        self.imports = self.imports or []


@dataclass
class MatchScore:
    """Match score with detailed breakdown."""

    agent_id: str
    total_score: float
    breakdown: dict[str, float]
    matched_criteria: list[str]
    confidence: str


# Built-in agent definitions (subset - expand as needed)
AGENTS = [
    AgentMetadata(
        id="frontend-architect",
        name="Frontend Architect",
        priority=1,
        domains=["frontend", "ui", "ux", "web"],
        languages=["javascript", "typescript", "css", "html"],
        keywords=[
            "react",
            "vue",
            "angular",
            "component",
            "ui",
            "frontend",
            "css",
            "tailwind",
            "styled",
        ],
        file_patterns=["*.tsx", "*.jsx", "*.vue", "*.svelte", "*.css", "*.scss"],
        imports=["react", "vue", "@angular", "svelte", "styled-components"],
    ),
    AgentMetadata(
        id="backend-architect",
        name="Backend Architect",
        priority=1,
        domains=["backend", "api", "database", "server"],
        languages=["python", "javascript", "typescript", "go", "rust", "java"],
        keywords=[
            "api",
            "endpoint",
            "database",
            "server",
            "rest",
            "graphql",
            "microservice",
        ],
        file_patterns=["*.py", "*.go", "*.rs", "*.java", "routes/*", "api/*"],
        imports=["express", "fastapi", "django", "flask", "gin", "actix"],
    ),
    AgentMetadata(
        id="system-architect",
        name="System Architect",
        priority=1,
        domains=["architecture", "system", "infrastructure", "design"],
        languages=["any"],
        keywords=[
            "architecture",
            "system",
            "design",
            "scalability",
            "distributed",
            "microservice",
        ],
        file_patterns=["*.md", "docs/*", "architecture/*"],
        imports=[],
    ),
    AgentMetadata(
        id="security-engineer",
        name="Security Engineer",
        priority=1,
        domains=["security", "auth", "encryption", "compliance"],
        languages=["any"],
        keywords=[
            "security",
            "auth",
            "authentication",
            "authorization",
            "encryption",
            "vulnerability",
            "owasp",
        ],
        file_patterns=["*auth*", "*security*", "*crypto*"],
        imports=["bcrypt", "jwt", "oauth", "passport", "cryptography"],
    ),
    AgentMetadata(
        id="devops-architect",
        name="DevOps Architect",
        priority=1,
        domains=["devops", "ci", "cd", "deployment", "infrastructure"],
        languages=["yaml", "bash", "python"],
        keywords=[
            "docker",
            "kubernetes",
            "ci",
            "cd",
            "pipeline",
            "deployment",
            "terraform",
            "aws",
            "gcp",
        ],
        file_patterns=["Dockerfile", "*.yml", "*.yaml", ".github/*", "terraform/*"],
        imports=["boto3", "google-cloud", "azure"],
    ),
    AgentMetadata(
        id="python-expert",
        name="Python Expert",
        priority=2,
        domains=["python", "scripting", "automation"],
        languages=["python"],
        keywords=["python", "django", "flask", "fastapi", "pytest", "pandas", "numpy"],
        file_patterns=["*.py", "pyproject.toml", "setup.py", "requirements.txt"],
        imports=["django", "flask", "fastapi", "pandas", "numpy", "pytest"],
    ),
    AgentMetadata(
        id="quality-engineer",
        name="Quality Engineer",
        priority=2,
        domains=["testing", "qa", "quality", "automation"],
        languages=["any"],
        keywords=[
            "test",
            "testing",
            "qa",
            "quality",
            "coverage",
            "e2e",
            "unit",
            "integration",
        ],
        file_patterns=["*test*", "*spec*", "*.test.*", "*.spec.*"],
        imports=["pytest", "jest", "mocha", "cypress", "playwright"],
    ),
    AgentMetadata(
        id="general-purpose",
        name="General Purpose",
        priority=3,
        domains=["general"],
        languages=["any"],
        keywords=[],
        file_patterns=[],
        imports=[],
    ),
]


def calculate_match_score(context: dict[str, Any], metadata: AgentMetadata) -> MatchScore:
    """
    Calculate detailed match score for an agent.

    Scoring components:
    - Keywords: 30% weight
    - Domains: 25% weight
    - Languages: 20% weight
    - File patterns: 15% weight
    - Import patterns: 10% weight
    - Priority bonus: Up to 10% bonus
    """
    score = 0.0
    breakdown = {}
    matched_criteria = []

    # Extract context data
    task_text = context.get("task", "").lower()
    files = [f.lower() for f in context.get("files", [])]
    languages = [lang.lower() for lang in context.get("languages", [])]
    domains = [d.lower() for d in context.get("domains", [])]
    keywords = [k.lower() for k in context.get("keywords", [])]
    imports = [i.lower() for i in context.get("imports", [])]

    # 1. Keyword matching (30% weight)
    keyword_score = 0.0
    if metadata.keywords:
        matched_keywords = []
        for keyword in metadata.keywords:
            keyword_lower = keyword.lower()
            if keyword_lower in task_text:
                keyword_score += 1.0
                matched_keywords.append(keyword)
            elif keyword_lower in keywords:
                keyword_score += 0.8
                matched_keywords.append(keyword)
            elif any(kw in keyword_lower or keyword_lower in kw for kw in keywords):
                keyword_score += 0.3

        keyword_score = min(keyword_score / len(metadata.keywords), 1.0)
        if matched_keywords:
            matched_criteria.append(f"keywords: {', '.join(matched_keywords[:3])}")

    breakdown["keywords"] = keyword_score * 0.30
    score += breakdown["keywords"]

    # 2. Domain matching (25% weight)
    domain_score = 0.0
    if metadata.domains:
        matched_domains = []
        for domain in metadata.domains:
            domain_lower = domain.lower()
            if domain_lower in task_text or domain_lower in domains:
                domain_score += 1.0
                matched_domains.append(domain)
            elif any(d in domain_lower or domain_lower in d for d in domains):
                domain_score += 0.5

        domain_score = min(domain_score / len(metadata.domains), 1.0)
        if matched_domains:
            matched_criteria.append(f"domains: {', '.join(matched_domains)}")

    breakdown["domains"] = domain_score * 0.25
    score += breakdown["domains"]

    # 3. Language matching (20% weight)
    language_score = 0.0
    if metadata.languages and metadata.languages != ["any"]:
        matched_languages = []
        for lang in metadata.languages:
            lang_lower = lang.lower()
            if lang_lower in languages or lang_lower in task_text:
                language_score += 1.0
                matched_languages.append(lang)

        if metadata.languages:
            language_score = min(language_score / len(metadata.languages), 1.0)
        if matched_languages:
            matched_criteria.append(f"languages: {', '.join(matched_languages)}")
    elif metadata.languages == ["any"]:
        language_score = 0.3  # Neutral score for any-language agents

    breakdown["languages"] = language_score * 0.20
    score += breakdown["languages"]

    # 4. File pattern matching (15% weight)
    file_pattern_score = 0.0
    if metadata.file_patterns and files:
        matched_patterns = []
        for pattern in metadata.file_patterns:
            pattern_lower = pattern.lower()
            for file in files:
                if pattern_lower in file or fnmatch.fnmatch(file, pattern_lower):
                    file_pattern_score += 1.0
                    matched_patterns.append(pattern)
                    break

        if metadata.file_patterns:
            file_pattern_score = min(file_pattern_score / len(metadata.file_patterns), 1.0)
        if matched_patterns:
            matched_criteria.append(f"files: {', '.join(matched_patterns[:3])}")

    breakdown["file_patterns"] = file_pattern_score * 0.15
    score += breakdown["file_patterns"]

    # 5. Import pattern matching (10% weight)
    import_score = 0.0
    if metadata.imports and imports:
        matched_imports = []
        for imp in metadata.imports:
            imp_lower = imp.lower()
            if any(imp_lower in i or i in imp_lower for i in imports):
                import_score += 1.0
                matched_imports.append(imp)

        if metadata.imports:
            import_score = min(import_score / len(metadata.imports), 1.0)
        if matched_imports:
            matched_criteria.append(f"imports: {', '.join(matched_imports[:2])}")

    breakdown["imports"] = import_score * 0.10
    score += breakdown["imports"]

    # 6. Priority bonus (up to 10%)
    priority_bonus = (4 - metadata.priority) / 3 * 0.10
    breakdown["priority"] = priority_bonus
    score += priority_bonus

    # Determine confidence level
    if score >= 0.8:
        confidence = "excellent"
    elif score >= 0.6:
        confidence = "high"
    elif score >= 0.4:
        confidence = "medium"
    else:
        confidence = "low"

    return MatchScore(
        agent_id=metadata.id,
        total_score=score,
        breakdown=breakdown,
        matched_criteria=matched_criteria,
        confidence=confidence,
    )


def select_agent(context: dict[str, Any], top_n: int = 3) -> dict[str, Any]:
    """
    Select the best agent(s) for a given context.

    Args:
        context: Task context with task, files, languages, etc.
        top_n: Number of top alternatives to return

    Returns:
        Selection result with primary agent and alternatives
    """
    scores = []

    for agent in AGENTS:
        match_score = calculate_match_score(context, agent)
        scores.append(match_score)

    # Sort by total score
    scores.sort(key=lambda x: x.total_score, reverse=True)

    # Primary selection
    primary = scores[0]
    alternatives = [asdict(s) for s in scores[1:top_n]]

    return {
        "selected_agent": primary.agent_id,
        "confidence": primary.confidence,
        "score": round(primary.total_score, 4),
        "breakdown": {k: round(v, 4) for k, v in primary.breakdown.items()},
        "matched_criteria": primary.matched_criteria,
        "alternatives": alternatives,
    }


def main():
    """Main entry point for script execution."""
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No context provided. Pass JSON as first argument."}))
        sys.exit(1)

    try:
        context = json.loads(sys.argv[1])
    except json.JSONDecodeError as e:
        print(json.dumps({"error": f"Invalid JSON: {e}"}))
        sys.exit(1)

    result = select_agent(context)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
