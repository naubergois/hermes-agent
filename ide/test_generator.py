"""
Test Generator for Hermes IDE - Phase 3
Generates test stubs, mocks, and fixtures automatically
"""

import json
import re
from pathlib import Path
from dataclasses import dataclass, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime


@dataclass
class TestSuite:
    """Represents a generated test suite"""
    path: str
    content: str
    language: str
    framework: str  # jest, pytest, vitest, mocha
    test_count: int = 0
    generated_at: str = None
    coverage_required: float = 80.0
    
    def __post_init__(self):
        if not self.generated_at:
            self.generated_at = datetime.now().isoformat()


class TestTemplates:
    """Test templates for different frameworks"""
    
    JEST_COMPONENT = '''import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import {ComponentName} from './{ComponentName}';

describe('{ComponentName}', () => {{
  describe('Rendering', () => {{
    it('should render without crashing', () => {{
      render(<{ComponentName} />);
      expect(screen.getByRole('heading')).toBeInTheDocument();
    }});

    it('should render with required props', () => {{
      const props = {{ {props_example} }};
      render(<{ComponentName} {{...props}} />);
      expect(screen.getByTestId('{ComponentName}')).toBeInTheDocument();
    }});
  }});

  describe('User Interactions', () => {{
    it('should handle click events', () => {{
      const mockHandler = jest.fn();
      render(<{ComponentName} onClick={{mockHandler}} />);
      fireEvent.click(screen.getByRole('button'));
      expect(mockHandler).toHaveBeenCalled();
    }});

    it('should update state on user input', () => {{
      render(<{ComponentName} />);
      const input = screen.getByRole('textbox');
      fireEvent.change(input, {{ target: {{ value: 'test' }} }});
      expect(input.value).toBe('test');
    }});
  }});

  describe('Edge Cases', () => {{
    it('should handle null props gracefully', () => {{
      render(<{ComponentName} prop={{null}} />);
      expect(screen.getByTestId('{ComponentName}')).toBeInTheDocument();
    }});

    it('should handle empty data', () => {{
      render(<{ComponentName} items={{[]}} />);
      expect(screen.queryByTestId('item')).not.toBeInTheDocument();
    }});
  }});

  describe('Accessibility', () => {{
    it('should have proper ARIA labels', () => {{
      render(<{ComponentName} />);
      expect(screen.getByRole('button')).toHaveAttribute('aria-label');
    }});

    it('should be keyboard navigable', () => {{
      render(<{ComponentName} />);
      expect(screen.getByRole('button')).not.toHaveAttribute('tabindex', '-1');
    }});
  }});

  describe('Snapshots', () => {{
    it('should match snapshot', () => {{
      const {{ container }} = render(<{ComponentName} />);
      expect(container).toMatchSnapshot();
    }});
  }});
}});
'''

    PYTEST_FUNCTION = '''"""
Tests for {module_name} module
"""
import pytest
from {module_path} import {function_name}


class Test{FunctionName}:
    """Test suite for {function_name} function"""

    def setup_method(self):
        """Setup before each test"""
        pass

    def teardown_method(self):
        """Cleanup after each test"""
        pass

    def test_basic_functionality(self):
        """Test basic functionality"""
        # Arrange
        {arrange}
        
        # Act
        result = {function_name}({params})
        
        # Assert
        assert result is not None

    def test_with_valid_input(self):
        """Test with valid input"""
        # Arrange
        {arrange}
        
        # Act
        result = {function_name}({params})
        
        # Assert
        assert result is not None

    def test_with_invalid_input(self):
        """Test with invalid input"""
        # Arrange / Act / Assert
        with pytest.raises(ValueError):
            {function_name}(None)

    def test_return_type(self):
        """Test return type"""
        # Arrange
        {arrange}
        
        # Act
        result = {function_name}({params})
        
        # Assert
        assert isinstance(result, ({expected_types}))

    def test_edge_cases(self):
        """Test edge cases"""
        # Test with empty input
        result = {function_name}()
        assert result is not None

    @pytest.mark.parametrize("input,expected", [
        ({test_cases})
    ])
    def test_parametrized(self, input, expected):
        """Parametrized test cases"""
        result = {function_name}(input)
        assert result == expected


class Test{FunctionName}Integration:
    """Integration tests for {function_name}"""

    def test_integration_with_dependencies(self):
        """Test integration with dependencies"""
        # TODO: Implement integration tests
        pass
'''

    PYTEST_CLASS = '''"""
Tests for {module_name} module
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from {module_path} import {ClassName}


class Test{ClassName}Init:
    """Test {ClassName} initialization"""

    def test_init_with_default_values(self):
        """Test initialization with default values"""
        obj = {ClassName}()
        assert obj is not None

    def test_init_with_custom_values(self):
        """Test initialization with custom values"""
        obj = {ClassName}({init_params})
        assert obj is not None

    def test_init_raises_on_invalid_input(self):
        """Test initialization raises on invalid input"""
        with pytest.raises((ValueError, TypeError)):
            {ClassName}(invalid_param=None)


class Test{ClassName}Methods:
    """Test {ClassName} methods"""

    @pytest.fixture
    def instance(self):
        """Fixture for {ClassName} instance"""
        return {ClassName}()

    {method_tests}

    def test_method_with_mock_dependency(self, instance):
        """Test method with mocked dependency"""
        with patch('module.dependency') as mock_dep:
            mock_dep.return_value = "mocked_value"
            result = instance.some_method()
            mock_dep.assert_called_once()


class Test{ClassName}EdgeCases:
    """Test edge cases and error handling"""

    def test_handles_none_input(self):
        """Test handling of None input"""
        obj = {ClassName}()
        result = obj.process(None)
        assert result is not None

    def test_handles_empty_data(self):
        """Test handling of empty data"""
        obj = {ClassName}()
        result = obj.process([])
        assert isinstance(result, (list, dict))

    def test_thread_safety(self):
        """Test thread safety if applicable"""
        # TODO: Implement thread safety tests
        pass


class Test{ClassName}Integration:
    """Integration tests for {ClassName}"""

    def test_integration_with_real_dependencies(self):
        """Test integration with real dependencies"""
        obj = {ClassName}()
        # TODO: Implement integration tests
        result = obj.main_method()
        assert result is not None
'''


