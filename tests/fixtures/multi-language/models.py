"""Data models for multi-language fixture."""

from dataclasses import dataclass


@dataclass
class User:
    """Represents an application user."""

    id: int
    name: str


@dataclass
class Product:
    """Represents a product."""

    sku: str
    price: float
    in_stock: bool


MAX_USERS = 1000
