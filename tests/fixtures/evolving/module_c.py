def validate(text: str) -> bool:
    try:
        return bool(text.strip())
    except AttributeError:
        return False
