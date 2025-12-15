"""
Security Engineer Agent for SuperClaude Framework

This agent specializes in security analysis, vulnerability detection,
and secure coding practices.
"""

import re
from typing import Any, Dict, List

from ..base import BaseAgent
from ..heuristic_markdown import HeuristicMarkdownAgent


class SecurityAnalysisAgent(BaseAgent):
    """
    Agent specialized in security analysis and vulnerability detection.

    Provides security assessments, vulnerability scanning, secure coding
    recommendations, and compliance validation.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the security engineer.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if "name" not in config:
            config["name"] = "security-engineer"
        if "description" not in config:
            config["description"] = "Identify and mitigate security vulnerabilities"
        if "category" not in config:
            config["category"] = "security"

        super().__init__(config)

        # Security patterns and rules
        self.vulnerability_patterns = self._initialize_vulnerability_patterns()
        self.security_best_practices = self._initialize_best_practices()
        self.owasp_top_10 = self._initialize_owasp_top_10()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute security analysis.

        Args:
            context: Execution context

        Returns:
            Security assessment results
        """
        result = {
            "success": False,
            "output": "",
            "actions_taken": [],
            "errors": [],
            "vulnerabilities": [],
            "risk_level": "unknown",
            "recommendations": [],
        }

        try:
            # Initialize if needed
            if not self._initialized:
                if not self.initialize():
                    result["errors"].append("Failed to initialize agent")
                    return result

            task = context.get("task", "")
            files = context.get("files", [])
            code = context.get("code", "")
            scan_type = context.get("scan_type", "comprehensive")

            if not task and not files and not code:
                result["errors"].append("No content to analyze for security")
                return result

            self.logger.info(f"Starting security analysis: {task[:100]}...")

            # Phase 1: Vulnerability scanning
            vulnerabilities = self._scan_vulnerabilities(code, files, scan_type)
            result["vulnerabilities"] = vulnerabilities
            result["actions_taken"].append(
                f"Scanned for {len(self.vulnerability_patterns)} vulnerability types"
            )

            # Phase 2: OWASP Top 10 assessment
            owasp_issues = self._assess_owasp_risks(code, vulnerabilities)
            result["actions_taken"].append(
                f"Assessed {len(owasp_issues)} OWASP Top 10 risks"
            )

            # Phase 3: Best practices validation
            practice_violations = self._check_best_practices(code, files)
            result["actions_taken"].append(
                f"Validated {len(self.security_best_practices)} best practices"
            )

            # Phase 4: Risk assessment
            risk_level = self._calculate_risk_level(vulnerabilities, owasp_issues)
            result["risk_level"] = risk_level
            result["actions_taken"].append(f"Calculated risk level: {risk_level}")

            # Phase 5: Generate recommendations
            recommendations = self._generate_recommendations(
                vulnerabilities, owasp_issues, practice_violations
            )
            result["recommendations"] = recommendations

            # Phase 6: Create security report
            report = self._generate_security_report(
                task,
                vulnerabilities,
                owasp_issues,
                practice_violations,
                risk_level,
                recommendations,
            )
            result["output"] = report

            result["success"] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Security analysis failed: {e}")
            result["errors"].append(str(e))

        return result

    def validate(self, context: Dict[str, Any]) -> bool:
        """Basic validation: require some code, files, or explicit task."""
        if not context:
            return False
        task = context.get("task")
        files = context.get("files") or []
        code = context.get("code")
        return bool((task and task.strip()) or files or (code and code.strip()))


