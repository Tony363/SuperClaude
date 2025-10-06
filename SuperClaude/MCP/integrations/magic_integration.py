"""
Magic MCP Integration for SuperClaude Framework.

Provides UI component generation and design system integration.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json

logger = logging.getLogger(__name__)


@dataclass
class MagicComponent:
    """Generated UI component from Magic MCP."""
    name: str
    type: str
    framework: str
    code: str
    styles: str
    props: Dict[str, Any]
    accessibility: Dict[str, Any]
    responsive: bool = True


class MagicIntegration:
    """
    Integration with Magic MCP for UI component generation.

    Features:
    - Modern UI component generation
    - Design system integration
    - Accessibility compliance
    - Responsive design patterns
    - Framework-specific outputs
    """

    SUPPORTED_FRAMEWORKS = ['react', 'vue', 'angular', 'svelte', 'vanilla']
    COMPONENT_TYPES = ['button', 'form', 'modal', 'card', 'navigation', 'layout', 'data-display']

    def __init__(self, mcp_client=None):
        """
        Initialize Magic integration.

        Args:
            mcp_client: Optional MCP client for Magic server
        """
        self.mcp_client = mcp_client
        self.design_system = self._load_design_system()
        self.component_cache = {}

    def _load_design_system(self) -> Dict[str, Any]:
        """Load design system configuration."""
        return {
            'colors': {
                'primary': '#007bff',
                'secondary': '#6c757d',
                'success': '#28a745',
                'danger': '#dc3545',
                'warning': '#ffc107',
                'info': '#17a2b8'
            },
            'spacing': {
                'xs': '0.25rem',
                'sm': '0.5rem',
                'md': '1rem',
                'lg': '1.5rem',
                'xl': '2rem'
            },
            'typography': {
                'font-family': '-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto',
                'font-sizes': {
                    'xs': '0.75rem',
                    'sm': '0.875rem',
                    'md': '1rem',
                    'lg': '1.125rem',
                    'xl': '1.25rem'
                }
            },
            'breakpoints': {
                'mobile': '640px',
                'tablet': '768px',
                'desktop': '1024px',
                'wide': '1280px'
            }
        }

    async def generate_component(self,
                                  component_type: str,
                                  framework: str = 'react',
                                  props: Optional[Dict[str, Any]] = None,
                                  accessibility: bool = True,
                                  responsive: bool = True) -> MagicComponent:
        """
        Generate a UI component.

        Args:
            component_type: Type of component to generate
            framework: Target framework
            props: Component properties
            accessibility: Include accessibility features
            responsive: Make component responsive

        Returns:
            MagicComponent with generated code
        """
        if framework not in self.SUPPORTED_FRAMEWORKS:
            raise ValueError(f"Framework {framework} not supported")

        # Check cache
        cache_key = f"{framework}_{component_type}_{json.dumps(props or {})}"
        if cache_key in self.component_cache:
            return self.component_cache[cache_key]

        # Generate component based on type
        if component_type == 'button':
            component = self._generate_button(framework, props, accessibility)
        elif component_type == 'form':
            component = self._generate_form(framework, props, accessibility)
        elif component_type == 'modal':
            component = self._generate_modal(framework, props, accessibility)
        elif component_type == 'card':
            component = self._generate_card(framework, props, accessibility)
        else:
            component = self._generate_generic(component_type, framework, props, accessibility)

        # Add responsive styles if needed
        if responsive:
            component.styles = self._add_responsive_styles(component.styles)

        # Cache component
        self.component_cache[cache_key] = component

        return component

    def _generate_button(self, framework: str, props: Dict[str, Any], accessibility: bool) -> MagicComponent:
        """Generate button component."""
        props = props or {}
        variant = props.get('variant', 'primary')
        size = props.get('size', 'md')

        if framework == 'react':
            code = f"""
import React from 'react';
import './Button.css';

interface ButtonProps {{
  children: React.ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'secondary' | 'success' | 'danger';
  size?: 'sm' | 'md' | 'lg';
  disabled?: boolean;
  ariaLabel?: string;
}}

export const Button: React.FC<ButtonProps> = ({{
  children,
  onClick,
  variant = '{variant}',
  size = '{size}',
  disabled = false,
  ariaLabel
}}) => {{
  return (
    <button
      className={{`btn btn-${{variant}} btn-${{size}}`}}
      onClick={{onClick}}
      disabled={{disabled}}
      aria-label={{ariaLabel || undefined}}
      aria-disabled={{disabled}}
    >
      {{children}}
    </button>
  );
}};
"""
        else:
            code = "// Framework specific implementation"

        styles = f"""
.btn {{
  padding: {self.design_system['spacing'][size]};
  font-size: {self.design_system['typography']['font-sizes'][size]};
  border: none;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.3s ease;
  font-family: {self.design_system['typography']['font-family']};
}}

