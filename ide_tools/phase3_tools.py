"""
Phase 3 Agent Tools for Hermes IDE
Exposes code generation, test generation, code review, and CI/CD as agent tools
"""

import json
from pathlib import Path
from typing import Optional, List
from tools.registry import registry
from ide.code_generator import CodeGenerator, CodeTemplates
from ide.test_generator import TestGenerator, MockGenerator
from ide.code_reviewer import CodeReviewer, ReviewReport
from ide.ci_cd_integration import CICDOrchestrator, WorkflowRun


# ============================================================================
# Code Generation Tools
# ============================================================================

def _generate_component(component_type: str, framework: str, component_name: str,
                       props: Optional[List[str]] = None,
                       task_id: str = None, **kwargs) -> str:
    """
    Generate a new component/file
    
    Args:
        component_type: "component", "page", "model", "utility"
        framework: "react", "django", "python", "typescript"
        component_name: Component name
        props: List of prop names (for components)
        task_id: Task ID
    
    Returns:
        JSON with generated code and metadata
    """
    try:
        generator = CodeGenerator()
        
        if component_type == "component":
            result = generator.generate_component(framework, component_name, props or [])
        elif component_type == "page":
            result = generator.generate_page(framework, component_name)
        elif component_type == "model":
            result = generator.generate_model(framework, component_name)
        elif component_type == "utility":
            result = generator.generate_utility(framework, component_name)
        else:
            return json.dumps({
                "success": False,
                "error": f"Unknown component type: {component_type}"
            })
        
        return json.dumps({
            "success": True,
            "path": result.path,
            "framework": result.framework,
            "component_type": result.component_type,
            "size": len(result.content),
            "content_preview": result.content[:500]
        })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


registry.register(
    name="generate_component",
    toolset="ide",
    schema={
        "name": "generate_component",
        "description": "Generate a new component/file with boilerplate and proper structure",
        "parameters": {
            "type": "object",
            "properties": {
                "component_type": {
                    "type": "string",
                    "enum": ["component", "page", "model", "utility"],
                    "description": "Type of component to generate"
                },
                "framework": {
                    "type": "string",
                    "enum": ["react", "django", "python", "typescript"],
                    "description": "Framework/language"
                },
                "component_name": {
                    "type": "string",
                    "description": "Name of the component (e.g., UserProfile, product_model)"
                },
                "props": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of prop names for components",
                    "default": []
                }
            },
            "required": ["component_type", "framework", "component_name"]
        }
    },
    handler=lambda args, **kw: _generate_component(
        component_type=args.get("component_type"),
        framework=args.get("framework"),
        component_name=args.get("component_name"),
        props=args.get("props", []),
        task_id=kw.get("task_id")
    )
)


# ============================================================================
# Test Generation Tools
# ============================================================================

def _generate_tests(test_type: str, framework: str, target_name: str,
                   module_path: Optional[str] = None,
                   methods: Optional[List[str]] = None,
                   task_id: str = None, **kwargs) -> str:
    """
    Generate test suite for code
    
    Args:
        test_type: "component", "function", "class"
        framework: "jest", "pytest", "vitest"
        target_name: Name of component/function/class
        module_path: Module path (for Python)
        methods: List of methods (for classes)
        task_id: Task ID
    
    Returns:
        JSON with test suite and metadata
    """
    try:
        generator = TestGenerator()
        
        if test_type == "component":
            suite = generator.generate_react_component_tests(
                target_name,
                props=methods or []
            )
        elif test_type == "function":
            if not module_path:
                return json.dumps({
                    "success": False,
                    "error": "module_path required for function tests"
                })
            suite = generator.generate_python_function_tests(
                target_name,
                module_path,
                params=methods or []
            )
        elif test_type == "class":
            if not module_path:
                return json.dumps({
                    "success": False,
                    "error": "module_path required for class tests"
                })
            suite = generator.generate_python_class_tests(
                target_name,
                module_path,
                methods=methods or []
            )
        else:
            return json.dumps({
                "success": False,
                "error": f"Unknown test type: {test_type}"
            })
        
        return json.dumps({
            "success": True,
            "path": suite.path,
            "framework": suite.framework,
            "test_count": suite.test_count,
            "content_preview": suite.content[:500]
        })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


