"""
Git操作工具集
提供常用的Git版本控制功能
"""

import subprocess
import json
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime


class GitOperations:
    """Git操作工具类"""

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()
        self.git_executable = self._find_git_executable()

    def _find_git_executable(self) -> str:
        """查找Git可执行文件"""
        try:
            result = subprocess.run(['which', 'git'], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
        except:
            pass
        return 'git'

    def _run_git_command(self, command: List[str], cwd: Optional[str] = None) -> Dict[str, Any]:
        """运行Git命令"""
        try:
            working_dir = cwd or str(self.repo_path)

            # 检查是否为Git仓库
            if not self._is_git_repo(working_dir):
                return {
                    "success": False,
                    "error": "当前目录不是Git仓库",
                    "output": "",
                    "return_code": 1
                }

            full_command = [self.git_executable] + command
            result = subprocess.run(
                full_command,
                cwd=working_dir,
                capture_output=True,
                text=True,
                timeout=30
            )

            return {
                "success": result.returncode == 0,
                "output": result.stdout,
                "error": result.stderr,
                "return_code": result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                "success": False,
                "error": "Git命令执行超时",
                "output": "",
                "return_code": 1
            }
        except Exception as e:
            return {
                "success": False,
                "error": f"执行Git命令失败: {str(e)}",
                "output": "",
                "return_code": 1
            }

    def _is_git_repo(self, path: str) -> bool:
        """检查是否为Git仓库"""
        git_dir = Path(path) / '.git'
        return git_dir.exists() and git_dir.is_dir()

    def get_status(self, repo_path: str = None) -> Dict[str, Any]:
        """获取Git仓库状态"""
        result = self._run_git_command(['status', '--porcelain'], repo_path)

        if not result["success"]:
            return result

        # 解析状态输出
        status_lines = result["output"].strip().split('\n') if result["output"].strip() else []

        staged_files = []
        unstaged_files = []
        untracked_files = []

        for line in status_lines:
            if not line:
                continue

            status = line[:2]
            filename = line[3:]

            if status[0] in 'MADRC':  # 已暂存
                staged_files.append({"file": filename, "status": status[0]})
            elif status[1] in 'MADRC':  # 未暂存
                unstaged_files.append({"file": filename, "status": status[1]})
            elif status == '??':  # 未跟踪
                untracked_files.append(filename)

        # 获取分支信息
        branch_info = self.get_branch_info(repo_path)

        return {
            "success": True,
            "status": {
                "branch": branch_info.get("current_branch", "unknown"),
                "is_clean": len(staged_files) == 0 and len(unstaged_files) == 0 and len(untracked_files) == 0,
                "staged_files": staged_files,
                "unstaged_files": unstaged_files,
                "untracked_files": untracked_files,
                "summary": {
                    "staged": len(staged_files),
                    "unstaged": len(unstaged_files),
                    "untracked": len(untracked_files)
                }
            }
        }

    def get_branch_info(self, repo_path: str = None) -> Dict[str, Any]:
        """获取分支信息"""
        # 获取当前分支
        current_result = self._run_git_command(['rev-parse', '--abbrev-ref', 'HEAD'], repo_path)
        if not current_result["success"]:
            return {"error": "无法获取分支信息"}

        current_branch = current_result["output"].strip()

        # 获取所有分支
        branches_result = self._run_git_command(['branch', '-a'], repo_path)
        branches = []
        if branches_result["success"]:
            for line in branches_result["output"].strip().split('\n'):
                if line:
                    branch_name = line.replace('*', '').strip()
                    branches.append({
                        "name": branch_name,
                        "is_current": '*' in line,
                        "is_remote": 'remotes/' in branch_name
                    })

        # 获取远程仓库信息
        remote_result = self._run_git_command(['remote', '-v'], repo_path)
        remotes = []
        if remote_result["success"]:
            for line in remote_result["output"].strip().split('\n'):
                if line:
                    parts = line.split()
                    if len(parts) >= 2:
                        remotes.append({
                            "name": parts[0],
                            "url": parts[1],
                            "type": parts[2].strip('()') if len(parts) > 2 else "fetch"
                        })

        return {
            "success": True,
            "current_branch": current_branch,
            "branches": branches,
            "remotes": remotes
        }

    def commit_changes(self, message: str, files: List[str] = None, repo_path: str = None) -> Dict[str, Any]:
        """提交更改"""
        if not message:
            return {
                "success": False,
                "error": "提交消息不能为空"
            }

        # 如果指定了文件，先添加到暂存区
        if files:
            add_result = self.add_files(files, repo_path)
            if not add_result["success"]:
                return add_result

        # 执行提交
        return self._run_git_command(['commit', '-m', message], repo_path)

    def add_files(self, files: List[str], repo_path: str = None) -> Dict[str, Any]:
        """添加文件到暂存区"""
        if not files:
            return {
                "success": False,
                "error": "文件列表不能为空"
            }

        command = ['add'] + files
        return self._run_git_command(command, repo_path)

    def push_changes(self, remote: str = 'origin', branch: str = None, repo_path: str = None) -> Dict[str, Any]:
        """推送更改"""
        command = ['push', remote]
        if branch:
            command.append(branch)

        return self._run_git_command(command, repo_path)

    def pull_changes(self, remote: str = 'origin', branch: str = None, repo_path: str = None) -> Dict[str, Any]:
        """拉取更改"""
        command = ['pull', remote]
        if branch:
            command.append(branch)

        return self._run_git_command(command, repo_path)

    def create_branch(self, branch_name: str, checkout: bool = True, repo_path: str = None) -> Dict[str, Any]:
        """创建分支"""
        if checkout:
            command = ['checkout', '-b', branch_name]
        else:
            command = ['branch', branch_name]

        return self._run_git_command(command, repo_path)

    def switch_branch(self, branch_name: str, repo_path: str = None) -> Dict[str, Any]:
        """切换分支"""
        return self._run_git_command(['checkout', branch_name], repo_path)

    def get_commit_history(self, max_count: int = 10, repo_path: str = None) -> Dict[str, Any]:
        """获取提交历史"""
        format_string = '%H|%an|%ae|%ad|%s'
        command = ['log', f'--max-count={max_count}', f'--pretty=format:{format_string}', '--date=iso']

        result = self._run_git_command(command, repo_path)
        if not result["success"]:
            return result

        commits = []
        for line in result["output"].strip().split('\n'):
            if line and '|' in line:
                parts = line.split('|', 4)
                if len(parts) == 5:
                    commits.append({
                        "hash": parts[0],
                        "author_name": parts[1],
                        "author_email": parts[2],
                        "date": parts[3],
                        "message": parts[4]
                    })

        return {
            "success": True,
            "commits": commits,
            "count": len(commits)
        }

    def get_diff(self, staged: bool = False, repo_path: str = None) -> Dict[str, Any]:
        """获取文件差异"""
        command = ['diff']
        if staged:
            command.append('--staged')

        return self._run_git_command(command, repo_path)

    def discard_changes(self, files: List[str] = None, repo_path: str = None) -> Dict[str, Any]:
        """放弃更改"""
        if files:
            command = ['checkout', '--'] + files
        else:
            command = ['checkout', '--', '.']

        return self._run_git_command(command, repo_path)

    def stash_changes(self, message: str = None, repo_path: str = None) -> Dict[str, Any]:
        """暂存更改"""
        command = ['stash']
        if message:
            command.extend(['save', message])

        return self._run_git_command(command, repo_path)

    def get_remotes(self, repo_path: str = None) -> Dict[str, Any]:
        """获取远程仓库信息"""
        return self._run_git_command(['remote', '-v'], repo_path)

    def fetch_from_remote(self, remote: str = 'origin', repo_path: str = None) -> Dict[str, Any]:
        """从远程仓库获取更新"""
        return self._run_git_command(['fetch', remote], repo_path)

    def merge_branch(self, branch_name: str, repo_path: str = None) -> Dict[str, Any]:
        """合并分支"""
        return self._run_git_command(['merge', branch_name], repo_path)

    def rebase_branch(self, branch_name: str, repo_path: str = None) -> Dict[str, Any]:
        """变基分支"""
        return self._run_git_command(['rebase', branch_name], repo_path)


# 统一的Git操作接口
def git_operation(operation: str, **kwargs) -> Dict[str, Any]:
    """统一的Git操作接口"""
    git_ops = GitOperations(kwargs.get('repo_path', '.'))

    operations = {
        'status': git_ops.get_status,
        'branch_info': git_ops.get_branch_info,
        'commit': git_ops.commit_changes,
        'add': git_ops.add_files,
        'push': git_ops.push_changes,
        'pull': git_ops.pull_changes,
        'create_branch': git_ops.create_branch,
        'switch_branch': git_ops.switch_branch,
        'commit_history': git_ops.get_commit_history,
        'diff': git_ops.get_diff,
        'discard': git_ops.discard_changes,
        'stash': git_ops.stash_changes,
        'remotes': git_ops.get_remotes,
        'fetch': git_ops.fetch_from_remote,
        'merge': git_ops.merge_branch,
        'rebase': git_ops.rebase_branch
    }

    if operation not in operations:
        return {
            "success": False,
            "error": f"不支持的操作: {operation}"
        }

    try:
        return operations[operation](**kwargs)
    except Exception as e:
        return {
            "success": False,
            "error": f"操作失败: {str(e)}"
        }


if __name__ == "__main__":
    # 测试Git操作
    result = git_operation('status')
    print(json.dumps(result, indent=2, ensure_ascii=False))