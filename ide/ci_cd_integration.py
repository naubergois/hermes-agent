"""
CI/CD Integration for Hermes IDE - Phase 3
Git workflow automation, PR creation, and deployment automation
"""

import json
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from enum import Enum


class WorkflowStatus(Enum):
    """Workflow status"""
    CREATED = "created"
    READY = "ready"
    IN_PROGRESS = "in_progress"
    PASSED = "passed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AutomationStep(Enum):
    """Automation steps"""
    BRANCH_CREATE = "branch_create"
    COMMIT = "commit"
    PUSH = "push"
    PR_CREATE = "pr_create"
    BUILD = "build"
    TEST = "test"
    DEPLOY = "deploy"


@dataclass
class WorkflowStep:
    """Represents one step in automation workflow"""
    step: AutomationStep
    status: WorkflowStatus
    started_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    output: str = ""
    error: Optional[str] = None
    
    @property
    def duration(self) -> float:
        """Get step duration in seconds"""
        if self.completed_at:
            start = datetime.fromisoformat(self.started_at)
            end = datetime.fromisoformat(self.completed_at)
            return (end - start).total_seconds()
        return 0.0


@dataclass
class WorkflowRun:
    """Represents a complete workflow run"""
    id: str
    branch: str
    title: str
    description: str
    status: WorkflowStatus = WorkflowStatus.CREATED
    steps: List[WorkflowStep] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    completed_at: Optional[str] = None
    pr_url: Optional[str] = None
    
    @property
    def is_complete(self) -> bool:
        """Check if workflow is complete"""
        return self.status in (WorkflowStatus.PASSED, WorkflowStatus.FAILED, WorkflowStatus.CANCELLED)
    
    @property
    def passed(self) -> bool:
        """Check if workflow passed all steps"""
        return self.status == WorkflowStatus.PASSED


