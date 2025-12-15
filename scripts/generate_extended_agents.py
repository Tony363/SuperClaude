#!/usr/bin/env python3
"""
Generate all 127 extended agent YAML definitions for SuperClaude Framework.
"""

from pathlib import Path

import yaml

# Base directory for extended agents
BASE_DIR = Path(__file__).parent.parent / "SuperClaude" / "Agents" / "extended"

# Agent definitions organized by category
AGENT_DEFINITIONS = {
    "01-core-development": [
        {
            "id": "frontend-developer",
            "name": "Frontend Developer",
            "description": "Expert in modern frontend frameworks and UI/UX implementation",
            "domains": ["frontend", "ui", "spa", "pwa", "responsive-design"],
            "languages": ["javascript", "typescript", "html", "css"],
            "frameworks": ["react", "vue", "angular", "svelte", "nextjs"],
        },
        {
            "id": "full-stack-developer",
            "name": "Full Stack Developer",
            "description": "End-to-end application development across frontend and backend",
            "domains": ["fullstack", "frontend", "backend", "database", "deployment"],
            "languages": ["javascript", "python", "typescript", "sql"],
            "frameworks": ["nextjs", "django", "express", "react", "postgresql"],
        },
        {
            "id": "mobile-developer",
            "name": "Mobile Developer",
            "description": "Native and cross-platform mobile application development",
            "domains": ["mobile", "ios", "android", "cross-platform"],
            "languages": ["swift", "kotlin", "java", "dart", "javascript"],
            "frameworks": ["react-native", "flutter", "swiftui", "jetpack-compose"],
        },
        {
            "id": "microservices-architect",
            "name": "Microservices Architect",
            "description": "Design and implementation of microservices architectures",
            "domains": [
                "microservices",
                "distributed-systems",
                "service-mesh",
                "api-gateway",
            ],
            "languages": ["go", "java", "python", "rust"],
            "frameworks": ["kubernetes", "istio", "consul", "spring-cloud"],
        },
        {
            "id": "database-engineer",
            "name": "Database Engineer",
            "description": "Database design, optimization, and management",
            "domains": ["database", "sql", "nosql", "data-modeling", "optimization"],
            "languages": ["sql", "python", "java"],
            "frameworks": ["postgresql", "mysql", "mongodb", "redis", "elasticsearch"],
        },
        {
            "id": "real-time-systems",
            "name": "Real-Time Systems Developer",
            "description": "WebSockets, streaming, and real-time communication systems",
            "domains": ["realtime", "websockets", "streaming", "pubsub"],
            "languages": ["javascript", "go", "rust", "python"],
            "frameworks": ["socket.io", "signalr", "webrtc", "kafka", "rabbitmq"],
        },
        {
            "id": "cli-developer",
            "name": "CLI Developer",
            "description": "Command-line interface and developer tools",
            "domains": ["cli", "tools", "automation", "scripting"],
            "languages": ["python", "go", "rust", "bash"],
            "frameworks": ["click", "cobra", "clap", "argparse"],
        },
        {
            "id": "desktop-developer",
            "name": "Desktop Application Developer",
            "description": "Cross-platform desktop application development",
            "domains": ["desktop", "gui", "cross-platform"],
            "languages": ["python", "javascript", "csharp", "cpp"],
            "frameworks": ["electron", "tauri", "pyqt", "wpf", "gtk"],
        },
    ],
    "02-language-specialists": [
        {
            "id": "python-specialist",
            "name": "Python Specialist",
            "description": "Advanced Python patterns, async programming, and optimization",
            "domains": ["python", "async", "metaclasses", "decorators"],
            "languages": ["python"],
            "frameworks": ["asyncio", "django", "fastapi", "pandas", "numpy"],
        },
        {
            "id": "javascript-specialist",
            "name": "JavaScript Specialist",
            "description": "Modern JavaScript, ES6+, and Node.js expertise",
            "domains": ["javascript", "nodejs", "es6", "async-await"],
            "languages": ["javascript"],
            "frameworks": ["nodejs", "express", "webpack", "babel"],
        },
        {
            "id": "rust-specialist",
            "name": "Rust Specialist",
            "description": "Systems programming with Rust, memory safety, and concurrency",
            "domains": ["rust", "systems", "memory-safety", "concurrency"],
            "languages": ["rust"],
            "frameworks": ["tokio", "actix", "rocket", "serde"],
        },
        {
            "id": "go-specialist",
            "name": "Go Specialist",
            "description": "Concurrent programming, microservices, and cloud-native Go",
            "domains": ["golang", "concurrency", "microservices", "cloud-native"],
            "languages": ["go"],
            "frameworks": ["gin", "echo", "fiber", "grpc"],
        },
        {
            "id": "java-specialist",
            "name": "Java Specialist",
            "description": "Enterprise Java, Spring ecosystem, and JVM optimization",
            "domains": ["java", "jvm", "enterprise", "spring"],
            "languages": ["java", "kotlin"],
            "frameworks": ["spring-boot", "spring-cloud", "hibernate", "maven"],
        },
        {
            "id": "cpp-specialist",
            "name": "C++ Specialist",
            "description": "Modern C++, performance optimization, and systems programming",
            "domains": ["cpp", "systems", "performance", "memory"],
            "languages": ["cpp", "c"],
            "frameworks": ["boost", "qt", "cmake", "stl"],
        },
        {
            "id": "csharp-specialist",
            "name": "C# Specialist",
            "description": ".NET ecosystem, enterprise applications, and game development",
            "domains": ["csharp", "dotnet", "enterprise", "gaming"],
            "languages": ["csharp", "fsharp"],
            "frameworks": ["dotnet", "aspnet", "entity-framework", "unity"],
        },
        {
            "id": "ruby-specialist",
            "name": "Ruby Specialist",
            "description": "Ruby on Rails, metaprogramming, and DSL creation",
            "domains": ["ruby", "rails", "metaprogramming", "dsl"],
            "languages": ["ruby"],
            "frameworks": ["rails", "sinatra", "rspec", "sidekiq"],
        },
        {
            "id": "swift-specialist",
            "name": "Swift Specialist",
            "description": "iOS development, SwiftUI, and Apple ecosystem",
            "domains": ["swift", "ios", "macos", "swiftui"],
            "languages": ["swift", "objective-c"],
            "frameworks": ["swiftui", "uikit", "combine", "coredata"],
        },
        {
            "id": "kotlin-specialist",
            "name": "Kotlin Specialist",
            "description": "Android development, Kotlin Multiplatform, and coroutines",
            "domains": ["kotlin", "android", "multiplatform", "coroutines"],
            "languages": ["kotlin", "java"],
            "frameworks": ["android", "ktor", "compose", "coroutines"],
        },
        {
            "id": "php-specialist",
            "name": "PHP Specialist",
            "description": "Modern PHP, Laravel, and web application development",
            "domains": ["php", "web", "laravel", "symfony"],
            "languages": ["php"],
            "frameworks": ["laravel", "symfony", "wordpress", "composer"],
        },
        {
            "id": "scala-specialist",
            "name": "Scala Specialist",
            "description": "Functional programming, Akka, and big data with Scala",
            "domains": ["scala", "functional", "akka", "spark"],
            "languages": ["scala"],
            "frameworks": ["akka", "play", "spark", "cats"],
        },
        {
            "id": "elixir-specialist",
            "name": "Elixir Specialist",
            "description": "Concurrent, fault-tolerant applications with Elixir",
            "domains": ["elixir", "erlang", "otp", "phoenix"],
            "languages": ["elixir", "erlang"],
            "frameworks": ["phoenix", "nerves", "otp", "ecto"],
        },
        {
            "id": "react-specialist",
            "name": "React Specialist",
            "description": "React ecosystem, hooks, state management, and optimization",
            "domains": ["react", "frontend", "hooks", "state-management"],
            "languages": ["javascript", "typescript"],
            "frameworks": ["react", "nextjs", "gatsby", "redux", "mobx"],
        },
        {
            "id": "vue-specialist",
            "name": "Vue Specialist",
            "description": "Vue 3, Composition API, and Vue ecosystem",
            "domains": ["vue", "frontend", "composition-api", "vuex"],
            "languages": ["javascript", "typescript"],
            "frameworks": ["vue", "nuxt", "vuex", "pinia", "vite"],
        },
        {
            "id": "angular-specialist",
            "name": "Angular Specialist",
            "description": "Angular framework, RxJS, and enterprise frontend",
            "domains": ["angular", "frontend", "rxjs", "enterprise"],
            "languages": ["typescript", "javascript"],
            "frameworks": ["angular", "rxjs", "ngrx", "angular-material"],
        },
        {
            "id": "dart-specialist",
            "name": "Dart Specialist",
            "description": "Flutter development and Dart programming",
            "domains": ["dart", "flutter", "mobile", "cross-platform"],
            "languages": ["dart"],
            "frameworks": ["flutter", "dart-sdk", "provider", "bloc"],
        },
        {
            "id": "haskell-specialist",
            "name": "Haskell Specialist",
            "description": "Pure functional programming with Haskell",
            "domains": ["haskell", "functional", "category-theory"],
            "languages": ["haskell"],
            "frameworks": ["ghc", "stack", "cabal", "yesod"],
        },
        {
            "id": "clojure-specialist",
            "name": "Clojure Specialist",
            "description": "Functional programming on the JVM with Clojure",
            "domains": ["clojure", "functional", "lisp", "jvm"],
            "languages": ["clojure", "clojurescript"],
            "frameworks": ["ring", "compojure", "reagent", "re-frame"],
        },
        {
            "id": "lua-specialist",
            "name": "Lua Specialist",
            "description": "Embedded scripting and game development with Lua",
            "domains": ["lua", "scripting", "embedded", "gaming"],
            "languages": ["lua"],
            "frameworks": ["love2d", "openresty", "torch", "neovim"],
        },
        {
            "id": "perl-specialist",
            "name": "Perl Specialist",
            "description": "Text processing, system administration, and web development",
            "domains": ["perl", "regex", "scripting", "web"],
            "languages": ["perl"],
            "frameworks": ["mojolicious", "catalyst", "dancer", "cpan"],
        },
        {
            "id": "r-specialist",
            "name": "R Specialist",
            "description": "Statistical computing and data analysis with R",
            "domains": ["r", "statistics", "data-analysis", "visualization"],
            "languages": ["r"],
            "frameworks": ["tidyverse", "shiny", "ggplot2", "dplyr"],
        },
    ],
    "03-infrastructure": [
        {
            "id": "devops-engineer",
            "name": "DevOps Engineer",
            "description": "CI/CD pipelines, automation, and infrastructure management",
            "domains": ["devops", "cicd", "automation", "monitoring"],
            "languages": ["python", "bash", "yaml"],
            "frameworks": [
                "jenkins",
                "gitlab-ci",
                "github-actions",
                "terraform",
                "ansible",
            ],
        },
        {
            "id": "kubernetes-specialist",
            "name": "Kubernetes Specialist",
            "description": "Container orchestration, cluster management, and cloud-native",
            "domains": ["kubernetes", "k8s", "containers", "orchestration"],
            "languages": ["yaml", "go", "bash"],
            "frameworks": ["helm", "istio", "prometheus", "grafana"],
        },
        {
            "id": "cloud-architect",
            "name": "Cloud Architect",
            "description": "Multi-cloud architecture and cloud-native solutions",
            "domains": ["cloud", "aws", "azure", "gcp", "architecture"],
            "languages": ["python", "typescript", "yaml"],
            "frameworks": ["terraform", "cloudformation", "pulumi", "cdk"],
        },
        {
            "id": "sre-engineer",
            "name": "Site Reliability Engineer",
            "description": "Reliability, observability, and incident management",
            "domains": ["sre", "reliability", "observability", "monitoring"],
            "languages": ["python", "go", "bash"],
            "frameworks": ["prometheus", "grafana", "datadog", "pagerduty"],
        },
        {
            "id": "network-engineer",
            "name": "Network Engineer",
            "description": "Network architecture, security, and optimization",
            "domains": ["networking", "tcp-ip", "security", "load-balancing"],
            "languages": ["python", "bash"],
            "frameworks": ["nginx", "haproxy", "istio", "envoy"],
        },
        {
            "id": "terraform-specialist",
            "name": "Terraform Specialist",
            "description": "Infrastructure as Code with Terraform",
            "domains": ["iac", "terraform", "infrastructure", "automation"],
            "languages": ["hcl", "python"],
            "frameworks": ["terraform", "terragrunt", "atlantis"],
        },
        {
            "id": "docker-specialist",
            "name": "Docker Specialist",
            "description": "Containerization, Docker, and container security",
            "domains": ["docker", "containers", "containerization", "security"],
            "languages": ["dockerfile", "yaml", "bash"],
            "frameworks": ["docker", "docker-compose", "buildkit", "containerd"],
        },
        {
            "id": "ci-cd-specialist",
            "name": "CI/CD Specialist",
            "description": "Continuous integration and deployment pipelines",
            "domains": ["cicd", "automation", "testing", "deployment"],
            "languages": ["yaml", "groovy", "bash"],
            "frameworks": ["jenkins", "gitlab", "circleci", "argocd"],
        },
        {
            "id": "monitoring-specialist",
            "name": "Monitoring Specialist",
            "description": "System monitoring, alerting, and observability",
            "domains": ["monitoring", "observability", "metrics", "logging"],
            "languages": ["python", "promql"],
            "frameworks": ["prometheus", "grafana", "elk", "datadog"],
        },
        {
            "id": "security-operations",
            "name": "Security Operations Engineer",
            "description": "Infrastructure security and compliance",
            "domains": ["security", "compliance", "scanning", "hardening"],
            "languages": ["python", "bash"],
            "frameworks": ["vault", "trivy", "falco", "opensca"],
        },
        {
            "id": "platform-engineer",
            "name": "Platform Engineer",
            "description": "Internal developer platforms and tooling",
            "domains": ["platform", "tooling", "developer-experience"],
            "languages": ["go", "python", "typescript"],
            "frameworks": ["backstage", "crossplane", "kubevela"],
        },
        {
            "id": "edge-computing",
            "name": "Edge Computing Specialist",
            "description": "Edge infrastructure and distributed computing",
            "domains": ["edge", "iot", "distributed", "5g"],
            "languages": ["rust", "go", "cpp"],
            "frameworks": ["k3s", "openfaas", "kubeedge"],
        },
    ],
    "04-quality-security": [
        {
            "id": "qa-engineer",
            "name": "QA Engineer",
            "description": "Comprehensive testing strategies and quality assurance",
            "domains": ["testing", "qa", "automation", "quality"],
            "languages": ["python", "javascript", "java"],
            "frameworks": ["selenium", "pytest", "jest", "cypress"],
        },
        {
            "id": "security-analyst",
            "name": "Security Analyst",
            "description": "Security assessment, vulnerability analysis, and threat modeling",
            "domains": ["security", "vulnerability", "pentesting", "threat-modeling"],
            "languages": ["python", "bash", "ruby"],
            "frameworks": ["metasploit", "burp", "owasp", "nmap"],
        },
        {
            "id": "test-automation",
            "name": "Test Automation Engineer",
            "description": "Automated testing frameworks and continuous testing",
            "domains": ["automation", "testing", "e2e", "integration"],
            "languages": ["python", "javascript", "java"],
            "frameworks": ["selenium", "appium", "testcafe", "robot"],
        },
        {
            "id": "performance-tester",
            "name": "Performance Tester",
            "description": "Load testing, performance analysis, and optimization",
            "domains": ["performance", "load-testing", "stress-testing"],
            "languages": ["python", "java", "javascript"],
            "frameworks": ["jmeter", "gatling", "k6", "locust"],
        },
        {
            "id": "code-reviewer",
            "name": "Code Review Specialist",
            "description": "Code quality, best practices, and technical debt analysis",
            "domains": ["code-review", "quality", "best-practices"],
            "languages": ["multiple"],
            "frameworks": ["sonarqube", "eslint", "pylint", "rubocop"],
        },
        {
            "id": "compliance-engineer",
            "name": "Compliance Engineer",
            "description": "Regulatory compliance and security standards",
            "domains": ["compliance", "gdpr", "hipaa", "pci-dss"],
            "languages": ["python", "sql"],
            "frameworks": ["compliance-tools", "audit-frameworks"],
        },
        {
            "id": "penetration-tester",
            "name": "Penetration Tester",
            "description": "Ethical hacking and security testing",
            "domains": ["pentesting", "ethical-hacking", "vulnerability"],
            "languages": ["python", "bash", "powershell"],
            "frameworks": ["kali", "metasploit", "nmap", "wireshark"],
        },
        {
            "id": "devsecops-engineer",
            "name": "DevSecOps Engineer",
            "description": "Security integration in CI/CD pipelines",
            "domains": ["devsecops", "security", "automation"],
            "languages": ["python", "yaml", "bash"],
            "frameworks": ["snyk", "aqua", "twistlock", "sonarqube"],
        },
        {
            "id": "accessibility-specialist",
            "name": "Accessibility Specialist",
            "description": "Web accessibility and WCAG compliance",
            "domains": ["accessibility", "wcag", "a11y", "usability"],
            "languages": ["javascript", "html", "css"],
            "frameworks": ["axe", "wave", "lighthouse", "nvda"],
        },
        {
            "id": "chaos-engineer",
            "name": "Chaos Engineering Specialist",
            "description": "Resilience testing and failure injection",
            "domains": ["chaos", "resilience", "failure-testing"],
            "languages": ["python", "go"],
            "frameworks": ["chaos-monkey", "litmus", "gremlin"],
        },
        {
            "id": "api-tester",
            "name": "API Testing Specialist",
            "description": "API testing, contract testing, and validation",
            "domains": ["api-testing", "contract-testing", "validation"],
            "languages": ["javascript", "python"],
            "frameworks": ["postman", "newman", "pact", "rest-assured"],
        },
        {
            "id": "static-analysis",
            "name": "Static Analysis Engineer",
            "description": "Code analysis, linting, and quality metrics",
            "domains": ["static-analysis", "linting", "metrics"],
            "languages": ["multiple"],
            "frameworks": ["sonarqube", "codeclimate", "semgrep"],
        },
    ],
    "05-data-ai": [
        {
            "id": "data-engineer",
            "name": "Data Engineer",
            "description": "Data pipelines, ETL, and data infrastructure",
            "domains": ["data", "etl", "pipelines", "warehousing"],
            "languages": ["python", "sql", "scala"],
            "frameworks": ["spark", "airflow", "kafka", "dbt"],
        },
        {
            "id": "ml-engineer",
            "name": "Machine Learning Engineer",
            "description": "ML model development, training, and deployment",
            "domains": ["ml", "ai", "deep-learning", "mlops"],
            "languages": ["python", "r"],
            "frameworks": ["tensorflow", "pytorch", "scikit-learn", "mlflow"],
        },
        {
            "id": "data-scientist",
            "name": "Data Scientist",
            "description": "Statistical analysis, modeling, and insights",
            "domains": ["statistics", "analysis", "modeling", "visualization"],
            "languages": ["python", "r", "sql"],
            "frameworks": ["pandas", "numpy", "matplotlib", "seaborn"],
        },
        {
            "id": "ai-architect",
            "name": "AI Architect",
            "description": "AI system design and architecture",
            "domains": ["ai", "architecture", "llm", "nlp"],
            "languages": ["python"],
            "frameworks": ["transformers", "langchain", "openai", "huggingface"],
        },
        {
            "id": "llm-specialist",
            "name": "LLM Specialist",
            "description": "Large language models and prompt engineering",
            "domains": ["llm", "nlp", "prompt-engineering", "fine-tuning"],
            "languages": ["python"],
            "frameworks": ["openai", "anthropic", "langchain", "llamaindex"],
        },
        {
            "id": "computer-vision",
            "name": "Computer Vision Engineer",
            "description": "Image processing and computer vision",
            "domains": ["cv", "image-processing", "object-detection"],
            "languages": ["python", "cpp"],
            "frameworks": ["opencv", "yolo", "detectron", "mediapipe"],
        },
        {
            "id": "nlp-engineer",
            "name": "NLP Engineer",
            "description": "Natural language processing and text analysis",
            "domains": ["nlp", "text-analysis", "sentiment", "ner"],
            "languages": ["python"],
            "frameworks": ["spacy", "nltk", "transformers", "bert"],
        },
        {
            "id": "data-analyst",
            "name": "Data Analyst",
            "description": "Business intelligence and data visualization",
            "domains": ["analytics", "bi", "visualization", "reporting"],
            "languages": ["python", "sql", "r"],
            "frameworks": ["tableau", "powerbi", "looker", "metabase"],
        },
        {
            "id": "mlops-engineer",
            "name": "MLOps Engineer",
            "description": "ML operations and model deployment",
            "domains": ["mlops", "deployment", "monitoring", "versioning"],
            "languages": ["python", "yaml"],
            "frameworks": ["mlflow", "kubeflow", "seldon", "bentoml"],
        },
        {
            "id": "recommendation-systems",
            "name": "Recommendation Systems Engineer",
            "description": "Recommendation algorithms and personalization",
            "domains": [
                "recommendations",
                "collaborative-filtering",
                "personalization",
            ],
            "languages": ["python"],
            "frameworks": ["surprise", "lightfm", "tensorflow-recommenders"],
        },
        {
            "id": "time-series-analyst",
            "name": "Time Series Analyst",
            "description": "Time series analysis and forecasting",
            "domains": ["time-series", "forecasting", "anomaly-detection"],
            "languages": ["python", "r"],
            "frameworks": ["prophet", "statsmodels", "arima", "lstm"],
        },
        {
            "id": "big-data-engineer",
            "name": "Big Data Engineer",
            "description": "Large-scale data processing and distributed computing",
            "domains": ["big-data", "distributed", "streaming"],
            "languages": ["scala", "java", "python"],
            "frameworks": ["spark", "hadoop", "flink", "storm"],
        },
    ],
    "06-developer-experience": [
        {
            "id": "dx-engineer",
            "name": "Developer Experience Engineer",
            "description": "Developer tools, productivity, and workflow optimization",
            "domains": ["dx", "tooling", "productivity", "automation"],
            "languages": ["typescript", "python", "go"],
            "frameworks": ["vscode", "cli-tools", "sdk-design"],
        },
        {
            "id": "documentation-engineer",
            "name": "Documentation Engineer",
            "description": "Technical documentation and developer guides",
            "domains": ["documentation", "api-docs", "tutorials"],
            "languages": ["markdown", "python", "javascript"],
            "frameworks": ["docusaurus", "mkdocs", "sphinx", "swagger"],
        },
        {
            "id": "refactoring-specialist",
            "name": "Refactoring Specialist",
            "description": "Code refactoring and technical debt reduction",
            "domains": ["refactoring", "clean-code", "technical-debt"],
            "languages": ["multiple"],
            "frameworks": ["refactoring-tools", "ast-manipulation"],
        },
        {
            "id": "tooling-engineer",
            "name": "Tooling Engineer",
            "description": "Development tools and automation",
            "domains": ["tooling", "cli", "automation", "sdk"],
            "languages": ["go", "rust", "typescript"],
            "frameworks": ["cli-frameworks", "sdk-tools"],
        },
        {
            "id": "build-engineer",
            "name": "Build Engineer",
            "description": "Build systems and compilation optimization",
            "domains": ["build", "compilation", "optimization"],
            "languages": ["python", "bash", "makefile"],
            "frameworks": ["webpack", "rollup", "bazel", "gradle"],
        },
        {
            "id": "package-maintainer",
            "name": "Package Maintainer",
            "description": "Package management and distribution",
            "domains": ["packages", "dependencies", "versioning"],
            "languages": ["javascript", "python", "ruby"],
            "frameworks": ["npm", "pip", "gem", "cargo"],
        },
        {
            "id": "ide-plugin-developer",
            "name": "IDE Plugin Developer",
            "description": "IDE extensions and editor plugins",
            "domains": ["ide", "plugins", "extensions", "editor"],
            "languages": ["typescript", "java"],
            "frameworks": ["vscode-api", "intellij-platform"],
        },
        {
            "id": "api-designer",
            "name": "API Designer",
            "description": "API design, versioning, and documentation",
            "domains": ["api-design", "rest", "graphql", "grpc"],
            "languages": ["yaml", "json"],
            "frameworks": ["openapi", "asyncapi", "graphql-schema"],
        },
        {
            "id": "legacy-modernization",
            "name": "Legacy Modernization Specialist",
            "description": "Modernizing legacy systems and migrations",
            "domains": ["legacy", "migration", "modernization"],
            "languages": ["multiple"],
            "frameworks": ["strangler-fig", "event-sourcing"],
        },
        {
            "id": "code-generation",
            "name": "Code Generation Specialist",
            "description": "Code generators and scaffolding tools",
            "domains": ["codegen", "scaffolding", "templates"],
            "languages": ["typescript", "python"],
            "frameworks": ["yeoman", "plop", "hygen"],
        },
    ],
    "07-specialized-domains": [
        {
            "id": "blockchain-developer",
            "name": "Blockchain Developer",
            "description": "Smart contracts and blockchain applications",
            "domains": ["blockchain", "web3", "smart-contracts", "defi"],
            "languages": ["solidity", "rust", "javascript"],
            "frameworks": ["ethereum", "hardhat", "truffle", "web3js"],
        },
        {
            "id": "game-developer",
            "name": "Game Developer",
            "description": "Game development and engine programming",
            "domains": ["gaming", "graphics", "physics", "ai"],
            "languages": ["cpp", "csharp", "lua"],
            "frameworks": ["unity", "unreal", "godot", "phaser"],
        },
        {
            "id": "iot-engineer",
            "name": "IoT Engineer",
            "description": "Internet of Things and embedded systems",
            "domains": ["iot", "embedded", "sensors", "mqtt"],
            "languages": ["c", "cpp", "python", "rust"],
            "frameworks": ["arduino", "raspberry-pi", "mqtt", "lwm2m"],
        },
        {
            "id": "fintech-engineer",
            "name": "FinTech Engineer",
            "description": "Financial technology and trading systems",
            "domains": ["fintech", "trading", "payments", "banking"],
            "languages": ["java", "python", "cpp"],
            "frameworks": ["fix-protocol", "swift", "iso20022"],
        },
        {
            "id": "healthcare-engineer",
            "name": "Healthcare Engineer",
            "description": "Healthcare systems and medical software",
            "domains": ["healthcare", "hl7", "fhir", "medical"],
            "languages": ["java", "python", "csharp"],
            "frameworks": ["hl7", "fhir", "dicom"],
        },
        {
            "id": "robotics-engineer",
            "name": "Robotics Engineer",
            "description": "Robotics and autonomous systems",
            "domains": ["robotics", "ros", "autonomous", "control"],
            "languages": ["cpp", "python"],
            "frameworks": ["ros", "ros2", "gazebo", "moveit"],
        },
        {
            "id": "ar-vr-developer",
            "name": "AR/VR Developer",
            "description": "Augmented and virtual reality applications",
            "domains": ["ar", "vr", "xr", "3d"],
            "languages": ["csharp", "cpp", "javascript"],
            "frameworks": ["unity-xr", "arcore", "arkit", "webxr"],
        },
        {
            "id": "audio-engineer",
            "name": "Audio Processing Engineer",
            "description": "Audio processing and digital signal processing",
            "domains": ["audio", "dsp", "music", "speech"],
            "languages": ["cpp", "python"],
            "frameworks": ["juce", "portaudio", "web-audio-api"],
        },
        {
            "id": "gis-developer",
            "name": "GIS Developer",
            "description": "Geographic information systems and mapping",
            "domains": ["gis", "mapping", "geospatial", "location"],
            "languages": ["python", "javascript"],
            "frameworks": ["postgis", "leaflet", "mapbox", "qgis"],
        },
        {
            "id": "ecommerce-developer",
            "name": "E-commerce Developer",
            "description": "E-commerce platforms and payment systems",
            "domains": ["ecommerce", "payments", "shopping", "marketplace"],
            "languages": ["javascript", "php", "python"],
            "frameworks": ["shopify", "woocommerce", "stripe", "magento"],
        },
        {
            "id": "education-tech",
            "name": "EdTech Developer",
            "description": "Educational technology and learning platforms",
            "domains": ["edtech", "lms", "e-learning", "assessment"],
            "languages": ["javascript", "python"],
            "frameworks": ["moodle", "canvas", "scorm", "xapi"],
        },
    ],
    "08-business-product": [
        {
            "id": "product-manager",
            "name": "Technical Product Manager",
            "description": "Product strategy and technical requirements",
            "domains": ["product", "requirements", "roadmap", "metrics"],
            "languages": ["sql", "python"],
            "frameworks": ["jira", "analytics", "a-b-testing"],
        },
        {
            "id": "business-analyst",
            "name": "Business Analyst",
            "description": "Business requirements and process optimization",
            "domains": ["business", "requirements", "process", "analysis"],
            "languages": ["sql", "python"],
            "frameworks": ["bpmn", "uml", "excel", "tableau"],
        },
        {
            "id": "technical-writer",
            "name": "Technical Writer",
            "description": "Documentation, tutorials, and user guides",
            "domains": ["documentation", "writing", "tutorials"],
            "languages": ["markdown"],
            "frameworks": ["docs-as-code", "dita", "restructuredtext"],
        },
        {
            "id": "ux-researcher",
            "name": "UX Researcher",
            "description": "User research and usability testing",
            "domains": ["ux", "research", "usability", "analytics"],
            "languages": ["javascript", "python"],
            "frameworks": ["hotjar", "fullstory", "mixpanel"],
        },
        {
            "id": "growth-engineer",
            "name": "Growth Engineer",
            "description": "Growth hacking and conversion optimization",
            "domains": ["growth", "analytics", "ab-testing", "conversion"],
            "languages": ["javascript", "python"],
            "frameworks": ["segment", "amplitude", "optimizely"],
        },
        {
            "id": "sales-engineer",
            "name": "Sales Engineer",
            "description": "Technical sales support and demos",
            "domains": ["sales", "demos", "poc", "integration"],
            "languages": ["multiple"],
            "frameworks": ["demo-tools", "integration-platforms"],
        },
        {
            "id": "customer-success",
            "name": "Customer Success Engineer",
            "description": "Customer onboarding and technical support",
            "domains": ["support", "onboarding", "troubleshooting"],
            "languages": ["multiple"],
            "frameworks": ["zendesk", "intercom", "freshdesk"],
        },
        {
            "id": "solutions-architect",
            "name": "Solutions Architect",
            "description": "Enterprise solutions and integrations",
            "domains": ["enterprise", "integration", "architecture"],
            "languages": ["multiple"],
            "frameworks": ["enterprise-patterns", "integration-patterns"],
        },
        {
            "id": "developer-advocate",
            "name": "Developer Advocate",
            "description": "Developer relations and community",
            "domains": ["devrel", "community", "evangelism"],
            "languages": ["multiple"],
            "frameworks": ["community-tools", "content-creation"],
        },
        {
            "id": "data-privacy-officer",
            "name": "Data Privacy Officer",
            "description": "Data privacy and compliance",
            "domains": ["privacy", "gdpr", "compliance", "data-protection"],
            "languages": ["sql", "python"],
            "frameworks": ["privacy-tools", "compliance-frameworks"],
        },
    ],
    "09-meta-orchestration": [
        {
            "id": "multi-agent-coordinator",
            "name": "Multi-Agent Coordinator",
            "description": "Orchestrating multiple agents for complex tasks",
            "domains": ["orchestration", "coordination", "delegation"],
            "languages": ["python"],
            "frameworks": ["agent-frameworks", "workflow-engines"],
        },
        {
            "id": "task-decomposer",
            "name": "Task Decomposer",
            "description": "Breaking down complex tasks into subtasks",
            "domains": ["task-analysis", "decomposition", "planning"],
            "languages": ["python"],
            "frameworks": ["task-frameworks", "planning-tools"],
        },
        {
            "id": "workflow-orchestrator",
            "name": "Workflow Orchestrator",
            "description": "Managing complex workflows and pipelines",
            "domains": ["workflow", "orchestration", "automation"],
            "languages": ["python", "yaml"],
            "frameworks": ["airflow", "prefect", "temporal"],
        },
        {
            "id": "decision-maker",
            "name": "Decision Making Agent",
            "description": "Strategic decision support and analysis",
            "domains": ["decision", "strategy", "analysis"],
            "languages": ["python"],
            "frameworks": ["decision-trees", "optimization"],
        },
        {
            "id": "consensus-builder",
            "name": "Consensus Builder",
            "description": "Building consensus from multiple perspectives",
            "domains": ["consensus", "voting", "aggregation"],
            "languages": ["python"],
            "frameworks": ["voting-systems", "consensus-algorithms"],
        },
        {
            "id": "quality-controller",
            "name": "Quality Controller",
            "description": "Quality assurance and validation",
            "domains": ["quality", "validation", "verification"],
            "languages": ["python"],
            "frameworks": ["quality-frameworks", "validation-tools"],
        },
        {
            "id": "resource-optimizer",
            "name": "Resource Optimizer",
            "description": "Optimizing resource allocation and usage",
            "domains": ["optimization", "resources", "allocation"],
            "languages": ["python"],
            "frameworks": ["optimization-libraries", "schedulers"],
        },
        {
            "id": "meta-learner",
            "name": "Meta Learning Agent",
            "description": "Learning from agent interactions and outcomes",
            "domains": ["meta-learning", "adaptation", "improvement"],
            "languages": ["python"],
            "frameworks": ["ml-frameworks", "reinforcement-learning"],
        },
    ],
    "10-research-analysis": [
        {
            "id": "market-researcher",
            "name": "Market Research Analyst",
            "description": "Market analysis and competitive intelligence",
            "domains": ["market", "research", "competitive", "trends"],
            "languages": ["python", "r"],
            "frameworks": ["analytics-tools", "scraping-tools"],
        },
        {
            "id": "technology-scout",
            "name": "Technology Scout",
            "description": "Emerging technology identification and evaluation",
            "domains": ["technology", "innovation", "trends", "evaluation"],
            "languages": ["python"],
            "frameworks": ["research-tools", "trend-analysis"],
        },
        {
            "id": "patent-analyst",
            "name": "Patent Analyst",
            "description": "Patent research and intellectual property",
            "domains": ["patents", "ip", "research", "analysis"],
            "languages": ["python"],
            "frameworks": ["patent-databases", "nlp-tools"],
        },
        {
            "id": "competitive-analyst",
            "name": "Competitive Intelligence Analyst",
            "description": "Competitor analysis and strategic insights",
            "domains": ["competitive", "intelligence", "strategy"],
            "languages": ["python", "sql"],
            "frameworks": ["bi-tools", "data-mining"],
        },
        {
            "id": "trend-forecaster",
            "name": "Trend Forecasting Specialist",
            "description": "Technology and market trend forecasting",
            "domains": ["forecasting", "trends", "prediction"],
            "languages": ["python", "r"],
            "frameworks": ["forecasting-models", "time-series"],
        },
        {
            "id": "research-synthesizer",
            "name": "Research Synthesizer",
            "description": "Synthesizing research from multiple sources",
            "domains": ["research", "synthesis", "analysis", "summary"],
            "languages": ["python"],
            "frameworks": ["nlp", "text-mining", "knowledge-graphs"],
        },
    ],
}


