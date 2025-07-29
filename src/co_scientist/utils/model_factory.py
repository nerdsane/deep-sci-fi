"""
Centralized Model Factory for Co-Scientist

This module provides a standardized way to create and manage LLM instances
across all co_scientist phases, eliminating hardcoded values and repetitive code.
"""

from typing import Any, Optional
from co_scientist.configuration import CoScientistConfiguration, ModelSettings
from co_scientist.utils.llm_manager import LLMManager


class ModelFactory:
    """
    Centralized factory for creating standardized model instances.
    
    This class eliminates scattered hardcoded values and provides a single
    point of configuration for all model creation across co_scientist phases.
    
    ModelFactory is the high-level, configuration-aware interface that
    delegates actual model creation to LLMManager.
    """
    
    def __init__(self, configuration: CoScientistConfiguration):
        """
        Initialize the ModelFactory with configuration.
        
        Args:
            configuration: CoScientistConfiguration containing model settings
        """
        self.configuration = configuration
        self.model_settings = configuration.model_settings
    
    def create_phase_model(
        self,
        phase: str,
        model_name: Optional[str] = None,
        isolated: bool = True,
        **override_params
    ) -> Any:
        """
        Create a model instance optimized for a specific phase.
        
        Args:
            phase: The phase name (e.g., 'meta_analysis', 'generation', 'debate')
            model_name: Override the default model (uses general_model if None)
            isolated: Whether to create an isolated instance (recommended for parallel tasks)
            **override_params: Any parameter overrides
            
        Returns:
            Configured model instance ready for use
        """
        # Create an LLMManager configured for this phase
        llm_manager = self.create_llm_manager(phase, model_name)
        
        # Apply any parameter overrides
        max_tokens = override_params.get('max_tokens', llm_manager.default_max_tokens)
        temperature = override_params.get('temperature', llm_manager.default_temperature)
        
        # Delegate to LLMManager for actual model creation
        if isolated:
            return llm_manager.create_isolated_instance(
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=temperature
            )
        else:
            return llm_manager.create_shared_instance(
                model_name=model_name,
                max_tokens=max_tokens,
                temperature=temperature
            )
    
    def create_llm_manager(
        self,
        phase: str,
        model_name: Optional[str] = None
    ) -> LLMManager:
        """
        Create an LLMManager instance configured for a specific phase.
        
        Args:
            phase: The phase name for appropriate settings
            model_name: Override the default model
            
        Returns:
            Configured LLMManager instance
        """
        if model_name is None:
            model_name = self.configuration.general_model
            
        temperature = self.model_settings.get_temperature_for_phase(phase, model_name)
        max_tokens = self.model_settings.get_max_tokens_for_phase(phase)
        
        return LLMManager(
            default_model=model_name,
            max_retries=self.model_settings.max_retries,
            base_delay=self.model_settings.base_delay,
            default_max_tokens=max_tokens,
            default_temperature=temperature
        )
    
    async def call_with_retry(
        self,
        phase: str,
        prompt: str,
        model_name: Optional[str] = None,
        system_message: Optional[str] = None,
        **override_params
    ) -> str:
        """
        Convenience method for simple phase-based LLM calls with retry logic.
        
        Args:
            phase: The phase name for appropriate settings
            prompt: The prompt to send to the model
            model_name: Override the default model
            system_message: Optional system message
            **override_params: Any parameter overrides
            
        Returns:
            Model response content
        """
        llm_manager = self.create_llm_manager(phase, model_name)
        
        return await llm_manager.call_with_prompt(
            prompt=prompt,
            model_name=model_name,
            system_message=system_message,
            **override_params
        )
    
    def get_phase_settings(self, phase: str) -> dict:
        """
        Get all settings for a specific phase.
        
        Args:
            phase: The phase name
            
        Returns:
            Dictionary containing all phase settings
        """
        model_name = self.configuration.general_model
        
        return {
            "model_name": model_name,
            "temperature": self.model_settings.get_temperature_for_phase(phase, model_name),
            "max_tokens": self.model_settings.get_max_tokens_for_phase(phase),
            "request_timeout": self.model_settings.request_timeout,
            "max_retries": self.model_settings.max_retries,
            "base_delay": self.model_settings.base_delay
        }


def create_model_factory(configuration: CoScientistConfiguration) -> ModelFactory:
    """
    Convenience function to create a ModelFactory from configuration.
    
    Args:
        configuration: CoScientistConfiguration instance
        
    Returns:
        Configured ModelFactory
    """
    return ModelFactory(configuration) 