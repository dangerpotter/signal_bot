# shared_utils.py

import requests
import logging
import openai

# Logger for this module (used by Gemini Interactions API)
logger = logging.getLogger(__name__)
import time
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from urllib.parse import quote as url_quote
from dotenv import load_dotenv
import base64
from openai import OpenAI
import re
try:
    from bs4 import BeautifulSoup
except ImportError:
    print("BeautifulSoup not found. Please install it with 'pip install beautifulsoup4'")

# Load environment variables
load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))


def _add_openrouter_transforms(payload: dict) -> dict:
    """Add OpenRouter message transforms if enabled.

    Middle-out compression automatically handles prompts that exceed
    the model's context size by removing/truncating messages from the middle.
    Also handles Anthropic's max 100 messages limit.
    """
    try:
        from config import OPENROUTER_MIDDLE_OUT_ENABLED
        if OPENROUTER_MIDDLE_OUT_ENABLED:
            payload["transforms"] = ["middle-out"]
    except ImportError:
        pass  # Config not available, skip transforms
    return payload


def call_openrouter_api_structured(
    prompt: str,
    model: str,
    system_prompt: str,
    json_schema: dict,
    schema_name: str = "response",
    conversation_history: Optional[list] = None
) -> dict | None:
    """Call OpenRouter API with guaranteed JSON schema response.

    Uses structured outputs to ensure the response matches the provided JSON schema.
    No JSON parsing retry logic needed - responses are guaranteed valid.

    Args:
        prompt: The user message/prompt
        model: Model ID (e.g., 'anthropic/claude-sonnet-4')
        system_prompt: System prompt for the model
        json_schema: JSON Schema dict defining the response structure
        schema_name: Name for the schema (used in response_format)
        conversation_history: Optional list of previous messages

    Returns:
        Parsed JSON dict on success, None on error
    """
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "HTTP-Referer": "http://localhost:3000",
            "Content-Type": "application/json",
            "X-Title": "AI Conversation"
        }

        # Normalize model ID for OpenRouter
        openrouter_model = model
        if model.startswith("claude-") and not model.startswith("anthropic/"):
            openrouter_model = f"anthropic/{model}"

        # Build messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        if conversation_history:
            for msg in conversation_history:
                if msg.get("role") != "system":
                    content = msg.get("content", "")
                    # Flatten structured content to text
                    if isinstance(content, list):
                        text_parts = [p.get('text', '') for p in content if p.get('type') == 'text']
                        content = ' '.join(text_parts)
                    messages.append({"role": msg.get("role", "user"), "content": content})

        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": openrouter_model,
            "messages": messages,
            "temperature": 0.7,  # Lower temp for more consistent structured output
            "max_tokens": 2000,
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema_name,
                    "strict": True,
                    "schema": json_schema
                }
            }
        }
        _add_openrouter_transforms(payload)

        print(f"[OpenRouter Structured] Model: {openrouter_model}, Schema: {schema_name}")

        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        if response.status_code == 200:
            response_data = response.json()
            if 'choices' in response_data and len(response_data['choices']) > 0:
                content = response_data['choices'][0].get('message', {}).get('content', '')
                if content:
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        print(f"[OpenRouter Structured] JSON parse error (shouldn't happen): {e}")
                        print(f"[OpenRouter Structured] Content: {content[:500]}")
                        # Fallback: Try to extract JSON from response if model returned markdown/text
                        import re
                        json_match = re.search(r'\{[^{}]*\}', content)
                        if json_match:
                            try:
                                extracted = json.loads(json_match.group())
                                print(f"[OpenRouter Structured] Fallback JSON extraction succeeded")
                                return extracted
                            except json.JSONDecodeError:
                                pass
                        return None
            print("[OpenRouter Structured] No content in response")
            return None
        else:
            print(f"[OpenRouter Structured] Error {response.status_code}: {response.text[:500]}")
            return None

    except requests.exceptions.Timeout:
        print("[OpenRouter Structured] Request timed out")
        return None
    except Exception as e:
        print(f"[OpenRouter Structured] Error: {e}")
        return None


def call_gemini_api_structured(
    prompt: str,
    model: str,
    system_prompt: str,
    json_schema: dict,
    schema_name: str = "response",
    thinking_level: str = "low"
) -> dict | None:
    """Call Gemini GenerateContent API with guaranteed JSON schema response.

    Uses the stable generateContent API (not Interactions API) with structured outputs
    to ensure the response matches the provided JSON schema.

    Args:
        prompt: The user message/prompt
        model: Gemini model ID (e.g., 'gemini-3-flash-preview')
        system_prompt: System prompt for the model
        json_schema: JSON Schema dict defining the response structure
        schema_name: Name for logging (not used in API)
        thinking_level: Reasoning depth - 'low' recommended for simple classification

    Returns:
        Parsed JSON dict on success, None on error
    """
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if not api_key:
        print("[Gemini Structured] Error: No API key. Set GEMINI_API_KEY in .env")
        return None

    try:
        # Build contents in Gemini format
        contents = [
            {
                "role": "user",
                "parts": [{"text": prompt}]
            }
        ]

        # Build generation config with structured output
        # For generateContent API: use responseMimeType + responseJsonSchema in generationConfig
        # No maxOutputTokens - let model use its default (64k for Gemini 3 Pro)
        generation_config = {
            "temperature": 0.7,
            "responseMimeType": "application/json",
            "responseJsonSchema": json_schema
        }

        # Add thinking config for Gemini 3 models
        # Use specified thinking level (default "low" to minimize token usage)
        if "gemini-3" in model or "gemini-2.5" in model:
            generation_config["thinkingConfig"] = {"thinkingLevel": thinking_level}

        # Build payload
        payload = {
            "contents": contents,
            "generationConfig": generation_config
        }

        # Add system instruction if provided
        if system_prompt:
            payload["systemInstruction"] = {
                "parts": [{"text": system_prompt}]
            }

        # API endpoint - use generateContent instead of Interactions API
        endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }

        print(f"[Gemini Structured] Model: {model}, Schema: {schema_name}")
        print(f"[Gemini Structured] Using generateContent API")
        # Debug: log generation config keys
        print(f"[Gemini Structured] GenerationConfig keys: {list(generation_config.keys())}")

        response = requests.post(endpoint, headers=headers, json=payload, timeout=60)
        print(f"[Gemini Structured] Response status: {response.status_code}")

        if response.status_code == 200:
            response_data = response.json()

            # Extract text from candidates
            candidates = response_data.get("candidates", [])
            if not candidates:
                print("[Gemini Structured] No candidates in response")
                print(f"[Gemini Structured] Full response: {json.dumps(response_data)[:1000]}")
                return None

            # Get first candidate's content
            candidate = candidates[0]
            finish_reason = candidate.get("finishReason", "unknown")
            content = candidate.get("content", {})
            parts = content.get("parts", [])

            # Debug: log finish reason and candidate info
            print(f"[Gemini Structured] Finish reason: {finish_reason}")
            if finish_reason != "STOP":
                # Log safety ratings if present
                safety_ratings = candidate.get("safetyRatings", [])
                if safety_ratings:
                    print(f"[Gemini Structured] Safety ratings: {safety_ratings}")
                print(f"[Gemini Structured] Full candidate: {json.dumps(candidate)[:1000]}")

            for part in parts:
                text_content = part.get("text", "")
                if text_content:
                    try:
                        return json.loads(text_content)
                    except json.JSONDecodeError as e:
                        print(f"[Gemini Structured] JSON parse error: {e}")
                        print(f"[Gemini Structured] Content: {text_content[:500]}")
                        return None

            print("[Gemini Structured] No text in response parts")
            print(f"[Gemini Structured] Parts: {parts}")
            print(f"[Gemini Structured] Full response: {json.dumps(response_data)[:2000]}")
            return None
        else:
            print(f"[Gemini Structured] Error {response.status_code}: {response.text[:500]}")
            return None

    except requests.exceptions.Timeout:
        print("[Gemini Structured] Request timed out")
        return None
    except Exception as e:
        print(f"[Gemini Structured] Error: {e}")
        return None


def call_claude_api(prompt, messages, model_id, system_prompt=None, stream_callback=None):
    """Call the Claude API with the given messages and prompt
    
    Args:
        stream_callback: Optional function(chunk: str) to call with each streaming token
    """
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "Error: ANTHROPIC_API_KEY not found in environment variables"
    
    url = "https://api.anthropic.com/v1/messages"
    
    # Ensure we have a system prompt
    payload = {
        "model": model_id,
        "max_tokens": 4000,
        "temperature": 1,
        "stream": stream_callback is not None  # Enable streaming if callback provided
    }
    
    # Set system if provided
    if system_prompt:
        payload["system"] = system_prompt
        print(f"CLAUDE API USING SYSTEM PROMPT: {system_prompt}")
    
    # Clean messages to remove duplicates
    filtered_messages = []
    seen_contents = set()
    
    for msg in messages:
        # Skip system messages (handled separately)
        if msg.get("role") == "system":
            continue
            
        # Get content - handle both string and list formats
        content = msg.get("content", "")
        
        # For duplicate detection, use a hashable representation (always a string)
        if isinstance(content, list):
            # For image messages, create a hash based on text content only
            text_parts = [part.get('text', '') for part in content if part.get('type') == 'text']
            content_hash = ''.join(text_parts)
        elif isinstance(content, str):
            content_hash = content
        else:
            # For any other type, convert to string
            content_hash = str(content) if content else ""
            
        # Check for duplicates
        if content_hash and content_hash in seen_contents:
            print(f"Skipping duplicate message in API call: {str(content_hash)[:30]}...")
            continue
            
        if content_hash:
            seen_contents.add(content_hash)
        filtered_messages.append(msg)
    
    # Add the current prompt as the final user message (if it's not already an image message)
    if prompt and not any(isinstance(msg.get("content"), list) for msg in filtered_messages[-1:]):
        filtered_messages.append({
            "role": "user",
            "content": prompt
        })

    # Add filtered messages to payload
    payload["messages"] = filtered_messages
    
    # Actual API call
    headers = {
        "Content-Type": "application/json",
        "x-api-key": api_key,
        "anthropic-version": "2023-06-01"
    }
    
    try:
        if stream_callback:
            # Streaming mode using REST API directly
            payload["stream"] = True
            full_response = ""
            
            response = requests.post(url, json=payload, headers=headers, stream=True)
            
            if response.status_code == 200:
                for line in response.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: '):
                            json_str = line_text[6:]  # Remove 'data: ' prefix
                            # Skip if this is a ping or message_stop event
                            if json_str.strip() in ['[DONE]', '']:
                                continue
                            try:
                                chunk_data = json.loads(json_str)
                                # Handle different event types from Claude's SSE stream
                                event_type = chunk_data.get('type')
                                
                                if event_type == 'content_block_delta':
                                    delta = chunk_data.get('delta', {})
                                    if delta.get('type') == 'text_delta':
                                        text = delta.get('text', '')
                                        if text:
                                            full_response += text
                                            stream_callback(text)
                            except json.JSONDecodeError:
                                continue
                return full_response
            else:
                return f"Error: API returned status {response.status_code}: {response.text}"
        else:
            # Non-streaming mode (original behavior)
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
            if 'content' in data and len(data['content']) > 0:
                for content_item in data['content']:
                    if content_item.get('type') == 'text':
                        return content_item.get('text', '')
                # Fallback if no text type content is found
                return str(data['content'])
            return "No content in response"
    except Exception as e:
        return f"Error calling Claude API: {str(e)}"

