from unittest.mock import MagicMock, patch

from app.agent import ProdAgent


@patch("app.agent.get_settings")
@patch("app.agent.ChatGoogleGenerativeAI")
def test_prod_agent_builds_graph_without_missing_node_error(mock_llm_cls, mock_get_settings):
    mock_get_settings.return_value = MagicMock(
        primary_model="gemini-3.1-flash-lite",
        fallback_model="gemini-3.1-flash",
        max_retry=3,
    )
    mock_llm_cls.return_value = MagicMock()

    agent = ProdAgent()

    assert agent.graph is not None