def create_agent_yaml(category: str, agent_data: dict) -> dict:
    """Create a complete YAML structure for an agent."""

    # Base structure
    yaml_data = {
        "id": agent_data["id"],
        "name": agent_data["name"],
        "category": category.split("-", 1)[1].replace("-", "_"),
        "description": agent_data["description"],
        "priority": "medium",
    }

    # Capabilities
    yaml_data["capabilities"] = {
        "domains": agent_data.get("domains", []),
        "languages": agent_data.get("languages", []),
        "frameworks": agent_data.get("frameworks", []),
        "patterns": agent_data.get("patterns", []),
    }

    # Keywords - generate from name, id, and domains
    keywords = [agent_data["id"].replace("-", " ")]
    keywords.extend(agent_data["name"].lower().split())
    keywords.extend(agent_data.get("domains", []))
    keywords.extend(agent_data.get("languages", []))
    yaml_data["keywords"] = list(set(keywords))

    # File patterns - generate from languages and frameworks
    file_patterns = []
    for lang in agent_data.get("languages", []):
        if lang == "python":
            file_patterns.append("*.py")
        elif lang == "javascript":
            file_patterns.extend(["*.js", "*.jsx"])
        elif lang == "typescript":
            file_patterns.extend(["*.ts", "*.tsx"])
        elif lang == "go":
            file_patterns.append("*.go")
        elif lang == "rust":
            file_patterns.append("*.rs")
        elif lang == "java":
            file_patterns.append("*.java")
        elif lang == "cpp":
            file_patterns.extend(["*.cpp", "*.hpp", "*.cc", "*.h"])
        elif lang == "csharp":
            file_patterns.append("*.cs")
    yaml_data["file_patterns"] = file_patterns

    # Imports - frameworks
    yaml_data["imports"] = agent_data.get("frameworks", [])

    # Execution configuration
    yaml_data["execution"] = {
        "type": "specialized",
        "focus": agent_data.get("domains", ["general"])[0],
        "validation": True,
        "testing": True,
    }

    return yaml_data


def main():
    """Generate all extended agent YAML files."""

    total_agents = 0

    for category, agents in AGENT_DEFINITIONS.items():
        category_dir = BASE_DIR / category
        category_dir.mkdir(parents=True, exist_ok=True)

        for agent_data in agents:
            yaml_content = create_agent_yaml(category, agent_data)

            # Write YAML file
            yaml_path = category_dir / f"{agent_data['id']}.yaml"
            with open(yaml_path, "w") as f:
                yaml.dump(yaml_content, f, default_flow_style=False, sort_keys=False)

            total_agents += 1
            print(f"Created: {yaml_path}")

    print(f"\n✅ Successfully generated {total_agents} extended agent definitions!")
    print(f"📁 Location: {BASE_DIR}")

    # Summary by category
    print("\n📊 Agents by category:")
    for category, agents in AGENT_DEFINITIONS.items():
        print(f"  {category}: {len(agents)} agents")


if __name__ == "__main__":
    main()
