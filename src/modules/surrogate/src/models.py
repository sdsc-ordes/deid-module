from __future__ import annotations
from pydantic import BaseModel, ConfigDict, Field, model_serializer

class Pii(BaseModel):
    """PII (Personal Identifying Information) that requires a surrogate."""
    model_config = ConfigDict(frozen=True)

    value: str = Field(description="PII value to replace, e.g. 'John Doe', '01/01/1990', 'New York'.")
    entity_type: str = Field(description="Entity tag, e.g. 'NAME', 'LOCATION', 'DATE'.")
    session: str | None = Field(
        default=None,
        description="Identifier of the session (e.g. document) scoping this PII. "
        "When omitted, the surrogate is shared globally across sessions.",
    )

    @model_serializer
    def _serialize(self) -> dict[str, str]:
        # Omit ``session`` when unset so sessionless mappings keep the original
        # two-field wire format (and round-trip unchanged).
        data = {"value": self.value, "entity_type": self.entity_type}
        if self.session is not None:
            data["session"] = self.session
        return data

    def to_sanitized(self) -> Pii:
        return self.model_copy(update={"value": self.value.lower()})

class MapItem(BaseModel):
    """A single PII-to-surrogate mapping."""

    pii: Pii= Field(description="Personal Identifiable Information value.")
    surrogate: str = Field(description="Replacement value for `pii`.")

    def to_sanitized(self) -> MapItem:
        return MapItem(
            pii=self.pii.to_sanitized(),
            surrogate=self.surrogate,
        )