class SecurityEngineer(HeuristicMarkdownAgent):
    """Strategist-tier security engineer combining heuristics with static analysis."""

    STRATEGIST_TIER = True

    SECURITY_KEYWORDS = {
        "security",
        "vulnerability",
        "secure",
        "auth",
        "authentication",
        "authorization",
        "permission",
        "encrypt",
        "decrypt",
        "hash",
        "owasp",
        "pentest",
        "penetration",
        "exploit",
        "injection",
        "xss",
        "csrf",
        "sql injection",
        "security audit",
    }

    def __init__(self, config: Dict[str, Any]):
        defaults = {
            "name": "security-engineer",
            "description": "Identify and mitigate security vulnerabilities",
            "category": "security",
            "capability_tier": "strategist",
        }
        merged = {**defaults, **config}
        super().__init__(merged)

        analysis_config = dict(merged)
        try:
            self.analysis_agent = SecurityAnalysisAgent(analysis_config)
            self.analysis_agent.logger = self.logger
        except Exception as exc:
            self.logger.debug(f"SecurityAnalysisAgent unavailable: {exc}")
            self.analysis_agent = None

    def validate(self, context: Dict[str, Any]) -> bool:
        task = str(context.get("task", "")).lower()
        if any(keyword in task for keyword in self.SECURITY_KEYWORDS):
            return True
        return super().validate(context) or self.analysis_agent.validate(context)

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        result = super().execute(context)

        if not self.analysis_agent:
            return result

        audit = self.analysis_agent.execute(context)
        result["security_audit"] = audit

        if audit.get("success"):
            vulnerabilities = audit.get("vulnerabilities") or []
            recommendations = audit.get("recommendations") or []
            report = audit.get("output") or ""

            actions = self._ensure_list(result, "actions_taken")
            if vulnerabilities:
                actions.append(
                    f"Identified {len(vulnerabilities)} potential vulnerabilities"
                )

            if recommendations:
                follow_up = self._ensure_list(result, "follow_up_actions")
                for rec in recommendations[:5]:
                    if isinstance(rec, dict):
                        text = rec.get("recommendation") or rec.get("summary")
                    else:
                        text = str(rec)
                    if text:
                        follow_up.append(f"Security recommendation: {text}")

            if vulnerabilities and not result.get("status") == "executed":
                result.setdefault("warnings", []).append(
                    f"Security audit uncovered {len(vulnerabilities)} vulnerability candidates; apply fixes before rerun."
                )

            if report:
                result["security_report"] = report
                if result.get("output"):
                    result["output"] = (
                        f"{result['output']}\n\n## Security Audit\n{report}".strip()
                    )
                else:
                    result["output"] = report
        else:
            errors = audit.get("errors") or []
            if errors:
                warning_list = self._ensure_list(result, "warnings")
                for err in errors:
                    if err not in warning_list:
                        warning_list.append(err)

        return result

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains security-related tasks
        """
        task = context.get("task", "")

        # Check for security keywords
        security_keywords = [
            "security",
            "vulnerability",
            "secure",
            "auth",
            "authentication",
            "authorization",
            "permission",
            "encrypt",
            "decrypt",
            "hash",
            "owasp",
            "pentest",
            "penetration",
            "exploit",
            "injection",
            "xss",
            "csrf",
            "sql injection",
            "security audit",
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in security_keywords)

    def _initialize_vulnerability_patterns(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize vulnerability detection patterns.

        Returns:
            Dictionary of vulnerability patterns
        """
        return {
            "sql_injection": {
                "pattern": r"(SELECT|INSERT|UPDATE|DELETE).*\+.*(?:request|params|query)",
                "severity": "critical",
                "cwe": "CWE-89",
                "description": "SQL Injection vulnerability",
            },
            "xss": {
                "pattern": r"innerHTML\s*=|document\.write\(|\.html\([^)]",
                "severity": "high",
                "cwe": "CWE-79",
                "description": "Cross-Site Scripting (XSS) vulnerability",
            },
            "command_injection": {
                "pattern": r"(exec|eval|system|shell_exec|`)",
                "severity": "critical",
                "cwe": "CWE-78",
                "description": "Command Injection vulnerability",
            },
            "path_traversal": {
                "pattern": r"\.\./|\.\.\\",
                "severity": "high",
                "cwe": "CWE-22",
                "description": "Path Traversal vulnerability",
            },
            "hardcoded_secrets": {
                "pattern": r'(password|api_key|secret|token)\s*=\s*["\'][^"\']+["\']',
                "severity": "high",
                "cwe": "CWE-798",
                "description": "Hardcoded credentials",
            },
            "weak_crypto": {
                "pattern": r"(md5|sha1|DES|RC4)\s*\(",
                "severity": "medium",
                "cwe": "CWE-327",
                "description": "Weak cryptographic algorithm",
            },
            "insecure_random": {
                "pattern": r"Math\.random\(\)|rand\(\)",
                "severity": "medium",
                "cwe": "CWE-330",
                "description": "Insecure random number generation",
            },
            "unsafe_deserialization": {
                "pattern": r"(pickle\.loads|yaml\.load|eval\(|unserialize)",
                "severity": "critical",
                "cwe": "CWE-502",
                "description": "Unsafe deserialization",
            },
            "xxe": {
                "pattern": r"<!ENTITY|SYSTEM|PUBLIC|DOCTYPE",
                "severity": "high",
                "cwe": "CWE-611",
                "description": "XML External Entity (XXE) vulnerability",
            },
            "open_redirect": {
                "pattern": r"redirect\([^)]*(request|params|query)",
                "severity": "medium",
                "cwe": "CWE-601",
                "description": "Open redirect vulnerability",
            },
        }

    def _initialize_best_practices(self) -> Dict[str, str]:
        """
        Initialize security best practices.

        Returns:
            Dictionary of best practices
        """
        return {
            "input_validation": "Validate and sanitize all user input",
            "output_encoding": "Encode output based on context",
            "authentication": "Use strong authentication mechanisms",
            "authorization": "Implement proper access controls",
            "session_management": "Secure session handling",
            "error_handling": "Avoid exposing sensitive information in errors",
            "logging": "Log security events without sensitive data",
            "encryption": "Use strong encryption for sensitive data",
            "least_privilege": "Follow principle of least privilege",
            "secure_defaults": "Use secure defaults for all configurations",
        }

    def _initialize_owasp_top_10(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize OWASP Top 10 categories.

        Returns:
            Dictionary of OWASP Top 10 risks
        """
        return {
            "A01": {
                "name": "Broken Access Control",
                "checks": ["authorization", "privilege escalation", "CORS"],
            },
            "A02": {
                "name": "Cryptographic Failures",
                "checks": ["weak crypto", "plaintext storage", "insufficient entropy"],
            },
            "A03": {
                "name": "Injection",
                "checks": ["SQL injection", "command injection", "LDAP injection"],
            },
            "A04": {
                "name": "Insecure Design",
                "checks": [
                    "threat modeling",
                    "secure design patterns",
                    "risk assessment",
                ],
            },
            "A05": {
                "name": "Security Misconfiguration",
                "checks": ["default configs", "unnecessary features", "error messages"],
            },
            "A06": {
                "name": "Vulnerable Components",
                "checks": [
                    "outdated libraries",
                    "known vulnerabilities",
                    "unmaintained",
                ],
            },
            "A07": {
                "name": "Authentication Failures",
                "checks": ["weak passwords", "session fixation", "credential stuffing"],
            },
            "A08": {
                "name": "Data Integrity Failures",
                "checks": [
                    "deserialization",
                    "integrity verification",
                    "CI/CD security",
                ],
            },
            "A09": {
                "name": "Security Logging Failures",
                "checks": ["insufficient logging", "log injection", "monitoring"],
            },
            "A10": {
                "name": "Server-Side Request Forgery",
                "checks": ["SSRF", "URL validation", "network segmentation"],
            },
        }

    def _scan_vulnerabilities(
        self, code: str, files: List[str], scan_type: str
    ) -> List[Dict[str, Any]]:
        """
        Scan for security vulnerabilities.

        Args:
            code: Code to scan
            files: Files to scan
            scan_type: Type of scan (quick/comprehensive)

        Returns:
            List of detected vulnerabilities
        """
        vulnerabilities = []

        if not code and not files:
            return vulnerabilities

        # Scan code for vulnerability patterns
        for vuln_type, vuln_info in self.vulnerability_patterns.items():
            if scan_type == "quick" and vuln_info["severity"] not in [
                "critical",
                "high",
            ]:
                continue

            pattern = vuln_info["pattern"]
            if code and re.search(pattern, code, re.IGNORECASE):
                vulnerabilities.append(
                    {
                        "type": vuln_type,
                        "severity": vuln_info["severity"],
                        "cwe": vuln_info["cwe"],
                        "description": vuln_info["description"],
                        "location": "code snippet",
                        "remediation": self._get_remediation(vuln_type),
                    }
                )

        # Check for common security issues
        if code:
            # Check for HTTP instead of HTTPS
            if "http://" in code and "https://" not in code:
                vulnerabilities.append(
                    {
                        "type": "insecure_protocol",
                        "severity": "medium",
                        "cwe": "CWE-319",
                        "description": "Unencrypted communication protocol",
                        "location": "code snippet",
                        "remediation": "Use HTTPS instead of HTTP",
                    }
                )

            # Check for disabled security features
            if "verify=False" in code or "SSLError" in code:
                vulnerabilities.append(
                    {
                        "type": "disabled_security",
                        "severity": "high",
                        "cwe": "CWE-295",
                        "description": "SSL/TLS verification disabled",
                        "location": "code snippet",
                        "remediation": "Enable SSL/TLS certificate verification",
                    }
                )

        return vulnerabilities

    def _assess_owasp_risks(
        self, code: str, vulnerabilities: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Assess OWASP Top 10 risks.

        Args:
            code: Code to assess
            vulnerabilities: Already detected vulnerabilities

        Returns:
            List of OWASP risks
        """
        owasp_issues = []

        # Map vulnerabilities to OWASP categories
        vuln_types = {v["type"] for v in vulnerabilities}

        if "sql_injection" in vuln_types or "command_injection" in vuln_types:
            owasp_issues.append(
                {
                    "category": "A03",
                    "name": self.owasp_top_10["A03"]["name"],
                    "risk": "critical",
                    "finding": "Injection vulnerabilities detected",
                }
            )

        if "weak_crypto" in vuln_types:
            owasp_issues.append(
                {
                    "category": "A02",
                    "name": self.owasp_top_10["A02"]["name"],
                    "risk": "high",
                    "finding": "Weak cryptographic algorithms in use",
                }
            )

        if "hardcoded_secrets" in vuln_types:
            owasp_issues.append(
                {
                    "category": "A05",
                    "name": self.owasp_top_10["A05"]["name"],
                    "risk": "high",
                    "finding": "Hardcoded credentials found",
                }
            )

        if "unsafe_deserialization" in vuln_types:
            owasp_issues.append(
                {
                    "category": "A08",
                    "name": self.owasp_top_10["A08"]["name"],
                    "risk": "critical",
                    "finding": "Unsafe deserialization vulnerability",
                }
            )

        return owasp_issues

    def _check_best_practices(
        self, code: str, files: List[str]
    ) -> List[Dict[str, str]]:
        """
        Check security best practices.

        Args:
            code: Code to check
            files: Files to check

        Returns:
            List of practice violations
        """
        violations = []

        if not code:
            return violations

        # Check for missing input validation
        if "request." in code and not re.search(r"validate|sanitize|clean", code, re.I):
            violations.append(
                {
                    "practice": "input_validation",
                    "issue": "Missing input validation for user data",
                }
            )

        # Check for missing error handling
        if "try" not in code and ("open(" in code or "connect(" in code):
            violations.append(
                {
                    "practice": "error_handling",
                    "issue": "Missing error handling for risky operations",
                }
            )

        # Check for logging sensitive data
        if "log" in code.lower() and re.search(r"password|token|secret", code, re.I):
            violations.append(
                {
                    "practice": "logging",
                    "issue": "Potentially logging sensitive information",
                }
            )

        # Check for missing authentication
        if "api" in code.lower() and "auth" not in code.lower():
            violations.append(
                {
                    "practice": "authentication",
                    "issue": "API endpoint without authentication check",
                }
            )

        return violations

    def _calculate_risk_level(
        self, vulnerabilities: List[Dict[str, Any]], owasp_issues: List[Dict[str, Any]]
    ) -> str:
        """
        Calculate overall risk level.

        Args:
            vulnerabilities: Detected vulnerabilities
            owasp_issues: OWASP risk assessment

        Returns:
            Risk level (critical/high/medium/low)
        """
        # Count by severity
        critical_count = sum(1 for v in vulnerabilities if v["severity"] == "critical")
        critical_count += sum(1 for o in owasp_issues if o["risk"] == "critical")

        high_count = sum(1 for v in vulnerabilities if v["severity"] == "high")
        high_count += sum(1 for o in owasp_issues if o["risk"] == "high")

        medium_count = sum(1 for v in vulnerabilities if v["severity"] == "medium")

        # Determine overall risk
        if critical_count > 0:
            return "critical"
        elif high_count > 1:
            return "high"
        elif high_count == 1 or medium_count > 2:
            return "medium"
        elif medium_count > 0:
            return "low"
        else:
            return "minimal"

    def _get_remediation(self, vuln_type: str) -> str:
        """
        Get remediation advice for vulnerability type.

        Args:
            vuln_type: Type of vulnerability

        Returns:
            Remediation advice
        """
        remediations = {
            "sql_injection": "Use parameterized queries or prepared statements",
            "xss": "Encode output and validate input; use Content Security Policy",
            "command_injection": "Avoid system calls; use safe APIs instead",
            "path_traversal": "Validate and sanitize file paths; use whitelisting",
            "hardcoded_secrets": "Use environment variables or secure vaults",
            "weak_crypto": "Use strong algorithms (AES-256, SHA-256+)",
            "insecure_random": "Use cryptographically secure random generators",
            "unsafe_deserialization": "Avoid deserializing untrusted data",
            "xxe": "Disable XML external entity processing",
            "open_redirect": "Validate and whitelist redirect URLs",
        }

        return remediations.get(vuln_type, "Apply secure coding practices")

    def _generate_recommendations(
        self,
        vulnerabilities: List[Dict[str, Any]],
        owasp_issues: List[Dict[str, Any]],
        practice_violations: List[Dict[str, str]],
    ) -> List[str]:
        """
        Generate security recommendations.

        Args:
            vulnerabilities: Detected vulnerabilities
            owasp_issues: OWASP assessment
            practice_violations: Best practice violations

        Returns:
            List of recommendations
        """
        recommendations = []

        # Priority 1: Fix critical vulnerabilities
        critical_vulns = [v for v in vulnerabilities if v["severity"] == "critical"]
        if critical_vulns:
            recommendations.append(
                f"🔴 **URGENT**: Fix {len(critical_vulns)} critical vulnerabilities immediately"
            )
            for vuln in critical_vulns[:3]:  # Top 3
                recommendations.append(
                    f"   - {vuln['description']}: {vuln['remediation']}"
                )

        # Priority 2: Address high-risk issues
        high_vulns = [v for v in vulnerabilities if v["severity"] == "high"]
        if high_vulns:
            recommendations.append(
                f"⚠️ **HIGH PRIORITY**: Address {len(high_vulns)} high-severity issues"
            )

        # Priority 3: OWASP compliance
        if owasp_issues:
            recommendations.append(
                f"📋 **OWASP**: Mitigate {len(owasp_issues)} OWASP Top 10 risks"
            )

        # Priority 4: Best practices
        if practice_violations:
            recommendations.append(
                f"💡 **BEST PRACTICES**: Implement {len(practice_violations)} security practices"
            )

        # General recommendations
        recommendations.extend(
            [
                "🔒 Implement security testing in CI/CD pipeline",
                "📝 Conduct regular security audits",
                "🎓 Provide security training to development team",
                "🔄 Keep dependencies updated and patched",
            ]
        )

        return recommendations

    def _generate_security_report(
        self,
        task: str,
        vulnerabilities: List[Dict[str, Any]],
        owasp_issues: List[Dict[str, Any]],
        practice_violations: List[Dict[str, str]],
        risk_level: str,
        recommendations: List[str],
    ) -> str:
        """
        Generate comprehensive security report.

        Args:
            task: Original task
            vulnerabilities: Detected vulnerabilities
            owasp_issues: OWASP assessment
            practice_violations: Best practice violations
            risk_level: Overall risk level
            recommendations: Security recommendations

        Returns:
            Security report
        """
        lines = []

        # Header
        lines.append("# Security Assessment Report\n")
        lines.append(f"**Task**: {task}\n")

        # Executive Summary
        lines.append("\n## Executive Summary\n")
        risk_emoji = {
            "critical": "🔴",
            "high": "🟠",
            "medium": "🟡",
            "low": "🟢",
            "minimal": "✅",
        }.get(risk_level, "⚪")

        lines.append(f"**Overall Risk Level**: {risk_emoji} {risk_level.upper()}")
        lines.append(f"**Vulnerabilities Found**: {len(vulnerabilities)}")
        lines.append(f"**OWASP Risks**: {len(owasp_issues)}")
        lines.append(f"**Best Practice Violations**: {len(practice_violations)}")

        # Vulnerabilities Section
        if vulnerabilities:
            lines.append("\n## Vulnerabilities Detected\n")

            # Group by severity
            for severity in ["critical", "high", "medium", "low"]:
                sevs = [v for v in vulnerabilities if v["severity"] == severity]
                if sevs:
                    lines.append(f"\n### {severity.title()} Severity\n")
                    for vuln in sevs:
                        lines.append(f"- **{vuln['type']}** ({vuln['cwe']})")
                        lines.append(f"  - Description: {vuln['description']}")
                        lines.append(f"  - Remediation: {vuln['remediation']}")

        # OWASP Assessment
        if owasp_issues:
            lines.append("\n## OWASP Top 10 Assessment\n")
            for issue in owasp_issues:
                lines.append(f"- **{issue['category']}: {issue['name']}**")
                lines.append(f"  - Risk: {issue['risk']}")
                lines.append(f"  - Finding: {issue['finding']}")

        # Best Practices
        if practice_violations:
            lines.append("\n## Security Best Practice Violations\n")
            for violation in practice_violations:
                lines.append(f"- **{violation['practice'].replace('_', ' ').title()}**")
                lines.append(f"  - Issue: {violation['issue']}")

        # Recommendations
        lines.append("\n## Recommendations\n")
        for rec in recommendations:
            lines.append(rec)

        # Compliance Notes
        lines.append("\n## Compliance Notes\n")
        lines.append("- Review against applicable standards (PCI DSS, HIPAA, GDPR)")
        lines.append("- Ensure alignment with organizational security policies")
        lines.append("- Document security controls and risk acceptance")

        return "\n".join(lines)
