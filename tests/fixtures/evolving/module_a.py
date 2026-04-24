def process(data: str) -> str:
    try:
        return data.strip()
    except AttributeError:
        return ""
