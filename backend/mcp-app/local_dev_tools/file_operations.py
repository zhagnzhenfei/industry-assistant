"""
文件操作工具集
提供文件读写、搜索、格式化等开发常用功能
"""

import os
import json
import re
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import mimetypes


class FileOperations:
    """文件操作工具类"""

    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path).resolve()

    def read_file(self, file_path: str, encoding: str = 'utf-8') -> Dict[str, Any]:
        """读取文件内容"""
        try:
            full_path = self._get_safe_path(file_path)
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"文件不存在: {file_path}",
                    "content": ""
                }

            if not full_path.is_file():
                return {
                    "success": False,
                    "error": f"路径不是文件: {file_path}",
                    "content": ""
                }

            with open(full_path, 'r', encoding=encoding) as f:
                content = f.read()

            # 检测文件类型
            mime_type, _ = mimetypes.guess_type(str(full_path))

            return {
                "success": True,
                "content": content,
                "file_info": {
                    "path": str(full_path),
                    "size": full_path.stat().st_size,
                    "modified_time": datetime.fromtimestamp(full_path.stat().st_mtime).isoformat(),
                    "mime_type": mime_type or "text/plain",
                    "encoding": encoding
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"读取文件失败: {str(e)}",
                "content": ""
            }

    def write_file(self, file_path: str, content: str, encoding: str = 'utf-8', create_dirs: bool = True) -> Dict[str, Any]:
        """写入文件内容"""
        try:
            full_path = self._get_safe_path(file_path)

            # 安全检查
            if not self._is_safe_write_path(full_path):
                return {
                    "success": False,
                    "error": "不允许写入系统目录或父目录"
                }

            # 创建目录
            if create_dirs:
                full_path.parent.mkdir(parents=True, exist_ok=True)

            # 写入文件
            with open(full_path, 'w', encoding=encoding) as f:
                f.write(content)

            return {
                "success": True,
                "message": f"文件已写入: {file_path}",
                "file_info": {
                    "path": str(full_path),
                    "size": len(content.encode(encoding)),
                    "modified_time": datetime.now().isoformat()
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"写入文件失败: {str(e)}"
            }

    def search_files(self, pattern: str, search_path: str = ".", recursive: bool = True, file_type: str = "all") -> Dict[str, Any]:
        """搜索文件"""
        try:
            search_dir = self._get_safe_path(search_path)
            if not search_dir.exists():
                return {
                    "success": False,
                    "error": f"搜索路径不存在: {search_path}",
                    "results": []
                }

            results = []
            search_pattern = re.compile(pattern, re.IGNORECASE)

            # 确定搜索范围
            if recursive:
                iterator = search_dir.rglob('*')
            else:
                iterator = search_dir.glob('*')

            for item in iterator:
                if not item.is_file():
                    continue

                # 文件类型过滤
                if file_type != "all":
                    if not self._match_file_type(item, file_type):
                        continue

                # 文件名匹配
                if search_pattern.search(item.name):
                    results.append(self._get_file_info(item))
                    continue

                # 文件内容匹配（文本文件）
                if self._is_text_file(item):
                    try:
                        with open(item, 'r', encoding='utf-8') as f:
                            content = f.read()
                            if search_pattern.search(content):
                                # 找到匹配内容的具体位置
                                matches = []
                                for match in search_pattern.finditer(content):
                                    start = max(0, match.start() - 50)
                                    end = min(len(content), match.end() + 50)
                                    context = content[start:end]
                                    matches.append({
                                        "line": content[:match.start()].count('\n') + 1,
                                        "context": context.strip()
                                    })

                                file_info = self._get_file_info(item)
                                file_info["matches"] = matches
                                results.append(file_info)
                    except Exception:
                        continue

            return {
                "success": True,
                "results": results,
                "summary": {
                    "total_files": len(results),
                    "search_pattern": pattern,
                    "search_path": str(search_dir),
                    "recursive": recursive
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"搜索失败: {str(e)}",
                "results": []
            }

    def list_directory(self, dir_path: str = ".", include_hidden: bool = False, details: bool = True) -> Dict[str, Any]:
        """列出目录内容"""
        try:
            full_path = self._get_safe_path(dir_path)
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"目录不存在: {dir_path}",
                    "items": []
                }

            if not full_path.is_dir():
                return {
                    "success": False,
                    "error": f"路径不是目录: {dir_path}",
                    "items": []
                }

            items = []
            for item in full_path.iterdir():
                # 跳过隐藏文件（如果需要）
                if not include_hidden and item.name.startswith('.'):
                    continue

                if details:
                    items.append(self._get_file_info(item))
                else:
                    items.append({
                        "name": item.name,
                        "type": "directory" if item.is_dir() else "file"
                    })

            # 排序：目录在前，文件在后，按名称排序
            items.sort(key=lambda x: (x.get("type", "file") != "directory", x.get("name", "")))

            return {
                "success": True,
                "items": items,
                "directory_info": {
                    "path": str(full_path),
                    "total_items": len(items),
                    "directories": sum(1 for item in items if item.get("type") == "directory"),
                    "files": sum(1 for item in items if item.get("type") == "file")
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"列出目录失败: {str(e)}",
                "items": []
            }

    def copy_file(self, source_path: str, dest_path: str, overwrite: bool = False) -> Dict[str, Any]:
        """复制文件或目录"""
        try:
            source = self._get_safe_path(source_path)
            dest = self._get_safe_path(dest_path)

            if not source.exists():
                return {
                    "success": False,
                    "error": f"源路径不存在: {source_path}"
                }

            if dest.exists() and not overwrite:
                return {
                    "success": False,
                    "error": f"目标路径已存在: {dest_path}"
                }

            if source.is_file():
                shutil.copy2(source, dest)
                action = "文件复制"
            else:
                if dest.exists():
                    shutil.rmtree(dest)
                shutil.copytree(source, dest)
                action = "目录复制"

            return {
                "success": True,
                "message": f"{action}成功: {source_path} -> {dest_path}",
                "source": str(source),
                "destination": str(dest)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"复制失败: {str(e)}"
            }

    def delete_file(self, file_path: str, recursive: bool = False) -> Dict[str, Any]:
        """删除文件或目录"""
        try:
            full_path = self._get_safe_path(file_path)

            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"路径不存在: {file_path}"
                }

            # 安全检查
            if not self._is_safe_delete_path(full_path):
                return {
                    "success": False,
                    "error": "不允许删除系统重要目录"
                }

            if full_path.is_file():
                full_path.unlink()
                action = "文件删除"
            else:
                if recursive:
                    shutil.rmtree(full_path)
                    action = "目录递归删除"
                else:
                    return {
                        "success": False,
                        "error": "目录删除需要recursive=True参数"
                    }

            return {
                "success": True,
                "message": f"{action}成功: {file_path}",
                "deleted_path": str(full_path)
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"删除失败: {str(e)}"
            }

    def get_file_stats(self, file_path: str) -> Dict[str, Any]:
        """获取文件统计信息"""
        try:
            full_path = self._get_safe_path(file_path)
            if not full_path.exists():
                return {
                    "success": False,
                    "error": f"路径不存在: {file_path}"
                }

            stat = full_path.stat()

            return {
                "success": True,
                "stats": {
                    "path": str(full_path),
                    "size": stat.st_size,
                    "created_time": datetime.fromtimestamp(stat.st_ctime).isoformat(),
                    "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
                    "accessed_time": datetime.fromtimestamp(stat.st_atime).isoformat(),
                    "is_directory": full_path.is_dir(),
                    "is_file": full_path.is_file(),
                    "permissions": oct(stat.st_mode)[-3:],
                    "extension": full_path.suffix.lower() if full_path.is_file() else "",
                    "mime_type": mimetypes.guess_type(str(full_path))[0] if full_path.is_file() else None
                }
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"获取文件统计失败: {str(e)}"
            }

    def _get_safe_path(self, path: str) -> Path:
        """获取安全路径，防止目录遍历"""
        requested_path = Path(path)
        if requested_path.is_absolute():
            return requested_path.resolve()
        else:
            return (self.base_path / requested_path).resolve()

    def _is_safe_write_path(self, path: Path) -> bool:
        """检查写入路径是否安全"""
        try:
            path.relative_to(self.base_path)
            return True
        except ValueError:
            return False

    def _is_safe_delete_path(self, path: Path) -> bool:
        """检查删除路径是否安全"""
        # 不允许删除根目录、系统目录等
        system_paths = ['/usr', '/bin', '/sbin', '/etc', '/var', '/lib']
        return str(path) not in system_paths and str(path) != '/'

    def _is_text_file(self, file_path: Path) -> bool:
        """检查是否为文本文件"""
        try:
            with open(file_path, 'rb') as f:
                chunk = f.read(1024)
                return not bool(chunk.translate(None, chunk.translate(None, b'\t\n\r\x20-\x7e')))
        except:
            return False

    def _match_file_type(self, file_path: Path, file_type: str) -> bool:
        """匹配文件类型"""
        if file_type == "text":
            return self._is_text_file(file_path)
        elif file_type == "code":
            code_extensions = ['.py', '.js', '.ts', '.java', '.cpp', '.c', '.go', '.rs', '.rb', '.php']
            return file_path.suffix.lower() in code_extensions
        elif file_type == "config":
            config_extensions = ['.json', '.yaml', '.yml', '.xml', '.ini', '.toml', '.conf']
            return file_path.suffix.lower() in config_extensions
        else:
            return file_path.suffix.lower() == f'.{file_type}'

    def _get_file_info(self, file_path: Path) -> Dict[str, Any]:
        """获取文件信息"""
        stat = file_path.stat()
        return {
            "name": file_path.name,
            "path": str(file_path),
            "type": "directory" if file_path.is_dir() else "file",
            "size": stat.st_size,
            "modified_time": datetime.fromtimestamp(stat.st_mtime).isoformat(),
            "extension": file_path.suffix.lower() if file_path.is_file() else "",
            "permissions": oct(stat.st_mode)[-3:]
        }


# 统一的文件操作接口
def file_operation(operation: str, **kwargs) -> Dict[str, Any]:
    """统一的文件操作接口"""
    file_ops = FileOperations()

    operations = {
        'read': file_ops.read_file,
        'write': file_ops.write_file,
        'search': file_ops.search_files,
        'list': file_ops.list_directory,
        'copy': file_ops.copy_file,
        'delete': file_ops.delete_file,
        'stats': file_ops.get_file_stats
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
    # 测试文件操作
    result = file_operation('list', dir_path='.')
    print(json.dumps(result, indent=2, ensure_ascii=False))