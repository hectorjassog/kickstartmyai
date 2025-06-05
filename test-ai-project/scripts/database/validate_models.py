"""Validate that all models are properly imported in models/__init__.py"""

import ast
import sys
from pathlib import Path
from typing import List, Set

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


class ModelValidator:
    """Validates model imports and exports."""
    
    def __init__(self, models_dir: Path = None):
        if models_dir is None:
            models_dir = Path(__file__).parent.parent.parent / "app" / "models"
        self.models_dir = models_dir
        self.init_file = models_dir / "__init__.py"
    
    def get_model_files(self) -> List[Path]:
        """Get all Python model files (excluding __init__.py)."""
        return [
            f for f in self.models_dir.glob("*.py") 
            if f.name != "__init__.py" and not f.name.startswith("_")
        ]
    
    def extract_classes_from_file(self, file_path: Path) -> Set[str]:
        """Extract class names from a Python file."""
        try:
            with open(file_path, 'r') as f:
                tree = ast.parse(f.read())
            
            classes = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    # Only include classes that likely inherit from Base or are enums
                    if any(isinstance(base, ast.Name) and base.id in ['Base', 'Enum'] 
                           for base in node.bases):
                        classes.add(node.name)
                    elif any(isinstance(base, ast.Attribute) and base.attr in ['Enum'] 
                             for base in node.bases):
                        classes.add(node.name)
            
            return classes
        except Exception as e:
            print(f"Warning: Could not parse {file_path}: {e}")
            return set()
    
    def extract_imports_from_init(self) -> dict:
        """Extract imports and __all__ from __init__.py"""
        if not self.init_file.exists():
            return {"imports": {}, "all_exports": set()}
        
        try:
            with open(self.init_file, 'r') as f:
                tree = ast.parse(f.read())
            
            imports = {}  # module -> set of imported names
            all_exports = set()
            
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom) and node.module:
                    # Handle: from .user import User, UserRole
                    module = node.module.lstrip('.')
                    imported_names = set()
                    
                    for alias in node.names:
                        imported_names.add(alias.name)
                    
                    imports[module] = imported_names
                
                elif isinstance(node, ast.Assign):
                    # Handle: __all__ = ["User", "UserRole", ...]
                    for target in node.targets:
                        if isinstance(target, ast.Name) and target.id == "__all__":
                            if isinstance(node.value, ast.List):
                                for elt in node.value.elts:
                                    if isinstance(elt, ast.Str):
                                        all_exports.add(elt.s)
                                    elif isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                        all_exports.add(elt.value)
            
            return {"imports": imports, "all_exports": all_exports}
        
        except Exception as e:
            print(f"Warning: Could not parse __init__.py: {e}")
            return {"imports": {}, "all_exports": set()}
    
    def validate_models(self) -> dict:
        """Validate all models are properly imported and exported."""
        model_files = self.get_model_files()
        init_data = self.extract_imports_from_init()
        
        results = {
            "valid": True,
            "missing_imports": [],
            "missing_exports": [],
            "unused_exports": [],
            "model_summary": {}
        }
        
        # Collect all classes from model files
        all_model_classes = set()
        for model_file in model_files:
            module_name = model_file.stem
            classes = self.extract_classes_from_file(model_file)
            results["model_summary"][module_name] = classes
            all_model_classes.update(classes)
        
        # Check imports
        imported_classes = set()
        for module, classes in init_data["imports"].items():
            imported_classes.update(classes)
            
            # Check if module file exists
            module_file = self.models_dir / f"{module}.py"
            if not module_file.exists():
                results["missing_imports"].append(f"Module {module} imported but file not found")
                results["valid"] = False
        
        # Check exports
        exported_classes = init_data["all_exports"]
        
        # Find missing imports (classes in files but not imported)
        missing_imports = all_model_classes - imported_classes
        if missing_imports:
            results["missing_imports"].extend(list(missing_imports))
            results["valid"] = False
        
        # Find missing exports (imported but not in __all__)
        missing_exports = imported_classes - exported_classes
        if missing_exports:
            results["missing_exports"].extend(list(missing_exports))
            results["valid"] = False
        
        # Find unused exports (in __all__ but not imported)
        unused_exports = exported_classes - imported_classes
        if unused_exports:
            results["unused_exports"].extend(list(unused_exports))
            # This is a warning, not an error
        
        return results
    
    def generate_fixed_init(self) -> str:
        """Generate a corrected __init__.py content."""
        model_files = self.get_model_files()
        
        imports = []
        all_exports = []
        
        for model_file in model_files:
            module_name = model_file.stem
            classes = self.extract_classes_from_file(model_file)
            
            if classes:
                class_list = ", ".join(sorted(classes))
                imports.append(f"from .{module_name} import {class_list}")
                all_exports.extend(sorted(classes))
        
        content = '"""Database models."""\n\n'
        content += "\n".join(imports)
        content += "\n\n__all__ = [\n"
        
        for export in sorted(all_exports):
            content += f'    "{export}",\n'
        
        content += "]\n"
        
        return content


def validate_models_cli():
    """Command line interface for model validation."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Validate model imports")
    parser.add_argument(
        "--fix", 
        action="store_true", 
        help="Generate fixed __init__.py content"
    )
    parser.add_argument(
        "--write-fix", 
        action="store_true", 
        help="Write the fixed __init__.py content to file"
    )
    
    args = parser.parse_args()
    
    validator = ModelValidator()
    results = validator.validate_models()
    
    print("🔍 Model Import Validation")
    print("=" * 30)
    
    if results["valid"]:
        print("✅ All models are properly imported and exported!")
    else:
        print("❌ Model import issues found:")
        
        if results["missing_imports"]:
            print("\n🔴 Missing imports:")
            for missing in results["missing_imports"]:
                print(f"  - {missing}")
        
        if results["missing_exports"]:
            print("\n🔴 Missing from __all__:")
            for missing in results["missing_exports"]:
                print(f"  - {missing}")
    
    if results["unused_exports"]:
        print("\n🟡 Unused exports in __all__:")
        for unused in results["unused_exports"]:
            print(f"  - {unused}")
    
    # Show model summary
    print(f"\n📊 Found models:")
    for module, classes in results["model_summary"].items():
        if classes:
            print(f"  {module}.py: {', '.join(sorted(classes))}")
    
    if args.fix or args.write_fix:
        fixed_content = validator.generate_fixed_init()
        
        if args.write_fix:
            init_file = validator.init_file
            with open(init_file, 'w') as f:
                f.write(fixed_content)
            print(f"\n✅ Fixed __init__.py written to {init_file}")
        else:
            print("\n🔧 Suggested __init__.py content:")
            print("-" * 40)
            print(fixed_content)
    
    return 0 if results["valid"] else 1


if __name__ == "__main__":
    sys.exit(validate_models_cli())
