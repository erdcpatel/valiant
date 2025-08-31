from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass, field
from enum import Enum
import re


class InputType(Enum):
    TEXT = "text"
    PASSWORD = "password"
    NUMBER = "number"
    BOOLEAN = "boolean"
    SELECT = "select"
    DATE = "date"
    CHECKBOX = "checkbox"


@dataclass
class InputField:
    name: str
    type: InputType
    label: str
    required: bool = True
    default: Any = None
    help_text: Optional[str] = None
    options: Optional[List[str]] = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    validation_regex: Optional[str] = None
    validation_message: Optional[str] = None
    
    def validate_value(self, value: Any) -> Tuple[bool, str]:
        """Validate a value against this field's constraints"""
        if self.required and (value is None or value == ""):
            return False, f"{self.label} is required"
        
        if value is None or value == "":
            return True, ""
        
        if self.type == InputType.NUMBER:
            try:
                num_value = float(value)
                if self.min_value is not None and num_value < self.min_value:
                    return False, f"{self.label} must be at least {self.min_value}"
                if self.max_value is not None and num_value > self.max_value:
                    return False, f"{self.label} must be at most {self.max_value}"
            except (ValueError, TypeError):
                return False, f"{self.label} must be a valid number"
        
        elif self.type == InputType.SELECT:
            if self.options and str(value) not in self.options:
                return False, f"{self.label} must be one of: {', '.join(self.options)}"
        
        if self.validation_regex:
            if not re.match(self.validation_regex, str(value)):
                message = self.validation_message or f"{self.label} format is invalid"
                return False, message
        
        return True, ""


@dataclass
class WorkflowMetadata:
    """Metadata for workflow documentation and discovery"""
    name: str = "Unnamed Workflow"
    description: str = "No description"
    version: str = "1.0.0"
    author: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = None
    documentation_url: Optional[str] = None
    estimated_duration: Optional[str] = None
    complexity_level: str = "medium"  # low, medium, high
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metadata to dictionary for serialization"""
        return {
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "tags": self.tags,
            "category": self.category,
            "documentation_url": self.documentation_url,
            "estimated_duration": self.estimated_duration,
            "complexity_level": self.complexity_level
        }


class BaseWorkflow:
    """
    Base class for all workflows.
    
    Provides the foundation for both legacy workflows and enhanced workflows
    with decorator support. Maintains full backward compatibility.
    """
    
    name = "Unnamed Workflow"
    description = "No description"
    
    def __init__(self):
        """Initialize the base workflow"""
        self._metadata: Optional[WorkflowMetadata] = None
    
    def get_metadata(self) -> WorkflowMetadata:
        """Get workflow metadata"""
        if self._metadata is None:
            self._metadata = WorkflowMetadata(
                name=self.name,
                description=self.description
            )
        return self._metadata
    
    def set_metadata(self, metadata: WorkflowMetadata):
        """Set workflow metadata"""
        self._metadata = metadata
        # Update class attributes for backward compatibility
        self.name = metadata.name
        self.description = metadata.description

    def get_input_fields(self) -> List[InputField]:
        """
        Define input fields required by this workflow.
        
        This is the preferred method for defining inputs in new workflows.
        Falls back to get_required_inputs() for backward compatibility.
        """
        try:
            return self._get_input_fields_impl()
        except NotImplementedError:
            # Fall back to legacy method for backward compatibility
            try:
                old_inputs = self.get_required_inputs()
                return [
                    InputField(
                        name=key,
                        type=InputType.PASSWORD if is_secret else InputType.TEXT,
                        label=prompt.replace(':', '').strip(),
                        default=""
                    )
                    for prompt, key, is_secret in old_inputs
                ]
            except NotImplementedError:
                return []
    
    def _get_input_fields_impl(self) -> List[InputField]:
        """
        Override this method to define input fields in new workflows.
        This method is separate to allow proper fallback to legacy inputs.
        """
        raise NotImplementedError()

    def get_required_inputs(self) -> List[Tuple[str, str, bool]]:
        """
        Legacy method for defining inputs.
        
        Returns list of (prompt, key, is_secret) tuples.
        Maintained for backward compatibility.
        """
        raise NotImplementedError("Workflows must implement get_required_inputs() for CLI compatibility")

    def validate_inputs(self, inputs: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        Validate workflow inputs against field constraints.
        
        Args:
            inputs: Dictionary of input values
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []
        input_fields = self.get_input_fields()
        
        for field in input_fields:
            value = inputs.get(field.name)
            is_valid, error_message = field.validate_value(value)
            if not is_valid:
                errors.append(error_message)
        
        return len(errors) == 0, errors

    def setup(self):
        """Initialize workflow with context values"""
        pass

    def define_steps(self):
        """Define the sequence of steps for this workflow"""
        raise NotImplementedError("Workflows must implement define_steps()")
    
    def get_step_count(self) -> int:
        """Get the estimated number of steps in this workflow"""
        return 0
    
    def get_estimated_duration(self) -> Optional[str]:
        """Get estimated workflow duration"""
        metadata = self.get_metadata()
        return metadata.estimated_duration
    
    def get_tags(self) -> List[str]:
        """Get workflow tags for categorization"""
        metadata = self.get_metadata()
        return metadata.tags
    
    def add_tag(self, tag: str):
        """Add a tag to the workflow"""
        metadata = self.get_metadata()
        if tag not in metadata.tags:
            metadata.tags.append(tag)
    
    def get_documentation_url(self) -> Optional[str]:
        """Get URL to workflow documentation"""
        metadata = self.get_metadata()
        return metadata.documentation_url
