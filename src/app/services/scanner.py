import os
import ast
import re
from pathlib import Path
from typing import Dict, List, Optional, Union
from github import ContentFile
from ..utils.cache import cache
from ..models import FileAnalysis
from ..config import settings

class CodeScanner:
    def __init__(self, github_client):
        self.github = github_client
        self.supported_languages = {
            '.py': 'python',
            '.js': 'javascript',
            '.ts': 'typescript',
            '.jsx': 'javascript',
            '.tsx': 'typescript'
        }
        
        # JS/TS function pattern (captures async, export, etc.)
        self.js_function_pattern = re.compile(
            r'(?P<prefix>(export\s+)?(async\s+)?(function\*?\s+|const\s+\w+\s*=\s*(async\s+)?function\*?\s*|class\s+))'
            r'(?P<name>\w+)'
            r'(?P<params>\([^)]*\))',
            re.MULTILINE
        )
        
        # JS/TS docstring pattern
        self.jsdoc_pattern = re.compile(
            r'/\*\*.*?\*/',
            re.DOTALL
        )

    async def scan_repository(self, repo_name: str) -> Dict[str, List[FileAnalysis]]:
        """Scan a repository and return analysis of undocumented code"""
        repo = self.github.get_repo(repo_name)
        results = {}
        
        for content_file in repo.get_contents(""):
            if content_file.type == "dir":
                await self._process_directory(repo, content_file.path, results)
            else:
                analysis = await self._analyze_file(repo, content_file)
                if analysis:
                    results[content_file.path] = analysis
        
        return results

    async def _process_directory(self, repo, path: str, results: dict):
        """Recursively process directory contents"""
        for content_file in repo.get_contents(path):
            if content_file.type == "dir":
                await self._process_directory(repo, content_file.path, results)
            else:
                analysis = await self._analyze_file(repo, content_file)
                if analysis:
                    results[content_file.path] = analysis

    async def _analyze_file(self, repo, content_file: ContentFile) -> Optional[FileAnalysis]:
        """Analyze a single file for documentation needs"""
        if not self._is_supported_file(content_file.path):
            return None
            
        cache_key = f"analysis:{repo.full_name}:{content_file.sha}"
        cached = await cache.get(cache_key)
        if cached:
            return cached
            
        content = self._get_file_content(content_file)
        analysis = self._parse_code(content, content_file.path)
        
        await cache.set(cache_key, analysis, ttl=86400)
        return analysis

    def _is_supported_file(self, path: str) -> bool:
        """Check if file extension is supported"""
        ext = Path(path).suffix.lower()
        return ext in self.supported_languages

    def _get_file_content(self, content_file: ContentFile) -> str:
        """Get file content with proper decoding"""
        if content_file.encoding == 'base64':
            import base64
            return base64.b64decode(content_file.content).decode('utf-8')
        return content_file.content

    def _parse_code(self, content: str, path: str) -> FileAnalysis:
        """Parse code and identify documentation needs"""
        ext = Path(path).suffix.lower()
        language = self.supported_languages.get(ext)
        
        if language == 'python':
            return self._parse_python(content, path)
        elif language in ('javascript', 'typescript'):
            return self._parse_javascript(content, path, language)
        
        return FileAnalysis(path=path, needs_docs=False)

    def _parse_python(self, content: str, path: str) -> FileAnalysis:
        """Python-specific code analysis"""
        tree = ast.parse(content)
        analysis = FileAnalysis(
            path=path,
            language='python',
            needs_docs=False,
            original_content=content
        )
        
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not self._has_proper_docs(node):
                    analysis.needs_docs = True
                    analysis.undocumented_items.append({
                        'type': 'function' if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) else 'class',
                        'name': node.name,
                        'line': node.lineno,
                        'code': ast.get_source_segment(content, node)
                    })
        
        return analysis

    def _parse_javascript(self, content: str, path: str, language: str) -> FileAnalysis:
        """JavaScript/TypeScript code analysis"""
        analysis = FileAnalysis(
            path=path,
            language=language,
            needs_docs=False,
            original_content=content
        )
        
        # Find all functions and classes
        for match in self.js_function_pattern.finditer(content):
            func_code = match.group(0)
            func_name = match.group('name')
            line_no = content[:match.start()].count('\n') + 1
            
            # Check for preceding JSDoc
            preceding_code = content[:match.start()]
            if not self._has_jsdoc(preceding_code):
                analysis.needs_docs = True
                analysis.undocumented_items.append({
                    'type': 'function',
                    'name': func_name,
                    'line': line_no,
                    'code': func_code
                })
        
        return analysis

    def _has_proper_docs(self, node) -> bool:
        """Check if Python node has proper docstring"""
        return (
            ast.get_docstring(node) is not None 
            and len(ast.get_docstring(node).strip()) > 10
        )

    def _has_jsdoc(self, preceding_code: str) -> bool:
        """Check if JS/TS code has preceding JSDoc"""
        # Find the last non-whitespace character before the function
        trimmed = preceding_code.rstrip()
        if not trimmed:
            return False
            
        # Look for JSDoc comments
        last_newline = trimmed.rfind('\n')
        search_area = trimmed[last_newline+1:] if last_newline != -1 else trimmed
        return bool(self.jsdoc_pattern.search(search_area))