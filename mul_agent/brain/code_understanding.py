"""Code Understanding Module - 代码理解模块

提供代码 AST 分析、依赖图生成、代码语义理解能力
"""

import ast
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field


@dataclass
class CodeEntity:
    """代码实体基类"""
    name: str
    file: str
    line_start: int
    line_end: int
    docstring: Optional[str] = None
    decorators: List[str] = field(default_factory=list)


@dataclass
class FunctionEntity(CodeEntity):
    """函数实体"""
    args: List[str] = field(default_factory=list)
    returns: Optional[str] = None
    body_type: str = ""  # 'simple', 'complex', 'generator'
    calls: List[str] = field(default_factory=list)  # 调用的函数


@dataclass
class ClassEntity(CodeEntity):
    """类实体"""
    bases: List[str] = field(default_factory=list)
    methods: List[str] = field(default_factory=list)
    attributes: List[str] = field(default_factory=list)


@dataclass
class ModuleEntity:
    """模块实体"""
    file: str
    imports: List[str] = field(default_factory=list)
    from_imports: Dict[str, List[str]] = field(default_factory=dict)
    functions: List[FunctionEntity] = field(default_factory=list)
    classes: List[ClassEntity] = field(default_factory=list)
    variables: List[str] = field(default_factory=list)


class PythonASTAnalyzer:
    """Python AST 分析器"""

    def __init__(self):
        self.entities: Dict[str, ModuleEntity] = {}
        self.symbol_table: Dict[str, CodeEntity] = {}

    def analyze_file(self, file_path: Path) -> ModuleEntity:
        """分析单个 Python 文件"""
        with open(file_path, 'r', encoding='utf-8') as f:
            source = f.read()

        tree = ast.parse(source, filename=str(file_path))
        module = ModuleEntity(file=str(file_path))

        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                func = self._parse_function(node)
                module.functions.append(func)
                self.symbol_table[func.name] = func

            elif isinstance(node, ast.ClassDef):
                cls = self._parse_class(node)
                module.classes.append(cls)
                self.symbol_table[cls.name] = cls

            elif isinstance(node, ast.Import):
                for alias in node.names:
                    module.imports.append(alias.name)

            elif isinstance(node, ast.ImportFrom):
                if module.file not in module.from_imports:
                    module.from_imports[module.file] = []
                if node.module:
                    for alias in node.names:
                        module.from_imports.setdefault(node.module, []).append(alias.name)

            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        module.variables.append(target.id)

        self.entities[str(file_path)] = module
        return module

    def analyze_directory(self, dir_path: Path, pattern: str = "*.py") -> List[ModuleEntity]:
        """分析目录下所有 Python 文件"""
        modules = []
        for py_file in dir_path.rglob(pattern):
            if "__pycache__" in str(py_file):
                continue
            try:
                module = self.analyze_file(py_file)
                modules.append(module)
            except Exception as e:
                print(f"Error analyzing {py_file}: {e}")
        return modules

    def _parse_function(self, node: ast.FunctionDef) -> FunctionEntity:
        """解析函数节点"""
        args = [arg.arg for arg in node.args.args if arg.arg != 'self']

        # 获取函数体类型
        body_type = self._analyze_function_body(node)

        # 获取调用的函数
        calls = self._extract_calls(node)

        return FunctionEntity(
            name=node.name,
            file="",  # 会在 analyze_file 中设置
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            args=args,
            returns=self._get_return_type(node.returns),
            body_type=body_type,
            calls=calls
        )

    def _parse_class(self, node: ast.ClassDef) -> ClassEntity:
        """解析类节点"""
        bases = [base.id if isinstance(base, ast.Name) else str(base)
                 for base in node.bases]

        methods = []
        attributes = []

        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                methods.append(item.name)
            elif isinstance(item, ast.Assign):
                for target in item.targets:
                    if isinstance(target, ast.Name):
                        attributes.append(target.id)

        return ClassEntity(
            name=node.name,
            file="",
            line_start=node.lineno,
            line_end=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
            decorators=[self._get_decorator_name(d) for d in node.decorator_list],
            bases=bases,
            methods=methods,
            attributes=attributes
        )

    def _analyze_function_body(self, node: ast.FunctionDef) -> str:
        """分析函数体复杂度"""
        body = node.body

        # 检查是否是生成器
        for child in ast.walk(node):
            if isinstance(child, ast.Yield) or isinstance(child, ast.YieldFrom):
                return "generator"

        # 计算复杂度
        complexity = 0
        for child in ast.walk(node):
            if isinstance(child, (ast.If, ast.For, ast.While, ast.Try, ast.With)):
                complexity += 1

        if complexity > 5:
            return "complex"
        return "simple"

    def _extract_calls(self, node: ast.FunctionDef) -> List[str]:
        """提取函数调用的名称"""
        calls = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                if isinstance(child.func, ast.Name):
                    calls.append(child.func.id)
                elif isinstance(child.func, ast.Attribute):
                    calls.append(child.func.attr)
        return list(set(calls))

    def _get_decorator_name(self, decorator: ast.expr) -> str:
        """获取装饰器名称"""
        if isinstance(decorator, ast.Name):
            return decorator.id
        elif isinstance(decorator, ast.Call):
            if isinstance(decorator.func, ast.Name):
                return decorator.func.id
        return str(decorator)

    def _get_return_type(self, returns: Optional[ast.expr]) -> Optional[str]:
        """获取返回类型注解"""
        if returns is None:
            return None
        if isinstance(returns, ast.Name):
            return returns.id
        elif isinstance(returns, ast.Subscript):
            if isinstance(returns.value, ast.Name):
                return f"{returns.value.id}[...]"
        return str(returns)

    def get_dependency_graph(self) -> Dict[str, Set[str]]:
        """生成依赖图"""
        graph: Dict[str, Set[str]] = {}

        for file_path, module in self.entities.items():
            module_name = Path(file_path).stem
            graph[module_name] = set()

            # 添加模块级依赖
            for imp in module.imports:
                graph[module_name].add(imp)

            # 添加函数调用依赖
            for func in module.functions:
                for call in func.calls:
                    # 查找被调用的函数在哪个模块
                    if call in self.symbol_table:
                        entity = self.symbol_table[call]
                        dep_module = Path(entity.file).stem
                        graph[module_name].add(dep_module)

        return graph

    def find_symbol(self, name: str) -> Optional[CodeEntity]:
        """查找符号定义"""
        return self.symbol_table.get(name)

    def find_usages(self, name: str) -> List[Tuple[str, int]]:
        """查找符号使用位置"""
        usages = []

        for file_path, module in self.entities.items():
            source = open(file_path, 'r').read()
            lines = source.split('\n')

            for i, line in enumerate(lines, 1):
                if name in line and f"def {name}" not in line and f"class {name}" not in line:
                    usages.append((file_path, i))

        return usages


