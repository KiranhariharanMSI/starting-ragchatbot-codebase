import anthropic
from typing import List, Optional, Dict, Any
import logging
import os
try:
    import aisuite as ai  # Unified multi-LLM client
except Exception:
    ai = None

def mask_api_key(api_key: str) -> str:
    """Mask API key for logging purposes"""
    if not api_key or len(api_key) < 8:
        return "****"
    return f"{api_key[:4]}****{api_key[-4:]}"

class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant for course materials. You MUST always search the course database first before answering any question.

MANDATORY Search Protocol:
- **ALWAYS use the search tool first** for every question, regardless of topic
- Search for relevant course content before providing any response
- Only answer based on what you find in the search results
- If no relevant content is found, say "I don't have information about this in the available course materials"

Response Requirements:
- Base answers ONLY on course content found through search
- Do not use general knowledge - only use course materials
- Be specific and cite course details when available
- Keep responses focused and educational
- Do not mention the search process in your response

Remember: SEARCH FIRST, then answer based only on course materials found.
"""
    
    def __init__(self, config):
        """Initialize with provider routing using config.

        Preferred order: OpenAI -> Anthropic -> Google Gemini -> xAI Grok.
        Anthropic path retains tool-use integration. Others use AISuite.
        """
        self.logger = logging.getLogger(__name__)
        self.config = config

        # Determine provider
        openai_key = getattr(config, "OPENAI_API_KEY", os.getenv("OPENAI_API_KEY", ""))
        anthropic_key = getattr(config, "ANTHROPIC_API_KEY", os.getenv("ANTHROPIC_API_KEY", ""))
        google_key = getattr(config, "GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY", ""))
        xai_key = getattr(config, "XAI_API_KEY", os.getenv("XAI_API_KEY", ""))

        self.provider_mode = None  # "anthropic" or "aisuite"
        self.model = None

        if openai_key:
            # AISuite path with OpenAI
            if ai is None:
                raise RuntimeError("aisuite is not installed but OPENAI_API_KEY is set. Add 'aisuite' to dependencies.")
            self.provider_mode = "aisuite"
            self.client = ai.Client()
            self.model = f"openai:{getattr(config, 'OPENAI_MODEL', 'gpt-4o')}"
            self.logger.info("Using OpenAI provider with key: %s", mask_api_key(openai_key))
        elif anthropic_key:
            # Anthropic SDK path (keeps tool-use)
            self.provider_mode = "anthropic"
            self.client = anthropic.Anthropic(api_key=anthropic_key)
            self.model = getattr(config, 'ANTHROPIC_MODEL', 'claude-sonnet-4-20250514')
            self.logger.info("Using Anthropic provider with key: %s", mask_api_key(anthropic_key))
        elif google_key:
            # AISuite with Google Gemini
            if ai is None:
                raise RuntimeError("aisuite is not installed but GOOGLE_API_KEY is set. Add 'aisuite' to dependencies.")
            self.provider_mode = "aisuite"
            self.client = ai.Client()
            self.model = f"google:{getattr(config, 'GEMINI_MODEL', 'gemini-1.5-pro-002')}"
            self.logger.info("Using Google provider with key: %s", mask_api_key(google_key))
        elif xai_key:
            # AISuite with xAI Grok
            if ai is None:
                raise RuntimeError("aisuite is not installed but XAI_API_KEY is set. Add 'aisuite' to dependencies.")
            self.provider_mode = "aisuite"
            self.client = ai.Client()
            self.model = f"xai:{getattr(config, 'GROK_MODEL', 'grok-2-latest')}"
            self.logger.info("Using xAI provider with key: %s", mask_api_key(xai_key))
        else:
            self.logger.error("No supported LLM API keys found. Set OPENAI_API_KEY, ANTHROPIC_API_KEY, GOOGLE_API_KEY, or XAI_API_KEY.")
            raise ValueError("No supported LLM API keys found.")

        # Pre-build base API parameters (used for Anthropic)
        self.base_params = {
            "model": self.model if self.provider_mode == "anthropic" else None,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None) -> str:
        """
        Generate AI response with optional tool usage and conversation context.
        
        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            
        Returns:
            Generated response as string
        """
        
        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history 
            else self.SYSTEM_PROMPT
        )
        
        if self.provider_mode == "anthropic":
            # Prepare API call parameters efficiently
            api_params = {
                **self.base_params,
                "messages": [{"role": "user", "content": query}],
                "system": system_content
            }
            # Add tools if available (Anthropic tool_use)
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = {"type": "auto"}
            # Get response from Claude
            try:
                response = self.client.messages.create(**api_params)
                try:
                    text_preview = response.content[0].text if response and response.content else "<no content>"
                except Exception:
                    text_preview = "<unavailable>"
                self.logger.debug("Anthropic response received. stop_reason=%s, preview=%s", getattr(response, 'stop_reason', None), text_preview)
            except anthropic.APIStatusError as e:
                status = getattr(e, 'status_code', None)
                body = getattr(e, 'response', None)
                self.logger.exception("Anthropic APIStatusError during messages.create: status=%s, body=%s", status, body)
                raise
            except Exception:
                self.logger.exception("Unexpected error during Anthropic messages.create")
                raise
            if response.stop_reason == "tool_use" and tool_manager:
                return self._handle_tool_execution(response, api_params, tool_manager)
            return response.content[0].text
        else:
            # AISuite path (OpenAI/Gemini/xAI) with tool support
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": query},
            ]
            
            # Prepare API call parameters
            api_params = {
                "model": self.model,
                "messages": messages,
                "temperature": 0
            }
            
            # Add tools if available (OpenAI function calling format)
            if tools and tool_manager:
                api_params["tools"] = tools  # Tools are already in correct format from ToolManager
                api_params["tool_choice"] = "auto"
            
            try:
                response = self.client.chat.completions.create(**api_params)
                
                # Check if response contains tool calls
                if (response.choices and response.choices[0].message.tool_calls and tool_manager):
                    return self._handle_openai_tool_execution(response, api_params, tool_manager)
                
                # Regular response without tool calls
                text = response.choices[0].message.content if response and response.choices else ""
                return text
            except Exception:
                self.logger.exception("AISuite chat.completions.create failed for model %s", self.model)
                raise
    
    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                tool_result = tool_manager.execute_tool(
                    content_block.name, 
                    **content_block.input
                )
                
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        try:
            final_response = self.client.messages.create(**final_params)
            try:
                final_text_preview = final_response.content[0].text if final_response and final_response.content else "<no content>"
            except Exception:
                final_text_preview = "<unavailable>"
            self.logger.debug("Anthropic final response after tool use. preview=%s", final_text_preview)
            return final_response.content[0].text
        except anthropic.APIStatusError as e:
            status = getattr(e, 'status_code', None)
            body = getattr(e, 'response', None)
            self.logger.exception("Anthropic APIStatusError during follow-up messages.create: status=%s, body=%s", status, body)
            raise
        except Exception:
            self.logger.exception("Unexpected error during Anthropic follow-up messages.create")
            raise
    
    def _convert_tools_to_openai_format(self, anthropic_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Convert Anthropic tool definitions to OpenAI function calling format.
        
        Args:
            anthropic_tools: List of Anthropic tool definitions
            
        Returns:
            List of OpenAI tool definitions
        """
        openai_tools = []
        for tool in anthropic_tools:
            openai_tool = {
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool["description"],
                    "parameters": tool["input_schema"]
                }
            }
            openai_tools.append(openai_tool)
        return openai_tools
    
    def _handle_openai_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of OpenAI tool calls and get follow-up response.
        
        Args:
            initial_response: The response containing tool calls
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        import json
        
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool call response
        assistant_message = {
            "role": "assistant",
            "content": initial_response.choices[0].message.content,
            "tool_calls": initial_response.choices[0].message.tool_calls
        }
        messages.append(assistant_message)
        
        # Execute all tool calls and collect results
        for tool_call in initial_response.choices[0].message.tool_calls:
            try:
                # Parse tool call arguments
                function_args = json.loads(tool_call.function.arguments)
                
                # Execute the tool
                tool_result = tool_manager.execute_tool(
                    tool_call.function.name,
                    **function_args
                )
                
                # Add tool result message
                tool_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": tool_result
                }
                messages.append(tool_message)
                
            except Exception as e:
                self.logger.error("Error executing tool %s: %s", tool_call.function.name, str(e))
                # Add error message
                error_message = {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": f"Error executing tool: {str(e)}"
                }
                messages.append(error_message)
        
        # Prepare final API call without tools to get the final response
        final_params = {
            "model": base_params["model"],
            "messages": messages,
            "temperature": base_params["temperature"]
        }
        
        # Get final response
        try:
            final_response = self.client.chat.completions.create(**final_params)
            text = final_response.choices[0].message.content if final_response and final_response.choices else ""
            self.logger.debug("OpenAI final response after tool execution. preview=%s", text[:100] if text else "<no content>")
            return text
        except Exception:
            self.logger.exception("Error during OpenAI follow-up chat.completions.create")
            raise