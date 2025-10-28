"""
Technical Writer Agent for SuperClaude Framework

This agent specializes in creating clear, comprehensive documentation
for code, APIs, and technical systems.
"""

from typing import Dict, Any, List, Optional
import re
import logging

from ..base import BaseAgent
from ..heuristic_markdown import HeuristicMarkdownAgent
from ..heuristic_markdown import HeuristicMarkdownAgent


class TechnicalDocumentationAgent(BaseAgent):
    """
    Agent specialized in technical documentation creation.

    Generates clear, structured documentation for various technical
    contexts including code, APIs, architecture, and user guides.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the technical writer.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if 'name' not in config:
            config['name'] = 'technical-writer'
        if 'description' not in config:
            config['description'] = 'Create clear technical documentation'
        if 'category' not in config:
            config['category'] = 'documentation'

        super().__init__(config)

        # Documentation templates
        self.doc_templates = self._initialize_templates()
        self.doc_sections = self._initialize_sections()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute documentation creation.

        Args:
            context: Execution context

        Returns:
            Generated documentation
        """
        result = {
            'success': False,
            'output': '',
            'actions_taken': [],
            'errors': [],
            'doc_type': None,
            'sections_created': []
        }

        try:
            # Initialize if needed
            if not self._initialized:
                if not self.initialize():
                    result['errors'].append("Failed to initialize agent")
                    return result

            task = context.get('task', '')
            subject = context.get('subject', '')
            doc_type = context.get('doc_type', 'auto')
            code = context.get('code', '')

            if not task and not subject:
                result['errors'].append("No documentation subject provided")
                return result

            self.logger.info(f"Creating documentation: {task[:100]}...")

            # Phase 1: Determine documentation type
            if doc_type == 'auto':
                doc_type = self._determine_doc_type(task, subject, code)
            result['doc_type'] = doc_type
            result['actions_taken'].append(f"Determined doc type: {doc_type}")

            # Phase 2: Analyze subject matter
            analysis = self._analyze_subject(task, subject, code, doc_type)
            result['actions_taken'].append("Analyzed subject matter")

            # Phase 3: Plan documentation structure
            structure = self._plan_structure(doc_type, analysis)
            result['actions_taken'].append(f"Planned {len(structure)} sections")

            # Phase 4: Generate documentation sections
            sections = self._generate_sections(structure, analysis, doc_type)
            result['sections_created'] = [s['title'] for s in sections]
            result['actions_taken'].append(f"Generated {len(sections)} sections")

            # Phase 5: Assemble final documentation
            documentation = self._assemble_documentation(
                sections, doc_type, task, analysis
            )
            result['output'] = documentation

            result['success'] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Documentation generation failed: {e}")
            result['errors'].append(str(e))

        return result


