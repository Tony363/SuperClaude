"""
Command Parser for SuperClaude Framework.

Parses and validates /sc: command strings with parameters and flags.
"""

import logging
import re
import shlex
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


@dataclass
class ParsedCommand:
    """Parsed command with extracted components."""

    name: str
    raw_string: str
    arguments: List[str] = field(default_factory=list)
    flags: Dict[str, bool] = field(default_factory=dict)
    parameters: Dict[str, Any] = field(default_factory=dict)
    description: str = ""


class CommandParser:
    """
    Parser for /sc: commands.

    Features:
    - Command extraction from messages
    - Parameter and flag parsing
    - Validation against schemas
    - Error reporting with suggestions
    """

    # Command patterns
    COMMAND_PATTERN = re.compile(r"/sc:([A-Za-z0-9_-]+)(?:\s+(.*))?")
    FLAG_PATTERN = re.compile(r"--([A-Za-z0-9_-]+)(?:=([^\s]+))?")
    SHORT_FLAG_PATTERN = re.compile(r"-(\w)(?:\s+([^\s]+))?")

    # Parameter type validators
    TYPE_VALIDATORS = {
        "string": lambda x: isinstance(x, str),
        "int": lambda x: x.isdigit(),
        "float": lambda x: re.match(r"^-?\d+\.?\d*$", x) is not None,
        "bool": lambda x: x.lower() in ("true", "false", "1", "0", "yes", "no"),
        "flag": lambda x: True,  # Flags are always valid
        "path": lambda x: True,  # Path validation done elsewhere
        "choice": lambda x, choices: x in choices,
    }

    def __init__(self, registry=None):
        """
        Initialize command parser.

        Args:
            registry: Optional CommandRegistry for validation
        """
        self.registry = registry
        self.flag_aliases = {
            "h": "help",
            "v": "verbose",
            "q": "quiet",
            "s": "safe",
            "t": "test",
            "f": "force",
            "d": "debug",
        }

    def parse(self, command_str: str) -> ParsedCommand:
        """
        Parse a command string.

        Args:
            command_str: Full command string (e.g., "/sc:implement --safe feature")

        Returns:
            ParsedCommand object
        """
        command_str = command_str.strip()

        # Extract command name
        match = self.COMMAND_PATTERN.match(command_str)
        if not match:
            raise ValueError(f"Invalid command format: {command_str}")

        command_name = match.group(1)
        args_str = match.group(2) or ""

        # Parse arguments and flags
        arguments, flags, parameters = self._parse_arguments(args_str)

        # Create parsed command
        parsed = ParsedCommand(
            name=command_name,
            raw_string=command_str,
            arguments=arguments,
            flags=flags,
            parameters=parameters,
        )

        # Validate against registry if available
        if self.registry:
            self._validate_with_registry(parsed)

        return parsed

    def _parse_arguments(
        self, args_str: str
    ) -> Tuple[List[str], Dict[str, bool], Dict[str, Any]]:
        """
        Parse arguments, flags, and parameters from argument string.

        Args:
            args_str: Argument portion of command

        Returns:
            Tuple of (arguments, flags, parameters)
        """
        if not args_str:
            return [], {}, {}

        arguments = []
        flags = {}
        parameters = {}

        try:
            # Use shlex for proper quote handling
            tokens = shlex.split(args_str)
        except ValueError as e:
            # Fall back to simple split if quotes are unbalanced
            logger.warning(f"Quote parsing failed, using simple split: {e}")
            tokens = args_str.split()

        i = 0
        while i < len(tokens):
            token = tokens[i]

            # Long flag (--flag or --param=value)
            if token.startswith("--"):
                flag_match = self.FLAG_PATTERN.match(token)
                if flag_match:
                    flag_name = flag_match.group(1)
                    flag_value = flag_match.group(2)

                    if flag_value:
                        # Parameter with value
                        parameters[flag_name] = self._parse_value(flag_value)
                    else:
                        # Check if next token is a value
                        if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                            parameters[flag_name] = self._parse_value(tokens[i + 1])
                            i += 1
                        else:
                            # Boolean flag
                            flags[flag_name] = True
                            # Also expose underscore alias for hyphenated flags
                            if "-" in flag_name:
                                flags[flag_name.replace("-", "_")] = True

            # Short flag (-f or -f value)
            elif token.startswith("-") and len(token) == 2:
                flag_char = token[1]
                flag_name = self.flag_aliases.get(flag_char, flag_char)

                # Check if next token is a value
                if i + 1 < len(tokens) and not tokens[i + 1].startswith("-"):
                    parameters[flag_name] = self._parse_value(tokens[i + 1])
                    i += 1
                else:
                    flags[flag_name] = True

            # Regular argument
            else:
                arguments.append(token)

            i += 1

        return arguments, flags, parameters

    def _parse_value(self, value: str) -> Any:
        """
        Parse a parameter value to appropriate type.

        Args:
            value: String value to parse

        Returns:
            Parsed value (string, int, float, bool, or list)
        """
        # Boolean values
        if value.lower() in ("true", "yes", "1"):
            return True
        if value.lower() in ("false", "no", "0"):
            return False

        # Numeric values
        if value.isdigit():
            return int(value)
        if re.match(r"^-?\d+$", value):
            return int(value)
        if re.match(r"^-?\d+\.\d+$", value):
            return float(value)

        # List values (comma-separated)
        if "," in value:
            return [item.strip() for item in value.split(",")]

        # Default to string
        return value

    def _validate_with_registry(self, parsed: ParsedCommand) -> None:
        """
        Validate parsed command against registry schema.

        Args:
            parsed: ParsedCommand to validate

        Raises:
            ValueError if validation fails
        """
        if not self.registry:
            return

        command_meta = self.registry.get_command(parsed.name)
        if not command_meta:
            suggestions = self.registry.find_command(parsed.name)
            if suggestions:
                similar = ", ".join([name for name, _ in suggestions[:3]])
                raise ValueError(
                    f"Unknown command '{parsed.name}'. Did you mean: {similar}?"
                )
            raise ValueError(f"Unknown command '{parsed.name}'")

        # Add description from registry
        parsed.description = command_meta.description

        # Validate parameters if schema exists
        if command_meta.parameters:
            self._validate_parameters(parsed, command_meta.parameters)

    def _validate_parameters(
        self, parsed: ParsedCommand, schema: Dict[str, Any]
    ) -> None:
        """
        Validate parameters against schema.

        Args:
            parsed: ParsedCommand with parameters
            schema: Parameter schema from registry

        Raises:
            ValueError if validation fails
        """
        for param_name, param_def in schema.items():
            param_type = param_def.get("type", "string")
            required = param_def.get("required", False)

            # Check required parameters
            if required and param_name not in parsed.parameters:
                raise ValueError(f"Required parameter '--{param_name}' is missing")

            # Validate parameter type if present
            if param_name in parsed.parameters:
                value = parsed.parameters[param_name]
                if param_type in self.TYPE_VALIDATORS:
                    validator = self.TYPE_VALIDATORS[param_type]
                    if not validator(str(value)):
                        raise ValueError(
                            f"Parameter '--{param_name}' must be of type {param_type}"
                        )

    def extract_commands(self, text: str) -> List[str]:
        """
        Extract all /sc: commands from a text.

        Args:
            text: Text to search for commands

        Returns:
            List of command strings
        """
        # Find all /sc: commands in text
        pattern = r"/sc:\w+(?:[^\n/]*(?:/(?!sc:)[^\n/]*)*)?"
        matches = re.findall(pattern, text)
        return [match.strip() for match in matches]

    def is_command(self, text: str) -> bool:
        """
        Check if text contains a /sc: command.

        Args:
            text: Text to check

        Returns:
            True if text contains a command
        """
        return bool(self.COMMAND_PATTERN.search(text))

    def suggest_command(self, partial: str) -> List[Tuple[str, str]]:
        """
        Suggest commands based on partial input.

        Args:
            partial: Partial command string

        Returns:
            List of (command_name, description) tuples
        """
        if not self.registry:
            return []

        # Remove /sc: prefix if present
        partial = partial.replace("/sc:", "").strip()

        # Find matching commands
        matches = self.registry.find_command(partial)

        # Get descriptions
        suggestions = []
        for name, score in matches[:5]:  # Top 5 suggestions
            command = self.registry.get_command(name)
            if command:
                suggestions.append((name, command.description))

        return suggestions

    def format_command(self, name: str, **kwargs) -> str:
        """
        Format a command string with parameters.

        Args:
            name: Command name
            **kwargs: Parameters and flags

        Returns:
            Formatted command string
        """
        parts = [f"/sc:{name}"]

        # Add flags
        for key, value in kwargs.items():
            if isinstance(value, bool):
                if value:
                    parts.append(f"--{key}")
            elif isinstance(value, list):
                parts.append(f"--{key}={','.join(map(str, value))}")
            elif value is not None:
                parts.append(f"--{key}={value}")

        return " ".join(parts)