registry.register(
    name="generate_tests",
    toolset="ide",
    schema={
        "name": "generate_tests",
        "description": "Generate comprehensive test suite with proper structure and patterns",
        "parameters": {
            "type": "object",
            "properties": {
                "test_type": {
                    "type": "string",
                    "enum": ["component", "function", "class"],
                    "description": "Type of test to generate"
                },
                "framework": {
                    "type": "string",
                    "enum": ["jest", "pytest", "vitest"],
                    "description": "Test framework"
                },
                "target_name": {
                    "type": "string",
                    "description": "Name of target (component, function, or class)"
                },
                "module_path": {
                    "type": "string",
                    "description": "Module path (required for Python tests)"
                },
                "methods": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "List of methods/props to test",
                    "default": []
                }
            },
            "required": ["test_type", "framework", "target_name"]
        }
    },
    handler=lambda args, **kw: _generate_tests(
        test_type=args.get("test_type"),
        framework=args.get("framework"),
        target_name=args.get("target_name"),
        module_path=args.get("module_path"),
        methods=args.get("methods", []),
        task_id=kw.get("task_id")
    )
)


def _generate_mocks(class_name: str, methods: Optional[List[str]] = None,
                   task_id: str = None, **kwargs) -> str:
    """
    Generate mock objects for testing
    
    Args:
        class_name: Class to mock
        methods: List of methods
        task_id: Task ID
    
    Returns:
        JSON with mock code
    """
    try:
        mock_code = MockGenerator.generate_mock(class_name, methods or [])
        
        return json.dumps({
            "success": True,
            "class_name": class_name,
            "mock_count": len(methods or []),
            "content_preview": mock_code[:500]
        })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


registry.register(
    name="generate_mocks",
    toolset="ide",
    schema={
        "name": "generate_mocks",
        "description": "Generate mock objects and stubs for testing",
        "parameters": {
            "type": "object",
            "properties": {
                "class_name": {
                    "type": "string",
                    "description": "Class name to create mock for"
                },
                "methods": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Methods to mock",
                    "default": []
                }
            },
            "required": ["class_name"]
        }
    },
    handler=lambda args, **kw: _generate_mocks(
        class_name=args.get("class_name"),
        methods=args.get("methods", []),
        task_id=kw.get("task_id")
    )
)


# ============================================================================
# Code Review Tools
# ============================================================================

def _review_code(file_path: str, test_coverage: float = 0.0,
                task_id: str = None, **kwargs) -> str:
    """
    Review code for quality and security
    
    Args:
        file_path: File to review
        test_coverage: Test coverage percentage
        task_id: Task ID
    
    Returns:
        JSON with review report
    """
    try:
        reviewer = CodeReviewer()
        report = reviewer.review_file(file_path, test_coverage)
        
        return json.dumps({
            "success": True,
            "grade": report.grade,
            "passed": report.passed,
            "total_issues": report.total_issues,
            "critical_issues": report.critical_issues,
            "security_issues": report.security_issues,
            "test_coverage": report.test_coverage,
            "complexity_score": report.complexity_score,
            "report_preview": reviewer.generate_report(report)[:500]
        })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


registry.register(
    name="review_code",
    toolset="ide",
    schema={
        "name": "review_code",
        "description": "Review code for quality, security vulnerabilities, and best practices",
        "parameters": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to file to review"
                },
                "test_coverage": {
                    "type": "number",
                    "description": "Test coverage percentage (0-100)",
                    "default": 0.0
                }
            },
            "required": ["file_path"]
        }
    },
    handler=lambda args, **kw: _review_code(
        file_path=args.get("file_path"),
        test_coverage=float(args.get("test_coverage", 0.0)),
        task_id=kw.get("task_id")
    )
)


# ============================================================================
# CI/CD Tools
# ============================================================================

