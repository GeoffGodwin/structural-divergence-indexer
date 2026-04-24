def parse(text: str) -> float:
    try:
        return float(text)
    except ValueError:
        raise
    except TypeError:
        return 0.0
    else:
        pass
    return 0.0
