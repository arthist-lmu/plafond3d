import json

def remove_keys_from_entities(input_file, output_file, keys_to_remove):
    # Load JSON data from the input file
    with open(input_file, 'r') as infile:
        data = json.load(infile)
    
    # Loop through each object and remove the keys if they exist
    for entity in data:
        for key in keys_to_remove:
            entity.pop(key, None)  # Safely remove key if it exists
    
    # Save the updated data to the output file
    with open(output_file, 'w') as outfile:
        json.dump(data, outfile, indent=2)

if __name__ == '__main__':
    keys_to_remove = ['shortText', 'text', 'bibliography']
    remove_keys_from_entities('dumps/deckenmalerei.eu/2025_02/entities.json', 'bavarikon/entities small.json', keys_to_remove)
