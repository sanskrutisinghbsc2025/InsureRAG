# structured_pipeline.py
import asyncio
from typing import List
import pandas as pd
from fastapi import HTTPException

from langchain_google_genai import ChatGoogleGenerativeAI

async def handle_excel(
    doc_path: str, 
    questions: List[str], 
    api_key_manager,
    mega_prompt # We now accept the same MEGA_PROMPT as the RAG tool
) -> List[str]:
    """
    Handles queries on Excel files by converting the sheet to a CSV string
    and passing it to the LLM as context.
    """
    print("--- Tool Selected: Structured Data Pipeline (CSV as Context) ---")
    try:
        # Read the entire Excel file into a pandas DataFrame
        df = pd.read_excel(doc_path)
        
        # --- YOUR BRILLIANT IDEA: Convert the entire DataFrame to a CSV string ---
        # This becomes the context for the LLM.
        # We drop the index to avoid confusing the LLM with unnecessary numbers.
        context = df.to_csv(index=False)

        if not context:
            return ["Could not read any data from the Excel file."] * len(questions)

        # We can now use the exact same batched answer generation as our RAG pipeline.
        # This is efficient and robust.
        BATCH_SIZE = 6
        final_answers = ["The information is not available in the provided document."] * len(questions)
        
        # We create a list of questions, each with the *same* full CSV context
        qa_pairs = [(q, context) for q in questions]

        for i in range(0, len(qa_pairs), BATCH_SIZE):
            batch = qa_pairs[i:i + BATCH_SIZE]
            
            key = api_key_manager.get_key()
            # We can use the faster Flash model, as it's excellent at reading structured text
            llm = ChatGoogleGenerativeAI(model="gemini-flash-latest", temperature=0, google_api_key=key)
            final_answer_chain = mega_prompt | llm
            
            print(f"--- Processing Excel batch {i//BATCH_SIZE + 1} with key '...{key[-4:]}' ---")

            formatted_input = ""
            for j, (question, ctx) in enumerate(batch):
                original_q_num = i + j + 1
                formatted_input += f"Question {original_q_num}:\n{question}\n\nContext {original_q_num}:\n{ctx}\n\n---\n\n"
            
            result = await final_answer_chain.ainvoke({"formatted_questions_and_contexts": formatted_input})
            final_text_block = result.content if hasattr(result, "content") else str(result)
            if isinstance(final_text_block, list): final_text_block = "".join(x.get("text", "") if isinstance(x, dict) else str(x) for x in final_text_block)
            
            import re
            matches = re.finditer(r'Answer\s+(\d+)[\s:]*(.*?)(?=\nAnswer\s+\d+|$)', final_text_block, re.DOTALL | re.IGNORECASE)
            for match in matches:
                try:
                    q_num = int(match.group(1)) - 1
                    if 0 <= q_num < len(final_answers):
                        final_answers[q_num] = match.group(2).strip()
                except (ValueError, IndexError):
                    continue
        
        return final_answers

    except Exception as e:
        print(f"Error in structured_pipeline: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to process the Excel file: {e}")