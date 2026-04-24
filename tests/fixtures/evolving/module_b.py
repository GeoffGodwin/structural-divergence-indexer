def compute(values: list) -> int:
    try:
        return sum(values)
    except TypeError:
        return 0
