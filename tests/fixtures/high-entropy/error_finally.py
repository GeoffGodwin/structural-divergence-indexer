"""Error handling style 4: except + finally block."""


def process_finally(resource, data):
    """Process with explicit finally clause for cleanup."""
    try:
        result = resource.parse(data)
        return result
    except Exception as exc:
        print(f"Parse error: {exc}")
        return None
    finally:
        resource.close()
