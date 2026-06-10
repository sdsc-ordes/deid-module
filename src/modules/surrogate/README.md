# Surrogates

## Usage

After starting the server, go to `http://127.0.0.1:80/docs` to read the API documentation.

### Local

```python
uv run fastapi dev
```

### Dockerize

```
docker build -t fastapi-app .
docker run -p 8000:80 fastapi-app
```

## fast API

Launch FastAPI server with `uv run fastapi dev`. 

## Import an Existing Map

To load an existing surrogate map into the surrogate service, you may use the helper script [`import-surrogate-map`](tools/scripts/import-surrogate-map).

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
    participant O as Presidio-Surrogate-Operator
    participant SG as Surrogate-Generator
    participant VK as Valkey

    PT-)An: POST /analyze *
    An-)An: Detect PIIs in text
    An-->>PT: return Analyzer results *
    PT-)Anon: POST /anonymize ** (anonymizer set to surrogates)
    Anon-)Anon: Extract PIIs from text for anonymization
    Anon-)O: Send PIIs one by one
    O-)SG: POST /pii
    SG-)SG: Generate surrogate for PII
    SG-)VK: PII?
    alt in cache
        VK->>SG: surrogate
    else missing
        SG->>SG: Generate
        SG->>VK: Insert
    end
    SG-->>O: return surrogate
    O-->>Anon: return surrogate
    Anon-)Anon: assemble surrogates into text
    Anon-->>PT: return text **
```
