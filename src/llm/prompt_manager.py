"""Prompt management for Gemini summarization.

Centralizes prompt templates and versioning for consistent
summary generation across the application.
"""


class PromptManager:
    """Manages prompts for Gemini summarization.

    Supports versioned prompt templates so that prompt changes
    can be tracked and compared.
    """

    VERSION = "v1"

    SYSTEM_PROMPT = (
        "You are a news summarization expert specializing in technology news.\n"
        "Generate structured summaries with the following fields:\n"
        "- title_zh: Chinese title translation\n"
        "- summary_zh: 1-2 sentence Chinese summary (under 100 characters)\n"
        "- key_points: Array of 3-5 key points in Chinese\n"
        "- tags: Array of relevant tags (e.g., AI, Google, Cloud)\n"
        "\n"
        "Output ONLY valid JSON, no markdown fences or extra text.\n"
        "Example output:\n"
        '{"title_zh": "...", "summary_zh": "...", "key_points": ["...", "..."], "tags": ["...", "..."]}'
    )

    USER_TEMPLATE = (
        "Please summarize this article:\n\n"
        "Title: {title}\n"
        "Content: {content}\n\n"
        "Requirements:\n"
        "- title_zh: Translate the title to Traditional Chinese\n"
        "- summary_zh: Keep under 100 Chinese characters\n"
        "- key_points: 3-5 key points in Traditional Chinese\n"
        "- tags: 3-5 English tags\n"
        "Output valid JSON only."
    )

    def get_user_prompt(self, title: str, content: str) -> str:
        """Generate user prompt from article title and content.

        Args:
            title: Article title.
            content: Article content (truncated to 3000 chars).

        Returns:
            Formatted prompt string.
        """
        return self.USER_TEMPLATE.format(title=title, content=content[:3000])
