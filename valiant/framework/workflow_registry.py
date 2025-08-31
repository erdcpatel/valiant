"""
Enhanced workflow registry with metadata support and discovery capabilities.

This module provides an enhanced registry system for workflows with support for
metadata, categorization, and automatic discovery of workflow capabilities.
"""

from typing import Dict, List, Type, Optional, Any, Tuple
from dataclasses import dataclass, field
import importlib
import inspect
import os
from pathlib import Path

from .workflow import BaseWorkflow, WorkflowMetadata


@dataclass
class WorkflowRegistryEntry:
    """Entry in the workflow registry"""
    name: str
    workflow_class: Type[BaseWorkflow]
    module_path: str
    metadata: WorkflowMetadata
    is_enhanced: bool = False
    step_count: int = 0
    input_count: int = 0
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert registry entry to dictionary"""
        return {
            "name": self.name,
            "module_path": self.module_path,
            "metadata": self.metadata.to_dict(),
            "is_enhanced": self.is_enhanced,
            "step_count": self.step_count,
            "input_count": self.input_count,
            "tags": self.tags,
            "category": self.category
        }


class EnhancedWorkflowRegistry:
    """
    Enhanced workflow registry with metadata support and discovery capabilities.
    
    Provides advanced features for workflow management including:
    - Automatic workflow discovery
    - Metadata extraction and indexing
    - Category-based organization
    - Search and filtering capabilities
    - Validation and health checks
    """
    
    def __init__(self):
        self._workflows: Dict[str, WorkflowRegistryEntry] = {}
        self._categories: Dict[str, List[str]] = {}
        self._tags: Dict[str, List[str]] = {}
    
    def register_workflow(
        self,
        name: str,
        workflow_class: Type[BaseWorkflow],
        module_path: str = "",
        force: bool = False
    ) -> bool:
        """
        Register a workflow in the registry.
        
        Args:
            name: Unique workflow name
            workflow_class: Workflow class
            module_path: Module path where workflow is defined
            force: Whether to overwrite existing registration
            
        Returns:
            True if registration successful, False if name already exists and force=False
        """
        if name in self._workflows and not force:
            return False
        
        try:
            workflow_instance = workflow_class()
            metadata = workflow_instance.get_metadata()
            
            try:
                from .enhanced_workflow import EnhancedBaseWorkflow
                is_enhanced = isinstance(workflow_instance, EnhancedBaseWorkflow)
            except ImportError:
                is_enhanced = False
            
            step_count = 0
            input_count = len(workflow_instance.get_input_fields())
            
            if is_enhanced:
                try:
                    from .enhanced_workflow import EnhancedBaseWorkflow
                    if isinstance(workflow_instance, EnhancedBaseWorkflow):
                        step_metadata = workflow_instance.get_step_metadata()
                        step_count = len(step_metadata)
                except:
                    step_count = 0
            
            entry = WorkflowRegistryEntry(
                name=name,
                workflow_class=workflow_class,
                module_path=module_path,
                metadata=metadata,
                is_enhanced=is_enhanced,
                step_count=step_count,
                input_count=input_count,
                tags=metadata.tags,
                category=metadata.category
            )
            
            self._workflows[name] = entry
            
            if metadata.category:
                if metadata.category not in self._categories:
                    self._categories[metadata.category] = []
                if name not in self._categories[metadata.category]:
                    self._categories[metadata.category].append(name)
            
            for tag in metadata.tags:
                if tag not in self._tags:
                    self._tags[tag] = []
                if name not in self._tags[tag]:
                    self._tags[tag].append(name)
            
            return True
            
        except Exception as e:
            print(f"Failed to register workflow {name}: {str(e)}")
            return False
    
    def unregister_workflow(self, name: str) -> bool:
        """
        Unregister a workflow from the registry.
        
        Args:
            name: Workflow name to unregister
            
        Returns:
            True if unregistration successful, False if workflow not found
        """
        if name not in self._workflows:
            return False
        
        entry = self._workflows[name]
        
        if entry.category and entry.category in self._categories:
            if name in self._categories[entry.category]:
                self._categories[entry.category].remove(name)
            if not self._categories[entry.category]:
                del self._categories[entry.category]
        
        for tag in entry.tags:
            if tag in self._tags and name in self._tags[tag]:
                self._tags[tag].remove(name)
            if tag in self._tags and not self._tags[tag]:
                del self._tags[tag]
        
        del self._workflows[name]
        
        return True
    
    def get_workflow(self, name: str) -> Optional[Type[BaseWorkflow]]:
        """Get workflow class by name"""
        entry = self._workflows.get(name)
        return entry.workflow_class if entry else None
    
    def get_workflow_entry(self, name: str) -> Optional[WorkflowRegistryEntry]:
        """Get full workflow registry entry by name"""
        return self._workflows.get(name)
    
    def list_workflows(self) -> List[str]:
        """Get list of all registered workflow names"""
        return list(self._workflows.keys())
    
    def list_workflows_by_category(self, category: str) -> List[str]:
        """Get list of workflow names in a specific category"""
        return self._categories.get(category, [])
    
    def list_workflows_by_tag(self, tag: str) -> List[str]:
        """Get list of workflow names with a specific tag"""
        return self._tags.get(tag, [])
    
    def get_categories(self) -> List[str]:
        """Get list of all categories"""
        return list(self._categories.keys())
    
    def get_tags(self) -> List[str]:
        """Get list of all tags"""
        return list(self._tags.keys())
    
    def search_workflows(
        self,
        query: str = "",
        category: Optional[str] = None,
        tags: Optional[List[str]] = None,
        is_enhanced: Optional[bool] = None
    ) -> List[WorkflowRegistryEntry]:
        """
        Search workflows by various criteria.
        
        Args:
            query: Text search in name and description
            category: Filter by category
            tags: Filter by tags (workflow must have all specified tags)
            is_enhanced: Filter by enhanced workflow type
            
        Returns:
            List of matching workflow entries
        """
        results = []
        
        for entry in self._workflows.values():
            if query:
                query_lower = query.lower()
                if (query_lower not in entry.name.lower() and 
                    query_lower not in entry.metadata.description.lower()):
                    continue
            
            if category and entry.category != category:
                continue
            
            if tags:
                if not all(tag in entry.tags for tag in tags):
                    continue
            
            if is_enhanced is not None and entry.is_enhanced != is_enhanced:
                continue
            
            results.append(entry)
        
        results.sort(key=lambda x: x.name)
        return results
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """Get statistics about registered workflows"""
        total_workflows = len(self._workflows)
        enhanced_workflows = sum(1 for entry in self._workflows.values() if entry.is_enhanced)
        legacy_workflows = total_workflows - enhanced_workflows
        
        total_steps = sum(entry.step_count for entry in self._workflows.values())
        total_inputs = sum(entry.input_count for entry in self._workflows.values())
        
        return {
            "total_workflows": total_workflows,
            "enhanced_workflows": enhanced_workflows,
            "legacy_workflows": legacy_workflows,
            "total_categories": len(self._categories),
            "total_tags": len(self._tags),
            "total_steps": total_steps,
            "total_inputs": total_inputs,
            "average_steps_per_workflow": total_steps / total_workflows if total_workflows > 0 else 0,
            "average_inputs_per_workflow": total_inputs / total_workflows if total_workflows > 0 else 0
        }
    
    def validate_registry(self) -> Tuple[bool, List[str]]:
        """
        Validate all registered workflows.
        
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        
        for name, entry in self._workflows.items():
            try:
                workflow_instance = entry.workflow_class()
                
                input_fields = workflow_instance.get_input_fields()
                for field in input_fields:
                    if not field.name:
                        errors.append(f"Workflow {name} has input field with empty name")
                
                if entry.is_enhanced:
                    try:
                        from .enhanced_workflow import EnhancedBaseWorkflow
                        if isinstance(workflow_instance, EnhancedBaseWorkflow):
                            is_valid, workflow_errors = workflow_instance.validate_workflow()
                            if not is_valid:
                                errors.extend([f"Workflow {name}: {error}" for error in workflow_errors])
                    except ImportError:
                        pass
                
            except Exception as e:
                errors.append(f"Failed to validate workflow {name}: {str(e)}")
        
        return len(errors) == 0, errors
    
    def auto_discover_workflows(self, base_path: str, package_prefix: str = "") -> int:
        """
        Automatically discover and register workflows from a directory.
        
        Args:
            base_path: Base directory to search for workflows
            package_prefix: Python package prefix for imports
            
        Returns:
            Number of workflows discovered and registered
        """
        discovered_count = 0
        base_path_obj = Path(base_path)
        
        if not base_path_obj.exists():
            return 0
        
        for py_file in base_path_obj.rglob("*.py"):
            if py_file.name.startswith("__"):
                continue
            
            try:
                relative_path = py_file.relative_to(base_path_obj)
                module_parts = list(relative_path.parts[:-1]) + [relative_path.stem]
                
                if package_prefix:
                    module_path = f"{package_prefix}.{'.'.join(module_parts)}"
                else:
                    module_path = '.'.join(module_parts)
                
                module = importlib.import_module(module_path)
                
                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (issubclass(obj, BaseWorkflow) and 
                        obj != BaseWorkflow):
                        
                        workflow_name = name.replace("Workflow", "").lower()
                        
                        if self.register_workflow(workflow_name, obj, module_path):
                            discovered_count += 1
                
            except Exception as e:
                print(f"Failed to discover workflows in {py_file}: {str(e)}")
                continue
        
        return discovered_count
    
    def export_registry(self) -> Dict[str, Any]:
        """Export registry data for serialization"""
        return {
            "workflows": {name: entry.to_dict() for name, entry in self._workflows.items()},
            "categories": self._categories,
            "tags": self._tags,
            "statistics": self.get_workflow_statistics()
        }


workflow_registry = EnhancedWorkflowRegistry()


def register_workflow(name: str, workflow_class: Type[BaseWorkflow], module_path: str = "") -> bool:
    """Convenience function to register a workflow"""
    return workflow_registry.register_workflow(name, workflow_class, module_path)


def get_workflow(name: str) -> Optional[Type[BaseWorkflow]]:
    """Convenience function to get a workflow class"""
    return workflow_registry.get_workflow(name)


def list_workflows() -> List[str]:
    """Convenience function to list all workflows"""
    return workflow_registry.list_workflows()


def search_workflows(**kwargs) -> List[WorkflowRegistryEntry]:
    """Convenience function to search workflows"""
    return workflow_registry.search_workflows(**kwargs)
