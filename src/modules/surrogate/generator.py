from __future__ import annotations

import re
import random
import dateutil
import gender_guesser.detector as gender

from loader import MapEntry, NameDatabase, SurrogateMap

_GENDER_DETECTOR = gender.Detector()


def generate_surrogate(
    pii: str,
    entity_type: str,
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

    match entity_type:
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


def generate_name_surrogate(pii: str, surrogate_map: SurrogateMap, names_db: NameDatabase) -> str:
    """Replace a person name token-by-token, preserving recognised titles (Dr., Mr., …)."""
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='NAME'))
    if surrogate is not None:
        return surrogate

    surrogate_name = ''
    for name in pii.split():
        if re.match(r'^(Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.|Mme\.|M\.|Mme|M|Dr|Mr|Ms|Mrs|Prof)$', name):
            surrogate_name += name + ' '
        else:
            token_surrogate = surrogate_map.get(MapEntry(pii=name, entity_type='NAME'))
            if token_surrogate is not None:
                surrogate_name += token_surrogate + ' '
            else:
                predicted_gender = _GENDER_DETECTOR.get_gender(name)
                first_letter = name[0]
                token_surrogate = names_db.pick_random(predicted_gender, first_letter)
                surrogate_name += token_surrogate + ' '
    surrogate_map.insert(MapEntry(pii=pii, entity_type='NAME'), surrogate_name.strip())
    return surrogate_name.strip()


def replace_digits(pii: str) -> str:
    def random_digit(_):
        return str(random.randint(0, 9))

    return re.sub(r'\d', random_digit, pii)


def generate_location_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='LOCATION'))
    if surrogate is not None:
        return surrogate

    if re.match(r'^[\d\s,-]+$', pii):
        surrogate = replace_digits(pii)
    else:
        surrogate = 'Ville_' + pii[0].upper()

    surrogate_map.insert(MapEntry(pii=pii, entity_type='LOCATION'), surrogate)
    return surrogate


def generate_date_surrogate(pii: str, surrogate_map: SurrogateMap, year_shift: int) -> str:
    """Shift a date forward by year_shift years, output as DD/MM/YYYY."""
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='DATE'))
    if surrogate is not None:
        return surrogate

    pii = pii.replace(".", "/").replace("-", "/").replace(" ", "/")
    pii = re.sub(r'/{2,}', '/', pii)
    pii = pii.strip('/')

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
        match = re.search(pattern, pii)
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
        surrogate = pii

    surrogate_map.insert(MapEntry(pii=pii, entity_type='DATE'), surrogate)
    return surrogate


def generate_contact_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    """Replace an email or phone number with a random surrogate of the same length/format."""
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='CONTACT'))
    if surrogate is not None:
        return surrogate

    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', pii):
        parts = pii.split('@')
        local_part = parts[0]
        domain_part = parts[1]
        surrogate_local = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=len(local_part)))
        surrogate_domain = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=len(domain_part.split('.')[0]))) + '.' + domain_part.split('.')[-1]
        surrogate = surrogate_local + '@' + surrogate_domain
    elif re.match(r'^[\d\s\-\+\(\)]+$', pii):
        surrogate = replace_digits(pii)
    else:
        surrogate = pii

    surrogate_map.insert(MapEntry(pii=pii, entity_type='CONTACT'), surrogate)
    return surrogate


def generate_number_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='NUMBER'))
    if surrogate is not None:
        return surrogate

    surrogate = replace_digits(pii)
    surrogate_map.insert(MapEntry(pii=pii, entity_type='NUMBER'), surrogate)
    return surrogate


def generate_url_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='URL'))
    if surrogate is not None:
        return surrogate

    surrogate = 'http://www.' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8)) + '.com'
    surrogate_map.insert(MapEntry(pii=pii, entity_type='URL'), surrogate)
    return surrogate


def generate_age_surrogate(pii: str, surrogate_map: SurrogateMap, year_shift: int) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='AGE'))
    if surrogate is not None:
        return surrogate

    match = re.match(r'(\d+)', pii)
    if match:
        age = int(match.group(1))
        surrogate = str(age + year_shift) + ' years'
    else:
        surrogate = pii

    surrogate_map.insert(MapEntry(pii=pii, entity_type='AGE'), surrogate)
    return surrogate


def generate_civil_status_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='CIVILSTATUS'))
    if surrogate is not None:
        return surrogate

    surrogate = 'CivilStatus-UNKNOWN'
    surrogate_map.insert(MapEntry(pii=pii, entity_type='CIVILSTATUS'), surrogate)
    return surrogate


def generate_nationality_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='NATIONALITY'))
    if surrogate is not None:
        return surrogate

    surrogate = 'Nationality-UNKNOWN'
    surrogate_map.insert(MapEntry(pii=pii, entity_type='NATIONALITY'), surrogate)
    return surrogate


def generate_profession_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='PROFESSION'))
    if surrogate is not None:
        return surrogate

    surrogate = 'Profession-UNKNOWN'
    surrogate_map.insert(MapEntry(pii=pii, entity_type='PROFESSION'), surrogate)
    return surrogate


def generate_hospital_service_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='SERVICE'))
    if surrogate is not None:
        return surrogate

    surrogate = 'HospitalService-' + pii[0].upper()
    surrogate_map.insert(MapEntry(pii=pii, entity_type='SERVICE'), surrogate)
    return surrogate


def generate_hospital_building_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='BUILDING'))
    if surrogate is not None:
        return surrogate

    surrogate = 'Building-' + pii[0].upper()
    surrogate_map.insert(MapEntry(pii=pii, entity_type='BUILDING'), surrogate)
    return surrogate


def generate_hospital_room_bed_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='ROOMBED'))
    if surrogate is not None:
        return surrogate

    surrogate = 'Room-' + ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=3))
    surrogate_map.insert(MapEntry(pii=pii, entity_type='ROOMBED'), surrogate)
    return surrogate


def generate_personal_relationship_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='PERSONALRELATIONSHIP'))
    if surrogate is not None:
        return surrogate

    surrogate = 'Relationship-UNKNOWN'
    surrogate_map.insert(MapEntry(pii=pii, entity_type='PERSONALRELATIONSHIP'), surrogate)
    return surrogate


def generate_organization_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    surrogate = surrogate_map.get(MapEntry(pii=pii, entity_type='ORGANIZATION'))
    if surrogate is not None:
        return surrogate

    surrogate = 'Organization-UNKNOWN'
    surrogate_map.insert(MapEntry(pii=pii, entity_type='ORGANIZATION'), surrogate)
    return surrogate
