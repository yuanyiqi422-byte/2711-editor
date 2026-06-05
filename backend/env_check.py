import os


def validate_env() -> list[str]:
    issues: list[str] = []
    key = os.getenv("AI_API_KEY", "").strip()
    if not key or key == "your-secret-key-here":
        issues.append("AI_API_KEY 未配置或为占位符")
    return issues
