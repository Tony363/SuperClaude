"""
Markdown Agent Parser for SuperClaude Framework

This module parses agent definitions from markdown files, extracting
metadata, behavioral mindset, focus areas, and boundaries.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # Optional dependency used for YAML frontmatter
    import yaml
except ModuleNotFoundError:  # pragma: no cover - depends on optional extras
    yaml = None  # type: ignore


class AgentMarkdownParser:
    """
    Parser for agent markdown files.

    Extracts structured data from markdown files that define agent
    behavior, capabilities, and configuration.
    """

    def __init__(self):
        """Initialize the markdown parser."""
        self.logger = logging.getLogger("agent.parser")

    def parse(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """
        Parse an agent markdown file.

        Args:
            file_path: Path to the markdown file

        Returns:
            Dictionary containing parsed agent configuration or None
        """
        try:
            # Try UTF-8 first, then fall back to latin-1
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
            except UnicodeDecodeError:
                # Fall back to latin-1 which accepts all byte values
                with open(file_path, 'r', encoding='latin-1') as f:
                    content = f.read()

            # Parse YAML frontmatter
            config = self._parse_frontmatter(content)

            if not config:
                config = {}

            # Parse markdown sections
            sections = self._parse_sections(content)

            # Extract key information
            config.update(self._extract_agent_info(sections))

            # Ensure required fields
            if 'name' not in config and file_path.stem != '__init__':
                config['name'] = file_path.stem

            return config

        except Exception as e:
            self.logger.error(f"Failed to parse {file_path}: {e}")
            return None

    def _parse_frontmatter(self, content: str) -> Dict[str, Any]:
        """
        Parse YAML frontmatter from markdown content.

        Args:
            content: Markdown file content

        Returns:
            Dictionary containing frontmatter data
        """
        # Check for YAML frontmatter (between --- markers)
        pattern = r'^---\s*\n(.*?)\n---\s*\n'
        match = re.match(pattern, content, re.DOTALL)

        if not match:
            return {}

        if yaml is None:
            self.logger.debug("PyYAML not installed; skipping frontmatter parsing")
            return {}

        try:
            yaml_content = match.group(1)
            data = yaml.safe_load(yaml_content)
            return data if isinstance(data, dict) else {}
        except yaml.YAMLError as e:
            self.logger.warning(f"Failed to parse YAML frontmatter: {e}")
            return {}

    def _parse_sections(self, content: str) -> Dict[str, str]:
        """
        Parse markdown sections from content.

        Args:
            content: Markdown file content

        Returns:
            Dictionary mapping section headers to content
        """
        sections = {}

        # Remove frontmatter if present
        content = re.sub(r'^---\s*\n.*?\n---\s*\n', '', content, flags=re.DOTALL)

        # Split by headers (## or ###)
        header_pattern = r'^##\s+(.+)$'
        lines = content.split('\n')

        current_section = None
        current_content = []

        for line in lines:
            header_match = re.match(header_pattern, line)

            if header_match:
                # Save previous section
                if current_section:
                    sections[current_section] = '\n'.join(current_content).strip()

                # Start new section
                current_section = header_match.group(1).strip()
                current_content = []
            else:
                current_content.append(line)

        # Save last section
        if current_section:
            sections[current_section] = '\n'.join(current_content).strip()

        return sections

    def _extract_agent_info(self, sections: Dict[str, str]) -> Dict[str, Any]:
        """
        Extract agent information from parsed sections.

        Args:
            sections: Dictionary of markdown sections

        Returns:
            Dictionary containing extracted agent information
        """
        info = {}

        # Extract triggers
        if 'Triggers' in sections:
            info['triggers'] = self._parse_list_section(sections['Triggers'])

        # Extract behavioral mindset
        if 'Behavioral Mindset' in sections:
            info['behavioral_mindset'] = sections['Behavioral Mindset']

        # Extract focus areas
        if 'Focus Areas' in sections:
            info['focus_areas'] = self._parse_focus_areas(sections['Focus Areas'])

        # Extract key actions
        if 'Key Actions' in sections:
            info['key_actions'] = self._parse_numbered_list(sections['Key Actions'])

        # Extract outputs
        if 'Outputs' in sections:
            info['outputs'] = self._parse_list_section(sections['Outputs'])

        # Extract boundaries
        if 'Boundaries' in sections:
            info['boundaries'] = self._parse_boundaries(sections['Boundaries'])

        return info

    def _parse_list_section(self, content: str) -> List[str]:
        """
        Parse a section containing a list.

        Args:
            content: Section content

        Returns:
            List of items
        """
        items = []
        lines = content.split('\n')

        for line in lines:
            # Match lines starting with - or *
            match = re.match(r'^[-*]\s+(.+)$', line.strip())
            if match:
                items.append(match.group(1).strip())

        return items

    def _parse_numbered_list(self, content: str) -> List[str]:
        """
        Parse a numbered list section.

        Args:
            content: Section content

        Returns:
            List of items
        """
        items = []
        lines = content.split('\n')
        current_item = []

        for line in lines:
            # Match lines starting with number
            match = re.match(r'^\d+\.\s+(.+)$', line.strip())

            if match:
                # Save previous item
                if current_item:
                    items.append(' '.join(current_item))
                # Start new item
                current_item = [match.group(1).strip()]
            elif line.strip() and current_item:
                # Continuation of current item
                current_item.append(line.strip())

        # Save last item
        if current_item:
            items.append(' '.join(current_item))

        return items

    def _parse_focus_areas(self, content: str) -> Dict[str, str]:
        """
        Parse focus areas section.

        Args:
            content: Section content

        Returns:
            Dictionary of focus areas
        """
        areas = {}
        lines = content.split('\n')

        for line in lines:
            # Match lines with bold text followed by colon
            match = re.match(r'^[-*]\s+\*\*(.+?)\*\*:\s+(.+)$', line.strip())
            if match:
                key = match.group(1).strip()
                value = match.group(2).strip()
                areas[key] = value

        return areas

    def _parse_boundaries(self, content: str) -> Dict[str, List[str]]:
        """
        Parse boundaries section (Will/Will Not).

        Args:
            content: Section content

        Returns:
            Dictionary with 'will' and 'will_not' lists
        """
        boundaries = {'will': [], 'will_not': []}
        current_section = None

        lines = content.split('\n')

        for line in lines:
            # Check for Will: or Will Not: headers
            if line.strip().startswith('**Will:**'):
                current_section = 'will'
            elif line.strip().startswith('**Will Not:**'):
                current_section = 'will_not'
            elif current_section:
                # Parse list items under current section
                match = re.match(r'^[-*]\s+(.+)$', line.strip())
                if match:
                    boundaries[current_section].append(match.group(1).strip())

        return boundaries

    def validate_agent_config(self, config: Dict[str, Any]) -> bool:
        """
        Validate agent configuration.

        Args:
            config: Agent configuration dictionary

        Returns:
            True if configuration is valid
        """
        required_fields = ['name']
        recommended_fields = ['description', 'category', 'tools']

        # Check required fields
        for field in required_fields:
            if field not in config:
                self.logger.error(f"Missing required field: {field}")
                return False

        # Warn about recommended fields
        for field in recommended_fields:
            if field not in config:
                self.logger.warning(f"Missing recommended field: {field}")

        return True
