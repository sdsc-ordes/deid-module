from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field

class Pii(BaseModel):
    """PII (Personal Identifying Information) that requires a surrogate."""
    model_config = ConfigDict(frozen=True)

    value: str = Field(description="PII value to replace, e.g. 'John Doe', '01/01/1990', 'New York'.")
    entity_type: str = Field(description="Entity tag, e.g. 'NAME', 'LOCATION', 'DATE'.")
    session: str | None = Field(description="Identifier of session scoping this PII.")

    def to_sanitized(self) -> Pii:
        return Pii(
            value = self.value.lower(),
            entity_type = self.entity_type,
            session = self.session,
        )

class MapItem(BaseModel):
    """A single PII-to-surrogate mapping."""

    pii: Pii= Field(description="Personal Identifiable Information value.")
    surrogate: str = Field(description="Replacement value for `pii`.")

    def to_sanitized(self) -> MapItem:
        return MapItem(
            pii=self.pii.to_sanitized(),
            surrogate=self.surrogate,
        )
