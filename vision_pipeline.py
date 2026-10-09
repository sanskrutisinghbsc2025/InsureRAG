# vision_pipeline.py
import asyncio
from typing import List
from fastapi import HTTPException

from langchain_community.document_loaders import UnstructuredImageLoader
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

async def handle_image(
    image_path: str, 
    questions: List[str], 
    api_key_manager
) -> List[str]:
    """
    Handles queries on image files by performing OCR to extract text and then using an LLM to answer.
    """
    print("--- Tool Selected: Vision Pipeline ---")
    try:
        # The UnstructuredImageLoader uses OCR to "read" the image
        print(f"--- Performing OCR on image: {image_path} ---")
        loader = UnstructuredImageLoader(image_path)
        docs = loader.load()
        context = "\n".join([doc.page_content for doc in docs])

        if not context or context.isspace():
            return ["Could not extract any readable text from the image."] * len(questions)
        
        print(f"--- OCR successful. Extracted context length: {len(context)} ---")

        # Now that we have the text, we can use a standard Q&A chain
        key = api_key_manager.get_key()
        # We use a powerful model as it needs to interpret potentially messy OCR output
        llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=key)
        
        prompt = ChatPromptTemplate.from_template("""
        You are an expert at reading and interpreting text extracted from tables in images.
        Your task is to answer the user's question with extreme precision based ONLY on the provided text.

        **Here is an example of the kind of reasoning you must perform:**

        <example>
        Context:
        Sum Insured | Room Limit
        --- | ---
        Up to 3 Lacs | 1% of SI
        5 to 10 Lacs | 2% of SI

        Question: What is the room limit for a sum insured of 2 lakhs?

        Answer: For a sum insured of 2 lakhs, the room limit is 1% of the Sum Insured, as it falls into the "Up to 3 Lacs" category.
        </example>
        
        **Now, follow these rules for the real task:**
        1.  Analyze the provided context to find the answer.
        2.  If the user's question involves a number that falls within a range in the context, you MUST use the data for that range to form your answer.
        3.  If the answer is truly not in the text, you MUST state: "The information is not available in the provided document."

        **CONTEXT FOR THE TASK:**
        {context}

        **QUESTION FOR THE TASK:**
        {question}

        **YOUR ANSWER:**
        """)
        chain = prompt | llm
        
        async def ask_chain(question: str):
            """A helper function to run a single question through the chain."""
            try:
                result = await chain.ainvoke({"context": context, "question": question})
                return result.content if hasattr(result, "content") else str(result)
            except Exception as e:
                print(f"Vision Chain Error for question '{question}': {e}")
                return f"The LLM encountered an error processing this question."

        # Run all questions concurrently
        tasks = [ask_chain(q) for q in questions]
        answers = await asyncio.gather(*tasks)
        return answers

    except Exception as e:
        print(f"Error in vision_pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process the image file: {e}")