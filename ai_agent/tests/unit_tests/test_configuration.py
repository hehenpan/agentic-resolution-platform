from pathlib import Path

from agent.core.config import Settings


def test_settings_loads_llm_and_embedding_config(tmp_path: Path) -> None:
    config_file = tmp_path / "config.ini"
    config_file.write_text(
        "\n".join(
            [
                "[database]",
                "db_file = test.sqlite3",
                "",
                "[qdrant]",
                "path = qdrant_test",
                "",
                "[mcp]",
                "server_url = http://localhost:8500/sse",
                "",
                "[llm]",
                "chat_model = test-chat-model",
                "",
                "[embedding]",
                "model = models/test-embedding",
                "dimensionality = 128",
                "",
            ]
        ),
        encoding="utf-8",
    )

    settings = Settings(str(config_file), "test")

    assert settings.LLM_CHAT_MODEL == "test-chat-model"
    assert settings.EMBEDDING_MODEL == "models/test-embedding"
    assert settings.EMBEDDING_DIM == 128
