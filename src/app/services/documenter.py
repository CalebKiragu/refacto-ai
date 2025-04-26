import openai
from typing import Dict, List
from ..models import FileAnalysis
from ..config import settings

class DocumentationGenerator:
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.temperature = 0.3
        self.max_tokens = 1000
        self.language_handlers = {
            'python': self._handle_python,
            'javascript': self._handle_javascript,
            'typescript': self._handle_typescript
        }

    async def generate_documentation(self, analysis: FileAnalysis) -> str:
        """Generate documentation for analyzed code"""
        if not analysis.needs_docs:
            return analysis.original_content
            
        handler = self.language_handlers.get(analysis.language, self._handle_generic)
        return await handler(analysis)

    async def _handle_python(self, analysis: FileAnalysis) -> str:
        """Python-specific documentation generation"""
        prompts = self._build_python_prompts(analysis)
        documented_code = analysis.original_content
        
        for item in analysis.undocumented_items:
            response = await self._get_ai_response(prompts[item['name']])
            documented_code = self._insert_python_docs(documented_code, item, response)
        
        return documented_code

    async def _handle_javascript(self, analysis: FileAnalysis) -> str:
        """JavaScript-specific documentation generation"""
        prompts = self._build_js_prompts(analysis)
        documented_code = analysis.original_content
        
        for item in analysis.undocumented_items:
            response = await self._get_ai_response(prompts[item['name']])
            documented_code = self._insert_js_docs(documented_code, item, response)
        
        return documented_code

    async def _handle_typescript(self, analysis: FileAnalysis) -> str:
        """TypeScript-specific documentation generation"""
        prompts = self._build_ts_prompts(analysis)
        documented_code = analysis.original_content
        
        for item in analysis.undocumented_items:
            response = await self._get_ai_response(prompts[item['name']])
            documented_code = self._insert_ts_docs(documented_code, item, response)
        
        return documented_code

    async def _handle_generic(self, analysis: FileAnalysis) -> str:
        """Fallback for unsupported languages"""
        return analysis.original_content

    def _build_python_prompts(self, analysis: FileAnalysis) -> Dict[str, str]:
        """Build Python-specific prompts"""
        prompts = {}
        for item in analysis.undocumented_items:
            prompts[item['name']] = f"""
            Add comprehensive Python docstring to:
            {item['code']}
            
            Requirements:
            1. Google-style docstring format
            2. Describe purpose clearly
            3. Document all parameters with types
            4. Document return value with type
            5. Include 1-2 usage examples
            6. Mention exceptions if applicable
            """
        return prompts

    def _build_js_prompts(self, analysis: FileAnalysis) -> Dict[str, str]:
        """Build JavaScript-specific prompts"""
        prompts = {}
        for item in analysis.undocumented_items:
            prompts[item['name']] = f"""
            Add comprehensive JSDoc documentation to:
            {item['code']}
            
            Requirements:
            1. Proper JSDoc syntax with @ tags
            2. Describe function purpose
            3. Document all parameters with @param
            4. Document return value with @returns
            5. Include type information where possible
            6. Add 1 usage example
            """
        return prompts

    def _build_ts_prompts(self, analysis: FileAnalysis) -> Dict[str, str]:
        """Build TypeScript-specific prompts"""
        prompts = {}
        for item in analysis.undocumented_items:
            prompts[item['name']] = f"""
            Add comprehensive TypeScript documentation to:
            {item['code']}
            
            Requirements:
            1. TSDoc format with type information
            2. Describe function/class purpose
            3. Document all parameters with types
            4. Document return type
            5. Include generics if applicable
            6. Add 1 usage example
            7. Mark @public/@private appropriately
            """
        return prompts

    async def _get_ai_response(self, prompt: str) -> str:
        """Get response from AI model"""
        response = await openai.ChatCompletion.acreate(
            model="gpt-4",
            messages=[{
                "role": "system",
                "content": "You are a senior developer adding professional documentation to code."
            }, {
                "role": "user", 
                "content": prompt
            }],
            temperature=self.temperature,
            max_tokens=self.max_tokens
        )
        return response.choices[0].message.content

    def _insert_python_docs(self, code: str, item: dict, docs: str) -> str:
        """Insert Python docstrings"""
        lines = code.splitlines()
        insert_line = item['line'] - 1
        indent = ' ' * (len(lines[insert_line]) - len(lines[insert_line].lstrip()))
        docstring = f'{indent}"""{docs.strip()}\n{indent}"""'
        lines.insert(insert_line + 1, docstring)
        return '\n'.join(lines)

    def _insert_js_docs(self, code: str, item: dict, docs: str) -> str:
        """Insert JSDoc comments"""
        lines = code.splitlines()
        insert_line = item['line'] - 1
        indent = ' ' * (len(lines[insert_line]) - len(lines[insert_line].lstrip()))
        docstring = f'{indent}/**\n{indent} * {docs.strip().replace("\n", f"\n{indent} * ")}\n{indent} */'
        lines.insert(insert_line, docstring)
        return '\n'.join(lines)

    def _insert_ts_docs(self, code: str, item: dict, docs: str) -> str:
        """Insert TSDoc comments (similar to JSDoc but with stricter types)"""
        return self._insert_js_docs(code, item, docs)  # Similar format for now