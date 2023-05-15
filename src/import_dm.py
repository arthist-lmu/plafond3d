import json
from src.db_connection import conn_3310
import urllib.parse
import urllib.request
import re
from torch.jit import isinstance
from memoization import cached

OBJECT_FILE = "../dumps/deckenmalerei.eu/exportedEntities_2022-05-03.json"
CONNECTION_FILE = "../dumps/deckenmalerei.eu/exportedRelations_2022-05-03.json"

apiprefix = "https://query.wikidata.org/sparql?query="

room_person_conn_types = ['ARCHITECT', 'ORDERER', 'PAINTER', 'SCULPTOR', 'ARTIST', 'POLYCHROMERS', 'PLASTERER', 'TEMPLATE_PROVIDER', 'BUILDER', 
                           'CONSTRUCTION_MANAGER', 'CABINETMAKER', 'DESIGNER', 'REFERENCE_PERSON', 'IMAGE_CARVER', 'ILLUSIONISTIC_CEILING_PAINTER', 
                           'MARBLE_WORKERS', 'RESIDENT']

building_person_conn_types = ['ARCHITECT', 'ORDERER', 'PHOTOGRAPHER', 'PAINTER', 'PLASTERER', 'SCULPTOR', 'BUILDER', 'CONSTRUCTION_MANAGER', 'ARTIST', 
                              'TEMPLATE_PROVIDER', 'OWNER', 'RESIDENT', 'REFERENCE_PERSON', 'AUTHOR', 'CABINETMAKER', 'POLYCHROMERS', 'BUILDING_CRAFTSMEN', 
                              'DESIGNER', 'CARPENTER', 'IMAGE_CARVER', 'DONATOR']

object_table_mapping = {
    "OBJ#PERSON" : {
        "name" : "persons",
        "primary_key": "id_person",
        "id_field": "DATA",
        "import_columns": {
            "full_name" : "name",
            "first_name" : ["name", "get_first_name"],
            "last_name" : ["name", "get_last_name"],
            "wikidata_id": ["gnd", "find_qid_from_gnd"]
        },
        "lists" : {},
        "connections" : {},
        "auto_columns" : {
            "source": "deckenmalerei"
        }
    },
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
            "address_locality": "addressLocality",
            "dating_original": "verbaleDating",
            "dating_start": ["verbaleDating", "get_start_year"],
            "dating_end": ["verbaleDating", "get_end_year"]
        },
        "lists" : {
            "building_function_join": ["functions", "id_building_function", "building_functions", "name_deckenmalerei = %s"]
        },
        "connections" : {
            "building_person_join" : [building_person_conn_types, ["OBJ#PERSON"], "connection_type", "to_lower", "id_person", "persons"]
        },
        "auto_columns" : {
            "source": "deckenmalerei",
            "country": "Germany"
        }
    },
    "OBJ#ROOM" : {
        "name" : "rooms",
        "primary_key": "id_room",
        "id_field": "DATA",
        "import_columns" : {
            "title": "name",
            "id_building": ["FK", "find_building_for_room"],
            "state": [("conditionDamaged", "ConditionDestroyed"), "get_room_condition"],
            "width" : ["width", "none_to_empty"],
            "length" : ["length", "none_to_empty"],
            "height" : ["height", "none_to_empty"]
        },
        "lists" : {
            "room_function_join": ["functions", "id_room_function", "room_functions", "name_deckenmalerei = %s"]
        },
        "connections" : {
            "room_person_join" : [room_person_conn_types, ["OBJ#PERSON"], "connection_type", "to_lower", "id_person", "persons"]
        },
        "auto_columns" : {
            "source": "deckenmalerei",
            "floor" : None
        }
    },
    "OBJ#PAINTING" : {
        "name" : "plafonds",
        "primary_key": "id_plafond",
        "id_field": "DATA",
        "import_columns": {
            "title" : "name",
            "id_room": ["FK", "find_room_for_plafond"],
            "dating_original": ["verbaleDating", "none_to_empty"],
            "dating_start": ["verbaleDating", "get_start_year"],
            "dating_end": ["verbaleDating", "get_end_year"]
        },
        "lists" : {},
        "connections" : {},
        "auto_columns" : {
            "source": "deckenmalerei"
        },
        "condition" : "is_plafond"
    }
}

connection_table_mapping = {}

changes = {}
conns = None
type_mapping = {} #Maps import ids to object types
id_mapping = {} #Maps import ids to data base ids

