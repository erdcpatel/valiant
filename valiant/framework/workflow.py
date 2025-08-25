from typing import Dict, List, Tuple, Any, Optional, Union
from dataclasses import dataclass
from enum import Enum


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


class BaseWorkflow:
    name = "Unnamed Workflow"
    description = "No description"

    def get_input_fields(self) -> List[InputField]:
        """Define input fields required by this workflow (NEW optional method)"""
        # Default implementation converts old format to new format for backward compatibility
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

    def get_required_inputs(self) -> List[Tuple[str, str, bool]]:
        """Original method - must be implemented by workflows for backward compatibility"""
        raise NotImplementedError("Workflows must implement get_required_inputs() for CLI compatibility")

    def setup(self):
        """Initialize workflow with context values"""
        pass

    def define_steps(self):
        """Define the sequence of steps for this workflow"""
        raise NotImplementedError("Workflows must implement define_steps()")