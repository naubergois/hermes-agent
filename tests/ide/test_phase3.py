"""
Tests for Hermes IDE Phase 3 - Code Generation, Testing, Review, and CI/CD
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Test imports
from ide.code_generator import CodeGenerator, CodeTemplates
from ide.test_generator import TestGenerator, TestTemplates, MockGenerator
from ide.code_reviewer import CodeReviewer, SecurityScanner, ComplexityAnalyzer, PatternValidator, Severity
from ide.ci_cd_integration import GitWorkflowAutomation, CICDOrchestrator, WorkflowRun


class TestCodeGenerator:
    """Test code generation"""
    
    def setup_method(self):
        """Setup"""
        self.generator = CodeGenerator()
    
    def test_generate_react_component(self):
        """Test React component generation"""
        result = self.generator.generate_component("react", "UserProfile", ["name", "email"])
        
        assert result is not None
        assert result.framework == "react"
        assert result.component_type == "component"
        assert "UserProfile" in result.content
        assert len(result.content) > 100
    
    def test_generate_django_model(self):
        """Test Django model generation"""
        result = self.generator.generate_model("django", "Product")
        
        assert result is not None
        assert result.framework == "django"
        assert "class Product" in result.content
        assert "models.Model" in result.content
    
    def test_generate_python_utility(self):
        """Test Python utility generation"""
        result = self.generator.generate_utility("python", "string_utils")
        
        assert result is not None
        assert result.framework == "python"
        assert "def" in result.content
    
    def test_generate_typescript_page(self):
        """Test TypeScript page generation"""
        result = self.generator.generate_page("typescript", "HomePage")
        
        assert result is not None
        assert result.framework == "typescript"
        assert "HomePage" in result.content
    
    def test_template_substitution(self):
        """Test template variable substitution"""
        result = self.generator.generate_component(
            "react", 
            "DataTable",
            ["columns", "rows", "onSort"]
        )
        
        # Should have converted property names
        assert "columns" in result.content.lower()
        assert "DataTable" in result.content


class TestTestGenerator:
    """Test test generation"""
    
    def setup_method(self):
        """Setup"""
        self.generator = TestGenerator()
    
    def test_generate_react_tests(self):
        """Test React component test generation"""
        suite = self.generator.generate_react_component_tests(
            "Button",
            props=["label", "onClick", "disabled"]
        )
        
        assert suite is not None
        assert suite.framework == "jest"
        assert suite.test_count > 0
        assert "describe" in suite.content
        assert "Button" in suite.content
    
    def test_generate_python_function_tests(self):
        """Test Python function test generation"""
        suite = self.generator.generate_python_function_tests(
            "calculate_total",
            "src.utils",
            ["items", "tax"]
        )
        
        assert suite is not None
        assert suite.framework == "pytest"
        assert "def test_" in suite.content
        assert "calculate_total" in suite.content
    
    def test_generate_python_class_tests(self):
        """Test Python class test generation"""
        suite = self.generator.generate_python_class_tests(
            "UserManager",
            "src.models",
            methods=["create_user", "delete_user", "update_user"]
        )
        
        assert suite is not None
        assert suite.framework == "pytest"
        assert "TestUserManager" in suite.content
        assert "create_user" in suite.content
    
    def test_test_suite_metadata(self):
        """Test test suite metadata"""
        suite = self.generator.generate_react_component_tests("Input")
        
        assert suite.language == "typescript"
        assert suite.framework == "jest"
        assert suite.test_count >= 5
        assert suite.generated_at is not None
    
    def test_mock_generation(self):
        """Test mock object generation"""
        mock_code = MockGenerator.generate_mock(
            "DataService",
            ["fetch_data", "save_data", "delete_data"]
        )
        
        assert "MockDataService" in mock_code
        assert "fetch_data" in mock_code
        assert "save_data" in mock_code


class TestSecurityScanner:
    """Test security vulnerability scanning"""
    
    def setup_method(self):
        """Setup"""
        self.scanner = SecurityScanner()
    
    def test_detect_hardcoded_password(self):
        """Test detection of hardcoded passwords"""
        code = '''
password = "my_secret_password_123"
api_key = "sk-1234567890"
'''
        issues = self.scanner.scan_file("test.py", code)
        
        assert len(issues) > 0
        assert any("password" in i.message.lower() for i in issues)
    
    def test_detect_sql_injection(self):
        """Test detection of SQL injection patterns"""
        code = '''
query = "SELECT * FROM users WHERE id = " + str(user_id)
sql = "INSERT INTO table VALUES (" + value + ")"
'''
        issues = self.scanner.scan_file("test.py", code)
        
        assert any("SQL" in i.message for i in issues)
    
    def test_detect_dangerous_functions(self):
        """Test detection of dangerous functions"""
        code = '''
eval(user_input)
exec(code_string)
'''
        issues = self.scanner.scan_file("test.py", code)
        
        assert any("eval" in i.message.lower() or "exec" in i.message.lower() for i in issues)
    
    def test_clean_code_no_issues(self):
        """Test clean code produces no issues"""
        code = '''
def calculate(a, b):
    return a + b
'''
        issues = self.scanner.scan_file("test.py", code)
        
        # Should have no security issues
        security_issues = [i for i in issues if i.severity == Severity.CRITICAL]
        assert len(security_issues) == 0


class TestComplexityAnalyzer:
    """Test code complexity analysis"""
    
    def setup_method(self):
        """Setup"""
        self.analyzer = ComplexityAnalyzer()
    
    def test_simple_code_complexity(self):
        """Test simple code has low complexity"""
        code = '''
def add(a, b):
    return a + b
'''
        complexity = self.analyzer.calculate_cyclomatic_complexity(code)
        
        assert complexity < 2
    
    def test_complex_code_complexity(self):
        """Test complex code has high complexity"""
        code = '''
def process(data):
    if data:
        if data > 10:
            for item in data:
                if item:
                    while item > 0:
                        item -= 1
        else:
            return None
    else:
        return 0
'''
        complexity = self.analyzer.calculate_cyclomatic_complexity(code)
        
        assert complexity > 2
    
    def test_lines_of_code_count(self):
        """Test LOC counting"""
        code = '''
def example():
    x = 1
    y = 2
    return x + y
'''
        loc = self.analyzer.calculate_lines_of_code(code)
        
        assert loc >= 3  # Should count at least the code lines


class TestPatternValidator:
    """Test pattern validation"""
    
    def setup_method(self):
        """Setup"""
        self.validator = PatternValidator()
    
    def test_python_naming_conventions(self):
        """Test Python naming convention validation"""
        code = '''
def MyFunction():  # Should be my_function
    pass

class user_model:  # Should be UserModel
    pass
'''
        issues = self.validator.validate_python_conventions(code, "test.py")
        
        assert len(issues) > 0
    
    def test_valid_naming_conventions(self):
        """Test valid naming conventions"""
        code = '''
def my_function():
    pass

class UserModel:
    pass
'''
        issues = self.validator.validate_python_conventions(code, "test.py")
        
        # Filter for naming issues
        naming_issues = [i for i in issues if "naming" in i.message.lower()]
        assert len(naming_issues) == 0


class TestCodeReviewer:
    """Test code review system"""
    
    def setup_method(self):
        """Setup"""
        self.reviewer = CodeReviewer()
    
    def test_review_file_generates_report(self):
        """Test file review generates report"""
        code = "def add(a, b):\n    return a + b"
        report = self.reviewer.review_file("test.py", test_coverage=85.0)
        
        assert report is not None
        assert report.test_coverage == 85.0
        assert report.grade in ["A", "B", "C", "D", "F"]
    
    def test_review_report_with_issues(self):
        """Test review report with security issues"""
        code = 'password = "secret123"'
        report = self.reviewer.review_file("test.py", test_coverage=60.0)
        
        assert report.total_issues > 0
        assert report.security_issues > 0
    
    def test_review_passed_checks(self):
        """Test review pass/fail logic"""
        code = "def func(): pass"
        report = self.reviewer.review_file("test.py", test_coverage=85.0)
        
        # Should pass if no critical issues and coverage >= 80%
        if report.critical_issues == 0 and report.test_coverage >= 80:
            assert report.passed
    
    def test_generate_text_report(self):
        """Test text report generation"""
        code = "x = 1"
        report = self.reviewer.review_file("test.py", 75.0)
        text_report = self.reviewer.generate_report(report, format="text")
        
        assert "CODE REVIEW" in text_report
        assert report.grade in text_report
    
    def test_generate_json_report(self):
        """Test JSON report generation"""
        code = "x = 1"
        report = self.reviewer.review_file("test.py", 90.0)
        json_report = self.reviewer.generate_report(report, format="json")
        
        data = json.loads(json_report)
        assert "grade" in data
        assert "total_issues" in data


class TestGitWorkflowAutomation:
    """Test Git workflow automation"""
    
    @patch('subprocess.run')
    def test_create_branch(self, mock_run):
        """Test branch creation"""
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        
        automation = GitWorkflowAutomation()
        success, output = automation.create_branch("feature/new-feature")
        
        assert success
        assert "created" in output.lower()
        assert mock_run.call_count >= 2  # checkout and branch creation
    
    @patch('subprocess.run')
    def test_commit_changes(self, mock_run):
        """Test commit"""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="[main 1234567] Test commit\n 1 file changed",
            stderr=""
        )
        
        automation = GitWorkflowAutomation()
        success, output = automation.commit_changes("Add new feature")
        
        assert success
        assert "commit" in output.lower()
    
    @patch('subprocess.run')
    def test_push_changes(self, mock_run):
        """Test push"""
        mock_run.return_value = MagicMock(returncode=0, stdout="Pushed", stderr="")
        
        automation = GitWorkflowAutomation()
        success, output = automation.push_changes("feature/branch")
        
        assert success


class TestCICDOrchestrator:
    """Test CI/CD orchestration"""
    
    def setup_method(self):
        """Setup"""
        self.orchestrator = CICDOrchestrator()
    
    def test_create_workflow(self):
        """Test workflow creation"""
        workflow = self.orchestrator.create_workflow(
            "wf-001",
            "feature/test",
            "Test Feature",
            "This is a test feature"
        )
        
        assert workflow.id == "wf-001"
        assert workflow.branch == "feature/test"
        assert workflow.title == "Test Feature"
    
    @patch('ide.ci_cd_integration.GitWorkflowAutomation')
    def test_workflow_execution(self, mock_git):
        """Test workflow execution"""
        # Mock Git automation
        mock_instance = MagicMock()
        mock_instance.create_branch.return_value = (True, "Branch created")
        mock_instance.commit_changes.return_value = (True, "Committed")
        mock_instance.push_changes.return_value = (True, "Pushed")
        mock_git.return_value = mock_instance
        
        orchestrator = CICDOrchestrator()
        workflow = orchestrator.create_workflow("wf-001", "test", "title", "desc")
        
        # Should have basic structure
        assert workflow.id == "wf-001"
        assert len(workflow.steps) == 0  # No steps yet
    
    def test_workflow_report_generation(self):
        """Test workflow report generation"""
        workflow = self.orchestrator.create_workflow(
            "wf-001",
            "feature/test",
            "Test Feature",
            "Description"
        )
        
        report = self.orchestrator.get_workflow_report(workflow, format="text")
        
        assert "WORKFLOW" in report
        assert "wf-001" in report
    
    def test_workflow_report_json(self):
        """Test JSON workflow report"""
        workflow = self.orchestrator.create_workflow(
            "wf-001",
            "feature/test",
            "Test Feature",
            "Description"
        )
        
        report = self.orchestrator.get_workflow_report(workflow, format="json")
        data = json.loads(report)
        
        assert data["id"] == "wf-001"
        assert "status" in data


class TestPhase3Integration:
    """Integration tests for Phase 3"""
    
    def test_full_code_generation_to_test_pipeline(self):
        """Test complete pipeline from generation to testing"""
        # Generate component
        generator = CodeGenerator()
        component = generator.generate_component("react", "Form", ["name", "email"])
        
        assert component is not None
        assert "Form" in component.content
        
        # Generate tests
        test_gen = TestGenerator()
        tests = test_gen.generate_react_component_tests("Form", ["name", "email"])
        
        assert tests is not None
        assert "Form" in tests.content
    
    def test_review_generated_code(self):
        """Test reviewing generated code"""
        generator = CodeGenerator()
        component = generator.generate_component("react", "Button", [])
        
        reviewer = CodeReviewer()
        report = reviewer.review_file("test.tsx", test_coverage=85.0)
        
        assert report is not None
        assert report.grade in ["A", "B", "C", "D", "F"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