class TechnicalWriter(HeuristicMarkdownAgent):
    """Strategist-class technical writer with heuristic planning and doc synthesis."""

    STRATEGIST_TIER = True

    DOC_KEYWORDS = {
        'document', 'documentation', 'docs', 'readme', 'explain', 'describe',
        'write docs', 'api docs', 'user guide', 'technical docs', 'comment'
    }

    def __init__(self, config: Dict[str, Any]):
        defaults = {
            'name': 'technical-writer',
            'description': 'Create clear technical documentation',
            'category': 'documentation',
            'capability_tier': 'strategist'
        }
        merged = {**defaults, **config}
        super().__init__(merged)

        self.doc_agent = TechnicalDocumentationAgent(dict(merged))
        self.doc_agent.logger = self.logger

    def validate(self, context: Dict[str, Any]) -> bool:
        task = str(context.get('task', '')).lower()
        if any(keyword in task for keyword in self.DOC_KEYWORDS):
            return True
        subject = str(context.get('subject', '')).lower()
        if any(keyword in subject for keyword in self.DOC_KEYWORDS):
            return True
        return super().validate(context) or self.doc_agent.validate(context)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        result = super().execute(context)

        doc_result = self.doc_agent.execute(context)
        result['documentation_artifact'] = doc_result

        if doc_result.get('success'):
            doc_output = doc_result.get('output') or ''
            doc_type = doc_result.get('doc_type')
            sections = doc_result.get('sections_created') or []

            actions = self._ensure_list(result, 'actions_taken')
            actions.append('Drafted structured documentation artifact')
            if sections:
                actions.append(f"Created documentation sections: {', '.join(sections[:5])}")

            follow_up = self._ensure_list(result, 'follow_up_actions')
            follow_up.append('Review generated documentation with stakeholders for accuracy.')

            if doc_type:
                follow_up.append(f"Ensure {doc_type} documentation stays in sync with implementation changes.")

            if doc_output:
                result['documentation_body'] = doc_output
                if result.get('output'):
                    result['output'] = f"{result['output']}\n\n## Documentation Draft\n{doc_output}".strip()
                else:
                    result['output'] = doc_output
        else:
            errors = doc_result.get('errors') or []
            if errors:
                warnings = self._ensure_list(result, 'warnings')
                for err in errors:
                    if err not in warnings:
                        warnings.append(err)

        return result
    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains documentation task
        """
        task = context.get('task', '')

        # Check for documentation keywords
        doc_keywords = [
            'document', 'documentation', 'docs', 'readme',
            'explain', 'describe', 'write docs', 'api docs',
            'user guide', 'technical docs', 'comment'
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in doc_keywords)

    def _initialize_templates(self) -> Dict[str, str]:
        """
        Initialize documentation templates.

        Returns:
            Dictionary of documentation templates
        """
        return {
            'readme': """# {title}

{description}

## Installation

{installation}

## Usage

{usage}

## Features

{features}

## Contributing

{contributing}

## License

{license}
""",
            'api': """# {title} API Documentation

## Overview

{overview}

## Authentication

{authentication}

## Endpoints

{endpoints}

## Request/Response Examples

{examples}

## Error Codes

{errors}

## Rate Limiting

{rate_limiting}
""",
            'function': """## {function_name}

### Description
{description}

### Parameters
{parameters}

### Returns
{returns}

### Examples
```{language}
{examples}
```

### Exceptions
{exceptions}
""",
            'class': """## Class: {class_name}

### Description
{description}

### Properties
{properties}

### Methods
{methods}

### Usage Example
```{language}
{example}
```
""",
            'guide': """# {title}

## Introduction
{introduction}

## Prerequisites
{prerequisites}

## Step-by-Step Instructions
{steps}

## Troubleshooting
{troubleshooting}

