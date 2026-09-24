from unittest.mock import MagicMock

from langchain_core.messages import AIMessage

from app.monitoring import LLMmon


def test_monitor_call_returns_message_content_and_tracks_tokens():
    llm = LLMmon.__new__(LLMmon)
    llm.metrics = MagicMock()
    llm.logger = MagicMock()
    llm.llm = MagicMock()
    llm.llm.invoke.return_value = AIMessage(
        content="Paris",
        response_metadata={
            "usage_metadata": {
                "prompt_token_count": 15,
                "candidates_token_count": 3,
                "total_token_count": 18,
            }
        },
    )

    response = llm.monitor_call("What is the capital of France?")

    assert response == "Paris"
    llm.metrics.record_request.assert_called_once_with(15, 3, llm.metrics.record_request.call_args.args[2], False, False)
