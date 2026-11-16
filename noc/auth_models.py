from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator


UserRole = Literal["global_admin", "admin", "operator", "viewer"]
USERNAME_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{2,63}$")


def validate_username(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not USERNAME_PATTERN.fullmatch(value):
        raise ValueError("Username must be 3–64 letters, numbers, dots, dashes or underscores")
    return value


class LoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("username")
    @classmethod
    def username_format(cls, value: str) -> str:
        return validate_username(value) or ""


class UserCreate(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=8, max_length=128)
    role: UserRole

    @field_validator("username")
    @classmethod
    def username_format(cls, value: str) -> str:
        return validate_username(value) or ""


class UserUpdate(BaseModel):
    username: str | None = Field(default=None, min_length=3, max_length=64)
    password: str | None = Field(default=None, min_length=8, max_length=128)
    role: UserRole | None = None
    is_active: bool | None = None

    @field_validator("username")
    @classmethod
    def username_format(cls, value: str | None) -> str | None:
        return validate_username(value)

    @model_validator(mode="after")
    def require_update(self):
        if not any(getattr(self, field) is not None for field in self.model_fields_set):
            raise ValueError("At least one user field must be provided")
        return self


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
