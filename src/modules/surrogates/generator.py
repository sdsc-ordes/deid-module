import pandas as pd
import re
import random

import gender_guesser.detector as gender

# PURPOSE: This script aims to generate surrogate values for different entity types based on predefined rules and datasets.
# <USAGE> python piiDEID_surrogate_generation.py <entity_file> <output_file>

# ENTITY TYPES TO BE PROCESSED
    # [[NAME]] – include patient, doctor, other names
    # [[LOCATION]] – include all address information, postal code
    # [[DATE]] - include all dates and time
    # [[CONTACT]]  – include telephone (fax) and emails
    # [[ID: PatientID]]
    # [[ID: StayID]]
    # [[NUMBER: Account]]
    # [[URL]]
    # [[IPAdress]]
    # [[DEMOGRAPHIC: Age]]
    # [[DEMOGRAPHIC: CivilStatus]]
    # [[DEMOGRAPHIC: Nationality]]
    # [[DEMOGRAPHIC: Profession]]
    # [[HOSPITAL: Service]]
    # [[HOSPITAL: Building]]
    # [[HOSPITAL: Room-Bed]] 
    # [[PersonalRelationship]]
    # [[Organization]]

def generate_surrogate(pii, entity, surrogate_map, name_db, parameters=None):
    """
    Generate surrogate values for entities in the input CSV file and save to output CSV file.
    
    Args:
        input (pd.DataFrame): The input DataFrame containing entities.
        surrogate_map (pd.DataFrame): The DataFrame containing surrogate mappings.
        name_db (pd.DataFrame): The DataFrame containing name lists.
        parameters (dict, optional): Parameters for surrogate generation.
    Returns:
        output (pd.DataFrame): The output DataFrame with surrogate values.
        surrogate_map (pd.DataFrame): The updated surrogate map with new mappings.
    """
    # set defult parameters if not provided
    if parameters is None:  
        parameters = {
            'year_shift':3,
        }

    match entity:  
        case '[[NAME]]' | '[[PERSON]]':
            surrogate = generate_name_surrogate(pii, surrogate_map, name_db)
        case '[[LOCATION]]':
            surrogate = generate_location_surrogate(pii, surrogate_map)
            print(f"Generated surrogate for location: {pii} -> {surrogate}")
        case '[[DATE]]':
            surrogate = generate_date_surrogate(pii, surrogate_map, parameters['year_shift'])
        case '[[CONTACT]]':
            surrogate = generate_contact_surrogate(pii, surrogate_map)
        case '[[ID: PatientID]]':
            surrogate = generate_number_surrogate(pii, surrogate_map)
        case '[[ID: StayID]]':
            surrogate = generate_number_surrogate(pii, surrogate_map)
        case '[[NUMBER: Account]]':
            surrogate = generate_number_surrogate(pii, surrogate_map)
        case '[[URL]]':
            surrogate = generate_url_surrogate(pii, surrogate_map)
        case '[[IPAdress]]':
            surrogate = generate_number_surrogate(pii, surrogate_map)
        case '[[DEMOGRAPHIC: Age]]':
            surrogate = generate_age_surrogate(pii, surrogate_map, parameters['year_shift'])
        case '[[DEMOGRAPHIC: CivilStatus]]':
            surrogate = generate_civil_status_surrogate(pii, surrogate_map)
        case '[[DEMOGRAPHIC: Nationality]]':
            surrogate = generate_nationality_surrogate(pii, surrogate_map)
        case '[[DEMOGRAPHIC: Profession]]':
            surrogate = generate_profession_surrogate(pii, surrogate_map)
        case '[[HOSPITAL: Service]]':
            surrogate = generate_hospital_service_surrogate(pii, surrogate_map)
        case '[[HOSPITAL: Building]]':
            surrogate = generate_hospital_building_surrogate(pii, surrogate_map)
        case '[[HOSPITAL: Room-Bed]]':
            surrogate = generate_hospital_room_bed_surrogate(pii, surrogate_map)
        case '[[PersonalRelationship]]':
            surrogate = generate_personal_relationship_surrogate(pii, surrogate_map)
        case '[[Organization]]':
            surrogate = generate_organization_surrogate(pii, surrogate_map)
        case _:
            surrogate = pii  # No change for unrecognized entities
    print(f"Surrogate generation completed.")
    return surrogate


