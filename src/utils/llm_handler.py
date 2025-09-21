# src/utils/llm_handler.py
import logging
from typing import Dict, Type
from pydantic import BaseModel

# This handler uses the LangChain library to abstract LLM provider interactions.
from langchain_core.prompts import ChatPromptTemplate
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import AzureChatOpenAI

logger = logging.getLogger(__name__)


class LlmApiHandler:
    """
    A unified handler for interacting with multiple LLM providers using LangChain.

    This class acts as an abstraction layer that initializes a specific LLM client
    (e.g., Azure OpenAI, Google Gemini) based on a configuration dictionary. It
    provides a consistent interface for generating structured, Pydantic-validated
    outputs, regardless of the underlying LLM provider.
    """

    def __init__(self, config: Dict):
        """
        Initializes the LLM client from a single, self-contained config object.

        Args:
            config: A dictionary containing 'provider', 'model', and provider-specific
                    credentials like 'api_key' and 'endpoint'.
        
        Raises:
            ValueError: If the provider is unsupported or config is missing keys.
        """
        self.provider = config.get('provider', '').lower()
        if not self.provider:
            raise ValueError("LLM configuration must include a 'provider' key.")

        model_name = config.get("model")
        if not model_name:
            raise ValueError(f"Configuration for provider '{self.provider}' must include a 'model' key.")
        
        self.model = None

        # --- Provider-Specific Initialization ---
        if self.provider == 'google':
            self.model = ChatGoogleGenerativeAI(
                model=model_name,
                google_api_key=config.get("api_key")
            )
        elif self.provider == 'azure':
            self.model = AzureChatOpenAI(
                api_key=config.get("api_key"),
                azure_endpoint=config.get("endpoint"),
                api_version=config.get("version"),
                azure_deployment=model_name
            )
        else:
            raise ValueError(f"Unsupported LLM provider: {self.provider}")
        
        logger.info(f"Initialized LlmApiHandler for provider: {self.provider} (Model: {model_name})")

    def generate_structured_content(self, prompt: str, pydantic_schema: Type[BaseModel], generation_params: Dict) -> BaseModel:
        """
        Generates structured content that is validated against a Pydantic schema.

        This method leverages LangChain's `with_structured_output` feature to reliably
        parse the LLM's JSON output into a Pydantic object, preventing errors from
        malformed responses.

        Args:
            prompt: The user-facing prompt to send to the LLM.
            pydantic_schema: The Pydantic class to validate the output against.
            generation_params: A dictionary of runtime parameters for the LLM
                               (e.g., 'temperature').

        Returns:
            An instance of the provided pydantic_schema, populated by the LLM.
        
        Raises:
            Exception: If the LangChain invocation or Pydantic parsing fails.
        """
        try:
            # Bind runtime parameters (e.g., temperature) to the model instance.
            model_with_runtime_params = self.model.bind(**generation_params)
            
            # Instruct the model to structure its output according to the Pydantic schema.
            structured_llm = model_with_runtime_params.with_structured_output(pydantic_schema)
            
            prompt_template = ChatPromptTemplate.from_template("{user_prompt}")
            
            # Create the LangChain Expression Language (LCEL) chain.
            chain = prompt_template | structured_llm
            
            result = chain.invoke({"user_prompt": prompt})
            return result
        except Exception as e:
            logger.error(f"LangChain structured content generation failed: {e}", exc_info=True)
            raise
