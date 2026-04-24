def transform(item: object) -> object:
    try:
        return str(item).upper()
    except (ValueError, TypeError) as exc:
        print(f"Error: {exc}")
        return None
    finally:
        pass
