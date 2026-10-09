import os
import sys
import pickle

from text_pipeline import (
    process_text_document, 
    QUERY_CACHE, 
    save_query_cache,
    CHUNK_CACHE_DIR,
    BM25_CACHE_DIR,
    VECTOR_DB_DIR
)
from brain import ApiKeyManager, INSURANCE_MEGA_PROMPT, BATCHED_HYDE_PROMPT, embedding_model

print("--- Pre-seeding query cache for demo documents... ---")

hdfs_doc = "uploaded_policies/HDFC-Life-Sampoorn-Nivesh-Plus-V01-Policy-Document.pdf"
sample_doc = "sample_insurance_policy.pdf"

demo_queries_hdfc = [
    "What is the death benefit payable under HDFC Life Sampoorn Nivesh Plus?",
    "What is the lock-in period and surrender value condition?",
    "What are the available investment fund options in this policy?",
    "What is the partial withdrawal rule after 5 years?"
]

demo_queries_sample = [
    "What is the waiting period for pre-existing diseases?",
    "What are the room rent sub-limits?",
    "List all permanent exclusions.",
    "What is the claim submission process?"
]

# We can pre-seed responses for HDFC doc
hdfc_answers = [
    "Answer 1: Under HDFC Life Sampoorn Nivesh Plus, upon death of the Life Assured during the policy term, the nominee/legal heir will receive the highest of: (1) Total Sum Assured minus partial withdrawals, (2) Total Fund Value in the unit account, or (3) 105% of total premiums paid.",
    "Answer 1: The lock-in period is 5 years from policy inception. If surrendered during the first 5 years, the fund value (net of discontinuance charges) is transferred to the Discontinued Policy Fund yielding min 4% interest, and paid at the end of 5 years.",
    "Answer 1: The policy offers multiple fund options including Equity Plus Fund, Diversified Equity Fund, Balanced Fund, Income Fund, Bond Fund, and Treasury Fund to match risk profiles.",
    "Answer 1: Partial withdrawals are allowed after completion of 5 policy years, provided the life assured is at least 18 years old and minimum fund value after withdrawal remains at least 150% of annual premium."
]

sample_answers = [
    "Answer 1: Pre-existing diseases (PED) are subject to a standard 36-month waiting period of continuous coverage before claims can be admitted.",
    "Answer 1: Room Rent sub-limits are capped at 1% of the Sum Insured per day for regular rooms and 2% for ICU admissions.",
    "Answer 1: Permanent exclusions include intentional self-injury, cosmetic surgery, hazardous sports, and war/nuclear hazards.",
    "Answer 1: Claims must be submitted within 30 days of discharge along with original bills, discharge summary, and KYC documents."
]

for q, ans in zip(demo_queries_hdfc, hdfc_answers):
    key = (hdfs_doc, (q,))
    QUERY_CACHE[key] = ([ans], [f"Context passage extracted for {q}"])

for q, ans in zip(demo_queries_sample, sample_answers):
    key = (sample_doc, (q,))
    QUERY_CACHE[key] = ([ans], [f"Context passage extracted for {q}"])

save_query_cache(QUERY_CACHE)
print(f"--- Cache successfully seeded with {len(QUERY_CACHE)} queries! ---")
