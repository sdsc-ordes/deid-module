from __future__ import annotations

import re
import random

import dateutil
import gender_guesser.detector as gender

from loader import NameDatabase, SurrogateMap

_GENDER_DETECTOR = gender.Detector()

_LOWER_ALPHA = 'abcdefghijklmnopqrstuvwxyz'
_LOWER_ALNUM = _LOWER_ALPHA + '0123456789'
_UPPER_ALNUM = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'

_TITLE_RE = re.compile(
    r'^(Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.|Mme\.|M\.|Mme|M|Dr|Mr|Ms|Mrs|Prof)$'
)

_DATE_PATTERNS = [
    r'(\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b)',  # DD/MM/YYYY or MM-DD-YYYY
    r'(\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b)',    # YYYY/MM/DD or YYYY-MM-DD
    r'(\b\d{1,2}\s\w+\s\d{2,4}\b)',          # DD Month YYYY
    r'(\b\w+\s\d{1,2},\s\d{2,4}\b)',         # Month DD, YYYY
    r'(\b\d{1,2}[/-]\d{1,2}\b)',             # DD/MM or MM-DD (no year)
    r'(\b\d{4}\b)',                          # standalone YYYY
]


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
    year_shift = parameters['year_shift']

    match entity_type:
        case 'NAME' | 'PERSON':
            return generate_name_surrogate(pii, surrogate_map, names_db)
        case 'LOCATION':
            return generate_location_surrogate(pii, surrogate_map)
        case 'DATE':
            return generate_date_surrogate(pii, surrogate_map, year_shift)
        case 'CONTACT':
            return generate_contact_surrogate(pii, surrogate_map)
        case 'PATIENTID' | 'STAYID' | 'ACCOUNT' | 'IPADDRESS':
            return generate_number_surrogate(pii, surrogate_map)
        case 'URL':
            return generate_url_surrogate(pii, surrogate_map)
        case 'AGE':
            return generate_age_surrogate(pii, surrogate_map, year_shift)
        case 'CIVILSTATUS':
            return generate_civil_status_surrogate(pii, surrogate_map)
        case 'NATIONALITY':
            return generate_nationality_surrogate(pii, surrogate_map)
        case 'PROFESSION':
            return generate_profession_surrogate(pii, surrogate_map)
        case 'SERVICE':
            return generate_hospital_service_surrogate(pii, surrogate_map)
        case 'BUILDING':
            return generate_hospital_building_surrogate(pii, surrogate_map)
        case 'ROOMBED':
            return generate_hospital_room_bed_surrogate(pii, surrogate_map)
        case 'PERSONALRELATIONSHIP':
            return generate_personal_relationship_surrogate(pii, surrogate_map)
        case 'ORGANIZATION':
            return generate_organization_surrogate(pii, surrogate_map)
        case _:
            return 'REDACTED'


def replace_digits(pii: str) -> str:
    return re.sub(r'\d', lambda _: str(random.randint(0, 9)), pii)


def generate_name_surrogate(pii: str, surrogate_map: SurrogateMap, names_db: NameDatabase) -> str:
    """Replace a person name token-by-token, preserving recognised titles (Dr., Mr., …)."""
    def build_full() -> str:
        parts = []
        for token in pii.split():
            if _TITLE_RE.match(token):
                parts.append(token)
            else:
                parts.append(surrogate_map.get_or_insert(
                    token, 'NAME',
                    lambda t=token: names_db.pick_random(_GENDER_DETECTOR.get_gender(t), t[0]),
                ))
        return ' '.join(parts)
    return surrogate_map.get_or_insert(pii, 'NAME', build_full)


def generate_location_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    def build() -> str:
        if re.match(r'^[\d\s,-]+$', pii):
            return replace_digits(pii)
        return 'Ville_' + pii[0].upper()
    return surrogate_map.get_or_insert(pii, 'LOCATION', build)


