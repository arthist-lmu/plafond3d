from src.importer import Importer, not_inferred
from memoization import cached
import re
import urllib.request
import urllib.parse
import urllib3
import json
import datetime

class DM_Importer (Importer):

    def __init__ (self):

        self.fmd_map = {}
        self.img_info = {
            "cc" : [],
            "no_cc" : [],
            "no_small" : [],
            "missing_fm" : [],
            "missing_zi" : [],
            "missing_other" : [],
            "missing_mixed" : [],
            "no_connection" : []
        }
        self.easydb_api_prefix = "https://deckenmalerei-bilder.badw.de/api/v1/"

        object_file = ["../dumps/deckenmalerei.eu/2025_02/entities.json", "../dumps/deckenmalerei.eu/2025_02/resources.json"]
        connection_file = "../dumps/deckenmalerei.eu/2025_02/relations.json"
        
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
                    "wikidata_id": ["normdata", "find_qid_from_normdata"],
                    "gender" : ["gender", "get_gender"],
                    "gnd": ["normdata", "get_gnd_from_normdata"]
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
                    "title": ["appellation", "handle_title"],
                    "wikidata_id": ["normdata", "find_qid_from_normdata"],
                    "longitude": ["locationLng", "to_str"],
                    "latitude": ["locationLat", "to_str"],
                    "address_street": "addressStreet",
                    "address_zip": "addressZip",
                    "address_locality": "addressLocality",
                    "country": ["addressCountry", "find_mapped_name"],
                    "condition" : ["condition", "combine_to_single_field_overwrite"],
                    "dating_original": "verbaleDating",
                    "dating_start": ["verbaleDating", "get_start_year"],
                    "dating_start_approx" : ["verbaleDating", "get_year_approx"],
                    "dating_end": ["verbaleDating", "get_end_year"],
                    "dating_end_approx" : ["verbaleDating", "get_year_approx"],
                    #"url_photo" : "leadImg"
                },
                "lists" : {
                    "building_function_join": ["functions", "id_building_function", "building_functions", ("name_e", True), "create_building_function", "original_name"]
                },
                "connections" : {
                    "building_person_join" : [["ACTOR_PERSON"], "connection_type", "id_person", "persons", "original_name"]
                },
                "auto_columns" : {
                    "source": ("CONST", "deckenmalerei")
                }
            },
            "OBJECT_ROOM" : {
                "name" : "rooms",
                "primary_key": "id_room",
                "import_columns" : {
                    "title": ["appellation", "handle_title"],
                    "id_building": ["FK", "find_building_for_room"],
                    "condition": ["condition", "combine_to_single_field_overwrite"],
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
                    "room_function_join": ["functions", "id_room_function", "room_functions", ("name_e", True), "create_room_function", "original_name"]
                },
                "connections" : {
                    "room_person_join" : [["ACTOR_PERSON"], "connection_type", "id_person", "persons", "original_name"]
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
                    "title" : ["appellation", "handle_title"],
                    "id_room": ["FK", "find_room_for_plafond"],
                    "dating_original": ["verbaleDating", "get_painting_dating"],
                    "dating_start": ["verbaleDating", "get_start_year_painting"],
                    "dating_start_approx" : ["verbaleDating", "get_year_approx_painting"],
                    "dating_end": ["verbaleDating", "get_end_year_painting"],
                    "dating_end_approx" : ["verbaleDating", "get_year_approx_painting"],
                    "dating_source" : ["verbaleDating", "get_dating_source"],
                    "technique" : [("productionMaterials", "productionMethods"), "combine_lists_to_single_fields_overwrite"],
                    "condition" : ["condition", "combine_to_single_field_overwrite"],
                    "url_photo" : ["ID", "get_img_url"],
                    "cc_licence" : ["ID", "get_licence"],
                    "signature" : "signature"
                },
                "lists" : {
                    "plafond_iconclass_join": ["iconography", "iconclass_id", "iconclasses", ("iconclass_id", False), "create_iconclass", False]
                },
                "connections" : {
                    "plafond_person_join" : [["ACTOR_PERSON"], "connection_type", "id_person", "persons", "original_name"]
                },
                "auto_columns" : {
                    "source": ("CONST", "deckenmalerei")
                }
            }
        }
        
        self.id_index_map = {}
        
        super().__init__(object_file, connection_file, basic_info, object_table_mapping)
        
    def data_function (self, data):
        for row in data:
            self.id_index_map[row["ID"]] = row

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

    @cached
    def infer_painting_dating (self, eid, datingDirect):
        if datingDirect:
            return (datingDirect, "plafond")
        
        pcycle_info = self.find_connections_with_types(eid, ["OBJECT_PICTURE_CYCLE"], self.dbname, "plafonds", "cycle")
       
        if len(pcycle_info) == 0:
            id_room = self.find_transitive_connection(eid, "OBJECT_ROOM", "PART", ["OBJECT_PICTURE_CYCLE"], False)
            if id_room and id_room in self.id_index_map and "verbaleDating" in self.id_index_map[id_room]:
                return (self.id_index_map[id_room]["verbaleDating"], "room")
            return (None, None)
         
        pcycle_data = self.id_index_map[pcycle_info[0][0]]
        if "verbaleDating" in pcycle_data:
            return (pcycle_data["verbaleDating"], "cycle")
        
        return (None, None)

    @not_inferred
    def get_img_url (self, id, dbname, table, field):
        return self.find_img(id)[0]
    
    @not_inferred
    def get_licence (self, id, dbname, table, field):
        res = self.find_img(id)[1]
        if not res:
            return False
        return res.startswith("CC")
        
    @not_inferred
    def handle_title (self, title, dbname, table, field):
        if not title:
            return "(Missing title)"
        
        return title

    @cached
    def find_img (self, id):

        lead = []
        other = []
        for conn in self.get_connections(id):
            rid = conn["relTar"] if conn["ID"] == id else conn["ID"]
            
            if conn["sType"] == "LEAD_RESOURCE" and rid not in lead:
                lead.append(rid)
            elif conn["sType"] == "IMAGE" and rid not in other:
                other.append(rid)
                
        if len(lead) == 0 and len(other) == 0: 
            self.img_info["no_connection"].append(id)
            return (None, None)
        
        # if resource["resProvider"] == "https://deckenmalerei-bilder.badw.de/":
        #     url = self.easydb_api_prefix + "objects/uuid/" + resource["ID"]
        #     f = urllib.request.urlopen(url)
        #     data = json.loads(f.read())
        #
        #     try:
        #         url = data["assets"]["datei"][0]["versions"]["small"]["url"]
        #         licence = data["assets"]["copyright"]["_sort"]["de-DE"] if "copyright" in data["assets"] else None
        #         return (url, licence)
        #     except Exception:
        #         print(data)
        #         return (None, None)
            
        imageFound = False
        for iid in lead:
            resource = self.id_index_map[iid]
            if resource["ID"] in self.fmd_map:
                imageFound = True
                break
            
        if not imageFound:
            for iid in other:
                resource = self.id_index_map[iid]
                if resource["ID"] in self.fmd_map:
                    imageFound = True
                    break
                
        if imageFound:
            if self.fmd_map[resource["ID"]]["licence"] and self.fmd_map[resource["ID"]]["licence"].startswith("CC"):
                self.img_info["cc"].append((id, resource["ID"]))
            else:
                self.img_info["no_cc"].append((id, resource["ID"]))
            return (self.fmd_map[resource["ID"]]["url"], self.fmd_map[resource["ID"]]["licence"])
        
        #No image
        sources = []
        for iid in lead + other:
            resource = self.id_index_map[iid]
            
            if resource["ID"].startswith("fm"):
                if not "fm" in sources:
                    sources.append("fm")
            elif resource["ID"].startswith("zi"):
                if not "zi" in sources:
                    sources.append("zi")
            else:
                if not "other" in sources:
                    sources.append("other")
                
                
        if len(sources) == 1 and sources[0] == "fm":
            self.img_info["missing_fm"].append((id, resource["ID"]))
        elif len(sources) == 1 and sources[0] == "zi":
            self.img_info["missing_zi"].append((id, resource["ID"]))
        elif len(sources) == 1 and sources[0] == "other":
            self.img_info["missing_other"].append((id, resource["ID"]))
        else:
            print(sources)
            self.img_info["missing_mixed"].append((id, resource["ID"]))
        
        return (None, None)

    @not_inferred
    def get_painting_dating (self, dating, dbname, table, field):
        return self.infer_painting_dating(self.cid, dating)[0]

    def get_start_year_painting (self, dating, dbname, table, field):
        dating = self.infer_painting_dating (self.cid, dating)[0]
        return self.handle_year(dating, dbname, table, field)[0]
    
    def get_end_year_painting (self, dating, dbname, table, field):
        dating = self.infer_painting_dating (self.cid, dating)[0]
        return self.handle_year(dating, dbname, table, field)[1]
    
    def get_year_approx_painting (self, dating, dbname, table, field):
        dating = self.infer_painting_dating (self.cid, dating)[0]
        return self.handle_year(dating, dbname, table, field)[2]
    
    @not_inferred
    def get_dating_source (self, dating, dbname, table, field):
        return self.infer_painting_dating(self.cid, dating)[1]

    def get_start_year (self, dating, dbname, table, field):
        return self.handle_year(dating, dbname, table, field)[0]
    
    def get_end_year (self, dating, dbname, table, field):
        return self.handle_year(dating, dbname, table, field)[1]
    
    def get_year_approx (self, dating, dbname, table, field):
        return self.handle_year(dating, dbname, table, field)[2]

    def get_gender (self, gender, dbname, table, field):
        if gender == "MALE":
            return "m"
        elif gender == "FEMALE":
            return "f"
        
        return ""

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
        
        matchObject = re.match("^([1-9][0-9])(\\.)? Jh\\.$", dating) #TODO maybe require the dot after the number
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
    
    def get_gnd_from_normdata (self, normdata, dbname, table, field):
        if normdata == None or not "gnd" in normdata:
            return None
        
        return normdata["gnd"]
    
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
    
    def create_fmd_map (self):
        
        try:
            with open("date_fmd.txt") as datefile:
                date = datetime.datetime.strptime(datefile.read().strip(), "%Y-%m-%d").date()
                if date == datetime.date.today():
                    print("Read FMD map")
                    with open("fmd.json") as datafile:
                        self.fmd_map = json.load(datafile)
                    return
        except Exception as e:
            print(e)
            pass
        
        print ("Create FMD map")
        try:
            url = self.easydb_api_prefix + "session"
            f = urllib.request.urlopen(url)
            data = json.loads(f.read())
            token = data["token"]
            #print(token)
    
            url = self.easydb_api_prefix + "session/authenticate"
            postdata = urllib.parse.urlencode({
                "token" : token,
                "login" : "fzacherl",
                "password" : "URt8hJ8hAMwjw5Zs27Abrcg$L%yIndE"
            }).encode()
            req =  urllib.request.Request(url, method="POST", data=postdata)
            f = urllib.request.urlopen(req)
            data = json.loads(f.read())
            
            http = urllib3.PoolManager()

            ready = False
            total = False
            offset = 0
            numPart = 1000
            
            while not ready:
                postdata = {
                    "limit" : numPart,
                    "offset" : offset,
                    "objecttypes" : ["assets"],
                    "search" : [
                        {
                            "type" : "in",
                            "bool" : "must",
                            "fields" : ["assets._pool.pool._id"],
                            "in": [2,5]
                        }
                    ]
                }

                r = http.request('POST', self.easydb_api_prefix + "search?token=" + token,
                             headers= {'Content-Type': 'application/json'},
                             body=json.dumps(postdata))
                odata = json.loads(r.data.decode('utf-8'))
            
                if total == False:
                    total = odata["count"]
            
                if len(odata["objects"]) == 0:
                    break
            
                for obj in odata["objects"]:
                    if not "assets" in obj or not "datei" in obj["assets"]:
                        continue
                    
                    file = obj["assets"]["datei"][0]
    
                    if not "small" in file["versions"] or not "url" in file["versions"]["small"]:
                        continue
                    
                    new_entry = {
                        "url": file["versions"]["small"]["url"],
                        "licence" : obj["assets"]["copyright"]["_sort"]["de-DE"] if "copyright" in obj["assets"] else None
                    }
                    
                    self.fmd_map[obj["_uuid"]] = new_entry
                    if obj["assets"]["_pool"]["pool"]["_id"] == 5: #Add fmd entries by deckenmalerei ID and by fmd ID, since some of them a referenced by deckenmalerei ID
                        self.fmd_map[file["original_filename_basename"]] = new_entry
                    
                offset += numPart
                ready = offset >= total
                
                print("Handled: " + str(offset) + " / " + str(total))
            
    
        except urllib.error.HTTPError as err:
            print(err.fp.read())
            
        with open("fmd.json", "w") as outfile:
            outfile.write(json.dumps(self.fmd_map))
            
        with open("date_fmd.txt", "w") as datefile:
            print(str(datetime.date.today()), file=datefile)
            
    def finalize_statistics_data (self):
        pass
    
if __name__ == "__main__":
    importer = DM_Importer()
    importer.create_fmd_map()
    importer.do_import()
    
    # for key in importer.img_info:
    #     print (key + ": " + str(len(importer.img_info[key])))
    #
    # for info in importer.img_info["missing_other"]:
    #     print(info)