def generate_name_surrogate(pii, surrogate_map, name_db):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    surrogate_name = ''
    # check if the pii is a single word or multiple words
    names = pii.split()
    for name in names:
        # check if name is a title (e.g., Dr., Mr., Mrs.)
        if re.match(r'^(Dr\.|Mr\.|Mrs\.|Ms\.|Prof\.|Mme\.|M\.|Mme|M|Dr|Mr|Ms|Mrs|Prof)$', name):
            surrogate_name += name + ' ' # keep the title as is
        else:
            # for each single name, check if it exists in the map
            exists, surrogate = surrogate_map.check_exists_in_map(name)
            if exists:
                surrogate_name += surrogate + ' '# use the existing surrogate
            else:
                d = gender.Detector()
                predicted_gender = d.get_gender(pii)
                first_letter = name[0]
                surrogate = name_db.pick_random(predicted_gender, first_letter)
                surrogate_map.add(name, surrogate, '[[NAME]]')
    return surrogate


def replace_digits(pii):
    def random_digit(_):
        return str(random.randint(0, 9))
    
    return re.sub(r'\d', random_digit, pii)


def generate_location_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # check if location pii only contains numbers (e.g., postal codes, house number)
    if re.match(r'^[\d\s,-]+$', pii):
        surrogate = replace_digits(pii)
    else:
        # generate a fake address
        surrogate = 'Ville_'+pii[0].upper()
    
    surrogate_map.add(pii, surrogate, '[[LOCATION]]')
    return surrogate

def generate_date_surrogate(pii, surrogate_map, year_shift):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # Step 1: reformat the date to a standard format (replace seperators such as '.', '-' with '/')
    pii = pii.replace(".", "/").replace("-", "/").replace(" ", "/")
    pii = re.sub(r'/{2,}', '/', pii)  # replace multiple '/' with single '/'
    pii = pii.strip('/') # remove leading/trailing '/'

    # Define regex patterns for different date formats
    date_patterns = [
        r'(\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b)',  # Matches DD/MM/YYYY or MM-DD-YYYY
        r'(\b\d{4}[/-]\d{1,2}[/-]\d{1,2}\b)',    # Matches YYYY/MM/DD or YYYY-MM-DD
        r'(\b\d{1,2}\s\w+\s\d{2,4}\b)',          # Matches DD Month YYYY
        r'(\b\w+\s\d{1,2},\s\d{2,4}\b)',         # Matches Month DD, YYYY
        r'(\b\d{1,2}[/-]\d{1,2}\b)',             # Matches DD/MM or MM-DD (without year)
        r'(\b\d{4}\b)'                           # Matches standalone year YYYY
    ]


    for pattern in date_patterns:
        match = re.search(pattern, pii)
        if match:
            date_str = match.group(0)
            try:
                # Try parsing the date with different formats
                if re.match(r'\d{1,2}[/-]\d{1,2}[/-]\d{2,4}', date_str):
                    date_obj = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                elif re.match(r'\d{4}[/-]\d{1,2}[/-]\d{1,2}', date_str):
                    date_obj = pd.to_datetime(date_str, errors='coerce')
                elif re.match(r'\d{1,2}\s\w+\s\d{2,4}', date_str):
                    date_obj = pd.to_datetime(date_str, dayfirst=True, errors='coerce')
                elif re.match(r'\w+\s\d{1,2},\s\d{2,4}', date_str):
                    date_obj = pd.to_datetime(date_str, errors='coerce')
                elif re.match(r'\d{1,2}[/-]\d{1,2}', date_str):
                    date_obj = pd.to_datetime(date_str, errors='coerce')
                elif re.match(r'\d{4}', date_str):
                    date_obj = pd.to_datetime(date_str, format='%Y', errors='coerce')
                else:
                    date_obj = None
            except:
                date_obj = None
    
    # If date parsing was successful, shift the year
    if date_obj is not None and not pd.isna(date_obj):
        new_year = date_obj.year + year_shift
        try:
            surrogate_date = date_obj.replace(year=new_year)
        except ValueError:
            # Handle February 29 for non-leap years
            surrogate_date = date_obj.replace(year=new_year, day=28)
        surrogate = surrogate_date.strftime('%d/%m/%Y')
    else:
        surrogate = pii  # If parsing fails, keep the original pii

    surrogate_map.add(pii, surrogate, '[[DATE]]')
    return surrogate