def call_openai_api(prompt, conversation_history, model, system_prompt):
    try:
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        for msg in conversation_history:
            messages.append({"role": msg["role"], "content": msg["content"]})
        
        messages.append({"role": "user", "content": prompt})
        
        response = openai.chat.completions.create(
            model=model,
            messages=messages,
            # Increase max_tokens and add n parameter
            max_tokens=4000,
            n=1,
            temperature=1,
            stream=True
        )
        
        collected_messages = []
        for chunk in response:
            if chunk.choices[0].delta.content is not None:  # Changed condition
                collected_messages.append(chunk.choices[0].delta.content)
                
        full_reply = ''.join(collected_messages)
        return full_reply
        
    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return None

def format_response_with_citations(text: str, annotations: list) -> str:
    """Format response text with inline footnote markers and a sources section.

    Args:
        text: The response text from the API
        annotations: List of annotation objects from the API response

    Returns:
        Formatted text with [1], [2] markers and a Sources section at the end
    """
    if not annotations:
        return text

    # Filter to only url_citation annotations
    url_citations = [a for a in annotations if a.get('type') == 'url_citation']
    if not url_citations:
        return text

    # Build URL to footnote number mapping (deduplicate URLs)
    url_to_number = {}
    sources = []  # List of (number, title, url) tuples

    for citation in url_citations:
        url = citation.get('url', '')
        if not url:
            continue
        if url not in url_to_number:
            number = len(url_to_number) + 1
            url_to_number[url] = number
            # Get title, fallback to domain if not available
            title = citation.get('title', '')
            if not title:
                # Extract domain from URL as fallback
                try:
                    from urllib.parse import urlparse
                    parsed = urlparse(url)
                    title = parsed.netloc or url
                except:
                    title = url
            sources.append((number, title, url))

    if not sources:
        return text

    # Insert footnote markers at end_index positions
    # Process in reverse order to preserve index positions
    citations_with_positions = [
        (c.get('end_index', 0), url_to_number.get(c.get('url', ''), 0))
        for c in url_citations
        if c.get('url') in url_to_number and c.get('end_index') is not None
    ]
    # Sort by position descending
    citations_with_positions.sort(key=lambda x: x[0], reverse=True)

    # Insert markers (avoid duplicates at same position)
    modified_text = text
    inserted_positions = set()
    for end_index, footnote_num in citations_with_positions:
        if end_index not in inserted_positions and footnote_num > 0:
            # Insert the marker at the position
            marker = f" [{footnote_num}]"
            modified_text = modified_text[:end_index] + marker + modified_text[end_index:]
            inserted_positions.add(end_index)

    # Build sources section
    sources_section = "\n\n---\nSources:"
    for number, title, url in sorted(sources, key=lambda x: x[0]):
        sources_section += f"\n{number}. {title} - {url}"

    return modified_text + sources_section