def generate_date_surrogate(pii: str, surrogate_map: SurrogateMap, year_shift: int) -> str:
    """Shift a date forward by year_shift years, output as DD/MM/YYYY."""
    def build() -> str:
        clean = pii.replace(".", "/").replace("-", "/").replace(" ", "/")
        clean = re.sub(r'/{2,}', '/', clean).strip('/')
        date_obj = _parse_date(clean)
        if date_obj is None:
            return clean
        try:
            shifted = date_obj.replace(year=date_obj.year + year_shift)
        except ValueError:
            # Feb 29 → Feb 28 on non-leap target years
            shifted = date_obj.replace(year=date_obj.year + year_shift, day=28)
        return shifted.strftime('%d/%m/%Y')
    return surrogate_map.get_or_insert(pii, 'DATE', build)


def _parse_date(s: str):
    for pattern in _DATE_PATTERNS:
        match = re.search(pattern, s)
        if not match:
            continue
        date_str = match.group(0)
        dayfirst = bool(re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', date_str)
                        or re.match(r'\d{1,2}\s\w+\s\d{2,4}', date_str))
        try:
            return dateutil.parser.parse(date_str, dayfirst=dayfirst)
        except Exception:
            continue
    return None


def generate_contact_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    """Replace an email or phone number with a random surrogate of the same length/format."""
    def build() -> str:
        if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', pii):
            local, domain = pii.split('@')
            domain_parts = domain.split('.')
            local_s = ''.join(random.choices(_LOWER_ALNUM, k=len(local)))
            domain_s = ''.join(random.choices(_LOWER_ALPHA, k=len(domain_parts[0])))
            return f'{local_s}@{domain_s}.{domain_parts[-1]}'
        if re.match(r'^[\d\s\-\+\(\)]+$', pii):
            return replace_digits(pii)
        return pii
    return surrogate_map.get_or_insert(pii, 'CONTACT', build)


def generate_number_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    return surrogate_map.get_or_insert(pii, 'NUMBER', lambda: replace_digits(pii))


def generate_url_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    return surrogate_map.get_or_insert(
        pii, 'URL',
        lambda: 'http://www.' + ''.join(random.choices(_LOWER_ALNUM, k=8)) + '.com',
    )


def generate_age_surrogate(pii: str, surrogate_map: SurrogateMap, year_shift: int) -> str:
    def build() -> str:
        match = re.match(r'(\d+)', pii)
        if match:
            return str(int(match.group(1)) + year_shift) + ' years'
        return pii
    return surrogate_map.get_or_insert(pii, 'AGE', build)


def generate_civil_status_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    return surrogate_map.get_or_insert(pii, 'CIVILSTATUS', lambda: 'CivilStatus-UNKNOWN')


def generate_nationality_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    return surrogate_map.get_or_insert(pii, 'NATIONALITY', lambda: 'Nationality-UNKNOWN')


def generate_profession_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    return surrogate_map.get_or_insert(pii, 'PROFESSION', lambda: 'Profession-UNKNOWN')


def generate_hospital_service_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    return surrogate_map.get_or_insert(pii, 'SERVICE', lambda: 'HospitalService-' + pii[0].upper())


def generate_hospital_building_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    return surrogate_map.get_or_insert(pii, 'BUILDING', lambda: 'Building-' + pii[0].upper())


def generate_hospital_room_bed_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    return surrogate_map.get_or_insert(
        pii, 'ROOMBED',
        lambda: 'Room-' + ''.join(random.choices(_UPPER_ALNUM, k=3)),
    )


def generate_personal_relationship_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    return surrogate_map.get_or_insert(pii, 'PERSONALRELATIONSHIP', lambda: 'Relationship-UNKNOWN')


def generate_organization_surrogate(pii: str, surrogate_map: SurrogateMap) -> str:
    return surrogate_map.get_or_insert(pii, 'ORGANIZATION', lambda: 'Organization-UNKNOWN')