class TestGenerator:
    """
    Test generator for creating test stubs and mocks
    """
    
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.templates = TestTemplates()
    
    def generate_react_component_tests(self, component_name: str,
                                      props: List[str] = None) -> TestSuite:
        """
        Generate tests for React component
        
        Args:
            component_name: Component name (PascalCase)
            props: List of prop names
        
        Returns:
            TestSuite with component tests
        """
        props = props or []
        props_example = ", ".join([f"{p}: 'test'" for p in props])
        
        content = self.templates.JEST_COMPONENT
        content = content.replace("{ComponentName}", component_name)
        content = content.replace("{props_example}", props_example or "// no props")
        
        path = f"src/components/__tests__/{component_name}.test.tsx"
        
        return TestSuite(
            path=path,
            content=content,
            language="typescript",
            framework="jest",
            test_count=9
        )
    
    def generate_python_function_tests(self, function_name: str, 
                                      module_path: str,
                                      params: List[str] = None) -> TestSuite:
        """
        Generate tests for Python function
        
        Args:
            function_name: Function name (snake_case)
            module_path: Module path (e.g., 'src.utils')
            params: List of parameter names
        
        Returns:
            TestSuite with function tests
        """
        params = params or []
        param_str = ", ".join(params)
        
        module_name = module_path.split('.')[-1]
        FunctionName = self._to_pascal_case(function_name)
        
        content = self.templates.PYTEST_FUNCTION
        content = content.replace("{module_name}", module_name)
        content = content.replace("{function_name}", function_name)
        content = content.replace("{FunctionName}", FunctionName)
        content = content.replace("{module_path}", module_path)
        content = content.replace("{arrange}", "# TODO: Setup test data")
        content = content.replace("{params}", param_str or "")
        content = content.replace("{expected_types}", "str, int, list, dict")
        content = content.replace("{test_cases}", "('input1', 'expected1'),\n        ('input2', 'expected2')")
        
        path = f"tests/test_{function_name}.py"
        
        return TestSuite(
            path=path,
            content=content,
            language="python",
            framework="pytest",
            test_count=6
        )
    
    def generate_python_class_tests(self, class_name: str,
                                   module_path: str,
                                   methods: List[str] = None) -> TestSuite:
        """
        Generate tests for Python class
        
        Args:
            class_name: Class name (PascalCase)
            module_path: Module path
            methods: List of method names
        
        Returns:
            TestSuite with class tests
        """
        methods = methods or []
        
        module_name = module_path.split('.')[-1]
        
        # Generate method test stubs
        method_tests = "\n    ".join([
            f'''def test_{method}(self, instance):
        """Test {method} method"""
        result = instance.{method}()
        assert result is not None'''
            for method in methods
        ])
        
        content = self.templates.PYTEST_CLASS
        content = content.replace("{module_name}", module_name)
        content = content.replace("{ClassName}", class_name)
        content = content.replace("{module_path}", module_path)
        content = content.replace("{init_params}", ", ".join([f"param{i}='value{i}'" for i in range(2)]))
        content = content.replace("{method_tests}", method_tests or "# No methods to test")
        
        path = f"tests/test_{self._to_snake_case(class_name)}.py"
        
        return TestSuite(
            path=path,
            content=content,
            language="python",
            framework="pytest",
            test_count=5 + len(methods)
        )
    
    def generate_fixtures(self, name: str, data: Dict[str, Any]) -> TestSuite:
        """
        Generate test fixtures
        
        Args:
            name: Fixture name
            data: Test data
        
        Returns:
            TestSuite with fixtures
        """
        content = f'''"""
Test fixtures for {name}
"""
import pytest


@pytest.fixture
def {name}_data():
    """Fixture for {name} test data"""
    return {self._format_data(data)}


@pytest.fixture
def {name}_mock():
    """Mock object for {name}"""
    from unittest.mock import Mock
    return Mock()


@pytest.fixture
def {name}_setup_teardown():
    """Setup and teardown for {name} tests"""
    # Setup
    print("Setting up {name}")
    
    yield  # Test runs here
    
    # Teardown
    print("Tearing down {name}")
'''
        
        path = f"tests/fixtures/{name}.py"
        
        return TestSuite(
            path=path,
            content=content,
            language="python",
            framework="pytest",
            test_count=0
        )
    
    def write_suite(self, suite: TestSuite) -> bool:
        """
        Write test suite to disk
        
        Args:
            suite: TestSuite to write
        
        Returns:
            True if successful
        """
        try:
            file_path = self.project_root / suite.path
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            file_path.write_text(suite.content)
            return True
        except Exception as e:
            print(f"Error writing test file: {e}")
            return False
    
    @staticmethod
    def _to_pascal_case(name: str) -> str:
        """Convert snake_case to PascalCase"""
        return "".join(word.title() for word in name.split('_'))
    
    @staticmethod
    def _to_snake_case(name: str) -> str:
        """Convert PascalCase to snake_case"""
        import re
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    @staticmethod
    def _format_data(data: Dict[str, Any]) -> str:
        """Format data as Python code"""
        return json.dumps(data, indent=4)


class MockGenerator:
    """
    Generate mock objects and stubs for testing
    """
    
    @staticmethod
    def generate_mock(class_name: str, methods: List[str] = None) -> str:
        """
        Generate mock class code
        
        Args:
            class_name: Class name
            methods: List of method names to mock
        
        Returns:
            Mock class code
        """
        methods = methods or []
        
        method_stubs = "\n    ".join([
            f"def {method}(self, *args, **kwargs):\n        return Mock()"
            for method in methods
        ])
        
        code = f'''from unittest.mock import Mock, MagicMock


class Mock{class_name}:
    """Mock for {class_name}"""
    
    def __init__(self):
        self.call_count = 0
        self.call_args = []
    
    {method_stubs}
    
    def __call__(self, *args, **kwargs):
        self.call_count += 1
        self.call_args.append((args, kwargs))
        return Mock()


def create_mock_{class_name.lower()}(**kwargs):
    """Factory for creating {class_name} mocks"""
    mock = Mock{class_name}()
    for key, value in kwargs.items():
        setattr(mock, key, value)
    return mock
'''
        
        return code