def call_openrouter_responses_api(
    prompt,
    conversation_history,
    model,
    system_prompt,
    tools=None,
    tool_executor=None,
    stream_callback=None
):
    """Call the OpenRouter Responses API with web search, tool calling, and streaming support.

    This API returns citation annotations for web search results and supports tool calling
    with proper multi-turn follow-up requests.

    Args:
        prompt: The current user message
        conversation_history: List of previous messages
        model: The model ID to use
        system_prompt: System prompt for the model
        tools: Optional list of function tool schemas (OpenAI format)
        tool_executor: Optional callback function(name, args) -> result to execute tool calls
        stream_callback: Optional function(chunk: str) to call with each streaming token

    Returns:
        Formatted response string with citations, or None on error
    """
    import uuid as uuid_module

    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "HTTP-Referer": "http://localhost:3000",
            "Content-Type": "application/json",
            "X-Title": "AI Conversation"
        }

        # Normalize model ID for OpenRouter
        openrouter_model = model
        if model.startswith("claude-") and not model.startswith("anthropic/"):
            openrouter_model = f"anthropic/{model}"

        # Build input array in OpenResponses format
        input_messages = []

        # Add system prompt as first message if provided
        if system_prompt:
            input_messages.append({
                "type": "message",
                "role": "system",
                "content": [{"type": "input_text", "text": system_prompt}]
            })

        # Add conversation history
        for msg in conversation_history:
            if msg.get("role") != "system":  # Skip system prompts in history
                content = msg.get("content", "")
                # Convert structured content to plain text for Responses API
                if isinstance(content, list):
                    text_parts = [p.get('text', '') for p in content if p.get('type') == 'text']
                    content = ' '.join(text_parts)
                input_messages.append({
                    "type": "message",
                    "role": msg.get("role", "user"),
                    "content": [{"type": "input_text", "text": content}]
                })

        # Add current prompt
        if isinstance(prompt, list):
            text_parts = [p.get('text', '') for p in prompt if p.get('type') == 'text']
            prompt_text = ' '.join(text_parts)
        else:
            prompt_text = prompt
        input_messages.append({
            "type": "message",
            "role": "user",
            "content": [{"type": "input_text", "text": prompt_text}]
        })

        # Build tools array - always include web_search, add function tools if provided
        api_tools: list[dict] = [{"type": "web_search"}]
        if tools:
            # Convert OpenAI-style tools to Responses API format
            for tool in tools:
                if tool.get("type") == "function":
                    api_tools.append({
                        "type": "function",
                        "name": tool["function"]["name"],
                        "description": tool["function"].get("description", ""),
                        "strict": None,
                        "parameters": tool["function"].get("parameters", {})
                    })

        payload = {
            "model": openrouter_model,
            "input": input_messages,
            "tools": api_tools,
            "tool_choice": "auto",
            "max_output_tokens": 4000,
            "temperature": 1,
            "stream": stream_callback is not None
        }
        _add_openrouter_transforms(payload)

        print(f"\n[OpenRouter Responses API] Sending request:")
        print(f"  Model: {openrouter_model}")
        print(f"  Messages: {len(input_messages)}")
        print(f"  Web search: ENABLED")
        print(f"  Streaming: {stream_callback is not None}")
        if tools:
            print(f"  Function tools: {[t['function']['name'] for t in tools if t.get('type') == 'function']}")
        # Debug: verify message format
        if input_messages:
            first_msg = input_messages[0]
            print(f"  First msg has 'type' key: {'type' in first_msg}, type value: {first_msg.get('type', 'MISSING')}")

        def make_request(req_payload, stream=False):
            """Make a request to the Responses API, handling streaming if enabled."""
            if stream:
                return _responses_api_streaming_request(headers, req_payload, stream_callback)
            else:
                response = requests.post(
                    "https://openrouter.ai/api/v1/responses",
                    headers=headers,
                    json=req_payload,
                    timeout=120
                )
                if response.status_code == 200:
                    return response.json()
                else:
                    print(f"[OpenRouter Responses API] Error: {response.status_code} - {response.text[:500]}")
                    return None

        response_data = make_request(payload, stream=stream_callback is not None)
        if not response_data:
            return None

        print(f"[OpenRouter Responses API] Response received")

        # Debug: log raw output structure
        output = response_data.get("output", [])
        print(f"[OpenRouter Responses API] Output items: {len(output)}, types: {[item.get('type') for item in output]}")
        if output and output[0].get("type") == "message":
            content = output[0].get("content", [])
            if content:
                print(f"[OpenRouter Responses API] First message content type: {content[0].get('type') if content else 'none'}")
                if content[0].get("type") == "output_text":
                    print(f"[OpenRouter Responses API] Text preview: {content[0].get('text', '')[:200]}")

        # Extract output items
        text = ""
        annotations = []
        function_calls = []

        for item in output:
            if item.get("type") == "message":
                for content in item.get("content", []):
                    if content.get("type") == "output_text":
                        text = content.get("text", "")
                        annotations = content.get("annotations", [])
            elif item.get("type") == "function_call":
                function_calls.append(item)

        # Handle function calls with proper multi-turn follow-up
        if function_calls and tool_executor:
            print(f"[OpenRouter Responses API] Processing {len(function_calls)} function call(s)")

            # Execute all tools and collect results
            tool_results = []
            image_generated = False

            for fc in function_calls:
                func_name = fc.get("name")
                func_args = fc.get("arguments") or "{}"  # Handle empty string case
                call_id = fc.get("call_id", fc.get("id", ""))
                fc_id = fc.get("id", f"fc_{uuid_module.uuid4().hex[:8]}")

                print(f"[OpenRouter Responses API] Executing tool: {func_name}")
                try:
                    args_dict = json.loads(func_args) if isinstance(func_args, str) else (func_args or {})
                    tool_result = tool_executor(func_name, args_dict)
                    print(f"[OpenRouter Responses API] Tool result: {str(tool_result)[:200]}")

                    # Track if image was generated (handled separately by executor)
                    if func_name == "generate_image" and tool_result:
                        image_generated = True

                    # Check for meta-tool expansion signal - return early to allow re-call with expanded tools
                    if isinstance(tool_result, dict) and tool_result.get("expansion_needed"):
                        print(f"[OpenRouter Responses API] Meta-tool expansion requested for {func_name}, returning early")
                        # Return None to signal expansion needed - don't send a message to the user
                        return None

                    tool_results.append({
                        "function_call": {
                            "type": "function_call",
                            "id": fc_id,
                            "call_id": call_id,
                            "name": func_name,
                            "arguments": func_args if isinstance(func_args, str) else json.dumps(func_args)
                        },
                        "output": {
                            "type": "function_call_output",
                            "id": f"fco_{uuid_module.uuid4().hex[:8]}",
                            "call_id": call_id,
                            "output": json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                        }
                    })

                except Exception as e:
                    print(f"[OpenRouter Responses API] Tool execution error: {e}")
                    tool_results.append({
                        "function_call": {
                            "type": "function_call",
                            "id": fc_id,
                            "call_id": call_id,
                            "name": func_name,
                            "arguments": func_args if isinstance(func_args, str) else json.dumps(func_args)
                        },
                        "output": {
                            "type": "function_call_output",
                            "id": f"fco_{uuid_module.uuid4().hex[:8]}",
                            "call_id": call_id,
                            "output": json.dumps({"error": str(e)})
                        }
                    })

            # Build follow-up request with tool results - support chained tool calls
            if tool_results:
                follow_up_input = list(input_messages)  # Copy original messages

                # Add each function call and its output
                for tr in tool_results:
                    follow_up_input.append(tr["function_call"])
                    follow_up_input.append(tr["output"])

                max_tool_iterations = 10  # Prevent infinite loops
                for iteration in range(max_tool_iterations):
                    follow_up_payload = {
                        "model": openrouter_model,
                        "input": follow_up_input,
                        "tools": api_tools,
                        "tool_choice": "auto",
                        "max_output_tokens": 4000,
                        "temperature": 1,
                        "stream": stream_callback is not None
                    }
                    _add_openrouter_transforms(follow_up_payload)

                    print(f"[OpenRouter Responses API] Making follow-up request (iteration {iteration + 1}) with tool result(s)")
                    follow_up_response = make_request(follow_up_payload, stream=stream_callback is not None)

                    if follow_up_response:
                        # Extract text and function calls from follow-up response
                        follow_up_output = follow_up_response.get("output", [])
                        follow_up_function_calls = []

                        for item in follow_up_output:
                            if item.get("type") == "message":
                                for content in item.get("content", []):
                                    if content.get("type") == "output_text":
                                        text = content.get("text", "")
                                        annotations = content.get("annotations", [])
                            elif item.get("type") == "function_call":
                                follow_up_function_calls.append(item)

                        # If more function calls requested, execute them
                        if follow_up_function_calls and tool_executor:
                            print(f"[OpenRouter Responses API] Follow-up has {len(follow_up_function_calls)} more function call(s)")

                            for fc in follow_up_function_calls:
                                func_name = fc.get("name")
                                func_args = fc.get("arguments") or "{}"  # Handle empty string case
                                call_id = fc.get("call_id", fc.get("id", ""))
                                fc_id = fc.get("id", f"fc_{uuid_module.uuid4().hex[:8]}")

                                print(f"[OpenRouter Responses API] Executing chained tool: {func_name}")
                                try:
                                    args_dict = json.loads(func_args) if isinstance(func_args, str) else (func_args or {})
                                    tool_result = tool_executor(func_name, args_dict)
                                    print(f"[OpenRouter Responses API] Chained tool result: {str(tool_result)[:200]}")

                                    # Check for meta-tool expansion signal
                                    if isinstance(tool_result, dict) and tool_result.get("expansion_needed"):
                                        print(f"[OpenRouter Responses API] Meta-tool expansion in chained call for {func_name}, returning early")
                                        # Return None to signal expansion needed - don't send a message to the user
                                        return None

                                    follow_up_input.append({
                                        "type": "function_call",
                                        "id": fc_id,
                                        "call_id": call_id,
                                        "name": func_name,
                                        "arguments": func_args if isinstance(func_args, str) else json.dumps(func_args)
                                    })
                                    follow_up_input.append({
                                        "type": "function_call_output",
                                        "id": f"fco_{uuid_module.uuid4().hex[:8]}",
                                        "call_id": call_id,
                                        "output": json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                                    })
                                except Exception as e:
                                    print(f"[OpenRouter Responses API] Chained tool error: {e}")
                                    follow_up_input.append({
                                        "type": "function_call",
                                        "id": fc_id,
                                        "call_id": call_id,
                                        "name": func_name,
                                        "arguments": func_args if isinstance(func_args, str) else json.dumps(func_args)
                                    })
                                    follow_up_input.append({
                                        "type": "function_call_output",
                                        "id": f"fco_{uuid_module.uuid4().hex[:8]}",
                                        "call_id": call_id,
                                        "output": json.dumps({"error": str(e)})
                                    })
                            # Continue loop for next iteration
                            continue

                        # No more function calls - we have our answer
                        if text:
                            break
                    else:
                        print(f"[OpenRouter Responses API] Follow-up request failed")
                        break

                # If image was generated and we have text, return it
                # If image was generated but no text, return empty (image sent separately)
                if image_generated and not text:
                    return ""

        if text:
            # Format response with citations
            formatted_response = format_response_with_citations(text, annotations)
            print(f"[OpenRouter Responses API] Response received, {len(annotations)} citations found")
            return formatted_response
        else:
            print("[OpenRouter Responses API] Empty text in response")
            return None

    except requests.exceptions.Timeout:
        print("[OpenRouter Responses API] Request timed out")
        return None
    except Exception as e:
        print(f"[OpenRouter Responses API] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def _responses_api_streaming_request(headers, payload, stream_callback):
    """Handle streaming requests to the Responses API.

    Parses Server-Sent Events and calls stream_callback with text deltas.
    Returns the complete response structure when done.

    Args:
        headers: Request headers
        payload: Request payload (should have stream=True)
        stream_callback: Function to call with each text chunk

    Returns:
        Complete response dict with output items, or None on error
    """
    try:
        response = requests.post(
            "https://openrouter.ai/api/v1/responses",
            headers=headers,
            json=payload,
            timeout=180,
            stream=True
        )

        if response.status_code != 200:
            print(f"[OpenRouter Responses API Stream] Error: {response.status_code} - {response.text[:500]}")
            return None

        # Track state for building final response
        response_id = None
        output_items = {}  # id -> item
        current_text = ""
        current_annotations = []
        function_calls = []

        for line in response.iter_lines():
            if not line:
                continue

            line_text = line.decode('utf-8')
            if not line_text.startswith('data: '):
                continue

            data_str = line_text[6:]  # Remove 'data: ' prefix
            if data_str.strip() == '[DONE]':
                break

            try:
                event = json.loads(data_str)
                event_type = event.get('type', '')

                if event_type == 'response.created':
                    resp = event.get('response', {})
                    response_id = resp.get('id')

                elif event_type == 'response.output_item.added':
                    item = event.get('item', {})
                    item_id = item.get('id')
                    if item_id:
                        output_items[item_id] = item
                    # Track function calls
                    if item.get('type') == 'function_call':
                        function_calls.append(item)

                elif event_type == 'response.content_part.delta':
                    # Text delta - stream it to callback
                    delta = event.get('delta', '')
                    if delta and stream_callback:
                        stream_callback(delta)
                    current_text += delta

                elif event_type == 'response.content_part.done':
                    # Content part completed - extract annotations
                    part = event.get('part', {})
                    if part.get('type') == 'output_text':
                        current_annotations = part.get('annotations', [])

                elif event_type == 'response.output_item.done':
                    # Update output item with final state
                    item = event.get('item', {})
                    item_id = item.get('id')
                    if item_id:
                        output_items[item_id] = item
                    # Track completed function calls
                    if item.get('type') == 'function_call':
                        # Update or add to function_calls
                        for i, fc in enumerate(function_calls):
                            if fc.get('id') == item_id:
                                function_calls[i] = item
                                break
                        else:
                            function_calls.append(item)

                elif event_type == 'response.function_call_arguments.delta':
                    # Function call arguments being streamed
                    pass  # We'll get the full args in output_item.done

                elif event_type == 'response.function_call_arguments.done':
                    # Function call arguments complete
                    pass  # We'll get the full item in output_item.done

                elif event_type == 'response.done':
                    # Final response with usage stats
                    pass

            except json.JSONDecodeError:
                continue

        # Build final response structure
        final_output = []

        # Add message with collected text if present
        if current_text:
            final_output.append({
                "type": "message",
                "role": "assistant",
                "content": [{
                    "type": "output_text",
                    "text": current_text,
                    "annotations": current_annotations
                }]
            })

        # Add function calls
        for fc in function_calls:
            final_output.append(fc)

        return {
            "id": response_id,
            "output": final_output,
            "status": "completed"
        }

    except requests.exceptions.Timeout:
        print("[OpenRouter Responses API Stream] Request timed out")
        return None
    except Exception as e:
        print(f"[OpenRouter Responses API Stream] Error: {e}")
        import traceback
        traceback.print_exc()
        return None


def call_openrouter_api(
    prompt,
    conversation_history,
    model,
    system_prompt,
    stream_callback=None,
    web_search=False,
    tools=None,
    tool_executor=None
):
    """Call the OpenRouter API to access various LLM models.

    Args:
        stream_callback: Optional function(chunk: str) to call with each streaming token
        web_search: If True, enable OpenRouter's web search via Responses API (returns citations)
        tools: Optional list of tool schemas for function calling
        tool_executor: Optional callback function(name, args) -> dict to execute tool calls
    """
    # Check if prompt OR conversation history contains images (structured content with image parts)
    # If any images exist, we must skip Responses API which strips image data from history
    has_images = False

    # Check current prompt
    if isinstance(prompt, list):
        for part in prompt:
            if part.get('type') == 'image':
                has_images = True
                break

    # Also check conversation history for images
    if not has_images and conversation_history:
        for msg in conversation_history:
            content = msg.get('content')
            if isinstance(content, list):
                for part in content:
                    if part.get('type') == 'image':
                        has_images = True
                        break
                if has_images:
                    break

    # Route web search requests to Responses API for citation support
    # BUT: Responses API doesn't support images, so skip it when images are present
    if web_search and not has_images:
        print(f"[OpenRouter] Web search enabled, using Responses API for citations")
        result = call_openrouter_responses_api(
            prompt, conversation_history, model, system_prompt,
            tools=tools, tool_executor=tool_executor,
            stream_callback=stream_callback
        )
        if result is not None:  # None could mean image was sent separately
            return result
        # Check if we got a tool call that was handled (returns None but tool ran)
        # Fall back to Chat Completions API if Responses API fails
        print(f"[OpenRouter] Responses API returned None, falling back to Chat Completions with :online suffix")
    elif web_search and has_images:
        print(f"[OpenRouter] Images detected - skipping Responses API (doesn't support vision), using Chat Completions")

    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "HTTP-Referer": "http://localhost:3000",
            "Content-Type": "application/json",
            "X-Title": "AI Conversation"  # Adding title for OpenRouter tracking
        }
        
        # Normalize model ID for OpenRouter - add provider prefix if missing
        openrouter_model = model
        if model.startswith("claude-") and not model.startswith("anthropic/"):
            openrouter_model = f"anthropic/{model}"
            print(f"Normalized Claude model ID for OpenRouter: {model} -> {openrouter_model}")
        
        # Format messages - need to handle structured content with images
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        def convert_to_openai_format(content, include_images=True):
            """Convert Anthropic-style image format to OpenAI/OpenRouter format.
            
            Args:
                content: The message content (string or list)
                include_images: If False, strip image content and keep only text
            """
            if not isinstance(content, list):
                return content
            
            converted = []
            for part in content:
                if part.get('type') == 'text':
                    converted.append({"type": "text", "text": part.get('text', '')})
                elif part.get('type') == 'image':
                    if include_images:
                        # Convert Anthropic format to OpenAI format
                        source = part.get('source', {})
                        if source.get('type') == 'base64':
                            media_type = source.get('media_type', 'image/png')
                            data = source.get('data', '')
                            converted.append({
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:{media_type};base64,{data}"
                                }
                            })
                    # If not including images, we skip this part (text description is already there)
                elif part.get('type') == 'image_url':
                    if include_images:
                        # Already in OpenAI format
                        converted.append(part)
                else:
                    # Pass through unknown types
                    converted.append(part)
            
            # If we stripped images and only have one text element, simplify to string
            if not include_images and len(converted) == 1 and converted[0].get('type') == 'text':
                return converted[0]['text']
            elif not include_images and len(converted) == 0:
                return ""
            
            return converted
        
        def build_messages(include_images=True):
            """Build the messages list, optionally stripping images."""
            msgs = []
            if system_prompt:
                msgs.append({"role": "system", "content": system_prompt})
            
            for msg in conversation_history:
                if msg["role"] != "system":  # Skip system prompts
                    msgs.append({
                        "role": msg["role"],
                        "content": convert_to_openai_format(msg["content"], include_images)
                    })
            
            # Also convert the prompt if it's structured content
            msgs.append({"role": "user", "content": convert_to_openai_format(prompt, include_images)})
            return msgs
        
        def make_api_call(include_images=True):
            """Make the API call, returns (success, result_or_error)"""
            msgs = build_messages(include_images=include_images)

            # Use :online suffix for web search (more reliable than plugins array)
            model_to_use = openrouter_model
            if web_search:
                # Append :online to enable web search
                if not model_to_use.endswith(":online"):
                    model_to_use = f"{model_to_use}:online"
                print(f"[OpenRouter] Web search ENABLED - using model: {model_to_use}")
            else:
                print(f"[OpenRouter] Web search: DISABLED")

            # Disable streaming when tools are provided (incompatible)
            use_streaming = stream_callback is not None and not tools

            payload = {
                "model": model_to_use,
                "messages": msgs,
                "temperature": 1,
                "max_tokens": 4000,
                "stream": use_streaming
            }

            # Add tools for function calling if provided
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"  # Let model decide when to use tools
                print(f"[OpenRouter] Tool calling enabled with {len(tools)} tools")

            _add_openrouter_transforms(payload)

            print(f"\nSending to OpenRouter:")
            print(f"Model: {model_to_use}")
            print(f"Include images: {include_images}")
            # Log message summary (avoid huge base64 dumps)
            for i, m in enumerate(msgs):
                content = m.get('content', '')
                if isinstance(content, list):
                    parts_summary = [p.get('type', 'unknown') for p in content]
                    print(f"  [{i}] {m.get('role')}: [structured: {parts_summary}]")
                else:
                    preview = str(content)[:80] + "..." if len(str(content)) > 80 else content
                    print(f"  [{i}] {m.get('role')}: {preview}")
            
            if stream_callback:
                # Streaming mode
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=180,
                    stream=True
                )
                
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    full_response = ""
                    chunk_count = 0
                    last_finish_reason = None
                    debug_chunks = []  # Store first few chunks for debugging
                    for line in response.iter_lines():
                        if line:
                            line_text = line.decode('utf-8')
                            if line_text.startswith('data: '):
                                json_str = line_text[6:]
                                if json_str.strip() == '[DONE]':
                                    break
                                try:
                                    chunk_data = json.loads(json_str)
                                    # Store first 5 chunks for debugging
                                    if len(debug_chunks) < 5:
                                        debug_chunks.append(chunk_data)
                                    if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                        choice = chunk_data['choices'][0]
                                        delta = choice.get('delta', {})
                                        content = delta.get('content', '')
                                        last_finish_reason = choice.get('finish_reason')
                                        if content:
                                            full_response += content
                                            stream_callback(content)
                                        chunk_count += 1
                                except json.JSONDecodeError:
                                    continue
                    # Log if response is empty
                    if not full_response or not full_response.strip():
                        print(f"[OpenRouter STREAM] Empty response from {model}", flush=True)
                        print(f"[OpenRouter STREAM]   Chunks received: {chunk_count}", flush=True)
                        print(f"[OpenRouter STREAM]   Last finish_reason: {last_finish_reason}", flush=True)
                        print(f"[OpenRouter STREAM]   Response repr: {repr(full_response)}", flush=True)
                        # Print the actual chunk data for debugging
                        for i, chunk in enumerate(debug_chunks):
                            print(f"[OpenRouter STREAM]   Chunk {i}: {json.dumps(chunk)[:300]}", flush=True)
                    return True, full_response
                else:
                    return False, (response.status_code, response.text)
            else:
                # Non-streaming mode
                response = requests.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=60
                )
                
                print(f"Response status: {response.status_code}")
                
                if response.status_code == 200:
                    response_data = response.json()
                    # Debug: log full response structure for empty responses
                    if 'choices' in response_data and len(response_data['choices']) > 0:
                        choice = response_data['choices'][0]
                        message = choice.get('message', {})
                        finish_reason = choice.get('finish_reason', '')
                        content = message.get('content', '') if message else ''
                        tool_calls = message.get('tool_calls', [])

                        # Handle tool calls if present and we have an executor
                        if tool_calls and tool_executor:
                            print(f"[OpenRouter] Model requested {len(tool_calls)} tool call(s)")

                            # Add assistant message with tool calls to conversation
                            tool_call_msg = {
                                "role": "assistant",
                                "content": content,  # May be null
                                "tool_calls": tool_calls
                            }
                            msgs.append(tool_call_msg)

                            # Execute each tool and collect results
                            for tc in tool_calls:
                                try:
                                    fn_name = tc.get('function', {}).get('name', '')
                                    fn_args_str = tc.get('function', {}).get('arguments') or '{}'  # Handle empty string
                                    tc_id = tc.get('id', '')

                                    # Parse arguments
                                    try:
                                        fn_args = json.loads(fn_args_str) if isinstance(fn_args_str, str) else (fn_args_str or {})
                                    except json.JSONDecodeError:
                                        fn_args = {}

                                    print(f"[OpenRouter] Executing tool: {fn_name}({fn_args})")

                                    # Execute the tool
                                    tool_result = tool_executor(fn_name, fn_args)

                                    # Check for meta-tool expansion signal
                                    if isinstance(tool_result, dict) and tool_result.get("expansion_needed"):
                                        print(f"[OpenRouter] Meta-tool expansion requested for {fn_name}, returning early")
                                        return tool_result.get("message", f"Expanded {fn_name}")

                                    # Add tool result to messages
                                    msgs.append({
                                        "role": "tool",
                                        "tool_call_id": tc_id,
                                        "content": json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                                    })
                                    print(f"[OpenRouter] Tool result: {tool_result}")

                                except Exception as e:
                                    print(f"[OpenRouter] Tool execution error: {e}")
                                    msgs.append({
                                        "role": "tool",
                                        "tool_call_id": tc.get('id', ''),
                                        "content": json.dumps({"success": False, "message": str(e)})
                                    })

                            # Make follow-up API call WITH tools to allow chained tool calls
                            max_tool_iterations = 10  # Prevent infinite loops
                            for iteration in range(max_tool_iterations):
                                follow_up_payload = {
                                    "model": model_to_use,
                                    "messages": msgs,
                                    "temperature": 1,
                                    "max_tokens": 4000,
                                    "stream": False
                                }
                                # Include tools for chained tool calls
                                if tools:
                                    follow_up_payload["tools"] = tools
                                _add_openrouter_transforms(follow_up_payload)

                                print(f"[OpenRouter] Making follow-up call (iteration {iteration + 1})...")
                                follow_up_response = requests.post(
                                    "https://openrouter.ai/api/v1/chat/completions",
                                    headers=headers,
                                    json=follow_up_payload,
                                    timeout=60
                                )

                                if follow_up_response.status_code == 200:
                                    follow_up_data = follow_up_response.json()
                                    if 'choices' in follow_up_data and len(follow_up_data['choices']) > 0:
                                        follow_up_choice = follow_up_data['choices'][0]
                                        follow_up_message = follow_up_choice.get('message', {})
                                        follow_up_content = follow_up_message.get('content', '')
                                        follow_up_tool_calls = follow_up_message.get('tool_calls', [])

                                        # If model wants more tool calls, execute them
                                        if follow_up_tool_calls and tool_executor:
                                            print(f"[OpenRouter] Follow-up requested {len(follow_up_tool_calls)} more tool call(s)")

                                            # Add assistant message with tool calls
                                            msgs.append({
                                                "role": "assistant",
                                                "content": follow_up_content,
                                                "tool_calls": follow_up_tool_calls
                                            })

                                            # Execute each tool
                                            for tc in follow_up_tool_calls:
                                                try:
                                                    fn_name = tc.get('function', {}).get('name', '')
                                                    fn_args_str = tc.get('function', {}).get('arguments') or '{}'  # Handle empty string
                                                    tc_id = tc.get('id', '')

                                                    try:
                                                        fn_args = json.loads(fn_args_str) if isinstance(fn_args_str, str) else (fn_args_str or {})
                                                    except json.JSONDecodeError:
                                                        fn_args = {}

                                                    print(f"[OpenRouter] Executing chained tool: {fn_name}({fn_args})")
                                                    tool_result = tool_executor(fn_name, fn_args)

                                                    # Check for meta-tool expansion signal
                                                    if isinstance(tool_result, dict) and tool_result.get("expansion_needed"):
                                                        print(f"[OpenRouter] Meta-tool expansion in chained call for {fn_name}, returning early")
                                                        return True, tool_result.get("message", f"Expanded {fn_name}")

                                                    msgs.append({
                                                        "role": "tool",
                                                        "tool_call_id": tc_id,
                                                        "content": json.dumps(tool_result) if isinstance(tool_result, dict) else str(tool_result)
                                                    })
                                                    print(f"[OpenRouter] Chained tool result: {tool_result}")
                                                except Exception as e:
                                                    print(f"[OpenRouter] Chained tool error: {e}")
                                                    msgs.append({
                                                        "role": "tool",
                                                        "tool_call_id": tc.get('id', ''),
                                                        "content": json.dumps({"success": False, "message": str(e)})
                                                    })
                                            # Continue loop for next iteration
                                            continue

                                        # No more tool calls - return content
                                        if follow_up_content:
                                            return True, follow_up_content
                                        break  # Exit loop if no content and no tool calls
                                else:
                                    print(f"[OpenRouter] Follow-up call failed with status {follow_up_response.status_code}")
                                    break

                            print(f"[OpenRouter] Follow-up loop ended, using initial content if any")

                        if content and content.strip():
                            return True, content
                        else:
                            # Log detailed info about empty response (avoiding base64)
                            import sys
                            print(f"[OpenRouter] Empty content from model: {model}", flush=True)
                            print(f"[OpenRouter]   Choice keys: {list(choice.keys())}", flush=True)
                            print(f"[OpenRouter]   Message keys: {list(message.keys()) if message else 'None'}", flush=True)
                            print(f"[OpenRouter]   Finish reason: {finish_reason}", flush=True)
                            print(f"[OpenRouter]   Content type: {type(content).__name__}, len: {len(content) if content else 0}", flush=True)
                            print(f"[OpenRouter]   Content repr: {repr(content)}", flush=True)
                            # Check for refusal or other indicators
                            if message.get('refusal'):
                                print(f"[OpenRouter]   Refusal: {message.get('refusal')}", flush=True)
                            # Check for tool_calls that weren't handled
                            if tool_calls and not tool_executor:
                                print(f"[OpenRouter]   Tool calls: {len(tool_calls)} call(s) (no executor provided)", flush=True)
                            sys.stdout.flush()
                            return True, None
                    else:
                        print(f"[OpenRouter] No choices in response. Keys: {list(response_data.keys()) if isinstance(response_data, dict) else 'non-dict'}")
                    return True, None
                else:
                    return False, (response.status_code, response.text)
        
        # Try with images first
        success, result = make_api_call(include_images=True)
        print(f"[OpenRouter] First call result - success: {success}, result type: {type(result).__name__}, result: {repr(result)[:100] if result else 'None'}", flush=True)
        
        if success:
            # Check for empty response and retry once
            if result is None or (isinstance(result, str) and not result.strip()):
                print(f"[OpenRouter] WARNING: Model {model} returned empty response, retrying...", flush=True)
                import time
                time.sleep(1)
                success, result = make_api_call(include_images=True)
                print(f"[OpenRouter] Retry result - success: {success}, result type: {type(result).__name__}, result: {repr(result)[:100] if result else 'None'}", flush=True)
                if success and result and (not isinstance(result, str) or result.strip()):
                    return result
                print(f"[OpenRouter] WARNING: Model {model} returned empty response again after retry", flush=True)
                return "[Model returned empty response - it may be experiencing issues]"
            return result
        
        # Check if error is due to model not supporting images
        # result is a tuple (status_code, error_text) when success is False
        if not isinstance(result, tuple):
            return f"Error: Unexpected result type"
        status_code, error_text = result
        if status_code == 404 and "support image" in error_text.lower():
            print(f"[OpenRouter] Model {model} doesn't support images, retrying without images...")
            success, result = make_api_call(include_images=False)
            if success:
                return result
            if not isinstance(result, tuple):
                return f"Error: Unexpected result type"
            status_code, error_text = result

        # Handle 429 rate limit with exponential backoff retry
        if status_code == 429:
            import time
            max_retries = 3
            base_delay = 2  # seconds

            for retry in range(max_retries):
                delay = base_delay * (2 ** retry)  # 2, 4, 8 seconds
                print(f"[OpenRouter] Rate limited (429), waiting {delay}s before retry {retry + 1}/{max_retries}...")
                time.sleep(delay)

                success, result = make_api_call(include_images=True)
                if success:
                    return result

                if isinstance(result, tuple):
                    status_code, error_text = result
                    if status_code != 429:
                        break  # Different error, stop retrying

            print(f"[OpenRouter] Rate limit persists after {max_retries} retries")

        # Handle other errors
        error_msg = f"OpenRouter API error {status_code}: {error_text}"
        print(error_msg)
        if status_code == 404:
            print("Model not found or doesn't support this request type.")
        elif status_code == 401:
            print("Authentication error. Please check your API key.")
        elif status_code == 429:
            print("Rate limited. Consider adding your own API key at https://openrouter.ai/settings/integrations")
        return f"Error: {error_msg}"
            
    except requests.exceptions.Timeout:
        print("Request timed out. The server took too long to respond.")
        return "Error: Request timed out"
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        return f"Error: Network error - {str(e)}"
    except Exception as e:
        print(f"Error calling OpenRouter API: {e}")
        print(f"Error type: {type(e)}")
        return f"Error: {str(e)}"

