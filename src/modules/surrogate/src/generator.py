from __future__ import annotations

import re
import random
import dateutil
import gender_guesser.detector as gender

from loader import NameDatabase, SurrogateMap
from models import Pii, MapItem

_GENDER_DETECTOR = gender.Detector()


def generate_surrogate(
    pii: Pii,
    surrogate_map: SurrogateMap,
    names_db: NameDatabase,
    parameters=None,
) -> str:
    """Dispatch PII to the appropriate surrogate generator based on entity type.

    Args:
        pii: The raw PII string to replace.
        entity_type: Entity label (e.g. 'NAME', 'DATE', 'LOCATION').
        surrogate_map: Persistent map used to retrieve and store pii->surrogate pairs.
        names_db: Name database used for person-name generation.
        parameters: Optional parameters for surrogate generation.
    Returns:
        Surrogate string, or 'REDACTED' for unrecognised entity types.
    """
    if parameters is None:
        parameters = {'year_shift': 3}

    match pii.entity_type:
        case 'NAME' | 'PERSON':
            surrogate = generate_name_surrogate(pii, surrogate_map, names_db)
        case 'LOCATION':
            surrogate = generate_location_surrogate(pii, surrogate_map)
        case 'DATE':
            surrogate = generate_date_surrogate(pii, surrogate_map, parameters['year_shift'])
        case 'CONTACT':
            surrogate = generate_contact_surrogate(pii, surrogate_map)
        case 'PATIENTID':
            surrogate = generate_number_surrogate(pii, surrogate_map)
        case 'STAYID':
            surrogate = generate_number_surrogate(pii, surrogate_map)
        case 'ACCOUNT':
            surrogate = generate_number_surrogate(pii, surrogate_map)
        case 'URL':
            surrogate = generate_url_surrogate(pii, surrogate_map)
        case 'IPADDRESS':
            surrogate = generate_number_surrogate(pii, surrogate_map)
        case 'AGE':
            surrogate = generate_age_surrogate(pii, surrogate_map, parameters['year_shift'])
        case 'CIVILSTATUS':
            surrogate = generate_civil_status_surrogate(pii, surrogate_map)
        case 'NATIONALITY':
            surrogate = generate_nationality_surrogate(pii, surrogate_map)
        case 'PROFESSION':
            surrogate = generate_profession_surrogate(pii, surrogate_map)
        case 'SERVICE':
            surrogate = generate_hospital_service_surrogate(pii, surrogate_map)
        case 'BUILDING':
            surrogate = generate_hospital_building_surrogate(pii, surrogate_map)
        case 'ROOMBED':
            surrogate = generate_hospital_room_bed_surrogate(pii, surrogate_map)
        case 'PERSONALRELATIONSHIP':
            surrogate = generate_personal_relationship_surrogate(pii, surrogate_map)
        case 'ORGANIZATION':
            surrogate = generate_organization_surrogate(pii, surrogate_map)
        case _:
            surrogate = 'REDACTED'
    return surrogate


def generate_name_surrogate(pii: Pii, surrogate_map: SurrogateMap, names_db: NameDatabase) -> str:
    """Replace a person name word-by-word, preserving recognised titles (Dr., Mr., …)."""
    #TODO: remove entity casting from generator logic -> use str enums instead
    cast_pii = pii.model_copy(update={'entity_type': 'NAME'})
    surrogate = surrogate_map.get(cast_pii)
    if surrogate is not None:
        return surrogate

    surrogate = ''
    for name in pii.value.split():
        if re.match(r'^(Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.|Mme\.|M\.|Mme|M|Dr|Mr|Ms|Mrs|Prof)$', name):
            surrogate += name + ' '
        else:
            surrogate_word = surrogate_map.get(pii.model_copy(update={'value': name, 'entity_type': 'NAME'}))
            if surrogate_word is not None:
                surrogate += surrogate_word + ' '
            else:
                predicted_gender = _GENDER_DETECTOR.get_gender(name)

                surrogate_word = names_db.pick_random(predicted_gender)
                surrogate += surrogate_word + ' '
    surrogate_map.insert(MapItem(pii=cast_pii, surrogate=surrogate.strip()))
    return surrogate.strip()


def replace_digits(pii: str) -> str:
    def random_digit(_):
        return str(random.randint(0, 9))

    return re.sub(r'\d', random_digit, pii)


def generate_location_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(pii)
    if surrogate is not None:
        return surrogate

    if re.match(r'^[\d\s,-]+$', pii.value):
        surrogate = replace_digits(pii.value)
    else:
        surrogate = 'Ville_' + pii.value[0].upper()

    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate


