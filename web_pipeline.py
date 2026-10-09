# web_pipeline.py
import asyncio
from typing import List
import aiohttp
from fastapi import HTTPException

# We now need an LLM to parse the response if it's not JSON
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

async def handle_web_endpoint(
    doc_url: str, 
    questions: List[str],
    api_key_manager
) -> List[str]:
    """
    Handles fetching data from a web endpoint, intelligently parsing either JSON or HTML,
    and using an LLM to extract the required information.
    """
    print("--- Tool Selected: Web Pipeline ---")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(doc_url) as response:
                response.raise_for_status()
                
                # --- THE FIX: Intelligent Content Handling ---
                content_type = response.headers.get("Content-Type", "").lower()
                
                if "application/json" in content_type:
                    print("--- Web Tool: Detected JSON response. ---")
                    data = await response.json()
                    # Directly extract the token if possible
                    token = data.get("secret_token")
                    if token:
                        print(f"--- Successfully extracted token directly from JSON: {token[:10]}... ---")
                        return [token] * len(questions)
                    else:
                        # Fallback to LLM if key is not found
                        response_text = str(data)
                else:
                    print("--- Web Tool: Detected non-JSON response (e.g., HTML). Reading as text. ---")
                    response_text = await response.text()

        # --- LLM EXTRACTION STEP ---
        # If the token wasn't found directly, use an LLM to find it in the raw text.
        print("--- Using LLM to extract secret token from the response text... ---")
        key = api_key_manager.get_key()
        llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=key)
        
        prompt = ChatPromptTemplate.from_template("""
        You are an expert at parsing raw data from web pages and APIs.
        Your task is to find a "secret token" within the following text content and extract it.
        The token is a long, random-looking string.
        You must return ONLY the token itself, with no extra explanation or text.
        If you cannot find a token, you must return the string "TOKEN_NOT_FOUND".

        Content to analyze:
        {raw_text}

        The Secret Token:
        """)
        chain = prompt | llm
        
        result = await chain.ainvoke({"raw_text": response_text})
        extracted_token = (result.content if hasattr(result, "content") else str(result)).strip()

        if "TOKEN_NOT_FOUND" in extracted_token:
            return ["Could not find a secret token in the web page content."] * len(questions)
        
        print(f"--- Successfully extracted token via LLM: {extracted_token[:10]}... ---")
        return [extracted_token] * len(questions)

    except aiohttp.ClientError as e:
        raise HTTPException(status_code=400, detail=f"Failed to fetch from endpoint: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred in the web pipeline: {e}")