def call_deepseek_api(prompt, conversation_history, model, system_prompt, stream_callback=None):
    """Call the DeepSeek model through OpenRouter API."""
    try:
        import re
        from config import SHOW_CHAIN_OF_THOUGHT_IN_CONTEXT
        
        # Build messages array
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        # Add conversation history
        for msg in conversation_history:
            if isinstance(msg, dict):
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if isinstance(content, str) and content.strip():
                    messages.append({"role": role, "content": content})
        
        # Add current prompt if provided
        if prompt:
            messages.append({"role": "user", "content": prompt})
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
        }
        
        payload = {
            "model": "deepseek/deepseek-r1",
            "messages": messages,
            "max_tokens": 8000,
            "temperature": 1,
            "stream": stream_callback is not None
        }
        _add_openrouter_transforms(payload)

        print(f"\nSending to DeepSeek via OpenRouter:")
        print(f"Model: deepseek/deepseek-r1")
        print(f"Messages: {len(messages)} messages")
        
        if stream_callback:
            # Streaming mode
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=180,
                stream=True
            )
            
            if response.status_code == 200:
                full_response = ""
                for line in response.iter_lines():
                    if line:
                        line_text = line.decode('utf-8')
                        if line_text.startswith('data: '):
                            json_str = line_text[6:]
                            if json_str.strip() == '[DONE]':
                                break
                            try:
                                chunk_data = json.loads(json_str)
                                if 'choices' in chunk_data and len(chunk_data['choices']) > 0:
                                    delta = chunk_data['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        full_response += content
                                        stream_callback(content)
                            except json.JSONDecodeError:
                                continue
                response_text = full_response
            else:
                error_msg = f"OpenRouter API error {response.status_code}: {response.text}"
                print(error_msg)
                return None
        else:
            # Non-streaming mode
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=180
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data['choices'][0]['message']['content']
            else:
                error_msg = f"OpenRouter API error {response.status_code}: {response.text}"
                print(error_msg)
                return None
        
        print(f"\nRaw Response: {response_text[:500]}...")
        
        # Initialize result with content
        result = {
            "content": response_text,
            "model": "deepseek/deepseek-r1"
        }
        
        # Extract and format chain of thought if enabled
        if SHOW_CHAIN_OF_THOUGHT_IN_CONTEXT:
            reasoning = None
            content = response_text
            
            if content:
                # Try both <think> and <thinking> tags
                think_match = re.search(r'<(think|thinking)>(.*?)</\1>', content, re.DOTALL | re.IGNORECASE)
                if think_match:
                    reasoning = think_match.group(2).strip()
                    content = re.sub(r'<(think|thinking)>.*?</\1>', '', content, flags=re.DOTALL | re.IGNORECASE).strip()
            
            display_text = ""
            if reasoning:
                display_text += f"[Chain of Thought]\n{reasoning}\n\n"
            if content:
                display_text += f"[Final Answer]\n{content}"
            
            result["display"] = display_text
            result["content"] = content
        else:
            # Clean up thinking tags from content
            content = response_text
            if content:
                content = re.sub(r'<(think|thinking)>.*?</\1>', '', content, flags=re.DOTALL | re.IGNORECASE).strip()
                result["content"] = content
        
        return result
        
    except Exception as e:
        print(f"Error calling DeepSeek via OpenRouter: {e}")
        print(f"Error type: {type(e)}")
        return None

def setup_image_directory():
    """Create an 'images' directory in the project root if it doesn't exist"""
    image_dir = Path("images")
    image_dir.mkdir(exist_ok=True)
    return image_dir

def cleanup_old_images(image_dir, max_age_hours=24):
    """Remove images older than max_age_hours"""
    current_time = datetime.now()
    for image_file in image_dir.glob("*.jpg"):
        file_age = datetime.fromtimestamp(image_file.stat().st_mtime)
        if (current_time - file_age).total_seconds() > max_age_hours * 3600:
            image_file.unlink()

def load_ai_memory(ai_number):
    """Load AI conversation memory from JSON files"""
    try:
        memory_path = f"memory/ai{ai_number}/conversations.json"
        with open(memory_path, 'r', encoding='utf-8') as f:
            conversations = json.load(f)
            # Ensure we're working with the array part
            if isinstance(conversations, dict) and "memories" in conversations:
                conversations = conversations["memories"]
        return conversations
    except Exception as e:
        print(f"Error loading AI{ai_number} memory: {e}")
        return []

def create_memory_prompt(conversations):
    """Convert memory JSON into conversation examples"""
    if not conversations:
        return ""
    
    prompt = "Previous conversations that demonstrate your personality:\n\n"
    
    # Add example conversations
    for convo in conversations:
        prompt += f"Human: {convo['human']}\n"
        prompt += f"Assistant: {convo['assistant']}\n\n"
    
    prompt += "Maintain this conversation style in your responses."
    return prompt 


def print_conversation_state(conversation):
    print("Current conversation state:")
    for message in conversation:
        content = message.get('content', '')
        # Safely preview content - handle both string and list (structured) content
        if isinstance(content, str):
            preview = content[:50] + "..." if len(content) > 50 else content
        else:
            preview = f"[structured content with {len(content)} parts]"
        print(f"{message['role']}: {preview}")

def list_together_models():
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('TOGETHERAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        response = requests.get(
            "https://api.together.xyz/v1/models",
            headers=headers
        )
        
        print("\nAvailable Together AI Models:")
        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            models = response.json()
            print(json.dumps(models, indent=2))
        else:
            print(f"Error Response: {response.text[:500]}..." if len(response.text) > 500 else f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"Error listing models: {str(e)}")

def start_together_model(model_id):
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('TOGETHERAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        # URL encode the model ID
        encoded_model = url_quote(model_id, safe='')
        start_url = f"https://api.together.xyz/v1/models/{encoded_model}/start"
        
        print(f"\nAttempting to start model: {model_id}")
        print(f"Using URL: {start_url}")
        response = requests.post(
            start_url,
            headers=headers
        )
        
        print(f"Start request status: {response.status_code}")
        print(f"Response: {response.text[:200]}..." if len(response.text) > 200 else f"Response: {response.text}")
        
        if response.status_code == 200:
            print("Model start request successful")
            return True
        else:
            print("Failed to start model")
            return False
            
    except Exception as e:
        print(f"Error starting model: {str(e)}")
        return False

def call_together_api(prompt, conversation_history, model, system_prompt):
    try:
        headers = {
            "Authorization": f"Bearer {os.getenv('TOGETHERAI_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        # Format messages
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
            
        for msg in conversation_history:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })
        
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": model,
            "messages": messages,
            "max_tokens": 500,
            "temperature": 0.9,
            "top_p": 0.95,
        }
        
        response = requests.post(
            "https://api.together.xyz/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code == 200:
            response_data = response.json()
            return response_data['choices'][0]['message']['content']
        else:
            print(f"Together API Error Status: {response.status_code}")
            print(f"Response Body: {response.text[:500]}..." if len(response.text) > 500 else f"Response Body: {response.text}")
            return None
            
    except Exception as e:
        print(f"Error calling Together API: {str(e)}")
        return None

def read_shared_html(*args, **kwargs):
    return ""

def update_shared_html(*args, **kwargs):
    return False

def open_html_in_browser(file_path="conversation_full.html"):
    import webbrowser, os
    full_path = os.path.abspath(file_path)
    webbrowser.open('file://' + full_path)

def create_initial_living_document(*args, **kwargs):
    return ""

def read_living_document(*args, **kwargs):
    return ""

def process_living_document_edits(result, model_name):
    return result

def generate_image_from_text(text, model="google/gemini-3-pro-image-preview"):
    """Generate an image based on text using OpenRouter's image generation API"""
    try:
        # Create a directory for the images if it doesn't exist
        image_dir = Path("images")
        image_dir.mkdir(exist_ok=True)
        
        # Create a timestamp for the image filename (include microseconds to avoid collisions)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        
        # Call OpenRouter API for image generation
        headers = {
            "Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "user",
                    "content": text
                }
            ],
            "modalities": ["image", "text"],
            "max_tokens": 1024  # Limit tokens for image generation to avoid credit issues
        }
        
        print(f"Generating image with {model}...")
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            data=json.dumps(payload),
            timeout=60
        )
        
        if response.status_code == 200:
            result = response.json()
            
            # The generated image will be in the assistant message
            if result.get("choices"):
                message = result["choices"][0].get("message", {})
                
                # Check for images in the message
                if message.get("images"):
                    for image in message["images"]:
                        image_url = image["image_url"]["url"]  # Base64 data URL
                        print(f"Generated image URL (first 50 chars): {image_url[:50]}...")
                        
                        # Handle base64 data URL
                        if image_url.startswith('data:image'):
                            try:
                                # Detect actual image format from data URL header
                                # Format: data:image/jpeg;base64,... or data:image/png;base64,...
                                ext = ".jpg"  # Default to jpg
                                if image_url.startswith('data:image/png'):
                                    ext = ".png"
                                elif image_url.startswith('data:image/gif'):
                                    ext = ".gif"
                                elif image_url.startswith('data:image/webp'):
                                    ext = ".webp"
                                
                                # Extract base64 data after comma
                                base64_data = image_url.split(',', 1)[1] if ',' in image_url else image_url
                                
                                # Decode base64 to image
                                image_data = base64.b64decode(base64_data)
                                image_path = image_dir / f"generated_{timestamp}{ext}"
                                with open(image_path, "wb") as f:
                                    f.write(image_data)
                                
                                print(f"Generated image saved to {image_path}")
                                return {
                                    "success": True,
                                    "image_path": str(image_path),
                                    "timestamp": timestamp
                                }
                            except Exception as e:
                                print(f"Failed to decode base64 image: {e}")
                                return {
                                    "success": False,
                                    "error": f"Failed to decode image: {e}"
                                }
                        else:
                            # If it's a regular URL, download it
                            try:
                                img_response = requests.get(image_url, timeout=30)
                                if img_response.status_code == 200:
                                    image_path = image_dir / f"generated_{timestamp}.png"
                                    with open(image_path, "wb") as f:
                                        f.write(img_response.content)
                                    
                                    print(f"Generated image saved to {image_path}")
                                    return {
                                        "success": True,
                                        "image_path": str(image_path),
                                        "timestamp": timestamp
                                    }
                            except Exception as e:
                                print(f"Failed to download image: {e}")
                                return {
                                    "success": False,
                                    "error": f"Failed to download image: {e}"
                                }
                
                # No images in response
                print(f"No images in response. Message keys: {list(message.keys()) if isinstance(message, dict) else 'non-dict'}")
                return {
                    "success": False,
                    "error": "No images in API response"
                }
            else:
                print(f"No choices in response. Result keys: {list(result.keys()) if isinstance(result, dict) else 'non-dict'}")
                return {
                    "success": False,
                    "error": "No choices in API response"
                }
        else:
            error_msg = f"API error {response.status_code}: {response.text[:500]}"
            print(f"Error generating image: {error_msg}")
            return {
                "success": False,
                "error": error_msg
            }
            
    except Exception as e:
        print(f"Error generating image: {e}")
        return {
            "success": False,
            "error": str(e)
        }