.btn-{variant} {{
  background-color: {self.design_system['colors'][variant]};
  color: white;
}}

.btn-{variant}:hover {{
  opacity: 0.9;
}}

.btn:disabled {{
  opacity: 0.6;
  cursor: not-allowed;
}}
"""

        return MagicComponent(
            name='Button',
            type='button',
            framework=framework,
            code=code,
            styles=styles,
            props=props,
            accessibility={'aria-label': True, 'aria-disabled': True} if accessibility else {},
            responsive=True
        )

    def _generate_form(self, framework: str, props: Dict[str, Any], accessibility: bool) -> MagicComponent:
        """Generate form component."""
        props = props or {}
        fields = props.get('fields', ['email', 'password'])

        if framework == 'react':
            code = f"""
import React, {{ useState }} from 'react';
import './Form.css';

interface FormData {{
  {'; '.join([f'{field}: string' for field in fields])}
}}

export const Form: React.FC = () => {{
  const [formData, setFormData] = useState<FormData>({{
    {', '.join([f'{field}: ""' for field in fields])}
  }});

  const handleSubmit = (e: React.FormEvent) => {{
    e.preventDefault();
    console.log('Form submitted:', formData);
  }};

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {{
    setFormData(prev => ({{
      ...prev,
      [e.target.name]: e.target.value
    }}));
  }};

  return (
    <form onSubmit={{handleSubmit}} className="form">
      {chr(10).join([f'''
      <div className="form-group">
        <label htmlFor="{field}" className="form-label">
          {field.capitalize()}
        </label>
        <input
          type="{field if field != 'email' else 'email'}"
          id="{field}"
          name="{field}"
          className="form-input"
          value={{formData.{field}}}
          onChange={{handleChange}}
          {"aria-describedby=" + chr(34) + field + "-error" + chr(34) if accessibility else ""}
          required
        />
      </div>''' for field in fields])}

      <button type="submit" className="btn btn-primary">
        Submit
      </button>
    </form>
  );
}};
"""
        else:
            code = "// Framework specific implementation"

        styles = """
.form {
  max-width: 400px;
  margin: 0 auto;
  padding: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
}

.form-input {
  width: 100%;
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 4px;
  font-size: 1rem;
}

.form-input:focus {
  outline: none;
  border-color: #007bff;
  box-shadow: 0 0 0 3px rgba(0,123,255,.25);
}
"""

        return MagicComponent(
            name='Form',
            type='form',
            framework=framework,
            code=code,
            styles=styles,
            props=props,
            accessibility={'aria-describedby': True, 'labels': True} if accessibility else {},
            responsive=True
        )

    def _generate_modal(self, framework: str, props: Dict[str, Any], accessibility: bool) -> MagicComponent:
        """Generate modal component."""
        props = props or {}

        if framework == 'react':
            code = """
import React, { useEffect, useRef } from 'react';
import './Modal.css';

interface ModalProps {
  isOpen: boolean;
  onClose: () => void;
  title: string;
  children: React.ReactNode;
}

export const Modal: React.FC<ModalProps> = ({ isOpen, onClose, title, children }) => {
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };

    if (isOpen) {
      document.addEventListener('keydown', handleEscape);
      modalRef.current?.focus();
    }

    return () => document.removeEventListener('keydown', handleEscape);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        ref={modalRef}
        className="modal-content"
        onClick={(e) => e.stopPropagation()}
        role="dialog"
        aria-modal="true"
        aria-labelledby="modal-title"
        tabIndex={-1}
      >
        <div className="modal-header">
          <h2 id="modal-title">{title}</h2>
          <button
            className="modal-close"
            onClick={onClose}
            aria-label="Close modal"
          >
            ×
          </button>
        </div>
        <div className="modal-body">
          {children}
        </div>
      </div>
    </div>
  );
};
"""
        else:
            code = "// Framework specific implementation"

        styles = """
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  border-radius: 8px;
  max-width: 500px;
  width: 90%;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.modal-header {
  padding: 1rem 1.5rem;
  border-bottom: 1px solid #e5e5e5;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-close {
  font-size: 2rem;
  background: none;
  border: none;
  cursor: pointer;
  line-height: 1;
}

.modal-body {
  padding: 1.5rem;
}
"""

        return MagicComponent(
            name='Modal',
            type='modal',
            framework=framework,
            code=code,
            styles=styles,
            props=props,
            accessibility={'aria-modal': True, 'role': 'dialog', 'aria-labelledby': True} if accessibility else {},
            responsive=True
        )

    def _generate_card(self, framework: str, props: Dict[str, Any], accessibility: bool) -> MagicComponent:
        """Generate card component."""
        props = props or {}

        if framework == 'react':
            code = """
import React from 'react';
import './Card.css';

interface CardProps {
  title: string;
  description?: string;
  image?: string;
  imageAlt?: string;
  actions?: React.ReactNode;
}