class GitWorkflowAutomation:
    """
    Git workflow automation (branch, commit, push)
    """
    
    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path)
    
    def create_branch(self, branch_name: str, base_branch: str = "main") -> Tuple[bool, str]:
        """
        Create new branch
        
        Args:
            branch_name: New branch name
            base_branch: Base branch to branch from
        
        Returns:
            (success, output)
        """
        try:
            # Checkout base branch
            subprocess.run(
                ["git", "checkout", base_branch],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            
            # Pull latest
            subprocess.run(
                ["git", "pull", "origin", base_branch],
                cwd=self.repo_path,
                check=True,
                capture_output=True
            )
            
            # Create branch
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            return True, f"Branch {branch_name} created successfully"
        
        except subprocess.CalledProcessError as e:
            return False, f"Error creating branch: {e.stderr}"
    
    def commit_changes(self, message: str, files: Optional[List[str]] = None) -> Tuple[bool, str]:
        """
        Commit changes
        
        Args:
            message: Commit message
            files: Specific files to commit (None for all)
        
        Returns:
            (success, output)
        """
        try:
            if files:
                # Stage specific files
                for file in files:
                    subprocess.run(
                        ["git", "add", file],
                        cwd=self.repo_path,
                        check=True,
                        capture_output=True
                    )
            else:
                # Stage all changes
                subprocess.run(
                    ["git", "add", "-A"],
                    cwd=self.repo_path,
                    check=True,
                    capture_output=True
                )
            
            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            return True, f"Changes committed: {result.stdout}"
        
        except subprocess.CalledProcessError as e:
            return False, f"Error committing: {e.stderr}"
    
    def push_changes(self, branch: str = None) -> Tuple[bool, str]:
        """
        Push changes to remote
        
        Args:
            branch: Branch to push (None for current)
        
        Returns:
            (success, output)
        """
        try:
            if not branch:
                # Get current branch
                result = subprocess.run(
                    ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                    cwd=self.repo_path,
                    check=True,
                    capture_output=True,
                    text=True
                )
                branch = result.stdout.strip()
            
            # Push
            result = subprocess.run(
                ["git", "push", "origin", branch, "-u"],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
                text=True
            )
            
            return True, f"Pushed to {branch}: {result.stdout}"
        
        except subprocess.CalledProcessError as e:
            return False, f"Error pushing: {e.stderr}"


class GitHubIntegration:
    """
    GitHub API integration for PR automation
    """
    
    def __init__(self, token: str = None, repo: str = None):
        self.token = token or self._get_token_from_env()
        self.repo = repo  # "owner/repo"
        self.api_url = "https://api.github.com"
    
    @staticmethod
    def _get_token_from_env() -> Optional[str]:
        """Get GitHub token from environment"""
        import os
        return os.getenv("GITHUB_TOKEN")
    
    def create_pull_request(self, title: str, body: str, head: str,
                           base: str = "main") -> Tuple[bool, Optional[Dict], str]:
        """
        Create pull request
        
        Args:
            title: PR title
            body: PR description
            head: Head branch
            base: Base branch
        
        Returns:
            (success, pr_data, message)
        """
        if not self.token or not self.repo:
            return False, None, "GitHub token or repo not configured"
        
        try:
            import requests
            
            url = f"{self.api_url}/repos/{self.repo}/pulls"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            data = {
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": False
            }
            
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 201:
                pr_data = response.json()
                return True, pr_data, f"PR created: {pr_data['html_url']}"
            else:
                return False, None, f"Error creating PR: {response.text}"
        
        except ImportError:
            return False, None, "requests library not installed"
        except Exception as e:
            return False, None, f"Error: {str(e)}"
    
    def update_pr_status(self, pr_number: int, status: str) -> Tuple[bool, str]:
        """
        Update PR status (draft, ready for review, etc)
        
        Args:
            pr_number: PR number
            status: "draft" or "ready_for_review"
        
        Returns:
            (success, message)
        """
        if not self.token or not self.repo:
            return False, "GitHub token or repo not configured"
        
        try:
            import requests
            
            url = f"{self.api_url}/repos/{self.repo}/pulls/{pr_number}"
            headers = {
                "Authorization": f"token {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            data = {
                "draft": status == "draft"
            }
            
            response = requests.patch(url, headers=headers, json=data, timeout=10)
            
            if response.status_code == 200:
                return True, "PR status updated"
            else:
                return False, f"Error updating PR: {response.text}"
        
        except Exception as e:
            return False, f"Error: {str(e)}"


class BuildAutomation:
    """
    Build system automation
    """
    
    @staticmethod
    def run_build(build_command: str, working_dir: str = ".") -> Tuple[bool, str, str]:
        """
        Run build command
        
        Args:
            build_command: Build command to run
            working_dir: Working directory
        
        Returns:
            (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                build_command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
        
        except subprocess.TimeoutExpired:
            return False, "", "Build timeout (5 minutes)"
        except Exception as e:
            return False, "", f"Error running build: {str(e)}"
    
    @staticmethod
    def run_tests(test_command: str, working_dir: str = ".") -> Tuple[bool, str, str]:
        """
        Run test command
        
        Args:
            test_command: Test command to run
            working_dir: Working directory
        
        Returns:
            (success, stdout, stderr)
        """
        try:
            result = subprocess.run(
                test_command,
                shell=True,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=600  # 10 minute timeout
            )
            
            success = result.returncode == 0
            return success, result.stdout, result.stderr
        
        except subprocess.TimeoutExpired:
            return False, "", "Tests timeout (10 minutes)"
        except Exception as e:
            return False, "", f"Error running tests: {str(e)}"


class CICDOrchestrator:
    """
    Orchestrates complete CI/CD workflow
    """
    
    def __init__(self, repo_path: str = ".", github_token: str = None):
        self.repo_path = Path(repo_path)
        self.git_automation = GitWorkflowAutomation(repo_path)
        self.github_integration = GitHubIntegration(github_token)
        self.build_automation = BuildAutomation()
        self.workflows: Dict[str, WorkflowRun] = {}
    
    def create_workflow(self, workflow_id: str, branch: str, title: str,
                       description: str) -> WorkflowRun:
        """
        Create new workflow
        
        Args:
            workflow_id: Unique workflow ID
            branch: Feature branch name
            title: PR title
            description: PR description
        
        Returns:
            WorkflowRun instance
        """
        workflow = WorkflowRun(
            id=workflow_id,
            branch=branch,
            title=title,
            description=description
        )
        self.workflows[workflow_id] = workflow
        return workflow
    
    def run_workflow(self, workflow: WorkflowRun, build_cmd: str = None,
                    test_cmd: str = None, create_pr: bool = True) -> WorkflowRun:
        """
        Execute complete workflow
        
        Args:
            workflow: WorkflowRun to execute
            build_cmd: Build command
            test_cmd: Test command
            create_pr: Whether to create PR
        
        Returns:
            Updated WorkflowRun
        """
        try:
            workflow.status = WorkflowStatus.IN_PROGRESS
            
            # Step 1: Create branch
            step1 = WorkflowStep(step=AutomationStep.BRANCH_CREATE, 
                                status=WorkflowStatus.IN_PROGRESS)
            success, output = self.git_automation.create_branch(workflow.branch)
            step1.status = WorkflowStatus.PASSED if success else WorkflowStatus.FAILED
            step1.output = output
            step1.completed_at = datetime.now().isoformat()
            workflow.steps.append(step1)
            
            if not success:
                workflow.status = WorkflowStatus.FAILED
                return workflow
            
            # Step 2: Build (optional)
            if build_cmd:
                step_build = WorkflowStep(step=AutomationStep.BUILD,
                                         status=WorkflowStatus.IN_PROGRESS)
                success, stdout, stderr = self.build_automation.run_build(
                    build_cmd, str(self.repo_path)
                )
                step_build.status = WorkflowStatus.PASSED if success else WorkflowStatus.FAILED
                step_build.output = stdout
                step_build.error = stderr
                step_build.completed_at = datetime.now().isoformat()
                workflow.steps.append(step_build)
                
                if not success:
                    workflow.status = WorkflowStatus.FAILED
                    return workflow
            
            # Step 3: Tests (optional)
            if test_cmd:
                step_test = WorkflowStep(step=AutomationStep.TEST,
                                        status=WorkflowStatus.IN_PROGRESS)
                success, stdout, stderr = self.build_automation.run_tests(
                    test_cmd, str(self.repo_path)
                )
                step_test.status = WorkflowStatus.PASSED if success else WorkflowStatus.FAILED
                step_test.output = stdout
                step_test.error = stderr
                step_test.completed_at = datetime.now().isoformat()
                workflow.steps.append(step_test)
                
                if not success:
                    workflow.status = WorkflowStatus.FAILED
                    return workflow
            
            # Step 4: Commit
            step_commit = WorkflowStep(step=AutomationStep.COMMIT,
                                      status=WorkflowStatus.IN_PROGRESS)
            success, output = self.git_automation.commit_changes(
                f"chore: {workflow.title}"
            )
            step_commit.status = WorkflowStatus.PASSED if success else WorkflowStatus.FAILED
            step_commit.output = output
            step_commit.completed_at = datetime.now().isoformat()
            workflow.steps.append(step_commit)
            
            # Step 5: Push
            step_push = WorkflowStep(step=AutomationStep.PUSH,
                                    status=WorkflowStatus.IN_PROGRESS)
            success, output = self.git_automation.push_changes(workflow.branch)
            step_push.status = WorkflowStatus.PASSED if success else WorkflowStatus.FAILED
            step_push.output = output
            step_push.completed_at = datetime.now().isoformat()
            workflow.steps.append(step_push)
            
            # Step 6: Create PR (optional)
            if create_pr:
                step_pr = WorkflowStep(step=AutomationStep.PR_CREATE,
                                      status=WorkflowStatus.IN_PROGRESS)
                success, pr_data, output = self.github_integration.create_pull_request(
                    title=workflow.title,
                    body=workflow.description,
                    head=workflow.branch
                )
                step_pr.status = WorkflowStatus.PASSED if success else WorkflowStatus.FAILED
                step_pr.output = output
                if pr_data:
                    workflow.pr_url = pr_data.get('html_url')
                step_pr.completed_at = datetime.now().isoformat()
                workflow.steps.append(step_pr)
            
            # Mark as complete
            workflow.status = WorkflowStatus.PASSED
            workflow.completed_at = datetime.now().isoformat()
        
        except Exception as e:
            workflow.status = WorkflowStatus.FAILED
            workflow.completed_at = datetime.now().isoformat()
        
        return workflow
    
    def get_workflow_report(self, workflow: WorkflowRun, format: str = "text") -> str:
        """
        Generate workflow report
        
        Args:
            workflow: WorkflowRun to report
            format: "text" or "json"
        
        Returns:
            Formatted report
        """
        if format == "json":
            return json.dumps({
                "id": workflow.id,
                "branch": workflow.branch,
                "title": workflow.title,
                "status": workflow.status.value,
                "passed": workflow.passed,
                "created_at": workflow.created_at,
                "completed_at": workflow.completed_at,
                "pr_url": workflow.pr_url,
                "steps": [
                    {
                        "step": s.step.value,
                        "status": s.status.value,
                        "duration": s.duration,
                        "output": s.output[:200] if s.output else "",
                        "error": s.error[:200] if s.error else ""
                    } for s in workflow.steps
                ]
            }, indent=2)
        
        # Text format
        status_emoji = "✅" if workflow.passed else "❌"
        output = [
            f"\n🚀 CI/CD WORKFLOW REPORT {status_emoji}",
            "=" * 70,
            f"Workflow ID:  {workflow.id}",
            f"Branch:       {workflow.branch}",
            f"Title:        {workflow.title}",
            f"Status:       {workflow.status.value.upper()}",
            f"Created:      {workflow.created_at}",
            f"Completed:    {workflow.completed_at or 'In Progress'}",
            f"PR URL:       {workflow.pr_url or 'N/A'}",
            "",
            "STEPS:",
            "-" * 70,
        ]
        
        for step in workflow.steps:
            status_icon = "✅" if step.status == WorkflowStatus.PASSED else "❌"
            output.append(f"{status_icon} {step.step.value.upper()} ({step.duration:.1f}s)")
            if step.output:
                lines = step.output.split('\n')[:2]
                for line in lines:
                    if line.strip():
                        output.append(f"   {line[:60]}")
        
        return '\n'.join(output)
