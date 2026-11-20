"""Part 2 的本地占位接口，不实现 Part 5 的安全处理。"""


def sanitize(text: str) -> str:
    """原样返回输入，供后续注入正式接口。"""
    return text


__all__ = ["sanitize"]
