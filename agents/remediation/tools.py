# agents/remediation/tools.py
import os
from typing import List, Dict, Optional
from litellm import completion
from rag.retriever import RAGRetriever
from config import LLM_MODEL, REPO_LOCAL_PATH

_retriever: Optional[RAGRetriever] = None


def get_retriever() -> RAGRetriever:
    global _retriever
    if _retriever is None:
        _retriever = RAGRetriever()
    return _retriever


def rag_retrieve(rule_id: str, code_snippet: str, top_k: int = 3) -> List[Dict]:
    query = f"{rule_id}: {code_snippet[:200]}"
    return get_retriever().search(query, top_k=top_k)


def read_file(relative_path: str) -> str:
    full_path = os.path.join(REPO_LOCAL_PATH, relative_path)
    with open(full_path, "r", encoding="utf-8") as f:
        return f.read()


def write_file(relative_path: str, content: str) -> None:
    full_path = os.path.join(REPO_LOCAL_PATH, relative_path)
    with open(full_path, "w", encoding="utf-8") as f:
        f.write(content)


def call_llm(rule_id: str, rule_description: str, remediation_guidance: str,
             rag_context: str, file_path: str,
             line_start: int, line_end: int, code_snippet: str) -> str:
    system_prompt = (
        "You are a Java code fixer specializing in SonarQube rule remediation. "
        "You MUST preserve the exact indentation style of the original code. "
        "Return ONLY the fixed code block — no explanations, no markdown fences."
    )
    user_prompt = (
        f"Rule: {rule_id} — {rule_description}\n"
        f"Remediation guidance: {remediation_guidance}\n\n"
        f"Similar rule examples from knowledge base:\n{rag_context}\n\n"
        f"Original code (lines {line_start}–{line_end} of {file_path}):\n"
        f"{code_snippet}\n\n"
        "Fix the above code to resolve the SonarQube rule violation."
    )
    response = completion(
        model=LLM_MODEL,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=2048,
        temperature=0.1,
    )
    return response.choices[0].message.content