# Gemini image models available for direct API
GEMINI_IMAGE_MODELS = {
    "Gemini 3 Pro Image": "gemini-3-pro-image-preview",
    "Imagen 3": "imagen-3.0-generate-002",
    "Imagen 4 Standard": "imagen-4.0-generate-001",
    "Imagen 4 Ultra": "imagen-4.0-ultra-generate-001",
    "Imagen 4 Fast": "imagen-4.0-fast-generate-001",
}


def generate_image_gemini(
    prompt: str,
    model: str = "imagen-3.0-generate-002",
    api_key: str = None,
    aspect_ratio: str = "1:1",
    number_of_images: int = 1
) -> dict:
    """
    Generate an image using Gemini's direct API (Imagen or Gemini 3 Pro Image).

    Args:
        prompt: Text description of the image to generate
        model: Model ID (imagen-3.0-generate-002, gemini-3-pro-image-preview, etc.)
        api_key: Gemini API key (uses GEMINI_API_KEY env var if not provided)
        aspect_ratio: Image aspect ratio (1:1, 3:4, 4:3, 9:16, 16:9)
        number_of_images: Number of images to generate (1-4)

    Returns:
        dict with success, image_path, timestamp, or error
    """
    api_key = api_key or os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if not api_key:
        return {
            "success": False,
            "error": "Gemini API key not configured. Set GEMINI_API_KEY in .env"
        }

    try:
        image_dir = Path("images")
        image_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")

        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }

        # Different API format for Imagen vs Gemini 3 Pro Image
        if model.startswith("imagen"):
            # Imagen 3/4 uses predict endpoint
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:predict"
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {
                    "sampleCount": min(number_of_images, 4),
                    "aspectRatio": aspect_ratio
                }
            }
            print(f"[Gemini Image] Generating with Imagen: {model}")
        else:
            # Gemini 3 Pro Image uses generateContent endpoint
            endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
            payload = {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {
                    "responseModalities": ["TEXT", "IMAGE"]
                }
            }
            print(f"[Gemini Image] Generating with Gemini model: {model}")

        print(f"[Gemini Image] Prompt: {prompt[:50]}...")
        response = requests.post(endpoint, headers=headers, json=payload, timeout=120)

        if response.status_code != 200:
            error_text = response.text[:500]
            print(f"[Gemini Image] API error {response.status_code}: {error_text}")
            return {
                "success": False,
                "error": f"Gemini API error {response.status_code}: {error_text[:200]}"
            }

        result = response.json()

        # Parse response based on model type
        if model.startswith("imagen"):
            # Imagen response format
            predictions = result.get("predictions", [])
            if not predictions:
                return {"success": False, "error": "No images generated"}

            # Get first image
            image_data = predictions[0].get("bytesBase64Encoded")
            if not image_data:
                return {"success": False, "error": "No image data in response"}

            # Imagen returns raw base64 without data URL prefix
            image_bytes = base64.b64decode(image_data)
            image_path = image_dir / f"generated_{timestamp}.png"
            with open(image_path, "wb") as f:
                f.write(image_bytes)

        else:
            # Gemini 3 Pro Image response format
            candidates = result.get("candidates", [])
            if not candidates:
                # Check for blocked content
                block_reason = result.get("promptFeedback", {}).get("blockReason")
                if block_reason:
                    return {"success": False, "error": f"Content blocked: {block_reason}"}
                return {"success": False, "error": "No response from Gemini"}

            # Find image part in response
            parts = candidates[0].get("content", {}).get("parts", [])
            image_data = None
            for part in parts:
                if "inlineData" in part:
                    image_data = part["inlineData"].get("data")
                    mime_type = part["inlineData"].get("mimeType", "image/png")
                    break

            if not image_data:
                # Model may have returned text only
                text_response = ""
                for part in parts:
                    if "text" in part:
                        text_response += part["text"]
                return {"success": False, "error": f"No image generated. Model response: {text_response[:200]}"}

            # Determine file extension from mime type
            ext = ".png"
            if "jpeg" in mime_type or "jpg" in mime_type:
                ext = ".jpg"
            elif "webp" in mime_type:
                ext = ".webp"

            image_bytes = base64.b64decode(image_data)
            image_path = image_dir / f"generated_{timestamp}{ext}"
            with open(image_path, "wb") as f:
                f.write(image_bytes)

        print(f"[Gemini Image] Saved to {image_path}")
        return {
            "success": True,
            "image_path": str(image_path),
            "timestamp": timestamp
        }

    except requests.exceptions.Timeout:
        return {"success": False, "error": "Gemini image request timed out"}
    except Exception as e:
        print(f"[Gemini Image] Error: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


# -------------------- Sora Video Utilities --------------------
def ensure_videos_dir() -> Path:
    """Create a 'videos' directory in the project root if it doesn't exist."""
    videos_dir = Path("videos")
    videos_dir.mkdir(exist_ok=True)
    return videos_dir

def generate_video_with_sora(
    prompt: str,
    model: str = "sora-2",
    seconds: int | None = None,
    size: str | None = None,
    poll_interval_seconds: float = 5.0,
) -> dict:
    """
    Create a Sora video via REST API, poll until completion, and save MP4 to videos/.

    Returns a dict with keys: success, video_id, status, video_path (when completed), error
    """
    try:
        api_key = os.getenv('OPENAI_API_KEY')
        if not api_key:
            return {"success": False, "error": "OPENAI_API_KEY not set"}

        base_url = os.getenv('OPENAI_BASE_URL', 'https://api.openai.com/v1')
        verbose = os.getenv('SORA_VERBOSE', '1').strip() == '1'
        def vlog(msg: str):
            if verbose:
                print(msg)
        headers_json = {
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json'
        }

        # Start render job
        payload = {"model": model, "prompt": prompt}
        if seconds is not None:
            payload["seconds"] = str(seconds)
        if size is not None:
            payload["size"] = size

        create_url = f"{base_url}/videos"
        vlog(f"[Sora] Create: url={create_url} model={model} seconds={seconds} size={size}")
        vlog(f"[Sora] Prompt (truncated): {prompt[:200]}{'...' if len(prompt) > 200 else ''}")
        resp = requests.post(create_url, headers=headers_json, json=payload, timeout=60)
        if not resp.ok:
            err_text = resp.text
            try:
                err_json = resp.json()
                vlog(f"[Sora] Create error JSON: {err_json}")
            except Exception:
                vlog(f"[Sora] Create error TEXT: {err_text}")
            return {"success": False, "error": f"Create failed {resp.status_code}: {err_text}"}
        job = resp.json()
        video_id = job.get('id')
        status = job.get('status')
        vlog(f"[Sora] Job started: id={video_id} status={status}")
        if not video_id:
            return {"success": False, "error": "No video id returned from create()"}

        # Poll until completion/failed
        retrieve_url = f"{base_url}/videos/{video_id}"
        last_status = status
        last_progress = None
        while status in ("queued", "in_progress"):
            time.sleep(poll_interval_seconds)
            r = requests.get(retrieve_url, headers=headers_json, timeout=60)
            if not r.ok:
                vlog(f"[Sora] Retrieve failed: code={r.status_code} body={r.text}")
                return {"success": False, "video_id": video_id, "error": f"Retrieve failed {r.status_code}: {r.text}"}
            job = r.json()
            status = job.get('status')
            progress = job.get('progress')
            if status != last_status or progress != last_progress:
                vlog(f"[Sora] Status update: status={status} progress={progress}")
                last_status = status
                last_progress = progress

        if status != "completed":
            vlog(f"[Sora] Final non-completed status: {status} job={job}")
            return {"success": False, "video_id": video_id, "status": status, "error": f"Final status: {status}"}

        # Download the MP4
        content_url = f"{base_url}/videos/{video_id}/content"
        vlog(f"[Sora] Download: url={content_url}")
        rc = requests.get(content_url, headers={'Authorization': f'Bearer {api_key}'}, stream=True, timeout=300)
        if not rc.ok:
            vlog(f"[Sora] Download failed: code={rc.status_code} body={rc.text}")
            return {"success": False, "video_id": video_id, "status": status, "error": f"Download failed {rc.status_code}: {rc.text}"}

        videos_dir = ensure_videos_dir()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safe_snippet = re.sub(r"[^a-zA-Z0-9_-]", "_", prompt[:40]) or "video"
        out_path = videos_dir / f"{timestamp}_{safe_snippet}.mp4"
        with open(out_path, "wb") as f:
            for chunk in rc.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    f.write(chunk)

        vlog(f"[Sora] Saved video: {out_path}")
        return {
            "success": True,
            "video_id": video_id,
            "status": status,
            "video_path": str(out_path)
        }
    except Exception as e:
        logging.exception("Sora video generation error")
        return {"success": False, "error": str(e)}


# ============================================================================
# GEMINI DIRECT API SUPPORT
# ============================================================================

def _sanitize_schema_for_gemini(schema):
    """
    Remove JSON Schema fields not supported by Gemini API.

    Gemini's function calling API doesn't support:
    - additionalProperties
    - default
    """
    if not isinstance(schema, dict):
        return schema

    unsupported = {"additionalProperties", "default"}
    cleaned = {}

    for key, value in schema.items():
        if key not in unsupported:
            if isinstance(value, dict):
                cleaned[key] = _sanitize_schema_for_gemini(value)
            elif isinstance(value, list):
                cleaned[key] = [
                    _sanitize_schema_for_gemini(item) if isinstance(item, dict) else item
                    for item in value
                ]
            else:
                cleaned[key] = value

    return cleaned


def _extract_gemini_thoughts(text: str) -> tuple:
    """
    Extract thought signatures from Gemini 3 responses.

    Gemini 3 may return thoughts in <thinking>...</thinking> tags.
    Similar to DeepSeek R1 handling.

    Returns:
        Tuple of (clean_text, thoughts or None)
    """
    import re

    thinking_match = re.search(r'<thinking>(.*?)</thinking>', text, re.DOTALL)
    if thinking_match:
        thoughts = thinking_match.group(1).strip()
        clean_text = re.sub(r'<thinking>.*?</thinking>', '', text, flags=re.DOTALL).strip()
        return clean_text, thoughts

    return text, None


def fetch_gemini_models(api_key: str) -> list:
    """
    Fetch available Gemini models that support text generation.

    Calls the Gemini API models.list endpoint and filters for models
    that support generateContent (text generation).

    Args:
        api_key: Gemini API key

    Returns:
        List of dicts with 'id' and 'name' keys, or empty list on error.
    """
    if not api_key:
        return []

    url = "https://generativelanguage.googleapis.com/v1beta/models"
    headers = {
        "x-goog-api-key": api_key,
        "Content-Type": "application/json"
    }

    try:
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            print(f"[Gemini Models] Error {response.status_code}: {response.text[:200]}")
            return []

        data = response.json()
        models = data.get("models", [])

        # Filter for models that support text generation
        text_models = [
            {
                "id": m.get("name", "").replace("models/", ""),
                "name": m.get("displayName", m.get("name", "").replace("models/", "")),
                "description": m.get("description", ""),
            }
            for m in models
            if "generateContent" in m.get("supportedGenerationMethods", [])
        ]

        # Sort by name for consistent ordering
        text_models.sort(key=lambda x: x["name"])
        return text_models

    except Exception as e:
        print(f"[Gemini Models] Exception: {e}")
        return []


# =============================================================================
# Gemini Interactions API (Beta)
# =============================================================================

def _convert_tools_to_interactions_format(tools: list) -> list:
    """
    Convert OpenAI-style tools to Interactions API flat format.

    OpenAI: {"type": "function", "function": {"name", "description", "parameters"}}
    Interactions: {"type": "function", "name", "description", "parameters"}
    """
    if not tools:
        return []

    result = []
    for tool in tools:
        if tool.get("type") == "function":
            fn = tool.get("function", {})
            interactions_tool = {
                "type": "function",
                "name": fn.get("name", ""),
                "description": fn.get("description", ""),
            }
            # Only include parameters if present (sanitized for Gemini compatibility)
            if fn.get("parameters"):
                interactions_tool["parameters"] = _sanitize_schema_for_gemini(fn["parameters"])
            result.append(interactions_tool)

    return result


def _convert_messages_to_interactions_format(messages: list, current_prompt=None) -> list:
    """
    Convert OpenAI-style messages to Interactions API input format.

    The Interactions API expects:
    - input: list of turns with {role: "user"|"model", content: ...}
    - content can be: string, list of content objects, or outputs from previous turn

    Returns:
        List of turns for the 'input' field
    """
    if not messages and not current_prompt:
        return []

    turns = []

    for msg in (messages or []):
        role = msg.get("role", "user")
        content = msg.get("content", "")

        # Map roles (OpenAI/Anthropic → Gemini)
        if role == "assistant":
            gemini_role = "model"
        elif role == "system":
            # System messages are handled via system_instruction, skip here
            continue
        else:
            gemini_role = "user"

        # Handle structured content (with images)
        if isinstance(content, list):
            parts = []
            for part in content:
                if part.get("type") == "text":
                    parts.append({"type": "text", "text": part.get("text", "")})
                elif part.get("type") == "image_url":
                    # OpenAI format: {"type": "image_url", "image_url": {"url": "data:..."}}
                    url = part.get("image_url", {}).get("url", "")
                    if url.startswith("data:"):
                        # Extract base64 from data URL
                        try:
                            header, b64_data = url.split(",", 1)
                            mime = header.split(":")[1].split(";")[0]
                            parts.append({
                                "type": "image",
                                "data": b64_data,
                                "mime_type": mime
                            })
                        except:
                            pass
                elif part.get("type") == "image":
                    # Already in Anthropic format
                    source = part.get("source", {})
                    if source.get("type") == "base64":
                        parts.append({
                            "type": "image",
                            "data": source.get("data", ""),
                            "mime_type": source.get("media_type", "image/png")
                        })
            if parts:
                turns.append({"role": gemini_role, "content": parts})
        elif content:
            turns.append({"role": gemini_role, "content": content})

    # Add current prompt as the last user turn
    if current_prompt:
        if isinstance(current_prompt, list):
            # Structured content with images
            parts = []
            for part in current_prompt:
                if part.get("type") == "text":
                    parts.append({"type": "text", "text": part.get("text", "")})
                elif part.get("type") == "image":
                    source = part.get("source", {})
                    if source.get("type") == "base64":
                        parts.append({
                            "type": "image",
                            "data": source.get("data", ""),
                            "mime_type": source.get("media_type", "image/png")
                        })
            if parts:
                turns.append({"role": "user", "content": parts})
        else:
            turns.append({"role": "user", "content": current_prompt})

    return turns


def _parse_interactions_response(response_data: dict) -> tuple:
    """
    Parse Interactions API response into text and function calls.

    The response structure:
    {
        "id": "...",
        "status": "completed",
        "outputs": [
            {"type": "text", "text": "..."},
            {"type": "function_call", "id": "...", "name": "...", "arguments": {...}}
        ],
        "usage": {...}
    }

    Returns:
        Tuple of (text_content, list of function_calls)
        function_calls format: [{"id": "...", "name": "...", "args": {...}}, ...]
    """
    text_parts = []
    function_calls = []

    outputs = response_data.get("outputs", [])
    for output in outputs:
        output_type = output.get("type", "")

        if output_type == "text":
            text_parts.append(output.get("text", ""))
        elif output_type == "function_call":
            function_calls.append({
                "id": output.get("id", ""),
                "name": output.get("name", ""),
                "args": output.get("arguments", {}),
                "thoughtSignature": output.get("thoughtSignature")  # Required for Gemini 3
            })
        # Skip other types like google_search_result, code_execution_result, url_context_result

    return "".join(text_parts), function_calls


def call_gemini_interactions_api(
    prompt,
    conversation_history,
    model,
    system_prompt,
    stream_callback=None,  # Not implemented yet
    tools=None,
    tool_executor=None,
    thinking_level="high",
    enable_google_search=False,
    enable_code_execution=False,
    enable_url_context=False,
):
    """
    Call the Gemini Interactions API (Beta).

    This is the new unified API for Gemini that provides:
    - Built-in tools (Google Search, Code Execution, URL Context)
    - Thinking level control (minimal, low, medium, high)
    - Simplified tool schema format
    - Optional server-side state management

    Args:
        prompt: The current user message (string or structured content with images)
        conversation_history: List of previous messages in OpenAI format
        model: Gemini model ID (e.g., 'gemini-3-flash-preview')
        system_prompt: System instructions for the model
        stream_callback: Not implemented (streaming not supported yet)
        tools: Optional list of tool schemas (OpenAI format - will be converted)
        tool_executor: Optional callback function(name, args) -> dict to execute tool calls
        thinking_level: Reasoning depth - 'minimal', 'low', 'medium', 'high' (default: 'high')
        enable_google_search: Enable built-in Google Search grounding
        enable_code_execution: Enable built-in Python code execution
        enable_url_context: Enable built-in URL fetch and summarization

    Returns:
        Response string, or None on error
    """
    # Get API key (with GOOGLE_API_KEY fallback)
    api_key = os.getenv('GEMINI_API_KEY') or os.getenv('GOOGLE_API_KEY')
    if not api_key:
        logger.error("[Gemini Interactions] No API key. Set GEMINI_API_KEY or GOOGLE_API_KEY in .env")
        return "Error: Gemini API key not configured. Please set GEMINI_API_KEY in .env"

    try:
        # Convert messages to Interactions API format
        input_data = _convert_messages_to_interactions_format(
            conversation_history or [], prompt
        )

        # Build tools list - custom functions OR built-in tools (can't mix in Interactions API)
        # Note: Multi-tool use (mixing function calling with built-in tools) is only supported
        # in the Live API (WebSocket streaming), not the standard Interactions API endpoint.
        # See: https://ai.google.dev/gemini-api/docs/function-calling#multi-tool-use
        custom_tools = _convert_tools_to_interactions_format(tools or [])

        if custom_tools:
            # Use custom function tools (our weather, sheets, memory, etc.)
            all_tools = custom_tools
        else:
            # No custom tools - can use built-in tools
            all_tools = []
            if enable_google_search:
                all_tools.append({"type": "google_search"})
            if enable_code_execution:
                all_tools.append({"type": "code_execution"})
            if enable_url_context:
                all_tools.append({"type": "url_context"})

        # Build generation config
        generation_config = {
            "temperature": 1.0,
            "max_output_tokens": 4000
        }

        # Only add thinking_level for models that support it (2.5+)
        # Note: 'minimal' and 'medium' are Flash-only
        if thinking_level and thinking_level in ['minimal', 'low', 'medium', 'high']:
            generation_config["thinking_level"] = thinking_level

        # Build payload
        payload = {
            "model": model,
            "input": input_data,
            "generation_config": generation_config,
            "store": False  # Don't store interactions server-side (privacy)
        }

        # Add system instruction if provided
        if system_prompt:
            payload["system_instruction"] = system_prompt

        # Add tools if any
        if all_tools:
            payload["tools"] = all_tools
            # Log which type of tools we're using (can't mix in Interactions API)
            if custom_tools:
                logger.info(f"[Gemini Interactions] Tools enabled: {len(all_tools)} custom function(s)")
            else:
                builtin_types = [t.get("type") for t in all_tools]
                logger.info(f"[Gemini Interactions] Tools enabled: built-in: {', '.join(builtin_types)}")

        # API endpoint
        endpoint = "https://generativelanguage.googleapis.com/v1beta/interactions"
        headers = {
            "x-goog-api-key": api_key,
            "Content-Type": "application/json"
        }

        logger.info(f"[Gemini Interactions] Request to: {model}")
        logger.info(f"[Gemini Interactions] Input turns: {len(input_data)}, thinking_level: {thinking_level}")

        # Multi-turn tool calling loop
        max_iterations = 15
        # Cache tool call results to avoid duplicate API calls within same response
        tool_call_cache = {}  # {(fn_name, sorted_args_json): result}

        for iteration in range(max_iterations):
            logger.info(f"[Gemini Interactions] Tool iteration {iteration + 1}/{max_iterations}")
            response = requests.post(endpoint, headers=headers, json=payload, timeout=120)

            if response.status_code != 200:
                error_text = response.text
                logger.error(f"[Gemini Interactions] API error {response.status_code}: {error_text[:500]}")

                # Parse common errors
                if response.status_code == 400:
                    return f"Error: Invalid request - {error_text[:200]}"
                elif response.status_code == 401:
                    return "Error: Invalid Gemini API key"
                elif response.status_code == 403:
                    return "Error: API key doesn't have access to this model"
                elif response.status_code == 404:
                    return f"Error: Model or endpoint not found: {model}"
                elif response.status_code == 429:
                    return "Error: Gemini rate limit exceeded. Try again later."
                else:
                    return f"Error: Gemini API error {response.status_code}"

            response_data = response.json()
            text, function_calls = _parse_interactions_response(response_data)

            # Check for status
            status = response_data.get("status", "")
            if status == "failed":
                error_msg = response_data.get("error", {}).get("message", "Unknown error")
                logger.error(f"[Gemini Interactions] Failed: {error_msg}")
                return f"Error: {error_msg}"

            # Handle function calls
            if function_calls and tool_executor:
                logger.info(f"[Gemini Interactions] Model requested {len(function_calls)} tool call(s)")

                for fc in function_calls:
                    fn_name = fc["name"]
                    fn_args = fc["args"]
                    call_id = fc["id"]

                    # Check for duplicate tool call (deduplication)
                    try:
                        cache_key = (fn_name, json.dumps(fn_args, sort_keys=True))
                    except (TypeError, ValueError):
                        cache_key = None  # Can't cache if args aren't serializable

                    if cache_key and cache_key in tool_call_cache:
                        result = tool_call_cache[cache_key]
                        logger.info(f"[Gemini Interactions] Using cached result for: {fn_name}({fn_args})")
                    else:
                        logger.info(f"[Gemini Interactions] Executing tool: {fn_name}({fn_args})")

                        # Execute tool
                        try:
                            result = tool_executor(fn_name, fn_args)
                            # Cache the result (only cache successful executions to avoid caching transient errors)
                            if cache_key and isinstance(result, dict) and result.get("success", True):
                                tool_call_cache[cache_key] = result
                        except Exception as e:
                            logger.error(f"[Gemini Interactions] Tool execution error: {e}")
                            result = {"success": False, "error": str(e)}

                    # Check for meta-tool expansion signal
                    if isinstance(result, dict) and result.get("expansion_needed"):
                        logger.info(f"[Gemini Interactions] Meta-tool expansion requested for {fn_name}")
                        return result  # Return the expansion signal

                    logger.debug(f"[Gemini Interactions] Tool result: {str(result)[:200]}")

                    # Add function result to input for next iteration
                    # Interactions API format for function results
                    function_result = {
                        "type": "function_result",
                        "name": fn_name,
                        "call_id": call_id,
                        "result": str(result) if not isinstance(result, str) else result
                    }
                    # Include thoughtSignature if present (required for Gemini 3)
                    # See: https://ai.google.dev/gemini-api/docs/gemini-3
                    if fc.get("thoughtSignature"):
                        function_result["thoughtSignature"] = fc["thoughtSignature"]

                    input_data.append({
                        "role": "user",
                        "content": [function_result]
                    })

                # Update payload for next iteration
                payload["input"] = input_data
                continue

            # No function calls - return text response
            if text:
                # Extract any thinking tags (Gemini 3 feature)
                clean_text, thoughts = _extract_gemini_thoughts(text)
                if thoughts:
                    logger.debug(f"[Gemini Interactions] Extracted thoughts: {thoughts[:100]}...")
                logger.info(f"[Gemini Interactions] Returning response ({len(clean_text)} chars): {clean_text[:100]}...")
                return clean_text

            # Empty response - return user-friendly message instead of None
            logger.warning("[Gemini Interactions] Empty response received from model")
            return "I processed your request but couldn't generate a response. Please try rephrasing your question."

        # Max iterations reached - provide helpful feedback
        logger.warning(f"[Gemini Interactions] Max tool iterations ({max_iterations}) reached")
        return "I tried to gather comprehensive data but hit a complexity limit. Please try asking a more focused question."

    except requests.exceptions.Timeout:
        logger.error("[Gemini Interactions] Request timed out")
        return "Error: Gemini request timed out"
    except requests.exceptions.RequestException as e:
        logger.error(f"[Gemini Interactions] Network error: {e}")
        return f"Error: Network error - {str(e)}"
    except Exception as e:
        logger.error(f"[Gemini Interactions] Unexpected error: {e}", exc_info=True)
        return f"Error: {str(e)}"



# DEPRECATED: call_gemini_api() removed - use call_gemini_interactions_api() instead

