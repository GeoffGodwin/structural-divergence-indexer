"""Entry point for the simple-python fixture."""

import os
import sys

from simple_python.models.user import User
from simple_python.utils.helpers import format_name


def main():
    user = User(name="Alice", email="alice@example.com")
    formatted = format_name(user.name)
    print(formatted)


if __name__ == "__main__":
    main()
