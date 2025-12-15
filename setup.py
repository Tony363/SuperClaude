"""
SuperClaude Framework Setup Configuration.

Install with: pip install -e .
"""

from pathlib import Path
from typing import List

from setuptools import find_packages, setup

# Read README for long description
this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text(encoding="utf-8")


def collect_package_files() -> List[str]:
    """Collect non-Python data files that need to ship with the package."""
    base_dir = this_directory / "SuperClaude"
    patterns = [
        "Commands/*.md",
        "Agents/*.md",
        "Agents/*.json",
        "Agents/Extended/**/*.md",
        "Agents/extended/**/*.yaml",
        "Config/**/*.yaml",
        "Config/**/*.yml",
        "Core/*.yaml",
        "Core/*.md",
        "Modes/*.md",
    ]

    collected = set()
    for pattern in patterns:
        for path in base_dir.glob(pattern):
            if path.is_file():
                collected.add(str(path.relative_to(base_dir)))

    return sorted(collected)


# Read requirements
requirements = [
    "pyyaml>=6.0",
    "aiofiles>=23.0",
    "python-dotenv>=1.0",
    "rich>=13.0",  # For enhanced terminal output
    "click>=8.1",  # For CLI interface
    "watchdog>=3.0",  # For file monitoring
    "gitpython>=3.1",  # For git operations
    "jinja2>=3.1",  # For template rendering
    "jsonschema>=4.0",  # For JSON validation
    "requests>=2.31",  # For HTTP requests
    "aiohttp>=3.8",  # For async HTTP
    "numpy>=1.24",  # For numerical operations
    "pandas>=2.0",  # For data analysis
]

# Development requirements
dev_requirements = [
    "pytest>=7.0",
    "pytest-asyncio>=0.21.0",
    "black>=23.0",
    "flake8>=6.0",
    "mypy>=1.0",
    "isort>=5.12",
    "pre-commit>=3.0",
    "coverage>=7.0",
    "pytest-cov>=4.0",
    "sphinx>=6.0",
    "sphinx-rtd-theme>=1.2",
]

setup(
    name="superclaud-framework",
    version="6.0.0",
    author="SuperClaude Team",
    author_email="team@superclaud.ai",
    description="Advanced AI Framework for Claude Code with Multi-Model Support",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/superclaud/framework",
    project_urls={
        "Documentation": "https://docs.superclaud.ai",
        "Source": "https://github.com/superclaud/framework",
        "Issues": "https://github.com/superclaud/framework/issues",
    },
    packages=find_packages(exclude=["tests", "tests.*", "docs", "examples"]),
    package_data={
        "SuperClaude": collect_package_files(),
    },
    include_package_data=True,
    install_requires=requirements,
    extras_require={
        "dev": dev_requirements,
        "mcp": [
            "mcp-client>=0.1.0",  # When available
        ],
        "ai": [
            "openai>=1.0",
            "anthropic>=0.7",
            "google-generativeai>=0.3",
        ],
    },
    python_requires=">=3.9",
    entry_points={
        "console_scripts": [
            "superclaude=SuperClaude.__main__:main",
            "SuperClaude=SuperClaude.__main__:main",
            "sc=SuperClaude.__main__:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Application Frameworks",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Operating System :: OS Independent",
        "Environment :: Console",
        "Framework :: AsyncIO",
    ],
    keywords=[
        "ai",
        "claude",
        "gpt-5",
        "gemini",
        "framework",
        "multi-model",
        "agents",
        "mcp",
        "orchestration",
        "consensus",
        "quality",
        "automation",
    ],
    zip_safe=False,
)
