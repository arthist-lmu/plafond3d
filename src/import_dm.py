from src.importer import Importer, not_inferred
from memoization import cached
import re
from src.db_connection import conn_3310
from copy import copy

class DM_Importer (Importer):

    def __init__ (self):

        object_file = ["../dumps/deckenmalerei.eu/2023_11/entities.json", "../dumps/deckenmalerei.eu/2023_11/resources.json"]
        connection_file = "../dumps/deckenmalerei.eu/2023_11/relations.json"
        
        basic_info = {
            "id_field": "ID",
            "type_field": "sType",
            "dbname" : "deckenmalerei",
            "conn_id1" : "ID",
            "conn_id2" : "relTar",
            "conn_type_field" : "sType",
            "conn_dir_field" : "relDir"
        }
        
        object_table_mapping = {
            "ACTOR_PERSON" : {
                "name" : "persons",
                "primary_key": "id_person",
                "import_columns": {
                    "full_name" : "appellation",
                    "first_name" : ["appellation", "get_first_name"],
                    "last_name" : ["appellation", "get_last_name"],
                    "wikidata_id": ["normdata", "find_qid_from_normdata"]
                },
                "lists" : {},
                "connections" : {},
                "auto_columns" : {
                    "source": ("CONST", "deckenmalerei"),
                    "id_person_unique" : ("FUNC", "get_id_person_unique")
                }
            },
            "OBJECT_BUILDING": {
                "name": "buildings",
                "primary_key" : "id_building",
                "import_columns": {
                    "title": "appellation",
                    "wikidata_id": ["normdata", "find_qid_from_normdata"],
                    "longitude": ["locationLng", "to_str"],
                    "latitude": ["locationLat", "to_str"],
                    "address_street": "addressStreet",
                    "address_zip": "addressZip",
                    "address_locality": "addressLocality",
                    "country": ["addressCountry", "find_mapped_name"],
                    "condition" : ["condition", "combine_to_single_field"],
                    "dating_original": "verbaleDating",
                    "dating_start": ["verbaleDating", "get_start_year"],
                    "dating_start_approx" : ["verbaleDating", "get_year_approx"],
                    "dating_end": ["verbaleDating", "get_end_year"],
                    "dating_end_approx" : ["verbaleDating", "get_year_approx"],
                    #"url_photo" : "leadImg"
                },
                "lists" : {
                    "building_function_join": ["functions", "id_building_function", "building_functions", ("name_e", True), "create_building_function"]
                },
                "connections" : {
                    "building_person_join" : [["ACTOR_PERSON"], "connection_type", "id_person", "persons"]
                },
                "auto_columns" : {
                    "source": ("CONST", "deckenmalerei")
                }
            },
            "OBJECT_ROOM" : {
                "name" : "rooms",
                "primary_key": "id_room",
                "import_columns" : {
                    "title": "appellation",
                    "id_building": ["FK", "find_building_for_room"],
                    "condition": ["condition", "combine_to_single_field"],
                    "width" : ["dimension", "get_width"],
                    "length" : ["dimension", "get_length"],
                    "height" : ["dimension", "get_height"],
                    "dating_original": "verbaleDating",
                    "dating_start": ["verbaleDating", "get_start_year"],
                    "dating_start_approx" : ["verbaleDating", "get_year_approx"],
                    "dating_end": ["verbaleDating", "get_end_year"],
                    "dating_end_approx" : ["verbaleDating", "get_year_approx"],
                    #"url_photo" : "leadImg"
                },
                "lists" : {
                    "room_function_join": ["functions", "id_room_function", "room_functions", ("name_e", True), "create_room_function"]
                },
                "connections" : {
                    "room_person_join" : [["ACTOR_PERSON"], "connection_type", "id_person", "persons"]
                },
                "auto_columns" : {
                    "source": ("CONST", "deckenmalerei"),
                    "floor" : ("CONST", None)
                }
            },
            "OBJECT_PAINTING" : {
                "name" : "plafonds",
                "primary_key": "id_plafond",
                "import_columns": {
                    "title" : "appellation",
                    "id_room": ["FK", "find_room_for_plafond"],
                    "dating_original": ["verbaleDating", "none_to_empty"],
                    "dating_start": ["verbaleDating", "get_start_year"],
                    "dating_start_approx" : ["verbaleDating", "get_year_approx"],
                    "dating_end": ["verbaleDating", "get_end_year"],
                    "dating_end_approx" : ["verbaleDating", "get_year_approx"],
                    "technique" : [("productionMaterials", "productionMethods"), "combine_lists_to_single_fields"],
                    "condition" : ["condition", "combine_to_single_field"],
                    #"url_photo" : "leadImg",
                    "signature" : "signature"
                },
                "lists" : {
                    "plafond_iconclass_join": ["iconography", "iconclass_id", "iconclasses", ("iconclass_id", False), "create_iconclass"]
                },
                "connections" : {
                    "plafond_person_join" : [["ACTOR_PERSON"], "connection_type", "id_person", "persons"]
                },
                "auto_columns" : {
                    "source": ("CONST", "deckenmalerei")
                },
                "condition" : "is_plafond"
            }
        }
        
        super().__init__(object_file, connection_file, basic_info, object_table_mapping)
        
    def data_function (self, data):
        return data
    
    def conn_function (self, conns):
        for conn in conns:
            conn["relDir"] = True if conn["relDir"] == "->" else False
        
        return conns


    def is_plafond (self, row):
        return "position" in row and "ceiling" in row["position"] and row["position"]["ceiling"]

    def get_value_from_key (self, field, key):
        if key in field:
            return field[key]
        
        return ""

    def get_start_year (self, dating, dbname, table, field):
        return self.handle_year(dating, dbname, table, field)[0]
    
    def get_end_year (self, dating, dbname, table, field):
        return self.handle_year(dating, dbname, table, field)[1]
    
    def get_year_approx (self, dating, dbname, table, field):
        return self.handle_year(dating, dbname, table, field)[2]

    @cached
    def handle_year (self, dating, dbname, table, field):
        if dating == None:
            return (None, None, False)
        
        if re.match("^[1-9][0-9]{3}$", dating):
            return (int(dating), int(dating), False)
        
        matchObject = re.match("^(?:um|wohl um) ([1-9][0-9]{3})$", dating)
        if matchObject:
            return (int(matchObject[1]), int(matchObject[1]), True)
    
        matchObject = re.match("^([1-9][0-9]{3}) ?[" + re.escape("–-/") + "] ?([1-9][0-9]{3})$", dating)
        if matchObject:
            return (int(matchObject[1]), int(matchObject[2]), False)
        
        matchObject = re.match("^([1-9][0-9]{3}) ?[" + re.escape("–-/") + "] ?([0-9]{2})$", dating)
        if matchObject:
            return (int(matchObject[1]), int(matchObject[1][0:2] + matchObject[2]), False)
        
        matchObject = re.match("^([1-9][0-9])(\.)? Jh\.$", dating) #TODO maybe require the dot after the number
        if matchObject:
            century = int(matchObject[1])
            return ((century - 1) * 100 + 1, century * 100, True)
        
        if (dating.find(",") != -1 or dating.find(";") != -1):
            parts = re.split(" ?[,;] ?", dating)
            
            first = None
            current = None
            for part in parts:
                newRange = self.handle_year(part, dbname, table, field)
                
                if not newRange[0] or not newRange[1]:
                    return (None, None, False)
                if newRange[0] > 1800:
                    break
                if not first:
                    first = newRange
                current = newRange
                
            return (first[0], current[1], False) 
        return (None, None, False)

    def find_qid_from_normdata (self, normdata, dbname, table, field):

        if normdata == None or not "gnd" in normdata:
            return None
        
        query = "SELECT ?item WHERE {?item wdt:P227 '" + normdata["gnd"] + "'.}"
        json_result = self.sparql_wikidata(query)
        
        if json_result == None:
            return None
        
        if len(json_result["results"]["bindings"]) == 1:
            return json_result["results"]["bindings"][0]["item"]["value"].rsplit("/", 1)[-1]
        return None
    
    def get_dim_part (self, dim, key):
        if dim == None or key not in dim:
            return ""
        
        return str(dim[key])
    
    @not_inferred
    def get_width (self, dim, dbname, table, field):
        return self.get_dim_part(dim, "width")
    
    @not_inferred
    def get_length (self, dim, dbname, table, field):
        return self.get_dim_part(dim, "length")
    
    @not_inferred
    def get_height (self, dim, dbname, table, field):
        return self.get_dim_part(dim, "height")
    
    
    def find_building_for_room (self, eid, dbname, table, field):
        return self.find_transitive_connection(eid, "OBJECT_BUILDING", "PART", ["OBJECT_ROOM", "OBJECT_ROOM_SEQUENCE", "OBJECT_BUILDING_DIVISION"], False)


    def find_room_for_plafond (self, eid, dbname, table, field):
        try:
            return self.find_transitive_connection(eid, "OBJECT_ROOM", "PART", ["OBJECT_PICTURE_CYCLE"], False)
        except Exception:
            try:
                bid = self.find_transitive_connection(eid, "OBJECT_BUILDING", "PART", ["OBJECT_PICTURE_CYCLE", "OBJECT_ROOM_SEQUENCE", "OBJECT_BUILDING_DIVISION"], False)
                return self.create_pseudo_room(bid)
            except Exception as e:
                raise e
                return None
            
    def create_pseudo_room (self, building_sid):
        building_id = self.id_mapping["OBJECT_BUILDING"][building_sid]
        
        sid = building_sid + "_PR"
        sql = "SELECT id_room FROM rooms WHERE source = %s AND source_id = %s"
        self.cur.execute(sql, (self.dbname, sid))
        
        dbres = self.cur.fetchone()
        dbid = None
        if dbres != None:
            dbid = dbres[0]
        
        if not dbid:
            sql = "INSERT INTO rooms (title, id_building, source, source_id) VALUES ('PSEUDO_ROOM', %s, %s, %s)"
            self.cur.execute(sql, (building_id, self.dbname, sid))
            self.conn.commit()
            dbid = self.cur.lastrowid
        
        self.id_mapping["OBJECT_ROOM"][sid] = dbid
        self.type_mapping[sid] = "OBJECT_ROOM"
        self.id_handled("rooms", dbid)
        
        return sid
    
 
    def find_transitive_connection (self, eid, objectType, connType, intermObjects, direction):
        result_id = None
        current_element = eid

        while current_element != None and result_id == None:
            conns = self.get_connections(current_element, direction)
            current_element = None
            
            for conn in conns:
                currentObjectType = self.type_mapping[conn["relTar"]]
                if currentObjectType == objectType and conn["sType"] == connType:
                    result_id = conn["relTar"]
                    break
                    
                if currentObjectType in intermObjects and conn["sType"] == connType:
                    current_element = conn["relTar"]
                    break
                
        if result_id == None:
            raise Exception("Object connection not found (" + eid + ", " + objectType + ").")
        
        return result_id
        
    
    def get_conn_name_from_type (self, full_name):
        return full_name
    
if __name__ == "__main__":
    importer = DM_Importer()
    importer.do_import()