def _create_pr(title: str, description: str, branch: str,
               base_branch: str = "main", task_id: str = None, **kwargs) -> str:
    """
    Create pull request with GitHub integration
    
    Args:
        title: PR title
        description: PR description
        branch: Branch name
        base_branch: Base branch
        task_id: Task ID
    
    Returns:
        JSON with PR details
    """
    try:
        import os
        from ide.ci_cd_integration import GitHubIntegration
        
        token = os.getenv("GITHUB_TOKEN")
        if not token:
            return json.dumps({
                "success": False,
                "error": "GITHUB_TOKEN not configured"
            })
        
        # Get repo from git remote
        import subprocess
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True
        )
        
        remote_url = result.stdout.strip()
        if "github.com" not in remote_url:
            return json.dumps({
                "success": False,
                "error": "Not a GitHub repository"
            })
        
        # Extract owner/repo
        import re
        match = re.search(r'github.com[:/](.+?)/(.+?)(?:\.git)?$', remote_url)
        if not match:
            return json.dumps({
                "success": False,
                "error": "Could not parse repository"
            })
        
        owner, repo = match.groups()
        
        github = GitHubIntegration(token, f"{owner}/{repo}")
        success, pr_data, message = github.create_pull_request(
            title=title,
            body=description,
            head=branch,
            base=base_branch
        )
        
        if success and pr_data:
            return json.dumps({
                "success": True,
                "pr_number": pr_data.get("number"),
                "pr_url": pr_data.get("html_url"),
                "pr_state": pr_data.get("state"),
                "message": message
            })
        else:
            return json.dumps({
                "success": False,
                "error": message
            })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


registry.register(
    name="create_pr",
    toolset="ide",
    schema={
        "name": "create_pr",
        "description": "Create pull request on GitHub with automated workflow",
        "parameters": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Pull request title"
                },
                "description": {
                    "type": "string",
                    "description": "Pull request description/body"
                },
                "branch": {
                    "type": "string",
                    "description": "Feature branch name"
                },
                "base_branch": {
                    "type": "string",
                    "description": "Base branch (default: main)",
                    "default": "main"
                }
            },
            "required": ["title", "description", "branch"]
        }
    },
    handler=lambda args, **kw: _create_pr(
        title=args.get("title"),
        description=args.get("description"),
        branch=args.get("branch"),
        base_branch=args.get("base_branch", "main"),
        task_id=kw.get("task_id")
    )
)


def _run_ci_workflow(workflow_id: str, branch: str, title: str,
                    description: str, build_command: Optional[str] = None,
                    test_command: Optional[str] = None,
                    create_pr: bool = True,
                    task_id: str = None, **kwargs) -> str:
    """
    Run complete CI/CD workflow
    
    Args:
        workflow_id: Workflow ID
        branch: Branch name
        title: PR title
        description: PR description
        build_command: Build command to run
        test_command: Test command to run
        create_pr: Whether to create PR
        task_id: Task ID
    
    Returns:
        JSON with workflow results
    """
    try:
        orchestrator = CICDOrchestrator()
        workflow = orchestrator.create_workflow(workflow_id, branch, title, description)
        workflow = orchestrator.run_workflow(
            workflow,
            build_cmd=build_command,
            test_cmd=test_command,
            create_pr=create_pr
        )
        
        step_results = []
        for step in workflow.steps:
            step_results.append({
                "step": step.step.value,
                "status": step.status.value,
                "duration": step.duration
            })
        
        return json.dumps({
            "success": workflow.passed,
            "workflow_id": workflow.id,
            "status": workflow.status.value,
            "pr_url": workflow.pr_url,
            "step_count": len(workflow.steps),
            "steps": step_results,
            "report_preview": orchestrator.get_workflow_report(workflow)[:500]
        })
    
    except Exception as e:
        return json.dumps({
            "success": False,
            "error": str(e)
        })


registry.register(
    name="run_ci_workflow",
    toolset="ide",
    schema={
        "name": "run_ci_workflow",
        "description": "Run complete CI/CD workflow: build, test, commit, push, and create PR",
        "parameters": {
            "type": "object",
            "properties": {
                "workflow_id": {
                    "type": "string",
                    "description": "Unique workflow identifier"
                },
                "branch": {
                    "type": "string",
                    "description": "Feature branch name"
                },
                "title": {
                    "type": "string",
                    "description": "PR title"
                },
                "description": {
                    "type": "string",
                    "description": "PR description"
                },
                "build_command": {
                    "type": "string",
                    "description": "Build command (optional)"
                },
                "test_command": {
                    "type": "string",
                    "description": "Test command (optional)"
                },
                "create_pr": {
                    "type": "boolean",
                    "description": "Whether to create PR",
                    "default": True
                }
            },
            "required": ["workflow_id", "branch", "title", "description"]
        }
    },
    handler=lambda args, **kw: _run_ci_workflow(
        workflow_id=args.get("workflow_id"),
        branch=args.get("branch"),
        title=args.get("title"),
        description=args.get("description"),
        build_command=args.get("build_command"),
        test_command=args.get("test_command"),
        create_pr=args.get("create_pr", True),
        task_id=kw.get("task_id")
    )
)
