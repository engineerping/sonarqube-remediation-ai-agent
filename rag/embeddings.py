# rag/embeddings.py
import os
from typing import List


class EmbeddingModel:
    """Wraps OpenAI text-embedding-3-small or local sentence-transformers.

    Set EMBEDDING_MODEL=openai (default) or EMBEDDING_MODEL=local.
    """

    def __init__(self):
        self.mode = os.getenv("EMBEDDING_MODEL", "openai")
        self._local_model = None
        self.dimension = 1536

        if self.mode == "local":
            from sentence_transformers import SentenceTransformer
            self._local_model = SentenceTransformer("all-MiniLM-L6-v2")
            self.dimension = 384

    def embed(self, text: str) -> List[float]:
        if self.mode == "local":
            return self._local_model.encode(text).tolist()
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text,
        )
        return response.data[0].embedding

    def embed_batch(self, texts: List[str]) -> List[List[float]]:
        if self.mode == "local":
            return self._local_model.encode(texts).tolist()
        from openai import OpenAI
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=texts,
        )
        return [item.embedding for item in response.data]