def is_plafond (row):
    return "positionCeiling" in row and row["positionCeiling"]

def none_to_empty (s):
    if s == None:
        return ""
    return str(s)

def to_lower (s):
    return s.lower()

def get_start_year (dating):
    return handle_year(dating)[0]

def get_end_year (dating):
    return handle_year(dating)[1]

@cached
def handle_year (dating):
    if dating == None:
        return (None,None)
    
    if re.match("^[1-9][0-9]{3}$", dating):
        return (int(dating),int(dating))
    
    matchObject = re.match("^(?:um|wohl um) ([1-9][0-9]{3})$", dating)
    if matchObject:
        return (int(matchObject[1]),int(matchObject[1]))

    matchObject = re.match("^([1-9][0-9]{3}) ?[" + re.escape("–-/") + "] ?([1-9][0-9]{3})$", dating)
    if matchObject:
        return (int(matchObject[1]),int(matchObject[2]))
    
    matchObject = re.match("^([1-9][0-9]{3}) ?[" + re.escape("–-/") + "] ?([0-9]{2})$", dating)
    if matchObject:
        return (int(matchObject[1]),int(matchObject[1][0:2] + matchObject[2]))
    
    matchObject = re.match("^([1-9][0-9])(\.)? Jh\.$", dating) #TODO maybe require the dot after the number
    if matchObject:
        century = int(matchObject[1])
        return ((century - 1) * 100 + 1, century * 100)
    
    if (dating.find(",") != -1 or dating.find(";") != -1):
        parts = re.split(" ?[,;] ?", dating)
        
        first = None
        current = None
        for part in parts:
            newRange = handle_year(part)
            
            if not newRange[0] or not newRange[1]:
                return (None, None)
            if newRange[0] > 1800:
                break
            if not first:
                first = newRange
            current = newRange
            
        return (first[0], current[1]) 
    return (None,None)

def get_first_name (full_name):
    return handle_name(full_name)[0]

def get_last_name (full_name):
    return handle_name(full_name)[1]

@cached
def handle_name (full_name):
    if full_name == None:
        return (None,None)
    
    matchObject = re.match("^([^,]+), ([^,]+)$", full_name)
    if matchObject:
        return (matchObject[2], matchObject[1])
    
    return (None,None)

def get_room_condition (damaged, destroyed):
    if destroyed == True:
        return "destroyed"
    elif damaged == True:
        return "damaged"
    return ""

def find_qid_from_gnd (gnd):
    if gnd == None:
        return None
    
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
 
def find_transitive_connection (eid, objectType, connType, intermObjects):
    result_id = None
    current_element = eid
    
    while current_element != None and result_id == None:
        conns = get_connections(current_element)
        current_element = None
        for conn in conns:
            #print (type_mapping[conn["DATA"]] + ", " + conn["type"])
            if type_mapping[conn["DATA"]] == objectType and conn["type"].startswith(connType):
                result_id = conn["DATA"]
                break
                
            if type_mapping[conn["DATA"]] in intermObjects and conn["type"].startswith(connType):
                current_element = conn["DATA"]
                break
            
    if result_id == None:
        raise Exception("Object connection not found (" + eid + ", " + objectType + ").")
    
    return result_id
        
def find_building_for_room (eid):
    return find_transitive_connection(eid, "OBJ#BUILDING", "<-#PART#", ("OBJ#ROOM", "OBJ#ROOM_SEQUENCE", "OBJ#BUILDING_DIVISION"))


def find_room_for_plafond (eid):
    try:
        return find_transitive_connection(eid, "OBJ#ROOM", "<-#PART#", ("OBJ#ROOM", "OBJ#PICTURE_CYCLE"))
    except Exception as e:
        print(e)
        return None

def find_connections_with_types (eid, conn_types, element_types):
    conns = get_connections(eid)
    ret = []
    
    for conn in conns:
        for ctype in conn_types:
            if conn["type"].startswith("->#" + ctype + "#") and type_mapping[conn["DATA"]] in element_types:
                ret.append((conn["DATA"], ctype))
                break
    
    return ret
    

def get_field_data (row, field_info, entry_id, info):
    
    table = info["name"]
    
    if type(field_info) == list:
        fun = globals().get(field_info[1])
        if field_info[0] == "FK":
            #TODO changes?
            arg = entry_id
            object_id = fun(arg)
            if object_id == None:
                return (None, True)
            return (id_mapping[type_mapping[object_id]][object_id], True)
        elif type(field_info[0]) == tuple:
            args = [row[x] if x in row else None for x in field_info[0]]
            #TODO strip?
            #TODO changes?
            return (fun(*args), True)
        elif field_info[0] in row:
            arg = base_value_or_changed(table, row, field_info[0], info)
            if isinstance(arg, str):
                arg = arg.strip()
            return (fun(arg), True)
        return (fun(None), True)
    else:
        if field_info in row:
            ret = base_value_or_changed(table, row, field_info, info)
            
            if isinstance(ret, str):
                ret = ret.strip()
            return (ret, False)
        return (None, False)
    
def base_value_or_changed (table, row, field_name, info):
    if table in changes:
        for change in changes[table]:
            if row[info["id_field"]] == change[1] and field_name == change[2]:
                return change[4]
    
    return row[field_name]
    
def get_list_data (info, row, field_name):
    table = info["name"]
    if table in changes:
        for change in changes[table]:
            if row[info["id_field"]] == change[1] and field_name == change[2]:
                changed = json.loads(change[4])
                return changed
    
    return row[field_name]
    

def update_fields (row, cur, info, old_data):
    if (old_data[1]): #TODO remove (or use skip systematically)
        return
    
    entry_id = row[info["id_field"]]

    updates = []
    values = []
    
    for i, db_field in enumerate(info["import_columns"]):
    
        old_val = old_data[i+2]#TODO set one if skipped is removed
        (new_val, inferred) = get_field_data(row, info["import_columns"][db_field], entry_id, info)
    
        if (not old_val and new_val) or (new_val and not inferred and new_val != old_val):
            print(db_field + " -- old: "+ str(old_val) + ", new: " + str(new_val))
            updates.append("`" + db_field + "` = %s")
            values.append(new_val)
        elif new_val and old_val and new_val != old_val:
            raise Exception("Different value in database for inferred value: " + info["name"] + " " + str(old_data[0]) 
                            + " field '" + db_field + "': Old value = '" + str(old_val) + "', new value = '" + str(new_val) + "'")
        elif old_val and not new_val and (db_field == "dating_start" or db_field == "dating_end"):
            #TODO delete
            sql = "UPDATE buildings SET skipped=1 WHERE id_building = " + str(old_data[0])
            cur.execute(sql)
            print("No new value for " + str(old_val))
            return True
    
    changed = False    
    if len(updates) > 0:
        print(old_data)
        sql = "UPDATE plafond.`" + info["name"] + "` SET " + ",".join(updates) + " WHERE " + info["primary_key"] + "=" + str(old_data[0])
        cur.execute(sql, values)
        changed = True
    
    for join_table in info["lists"]:
        (name_export, key_ref_table, ref_table, where_part) = info['lists'][join_table]

        sql = "SELECT " + key_ref_table + " FROM plafond.`" + join_table + "` WHERE " + info["primary_key"] + " = " + str(old_data[0])
        cur.execute(sql)
        existing_ids = list(map(lambda x: x[0], cur.fetchall()))
        
        list_data = get_list_data(info, row, name_export)
        
        new_ids = []
        for li in list_data:
            sql = "SELECT " + key_ref_table + " FROM plafond.`" + ref_table + "` WHERE " + where_part
            cur.execute(sql, (li))
            sub_res = cur.fetchone()
            
            if sub_res == None:
                raise Exception("Field '" + name_export + "' with value '" + li + "' not found.")
            
            new_ids.append(sub_res[0])
        
        for eid in existing_ids:
            if eid not in new_ids:
                sql = "DELETE FROM plafond.`" + join_table + "` WHERE " + info["primary_key"] + " = %s AND " + key_ref_table + " = %s"
                cur.execute(sql, (old_data[0], eid))
                changed = True
           
        for nid in new_ids:
            if nid not in existing_ids:
                sql = "INSERT INTO plafond.`" + join_table + "` (" + info["primary_key"] + ", " + key_ref_table + ") VALUES (%s, %s)"
                cur.execute(sql, (old_data[0], nid))
                changed = True
                
    for join_table in info["connections"]:
        (conn_types, element_types, type_field, type_field_fun, key_ref_table, ref_table) = info["connections"][join_table]

        sql = "SELECT " + key_ref_table + ", " + type_field + " FROM plafond.`" + join_table + "` WHERE " + info["primary_key"] + " = " + str(old_data[0])
        cur.execute(sql)
        existing_conns = cur.fetchall()
        
        new_conns = []
        for (export_id, export_type) in find_connections_with_types(entry_id, conn_types, element_types):
            db_type_val = globals().get(type_field_fun)(export_type)
            sql = "SELECT " + key_ref_table + " FROM plafond.`" + ref_table + "` WHERE source_id = %s" 
            cur.execute(sql, (export_id))
            sub_res = cur.fetchone()
            
            if sub_res == None:
                raise Exception("Field '" + type_field + "' with value '" + export_id + "' not found.")
            
            new_conns.append((sub_res[0], db_type_val))
        
        for (eid, etype) in existing_conns:
            if (eid, etype) not in new_conns:
                sql = "DELETE FROM plafond.`" + join_table + "` WHERE " + info["primary_key"] + " = %s AND " + key_ref_table + " = %s"
                cur.execute(sql, (old_data[0], eid))
                changed = True
        
        for (nid, ntype) in new_conns:
            if (nid, ntype) not in existing_conns:
                sql = "INSERT INTO plafond.`" + join_table + "` (" + info["primary_key"] + ", " + key_ref_table + ", " + type_field + ") VALUES (%s, %s, %s)"
                cur.execute(sql, (old_data[0], nid, ntype))
                changed = True
            
        
    
    return changed

def get_connections (eid):
    return [e for e in conns if e["id"] == eid] # or e["DATA"] == eid

def create_new_entry (row, info, cur):
    eid = row[info["id_field"]]
    
    import_keys = info["import_columns"].keys()
    columns = list(import_keys) + list(info["auto_columns"].keys())
    used_fields = []
    
    for ikey in import_keys:
        (new_val, _) = get_field_data(row, info["import_columns"][ikey], eid, info)
        used_fields.append(new_val)
        
    #TODO lists, connections

    sql = "INSERT INTO " + info["name"] + " (source_id," + ",".join(columns) + ") VALUES(%s" + (",%s" * len(columns)) + ")"
    fields = [eid] + used_fields + list(info["auto_columns"].values())
    print(fields)
    
    cur.execute(sql, fields)
    id_mapping[row["type"]][eid] = cur.lastrowid

def handle_row (row, cur):
    if row["type"] != "OBJ#PAINTING":
        return #TODO REMOVE
    
    if row["type"] in object_table_mapping:
        info = object_table_mapping[row["type"]]
        
        if "condition" in info:
            fun = globals().get(info["condition"])
            if not fun(row):
                return False
        
        fields = [info["primary_key"],"skipped"] + list(info["import_columns"].keys()) #TODO remove skipped
        sql = "SELECT " + ",".join(fields) + " FROM plafond.`" + info["name"] + "` WHERE source='deckenmalerei' AND source_id = %s"
        cur.execute(sql, row[info["id_field"]])
        old_data = cur.fetchone()
        
        if (old_data):
            return update_fields(row, cur, info, old_data)
        else:
            create_new_entry(row, info, cur)
            
        return True
    return False

def fill_id_mapping (type_name, cur):
    id_mapping[type_name] = {}
    
    info = object_table_mapping[type_name]
    sql = "SELECT " + info["primary_key"] + ", source_id FROM plafond.`" + info["name"] + "`"
    cur.execute(sql)
    
    
    for (eid, did) in cur.fetchall():
        id_mapping[type_name][did] = eid

if __name__ == "__main__":
    conn = conn_3310()
    
    with open(OBJECT_FILE, encoding="utf8") as f, open(CONNECTION_FILE, encoding="utf8") as cf:
        data = json.load(f)
        conns = json.load(cf)
        
        with conn.cursor() as cur:
            
            # for row in data:
            #     if row["type"] == "OBJ#PERSON":
            #         print(str(row) + ",")
            # exit(0)
            
            sql = "SELECT * FROM plafond.changes"
            cur.execute(sql)
            for row in cur.fetchall():
                if not row[0] in changes:
                    changes[row[0]] = []
                changes[row[0]].append(row)

            for row in data:
                type_mapping[row["DATA"]] = row["type"]

            for object_type in object_table_mapping.keys():
                
                fill_id_mapping(object_type, cur)
                
                for row in data:
                    if row["type"] == object_type:
                        if handle_row(row, cur):
                            print(row)
                            conn.commit()
                            #exit()
                

                    
            
