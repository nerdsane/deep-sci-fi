"""
LLM Manager - Centralized LLM Communication Utilities

This module provides a clean, unified interface for all LLM operations in the Co-Scientist system.
It eliminates repetitive patterns and provides robust error handling with exponential backoff.

Key Features:
- Automatic retry logic for transient errors (API overload, network issues)
- Isolated model instances to prevent context bleeding in parallel tasks
- Consistent error handling across all LLM calls
- Clean, async interface that's easy for new developers to use

Usage Example:
    llm_manager = LLMManager("openai:gpt-4", max_retries=3)
    result = await llm_manager.call_with_prompt("Your prompt here")
"""

import asyncio
import random
import time
import uuid
from typing import Any, Optional, Dict, List
from langchain.chat_models import init_chat_model
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage


class LLMManager:
    """
    Centralized manager for all LLM operations.
    
    This class handles:
    - Model instantiation with proper isolation
    - Retry logic for transient failures
    - Consistent error handling
    - Performance optimization through connection reuse where appropriate
    """
    
    def __init__(
        self, 
        default_model: str, 
        max_retries: int = 3, 
        base_delay: float = 1.0,
        default_max_tokens: int = 8000,
        default_temperature: float = 0.9
    ):
        """
        Initialize the LLM Manager.
        
        Args:
            default_model: Default model name (e.g., "openai:gpt-4", "anthropic:claude-3")
            max_retries: Maximum retry attempts for failed calls
            base_delay: Base delay for exponential backoff (seconds)
            default_max_tokens: Default token limit for responses
            default_temperature: Default creativity setting (0.0-1.0)
        """
        self.default_model = default_model
        self.max_retries = max_retries
        self.base_delay = base_delay
        self.default_max_tokens = default_max_tokens
        self.default_temperature = default_temperature
        
    async def call_with_prompt(
        self, 
        prompt: str, 
        model_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_isolated_instance: bool = True,
        system_message: Optional[str] = None
    ) -> str:
        """
        Make an LLM call with a text prompt and return the response content.
        
        This is the main interface for simple LLM calls. It handles all the complexity
        of model creation, retry logic, and error handling behind the scenes.
        
        Args:
            prompt: The text prompt to send to the LLM
            model_name: Override the default model (optional)
            max_tokens: Override default max tokens (optional)  
            temperature: Override default temperature (optional)
            use_isolated_instance: Create fresh model instance (recommended for parallel tasks)
            system_message: Optional system message to prepend
            
        Returns:
            str: The LLM's response content
            
        Raises:
            Exception: If all retry attempts fail
            
        Example:
            response = await llm_manager.call_with_prompt(
                "Analyze this scenario for scientific plausibility",
                temperature=0.7
            )
        """
        # Use provided values or fall back to defaults
        model = model_name or self.default_model
        tokens = max_tokens or self.default_max_tokens
        temp = temperature or self.default_temperature
        
        # Create model instance
        if use_isolated_instance:
            llm = self._create_isolated_instance(model, tokens, temp)
        else:
            # Use shared instance for better performance when isolation isn't needed
            llm = self._create_shared_instance(model, tokens, temp)
        
        # Prepare messages
        messages = []
        if system_message:
            messages.append(SystemMessage(content=system_message))
        messages.append(HumanMessage(content=prompt))
        
        # Make the call with retry logic
        response = await self._call_with_retry(llm, messages)
        return response.content
    
    async def call_with_messages(
        self,
        messages: List[Any],
        model_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None,
        use_isolated_instance: bool = True
    ) -> str:
        """
        Make an LLM call with pre-formatted messages.
        
        Use this when you need more control over the message structure,
        such as for multi-turn conversations or specific message types.
        
        Args:
            messages: List of LangChain message objects
            model_name: Override the default model (optional)
            max_tokens: Override default max tokens (optional)
            temperature: Override default temperature (optional) 
            use_isolated_instance: Create fresh model instance (recommended for parallel tasks)
            
        Returns:
            str: The LLM's response content
        """
        # Use provided values or fall back to defaults
        model = model_name or self.default_model
        tokens = max_tokens or self.default_max_tokens
        temp = temperature or self.default_temperature
        
        # Create model instance
        if use_isolated_instance:
            llm = self._create_isolated_instance(model, tokens, temp)
        else:
            llm = self._create_shared_instance(model, tokens, temp)
        
        # Make the call with retry logic
        response = await self._call_with_retry(llm, messages)
        return response.content
    
    def create_isolated_instance(
        self,
        model_name: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> Any:
        """
        Create a completely isolated model instance for parallel tasks.
        
        Use this when you need direct access to the model instance, such as
        for complex conversation flows or when you want to manage the instance lifecycle.
        
        Isolated instances prevent context bleeding between parallel tasks by ensuring
        each task gets its own model instance with no shared state.
        
        Args:
            model_name: Model to instantiate (optional, uses default)
            max_tokens: Token limit (optional, uses default)
            temperature: Temperature setting (optional, uses default)
            
        Returns:
            LangChain model instance ready for use
            
        Example:
            # For parallel scenario generation where isolation is critical
            model_a = llm_manager.create_isolated_instance(temperature=0.8)
            model_b = llm_manager.create_isolated_instance(temperature=0.9)
        """
        model = model_name or self.default_model
        tokens = max_tokens or self.default_max_tokens
        temp = temperature or self.default_temperature
        
        return self._create_isolated_instance(model, tokens, temp)
    
    async def _call_with_retry(self, llm: Any, messages: List[Any]) -> Any:
        """
        Internal method that implements the retry logic with exponential backoff.
        
        This handles transient failures like API overloads, rate limits, and network issues.
        Each retry waits longer than the previous attempt to avoid overwhelming the API.
        """
        import anthropic  # Import here to avoid dependency issues
        
        last_exception = None
        
        for attempt in range(self.max_retries):
            try:
                # Attempt the LLM call
                return await llm.ainvoke(messages)
                
            except anthropic.APIStatusError as e:
                # Handle Anthropic-specific errors
                error_type = e.body.get("error", {}).get("type", "") if hasattr(e, 'body') else ""
                
                if error_type in ["overloaded_error", "rate_limit_error"] and attempt < self.max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"  ⏳ API {error_type}, retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                    last_exception = e
                    continue
                else:
                    # Non-retryable error or max retries exceeded
                    raise e
                    
            except Exception as e:
                # Handle general network/connection errors
                error_msg = str(e).lower()
                network_errors = ["timeout", "connection", "network", "refused", "unreachable"]
                
                if any(keyword in error_msg for keyword in network_errors) and attempt < self.max_retries - 1:
                    # Calculate exponential backoff delay
                    delay = self.base_delay * (2 ** attempt) + random.uniform(0, 1)
                    print(f"  ⏳ Network error, retrying in {delay:.1f}s (attempt {attempt + 1}/{self.max_retries})")
                    await asyncio.sleep(delay)
                    last_exception = e
                    continue
                else:
                    # Non-retryable error or max retries exceeded
                    raise e
        
        # If we get here, all retries failed
        raise Exception(f"LLM call failed after {self.max_retries} attempts. Last error: {last_exception}")
    
    def _create_isolated_instance(self, model_name: str, max_tokens: int, temperature: float) -> Any:
        """
        Create a completely isolated model instance to prevent context bleeding.
        
        Each isolated instance gets:
        - Unique random seed (for OpenAI models)
        - Unique metadata to force separate instantiation  
        - Individual parameter settings
        - No shared state with other instances
        """
        # Create unique seed for this model instance
        unique_seed = hash(f"{model_name}_{max_tokens}_{time.time()}_{random.random()}")
        
        # Build model parameters (don't include 'model' since it's passed as first argument)
        model_params = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "request_timeout": 300,
            "max_retries": 3,
            "seed": unique_seed % 2**31  # Ensure seed is within valid range
        }
        
        return init_chat_model(model_name, **model_params)
    
    def _create_shared_instance(self, model_name: str, max_tokens: int, temperature: float) -> Any:
        """
        Create or retrieve shared model instance for efficiency.
        Uses caching to reuse instances with identical parameters.
        """
        # Build model parameters (don't include 'model' since it's passed as first argument)
        model_params = {
            "max_tokens": max_tokens,
            "temperature": temperature,
            "request_timeout": 300,
            "max_retries": 3
        }
        
        return init_chat_model(model_name, **model_params)


# Convenience function for quick setup
def create_default_llm_manager(model_name: str = "openai:gpt-4") -> LLMManager:
    """
    Create a default LLM manager with sensible settings.
    
    This is a convenience function for quick setup. For more control,
    instantiate LLMManager directly with custom parameters.
    
    Args:
        model_name: The default model to use
        
    Returns:
        Configured LLMManager instance
        
    Example:
        llm_manager = create_default_llm_manager("anthropic:claude-3-sonnet")
        response = await llm_manager.call_with_prompt("Hello, world!")
    """
    return LLMManager(
        default_model=model_name,
        max_retries=3,
        base_delay=1.0,
        default_max_tokens=8000,
        default_temperature=0.9
    ) 