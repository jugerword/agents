"""Tests for embedding provider dispatch in chroma.py."""

from unittest import mock

from agents.connectors.chroma import get_embedding_function


def _dispatch(**env):
    base = {
        "OPENAI_API_KEY": "k",
    }
    base.update(env)
    with mock.patch.dict("os.environ", base, clear=True):
        return get_embedding_function()


def test_minimax_forced():
    assert _dispatch(EMBEDDING_PROVIDER="minimax").__class__.__name__ == "MiniMaxEmbeddings"


def test_minimax_when_base_is_minimax():
    # LLM base points at MiniMax -> embeddings must also use MiniMax
    assert (
        _dispatch(OPENAI_API_BASE="https://api.minimax.cn/v1").__class__.__name__
        == "MiniMaxEmbeddings"
    )


def test_minimax_when_no_base():
    # No OpenAI-compatible base configured -> default to MiniMax
    assert (
        _dispatch().__class__.__name__ == "MiniMaxEmbeddings"
    )


def test_openai_when_custom_base():
    # A real OpenAI-compatible embeddings endpoint -> OpenAIEmbeddings
    assert (
        _dispatch(OPENAI_API_BASE="https://custom.openai.com/v1").__class__.__name__
        == "OpenAIEmbeddings"
    )


def test_openai_forced():
    assert (
        _dispatch(OPENAI_API_BASE="https://api.minimax.cn/v1",
                  EMBEDDING_PROVIDER="openai").__class__.__name__
        == "OpenAIEmbeddings"
    )