def generate_contact_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # Check if it's an email
    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', pii):
        parts = pii.split('@')
        local_part = parts[0]
        domain_part = parts[1]
        surrogate_local = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=len(local_part)))
        surrogate_domain = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=len(domain_part.split('.')[0]))) + '.' + domain_part.split('.')[-1]
        surrogate = surrogate_local + '@' + surrogate_domain
    # Check if it's a phone number (simple check for digits, spaces, dashes, parentheses)
    elif re.match(r'^[\d\s\-\+\(\)]+$', pii):
        surrogate = replace_digits(pii)
    else:
        surrogate = pii  # If it doesn't match known patterns, keep original
    
    surrogate_map.add(pii, surrogate, '[[CONTACT]]')
    return surrogate

def generate_number_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    surrogate = replace_digits(pii)
    
    surrogate_map.add(pii, surrogate, '[[NUMBER]]')
    return surrogate 

def generate_url_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # Simple URL surrogate generation
    surrogate = 'http://www.' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8)) + '.com'
    
    surrogate_map.add(pii, surrogate, '[[URL]]')
    return surrogate

def generate_age_surrogate(pii, surrogate_map, year_shift):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # Check if age is in format "X years" or just "X"
    match = re.match(r'(\d+)', pii)
    if match:
        age = int(match.group(1))
        new_age = age + year_shift
        surrogate = str(new_age) + ' years'
    else:
        surrogate = pii  # If parsing fails, keep the original pii
    
    surrogate_map.add(pii, surrogate, '[[DEMOGRAPHIC: Age]]')
    return surrogate

def generate_civil_status_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # replace civil status with 'CivilStatus-UNKNOWN'
    surrogate = 'CivilStatus-UNKNOWN'
    # civil_status_options = ['Single', 'Married', 'Divorced', 'Widowed', 'Separated', 'In a relationship']
    # surrogate = random.choice(civil_status_options)

    surrogate_map.add(pii, surrogate, '[[DEMOGRAPHIC: CivilStatus]]')
    return surrogate

def generate_nationality_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # replace nationality with 'Nationality-UNKNOWN'
    surrogate = 'Nationality-UNKNOWN'

    surrogate_map.add(pii, surrogate, '[[DEMOGRAPHIC: Nationality]]')    
    return surrogate

def generate_profession_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # replace profession with 'Profession-UNKNOWN'
    surrogate = 'Profession-UNKNOWN'

    surrogate_map.add(pii, surrogate, '[[DEMOGRAPHIC: Profession]]')
    return surrogate 

def generate_hospital_service_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # Simple surrogate generation for hospital service
    surrogate = 'HospitalService-' + pii[0].upper()
        
    surrogate_map.add(pii, surrogate, '[[HOSPITAL: Service]]')
    return surrogate 

def generate_hospital_building_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # Simple surrogate generation for hospital building
    surrogate = 'Building-' + pii[0].upper()
       
    surrogate_map.add(pii, surrogate, '[[HOSPITAL: Building]]')
    return surrogate

def generate_hospital_room_bed_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # Simple surrogate generation for hospital room/bed
    surrogate = 'Room-' + ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=3))
      
    surrogate_map.add(pii, surrogate, '[[HOSPITAL: Room-Bed]]')
    return surrogate 

def generate_personal_relationship_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # replace personal relationship with 'Relationship-UNKNOWN'
    surrogate = 'Relationship-UNKNOWN'
    
    surrogate_map.add(pii, surrogate, '[[PersonalRelationship]]')
    return surrogate 

def generate_organization_surrogate(pii, surrogate_map):
    # check if the pii already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(pii)
    if exists:
        return surrogate

    # replace organization with 'Organization-UNKNOWN'
    surrogate = 'Organization-UNKNOWN'
       
    surrogate_map.add(pii, surrogate, '[[Organization]]')
    return surrogate 