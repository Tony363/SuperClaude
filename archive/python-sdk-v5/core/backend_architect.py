"""
Backend Architect Agent for SuperClaude Framework

This agent specializes in backend system design, API architecture,
database design, and server-side implementation patterns.
"""

import re
from typing import Any

from ..base import BaseAgent


class BackendArchitect(BaseAgent):
    """
    Agent specialized in backend architecture and development.

    Provides API design, database architecture, microservices patterns,
    and backend best practices for robust server-side systems.
    """

    def __init__(self, config: dict[str, Any]):
        """
        Initialize the backend architect.

        Args:
            config: Agent configuration
        """
        # Ensure proper configuration
        if "name" not in config:
            config["name"] = "backend-architect"
        if "description" not in config:
            config["description"] = "Design reliable backend systems"
        if "category" not in config:
            config["category"] = "backend"

        super().__init__(config)

        # Backend patterns and technologies
        self.api_patterns = self._initialize_api_patterns()
        self.database_patterns = self._initialize_database_patterns()
        self.backend_principles = self._initialize_backend_principles()

    def execute(self, context: dict[str, Any]) -> dict[str, Any]:
        """
        Execute backend architecture tasks.

        Args:
            context: Execution context

        Returns:
            Backend architecture analysis and recommendations
        """
        result = {
            "success": False,
            "output": "",
            "actions_taken": [],
            "errors": [],
            "api_design": {},
            "database_design": {},
            "service_architecture": {},
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
            requirements = context.get("requirements", {})

            if not task and not files and not code:
                result["errors"].append("No content for backend analysis")
                return result

            self.logger.info(f"Starting backend architecture analysis: {task[:100]}...")

            # Phase 1: Analyze API design
            api_design = self._analyze_api_design(task, files, code)
            result["api_design"] = api_design
            result["actions_taken"].append(
                f"Analyzed {len(api_design.get('endpoints', []))} API endpoints"
            )

            # Phase 2: Analyze database design
            db_design = self._analyze_database_design(task, files, code, requirements)
            result["database_design"] = db_design
            result["actions_taken"].append(
                f"Designed {len(db_design.get('entities', []))} database entities"
            )

            # Phase 3: Design service architecture
            service_arch = self._design_service_architecture(
                task, api_design, db_design, requirements
            )
            result["service_architecture"] = service_arch
            result["actions_taken"].append(
                f"Designed {len(service_arch.get('services', []))} services"
            )

            # Phase 4: Evaluate backend patterns
            patterns = self._evaluate_backend_patterns(
                api_design, db_design, service_arch
            )
            result["actions_taken"].append(
                f"Evaluated {len(patterns)} backend patterns"
            )

            # Phase 5: Generate recommendations
            recommendations = self._generate_recommendations(
                api_design, db_design, service_arch, patterns
            )
            result["recommendations"] = recommendations

            # Phase 6: Generate backend report
            report = self._generate_backend_report(
                task, api_design, db_design, service_arch, patterns, recommendations
            )
            result["output"] = report

            result["success"] = True
            self.log_execution(context, result)

        except Exception as e:
            self.logger.error(f"Backend architecture analysis failed: {e}")
            result["errors"].append(str(e))

        return result

    def validate(self, context: dict[str, Any]) -> bool:
        """
        Check if this agent can handle the context.

        Args:
            context: Validation context

        Returns:
            True if context contains backend tasks
        """
        task = context.get("task", "")

        # Check for backend keywords
        backend_keywords = [
            "backend",
            "api",
            "rest",
            "graphql",
            "database",
            "server",
            "microservice",
            "endpoint",
            "auth",
            "crud",
            "orm",
            "sql",
            "nosql",
            "cache",
            "queue",
            "message",
        ]

        task_lower = task.lower()
        return any(keyword in task_lower for keyword in backend_keywords)

    def _initialize_api_patterns(self) -> dict[str, dict[str, Any]]:
        """
        Initialize API design patterns.

        Returns:
            Dictionary of API patterns
        """
        return {
            "rest": {
                "name": "RESTful API",
                "description": "Resource-based HTTP API following REST principles",
                "pros": ["Simple", "Cacheable", "Stateless", "Wide support"],
                "cons": ["Over-fetching", "Multiple requests", "Versioning complexity"],
                "best_for": ["CRUD operations", "Resource-oriented systems"],
            },
            "graphql": {
                "name": "GraphQL API",
                "description": "Query language for flexible data fetching",
                "pros": ["Precise data fetching", "Single endpoint", "Type system"],
                "cons": ["Complexity", "Caching challenges", "N+1 queries"],
                "best_for": ["Complex data requirements", "Mobile apps"],
            },
            "grpc": {
                "name": "gRPC",
                "description": "High-performance RPC framework",
                "pros": ["Performance", "Streaming", "Type safety", "Code generation"],
                "cons": ["Browser support", "Human readability", "Debugging"],
                "best_for": ["Microservices", "Internal APIs", "Real-time systems"],
            },
            "websocket": {
                "name": "WebSocket API",
                "description": "Full-duplex communication protocol",
                "pros": ["Real-time", "Bidirectional", "Low latency"],
                "cons": ["Stateful", "Connection management", "Scaling complexity"],
                "best_for": ["Real-time apps", "Chat", "Live updates"],
            },
        }

    def _initialize_database_patterns(self) -> dict[str, dict[str, Any]]:
        """
        Initialize database patterns.

        Returns:
            Dictionary of database patterns
        """
        return {
            "relational": {
                "name": "Relational Database",
                "examples": ["PostgreSQL", "MySQL", "SQL Server"],
                "pros": ["ACID compliance", "Strong consistency", "Complex queries"],
                "cons": ["Scaling limitations", "Schema rigidity"],
                "best_for": ["Transactional systems", "Complex relationships"],
            },
            "document": {
                "name": "Document Database",
                "examples": ["MongoDB", "CouchDB", "DynamoDB"],
                "pros": ["Flexible schema", "Horizontal scaling", "Developer friendly"],
                "cons": ["Eventual consistency", "Limited transactions"],
                "best_for": ["Content management", "Catalogs", "User profiles"],
            },
            "key_value": {
                "name": "Key-Value Store",
                "examples": ["Redis", "Memcached", "DynamoDB"],
                "pros": ["Performance", "Simplicity", "Caching"],
                "cons": ["Limited queries", "No relationships"],
                "best_for": ["Caching", "Session storage", "Real-time data"],
            },
            "graph": {
                "name": "Graph Database",
                "examples": ["Neo4j", "Amazon Neptune", "ArangoDB"],
                "pros": ["Relationship queries", "Pattern matching", "Flexible"],
                "cons": ["Learning curve", "Limited tooling"],
                "best_for": ["Social networks", "Recommendations", "Fraud detection"],
            },
            "time_series": {
                "name": "Time Series Database",
                "examples": ["InfluxDB", "TimescaleDB", "Prometheus"],
                "pros": ["Time-based queries", "Compression", "Aggregations"],
                "cons": ["Specialized use case", "Limited flexibility"],
                "best_for": ["Metrics", "IoT data", "Monitoring"],
            },
        }

    def _initialize_backend_principles(self) -> list[dict[str, str]]:
        """
        Initialize backend development principles.

        Returns:
            List of backend principles
        """
        return [
            {
                "name": "Idempotency",
                "description": "Operations produce same result when called multiple times",
            },
            {
                "name": "Statelessness",
                "description": "No client context stored between requests",
            },
            {
                "name": "Fault Tolerance",
                "description": "System continues operating when failures occur",
            },
            {
                "name": "Data Integrity",
                "description": "Maintain data accuracy and consistency",
            },
            {
                "name": "Security by Design",
                "description": "Security built into every layer",
            },
            {
                "name": "Observability",
                "description": "Comprehensive logging, monitoring, and tracing",
            },
        ]

    def _analyze_api_design(
        self, task: str, files: list[str], code: str
    ) -> dict[str, Any]:
        """
        Analyze API design requirements.

        Args:
            task: Task description
            files: File paths
            code: Code content

        Returns:
            API design analysis
        """
        api_design = {
            "type": "rest",  # Default
            "endpoints": [],
            "authentication": "none",
            "versioning": "none",
            "rate_limiting": False,
            "documentation": False,
        }

        # Detect API type from task/code
        if "graphql" in task.lower() or "graphql" in code.lower():
            api_design["type"] = "graphql"
        elif "grpc" in task.lower() or "proto" in str(files):
            api_design["type"] = "grpc"
        elif "websocket" in task.lower() or "ws://" in code:
            api_design["type"] = "websocket"

        # Extract endpoints from code patterns
        if code:
            # REST endpoints
            rest_patterns = [
                r'@(Get|Post|Put|Delete|Patch)Mapping\(["\']([^"\']+)',
                r'app\.(get|post|put|delete|patch)\(["\']([^"\']+)',
                r'router\.(get|post|put|delete|patch)\(["\']([^"\']+)',
            ]

            for pattern in rest_patterns:
                matches = re.findall(pattern, code, re.IGNORECASE)
                for match in matches:
                    method = match[0].upper() if len(match) > 1 else "GET"
                    path = match[1] if len(match) > 1 else match[0]
                    api_design["endpoints"].append(
                        {"method": method, "path": path, "authenticated": False}
                    )

        # Detect authentication
        auth_keywords = ["jwt", "oauth", "bearer", "api_key", "auth"]
        if any(keyword in code.lower() for keyword in auth_keywords):
            if "jwt" in code.lower():
                api_design["authentication"] = "jwt"
            elif "oauth" in code.lower():
                api_design["authentication"] = "oauth2"
            else:
                api_design["authentication"] = "token"

        # Detect versioning
        if "/v1/" in code or "/v2/" in code or "api/v" in code:
            api_design["versioning"] = "url"
        elif "Accept-Version" in code or "API-Version" in code:
            api_design["versioning"] = "header"

        # Detect rate limiting
        if "rate" in code.lower() and "limit" in code.lower():
            api_design["rate_limiting"] = True

        # Detect documentation
        if "swagger" in code.lower() or "openapi" in code.lower():
            api_design["documentation"] = True

        return api_design

    def _analyze_database_design(
        self, task: str, files: list[str], code: str, requirements: dict[str, Any]
    ) -> dict[str, Any]:
        """
        Analyze database design requirements.

        Args:
            task: Task description
            files: File paths
            code: Code content
            requirements: Requirements

        Returns:
            Database design analysis
        """
        db_design = {
            "type": "relational",  # Default
            "entities": [],
            "relationships": [],
            "indexes": [],
            "caching_strategy": None,
            "sharding": False,
        }

        # Detect database type
        if "mongodb" in code.lower() or "mongoose" in code.lower():
            db_design["type"] = "document"
        elif "redis" in code.lower():
            db_design["type"] = "key_value"
            db_design["caching_strategy"] = "redis"
        elif "neo4j" in code.lower() or "graph" in task.lower():
            db_design["type"] = "graph"

        # Extract entities from code
        if code:
            # Look for model/entity definitions
            entity_patterns = [
                r"class\s+(\w+).*Model",
                r"@Entity.*class\s+(\w+)",
                r"Schema\(\{[^}]+\}\)",
                r"CREATE TABLE\s+(\w+)",
            ]

            for pattern in entity_patterns:
                matches = re.findall(pattern, code)
                for match in matches:
                    entity_name = match if isinstance(match, str) else match[0]
                    db_design["entities"].append(
                        {
                            "name": entity_name,
                            "type": "table"
                            if db_design["type"] == "relational"
                            else "collection",
                        }
                    )

        # Detect relationships
        if (
            "foreign key" in code.lower()
            or "@ManyToOne" in code
            or "@OneToMany" in code
        ):
            db_design["relationships"].append(
                {
                    "type": "one-to-many",
                    "description": "Foreign key relationships detected",
                }
            )

        # Detect indexes
        if "index" in code.lower() or "@Index" in code:
            db_design["indexes"].append(
                {"type": "standard", "description": "Database indexes detected"}
            )

        # Detect sharding
        if "shard" in code.lower() or "partition" in code.lower():
            db_design["sharding"] = True

        return db_design

    def _design_service_architecture(
        self,
        task: str,
        api_design: dict[str, Any],
        db_design: dict[str, Any],
        requirements: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Design service architecture.

        Args:
            task: Task description
            api_design: API design
            db_design: Database design
            requirements: Requirements

        Returns:
            Service architecture
        """
        service_arch = {
            "pattern": "monolithic",  # Default
            "services": [],
            "communication": "synchronous",
            "data_management": "shared",
            "deployment": "single",
        }

        # Determine architecture pattern
        num_endpoints = len(api_design.get("endpoints", []))
        len(db_design.get("entities", []))

        if "microservice" in task.lower() or num_endpoints > 20:
            service_arch["pattern"] = "microservices"
            service_arch["data_management"] = "database-per-service"
            service_arch["deployment"] = "containerized"

            # Design services based on entities
            for entity in db_design.get("entities", [])[:10]:  # Limit to 10
                service_arch["services"].append(
                    {
                        "name": f"{entity['name'].lower()}-service",
                        "responsibility": f"Manage {entity['name']} operations",
                        "database": "dedicated",
                        "api_style": api_design["type"],
                    }
                )
        else:
            # Monolithic architecture
            service_arch["services"] = [
                {
                    "name": "main-application",
                    "responsibility": "All business logic",
                    "database": "shared",
                    "api_style": api_design["type"],
                }
            ]

        # Determine communication pattern
        if api_design["type"] == "graphql":
            service_arch["communication"] = "graphql-gateway"
        elif "queue" in task.lower() or "async" in task.lower():
            service_arch["communication"] = "asynchronous"

        return service_arch

    def _evaluate_backend_patterns(
        self,
        api_design: dict[str, Any],
        db_design: dict[str, Any],
        service_arch: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Evaluate backend patterns.

        Args:
            api_design: API design
            db_design: Database design
            service_arch: Service architecture

        Returns:
            Evaluated patterns
        """
        patterns = []

        # API Pattern evaluation
        api_pattern = self.api_patterns.get(api_design["type"], {})
        if api_pattern:
            patterns.append(
                {
                    "category": "API",
                    "pattern": api_pattern["name"],
                    "suitability": "high"
                    if len(api_design["endpoints"]) > 5
                    else "medium",
                    "pros": api_pattern.get("pros", []),
                    "cons": api_pattern.get("cons", []),
                }
            )

        # Database pattern evaluation
        db_pattern = self.database_patterns.get(db_design["type"], {})
        if db_pattern:
            patterns.append(
                {
                    "category": "Database",
                    "pattern": db_pattern["name"],
                    "suitability": "high",
                    "pros": db_pattern.get("pros", []),
                    "cons": db_pattern.get("cons", []),
                }
            )

        # Service pattern evaluation
        if service_arch["pattern"] == "microservices":
            patterns.append(
                {
                    "category": "Architecture",
                    "pattern": "Microservices",
                    "suitability": "high"
                    if len(service_arch["services"]) > 3
                    else "medium",
                    "pros": ["Scalability", "Independence", "Technology diversity"],
                    "cons": ["Complexity", "Network overhead", "Data consistency"],
                }
            )

        # Additional patterns
        if api_design["authentication"] != "none":
            patterns.append(
                {
                    "category": "Security",
                    "pattern": f"{api_design['authentication'].upper()} Authentication",
                    "suitability": "high",
                    "pros": ["Secure", "Standard"],
                    "cons": ["Token management"],
                }
            )

        return patterns

    def _generate_recommendations(
        self,
        api_design: dict[str, Any],
        db_design: dict[str, Any],
        service_arch: dict[str, Any],
        patterns: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """
        Generate backend recommendations.

        Args:
            api_design: API design
            db_design: Database design
            service_arch: Service architecture
            patterns: Evaluated patterns

        Returns:
            Recommendations
        """
        recommendations = []

        # API recommendations
        if not api_design["documentation"]:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "API",
                    "recommendation": "Add API documentation (OpenAPI/Swagger)",
                    "benefit": "Improved developer experience and API discoverability",
                }
            )

        if not api_design["rate_limiting"]:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Security",
                    "recommendation": "Implement rate limiting",
                    "benefit": "Protect against abuse and ensure fair usage",
                }
            )

        if api_design["versioning"] == "none":
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "API",
                    "recommendation": "Implement API versioning strategy",
                    "benefit": "Backward compatibility and smooth upgrades",
                }
            )

        # Database recommendations
        if not db_design["caching_strategy"]:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Performance",
                    "recommendation": "Implement caching layer (Redis/Memcached)",
                    "benefit": "Reduced database load and improved response times",
                }
            )

        if len(db_design["indexes"]) == 0 and len(db_design["entities"]) > 3:
            recommendations.append(
                {
                    "priority": "high",
                    "category": "Database",
                    "recommendation": "Add database indexes for frequently queried fields",
                    "benefit": "Improved query performance",
                }
            )

        # Architecture recommendations
        if (
            service_arch["pattern"] == "microservices"
            and service_arch["communication"] == "synchronous"
        ):
            recommendations.append(
                {
                    "priority": "medium",
                    "category": "Architecture",
                    "recommendation": "Consider async messaging for inter-service communication",
                    "benefit": "Better resilience and decoupling",
                }
            )

        # Observability
        recommendations.append(
            {
                "priority": "high",
                "category": "Observability",
                "recommendation": "Implement comprehensive logging, monitoring, and tracing",
                "benefit": "Better debugging and system understanding",
            }
        )

        return recommendations

    def _generate_backend_report(
        self,
        task: str,
        api_design: dict[str, Any],
        db_design: dict[str, Any],
        service_arch: dict[str, Any],
        patterns: list[dict[str, Any]],
        recommendations: list[dict[str, Any]],
    ) -> str:
        """
        Generate comprehensive backend report.

        Args:
            task: Original task
            api_design: API design
            db_design: Database design
            service_arch: Service architecture
            patterns: Evaluated patterns
            recommendations: Recommendations

        Returns:
            Backend architecture report
        """
        lines = []

        # Header
        lines.append("# Backend Architecture Report\n")
        lines.append(f"**Task**: {task}\n")

        # API Design
        lines.append("\n## API Design\n")
        lines.append(f"**Type**: {api_design['type'].upper()}")
        lines.append(f"**Authentication**: {api_design['authentication'].title()}")
        lines.append(f"**Versioning**: {api_design['versioning'].title()}")
        lines.append(
            f"**Rate Limiting**: {'✅ Enabled' if api_design['rate_limiting'] else '❌ Not configured'}"
        )
        lines.append(
            f"**Documentation**: {'✅ Available' if api_design['documentation'] else '❌ Missing'}"
        )

        if api_design["endpoints"]:
            lines.append("\n### Endpoints")
            for endpoint in api_design["endpoints"][:10]:  # Limit to 10
                lines.append(f"- {endpoint['method']} {endpoint['path']}")

        # Database Design
        lines.append("\n## Database Design\n")
        lines.append(f"**Type**: {db_design['type'].replace('_', ' ').title()}")
        lines.append(f"**Entities**: {len(db_design['entities'])}")
        lines.append(f"**Caching**: {db_design['caching_strategy'] or 'None'}")
        lines.append(
            f"**Sharding**: {'✅ Enabled' if db_design['sharding'] else '❌ Not configured'}"
        )

        if db_design["entities"]:
            lines.append("\n### Entities")
            for entity in db_design["entities"][:10]:  # Limit to 10
                lines.append(f"- **{entity['name']}** ({entity['type']})")

        # Service Architecture
        lines.append("\n## Service Architecture\n")
        lines.append(f"**Pattern**: {service_arch['pattern'].title()}")
        lines.append(
            f"**Communication**: {service_arch['communication'].replace('_', ' ').title()}"
        )
        lines.append(
            f"**Data Management**: {service_arch['data_management'].replace('-', ' ').title()}"
        )
        lines.append(f"**Deployment**: {service_arch['deployment'].title()}")

        if service_arch["services"]:
            lines.append("\n### Services")
            for service in service_arch["services"][:10]:  # Limit to 10
                lines.append(f"- **{service['name']}**: {service['responsibility']}")

        # Patterns
        if patterns:
            lines.append("\n## Design Patterns\n")
            for pattern in patterns:
                lines.append(f"### {pattern['category']}: {pattern['pattern']}")
                lines.append(f"**Suitability**: {pattern['suitability'].title()}")
                if pattern.get("pros"):
                    lines.append(f"**Pros**: {', '.join(pattern['pros'][:3])}")
                if pattern.get("cons"):
                    lines.append(f"**Cons**: {', '.join(pattern['cons'][:3])}")

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

        # Backend Principles
        lines.append("\n## Applied Principles\n")
        for principle in self.backend_principles[:6]:
            lines.append(f"- **{principle['name']}**: {principle['description']}")

        # Implementation Checklist
        lines.append("\n## Implementation Checklist\n")
        lines.append("- [ ] Set up project structure and dependencies")
        lines.append("- [ ] Configure database connection and migrations")
        lines.append("- [ ] Implement authentication and authorization")
        lines.append("- [ ] Create API endpoints with validation")
        lines.append("- [ ] Add error handling and logging")
        lines.append("- [ ] Implement caching strategy")
        lines.append("- [ ] Set up monitoring and alerting")
        lines.append("- [ ] Write comprehensive tests")
        lines.append("- [ ] Document API with OpenAPI/Swagger")
        lines.append("- [ ] Configure CI/CD pipeline")

        return "\n".join(lines)
