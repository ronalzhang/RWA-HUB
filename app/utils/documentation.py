"""
文档和注释工具
提供代码文档生成和注释标准化功能
"""

import inspect
import ast
from typing import Dict, List, Any, Optional, Callable
from datetime import datetime
import json


class CodeDocumenter:
    """代码文档生成器"""
    
    @staticmethod
    def generate_function_doc(func: Callable, include_examples: bool = True) -> str:
        """
        生成函数文档
        
        Args:
            func: 要生成文档的函数
            include_examples: 是否包含使用示例
            
        Returns:
            str: 生成的文档字符串
        """
        # 获取函数签名
        sig = inspect.signature(func)
        
        # 获取现有文档
        existing_doc = inspect.getdoc(func) or ""
        
        # 构建文档
        doc_parts = []
        
        # 函数描述
        if existing_doc:
            doc_parts.append(existing_doc)
        else:
            doc_parts.append(f"{func.__name__} 函数")
        
        doc_parts.append("")
        
        # 参数说明
        if sig.parameters:
            doc_parts.append("Args:")
            for param_name, param in sig.parameters.items():
                param_type = param.annotation if param.annotation != inspect.Parameter.empty else "Any"
                default = f" = {param.default}" if param.default != inspect.Parameter.empty else ""
                doc_parts.append(f"    {param_name} ({param_type}){default}: 参数描述")
            doc_parts.append("")
        
        # 返回值说明
        if sig.return_annotation != inspect.Signature.empty:
            doc_parts.append("Returns:")
            doc_parts.append(f"    {sig.return_annotation}: 返回值描述")
            doc_parts.append("")
        
        # 异常说明
        doc_parts.append("Raises:")
        doc_parts.append("    Exception: 异常描述")
        doc_parts.append("")
        
        # 使用示例
        if include_examples:
            doc_parts.append("Example:")
            doc_parts.append(f"    >>> {func.__name__}()")
            doc_parts.append("    # 示例输出")
            doc_parts.append("")
        
        return "\n".join(doc_parts)
    
    @staticmethod
    def generate_class_doc(cls: type) -> str:
        """
        生成类文档
        
        Args:
            cls: 要生成文档的类
            
        Returns:
            str: 生成的文档字符串
        """
        doc_parts = []
        
        # 类描述
        existing_doc = inspect.getdoc(cls) or f"{cls.__name__} 类"
        doc_parts.append(existing_doc)
        doc_parts.append("")
        
        # 属性说明
        doc_parts.append("Attributes:")
        for attr_name in dir(cls):
            if not attr_name.startswith('_'):
                attr = getattr(cls, attr_name)
                if not callable(attr):
                    doc_parts.append(f"    {attr_name}: 属性描述")
        doc_parts.append("")
        
        # 方法说明
        doc_parts.append("Methods:")
        for method_name in dir(cls):
            if not method_name.startswith('_'):
                method = getattr(cls, method_name)
                if callable(method):
                    doc_parts.append(f"    {method_name}(): 方法描述")
        doc_parts.append("")
        
        return "\n".join(doc_parts)
    
    @staticmethod
    def generate_module_doc(module_path: str) -> str:
        """
        生成模块文档
        
        Args:
            module_path: 模块文件路径
            
        Returns:
            str: 生成的文档字符串
        """
        try:
            with open(module_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 解析AST
            tree = ast.parse(content)
            
            doc_parts = []
            
            # 模块描述
            if ast.get_docstring(tree):
                doc_parts.append(ast.get_docstring(tree))
            else:
                doc_parts.append(f"模块: {module_path}")
            doc_parts.append("")
            
            # 导入说明
            imports = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        imports.append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    module = node.module or ""
                    for alias in node.names:
                        imports.append(f"{module}.{alias.name}")
            
            if imports:
                doc_parts.append("Imports:")
                for imp in sorted(set(imports)):
                    doc_parts.append(f"    {imp}")
                doc_parts.append("")
            
            # 函数和类说明
            functions = []
            classes = []
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    functions.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    classes.append(node.name)
            
            if classes:
                doc_parts.append("Classes:")
                for cls in sorted(set(classes)):
                    doc_parts.append(f"    {cls}: 类描述")
                doc_parts.append("")
            
            if functions:
                doc_parts.append("Functions:")
                for func in sorted(set(functions)):
                    doc_parts.append(f"    {func}(): 函数描述")
                doc_parts.append("")
            
            return "\n".join(doc_parts)
            
        except Exception as e:
            return f"生成模块文档失败: {str(e)}"


class CommentStandardizer:
    """注释标准化工具"""
    
    # 标准注释模板
    COMMENT_TEMPLATES = {
        'function': {
            'zh': [
                "# {description}",
                "# 参数: {params}",
                "# 返回: {returns}",
                "# 异常: {raises}"
            ],
            'en': [
                "# {description}",
                "# Args: {params}",
                "# Returns: {returns}",
                "# Raises: {raises}"
            ]
        },
        'class': {
            'zh': [
                "# {description}",
                "# 属性: {attributes}",
                "# 方法: {methods}"
            ],
            'en': [
                "# {description}",
                "# Attributes: {attributes}",
                "# Methods: {methods}"
            ]
        },
        'section': {
            'zh': [
                "# " + "=" * 50,
                "# {title}",
                "# " + "=" * 50
            ],
            'en': [
                "# " + "=" * 50,
                "# {title}",
                "# " + "=" * 50
            ]
        }
    }
    
    @staticmethod
    def generate_section_comment(title: str, language: str = 'zh') -> str:
        """
        生成章节注释
        
        Args:
            title: 章节标题
            language: 语言 ('zh' 或 'en')
            
        Returns:
            str: 生成的章节注释
        """
        template = CommentStandardizer.COMMENT_TEMPLATES['section'][language]
        return "\n".join(template).format(title=title)
    
    @staticmethod
    def generate_function_comment(func_name: str, description: str = "", 
                                params: str = "", returns: str = "", 
                                raises: str = "", language: str = 'zh') -> str:
        """
        生成函数注释
        
        Args:
            func_name: 函数名
            description: 函数描述
            params: 参数说明
            returns: 返回值说明
            raises: 异常说明
            language: 语言
            
        Returns:
            str: 生成的函数注释
        """
        template = CommentStandardizer.COMMENT_TEMPLATES['function'][language]
        
        comment_parts = []
        for line in template:
            if '{description}' in line and description:
                comment_parts.append(line.format(description=description))
            elif '{params}' in line and params:
                comment_parts.append(line.format(params=params))
            elif '{returns}' in line and returns:
                comment_parts.append(line.format(returns=returns))
            elif '{raises}' in line and raises:
                comment_parts.append(line.format(raises=raises))
        
        return "\n".join(comment_parts)
    
    @staticmethod
    def generate_todo_comment(task: str, priority: str = "NORMAL", 
                            assignee: str = "", deadline: str = "") -> str:
        """
        生成TODO注释
        
        Args:
            task: 任务描述
            priority: 优先级 (LOW, NORMAL, HIGH, URGENT)
            assignee: 负责人
            deadline: 截止日期
            
        Returns:
            str: 生成的TODO注释
        """
        comment_parts = [f"# TODO: {task}"]
        
        if priority != "NORMAL":
            comment_parts.append(f"# Priority: {priority}")
        
        if assignee:
            comment_parts.append(f"# Assignee: {assignee}")
        
        if deadline:
            comment_parts.append(f"# Deadline: {deadline}")
        
        comment_parts.append(f"# Created: {datetime.now().strftime('%Y-%m-%d')}")
        
        return "\n".join(comment_parts)
    
    @staticmethod
    def generate_fixme_comment(issue: str, severity: str = "MEDIUM") -> str:
        """
        生成FIXME注释
        
        Args:
            issue: 问题描述
            severity: 严重程度 (LOW, MEDIUM, HIGH, CRITICAL)
            
        Returns:
            str: 生成的FIXME注释
        """
        return f"# FIXME: {issue} (Severity: {severity}) - {datetime.now().strftime('%Y-%m-%d')}"
    
    @staticmethod
    def generate_hack_comment(reason: str, temporary: bool = True) -> str:
        """
        生成HACK注释
        
        Args:
            reason: 使用hack的原因
            temporary: 是否是临时方案
            
        Returns:
            str: 生成的HACK注释
        """
        temp_note = " (TEMPORARY)" if temporary else ""
        return f"# HACK: {reason}{temp_note} - {datetime.now().strftime('%Y-%m-%d')}"


class APIDocGenerator:
    """API文档生成器"""
    
    @staticmethod
    def generate_endpoint_doc(route: str, method: str, description: str,
                            params: List[Dict] = None, responses: List[Dict] = None,
                            examples: List[Dict] = None) -> str:
        """
        生成API端点文档
        
        Args:
            route: 路由路径
            method: HTTP方法
            description: 端点描述
            params: 参数列表
            responses: 响应列表
            examples: 示例列表
            
        Returns:
            str: 生成的API文档
        """
        doc_parts = []
        
        # 端点标题
        doc_parts.append(f"## {method.upper()} {route}")
        doc_parts.append("")
        doc_parts.append(description)
        doc_parts.append("")
        
        # 参数说明
        if params:
            doc_parts.append("### 参数")
            doc_parts.append("")
            doc_parts.append("| 参数名 | 类型 | 必填 | 描述 |")
            doc_parts.append("|--------|------|------|------|")
            
            for param in params:
                required = "是" if param.get('required', False) else "否"
                doc_parts.append(f"| {param['name']} | {param['type']} | {required} | {param['description']} |")
            
            doc_parts.append("")
        
        # 响应说明
        if responses:
            doc_parts.append("### 响应")
            doc_parts.append("")
            
            for response in responses:
                doc_parts.append(f"#### {response['status']} - {response['description']}")
                doc_parts.append("")
                
                if response.get('schema'):
                    doc_parts.append("```json")
                    doc_parts.append(json.dumps(response['schema'], indent=2, ensure_ascii=False))
                    doc_parts.append("```")
                    doc_parts.append("")
        
        # 使用示例
        if examples:
            doc_parts.append("### 示例")
            doc_parts.append("")
            
            for example in examples:
                doc_parts.append(f"#### {example['title']}")
                doc_parts.append("")
                
                if example.get('request'):
                    doc_parts.append("**请求:**")
                    doc_parts.append("```bash")
                    doc_parts.append(example['request'])
                    doc_parts.append("```")
                    doc_parts.append("")
                
                if example.get('response'):
                    doc_parts.append("**响应:**")
                    doc_parts.append("```json")
                    doc_parts.append(json.dumps(example['response'], indent=2, ensure_ascii=False))
                    doc_parts.append("```")
                    doc_parts.append("")
        
        return "\n".join(doc_parts)
    
    @staticmethod
    def generate_model_doc(model_name: str, fields: List[Dict]) -> str:
        """
        生成数据模型文档
        
        Args:
            model_name: 模型名称
            fields: 字段列表
            
        Returns:
            str: 生成的模型文档
        """
        doc_parts = []
        
        # 模型标题
        doc_parts.append(f"## {model_name}")
        doc_parts.append("")
        
        # 字段说明
        doc_parts.append("| 字段名 | 类型 | 必填 | 描述 |")
        doc_parts.append("|--------|------|------|------|")
        
        for field in fields:
            required = "是" if field.get('required', False) else "否"
            doc_parts.append(f"| {field['name']} | {field['type']} | {required} | {field['description']} |")
        
        doc_parts.append("")
        
        # 示例
        doc_parts.append("### 示例")
        doc_parts.append("")
        doc_parts.append("```json")
        
        example = {}
        for field in fields:
            if field['type'] == 'string':
                example[field['name']] = "示例字符串"
            elif field['type'] == 'integer':
                example[field['name']] = 123
            elif field['type'] == 'number':
                example[field['name']] = 123.45
            elif field['type'] == 'boolean':
                example[field['name']] = True
            elif field['type'] == 'array':
                example[field['name']] = []
            elif field['type'] == 'object':
                example[field['name']] = {}
            else:
                example[field['name']] = None
        
        doc_parts.append(json.dumps(example, indent=2, ensure_ascii=False))
        doc_parts.append("```")
        doc_parts.append("")
        
        return "\n".join(doc_parts)


# 便捷函数
def add_section_comment(title: str, language: str = 'zh') -> str:
    """添加章节注释"""
    return CommentStandardizer.generate_section_comment(title, language)


def add_todo(task: str, priority: str = "NORMAL", assignee: str = "", deadline: str = "") -> str:
    """添加TODO注释"""
    return CommentStandardizer.generate_todo_comment(task, priority, assignee, deadline)


def add_fixme(issue: str, severity: str = "MEDIUM") -> str:
    """添加FIXME注释"""
    return CommentStandardizer.generate_fixme_comment(issue, severity)


def add_hack(reason: str, temporary: bool = True) -> str:
    """添加HACK注释"""
    return CommentStandardizer.generate_hack_comment(reason, temporary)


# 使用示例：
# 
# # 添加章节注释
# print(add_section_comment("数据库操作"))
# 
# # 添加TODO
# print(add_todo("优化查询性能", "HIGH", "张三", "2024-02-01"))
# 
# # 添加FIXME
# print(add_fixme("内存泄漏问题", "CRITICAL"))
# 
# # 生成函数文档
# documenter = CodeDocumenter()
# print(documenter.generate_function_doc(some_function))