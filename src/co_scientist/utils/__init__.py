"""
Co-Scientist Utilities Package

This package contains all the utility modules that provide infrastructure functionality
for the Co-Scientist system, including LLM management, content formatting, and output handling.
"""

# Import the main classes for convenient access
from .llm_manager import LLMManager, create_default_llm_manager
from .output_manager import UnifiedOutputManager, get_output_manager, reset_output_manager
from .content_formatters import ContentFormatter, format_content
from .feedback_utils import get_critique_summary, get_comprehensive_feedback_summary
from .session_manager import comprehensive_session_reset, get_session_id, set_random_seeds
from .helper_functions import extract_integration_score, get_competing_scenarios

__all__ = [
    # LLM Management
    'LLMManager', 
    'create_default_llm_manager',
    
    # Output Management
    'UnifiedOutputManager', 
    'get_output_manager', 
    'reset_output_manager',
    
    # Content Formatting
    'ContentFormatter', 
    'format_content',
    
    # Feedback Utilities
    'get_critique_summary',
    'get_comprehensive_feedback_summary',
    
    # Session Management
    'comprehensive_session_reset',
    'get_session_id',
    'set_random_seeds',
    
    # Helper Functions
    'extract_integration_score',
    'get_competing_scenarios',
] 