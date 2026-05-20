import pandas as pd
import os
import re
import random

import gender_guesser.detector as gender

# PURPOSE: This script aims to generate surrogate values for different entity types based on predefined rules and datasets.
# <USAGE> python TEXTDEID_surrogate_generation.py <entity_file> <output_file>

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

def generate_surrogates(input, surrogate_map, name_db, parameters=None):
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

    # Iterate through each row and generate surrogates based on entity type, update surrogatmap with the generated surrogate
    for idx, row in input.iterrows():
        entity = row['entity']
        text = row['word']
        
        if entity == '[[NAME]]':
            surrogate = generate_name_surrogate(text, surrogate_map, name_db)
        elif entity == '[[LOCATION]]':
            surrogate = generate_location_surrogate(text, surrogate_map)
        elif entity == '[[DATE]]':
            surrogate = generate_date_surrogate(text, surrogate_map, parameters['year_shift'])
        elif entity == '[[CONTACT]]':
            surrogate = generate_contact_surrogate(text, surrogate_map)
        elif entity == '[[ID: PatientID]]':
            surrogate = generate_number_surrogate(text, surrogate_map)
        elif entity == '[[ID: StayID]]':
            surrogate = generate_number_surrogate(text, surrogate_map)
        elif entity == '[[NUMBER: Account]]':
            surrogate = generate_number_surrogate(text, surrogate_map)
        elif entity == '[[URL]]':
            surrogate = generate_url_surrogate(text, surrogate_map)
        elif entity == '[[IPAdress]]':
            surrogate = generate_number_surrogate(text, surrogate_map)
        elif entity == '[[DEMOGRAPHIC: Age]]':
            surrogate = generate_age_surrogate(text, surrogate_map, parameters['year_shift'])
        elif entity == '[[DEMOGRAPHIC: CivilStatus]]':
            surrogate = generate_civil_status_surrogate(text, surrogate_map)
        elif entity == '[[DEMOGRAPHIC: Nationality]]':
            surrogate = generate_nationality_surrogate(text, surrogate_map)
        elif entity == '[[DEMOGRAPHIC: Profession]]':
            surrogate = generate_profession_surrogate(text, surrogate_map)
        elif entity == '[[HOSPITAL: Service]]':
            surrogate = generate_hospital_service_surrogate(text, surrogate_map)
        elif entity == '[[HOSPITAL: Building]]':
            surrogate = generate_hospital_building_surrogate(text, surrogate_map)
        elif entity == '[[HOSPITAL: Room-Bed]]':
            surrogate = generate_hospital_room_bed_surrogate(text, surrogate_map)
        elif entity == '[[PersonalRelationship]]':
            surrogate = generate_personal_relationship_surrogate(text, surrogate_map)
        elif entity == '[[Organization]]':
            surrogate = generate_organization_surrogate(text, surrogate_map)
        else:
            surrogate = text  # No change for unrecognized entities

        # Update the input df and save to output_file
        input.at[idx, 'surrogate'] = surrogate
    output=input
    print(f"Surrogate generation completed.")
    return output, surrogate_map


def generate_name_surrogate(text, surrogate_map, name_db):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    surrogate_name = ''
    # check if the text is a single word or multiple words
    names = text.split()
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
                predicted_gender = d.get_gender(text)
                first_letter = name[0]
                surrogate = name_db.pick_random(predicted_gender, first_letter)
                 # if no file, use a default name
                surrogate_name += surrogate + ' '# add to the surrogate name
                # add the new surrogate to the map
                surrogate_map.add(name, surrogate, '[[NAME]]')
    return surrogate_name


def replace_digits(text):
    def random_digit(_):
        return str(random.randint(0, 9))
    
    return re.sub(r'\d', random_digit, text)


def generate_location_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # check if location text only contains numbers (e.g., postal codes, house number)
    if re.match(r'^[\d\s,-]+$', text):
        surrogate = replace_digits(text)
    else:
        # generate a fake address
        surrogate = 'Ville_'+text[0].upper()
    
    surrogate_map.add(text, surrogate, '[[LOCATION]]')
    return surrogate

def generate_date_surrogate(text, surrogate_map, year_shift):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # Step 1: reformat the date to a standard format (replace seperators such as '.', '-' with '/')
    text = text.replace(".", "/").replace("-", "/").replace(" ", "/")
    text = re.sub(r'/{2,}', '/', text)  # replace multiple '/' with single '/'
    text = text.strip('/') # remove leading/trailing '/'

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
        match = re.search(pattern, text)
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
        surrogate = text  # If parsing fails, keep the original text

    surrogate_map.add(text, surrogate, '[[DATE]]')
    return surrogate


