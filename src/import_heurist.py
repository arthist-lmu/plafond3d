from src.importer import Importer, not_inferred
import re
from pyreadline3.configuration import startup
from pandas.io.sas.sas_constants import align_1_checker_value

class Heurist_Importer (Importer):
    def __init__ (self):

        object_file = "../dumps/heurist/Export_PLAFOND_3D_20230710142819.json"
        connection_file = None
        
        self.temp_conns = []
        
        basic_info = {
            "id_field": "rec_ID",
            "type_field": "rec_RecTypeName",
            "dbname": "heurist",
            "conn_id1" : "id1",
            "conn_id2" : "id2",
            "conn_type_field" : "type",
        }
        
        self.person_data = {
            "Pièce" : [
                {"fields" : {"full_name": "Architecte / Architekt", "qid": "ID wikidata Architecte / Architekt"}, "connection": "Architecte / Architekt"},
                {"fields" : {"full_name": "Artiste(s) - Auteur(s) décor mural / Autor der Wanddekoration", "qid": "ID wikidata Artiste(s)/Auteur(s) décor mural / Autor der Wanddekoration"}, "connection": "Artiste"}
            ]
        }
            
        object_table_mapping = {
            "Personne" : {
                "name" : "persons",
                "primary_key": "id_person",
                "import_columns": {
                    "full_name": "full_name",
                    "first_name" : ["full_name", "get_first_name"],
                    "last_name" : ["full_name", "get_last_name"],
                    "wikidata_id" : "qid"
                },
                "lists" : {},
                "connections" : {},
                "auto_columns" : {
                    "source": "heurist"
                }
            },
            "Edifice / Bauwerk" : {
                "name" : "buildings",
                "primary_key": "id_building",
                "import_columns": {
                    "title" : "Titre courant / Titel",
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
                "lists" : {},
                "connections" : {},
                "auto_columns" : {
                    "source": "heurist"
                }
            },
            "Pièce" : {
                "name" : "rooms",
                "primary_key": "id_room",
                "import_columns": {
                    "title" : "Dénomination actuelle / Aktuelle Bezeichnung",
                    "id_building": ["Édifice / Teil von Bauwerk", "handle_fk"],
                    "length": ["Longueur / Länge", "none_to_empty"],
                    "width": ["Largeur / Breite", "none_to_empty"],
                    "height": ["Hauteur / Höhe", "none_to_empty"],
                    "floor": ["Niveau / Stockwerk", "append_elements"],
                    "condition" : ["Etat de conservation pièce / Erhaltungszustand Raum", "find_mapped_name"],
                    "dating_original" : [("Date inférieure pièce / frühestes Datum Raum", "Date supérieure pièce / spätestes Datum"), "handle_unformated_date"],
                    "dating_start": ["Date inférieure pièce / frühestes Datum Raum", "handle_date"],
                    "dating_end": ["Date supérieure pièce / spätestes Datum", "handle_date"],
                    "dating_start_approx": ["Date inférieure pièce / frühestes Datum Raum", "handle_approx"],
                    "dating_end_approx": ["Date supérieure pièce / spätestes Datum", "handle_approx"],
                    "url_photo" : ["URL photo", "first_in_list"],
                },
                "lists" : {},
                "connections" : {
                    "room_person_join" : [["Personne"], "connection_type", "id_person", "persons"]
                },
                "auto_columns" : {
                    "source": "heurist"
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
                    "url_photo" : ["URL photo / URL Fotografie", "first_in_list"],
                    "signature" : "Inscription signature / Inschrift, Signatur",
                },
                "lists" : {
                    "plafond_iconclass_join": 
                        [("Centre Iconclass / Iconlass der Deckenmitte", "Côté Iconclass / Iconclass der Seitenbereiche", "Iconclass sujet général / Iconclass, Allgemeines Sujet"), "iconclass_id", "iconclasses", "iconclass_id = %s", "create_iconclass"],
                },
                "connections" : {},
                "auto_columns" : {
                    "source": "heurist"
                }
            },
        }
        
        self.fk_mapping = {
            "id_room" : "Pièce",
            "id_building" : "Edifice / Bauwerk"
        }
        
        super().__init__(object_file, connection_file, basic_info, object_table_mapping)
       
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
        
        if (not start or re.match("[0-9]{4}\*?", start)) and (not end or re.match("[0-9]{4}\*?", end)):
            return ""
        
        if (start and not end) or start == end:
            return start
        elif end and not start:
            return end
        
        return start + " - " + end
        
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
                        "type" : row["connection"]
                    })
                    
                for ofield in row["fields"]:
                    if ofield in obj:
                        del obj[ofield]

        return (obj, pdata)
    
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
    
if __name__ == "__main__":
    importer = Heurist_Importer()
    importer.do_import() #only = "Plafond"
        