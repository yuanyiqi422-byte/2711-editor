import os

from primary_api import has_usable_api_key, is_primary_disabled


def validate_env() -> list[str]:
    issues: list[str] = []
    if not has_usable_api_key():
        if is_primary_disabled():
            issues.append("主接口已禁用且未配置备用 AI_API_KEY_FALLBACK")
        else:
            issues.append("AI_API_KEY 未配置或为占位符")
    return issues
