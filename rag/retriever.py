# rag/retriever.py
import os
from typing import List, Dict
import psycopg2
from psycopg2.extras import RealDictCursor
from pgvector.psycopg2 import register_vector
from rag.embeddings import EmbeddingModel


CREATE_TABLE_SQL = """
CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS sonar_rules (
    id          SERIAL PRIMARY KEY,
    rule_key    VARCHAR(100) UNIQUE NOT NULL,
    name        TEXT NOT NULL,
    description TEXT,
    remediation TEXT,
    severity    VARCHAR(20),
    embedding   vector({dim})
);

CREATE INDEX IF NOT EXISTS sonar_rules_embedding_idx
    ON sonar_rules USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);
"""


class RAGRetriever:
    def __init__(self):
        self.dsn = os.environ["PGVECTOR_DSN"]
        self.embedder = EmbeddingModel()
        self._ensure_table()

    def _create_table_sql(self) -> str:
        return CREATE_TABLE_SQL.format(dim=self.embedder.dimension)

    def _conn(self):
        conn = psycopg2.connect(self.dsn)
        register_vector(conn)
        return conn

    def _ensure_table(self):
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute(self._create_table_sql())
            conn.commit()

    def upsert(self, rule_key: str, name: str, description: str,
               remediation: str, severity: str, embedding: List[float]):
        with self._conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO sonar_rules
                        (rule_key, name, description, remediation, severity, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (rule_key) DO UPDATE SET
                        name        = EXCLUDED.name,
                        description = EXCLUDED.description,
                        remediation = EXCLUDED.remediation,
                        severity    = EXCLUDED.severity,
                        embedding   = EXCLUDED.embedding
                """, (rule_key, name, description, remediation, severity, embedding))
            conn.commit()

    def search(self, query_text: str, top_k: int = 3) -> List[Dict]:
        embedding = self.embedder.embed(query_text)
        with self._conn() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute("""
                    SELECT rule_key, name, description, remediation, severity
                    FROM sonar_rules
                    ORDER BY embedding <=> %s::vector
                    LIMIT %s
                """, (embedding, top_k))
                return [dict(row) for row in cur.fetchall()]
