# Surrogates

## set-up

```python
uv sync
uv run main.py
```

## fast API

### POST /pii

## Presidio Integration

Here is the expected flow of this module for its integration with Presidio.

Key references:

- *[Presidio API documentation for Analyzer](https://microsoft.github.io/presidio/api-docs/api-docs.html#tag/Analyzer)
- **[Presidio API documentation for Anonymizer](https://microsoft.github.io/presidio/api-docs/api-docs.html#tag/Anonymizer)


```mermaid
sequenceDiagram
    participant PT as Privacy Toolbox
    participant An as Presidio-Analyzer
    participant Anon as Presidio-Anonymizer
    participant SG as Surrogate-Generator
    participant VK as Valkey

    PT-)An: POST /analyze *
    An-)An: Detect PIIs
    An-->>PT: return Analyzer results *
    PT-)Anon: POST /anonymize ** (anonymizer set to surrogates)
    Anon-)Anon: Extract PIIs for anonymization
    Anon-)SG: POST /generate-surrogates
    SG-)SG: Generate surrogates for PIIs
    SG-)VK: PII?
    alt in cache
        VK->>SG: surrogate
    else missing
        SG->>SG: Generate
        SG->>VK: Insert
    end
    VK-->>SG: return surrogate if exists
    SG-->>Anon: return PIIs replaced with surrogates
    Anon-->>PT: return Operator Result **
```