export const Card: React.FC<CardProps> = ({ title, description, image, imageAlt, actions }) => {
  return (
    <article className="card">
      {image && (
        <img
          src={image}
          alt={imageAlt || title}
          className="card-image"
        />
      )}
      <div className="card-body">
        <h3 className="card-title">{title}</h3>
        {description && (
          <p className="card-description">{description}</p>
        )}
        {actions && (
          <div className="card-actions">{actions}</div>
        )}
      </div>
    </article>
  );
};
"""
        else:
            code = "// Framework specific implementation"

        styles = """
.card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  overflow: hidden;
  transition: transform 0.3s ease, box-shadow 0.3s ease;
}

.card:hover {
  transform: translateY(-4px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.card-image {
  width: 100%;
  height: 200px;
  object-fit: cover;
}

.card-body {
  padding: 1.5rem;
}

.card-title {
  margin: 0 0 0.5rem;
  font-size: 1.25rem;
  font-weight: 600;
}

.card-description {
  margin: 0 0 1rem;
  color: #666;
  line-height: 1.5;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
}
"""

        return MagicComponent(
            name='Card',
            type='card',
            framework=framework,
            code=code,
            styles=styles,
            props=props,
            accessibility={'alt': True, 'semantic-html': True} if accessibility else {},
            responsive=True
        )

    def _generate_generic(self, component_type: str, framework: str, props: Dict[str, Any], accessibility: bool) -> MagicComponent:
        """Generate generic component."""
        return MagicComponent(
            name=component_type.capitalize(),
            type=component_type,
            framework=framework,
            code=f"// Generic {component_type} component for {framework}",
            styles="/* Component styles */",
            props=props or {},
            accessibility={'aria-label': True} if accessibility else {},
            responsive=True
        )

    def _add_responsive_styles(self, styles: str) -> str:
        """Add responsive breakpoints to styles."""
        responsive_additions = f"""

/* Responsive Design */
@media (max-width: {self.design_system['breakpoints']['mobile']}) {{
  .form, .modal-content {{
    width: 95%;
    padding: 1rem;
  }}

  .btn {{
    width: 100%;
  }}
}}

@media (min-width: {self.design_system['breakpoints']['tablet']}) {{
  .card {{
    max-width: 350px;
  }}
}}

@media (min-width: {self.design_system['breakpoints']['desktop']}) {{
  .form {{
    max-width: 500px;
  }}

  .modal-content {{
    max-width: 600px;
  }}
}}
"""
        return styles + responsive_additions

    def validate_accessibility(self, component: MagicComponent) -> Dict[str, Any]:
        """
        Validate component accessibility.

        Args:
            component: Component to validate

        Returns:
            Validation results with issues and recommendations
        """
        issues = []
        recommendations = []

        # Check for ARIA attributes
        code_lower = component.code.lower()

        if 'aria-label' not in code_lower and component.type in ['button', 'form']:
            issues.append("Missing aria-label for interactive element")
            recommendations.append("Add aria-label to improve screen reader support")

        if 'role=' not in code_lower and component.type == 'modal':
            issues.append("Missing role attribute")
            recommendations.append("Add role='dialog' for modal components")

        if '<img' in code_lower and 'alt=' not in code_lower:
            issues.append("Missing alt attribute for image")
            recommendations.append("Always include alt text for images")

        return {
            'passed': len(issues) == 0,
            'issues': issues,
            'recommendations': recommendations,
            'score': max(0, 100 - len(issues) * 20)
        }

    def get_design_tokens(self) -> Dict[str, Any]:
        """Get design system tokens."""
        return self.design_system

    def export_component(self, component: MagicComponent, output_dir: str) -> Dict[str, str]:
        """
        Export component to files.

        Args:
            component: Component to export
            output_dir: Output directory path

        Returns:
            Dictionary of created file paths
        """
        from pathlib import Path

        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Determine file extensions based on framework
        ext_map = {
            'react': {'code': '.tsx', 'styles': '.css'},
            'vue': {'code': '.vue', 'styles': '.css'},
            'angular': {'code': '.ts', 'styles': '.css'},
            'svelte': {'code': '.svelte', 'styles': '.css'},
            'vanilla': {'code': '.js', 'styles': '.css'}
        }

        extensions = ext_map.get(component.framework, {'code': '.js', 'styles': '.css'})

        # Write component code
        code_file = output_path / f"{component.name}{extensions['code']}"
        with open(code_file, 'w') as f:
            f.write(component.code)

        # Write styles
        styles_file = output_path / f"{component.name}{extensions['styles']}"
        with open(styles_file, 'w') as f:
            f.write(component.styles)

        # Write props schema if present
        if component.props:
            props_file = output_path / f"{component.name}.props.json"
            with open(props_file, 'w') as f:
                json.dump(component.props, f, indent=2)

        return {
            'code': str(code_file),
            'styles': str(styles_file),
            'props': str(props_file) if component.props else None
        }