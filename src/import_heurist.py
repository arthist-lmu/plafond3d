from src.importer import Importer, not_inferred
import re
from overrides import override
from memoization import cached

class Heurist_Importer (Importer):
    def __init__ (self):

        object_file = "../dumps/heurist/Export_PLAFOND_3D_20250225110423.json"
        connection_file = None
        
        self.temp_conns = []
        
        basic_info = {
            "id_field": "rec_ID",
            "type_field": "rec_RecTypeName",
            "dbname": "heurist",
            "conn_id1" : "id1",
            "conn_id2" : "id2",
            "conn_type_field" : "type",
            "conn_dir_field" : "dir"
        }
        
        self.person_data = {
            "Pièce" : [
                {"fields" : {"full_name": "Architecte / Architekt", "wikidata_id": "ID wikidata Architecte / Architekt"}, "connection": "Architecte / Architekt"},
                {"fields" : {"full_name": "Artiste(s) - Auteur(s) décor mural / Autor der Wanddekoration", "wikidata_id": "ID wikidata Artiste(s)/Auteur(s) décor mural / Autor der Wanddekoration"}, "connection": "Artiste"}
            ],
            "Plafond" : [
                 {"fields" : {"full_name": "Auteur(s) principal / Autor", "wikidata_id": "ID wikidata auteur(s) principal / ID wikidata Autor"}, "connection": "Auteur"},
                {"fields" : {"full_name": "Auteur(s) secondaires / Mitarbeiter", "wikidata_id": "ID wikidata auteur(s) secondaire(s) / ID wikidata Mitarbeiter"}, "connection": "Auteur"},
                {"fields" : {"full_name": "Commanditaire(s) / Auftrageber*in", "wikidata_id" : "ID wikidata commanditaire(s) / ID wikidata Auftrageber*in"}, "connection": "Commanditaire"}
            ]
        }
            
        object_table_mapping = {
            "Personne" : {
                "name" : "persons",
                "primary_key": "id_person",
                "import_columns": {
                    "full_name": ["full_name", "handle_full_name"],
                    "first_name" : ["full_name", "get_first_name"],
                    "last_name" : ["full_name", "get_last_name"],
                    "wikidata_id" : ["wikidata_id", "handle_qid"],
                    "gender" : ["wikidata_id", "get_gender"]
                },
                "lists" : {},
                "connections" : {},
                "auto_columns" : {
                    "source": ("CONST", "heurist"),
                    "id_person_unique" : ("FUNC", "get_id_person_unique")
                }
            },
            "Edifice / Bauwerk" : {
                "name" : "buildings",
                "primary_key": "id_building",
                "import_columns": {
                    "title" : [("Titre courant / Titel", "Adresse actuelle (commune)"), "add_locality"],
                    "wikidata_id" : "ID wikidata édifice",
                    "country": "Pays",
                    "longitude": "Longitude X", #[("Latitude X", "Longitude Y"), "correct_lat_lng"],
                    "latitude": "Latitude Y", #[("Latitude X", "Longitude Y"), "correct_lat_lng"],
                    "address_street": ["Adresse actuelle (rue et numéro)", "none_to_empty"],
                    "address_zip": ["Adresse actuelle (code postal)", "none_to_empty"],
                    "address_locality": ["Adresse actuelle (commune)", "none_to_empty"],
                    "dating_original" : [("Date inférieure / Frühestes Datum", "Date supérieure / Spätestes Datum"), "handle_unformated_date"],
                    "dating_start": ["Date inférieure / Frühestes Datum", "handle_date"],
                    "dating_end": ["Date supérieure / Spätestes Datum", "handle_date"],
                    "dating_start_approx": ["Date inférieure / Frühestes Datum", "handle_approx"],
                    "dating_end_approx": ["Date supérieure / Spätestes Datum", "handle_approx"]
                },
                "lists" : {
                    "building_function_join": ["Fonction / Funktion", "id_building_function", "building_functions", ("name_e", True), "create_building_function", False]
                },
                "connections" : {},
                "auto_columns" : {
                    "source": ("CONST", "heurist")
                }
            },
            "Pièce" : {
                "name" : "rooms",
                "primary_key": "id_room",
                "import_columns": {
                    "title" : "Dénomination actuelle / Aktuelle Bezeichnung",
                    "id_building": ["Édifice / Teil von Bauwerk", "handle_fk"],
                    "length": ["Longueur / Länge", "parse_dim"],
                    "width": ["Largeur / Breite", "parse_dim"],
                    "height": ["Hauteur / Höhe", "parse_dim"],
                    "floor": ["Niveau / Stockwerk", "append_elements"],
                    "condition" : ["Etat de conservation pièce / Erhaltungszustand Raum", "find_mapped_name"],
                    "dating_original" : [("Date inférieure pièce / frühestes Datum Raum", "Date supérieure pièce / spätestes Datum"), "handle_unformated_date"],
                    "dating_start": ["Date inférieure pièce / frühestes Datum Raum", "handle_date"],
                    "dating_end": ["Date supérieure pièce / spätestes Datum", "handle_date"],
                    "dating_start_approx": ["Date inférieure pièce / frühestes Datum Raum", "handle_approx"],
                    "dating_end_approx": ["Date supérieure pièce / spätestes Datum", "handle_approx"],
                    "url_photo" : ["URL photo", "first_in_list"]
                },
                "lists" : {
                    "room_function_join": ["Fonction au moment du décor", "id_room_function", "room_functions", ("name_e", True), "create_room_function", False]
                },
                "connections" : {
                    "room_person_join" : [["Personne"], "connection_type", "id_person", "persons", False]
                },
                "auto_columns" : {
                    "source": ("CONST", "heurist")
                }
            },
            "Plafond" : {
                "name" : "plafonds",
                "primary_key": "id_plafond",
                "import_columns": {
                    "title": "Titre notice",
                    "id_room": ["Référence pièce / Teil von  Raum", "handle_fk"],
                    "dating_original" : [("Date inférieure / Frühestes Datum", "Date supérieure / Spätestes Datum"), "handle_unformated_date"],
                    "dating_start": ["Date inférieure / Frühestes Datum", "handle_date"],
                    "dating_end": ["Date supérieure / Spätestes Datum", "handle_date"],
                    "dating_start_approx": ["Date inférieure / Frühestes Datum", "handle_approx"],
                    "dating_end_approx": ["Date supérieure / Spätestes Datum", "handle_approx"],
                    "condition" : ["État de conservation / Erhaltungszustand", "find_mapped_name"],
                    "url_photo" : ["URL photo / URL Fotografie", "get_img_url"],
                    "url_invalid" : ["URL photo / URL Fotografie", "get_img_invalid"],
                    'cc_licence' : ["URL photo / URL Fotografie", "is_cc"],
                    "signature" : "Inscription signature / Inschrift, Signatur",
                    "technique" : ["Technique / Technik", "find_mapped_name"]
                },
                "lists" : {
                    "plafond_iconclass_join": 
                        [("Centre Iconclass / Iconlass der Deckenmitte", "Côté Iconclass / Iconclass der Seitenbereiche", "Iconclass sujet général / Iconclass, Allgemeines Sujet"), "iconclass_id", "iconclasses", ("iconclass_id", False), "create_iconclass", False],
                },
                "connections" : {
                    "plafond_person_join" : [["Personne"], "connection_type", "id_person", "persons", False]
                },
                "auto_columns" : {
                    "source": ("CONST", "heurist"),
                    "dating_source": ("CONST", "plafond")
                }
            },
        }
        
        self.fk_mapping = {
            "id_room" : "Pièce",
            "id_building" : "Edifice / Bauwerk"
        }
        
        super().__init__(object_file, connection_file, basic_info, object_table_mapping)
       
    @not_inferred
    def get_img_url (self, val, dbname, table, field):
        return self.handle_img_urls(val)[0]
    
    @not_inferred
    def get_img_invalid (self, val, dbname, table, field):
        return self.handle_img_urls(val)[1]
     
    @cached
    def handle_img_urls (self, urls):
        if urls is None:
            return (None, False)
        
        for url in urls:
            if self.check_url(url):
                return (url, False)
            
        return (urls[0], True)
        
    @not_inferred
    def add_locality (self, val, dbname, table, field):
        if not val["Titre courant / Titel"]:
            return ""
        
        if not val["Adresse actuelle (commune)"]:
            return val["Titre courant / Titel"]
        
        return val["Adresse actuelle (commune)"] + ", " + val["Titre courant / Titel"]
        
    @not_inferred
    def is_cc (self, val, dbname, table, field):
        if val is None or not val[0]:
            return False
        
        return val[0].startswith("https://upload.wikimedia.org")
       
    @not_inferred
    def parse_dim (self, s, dbname, table, field):
        if s == None:
            return ""
        
        s = str(s).replace(",", ".")
        
        posBracket = s.find(" (")
        if posBracket != -1:
            s = s[0:posBracket]
            
        return s
       
    @not_inferred 
    def correct_lat_lng (self, params, dbname, table, field):
        
        if params["Longitude Y"] == None or params["Latitude X"] == None:
            return None
        
        if field == "longitude" and float(params["Longitude Y"]) > 20:
            return params["Latitude X"]
        
        if field == "latitude" and float(params["Latitude X"]) < 20:
            return params["Longitude Y"]
        
        elif field == "longitude":
            return params["Longitude Y"]
        
        return params["Latitude X"]
            
        
    @not_inferred
    def handle_unformated_date (self, params, dbname, table, field):
        keys = list(params.keys())
        start = params[keys[0]]
        end = params[keys[1]]
        
        if (start and not end) or start == end:
            return start
        elif end and not start:
            return end
        elif start and end:
            return start + " - " + end
        
        return None
        
    @not_inferred
    def handle_date (self, s, dbname, table, field):
        if s == "???" or s == None:
            return None
        
        try:
            if s.endswith("*"):
                return int(s[:-1])
            
            return int(s)
        except:
            return None
        
    def get_gender (self, val, dbname, table, field):
        (qid, _) = self.handle_qid (val, dbname, table, field)
        
        if qid == None:
            return ""
        
        query = "SELECT ?genderLabel WHERE { ?item wdt:P21 ?gender. FILTER (?item = wd:" + qid + "). SERVICE wikibase:label {bd:serviceParam wikibase:language 'en'.}}"
        json_result = self.sparql_wikidata(query)
        
        if json_result == None:
            return ""
        
        if len(json_result["results"]["bindings"]) == 1:
            return json_result["results"]["bindings"][0]["genderLabel"]["value"][0]
        
        return None
    
    @not_inferred
    def handle_approx (self, s, dbname, table, field):
        if s == None:
            return False
        
        return s.endswith("*")
    
    def is_list_mapping (self, data):
        res = {}
        for record in data["heurist"]["records"]:
            tempMap = {}
            for detail in record["details"]:
                if not detail["fieldName"] in tempMap:
                    tempMap[detail["fieldName"]] = 0
                    
                tempMap[detail["fieldName"]] += 1
            
            for fieldName in tempMap:
                if tempMap[fieldName] > 1:
                    res[fieldName] = True
                elif fieldName not in res:
                    res[fieldName] = False
                    
        return res
                    
        
    def data_function (self, data):
        is_list = self.is_list_mapping(data)

        res = []
        for record in data["heurist"]["records"]:
            obj = {k: v for (k,v) in record.items() if k in ("rec_ID", "rec_RecTypeName")}
            for detail in record["details"]:
                if detail["fieldType"] == "enum":
                    newVal = detail["termLabel"]
                elif detail["fieldType"] == "file":
                    newVal = detail["value"]["file"]["ulf_ExternalFileReference"]
                else:
                    newVal = detail["value"]
                    
                if is_list[detail["fieldName"]]:
                    if not detail["fieldName"] in obj:
                        obj[detail["fieldName"]] = []
                    obj[detail["fieldName"]].append(newVal)
                else:
                    obj[detail["fieldName"]] = newVal
                 
            (obj, extra_data) = self.handle_persons(obj)
                 
            res.append(obj)
            for extra in extra_data:
                res.append(extra)
            
        return res
    
    #Create own entries and connections for persons
    def handle_persons (self, obj):
        pdata = []
        person_id = 0
        
        if obj[self.type_field] in self.person_data:
            for row in self.person_data[obj[self.type_field]]:           
                max_elements = 0
                for dbfield, ofield in row["fields"].items():
                    if ofield in obj and len(obj[ofield]) > max_elements:
                        max_elements = len(obj[ofield])
                for i in range(0, max_elements):
                    id_str = "R" + obj[self.id_field] + "_P" + str(person_id)
                    person_id += 1
                    cdata = {}
                    for dbfield, ofield in row["fields"].items():
                        cdata[dbfield] = obj[ofield][i] if ofield in obj and i < len(obj[ofield]) else None
                    pdata.append({
                        "rec_ID": id_str,
                        "rec_RecTypeName" : "Personne" 
                    } | cdata)
                    
                    self.temp_conns.append({
                        "id1" : obj[self.id_field],
                        "id2" : id_str,
                        "type" : row["connection"],
                        "dir" : True
                    })
                    
                for ofield in row["fields"]:
                    if ofield in obj:
                        del obj[ofield]

        return (obj, pdata)
    
    def finalize_statistics_data (self):

        # Remove statistics data from the type "Personne" needed for the import and move it to the actual db fields
        del self.statistics["Personne"]
        
        for otype in self.person_data:
            for info in self.person_data[otype]:
                for field_pseudo in info["fields"]:
                    field_orig = info["fields"][field_pseudo]
                    for field_db in self.object_table_mapping["Personne"]["import_columns"]:
                        if self.object_table_mapping["Personne"]["import_columns"][field_db][0] == field_pseudo:
                            self.update_statistics(otype, field_orig, "persons->" + field_db)
    
    def conn_function (self, conns):
        return self.temp_conns

    @not_inferred
    def handle_fk (self, val, dbname, table, field):
        heurist_id = val["id"]
        
        ref_entity = self.fk_mapping[field]
        dbid = self.id_mapping[ref_entity][heurist_id]
        
        return dbid      
    
    def get_conn_name_from_type (self, full_name):
        return full_name
    
    @not_inferred
    def handle_full_name (self, full_name, dbname, table, field):
        return self.remove_brackets_from_name(full_name)
    
    def remove_brackets_from_name (self, full_name):
        if full_name[-1] == ")":
            full_name = full_name[0: full_name.rfind(" (")]
            
        return full_name
    
    @cached
    @override
    def handle_name (self, full_name, dbname, table, field):
        if full_name == None:
            return (None,None)
        
        full_name = self.remove_brackets_from_name(full_name)
        
        return super().handle_name(full_name, dbname, table, field)
    
    @not_inferred
    def handle_qid (self, qid, dbname, table, field):
        if qid == None:
            return None
                    
        if re.match("^Q[0-9]+$", qid):
            return qid
        
        return None
    
if __name__ == "__main__":
    importer = Heurist_Importer()
    importer.do_import() #only = "Plafond"
        