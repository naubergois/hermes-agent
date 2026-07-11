"""
Code Generator for Hermes IDE - Phase 3
Generates new components and files with proper structure and templates
"""

import json
import os
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
from enum import Enum


class ComponentType(Enum):
    """Supported component types"""
    REACT_FC = "react_fc"  # React Functional Component
    REACT_CLASS = "react_class"  # React Class Component
    DJANGO_MODEL = "django_model"  # Django Model
    DJANGO_VIEW = "django_view"  # Django View
    PYTHON_CLASS = "python_class"  # Python Class
    PYTHON_FUNCTION = "python_function"  # Python Function
    TYPESCRIPT_INTERFACE = "typescript_interface"  # TypeScript Interface
    TYPESCRIPT_CLASS = "typescript_class"  # TypeScript Class


class Framework(Enum):
    """Supported frameworks"""
    REACT = "react"
    DJANGO = "django"
    FLASK = "flask"
    FASTAPI = "fastapi"
    NODEJS = "nodejs"
    PYTHON = "python"
    TYPESCRIPT = "typescript"


@dataclass
class GeneratedFile:
    """Represents a generated file"""
    path: str
    content: str
    language: str
    component_type: str
    framework: str
    generated_at: str = None
    test_file: Optional[str] = None
    test_content: Optional[str] = None
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()


class CodeTemplates:
    """Code templates for different frameworks and components"""
    
    REACT_FC = '''import React, { useState } from 'react';

interface {ComponentName}Props {{
  {props}
}}

/**
 * {ComponentName} Component
 * 
 * @component
 * @example
 * return (
 *   <{ComponentName} />
 * )
 */
export const {ComponentName}: React.FC<{ComponentName}Props> = ({{
  {propNames}
}}) => {{
  const [state, setState] = useState<any>(null);

  return (
    <div className="{component-name}">
      {{/* TODO: Implement component */}}
    </div>
  );
}};

export default {ComponentName};
'''

    REACT_CLASS = '''import React from 'react';

interface {ComponentName}Props {{
  {props}
}}

interface {ComponentName}State {{
  loading: boolean;
  error: Error | null;
}}

/**
 * {ComponentName} Component
 */
export class {ComponentName} extends React.Component<{ComponentName}Props, {ComponentName}State> {{
  constructor(props: {ComponentName}Props) {{
    super(props);
    this.state = {{
      loading: false,
      error: null
    }};
  }}

  render() {{
    return (
      <div className="{component-name}">
        {{/* TODO: Implement component */}}
      </div>
    );
  }}
}}

export default {ComponentName};
'''

    DJANGO_MODEL = '''from django.db import models
from django.utils import timezone

class {ModelName}(models.Model):
    """
    {ModelName} Model
    
    Attributes:
        {attributes}
    """
    
    # Fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = '{ModelName}'
        verbose_name_plural = '{ModelNamePlural}'
    
    def __str__(self):
        return f"{{{ModelName} instance}}"
    
    def save(self, *args, **kwargs):
        """Custom save logic"""
        super().save(*args, **kwargs)
'''

    DJANGO_VIEW = '''from django.shortcuts import render
from django.views import View
from django.views.generic import ListView, DetailView
from django.contrib.auth.mixins import LoginRequiredMixin

class {ViewName}(LoginRequiredMixin, ListView):
    """
    {ViewName}
    
    Lists all {model_name} objects.
    """
    
    model = {Model}
    template_name = '{template_name}'
    context_object_name = '{object_name}'
    paginate_by = 20
    
    def get_queryset(self):
        """Filter queryset based on user permissions"""
        return super().get_queryset()
    
    def get_context_data(self, **kwargs):
        """Add custom context"""
        context = super().get_context_data(**kwargs)
        # TODO: Add custom context
        return context
'''

    PYTHON_CLASS = '''"""
{ModuleName} Module
"""


class {ClassName}:
    """
    {ClassName}
    
    {Description}
    
    Attributes:
        {attributes}
    """
    
    def __init__(self, {init_params}):
        """Initialize {ClassName}"""
        {init_body}
    
    def __repr__(self) -> str:
        return f"{{{ClassName}()}}"
    
    def __str__(self) -> str:
        return f"{{{ClassName}()}}"
    
    # TODO: Add methods


if __name__ == "__main__":
    # Example usage
    obj = {ClassName}()
    print(obj)
'''

    PYTHON_FUNCTION = '''"""
{ModuleName} Module
"""


def {function_name}({parameters}) -> {return_type}:
    """
    {function_name}
    
    {description}
    
    Args:
        {args_doc}
    
    Returns:
        {return_doc}
    
    Raises:
        {raises_doc}
    
    Example:
        >>> result = {function_name}({example_params})
        >>> print(result)
    """
    # TODO: Implement function
    pass


if __name__ == "__main__":
    # Example usage
    result = {function_name}({example_params})
    print(result)
'''

    TYPESCRIPT_INTERFACE = '''/**
 * {InterfaceName} Interface
 * 
 * {Description}
 */
export interface {InterfaceName} {{
{properties}
}}

/**
 * Type guard for {InterfaceName}
 */
export function is{InterfaceName}(obj: any): obj is {InterfaceName} {{
  return (
{guards}
  );
}}
'''


