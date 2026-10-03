import os
from typing import List

import httpx

from dotenv import load_dotenv
from langchain_core.embeddings import Embeddings

load_dotenv()

MINIMAX_EMBEDDINGS_URL = "https://api.minimax.cn/v1/embeddings"

# MiniMax is a domestic API that does not need a proxy. Disable env proxies
# (http_proxy/all_proxy) so a broken SOCKS entry cannot break embedding calls.
_httpx_client = httpx.Client(trust_env=False, timeout=60.0)


class MiniMaxEmbeddings(Embeddings):
    """LangChain-compatible embeddings backed by MiniMax's embo-01 model.

    MiniMax's embeddings API is NOT OpenAI-compatible: it expects a ``texts``
    array plus a ``type`` field and returns ``vectors`` instead of
    ``data[].embedding``. This adapter translates between the two formats so
    the rest of the RAG pipeline (chroma) can use MiniMax directly.

    Config via environment:
      - OPENAI_API_KEY (used as the MiniMax subscription key)
      - EMBEDDING_MODEL (default: embo-01)
    """

    def __init__(self, model: str = None, type: str = "query") -> None:
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("EMBEDDING_MODEL", "embo-01")
        self.type = type
        if not self.api_key:
            raise ValueError(
                "OPENAI_API_KEY (MiniMax subscription key) is required for "
                "MiniMaxEmbeddings. Set it in your .env file."
            )

    def _embed_texts(self, texts: List[str], type: str) -> List[List[float]]:
        response = _httpx_client.post(
            MINIMAX_EMBEDDINGS_URL,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}",
            },
            json={
                "model": self.model,
                "texts": texts,
                "type": type,
            },
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        base_resp = data.get("base_resp", {})
        if base_resp.get("status_code") != 0:
            raise RuntimeError(
                f"MiniMax embeddings error: {base_resp.get('status_msg')}"
            )
        vectors = data.get("vectors")
        if vectors is None:
            raise RuntimeError("MiniMax embeddings returned no vectors")
        return vectors

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """Embed a list of documents (stored corpus).

        MiniMax rejects requests with too many text blocks ("embedding too
        much blocks"), so split into batches of BATCH_SIZE.
        """
        BATCH_SIZE = 32
        all_vectors: List[List[float]] = []
        for i in range(0, len(texts), BATCH_SIZE):
            batch = texts[i : i + BATCH_SIZE]
            all_vectors.extend(self._embed_texts(batch, type="db"))
        return all_vectors

    def embed_query(self, text: str) -> List[float]:
        """Embed a single query string."""
        return self._embed_texts([text], type="query")[0]
