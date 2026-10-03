"""Tests for the MiniMax embeddings adapter."""

from unittest import mock

from agents.connectors.embeddings import MiniMaxEmbeddings


def _make_embeddings():
    with mock.patch.dict(
        "os.environ",
        {"OPENAI_API_KEY": "test-key"},
        clear=False,
    ):
        return MiniMaxEmbeddings()


def _mock_post(vectors):
    resp = mock.MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "vectors": vectors,
        "total_tokens": 10,
        "base_resp": {"status_code": 0, "status_msg": "success"},
    }
    return resp


def test_embed_documents_uses_db_type():
    emb = _make_embeddings()
    vectors = [[0.1] * 1536, [0.2] * 1536]
    with mock.patch(
        "agents.connectors.embeddings._httpx_client.post",
        return_value=_mock_post(vectors),
    ) as post:
        out = emb.embed_documents(["doc a", "doc b"])
    assert len(out) == 2
    assert out[0] == vectors[0]
    body = post.call_args.kwargs["json"]
    assert body["type"] == "db"
    assert body["texts"] == ["doc a", "doc b"]
    assert body["model"] == "embo-01"


def test_embed_query_uses_query_type_and_returns_single():
    emb = _make_embeddings()
    vector = [0.3] * 1536
    with mock.patch(
        "agents.connectors.embeddings._httpx_client.post",
        return_value=_mock_post([vector]),
    ) as post:
        out = emb.embed_query("question?")
    assert out == vector
    body = post.call_args.kwargs["json"]
    assert body["type"] == "query"
    assert body["texts"] == ["question?"]


def test_error_status_raises():
    emb = _make_embeddings()
    resp = mock.MagicMock()
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "vectors": None,
        "base_resp": {"status_code": 2013, "status_msg": "missing type"},
    }
    with mock.patch(
        "agents.connectors.embeddings._httpx_client.post", return_value=resp
    ):
        try:
            emb.embed_documents(["x"])
            raise AssertionError("expected RuntimeError")
        except RuntimeError as err:
            assert "missing type" in str(err)


def test_missing_api_key_raises():
    with mock.patch.dict("os.environ", {}, clear=True):
        try:
            MiniMaxEmbeddings()
            raise AssertionError("expected ValueError")
        except ValueError as err:
            assert "OPENAI_API_KEY" in str(err)