class CodeGenerator:
    """
    Code generator for creating new components and files with templates
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.templates = CodeTemplates()
    
    def generate_react_component(self, name: str, is_class: bool = False,
                                props: List[str] = None) -> GeneratedFile:
        """
        Generate React component
        
        Args:
            name: Component name (PascalCase)
            is_class: Generate class component instead of functional
            props: List of prop names
        
        Returns:
            GeneratedFile with component code
        """
        props = props or []
        prop_names = ", ".join(props)
        props_interface = "\n  ".join([f"{prop}: any;" for prop in props])
        
        template = self.templates.REACT_CLASS if is_class else self.templates.REACT_FC
        
        # Use replace instead of format to avoid JSX/TypeScript syntax conflicts
        content = template
        content = content.replace("{ComponentName}", name)
        content = content.replace("{componentName}", name)
        content = content.replace("{component-name}", self._to_kebab_case(name))
        content = content.replace("{props}", props_interface)
        content = content.replace("{propNames}", prop_names)
        
        path = f"src/components/{name}.tsx"
        
        return GeneratedFile(
            path=path,
            content=content,
            language="typescript",
            component_type="react_fc" if not is_class else "react_class",
            framework="react"
        )
    
    def generate_django_model(self, name: str, fields: Dict[str, str] = None) -> GeneratedFile:
        """
        Generate Django model
        
        Args:
            name: Model name (singular, PascalCase)
            fields: Dict of field_name: field_type
        
        Returns:
            GeneratedFile with model code
        """
        fields = fields or {}
        
        # Generate field definitions
        field_defs = "\n    ".join([
            f"{fname} = models.{self._django_field_type(ftype)}()"
            for fname, ftype in fields.items()
        ])
        
        content = self.templates.DJANGO_MODEL.format(
            ModelName=name,
            ModelNamePlural=f"{name}s",
            attributes=", ".join(fields.keys())
        )
        
        # Add field definitions before class Meta
        content = content.replace(
            "    # Fields",
            f"    # Fields\n    {field_defs}\n"
        )
        
        path = f"app/models/{self._to_snake_case(name)}.py"
        
        return GeneratedFile(
            path=path,
            content=content,
            language="python",
            component_type="django_model",
            framework="django"
        )
    
    def generate_python_class(self, name: str, methods: List[str] = None,
                             attributes: List[str] = None) -> GeneratedFile:
        """
        Generate Python class
        
        Args:
            name: Class name (PascalCase)
            methods: List of method names
            attributes: List of attribute names
        
        Returns:
            GeneratedFile with class code
        """
        methods = methods or []
        attributes = attributes or []
        
        init_params = ", ".join(attributes)
        init_body = "\n        ".join([
            f"self.{attr} = {attr}" for attr in attributes
        ]) if attributes else "pass"
        
        content = self.templates.PYTHON_CLASS.format(
            ModuleName=self._to_snake_case(name),
            ClassName=name,
            Description="TODO: Add description",
            attributes=", ".join(attributes),
            init_params=init_params,
            init_body=init_body
        )
        
        # Add method stubs
        methods_section = "\n    ".join([
            f"def {method}(self):\n        \"\"\"TODO: Implement {method}\"\"\"\n        pass"
            for method in methods
        ])
        
        if methods_section:
            content = content.replace("    # TODO: Add methods", f"    # TODO: Add methods\n    {methods_section}")
        
        path = f"src/{self._to_snake_case(name)}.py"
        
        return GeneratedFile(
            path=path,
            content=content,
            language="python",
            component_type="python_class",
            framework="python"
        )
    
    def generate_python_function(self, name: str, params: List[str] = None,
                                return_type: str = "Any") -> GeneratedFile:
        """
        Generate Python function
        
        Args:
            name: Function name (snake_case)
            params: List of parameter names
            return_type: Return type annotation
        
        Returns:
            GeneratedFile with function code
        """
        params = params or []
        
        parameters = ", ".join(params)
        args_doc = "\n        ".join([f"{p}: Description" for p in params])
        
        content = self.templates.PYTHON_FUNCTION.format(
            ModuleName=self._to_snake_case(name),
            function_name=name,
            parameters=parameters,
            return_type=return_type,
            description="TODO: Add description",
            args_doc=args_doc or "None",
            return_doc="TODO: Add return documentation",
            raises_doc="None",
            example_params=", ".join([f'"{p}"' for p in params]) if params else ""
        )
        
        path = f"src/{name}.py"
        
        return GeneratedFile(
            path=path,
            content=content,
            language="python",
            component_type="python_function",
            framework="python"
        )
    
    def generate_typescript_interface(self, name: str, 
                                     properties: Dict[str, str] = None) -> GeneratedFile:
        """
        Generate TypeScript interface
        
        Args:
            name: Interface name (PascalCase)
            properties: Dict of property_name: property_type
        
        Returns:
            GeneratedFile with interface code
        """
        properties = properties or {}
        
        # Generate property definitions
        props_def = "\n".join([
            f"  {pname}: {ptype};" for pname, ptype in properties.items()
        ])
        
        # Generate type guards
        guards = "\n    && ".join([
            f"typeof obj.{pname} === '{self._ts_type_to_js(ptype)}'"
            for pname, ptype in properties.items()
        ])
        
        content = self.templates.TYPESCRIPT_INTERFACE.format(
            InterfaceName=name,
            Description="TODO: Add description",
            properties=props_def,
            guards=guards
        )
        
        path = f"src/types/{self._to_snake_case(name)}.ts"
        
        return GeneratedFile(
            path=path,
            content=content,
            language="typescript",
            component_type="typescript_interface",
            framework="typescript"
        )
    
    def write_file(self, generated: GeneratedFile) -> bool:
        """
        Write generated file to disk
        
        Args:
            generated: GeneratedFile to write
        
        Returns:
            True if successful
        """
        try:
            file_path = self.project_root / generated.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_path.write_text(generated.content)
            return True
        except Exception as e:
            print(f"Error writing file: {e}")
            return False
    
    @staticmethod
    def _to_kebab_case(name: str) -> str:
        """Convert PascalCase to kebab-case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()
    
    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert PascalCase to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    @staticmethod
    def _django_field_type(ftype: str) -> str:
        """Map Python type to Django field type"""
        mapping = {
            "str": "CharField(max_length=255)",
            "int": "IntegerField()",
            "float": "FloatField()",
            "bool": "BooleanField()",
            "date": "DateField()",
            "datetime": "DateTimeField()",
            "text": "TextField()",
            "json": "JSONField()",
            "uuid": "UUIDField()",
        }
        return mapping.get(ftype, "CharField(max_length=255)")
    
    @staticmethod
    def _ts_type_to_js(ts_type: str) -> str:
        """Map TypeScript type to JavaScript typeof"""
        mapping = {
            "string": "string",
            "number": "number",
            "boolean": "boolean",
            "any": "object",
        }
        return mapping.get(ts_type, "object")
