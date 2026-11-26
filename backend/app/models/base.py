"""Shared declarative base for the stored records."""
from __future__ import annotations


from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base for every table in this prototype."""
