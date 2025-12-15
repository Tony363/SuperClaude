"""
DevOps Architect Agent for SuperClaude Framework

This agent specializes in CI/CD pipelines, infrastructure as code,
containerization, and deployment automation.
"""

from typing import Any, Dict, List

from ..base import BaseAgent


class DevOpsArchitect(BaseAgent):
    """
    Agent specialized in DevOps practices and infrastructure.

    Provides CI/CD design, container orchestration, monitoring strategies,
    and infrastructure automation for reliable deployments.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the DevOps architect.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if "name" not in config:
            config["name"] = "devops-architect"
        if "description" not in config:
            config["description"] = "Automate infrastructure and deployment"
        if "category" not in config:
            config["category"] = "devops"

        super().__init__(config)

        # DevOps patterns and tools
        self.ci_cd_tools = self._initialize_ci_cd_tools()
        self.container_platforms = self._initialize_container_platforms()
        self.monitoring_stack = self._initialize_monitoring_stack()
        self.deployment_strategies = self._initialize_deployment_strategies()

    def execute(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute DevOps architecture tasks.

        Args:
            context: Execution context

        Returns:
            DevOps architecture analysis and recommendations
        """
        result = {
            "success": False,
            "output": "",
            "actions_taken": [],
            "errors": [],
            "pipeline_design": {},
            "infrastructure": {},
            "deployment_strategy": {},
            "monitoring_plan": {},
            "security_measures": {},
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
            environment = context.get("environment", "production")

            if not task and not files and not code:
                result["errors"].append("No content for DevOps analysis")
                return result

            self.logger.info(f"Starting DevOps architecture analysis: {task[:100]}...")

            # Phase 1: Analyze CI/CD pipeline
            pipeline = self._design_ci_cd_pipeline(task, files, code)
            result["pipeline_design"] = pipeline
            result["actions_taken"].append(
                f"Designed {len(pipeline.get('stages', []))} pipeline stages"
            )

            # Phase 2: Design infrastructure
            infrastructure = self._design_infrastructure(task, files, environment)
            result["infrastructure"] = infrastructure
            result["actions_taken"].append("Designed infrastructure architecture")

            # Phase 3: Determine deployment strategy
            deployment = self._determine_deployment_strategy(
                task, infrastructure, environment
            )
            result["deployment_strategy"] = deployment
            result["actions_taken"].append(
                f"Selected {deployment['strategy']} deployment"
            )

            # Phase 4: Plan monitoring
            monitoring = self._plan_monitoring(infrastructure, deployment)
            result["monitoring_plan"] = monitoring
            result["actions_taken"].append("Created monitoring strategy")

            # Phase 5: Security measures
            security = self._assess_security_measures(
                pipeline, infrastructure, deployment
            )
            result["security_measures"] = security
            result["actions_taken"].append("Assessed security measures")

            # Phase 6: Generate recommendations
            recommendations = self._generate_recommendations(
                pipeline, infrastructure, deployment, monitoring, security
            )
            result["recommendations"] = recommendations

            # Phase 7: Generate DevOps report
            report = self._generate_devops_report(
                task,
                pipeline,
                infrastructure,
                deployment,
                monitoring,
                security,
                recommendations,
            )
            result["output"] = report

            result["success"] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"DevOps architecture analysis failed: {e}")
            result["errors"].append(str(e))

        return result

    def validate(self, context: Dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains DevOps tasks
        """
        task = context.get("task", "")

        # Check for DevOps keywords
        devops_keywords = [
            "devops",
            "ci/cd",
            "pipeline",
            "deploy",
            "docker",
            "kubernetes",
            "container",
            "infrastructure",
            "terraform",
            "ansible",
            "jenkins",
            "monitoring",
            "logging",
            "automation",
            "orchestration",
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in devops_keywords)

    def _initialize_ci_cd_tools(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize CI/CD tools.

        Returns:
            Dictionary of CI/CD tools
        """
        return {
            "github_actions": {
                "name": "GitHub Actions",
                "type": "cloud",
                "pros": ["GitHub integration", "Free tier", "Matrix builds"],
                "cons": ["Vendor lock-in", "Limited self-hosted"],
                "best_for": ["GitHub repos", "Open source", "Small teams"],
            },
            "jenkins": {
                "name": "Jenkins",
                "type": "self-hosted",
                "pros": ["Extensible", "Open source", "Mature"],
                "cons": ["Maintenance overhead", "Complex setup"],
                "best_for": ["Enterprise", "Complex pipelines", "On-premise"],
            },
            "gitlab_ci": {
                "name": "GitLab CI",
                "type": "hybrid",
                "pros": ["GitLab integration", "Auto DevOps", "Container registry"],
                "cons": ["Resource intensive", "Learning curve"],
                "best_for": ["GitLab users", "Full DevOps lifecycle"],
            },
            "circleci": {
                "name": "CircleCI",
                "type": "cloud",
                "pros": ["Fast builds", "Docker support", "Orbs ecosystem"],
                "cons": ["Cost at scale", "Limited free tier"],
                "best_for": ["Docker workflows", "Fast iteration"],
            },
        }

    def _initialize_container_platforms(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize container platforms.

        Returns:
            Dictionary of container platforms
        """
        return {
            "docker": {
                "name": "Docker",
                "type": "containerization",
                "use_cases": ["Local development", "Simple deployments"],
            },
            "kubernetes": {
                "name": "Kubernetes",
                "type": "orchestration",
                "use_cases": ["Production workloads", "Auto-scaling", "Multi-cloud"],
            },
            "docker_compose": {
                "name": "Docker Compose",
                "type": "multi-container",
                "use_cases": ["Development", "Small deployments"],
            },
            "ecs": {
                "name": "AWS ECS",
                "type": "managed",
                "use_cases": ["AWS deployments", "Serverless containers"],
            },
        }

    def _initialize_monitoring_stack(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize monitoring tools.

        Returns:
            Dictionary of monitoring tools
        """
        return {
            "metrics": {
                "prometheus": "Time-series metrics",
                "datadog": "Cloud monitoring",
                "cloudwatch": "AWS native",
            },
            "logging": {
                "elk": "Elasticsearch, Logstash, Kibana",
                "splunk": "Enterprise logging",
                "cloudwatch_logs": "AWS native",
            },
            "tracing": {
                "jaeger": "Distributed tracing",
                "zipkin": "Distributed tracing",
                "xray": "AWS native",
            },
            "alerting": {
                "pagerduty": "Incident management",
                "opsgenie": "Alert management",
                "sns": "AWS native",
            },
        }

    def _initialize_deployment_strategies(self) -> Dict[str, Dict[str, Any]]:
        """
        Initialize deployment strategies.

        Returns:
            Dictionary of deployment strategies
        """
        return {
            "blue_green": {
                "description": "Switch between two identical environments",
                "pros": ["Zero downtime", "Easy rollback"],
                "cons": ["Resource cost", "Database migrations"],
                "risk": "low",
            },
            "canary": {
                "description": "Gradual rollout to subset of users",
                "pros": ["Risk mitigation", "Performance validation"],
                "cons": ["Complex monitoring", "Slower rollout"],
                "risk": "low",
            },
            "rolling": {
                "description": "Update instances incrementally",
                "pros": ["Resource efficient", "Gradual update"],
                "cons": ["Mixed versions", "Rollback complexity"],
                "risk": "medium",
            },
            "recreate": {
                "description": "Stop old version, start new version",
                "pros": ["Simple", "Clean state"],
                "cons": ["Downtime", "No rollback"],
                "risk": "high",
            },
        }

    def _design_ci_cd_pipeline(
        self, task: str, files: List[str], code: str
    ) -> Dict[str, Any]:
        """
        Design CI/CD pipeline.

        Args:
            task: Task description
            files: File paths
            code: Code content

        Returns:
            Pipeline design
        """
        pipeline = {
            "tool": "github_actions",  # Default
            "stages": [],
            "triggers": [],
            "artifacts": [],
            "environments": [],
        }

        # Detect CI/CD tool from files
        for file_path in files:
            if ".github/workflows" in file_path:
                pipeline["tool"] = "github_actions"
            elif "Jenkinsfile" in file_path:
                pipeline["tool"] = "jenkins"
            elif ".gitlab-ci.yml" in file_path:
                pipeline["tool"] = "gitlab_ci"
            elif ".circleci" in file_path:
                pipeline["tool"] = "circleci"

        # Design pipeline stages
        pipeline["stages"] = [
            {"name": "checkout", "description": "Clone repository", "duration": "30s"},
            {
                "name": "dependencies",
                "description": "Install dependencies",
                "duration": "2m",
            },
            {"name": "lint", "description": "Code quality checks", "duration": "1m"},
            {"name": "test", "description": "Run test suite", "duration": "5m"},
            {"name": "build", "description": "Build application", "duration": "3m"},
            {
                "name": "security_scan",
                "description": "Security vulnerability scan",
                "duration": "2m",
            },
        ]

        # Add deployment stage if production
        if "production" in task.lower() or "deploy" in task.lower():
            pipeline["stages"].append(
                {
                    "name": "deploy",
                    "description": "Deploy to environment",
                    "duration": "5m",
                }
            )

        # Set triggers
        pipeline["triggers"] = ["push", "pull_request"]
        if "production" in task.lower():
            pipeline["triggers"].append("tag")

        # Set artifacts
        pipeline["artifacts"] = ["build_output", "test_reports", "coverage_reports"]

        # Set environments
        pipeline["environments"] = ["development", "staging"]
        if "production" in task.lower():
            pipeline["environments"].append("production")

        return pipeline

    def _design_infrastructure(
        self, task: str, files: List[str], environment: str
    ) -> Dict[str, Any]:
        """
        Design infrastructure architecture.

        Args:
            task: Task description
            files: File paths
            environment: Target environment

        Returns:
            Infrastructure design
        """
        infrastructure = {
            "platform": "cloud",
            "provider": "aws",  # Default
            "containerization": "docker",
            "orchestration": None,
            "iac_tool": "terraform",
            "configuration_mgmt": None,
            "networking": {},
            "storage": {},
            "compute": {},
        }

        # Detect cloud provider
        if "aws" in task.lower() or "amazon" in task.lower():
            infrastructure["provider"] = "aws"
        elif "azure" in task.lower():
            infrastructure["provider"] = "azure"
        elif "gcp" in task.lower() or "google cloud" in task.lower():
            infrastructure["provider"] = "gcp"

        # Determine orchestration
        if (
            "kubernetes" in task.lower()
            or "k8s" in task.lower()
            or environment == "production"
        ):
            infrastructure["orchestration"] = "kubernetes"

        # Design networking
        infrastructure["networking"] = {
            "vpc": True,
            "subnets": ["public", "private"],
            "load_balancer": "application",
            "cdn": environment == "production",
        }

        # Design storage
        infrastructure["storage"] = {
            "object_storage": "s3" if infrastructure["provider"] == "aws" else "blob",
            "database": "rds" if infrastructure["provider"] == "aws" else "managed",
            "cache": "redis",
            "file_system": "efs" if infrastructure["provider"] == "aws" else "nfs",
        }

        # Design compute
        infrastructure["compute"] = {
            "type": "containers" if infrastructure["orchestration"] else "vms",
            "auto_scaling": True,
            "instance_type": "t3.medium"
            if infrastructure["provider"] == "aws"
            else "standard",
        }

        return infrastructure

    def _determine_deployment_strategy(
        self, task: str, infrastructure: Dict[str, Any], environment: str
    ) -> Dict[str, Any]:
        """
        Determine deployment strategy.

        Args:
            task: Task description
            infrastructure: Infrastructure design
            environment: Target environment

        Returns:
            Deployment strategy
        """
        deployment = {
            "strategy": "rolling",  # Default
            "rollback_plan": "automatic",
            "health_checks": True,
            "smoke_tests": True,
            "approval_required": False,
        }

        # Select strategy based on environment and risk
        if environment == "production":
            if "zero downtime" in task.lower():
                deployment["strategy"] = "blue_green"
            elif "gradual" in task.lower() or "canary" in task.lower():
                deployment["strategy"] = "canary"
            else:
                deployment["strategy"] = "blue_green"  # Safe default for production
            deployment["approval_required"] = True
        elif environment == "staging":
            deployment["strategy"] = "rolling"
        else:
            deployment["strategy"] = "recreate"  # Simple for development

        # Get strategy details
        strategy_info = self.deployment_strategies.get(deployment["strategy"], {})
        deployment["risk_level"] = strategy_info.get("risk", "unknown")
        deployment["description"] = strategy_info.get("description", "")

        return deployment

    def _plan_monitoring(
        self, infrastructure: Dict[str, Any], deployment: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Plan monitoring strategy.

        Args:
            infrastructure: Infrastructure design
            deployment: Deployment strategy

        Returns:
            Monitoring plan
        """
        monitoring = {
            "metrics": {},
            "logging": {},
            "tracing": {},
            "alerting": {},
            "dashboards": [],
        }

        # Select metrics solution
        if infrastructure["provider"] == "aws":
            monitoring["metrics"] = {
                "solution": "cloudwatch",
                "custom_metrics": True,
                "retention": "30 days",
            }
        else:
            monitoring["metrics"] = {
                "solution": "prometheus",
                "custom_metrics": True,
                "retention": "15 days",
            }

        # Select logging solution
        monitoring["logging"] = {
            "solution": "elk"
            if infrastructure["orchestration"] == "kubernetes"
            else "cloudwatch",
            "centralized": True,
            "retention": "7 days",
        }

        # Select tracing solution
        if infrastructure["orchestration"] == "kubernetes":
            monitoring["tracing"] = {"solution": "jaeger", "sampling_rate": 0.1}

        # Configure alerting
        monitoring["alerting"] = {
            "channels": ["email", "slack"],
            "severity_levels": ["critical", "warning", "info"],
            "escalation": deployment["strategy"] == "blue_green",
        }

        # Define dashboards
        monitoring["dashboards"] = [
            "System Overview",
            "Application Performance",
            "Error Rates",
            "Deployment Status",
        ]

        return monitoring

    def _assess_security_measures(
        self,
        pipeline: Dict[str, Any],
        infrastructure: Dict[str, Any],
        deployment: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Assess security measures.

        Args:
            pipeline: CI/CD pipeline
            infrastructure: Infrastructure design
            deployment: Deployment strategy

        Returns:
            Security assessment
        """
        security = {
            "scanning": [],
            "secrets_management": None,
            "network_security": [],
            "compliance": [],
            "score": 50,  # Base score
        }

        # Pipeline security
        if "security_scan" in str(pipeline.get("stages", [])):
            security["scanning"].append("SAST (Static Analysis)")
            security["score"] += 10

        security["scanning"].append("Container scanning")
        security["scanning"].append("Dependency scanning")

        # Secrets management
        if infrastructure["provider"] == "aws":
            security["secrets_management"] = "AWS Secrets Manager"
        else:
            security["secrets_management"] = "HashiCorp Vault"
        security["score"] += 10

        # Network security
        if infrastructure.get("networking", {}).get("vpc"):
            security["network_security"].append("VPC isolation")
            security["score"] += 10

        security["network_security"].extend(
            ["Security groups", "Network ACLs", "TLS everywhere"]
        )

        # Compliance
        security["compliance"] = ["SOC2", "GDPR", "HIPAA-ready"]
        security["score"] += 20

        # Cap score at 100
        security["score"] = min(100, security["score"])

        return security

    def _generate_recommendations(
        self,
        pipeline: Dict[str, Any],
        infrastructure: Dict[str, Any],
        deployment: Dict[str, Any],
        monitoring: Dict[str, Any],
        security: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        """
        Generate DevOps recommendations.

        Args:
            pipeline: CI/CD pipeline
            infrastructure: Infrastructure design
            deployment: Deployment strategy
            monitoring: Monitoring plan
            security: Security measures

        Returns:
            List of recommendations
        """
        recommendations = []

        # Pipeline recommendations
        if "test" not in str(pipeline.get("stages", [])):
            recommendations.append(
                {
                    "priority": "critical",
                    "category": "Pipeline",
                    "recommendation": "Add automated testing stage",
                    "benefit": "Catch bugs before deployment",
                }
            )

        # Infrastructure recommendations
        if (
            not infrastructure.get("orchestration")
            and len(pipeline.get("environments", [])) > 2
        ):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Infrastructure",
                    "recommendation": "Implement container orchestration (Kubernetes)",
                    "benefit": "Better resource utilization and scaling",
                }
            )

        # Deployment recommendations
        if (
            deployment["strategy"] == "recreate"
            and deployment.get("risk_level") == "high"
        ):
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Deployment",
                    "recommendation": "Switch to blue-green or canary deployment",
                    "benefit": "Zero downtime deployments",
                }
            )

        # Monitoring recommendations
        if not monitoring.get("tracing"):
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "Observability",
                    "recommendation": "Implement distributed tracing",
                    "benefit": "Better debugging of microservices",
                }
            )

        # Security recommendations
        if security["score"] < 70:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Security",
                    "recommendation": "Implement comprehensive security scanning",
                    "benefit": "Identify vulnerabilities before production",
                }
            )

        # Cost optimization
        recommendations.append(
            {
                "priority": "medium",
                "category": "Cost",
                "recommendation": "Implement resource tagging and cost monitoring",
                "benefit": "Track and optimize cloud spending",
            }
        )

        return recommendations

    def _generate_devops_report(
        self,
        task: str,
        pipeline: Dict[str, Any],
        infrastructure: Dict[str, Any],
        deployment: Dict[str, Any],
        monitoring: Dict[str, Any],
        security: Dict[str, Any],
        recommendations: List[Dict[str, Any]],
    ) -> str:
        """
        Generate comprehensive DevOps report.

        Args:
            task: Original task
            pipeline: CI/CD pipeline
            infrastructure: Infrastructure design
            deployment: Deployment strategy
            monitoring: Monitoring plan
            security: Security measures
            recommendations: Recommendations

        Returns:
            DevOps architecture report
        """
        lines = []

        # Header
        lines.append("# DevOps Architecture Report\n")
        lines.append(f"**Task**: {task}\n")

        # CI/CD Pipeline
        lines.append("\n## CI/CD Pipeline\n")
        lines.append(f"**Tool**: {pipeline['tool'].replace('_', ' ').title()}")
        lines.append(f"**Stages**: {len(pipeline['stages'])}")
        lines.append(f"**Triggers**: {', '.join(pipeline['triggers'])}")
        lines.append(f"**Environments**: {', '.join(pipeline['environments'])}")

        if pipeline["stages"]:
            lines.append("\n### Pipeline Stages")
            total_time = 0
            for stage in pipeline["stages"]:
                lines.append(
                    f"- **{stage['name']}**: {stage['description']} ({stage['duration']})"
                )
                # Parse duration and sum
                if "m" in stage["duration"]:
                    total_time += int(stage["duration"].replace("m", "")) * 60
                elif "s" in stage["duration"]:
                    total_time += int(stage["duration"].replace("s", ""))

            lines.append(
                f"\n**Total Pipeline Duration**: ~{total_time // 60}m {total_time % 60}s"
            )

        # Infrastructure
        lines.append("\n## Infrastructure Architecture\n")
        lines.append(f"**Platform**: {infrastructure['platform'].title()}")
        lines.append(f"**Provider**: {infrastructure['provider'].upper()}")
        lines.append(
            f"**Containerization**: {infrastructure['containerization'].title()}"
        )
        if infrastructure["orchestration"]:
            lines.append(
                f"**Orchestration**: {infrastructure['orchestration'].title()}"
            )
        lines.append(f"**IaC Tool**: {infrastructure['iac_tool'].title()}")

        lines.append("\n### Networking")
        net = infrastructure.get("networking", {})
        lines.append(f"- VPC: {'✅' if net.get('vpc') else '❌'}")
        lines.append(f"- Load Balancer: {net.get('load_balancer', 'None')}")
        lines.append(f"- CDN: {'✅' if net.get('cdn') else '❌'}")

        # Deployment Strategy
        lines.append("\n## Deployment Strategy\n")
        lines.append(
            f"**Strategy**: {deployment['strategy'].replace('_', ' ').title()}"
        )
        lines.append(f"**Risk Level**: {deployment['risk_level'].title()}")
        lines.append(f"**Description**: {deployment['description']}")
        lines.append(
            f"**Health Checks**: {'✅' if deployment['health_checks'] else '❌'}"
        )
        lines.append(
            f"**Approval Required**: {'✅' if deployment['approval_required'] else '❌'}"
        )

        # Monitoring
        lines.append("\n## Monitoring & Observability\n")
        lines.append(f"**Metrics**: {monitoring['metrics'].get('solution', 'None')}")
        lines.append(f"**Logging**: {monitoring['logging'].get('solution', 'None')}")
        if monitoring.get("tracing"):
            lines.append(
                f"**Tracing**: {monitoring['tracing'].get('solution', 'None')}"
            )
        lines.append(
            f"**Alerting Channels**: {', '.join(monitoring['alerting'].get('channels', []))}"
        )

        # Security
        lines.append("\n## Security Measures\n")
        score_emoji = (
            "🟢"
            if security["score"] >= 80
            else "🟡"
            if security["score"] >= 60
            else "🔴"
        )
        lines.append(f"{score_emoji} **Security Score**: {security['score']}/100")
        lines.append(f"**Secrets Management**: {security['secrets_management']}")

        if security["scanning"]:
            lines.append("\n### Security Scanning")
            for scan in security["scanning"]:
                lines.append(f"- {scan}")

        # Recommendations
        if recommendations:
            lines.append("\n## Recommendations\n")
            priority_order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
            sorted_recs = sorted(
                recommendations, key=lambda x: priority_order.get(x["priority"], 4)
            )

            for rec in sorted_recs:
                priority_emoji = {
                    "critical": "🚨",
                    "high": "🔴",
                    "medium": "🟡",
                    "low": "🟢",
                }.get(rec["priority"], "⚪")
                lines.append(
                    f"{priority_emoji} **{rec['category']}**: {rec['recommendation']}"
                )
                lines.append(f"   - Benefit: {rec['benefit']}")

        # Implementation Roadmap
        lines.append("\n## Implementation Roadmap\n")
        lines.append("### Phase 1: Foundation (Week 1-2)")
        lines.append("- [ ] Set up version control and branching strategy")
        lines.append("- [ ] Configure CI/CD pipeline")
        lines.append("- [ ] Create development environment")

        lines.append("\n### Phase 2: Infrastructure (Week 3-4)")
        lines.append("- [ ] Provision cloud resources with IaC")
        lines.append("- [ ] Set up container registry")
        lines.append("- [ ] Configure networking and security")

        lines.append("\n### Phase 3: Deployment (Week 5-6)")
        lines.append("- [ ] Implement deployment strategy")
        lines.append("- [ ] Set up monitoring and alerting")
        lines.append("- [ ] Create runbooks and documentation")

        lines.append("\n### Phase 4: Optimization (Ongoing)")
        lines.append("- [ ] Performance tuning")
        lines.append("- [ ] Cost optimization")
        lines.append("- [ ] Security hardening")

        return "\n".join(lines)