def generate_contact_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # Check if it's an email
    if re.match(r'^[\w\.-]+@[\w\.-]+\.\w+$', text):
        parts = text.split('@')
        local_part = parts[0]
        domain_part = parts[1]
        surrogate_local = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=len(local_part)))
        surrogate_domain = ''.join(random.choices('abcdefghijklmnopqrstuvwxyz', k=len(domain_part.split('.')[0]))) + '.' + domain_part.split('.')[-1]
        surrogate = surrogate_local + '@' + surrogate_domain
    # Check if it's a phone number (simple check for digits, spaces, dashes, parentheses)
    elif re.match(r'^[\d\s\-\+\(\)]+$', text):
        surrogate = replace_digits(text)
    else:
        surrogate = text  # If it doesn't match known patterns, keep original
    
    surrogate_map.add(text, surrogate, '[[CONTACT]]')
    return surrogate

def generate_number_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    surrogate = replace_digits(text)
    
    surrogate_map.add(text, surrogate, '[[NUMBER]]')
    return surrogate 

def generate_url_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # Simple URL surrogate generation
    surrogate = 'http://www.' + ''.join(random.choices('abcdefghijklmnopqrstuvwxyz0123456789', k=8)) + '.com'
    
    surrogate_map.add(text, surrogate, '[[URL]]')
    return surrogate

def generate_age_surrogate(text, surrogate_map, year_shift):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # Check if age is in format "X years" or just "X"
    match = re.match(r'(\d+)', text)
    if match:
        age = int(match.group(1))
        new_age = age + year_shift
        surrogate = str(new_age) + ' years'
    else:
        surrogate = text  # If parsing fails, keep the original text
    
    surrogate_map.add(text, surrogate, '[[DEMOGRAPHIC: Age]]')
    return surrogate

def generate_civil_status_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # replace civil status with 'CivilStatus-UNKNOWN'
    surrogate = 'CivilStatus-UNKNOWN'
    # civil_status_options = ['Single', 'Married', 'Divorced', 'Widowed', 'Separated', 'In a relationship']
    # surrogate = random.choice(civil_status_options)

    surrogate_map.add(text, surrogate, '[[DEMOGRAPHIC: CivilStatus]]')
    return surrogate

def generate_nationality_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # replace nationality with 'Nationality-UNKNOWN'
    surrogate = 'Nationality-UNKNOWN'

    surrogate_map.add(text, surrogate, '[[DEMOGRAPHIC: Nationality]]')    
    return surrogate

def generate_profession_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # replace profession with 'Profession-UNKNOWN'
    surrogate = 'Profession-UNKNOWN'

    surrogate_map.add(text, surrogate, '[[DEMOGRAPHIC: Profession]]')
    return surrogate 

def generate_hospital_service_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # Simple surrogate generation for hospital service
    surrogate = 'HospitalService-' + text[0].upper()
        
    surrogate_map.add(text, surrogate, '[[HOSPITAL: Service]]')
    return surrogate 

def generate_hospital_building_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # Simple surrogate generation for hospital building
    surrogate = 'Building-' + text[0].upper()
       
    surrogate_map.add(text, surrogate, '[[HOSPITAL: Building]]')
    return surrogate

def generate_hospital_room_bed_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # Simple surrogate generation for hospital room/bed
    surrogate = 'Room-' + ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=3))
      
    surrogate_map.add(text, surrogate, '[[HOSPITAL: Room-Bed]]')
    return surrogate 

def generate_personal_relationship_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # replace personal relationship with 'Relationship-UNKNOWN'
    surrogate = 'Relationship-UNKNOWN'
    
    surrogate_map.add(text, surrogate, '[[PersonalRelationship]]')
    return surrogate 

def generate_organization_surrogate(text, surrogate_map):
    # check if the text already has a surrogate in the map
    exists, surrogate = surrogate_map.check_exists_in_map(text)
    if exists:
        return surrogate

    # replace organization with 'Organization-UNKNOWN'
    surrogate = 'Organization-UNKNOWN'
       
    surrogate_map.add(text, surrogate, '[[Organization]]')
    return surrogate 


# def replace_orig_text_with_surrogate(orig_text_path, surrogate_map_path, output_text_path):
#     # read the original text
#     with open(orig_text_path, 'r', encoding='utf-8') as f:
#         orig_text = f.read()

#     # read the surrogate map
#     if os.path.exists(surrogate_map_path):
#         surrogate_map = pd.read_csv(surrogate_map_path)
#     else:
#         print(f"Surrogate map file {surrogate_map_path} not found. Exiting.")
#         with open(output_text_path, 'w', encoding='utf-8') as f:
#             f.write(orig_text)
#         return 


#     # sort the surrogate map by length of 'word' in descending order to replace longer matches first
#     surrogate_map['word_length'] = surrogate_map['word'].apply(len)
#     surrogate_map = surrogate_map.sort_values(by='word_length', ascending=False)

#     # replace each entity in the original text with its surrogate
#     for i, row in surrogate_map.iterrows():
#         word = row['word']
#         surrogate = row['surrogate']
#         # Use regex to replace whole words only, case-insensitive
#         pattern = r'\b' + re.escape(word) + r'\b'
#         orig_text = re.sub(pattern, surrogate, orig_text, flags=re.IGNORECASE)
    
#     # save the modified text
#     with open(output_text_path, 'w', encoding='utf-8') as f:
#         f.write(orig_text)
#     return 
