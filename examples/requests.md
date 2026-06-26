# Requests Examples

These example requests allow you to test that the setup is successful.

## K8s setup

Ensure you port forward the surrogate service and the anonymizer service for the following tests.

Surrogate service:
`kubectl port-forward services/dev-deid-presidio-surrogate -n ml-clin-deid 3300:1010`

you can then see the docs at http://localhost:3300/docs as well as ping endpoints of the API.

Anonymizer service:
`kubectl port-forward services/dev-deid-presidio-anonymizer -n ml-clin-deid 3000:80`

## Test 1: Upload a reference map to surrogate service

Example command (adapt if you move the file or port forward to a different port):

```bash
cd src/modules/surrogate/tools/scripts
bash import-surrogate-map http://localhost:3300/map ../../data/example_map.jsonl
```

You should get a 204 (or other 2xx) response if the upload is successful:

```bash
* Host localhost:3300 was resolved.
* IPv6: ::1
* IPv4: 127.0.0.1
*   Trying [::1]:3300...
* Established connection to localhost (::1 port 3300) from ::1 port 49561
* using HTTP/1.x
> POST /map HTTP/1.1
> Host: localhost:3300
> User-Agent: curl/8.19.0
> Accept: */*
> Content-Type: application/jsonl
> Content-Length: 231
>
* upload completely sent off: 231 bytes
< HTTP/1.1 204 No Content
< date: Wed, 17 Jun 2026 08:16:16 GMT
< server: uvicorn
< content-type: application/json
```

## Test 2: Anonymizer and Surrogate connection

```bash
curl \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{"anonymizers": {"DEFAULT": {"type": "surrogate"}}, "text": "Bonsoir Steve", "analyzer_results": [{"start": 8, "end": 13, "score": 0.8, "entity_type": "NAME"}]}' \
  http://localhost:3000/anonymize
```

You should get the following output:

```bash
{"text": "Bonsoir Simone", "items": [{"start": 8, "end": 14, "entity_type": "NAME", "text": "Simone", "operator": "surrogate"}]}%
```

Where the PII Steve has been replaced by Simone, according to the example map we provided.

This test ensures that the anonymizer and the surrogate services can talk, as well as ensure the example map is being used.

## Test 3: Session scoping (optional)

Test 2 omits a session, so surrogates are shared globally (`Steve -> Simone` mapping is reused).
To scope surrogates to a document, pass a `session` in the operator config:

```bash
curl \
  -H 'Content-Type: application/json' \
  -X POST \
  -d '{"anonymizers": {"DEFAULT": {"type": "surrogate", "session": "doc-123"}}, "text": "Bonsoir Steve", "analyzer_results": [{"start": 8, "end": 13, "score": 0.8, "entity_type": "NAME"}]}' \
  http://localhost:3000/anonymize
```

The same value gets a stable surrogate within a session but an independent one
across sessions. 
