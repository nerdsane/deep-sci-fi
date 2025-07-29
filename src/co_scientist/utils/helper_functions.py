"""
Helper Functions - General Utility Functions

This module contains general utility functions used throughout the Co-Scientist
system for various data processing and analysis tasks.

Key Features:
- Integration score extraction
- Scenario comparison utilities
- Text processing helpers
- Data validation functions
"""

import re
from typing import Dict, List, Any


def extract_integration_score(content: str) -> int:
    """
    Extract integration score from world integration analysis content.
    
    Looks for various patterns indicating integration scores in LLM outputs
    and returns a normalized score between 1-10.
    
    Args:
        content: Text content containing integration analysis
        
    Returns:
        int: Integration score between 1-10, defaults to 5 if not found
    """
    patterns = [
        r"integration score[:\s]+(\d+)",
        r"world integration[:\s]+(\d+)",
        r"score[:\s]+(\d+)",
        r"(\d+)/10"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, content.lower())
        if match:
            score = min(int(match.group(1)), 10)
            return max(score, 1)  # Ensure minimum score of 1
    
    return 5  # Default moderate integration score


def get_competing_scenarios(target_scenario: Dict[str, Any], all_scenarios: List[Dict[str, Any]]) -> str:
    """
    Get competing scenarios for inspiration and comparison.
    
    Extracts up to 3 competing scenarios (excluding the target) and formats
    them for use in evolution or comparison processes.
    
    Args:
        target_scenario: The scenario to find competitors for
        all_scenarios: Complete list of scenarios to search
        
    Returns:
        str: Formatted summary of competing scenarios
    """
    competing = [s for s in all_scenarios if s["scenario_id"] != target_scenario["scenario_id"]]
    
    if not competing:
        return "No competing scenarios available."
    
    summary = "Competing approaches for inspiration:\n"
    for i, scenario in enumerate(competing[:3]):
        summary += f"\nApproach {i+1} ({scenario['research_direction']}):\n"
        content = scenario.get("scenario_content", "")
        summary += content + "\n"
    
    return summary


def clean_text_content(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text content
        
    Returns:
        str: Cleaned text content
    """
    if not text:
        return ""
    
    # Remove excessive whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove markdown artifacts that might interfere
    text = text.replace("**", "").replace("###", "").replace("##", "")
    
    return text.strip()


def validate_scenario_data(scenario: Dict[str, Any]) -> bool:
    """
    Validate that scenario data contains required fields.
    
    Args:
        scenario: Scenario dictionary to validate
        
    Returns:
        bool: True if scenario has required fields
    """
    required_fields = ["scenario_id", "research_direction"]
    return all(field in scenario for field in required_fields)


def extract_numeric_score(text: str, default: float = 0.0) -> float:
    """
    Extract a numeric score from text content.
    
    Args:
        text: Text content potentially containing scores
        default: Default value if no score found
        
    Returns:
        float: Extracted numeric score or default
    """
    if not text:
        return default
    
    # Look for patterns like "score: 8.5" or "rating: 7/10"
    patterns = [
        r"score[:\s]+(\d+(?:\.\d+)?)",
        r"rating[:\s]+(\d+(?:\.\d+)?)",
        r"(\d+(?:\.\d+)?)/\d+",
        r"(\d+(?:\.\d+)?)%"
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text.lower())
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                continue
    
    return default


def format_list_as_text(items: List[str], separator: str = ", ") -> str:
    """
    Format a list of items as readable text.
    
    Args:
        items: List of string items
        separator: Separator between items
        
    Returns:
        str: Formatted text representation
    """
    if not items:
        return "None"
    
    if len(items) == 1:
        return items[0]
    elif len(items) == 2:
        return f"{items[0]} and {items[1]}"
    else:
        return f"{separator.join(items[:-1])}, and {items[-1]}"


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to a maximum length with optional suffix.
    
    Args:
        text: Text to truncate
        max_length: Maximum allowed length
        suffix: Suffix to add if truncated
        
    Returns:
        str: Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix 