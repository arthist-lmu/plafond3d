import json
from src.db_connection import conn_3310
import urllib.parse
import urllib.request

OBJECT_FILE = "../dumps/deckenmalerei.eu/exportedEntities_2022-05-03.json"

apiprefix = "https://query.wikidata.org/sparql?query="

object_table_mapping = {
    "OBJ#BUILDING": {
        "name": "buildings",
        "primary_key" : "id_building",
        "id_field": "DATA",
        "import_columns": {
            "title": "name",
            "wikidata_id": ["gnd", "find_qid_from_gnd"],
            "longitude": "locationLng",
            "latitude": "locationLat",
            "address_street": "addressStreet",
            "address_zip": "addressZip",
            "address_locality": "addressLocality"
        },
        "lists" : {
            "building_function_join": ["id_building", "id_function", "WHERE name_deckenmalerei = %s"]
        },
        "auto_columns" : {
            "source": "deckenmalerei",
            "county": "Germany"
        }
    }
}

def find_qid_from_gnd (gnd):
    query = "SELECT ?item WHERE {?item wdt:P227 '" + gnd + "'.}"
    json_result = sparql_wikidata(query)
    
    if len(json_result["results"]["bindings"]) == 1:
        return json_result["results"]["bindings"][0]["item"]["value"].rsplit("/", 1)[-1]
    return None
        
def sparql_wikidata (query):
    url = apiprefix + urllib.parse.quote(query) + "&format=json"
    
    try:
        f = urllib.request.urlopen(url)
        jsonstring = f.read()
        return json.loads(jsonstring)
    except urllib.error.HTTPError as err:
        print(err)

def get_field_data (row, field_info):
    if isinstance (field_info, list):
        if field_info[0] in row:
            return (globals().get(field_info[1])(row[field_info[0]]), True)
        return (None, True)
    else:
        if field_info in row:
            return (row[field_info], False)
        return (None, False)

def update_fields (row, cur, info, old_data):
    updates = []
    values = []
    
    for i, db_field in enumerate(info["import_columns"]):
        
        old_val = old_data[i+1]
        (new_val, inferred) = get_field_data(row, info["import_columns"][db_field])

        if (not old_val and new_val) or (new_val and not inferred and new_val != old_val):
            print(db_field + " -- old: "+ str(old_val) + ", new: " + str(new_val))
            updates.append("`" + db_field + "` = %s")
            values.append(new_val)
        elif new_val and old_val and new_val != old_val:
            raise Exception("Different value in database for inferred value: " + info["name"] + " " + str(old_data[0]) 
                            + " field '" + db_field + "': Old value = '" + str(old_val) + "', new value = '" + str(new_val) + "'")
            
    if len(updates) > 0:
        print(old_data)
        sql = "UPDATE plafond.`" + info["name"] + "` SET " + ",".join(updates) + " WHERE " + info["primary_key"] + "=" + str(old_data[0])
        #cur.execute(sql, values)
        return True
    
    return False

def create_new_entry (row, info, cur):
    print("create")

def handle_row (row, cur):
    if row["type"] in object_table_mapping:
        info = object_table_mapping[row["type"]]
        
        fields = [info["primary_key"]] + list(info["import_columns"].keys())
        sql = "SELECT " + ",".join(fields) + " FROM plafond.`" + info["name"] + "` WHERE source='deckenmalerei' AND source_id = %s"
        cur.execute(sql, row[info["id_field"]])
        old_data = cur.fetchone()
        
        if (old_data):
            return update_fields(row, cur, info, old_data)
        else:
            create_new_entry(row, cur, info)
            
        return True
    return False

if __name__ == "__main__":
    conn = conn_3310()
    
    with open(OBJECT_FILE, encoding="utf8") as f:
        data = json.load(f)
        
        with conn.cursor() as cur:
            functions = []
            for row in data:
                if handle_row(row, cur):
                    print(row)
                    conn.commit()
                    exit()
                    
                    
            