def generate_date_surrogate(pii: Pii, surrogate_map: SurrogateMap, year_shift: int) -> str:
    """Shift a date forward by year_shift years, output as DD/MM/YYYY."""
    surrogate = surrogate_map.get(pii)
    if surrogate is not None:
        return surrogate

    clean_date = pii.value.replace(".", "/").replace("-", "/").replace(" ", "/")
    clean_date = re.sub(r'/{2,}', '/', pii.value)
    clean_date = pii.value.strip('/')

    date_patterns = [
        r'(\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b)',  # Matches DD/MM/YYYY or MM-DD-YYYY
        r'(\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b)',    # Matches YYYY/MM/DD or YYYY-MM-DD
        r'(\b\d{1,2}\s\w+\s\d{2,4}\b)',          # Matches DD Month YYYY
        r'(\b\w+\s\d{1,2},\s\d{2,4}\b)',         # Matches Month DD, YYYY
        r'(\b\d{1,2}[/-]\d{1,2}\b)',             # Matches DD/MM or MM-DD (without year)
        r'(\b\d{4}\b)'                           # Matches standalone year YYYY
    ]

    date_obj = None
    for pattern in date_patterns:
        match = re.search(pattern, clean_date)
        if match:
            date_str = match.group(0)
            try:
                if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', date_str):
                    date_obj = dateutil.parser.parse(date_str, dayfirst=True)
                elif re.match(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', date_str):
                    date_obj = dateutil.parser.parse(date_str)
                elif re.match(r'\d{1,2}\s\w+\s\d{2,4}', date_str):
                    date_obj = dateutil.parser.parse(date_str, dayfirst=True)
                elif re.match(r'\w+\s\d{1,2},\s\d{2,4}', date_str):
                    date_obj = dateutil.parser.parse(date_str)
                elif re.match(r'\d{1,2}[/-]\d{1,2}', date_str):
                    date_obj = dateutil.parser.parse(date_str)
                elif re.match(r'\d{4}', date_str):
                    date_obj = dateutil.parser.parse(date_str, format='%Y')
            except Exception:
                date_obj = None

            if date_obj is not None:
                break

    if date_obj is not None:
        new_year = date_obj.year + year_shift
        try:
            surrogate_date = date_obj.replace(year=new_year)
        except ValueError:
            # Handle February 29 for non-leap years
            surrogate_date = date_obj.replace(year=new_year, day=28)
        surrogate = surrogate_date.strftime('%d/%m/%Y')
    else:
        surrogate = clean_date

    surrogate_map.insert(
        MapItem(
            pii=pii.model_copy(update={'value': clean_date, 'entity_type': 'DATE'}),
            surrogate=surrogate,
        )
    )
    return surrogate


def generate_contact_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    """Replace an email or phone number with a random surrogate of the same length/format."""
    surrogate = surrogate_map.get(pii)
    if surrogate is not None:
        return surrogate

    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', pii.value):
        parts = pii.value.split('@')
        local_part = parts[0]
        domain_part = parts[1]
        surrogate_local = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=len(local_part)))
        surrogate_domain = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=len(domain_part.split('.')[0]))) + '.' + domain_part.split('.')[-1]
        surrogate = surrogate_local + '@' + surrogate_domain
    elif re.match(r'^[\d\s\-\+\(\)]+$', pii.value):
        surrogate = replace_digits(pii.value)
    else:
        surrogate = pii.value

    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate


def generate_number_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    cast_pii = pii.model_copy(update={'entity_type': 'NUMBER'})
    surrogate = surrogate_map.get(cast_pii)
    if surrogate is not None:
        return surrogate

    surrogate = replace_digits(pii.value)
    surrogate_map.insert(MapItem(pii=cast_pii, surrogate=surrogate))
    return surrogate


def generate_url_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(pii)
    if surrogate is not None:
        return surrogate

    surrogate = 'http://www.' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8)) + '.com'
    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate


def generate_age_surrogate(pii: Pii, surrogate_map: SurrogateMap, year_shift: int) -> str:
    surrogate = surrogate_map.get(pii)
    if surrogate is not None:
        return surrogate

    match = re.match(r'(\d+)', pii.value)
    if match:
        age = int(match.group(1))
        surrogate = str(age + year_shift) + ' years'
    else:
        surrogate = pii.value

    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate


def generate_civil_status_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(pii)
    if surrogate is not None:
        return surrogate

    surrogate = 'CivilStatus-UNKNOWN'
    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate


def generate_nationality_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(pii)
    if surrogate is not None:
        return surrogate

    surrogate = 'Nationality-UNKNOWN'
    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate


def generate_profession_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(pii)
    if surrogate is not None:
        return surrogate

    surrogate = 'Profession-UNKNOWN'
    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate


def generate_hospital_service_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(pii=pii)
    if surrogate is not None:
        return surrogate

    surrogate = 'HospitalService-' + pii.value[0].upper()
    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate


def generate_hospital_building_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(pii)
    if surrogate is not None:
        return surrogate

    surrogate = 'Building-' + pii.value[0].upper()
    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate


def generate_hospital_room_bed_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(pii)
    if surrogate is not None:
        return surrogate

    surrogate = 'Room-' + ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=3))
    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate


def generate_personal_relationship_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(pii=pii)
    if surrogate is not None:
        return surrogate

    surrogate = 'Relationship-UNKNOWN'
    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate


def generate_organization_surrogate(pii: Pii, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(pii)
    if surrogate is not None:
        return surrogate

    surrogate = 'Organization-UNKNOWN'
    surrogate_map.insert(MapItem(pii=pii, surrogate=surrogate))
    return surrogate
