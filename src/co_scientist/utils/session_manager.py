"""
Session Management Utilities - System State Reset and Management

This module handles session lifecycle management including comprehensive reset
functionality for fresh Co-Scientist runs with proper isolation.

Key Features:
- Comprehensive session reset
- Random seed management  
- Session ID generation
- Memory and state cleanup
- Integration with external systems
"""

import gc
import os
import time
import uuid
import random
import numpy as np


def comprehensive_session_reset() -> str:
    """
    Enhanced session reset for fresh Co-Scientist runs.
    
    Performs comprehensive cleanup including output manager reset, garbage collection,
    random seed reset, session ID generation, and external system state reset.
    
    Returns:
        str: Unique session identifier for this run
    """
    print("🔄 Starting comprehensive session reset...")
    
    # Reset output manager for fresh run
    from co_scientist.utils.output_manager import reset_output_manager
    reset_output_manager()
    
    # Force garbage collection to free memory
    gc.collect()
    print("  ✅ Forced garbage collection")
    
    # Reset random seeds for entropy
    session_entropy = int(time.time() * 1000000) % (2**31 - 1)
    random.seed(session_entropy)
    np.random.seed(session_entropy)
    print(f"  ✅ Reset random seeds: {session_entropy}")
    
    # Set unique session identifier
    unique_session_id = f"session_{uuid.uuid4().hex[:8]}_{int(time.time())}"
    os.environ['DEEP_SCI_FI_SESSION_ID'] = unique_session_id
    print(f"  ✅ Set session ID: {unique_session_id}")
    
    # Reset deep_researcher state if available
    try:
        from open_deep_research.deep_researcher import reset_deep_researcher_global_state
        reset_deep_researcher_global_state()
        print("  ✅ Reset deep_researcher state")
    except (ImportError, AttributeError):
        print("  ⚠️  Deep_researcher reset not available")
    
    print("🔄 Session reset completed\n")
    return unique_session_id


def get_session_id() -> str:
    """
    Get current session identifier.
    
    Returns:
        str: Current session ID or default if not set
    """
    return os.environ.get('DEEP_SCI_FI_SESSION_ID', 'default_session')


def set_random_seeds(seed: int = None) -> int:
    """
    Set random seeds for reproducible runs.
    
    Args:
        seed: Optional specific seed value, generates entropy-based if None
        
    Returns:
        int: The seed value that was set
    """
    if seed is None:
        seed = int(time.time() * 1000000) % (2**31 - 1)
    
    random.seed(seed)
    np.random.seed(seed)
    
    return seed


def cleanup_session_environment():
    """Clean up session-specific environment variables."""
    env_vars_to_clean = [
        'DEEP_SCI_FI_SESSION_ID',
        # Add other session-specific variables as needed
    ]
    
    for var in env_vars_to_clean:
        if var in os.environ:
            del os.environ[var] 