class CodeUnderstandingHandler:
    """代码理解处理器 - 供 Router 调用"""

    def __init__(self):
        self.analyzer = PythonASTAnalyzer()

    def analyze(self, path: str) -> Dict[str, Any]:
        """分析代码路径"""
        path_obj = Path(path)

        if path_obj.is_file():
            module = self.analyzer.analyze_file(path_obj)
            return self._format_module_result(module)
        elif path_obj.is_dir():
            modules = self.analyzer.analyze_directory(path_obj)
            return self._format_directory_result(modules, path_obj)

        return {"status": "error", "message": "Invalid path"}

    def get_dependencies(self, path: str) -> Dict[str, Any]:
        """获取依赖图"""
        path_obj = Path(path)
        self.analyzer.analyze_directory(path_obj)
        graph = self.analyzer.get_dependency_graph()

        return {
            "status": "success",
            "graph": {k: list(v) for k, v in graph.items()}
        }

    def find_symbol(self, name: str, path: str = ".") -> Dict[str, Any]:
        """查找符号"""
        path_obj = Path(path)
        self.analyzer.analyze_directory(path_obj)

        entity = self.analyzer.find_symbol(name)
        if entity:
            return {
                "status": "success",
                "symbol": {
                    "name": entity.name,
                    "file": entity.file,
                    "line": entity.line_start,
                    "type": type(entity).__name__.replace("Entity", "")
                }
            }

        return {"status": "error", "message": f"Symbol '{name}' not found"}

    def find_usages(self, name: str, path: str = ".") -> Dict[str, Any]:
        """查找符号使用"""
        path_obj = Path(path)
        self.analyzer.analyze_directory(path_obj)

        usages = self.analyzer.find_usages(name)
        return {
            "status": "success",
            "symbol": name,
            "usages": [{"file": f, "line": l} for f, l in usages],
            "count": len(usages)
        }

    def _format_module_result(self, module: ModuleEntity) -> Dict[str, Any]:
        """格式化模块分析结果"""
        return {
            "status": "success",
            "module": {
                "file": module.file,
                "imports": module.imports,
                "functions": [
                    {"name": f.name, "line": f.line_start, "args": f.args}
                    for f in module.functions
                ],
                "classes": [
                    {"name": c.name, "line": c.line_start, "methods": c.methods}
                    for c in module.classes
                ],
                "variables": module.variables
            }
        }

    def _format_directory_result(self, modules: List[ModuleEntity], path: Path) -> Dict[str, Any]:
        """格式化目录分析结果"""
        summary = {
            "status": "success",
            "path": str(path),
            "total_files": len(modules),
            "total_functions": sum(len(m.functions) for m in modules),
            "total_classes": sum(len(m.classes) for m in modules),
            "modules": []
        }

        for module in modules:
            rel_path = Path(module.file).relative_to(path)
            summary["modules"].append({
                "file": str(rel_path),
                "functions": len(module.functions),
                "classes": len(module.classes)
            })

        return summary


# 导出全局实例
code_understanding = CodeUnderstandingHandler()
