from agent_runtime.llm import OpenAIAdapter
from design_workflow.llm_client import create_glm_client


def test_create_glm_client_normalizes_base_url_to_chat_completions() -> None:
    client = create_glm_client(
        api_key="key",
        base_url="https://open.bigmodel.cn/api/paas/v4/",
        model="glm-4",
    )

    assert isinstance(client, OpenAIAdapter)
    assert client.model == "glm-4"
