import csv

def load_all_regions(filepath):

    regions = []
    with open(filepath, mode='r', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        for row in csv_reader:
            if len(row) == 2:  # Ensure the row has the correct structure
                regions.append({'kode_wilayah': row[0], 'name': row[1]})
    return regions

def suggest_regions_by_name(regions, query, limit=10):

    suggestions = []
    query_lower = query.lower()
    for region in regions:
        if region['name'].lower().startswith(query_lower):
            suggestions.append({'name': region['name']})
            if len(suggestions) >= limit:
                break
    return suggestions

def get_codes_by_name(regions, query):

    suggestions = []
    query_lower = query.lower()
    for region in regions:
        if region['name'].lower().startswith(query_lower):
            suggestions.append({'kode_wilayah': region['kode_wilayah']})
    return suggestions

def find_name_by_code(regions, kode_wilayah):
 
    for region in regions:
        if region['kode_wilayah'] == kode_wilayah:
            return region  # Return the full region (kode_wilayah and name)
    return None
