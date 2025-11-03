"""
Socratic Mentor Agent for SuperClaude Framework

This agent specializes in educational guidance through the Socratic method,
helping users discover solutions through strategic questioning and guided exploration.
"""

from typing import Dict, Any, List, Optional
import re
import json
import logging
from pathlib import Path

from ..base import BaseAgent


class SocraticMentor(BaseAgent):
    """
    Agent specialized in educational guidance through Socratic method.

    Uses strategic questioning to guide discovery learning, helping users
    understand concepts deeply rather than just providing answers.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the Socratic mentor.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if 'name' not in config:
            config['name'] = 'socratic-mentor'
        if 'description' not in config:
            config['description'] = 'Educational guide using Socratic method'
        if 'category' not in config:
            config['category'] = 'education'

        super().__init__(config)

        # Socratic patterns and learning frameworks
        self.question_types = self._initialize_question_types()
        self.learning_stages = self._initialize_learning_stages()
        self.concept_frameworks = self._initialize_concept_frameworks()
        self.scaffolding_patterns = self._initialize_scaffolding_patterns()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute Socratic mentoring session.

        Args:
            context: Execution context

        Returns:
            Educational guidance and learning path
        """
        result = {
            'success': False,
            'output': '',
            'actions_taken': [],
            'errors': [],
            'learning_assessment': {},
            'questions_posed': [],
            'concepts_explored': [],
            'learning_path': [],
            'next_steps': [],
            'resources': []
        }

        try:
            # Initialize if needed
            if not self._initialized:
                if not self.initialize():
                    result['errors'].append("Failed to initialize agent")
                    return result

            topic = context.get('topic', '')
            question = context.get('question', '')
            level = context.get('level', 'intermediate')
            goal = context.get('goal', 'understanding')

            if not topic and not question:
                result['errors'].append("No topic or question for mentoring")
                return result

            self.logger.info(f"Starting Socratic mentoring: {topic[:100]}...")

            # Phase 1: Assess current understanding
            assessment = self._assess_understanding(topic, question, level)
            result['learning_assessment'] = assessment
            result['actions_taken'].append("Assessed current understanding level")

            # Phase 2: Generate guiding questions
            questions = self._generate_guiding_questions(topic, assessment, goal)
            result['questions_posed'] = questions
            result['actions_taken'].append(f"Generated {len(questions)} guiding questions")

            # Phase 3: Identify key concepts
            concepts = self._identify_key_concepts(topic, question, assessment)
            result['concepts_explored'] = concepts
            result['actions_taken'].append(f"Identified {len(concepts)} key concepts")

            # Phase 4: Create learning path
            learning_path = self._create_learning_path(concepts, assessment, level)
            result['learning_path'] = learning_path
            result['actions_taken'].append(f"Created {len(learning_path)} step learning path")

            # Phase 5: Determine next steps
            next_steps = self._determine_next_steps(assessment, learning_path, goal)
            result['next_steps'] = next_steps
            result['actions_taken'].append("Determined learning next steps")

            # Phase 6: Gather resources
            resources = self._gather_learning_resources(topic, concepts, level)
            result['resources'] = resources
            result['actions_taken'].append(f"Gathered {len(resources)} learning resources")

            # Phase 7: Generate mentoring report
            report = self._generate_mentoring_report(
                topic, assessment, questions, concepts,
                learning_path, next_steps, resources
            )
            result['output'] = report

            result['success'] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Socratic mentoring failed: {e}")
            result['errors'].append(str(e))

        return result

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains educational/mentoring tasks
        """
        task = context.get('task', '')

        # Check for educational keywords
        education_keywords = [
            'learn', 'teach', 'explain', 'understand', 'mentor',
            'guide', 'tutorial', 'concept', 'why', 'how does',
            'what is', 'educate', 'study', 'practice'
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in education_keywords)

    def _initialize_question_types(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize Socratic question types.

        Returns:
            Dictionary of question types
        """
        return {
            'clarification': {
                'purpose': 'Ensure clear understanding of the problem',
                'examples': [
                    "What do you mean by...?",
                    "Can you give an example of...?",
                    "How does this relate to...?"
                ],
                'stage': 'initial'
            },
            'assumptions': {
                'purpose': 'Challenge underlying assumptions',
                'examples': [
                    "What assumptions are you making?",
                    "What if the opposite were true?",
                    "Is this always the case?"
                ],
                'stage': 'exploration'
            },
            'evidence': {
                'purpose': 'Examine reasoning and evidence',
                'examples': [
                    "How do you know this?",
                    "What evidence supports this?",
                    "What might someone who disagrees say?"
                ],
                'stage': 'analysis'
            },
            'perspective': {
                'purpose': 'Explore different viewpoints',
                'examples': [
                    "What's another way to look at this?",
                    "What are the strengths and weaknesses?",
                    "Why is this issue important?"
                ],
                'stage': 'synthesis'
            },
            'consequences': {
                'purpose': 'Consider implications and consequences',
                'examples': [
                    "What follows from this?",
                    "How does this affect...?",
                    "What would happen if...?"
                ],
                'stage': 'evaluation'
            },
            'metacognitive': {
                'purpose': 'Reflect on the thinking process',
                'examples': [
                    "How did you arrive at this conclusion?",
                    "What was most challenging about this?",
                    "What would you do differently?"
                ],
                'stage': 'reflection'
            }
        }

    def _initialize_learning_stages(self) -> List[Dict[str, Any]]:
        """
        Initialize learning progression stages.

        Returns:
            List of learning stages
        """
        return [
            {
                'stage': 'awareness',
                'description': 'Recognition that knowledge gap exists',
                'objective': 'Identify what needs to be learned'
            },
            {
                'stage': 'exploration',
                'description': 'Initial investigation of concepts',
                'objective': 'Discover fundamental principles'
            },
            {
                'stage': 'understanding',
                'description': 'Grasp of core concepts',
                'objective': 'Comprehend how and why things work'
            },
            {
                'stage': 'application',
                'description': 'Use knowledge in practice',
                'objective': 'Apply concepts to solve problems'
            },
            {
                'stage': 'analysis',
                'description': 'Break down complex problems',
                'objective': 'Decompose and examine components'
            },
            {
                'stage': 'synthesis',
                'description': 'Combine knowledge creatively',
                'objective': 'Create new solutions from understanding'
            },
            {
                'stage': 'evaluation',
                'description': 'Judge and assess solutions',
                'objective': 'Critical thinking and decision making'
            }
        ]

    def _initialize_concept_frameworks(self) -> Dict[str, List[str]]:
        """
        Initialize concept learning frameworks.

        Returns:
            Dictionary of concept frameworks
        """
        return {
            'programming': [
                'Variables and data types',
                'Control structures',
                'Functions and scope',
                'Data structures',
                'Algorithms',
                'Object-oriented concepts',
                'Design patterns',
                'Testing and debugging'
            ],
            'system_design': [
                'Requirements analysis',
                'Architecture patterns',
                'Component design',
                'Data modeling',
                'API design',
                'Scalability',
                'Security',
                'Deployment'
            ],
            'problem_solving': [
                'Problem definition',
                'Decomposition',
                'Pattern recognition',
                'Abstraction',
                'Algorithm design',
                'Testing hypotheses',
                'Optimization',
                'Trade-offs'
            ],
            'software_engineering': [
                'Development lifecycle',
                'Version control',
                'Code quality',
                'Documentation',
                'Collaboration',
                'Testing strategies',
                'Deployment',
                'Maintenance'
            ]
        }

    def _initialize_scaffolding_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize learning scaffolding patterns.

        Returns:
            Dictionary of scaffolding patterns
        """
        return {
            'worked_example': {
                'description': 'Step-by-step demonstration',
                'use_case': 'Initial exposure to concept',
                'support_level': 'high'
            },
            'partial_solution': {
                'description': 'Incomplete solution to complete',
                'use_case': 'Guided practice',
                'support_level': 'medium'
            },
            'hints_and_tips': {
                'description': 'Strategic hints without full solution',
                'use_case': 'Independent problem solving',
                'support_level': 'low'
            },
            'exploration_prompt': {
                'description': 'Open-ended investigation',
                'use_case': 'Discovery learning',
                'support_level': 'minimal'
            }
        }

    def _assess_understanding(self, topic: str, question: str, level: str) -> Dict[str, Any]:
        """
        Assess learner's current understanding.

        Args:
            topic: Learning topic
            question: Learner's question
            level: Stated experience level

        Returns:
            Understanding assessment
        """
        assessment = {
            'level': level,
            'gaps': [],
            'strengths': [],
            'misconceptions': [],
            'learning_style': 'unknown',
            'readiness': 'moderate'
        }

        # Analyze question complexity
        question_lower = question.lower() if question else ''

        # Identify knowledge gaps from question type
        if 'what is' in question_lower or 'define' in question_lower:
            assessment['gaps'].append('Basic definitions')
            assessment['readiness'] = 'beginner'
        elif 'how to' in question_lower:
            assessment['gaps'].append('Practical application')
            assessment['readiness'] = 'intermediate'
        elif 'why' in question_lower or 'when' in question_lower:
            assessment['gaps'].append('Conceptual understanding')
            assessment['readiness'] = 'advanced'

        # Identify strengths based on question sophistication
        if 'compare' in question_lower or 'difference' in question_lower:
            assessment['strengths'].append('Comparative thinking')
        if 'optimize' in question_lower or 'improve' in question_lower:
            assessment['strengths'].append('Performance awareness')
        if 'pattern' in question_lower or 'architecture' in question_lower:
            assessment['strengths'].append('Abstract thinking')

        # Identify potential misconceptions
        if 'always' in question_lower or 'never' in question_lower:
            assessment['misconceptions'].append('Absolute thinking')
        if 'best' in question_lower and 'context' not in question_lower:
            assessment['misconceptions'].append('Context-independent solutions')

        # Infer learning style
        if 'example' in question_lower or 'show' in question_lower:
            assessment['learning_style'] = 'visual/example-based'
        elif 'explain' in question_lower or 'understand' in question_lower:
            assessment['learning_style'] = 'conceptual'
        elif 'step' in question_lower or 'how to' in question_lower:
            assessment['learning_style'] = 'procedural'

        return assessment

    def _generate_guiding_questions(
        self, topic: str, assessment: Dict[str, Any], goal: str
    ) -> List[Dict[str, Any]]:
        """
        Generate Socratic guiding questions.

        Args:
            topic: Learning topic
            assessment: Understanding assessment
            goal: Learning goal

        Returns:
            List of guiding questions
        """
        questions = []

        # Start with clarification questions
        questions.append({
            'type': 'clarification',
            'question': f"What specifically about {topic} would you like to understand better?",
            'purpose': 'Focus learning objectives',
            'follow_up': 'Can you describe what you already know about this?'
        })

        # Add assumption-challenging questions
        questions.append({
            'type': 'assumptions',
            'question': f"What assumptions are you making about how {topic} works?",
            'purpose': 'Identify preconceptions',
            'follow_up': 'What leads you to believe this?'
        })

        # Add evidence-seeking questions
        questions.append({
            'type': 'evidence',
            'question': "What evidence or examples have you seen of this concept in practice?",
            'purpose': 'Connect to experience',
            'follow_up': 'How might you test this understanding?'
        })

        # Add perspective questions based on level
        if assessment['readiness'] in ['intermediate', 'advanced']:
            questions.append({
                'type': 'perspective',
                'question': "How would different stakeholders view this solution?",
                'purpose': 'Broaden thinking',
                'follow_up': 'What trade-offs are involved?'
            })

        # Add consequence questions
        questions.append({
            'type': 'consequences',
            'question': "What would happen if we applied this concept incorrectly?",
            'purpose': 'Understand implications',
            'follow_up': 'How can we prevent these issues?'
        })

        # Add metacognitive questions
        questions.append({
            'type': 'metacognitive',
            'question': "What part of this concept is most challenging for you?",
            'purpose': 'Self-reflection',
            'follow_up': 'What learning approach works best for you?'
        })

        return questions

    def _identify_key_concepts(
        self, topic: str, question: str, assessment: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """
        Identify key concepts to explore.

        Args:
            topic: Learning topic
            question: Learner's question
            assessment: Understanding assessment

        Returns:
            List of key concepts
        """
        concepts = []

        # Map topic to concept framework
        topic_lower = topic.lower()

        # Determine which framework to use
        if 'program' in topic_lower or 'code' in topic_lower:
            framework = self.concept_frameworks['programming']
            category = 'programming'
        elif 'design' in topic_lower or 'architect' in topic_lower:
            framework = self.concept_frameworks['system_design']
            category = 'system_design'
        elif 'problem' in topic_lower or 'solve' in topic_lower:
            framework = self.concept_frameworks['problem_solving']
            category = 'problem_solving'
        else:
            framework = self.concept_frameworks['software_engineering']
            category = 'software_engineering'

        # Select concepts based on assessment level
        if assessment['readiness'] == 'beginner':
            selected_concepts = framework[:3]  # First 3 concepts
        elif assessment['readiness'] == 'intermediate':
            selected_concepts = framework[2:6]  # Middle concepts
        else:
            selected_concepts = framework[4:]  # Advanced concepts

        # Create concept objects
        for i, concept_name in enumerate(selected_concepts[:5]):  # Limit to 5
            concepts.append({
                'name': concept_name,
                'category': category,
                'complexity': 'basic' if i < 2 else 'intermediate' if i < 4 else 'advanced',
                'prerequisites': selected_concepts[:i] if i > 0 else [],
                'importance': 'critical' if i < 2 else 'important'
            })

        return concepts

    def _create_learning_path(
        self, concepts: List[Dict[str, Any]], assessment: Dict[str, Any], level: str
    ) -> List[Dict[str, Any]]:
        """
        Create personalized learning path.

        Args:
            concepts: Key concepts
            assessment: Understanding assessment
            level: Experience level

        Returns:
            Learning path steps
        """
        learning_path = []

        # Create steps for each concept
        for i, concept in enumerate(concepts):
            # Determine scaffolding based on level
            if level == 'beginner':
                scaffold = self.scaffolding_patterns['worked_example']
            elif level == 'intermediate':
                scaffold = self.scaffolding_patterns['partial_solution']
            else:
                scaffold = self.scaffolding_patterns['hints_and_tips']

            step = {
                'step': i + 1,
                'concept': concept['name'],
                'objective': f"Understand and apply {concept['name']}",
                'approach': scaffold['description'],
                'activities': [],
                'estimated_time': '30-45 minutes',
                'assessment_method': 'Practice problem'
            }

            # Add activities based on learning style
            if assessment.get('learning_style') == 'visual/example-based':
                step['activities'].extend([
                    'Study worked examples',
                    'Analyze code samples',
                    'Create visual diagrams'
                ])
            elif assessment.get('learning_style') == 'conceptual':
                step['activities'].extend([
                    'Read conceptual overview',
                    'Explore underlying principles',
                    'Compare with similar concepts'
                ])
            else:
                step['activities'].extend([
                    'Follow step-by-step tutorial',
                    'Complete guided exercises',
                    'Build small project'
                ])

            learning_path.append(step)

        return learning_path

    def _determine_next_steps(
        self, assessment: Dict[str, Any], learning_path: List[Dict[str, Any]], goal: str
    ) -> List[Dict[str, Any]]:
        """
        Determine next learning steps.

        Args:
            assessment: Understanding assessment
            learning_path: Created learning path
            goal: Learning goal

        Returns:
            List of next steps
        """
        next_steps = []

        # Immediate next step
        next_steps.append({
            'priority': 'immediate',
            'action': 'Begin with the first concept in the learning path',
            'description': f"Start with {learning_path[0]['concept'] if learning_path else 'fundamentals'}",
            'resources': 'Use provided learning resources'
        })

        # Short-term steps
        next_steps.append({
            'priority': 'short-term',
            'action': 'Complete hands-on practice',
            'description': 'Apply concepts through practical exercises',
            'resources': 'Practice problems and projects'
        })

        # Address gaps
        if assessment['gaps']:
            next_steps.append({
                'priority': 'important',
                'action': 'Address knowledge gaps',
                'description': f"Focus on: {', '.join(assessment['gaps'][:3])}",
                'resources': 'Targeted tutorials and explanations'
            })

        # Address misconceptions
        if assessment['misconceptions']:
            next_steps.append({
                'priority': 'critical',
                'action': 'Correct misconceptions',
                'description': f"Clarify: {', '.join(assessment['misconceptions'][:2])}",
                'resources': 'Conceptual clarifications'
            })

        # Long-term development
        next_steps.append({
            'priority': 'long-term',
            'action': 'Build portfolio project',
            'description': 'Apply all learned concepts in a comprehensive project',
            'resources': 'Project ideas and guidelines'
        })

        return next_steps

    def _gather_learning_resources(
        self, topic: str, concepts: List[Dict[str, Any]], level: str
    ) -> List[Dict[str, Any]]:
        """
        Gather appropriate learning resources.

        Args:
            topic: Learning topic
            concepts: Key concepts
            level: Experience level

        Returns:
            List of learning resources
        """
        resources = []

        # Documentation resources
        resources.append({
            'type': 'documentation',
            'title': f'Official {topic} Documentation',
            'description': 'Primary source for accurate information',
            'level': 'all',
            'format': 'text'
        })

        # Tutorial resources based on level
        if level == 'beginner':
            resources.append({
                'type': 'tutorial',
                'title': 'Interactive Beginner Tutorial',
                'description': 'Step-by-step guided learning',
                'level': 'beginner',
                'format': 'interactive'
            })
        elif level == 'intermediate':
            resources.append({
                'type': 'course',
                'title': 'Intermediate Concepts Course',
                'description': 'Structured learning with projects',
                'level': 'intermediate',
                'format': 'video'
            })
        else:
            resources.append({
                'type': 'book',
                'title': 'Advanced Patterns and Practices',
                'description': 'Deep dive into advanced topics',
                'level': 'advanced',
                'format': 'text'
            })

        # Practice resources
        resources.append({
            'type': 'practice',
            'title': 'Coding Challenges',
            'description': 'Hands-on practice problems',
            'level': level,
            'format': 'interactive'
        })

        # Community resources
        resources.append({
            'type': 'community',
            'title': 'Developer Forums and Q&A',
            'description': 'Get help and share knowledge',
            'level': 'all',
            'format': 'discussion'
        })

        # Reference resources
        resources.append({
            'type': 'reference',
            'title': 'Quick Reference Guide',
            'description': 'Cheat sheets and quick lookups',
            'level': 'all',
            'format': 'text'
        })

        return resources

    def _generate_mentoring_report(
        self, topic: str, assessment: Dict[str, Any],
        questions: List[Dict[str, Any]], concepts: List[Dict[str, Any]],
        learning_path: List[Dict[str, Any]], next_steps: List[Dict[str, Any]],
        resources: List[Dict[str, Any]]
    ) -> str:
        """
        Generate comprehensive mentoring report.

        Args:
            topic: Learning topic
            assessment: Understanding assessment
            questions: Guiding questions
            concepts: Key concepts
            learning_path: Learning path
            next_steps: Next steps
            resources: Learning resources

        Returns:
            Socratic mentoring report
        """
        lines = []

        # Header
        lines.append("# Socratic Learning Guide\n")
        lines.append(f"**Topic**: {topic}\n")
        lines.append(f"**Learning Level**: {assessment['level'].title()}")
        lines.append(f"**Readiness**: {assessment['readiness'].title()}\n")

        # Learning Assessment
        lines.append("## Your Learning Profile\n")
        if assessment.get('learning_style') != 'unknown':
            lines.append(f"**Learning Style**: {assessment['learning_style'].replace('/', ' / ').title()}")

        if assessment['strengths']:
            lines.append("\n### Strengths to Build On")
            for strength in assessment['strengths']:
                lines.append(f"- ✅ {strength}")

        if assessment['gaps']:
            lines.append("\n### Areas for Growth")
            for gap in assessment['gaps']:
                lines.append(f"- 📚 {gap}")

        if assessment['misconceptions']:
            lines.append("\n### Misconceptions to Address")
            for misconception in assessment['misconceptions']:
                lines.append(f"- ⚠️ {misconception}")

        # Guiding Questions
        lines.append("\n## Questions to Guide Your Learning\n")
        lines.append("*Reflect on these questions as you learn:*\n")
        for i, q in enumerate(questions[:6], 1):
            lines.append(f"### {i}. {q['question']}")
            lines.append(f"**Purpose**: {q['purpose']}")
            lines.append(f"**Follow-up**: {q['follow_up']}\n")

        # Key Concepts
        lines.append("## Concepts to Master\n")
        for concept in concepts:
            complexity_emoji = {'basic': '🟢', 'intermediate': '🟡', 'advanced': '🔴'}.get(
                concept['complexity'], '⚪'
            )
            lines.append(f"{complexity_emoji} **{concept['name']}**")
            if concept['prerequisites']:
                lines.append(f"   - Prerequisites: {', '.join(concept['prerequisites'][:2])}")

        # Learning Path
        lines.append("\n## Your Personalized Learning Path\n")
        for step in learning_path:
            lines.append(f"### Step {step['step']}: {step['concept']}")
            lines.append(f"**Objective**: {step['objective']}")
            lines.append(f"**Approach**: {step['approach']}")
            lines.append(f"**Time**: {step['estimated_time']}")
            lines.append("\n**Activities**:")
            for activity in step['activities']:
                lines.append(f"- {activity}")
            lines.append("")

        # Next Steps
        lines.append("## Next Steps\n")
        priority_emoji = {
            'immediate': '🚀',
            'short-term': '📅',
            'important': '⚠️',
            'critical': '🚨',
            'long-term': '🎯'
        }
        for step in next_steps:
            emoji = priority_emoji.get(step['priority'], '📌')
            lines.append(f"{emoji} **{step['action']}**")
            lines.append(f"   - {step['description']}")

        # Learning Resources
        lines.append("\n## Recommended Resources\n")
        type_emoji = {
            'documentation': '📖',
            'tutorial': '🎓',
            'course': '📚',
            'book': '📘',
            'practice': '💻',
            'community': '👥',
            'reference': '📋'
        }
        for resource in resources:
            emoji = type_emoji.get(resource['type'], '📄')
            lines.append(f"{emoji} **{resource['title']}** ({resource['level']})")
            lines.append(f"   - {resource['description']}")

        # Learning Tips
        lines.append("\n## Learning Tips\n")
        lines.append("1. **Ask Why**: Always question why something works the way it does")
        lines.append("2. **Make Connections**: Link new concepts to what you already know")
        lines.append("3. **Practice Deliberately**: Focus on weak areas, not just comfortable ones")
        lines.append("4. **Teach Others**: Explaining concepts solidifies understanding")
        lines.append("5. **Reflect Regularly**: Review what you've learned and identify gaps")
        lines.append("6. **Embrace Mistakes**: Errors are learning opportunities")

        # Closing Encouragement
        lines.append("\n## Remember\n")
        lines.append("*\"The only true wisdom is in knowing you know nothing.\"* - Socrates\n")
        lines.append("Learning is a journey, not a destination. Each question you ask and ")
        lines.append("concept you explore brings you closer to mastery. Stay curious!")

        return '\n'.join(lines)