## Additional Resources
{resources}
"""
        }

    def _initialize_sections(self) -> Dict[str, List[str]]:
        """
        Initialize documentation sections by type.

        Returns:
            Dictionary of section lists by doc type
        """
        return {
            'readme': [
                'Overview', 'Installation', 'Quick Start', 'Features',
                'Usage', 'Configuration', 'Contributing', 'License'
            ],
            'api': [
                'Overview', 'Authentication', 'Base URL', 'Endpoints',
                'Request Format', 'Response Format', 'Error Handling',
                'Examples', 'Rate Limiting'
            ],
            'technical': [
                'Architecture Overview', 'Components', 'Data Flow',
                'Dependencies', 'Configuration', 'Deployment',
                'Performance', 'Security', 'Troubleshooting'
            ],
            'user_guide': [
                'Introduction', 'Getting Started', 'Features',
                'How-To Guides', 'Best Practices', 'FAQ',
                'Troubleshooting', 'Support'
            ],
            'code': [
                'Purpose', 'Parameters', 'Return Values',
                'Usage Examples', 'Edge Cases', 'Performance Notes',
                'Related Functions'
            ]
        }

    def _determine_doc_type(self, task: str, subject: str, code: str) -> str:
        """
        Determine the appropriate documentation type.

        Args:
            task: Task description
            subject: Subject matter
            code: Code snippet if available

        Returns:
            Documentation type
        """
        combined = f"{task} {subject}".lower()

        # Check for specific doc type indicators
        if 'readme' in combined:
            return 'readme'
        elif 'api' in combined or 'endpoint' in combined:
            return 'api'
        elif 'guide' in combined or 'tutorial' in combined:
            return 'user_guide'
        elif 'function' in combined or 'method' in combined:
            return 'code'
        elif 'class' in combined or 'object' in combined:
            return 'code'
        elif 'architecture' in combined or 'system' in combined:
            return 'technical'

        # Default based on presence of code
        if code:
            return 'code'
        else:
            return 'technical'

    def _analyze_subject(
        self, task: str, subject: str, code: str, doc_type: str
    ) -> Dict[str, Any]:
        """
        Analyze the subject matter for documentation.

        Args:
            task: Task description
            subject: Subject matter
            code: Code snippet
            doc_type: Documentation type

        Returns:
            Analysis results
        """
        analysis = {
            'main_topic': subject or self._extract_topic(task),
            'key_concepts': [],
            'technical_level': 'intermediate',
            'audience': 'developers',
            'scope': 'comprehensive'
        }

        # Extract key concepts
        concepts = self._extract_concepts(task, subject, code)
        analysis['key_concepts'] = concepts

        # Determine technical level
        if any(word in task.lower() for word in ['beginner', 'intro', 'basic']):
            analysis['technical_level'] = 'beginner'
        elif any(word in task.lower() for word in ['advanced', 'expert', 'complex']):
            analysis['technical_level'] = 'advanced'

        # Determine audience
        if 'user' in task.lower() or 'guide' in doc_type:
            analysis['audience'] = 'end users'
        elif 'internal' in task.lower():
            analysis['audience'] = 'internal team'

        # Determine scope
        if any(word in task.lower() for word in ['quick', 'brief', 'summary']):
            analysis['scope'] = 'summary'
        elif any(word in task.lower() for word in ['detailed', 'comprehensive', 'complete']):
            analysis['scope'] = 'comprehensive'

        return analysis

    def _extract_topic(self, text: str) -> str:
        """
        Extract main topic from text.

        Args:
            text: Text to analyze

        Returns:
            Main topic
        """
        # Remove common words
        stop_words = {'the', 'a', 'an', 'for', 'to', 'of', 'in', 'on', 'at', 'by'}
        words = text.split()
        meaningful_words = [w for w in words if w.lower() not in stop_words]

        # Return first few meaningful words as topic
        return ' '.join(meaningful_words[:5])

    def _extract_concepts(self, task: str, subject: str, code: str) -> List[str]:
        """
        Extract key concepts to document.

        Args:
            task: Task description
            subject: Subject matter
            code: Code snippet

        Returns:
            List of key concepts
        """
        concepts = []
        combined = f"{task} {subject} {code}"

        # Technical concept patterns
        patterns = {
            'functions': r'\bdef\s+(\w+)',
            'classes': r'\bclass\s+(\w+)',
            'apis': r'(?:GET|POST|PUT|DELETE)\s+([/\w]+)',
            'variables': r'\b([A-Z_]+)\s*=',
            'imports': r'(?:import|from)\s+(\w+)'
        }

        for concept_type, pattern in patterns.items():
            matches = re.findall(pattern, combined)
            for match in matches[:3]:  # Limit to 3 per type
                concepts.append(match)

        # Add mentioned technologies
        tech_keywords = [
            'python', 'javascript', 'api', 'database', 'server',
            'client', 'frontend', 'backend', 'framework', 'library'
        ]

        combined_lower = combined.lower()
        for tech in tech_keywords:
            if tech in combined_lower:
                concepts.append(tech)

        return list(set(concepts))[:10]  # Return unique concepts, max 10

    def _plan_structure(
        self, doc_type: str, analysis: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Plan documentation structure.

        Args:
            doc_type: Documentation type
            analysis: Subject analysis

        Returns:
            Documentation structure plan
        """
        structure = []

        # Get base sections for doc type
        base_sections = self.doc_sections.get(doc_type, ['Overview', 'Details', 'Examples'])

        # Adapt sections based on analysis
        for section in base_sections:
            include = True

            # Skip sections based on scope
            if analysis['scope'] == 'summary':
                if section in ['Troubleshooting', 'Performance Notes', 'Advanced Features']:
                    include = False

            # Skip sections based on audience
            if analysis['audience'] == 'end users':
                if section in ['Architecture Overview', 'Data Flow', 'Dependencies']:
                    include = False

            if include:
                structure.append({
                    'title': section,
                    'content_type': self._get_content_type(section),
                    'priority': self._get_section_priority(section)
                })

        # Sort by priority
        structure.sort(key=lambda x: x['priority'])

        return structure

    def _get_content_type(self, section: str) -> str:
        """
        Determine content type for section.

        Args:
            section: Section name

        Returns:
            Content type
        """
        if section in ['Overview', 'Introduction', 'Description']:
            return 'narrative'
        elif section in ['Installation', 'Configuration', 'Setup']:
            return 'procedural'
        elif section in ['API', 'Endpoints', 'Methods', 'Functions']:
            return 'reference'
        elif section in ['Examples', 'Usage', 'Quick Start']:
            return 'example'
        else:
            return 'general'

    def _get_section_priority(self, section: str) -> int:
        """
        Get priority for section.

        Args:
            section: Section name

        Returns:
            Priority (lower is higher priority)
        """
        priority_map = {
            'Overview': 1,
            'Introduction': 1,
            'Installation': 2,
            'Quick Start': 3,
            'Getting Started': 3,
            'Usage': 4,
            'Features': 5,
            'Configuration': 6,
            'Examples': 7,
            'API': 8,
            'Troubleshooting': 9,
            'Contributing': 10,
            'License': 11
        }

        return priority_map.get(section, 5)

    def _generate_sections(
        self, structure: List[Dict[str, Any]], analysis: Dict[str, Any], doc_type: str
    ) -> List[Dict[str, Any]]:
        """
        Generate documentation sections.

        Args:
            structure: Documentation structure
            analysis: Subject analysis
            doc_type: Documentation type

        Returns:
            Generated sections
        """
        sections = []

        for section_plan in structure:
            section = {
                'title': section_plan['title'],
                'content': self._generate_section_content(
                    section_plan, analysis, doc_type
                )
            }
            sections.append(section)

        return sections

    def _generate_section_content(
        self, section: Dict[str, Any], analysis: Dict[str, Any], doc_type: str
    ) -> str:
        """
        Generate content for a specific section.

        Args:
            section: Section plan
            analysis: Subject analysis
            doc_type: Documentation type

        Returns:
            Section content
        """
        title = section['title']
        content_type = section['content_type']
        topic = analysis['main_topic']

        # Generate content based on type
        if content_type == 'narrative':
            return f"This section provides an overview of {topic}. " \
                   f"It is designed for {analysis['audience']} " \
                   f"at a {analysis['technical_level']} level."

        elif content_type == 'procedural':
            steps = [
                f"1. First, ensure prerequisites are met",
                f"2. Install required dependencies",
                f"3. Configure {topic}",
                f"4. Verify installation"
            ]
            return '\n'.join(steps)

        elif content_type == 'example':
            return f"```python\n# Example usage of {topic}\n" \
                   f"# TODO: Add specific examples\n```"

        elif content_type == 'reference':
            if analysis['key_concepts']:
                items = [f"- {concept}" for concept in analysis['key_concepts'][:5]]
                return f"Key components:\n" + '\n'.join(items)
            else:
                return f"Reference documentation for {topic}."

        else:
            return f"Content for {title} section."

    def _assemble_documentation(
        self, sections: List[Dict[str, Any]], doc_type: str,
        task: str, analysis: Dict[str, Any]
    ) -> str:
        """
        Assemble final documentation.

        Args:
            sections: Generated sections
            doc_type: Documentation type
            task: Original task
            analysis: Subject analysis

        Returns:
            Complete documentation
        """
        lines = []

        # Add header
        lines.append(f"# {analysis['main_topic']}\n")

        # Add metadata comment
        lines.append(f"<!-- Generated documentation for: {task} -->\n")

        # Add sections
        for section in sections:
            lines.append(f"\n## {section['title']}\n")
            lines.append(section['content'])

        # Add footer
        lines.append(f"\n---\n")
        lines.append(f"*Documentation type: {doc_type}*")
        lines.append(f"*Technical level: {analysis['technical_level']}*")
        lines.append(f"*Target audience: {analysis['audience']}*")

        return '\n'.join(lines)
