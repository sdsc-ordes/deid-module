# Presidio exploration

## deployment

- can be deployed as a webapp (hugging face demo) in a docker container
  - works out of the box
  - calls functions from presidio python library directly
- can be deployed as an API server using a compose stack

## API usage
2-steps:
- analyze: NER from raw text using models
- anonymize: config (rule) based processing of pre-detected PII

### analyze
- Minimal requirements: text + language. By default, all recognizers for that language are enabled.
  ```sh
  $ curl http://localhost:5002/analyze -s --header "Content-Type: application/json" --request POST --data '{"text": "John Smith drivers license is AC432223","language": "en"}' | jq                                                             
  [
    {
      "analysis_explanation": null,
      "end": 10,
      "entity_type": "PERSON",
      "score": 0.85,
      "start": 0
    },
    {
      "analysis_explanation": null,
      "end": 38,
      "entity_type": "US_DRIVER_LICENSE",
      "score": 0.6499999999999999,
      "start": 30
    }
  ]
  ```
- analysis can be controlled by setting detection score, selecting entities, adding context words and  adding a correlation id(?)
- ad-hoc pattern (regex) recognizers can be provided as json objects
- a correlation-id (hash) can be given to append to logs for easier grouping of analyses in logs / traces.

### anonymize
- By default, the anonymization replaces all detected identifies by their type (e.g. <PERSON>) in the input text.
- An anonymizer dictionary can be provided to associate specific anonymization procedure to specific entity types.
- Two inputs must be given to the endpoint:
  - the raw text
  - the response from the analyze step (detected entities and their positions)

### artificial sample
Input:
```
Prof. Gérard Waeber, Chef de service
Tél: +41 21 314 68 85 / Fax: +41 21 314 08 95

Lausanne, le 27 août 2014

Faxmed de sortie
LE VERT ALBERT, 04.03.1994, N° de séjour: 314052867
P.A. MME MARTIN ILDA, 1400 FRANCE
_______________________________________________________________________________
La patiente susnommée a séjourné dans notre service du 27.05.2014 au 27.05.2014, date de son
retour à domicile/ transfert.
Motif de recours
BEG
Diagnostics - Antécédents - Interventions
Diagnostic principal
Diagnostic(s) secondaire(s) / comorbidité(s) active(s)
Complication(s)
Comorbidité(s) passive(s)
Antécédent(s)
Autre(s)
Anamnèse
Anamnèse à l'entrée:
fhdkfjhjhfhdkjhdjkhd
djhfdkfhdkfhdl
dfjhdslfdif
jfldéijf

Dr Médecin 00 Formateur
Chef de clinique
```
- ## initial tests
Works with example artifical lettre de sortie.
```python
import json
import requests

letter = """
Tél: +41 21 314 68 85 / Fax: +41 21 314 08 95
Lausanne, le 27 août 2014

Faxmed de sortie
LE VERT ALBERT, 04.03.1994, N° de séjour: 314052867
P.A. MME MARTIN ILDA, 1400 FRANCE
_______________________________________________________________________________
La patiente susnommée a séjourné dans notre service du 27.05.2014 au 27.05.2014, date de son
retour à domicile/ transfert.
Motif de recours
BEG
Diagnostics - Antécédents - Interventions
Diagnostic principal
Diagnostic(s) secondaire(s) / comorbidité(s) active(s)
Complication(s)
Comorbidité(s) passive(s)
Antécédent(s)
Autre(s)
Anamnèse
Anamnèse à l'entrée:
fhdkfjhjhfhdkjhdjkhd
djhfdkfhdkfhdl
dfjhdslfdif
jfldéijf

Dr Médecin 00 Formateur
Chef de clinique
Prof. Gérard Waeber, Chef de service
"""

data = {"text": letter, "language": "en"}

# print(json.dumps(requests.post("http://localhost:5002/analyze", json=data).json()))
analyzer_result = requests.post("http://localhost:5002/analyze", json=data).json()
anonymizer_data = {"text": letter, "analyzer_results": analyzer_result}
print(
    json.dumps(
        requests.post("http://localhost:5001/anonymize", json=anonymizer_data).json()
    )
)
```

## limitations

### potential improvements
Model configuration
```yaml
# config.yaml
nlp_engine_name: spacy
models:
  - lang_code: fr
    model_name: ml-clin-deid/m2p2-model
  - lang_code: it
    model_name: ml-clin-deid/m2p2-model
  - lang_code: de
    model_name: ml-clin-deid/m2p2-model

ner_model_configuration:
  model_to_presidio_entity_mapping:
    PER: PERSON
    PERSON: PERSON
    NORP: NRP
    FAC: FACILITY
    LOC: LOCATION
    GPE: LOCATION
    LOCATION: LOCATION
    ORG: ORGANIZATION
    ORGANIZATION: ORGANIZATION
    DATE: DATE_TIME
    TIME: DATE_TIME
```

Recognizer configuration
```yaml
# recognizers.yaml
recognizers:
  -
    name: "Swiss Zip code Recognizer"
    supported_languages:
      - language: fr
        context: [adresse, postal]
      - language: de
        context: [ort,]
      - language: it
        context: [...]

    patterns:
      -
         name: "zip code (weak)"
         regex: "(\\b\\d{5}(?:\\-\\d{4})?\\b)"
         score: 0.01
    context:
     - zip
     - code
    supported_entity: "ZIP"
  -
    name: "Titles recognizer"
    supported_language: "en"
    supported_entity: "TITLE"
    deny_list:
      - Mr.
      - Mrs.
      - Ms.
      - Miss
      - Dr.
      - Prof.

```
