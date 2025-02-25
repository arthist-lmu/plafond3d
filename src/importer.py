import json
import io
import abc
import re
from src.db_connection import conn_3310
import urllib.parse
import urllib.request
from memoization import cached
import requests

class NameMappingException(Exception):
    def __init__(self, name):
        super().__init__("Values missing in name mapping: " + name)

def not_inferred (func):
    def wrapper_fun (*args, **kwargs):
        return (func(*args, **kwargs), False)
    return wrapper_fun

class Importer:
    def __init__ (self, object_file, connection_file, basic_info, object_table_mapping):
        
        self.object_file = object_file
        self.connection_file = connection_file
        self.object_table_mapping = object_table_mapping
        
        self.dbname = basic_info["dbname"]
        self.id_field = basic_info["id_field"]
        self.type_field = basic_info["type_field"]
        self.conn_id1 =    basic_info["conn_id1"]
        self.conn_id2 =    basic_info["conn_id2"]
        self.conn_type_field = basic_info["conn_type_field"]
        self.conn_dir_field = basic_info["conn_dir_field"]
        
        self.connection_table_mapping = {}
        
        self.changes = {}
        self.changes_conns = {}
        self.conns = None
        self.type_mapping = {} #Maps import ids to object types
        self.id_mapping = {} #Maps import ids to data base ids
        self.type_count = {}
        self.ids_handled = {} #Stores the keys for every table that have been handled to delete entries that does not exist any more in the source data base
        self.statistics = {}
        
        self.cid = None
        
        self.cur = None
        
        self.wikidata_api_prefix = "https://query.wikidata.org/sparql?query="
        
    @abc.abstractmethod
    def data_function (self, data):
        pass
    
    @abc.abstractmethod
    def conn_function (self, conns):
        pass
    
    @abc.abstractmethod
    def get_conn_name_from_type (self, full_name):
        pass
        
    def do_import (self, only = None):
        self.conn = conn_3310()
    
        if type(self.object_file) is not list:
            self.object_file = [self.object_file]
            
        self.data = []
        for ofile in self.object_file:
            with open(ofile, encoding="utf8") as f:
                self.data += self.data_function(json.load(f))
    
        with open(self.connection_file, encoding="utf8") if self.connection_file else io.StringIO("{}") as cf:
            self.conns = self.conn_function(json.load(cf))
            
        self.cur = self.conn.cursor()

        sql = "SELECT `table`, `id`, `field`, `old`, `new` FROM plafond.changes WHERE source = '" + self.dbname + "'"
        self.cur.execute(sql)
        for row in self.cur.fetchall():
            if not row[0] in self.changes:
                self.changes[row[0]] = []
            self.changes[row[0]].append(row)
            
        sql = "SELECT type_in, type_out FROM plafond.changes_connections WHERE source = 'deckenmalerei'"
        self.cur.execute(sql)
        for row in self.cur.fetchall():
            self.changes_conns[row[0]] = row[1]

        for row in self.data:
            self.type_mapping[row[self.id_field]] = row[self.type_field]
            if not row[self.type_field] in self.type_count:
                self.type_count[row[self.type_field]] = 0
            self.type_count[row[self.type_field]] += 1

        #Update/insert data
        for object_type in self.object_table_mapping.keys():  
            print ("Handling " + object_type + "...")
            self.fill_id_mapping(object_type)
            cElements = self.type_count[object_type]
            
            if only != None and only != object_type:
                continue
            
            self.statistics[object_type] = {
                "rows" : 0,
                "rows_used" : 0,
                "fields" : {}
            }
            
            info = self.object_table_mapping[object_type]
            for db_field in info["import_columns"]:
                self.update_statistics (object_type, info["import_columns"][db_field], db_field)
            
            for join_table in info["lists"]:
                fields = info["lists"][join_table][0]
                if type(fields) != tuple:
                    fields = (fields,)
                
                for field in fields:
                    self.update_statistics (object_type, field, join_table)
            
            self.statistics[object_type]["fields"]["auto"] = {
                "db_fields": [],
                "count" : 0
            }
            
            for db_field in info["auto_columns"]:
                self.statistics[object_type]["fields"]["auto"]["db_fields"].append(db_field)

            num = 0
            
            for row in self.data:  
                if row[self.type_field] == object_type:
                    if num % 100 == 0:
                        print(str(num) + " / " + str(cElements))
                        
                    num += 1
                    self.statistics[object_type]["rows"] += 1

                    if self.handle_row(row):
                        self.conn.commit()
                        #exit()
                                 
        if only:
            print("Finished!")
            return
                                    
        #Check for removed entries
        for table in reversed(self.ids_handled.keys()):
            info = self.get_info_for_table(table)
            id_list = ",".join(map (str, self.ids_handled[table]))
            sql = "SELECT " + info["primary_key"] + " FROM " + table + " WHERE source = '" + self.dbname + "' AND " + info["primary_key"] + " NOT IN (" + id_list + ")"
            self.cur.execute(sql)
            
            dids = self.cur.fetchall()
            if (len(dids) > 0):
                print("Deleting " + str(len(dids)) + " rows from table " + table)
                sql = "DELETE FROM plafond.`" + table + "` WHERE " + info["primary_key"] + " IN (" + ",".join(map (lambda x: str(x[0]), dids)) + ")"
                print(sql)
                self.cur.execute(sql)
                self.conn.commit()
              
        print("Create statistics ...")
                
        sql = "DELETE FROM plafond.import_statistics WHERE source = %s"
        params = (self.dbname,)
        
        if only != None:
            sql += " AND table_name = %s"
            params += (self.object_table_mapping[only]["name"],)
            
        self.cur.execute(sql, params)
        
        sql = "INSERT INTO plafond.import_statistics (source, table_name, original_name, db_field, count_original) VALUES (%s, %s, %s, %s, %s)"

        stat_data = []
        for object_type in self.statistics:
            for field, field_data in self.statistics[object_type]["fields"].items():
                if len(field_data["db_fields"]) == 0:
                    stat_data.append((self.dbname, self.object_table_mapping[object_type]["name"], field, None, str(field_data["count"])))
                else:
                    for dbfield in field_data["db_fields"]:
                        stat_data.append((self.dbname, self.object_table_mapping[object_type]["name"], field, dbfield, str(field_data["count"])))
        self.cur.executemany(sql, stat_data)
        self.conn.commit()
        
        print("Finished!")
        
    def check_url (self, url):
        try:
            get = requests.head(url, allow_redirects=True)
            
            if get.status_code != 404:
                return True
            
            return False
        except Exception:
            return False
                            
    def handle_row (self, row):
        info = self.object_table_mapping[row[self.type_field]]
        
        self.cid = row[self.id_field]
        otype = self.type_mapping[self.cid]
        for field in row:
            if field not in self.statistics[otype]["fields"]:
                self.statistics[otype]["fields"][field] = {
                    "db_fields": [],
                    "count" : 0
                }
            
            self.statistics[otype]["fields"][field]["count"] += 1
                
        
        if "condition" in info:
            fun = getattr(self, info["condition"])
            if not fun(row):
                return False
            
        self.statistics[otype]["rows_used"] += 1
        
        fields = [info["primary_key"]] + list(info["import_columns"].keys()) + list(info["auto_columns"].keys())
        sql = "SELECT " + ",".join(map(lambda x: "`" + x + "`", fields)) + " FROM plafond.`" + info["name"] + "` WHERE source='" + self.dbname + "' AND source_id = %s"
        self.cur.execute(sql, self.cid)
        old_data = self.cur.fetchone()
        
        if (old_data):
            return self.update_fields(row, info, old_data)
        else:
            self.create_new_entry(row, info)
            
        return True
    
    def to_int (self, s, dbname, table, field):
        if s == None:
            return None
        
        return int(s)
    
    @not_inferred
    def to_str (self, s, dbname, table, field):
        if s == None:
            return None
        
        return str(s)
    
    def create_building_function (self, name, dbname):
        if name == None:
            raise NameMappingException("None") 
        
        sql = "INSERT IGNORE INTO building_functions (name_e) VALUES (%s)"
        self.cur.execute(sql, name)
        self.conn.commit()
        
        return self.cur.lastrowid
    
    def create_room_function (self, name, dbname):
        if name == None:
            raise NameMappingException("None") 
        
        sql = "INSERT IGNORE INTO room_functions (name_e) VALUES (%s)"
        self.cur.execute(sql, name)
        self.conn.commit()
        
        return self.cur.lastrowid
                
    
    def create_iconclass (self, val, dbname):
        url = "https://iconclass.org/" + urllib.parse.quote(val) + ".json"
        
        try:
            f = urllib.request.urlopen(url)
            json_str = f.read()
            data = json.loads(json_str)
            sql = "INSERT INTO plafond.iconclasses (iconclass_id, description, iconclass_id_0, iconclass_id_1, iconclass_id_2, description_de, description_fr) VALUES (%s, %s, %s, %s, %s, %s, %s)"
            if data == None:
                raise Exception("Non-valid json: " + str(json_str) + " for iconclass " + val)

            id_0 = data["p"][0]
            id_1 = data["p"][1] if 1 in data["p"] else id_0
            id_2 = data["p"][2] if 2 in data["p"] else id_1
            
            descr_en = data["txt"]["en"]
            descr_de = data["txt"]["de"] if "de" in data["txt"] else ""
            descr_fr = data["txt"]["fr"] if "fr" in data["txt"] else ""
            
            self.cur.execute(sql, [val, descr_en, id_0, id_1, id_2, descr_de, descr_fr])
            
            return val
        except urllib.error.HTTPError as err:
            raise Exception(err)
        
    def combine_lists_to_single_fields (self, params, dbname, table, field):
        name_mapping = self.get_type_name_mapping(dbname, table, field)
        
        res = ""
        for key, slist in params.items():
            if slist != None and len(slist) > 0:
                if res != "":
                    res += ";"
                res += key + ":" + "+".join(slist)
                
        if res == "":
            res = "NONE"
            
        if not self.check_in_name_mapping(res, name_mapping, table, field):
            return None
        
        mapped_name = name_mapping[res]
        
        if mapped_name == "NONE":
            return None
        
        return mapped_name
        
        
    def combine_to_single_field (self, params, dbname, table, field):
        name_mapping = self.get_type_name_mapping(dbname, table, field)
        
        if params == None:
            key = "NONE"
        else:
            key = "+".join([key for key, val in params.items() if val])

        if not self.check_in_name_mapping(key, name_mapping, table, field):
            return None

        mapped_name = name_mapping[key]
        
        if mapped_name == "NONE":
            return None
        
        return mapped_name
    
    def check_in_name_mapping (self, key, name_mapping, table, field):
        if key not in name_mapping or not name_mapping[key]:
            if key not in name_mapping:
                sql = "INSERT IGNORE INTO plafond.name_mapping (`source`, `table`, `field`, `input`, `output`) VALUES (%s, %s, %s, %s, '')"
                self.cur.execute(sql, (self.dbname, table, field, key))
                self.conn.commit()
                           
            print("Value \"" + key + "\" for id " + self.cid + " not found in name mapping for source \"" + self.dbname + "\",  table \"" + table + "\",  field \"" + field + "\"")
            return False
        
        return True
    
    @not_inferred
    def none_to_empty (self, s, dbname, table, field):
        if s == None:
            return ""
        return str(s)
    
    @not_inferred
    def append_elements (self, s, dbname, table, field):
        if s == None:
            return None
        
        return ",".join(s)
    
    def sparql_wikidata (self, query):
        return None #TODO!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
        url = self.wikidata_api_prefix + urllib.parse.quote(query) + "&format=json"
        
        try:
            f = urllib.request.urlopen(url)
            jsonstring = f.read()
            return json.loads(jsonstring)
        except urllib.error.HTTPError as err:
            print(err)
            
    @cached 
    def get_type_name_mapping (self, dbname, table, field):
        sql = "SELECT input, output FROM name_mapping WHERE `source` = '" + dbname + "' AND `table` = '" + table + "' and `field` = '" + field + "'"
        self.cur.execute(sql)
        
        ret = {}
        for row in self.cur.fetchall():
            ret[row[0]] = row[1]
            
        return ret
    
    @not_inferred
    def first_in_list (self, val, dbname, table, field):
        if val is None:
            return None
        
        return val[0]
    
    @not_inferred
    def find_mapped_name (self, val, dbname, table, field):
        
        if type(val) == list:
            val = "+".join(val)
        
        if val == None:
            return None
        
        name_mapping = self.get_type_name_mapping(dbname, table, field)
        
        if not self.check_in_name_mapping(val, name_mapping, table, field):
            return None
        
        mapped_name = name_mapping[val]
        
        if mapped_name == "NONE":
            return None
        
        return mapped_name
    
    def get_field_data (self, row, dbfield, field_info, entry_id, info):
        table = info["name"]

        if type(field_info) == list:
            fun = getattr(self, field_info[1])
            if field_info[0] == "FK":
                #TODO changes?
                arg = entry_id
                object_id = fun(arg, self.dbname, table, dbfield)
                if object_id == None:
                    return (None, False)
                return (self.id_mapping[self.type_mapping[object_id]][object_id], False)
            elif type(field_info[0]) == tuple:
                args = {x: (self.base_value_or_changed(table, row, x, info) if x in row else None) for x in field_info[0]}
                #TODO strip?
                
                ret_val = fun(args, self.dbname, table, dbfield)
                return self.ret_fun_result(ret_val)
            elif field_info[0] in row:
                arg = self.base_value_or_changed(table, row, field_info[0], info)
                if isinstance(arg, str):
                    arg = arg.strip()
                    
                ret_val = fun(arg, self.dbname, table, dbfield)
                return self.ret_fun_result(ret_val)
            
            ret_val = fun(None, self.dbname, table, dbfield)
            return self.ret_fun_result(ret_val)
        else:
            if field_info in row:
                ret = self.base_value_or_changed(table, row, field_info, info)
                
                if isinstance(ret, str):
                    ret = ret.strip()
                return (ret, False)
            return (None, False)
        
    def ret_fun_result (self, result):
        if type(result) == tuple:
            return result
        
        return (result, True)
        
    def find_change (self, val, table, row, field_name, process_fun):
        if table in self.changes:
            for change in self.changes[table]:
                if row[self.id_field] == change[1] and field_name == change[2]:
                    if process_fun(change[3]) != val:
                        print("Change original value does not exist anymore. New value: " + json.dumps(row[field_name]) + ", change data: " + str(change))
                        break
                    return process_fun(change[4])
                
        return val
        
    def base_value_or_changed (self, table, row, field_name, info):
        return self.find_change(row[field_name], table, row, field_name, lambda x: x)
    
    def get_list_data (self, info, row, field_name):
        if field_name not in row:
            return []
        
        val = row[field_name]
        
        if type(val) != list:
            val = [val]

        table = info["name"]

        return self.find_change(val, table, row, field_name, lambda x: self.load_json(x))
    
    def load_json (self, x):
        try:
            return json.loads(x)
        except Exception as e:
            print("JSON string not valid: " + x)
            return []
    
    def find_connections_with_types (self, eid, element_types, source, table, field):
        conns = self.get_connections(eid)
        ret = []
        
        tname_mapping = self.get_type_name_mapping(source, table, field)
        
        for conn in conns:
            curr_type = self.type_mapping[conn[self.conn_id2]]
            
            if curr_type in element_types:
                conn_type_orig = conn[self.conn_type_field]
                
                if conn_type_orig in self.changes_conns:
                    conn_type_orig = self.changes_conns[conn_type_orig]
                    if conn_type_orig == None:
                        continue
                
                conn_name = self.get_conn_name_from_type(conn_type_orig)
                
                if not self.check_in_name_mapping(conn_name, tname_mapping, table, field) or tname_mapping[conn_name] == "NONE":
                    continue

                ret.append((conn[self.conn_id2], tname_mapping[conn_name], conn_type_orig))
        
        return ret
    
    def get_connections (self, eid, direction = None):
        res = []
        for conn in self.conns:
            if conn[self.conn_id1] == eid and (direction == None or direction == conn[self.conn_dir_field]):
                res.append(conn)
            elif conn[self.conn_id2] == eid and (direction == None or direction != conn[self.conn_dir_field]):
                revConn = {}
                revConn[self.conn_id1] = conn[self.conn_id2]
                revConn[self.conn_id2] = conn[self.conn_id1]
                revConn[self.conn_type_field] = conn[self.conn_type_field]
                revConn[self.conn_dir_field] = not conn[self.conn_dir_field]
                res.append(revConn)
        return res

    
    def id_handled (self, table, idx):
        if table not in self.ids_handled:
            self.ids_handled[table] = []
            
        self.ids_handled[table].append(idx)
    
    def update_fields (self, row, info, old_data):
        
        self.id_handled(info["name"], old_data[0])
        
        entry_id = row[self.id_field]
    
        updates = []
        values = []
        all_values = []
        
        for i, db_field in enumerate(info["import_columns"]):
            
            key_import = info["import_columns"][db_field]
            old_val = old_data[i+1]
            (new_val, inferred) = self.get_field_data(row, db_field, key_import, entry_id, info)
        
            if (not old_val and new_val) or (not inferred and new_val != old_val):
                print(old_val)
                print(new_val)
                updates.append("`" + db_field + "` = %s")
                values.append(new_val)
                all_values.append(new_val)
            elif new_val and old_val and new_val != old_val:
                raise Exception("Different value in database for inferred value: " + info["name"] + " " + str(old_data[0]) 
                                + " field '" + db_field + "': Old value = '" + str(old_val) + "', new value = '" + str(new_val) + "'")
            else:
                all_values.append(old_val)
                
        columns = list(info["import_columns"].keys()) + list(info["auto_columns"].keys())
        avals = self.get_auto_values(info, columns, all_values)
        for i, aval_key in enumerate(info["auto_columns"].keys()):
            new_aval = avals[i]
            old_aval = old_data[len(info["import_columns"]) + 1 + i]
            
            if new_aval != old_aval:
                updates.append("`" + aval_key + "` = %s")
                values.append(new_aval)
            all_values.append(new_aval)

        changed = False    
        if len(updates) > 0:
            print(old_data)
            sql = "UPDATE plafond.`" + info["name"] + "` SET " + ",".join(updates) + " WHERE " + info["primary_key"] + "=" + str(old_data[0])
            print(sql, values)
            self.cur.execute(sql, values)
            changed = True
        
        changed = changed or self.handle_lists(info, old_data, row, entry_id)
        changed = changed or self.handle_connections(info, old_data, entry_id)
                
        return changed
    
    def handle_lists (self, info, old_data, row, entry_id):
        changed = False
        
        for join_table in info["lists"]:
            (names_export, key_ref_table, ref_table, (where_field, use_name_mapping), new_element_fun, col_orig) = info['lists'][join_table]
            
            if type(names_export) != tuple:
                names_export = (names_export,)
    
            sql = "SELECT " + key_ref_table + " FROM plafond.`" + join_table + "` WHERE " + info["primary_key"] + " = " + str(old_data[0])
            self.cur.execute(sql)
            existing_ids = list(map(lambda x: x[0], self.cur.fetchall()))
            
            new_ids = []
            id_name_map = {}
            for name_export in names_export:
                list_data = self.get_list_data(info, row, name_export)
                invalid_elements = []
                for li in list_data:
                    if use_name_mapping:
                        (name, _) = self.find_mapped_name(li, self.dbname, ref_table, where_field)
                    else:
                        name = li
                        
                    if name == None:
                        sub_res = None
                    else:
                        sql = "SELECT " + key_ref_table + " FROM plafond.`" + ref_table + "` WHERE " + where_field + " = %s"
                        self.cur.execute(sql, (name))
                        sub_res = self.cur.fetchone()
                    
                    if sub_res == None:
                        if new_element_fun:
                            try:
                                id_created = getattr(self, new_element_fun)(name, self.dbname)
                                new_ids.append(id_created)
                                id_name_map[id_created] = li
                            except Exception as e:

                                if not isinstance(e, NameMappingException):
                                    print(e)
                                    invalid_elements.append(li)
                                #print("\nNew entry could not be created in table '" + ref_table + "' for value '" + li + "' for row\n" + str(row) + ":\n" + str(e) + "\n")
                                
                        else:
                            raise Exception("Field '" + name_export + "' with value '" + li + "' not found.")
                    else:
                        new_ids.append(sub_res[0])
                        id_name_map[sub_res[0]] = li
                        
                if len(invalid_elements) > 0:
                    try:
                        sql = "INSERT INTO plafond.changes VALUES (%s,%s,%s,%s,%s,%s)"
                        json_valid = json.dumps(list(filter(lambda x: x not in invalid_elements, list_data)))
                        
                        oval = row[name_export]
                        if type(oval) != list:
                            oval = [oval]
                            
                        self.cur.execute(sql, (self.dbname, info["name"], entry_id, name_export, json.dumps(oval), "AUTO:" + json_valid))
                        self.conn.commit()
                    except Exception as e:
                        print("Values from changes still not working for " + entry_id + ", field '" + name_export + "'. Invalid elements: " + str(invalid_elements))
                    
            for eid in existing_ids:
                if eid not in new_ids:
                    print("Remove list connection: " + str(eid))
                    sql = "DELETE FROM plafond.`" + join_table + "` WHERE " + info["primary_key"] + " = %s AND " + key_ref_table + " = %s"
                    self.cur.execute(sql, (old_data[0], eid))
                    changed = True
               
            for nid in new_ids:
                if nid not in existing_ids:
                    print("Add list connection: " + str((old_data[0], nid)))
                    if col_orig:
                        sql = "INSERT INTO plafond.`" + join_table + "` (" + info["primary_key"] + ", " + key_ref_table + ", " + col_orig + ") VALUES (%s, %s, %s)"
                        self.cur.execute(sql, (old_data[0], nid, id_name_map[nid]))
                    else:
                        sql = "INSERT INTO plafond.`" + join_table + "` (" + info["primary_key"] + ", " + key_ref_table + ") VALUES (%s, %s)"
                        self.cur.execute(sql, (old_data[0], nid))
                    changed = True
                    existing_ids.append(nid)
                    
        return changed
    
    def handle_connections (self, info, old_data, entry_id):
        changed = False
        
        for join_table in info["connections"]:
            (element_types, type_field, key_ref_table, ref_table, orig_col) = info["connections"][join_table]
    
            sql = "SELECT " + key_ref_table + ", " + type_field + " FROM plafond.`" + join_table + "` WHERE " + info["primary_key"] + " = " + str(old_data[0])
            self.cur.execute(sql)
            existing_conns = list(self.cur.fetchall())
            
            new_conns = []
            new_conns_origs = {}
            
            for (export_id, db_type_val, conn_type_orig) in self.find_connections_with_types(entry_id, element_types, self.dbname, join_table, type_field):
                sql = "SELECT " + key_ref_table + " FROM plafond.`" + ref_table + "` WHERE source_id = %s" 
                self.cur.execute(sql, (export_id))
                sub_res = self.cur.fetchone()
                
                if sub_res == None:
                    raise Exception("Field '" + type_field + "' with value '" + export_id + "' not found.")
                
                new_conns.append((sub_res[0], db_type_val))
                if orig_col:
                    if not (sub_res[0], db_type_val) in new_conns_origs:
                        new_conns_origs[(sub_res[0], db_type_val)] = []
                    if not conn_type_orig in new_conns_origs[(sub_res[0], db_type_val)]:
                        new_conns_origs[(sub_res[0], db_type_val)].append(conn_type_orig)
                
            new_conns = list(set(new_conns)) #only unique rows if multiple types are mapped to the same value
            
            for (eid, etype) in existing_conns:
                if (eid, etype) not in new_conns:
                    print("Remove connection from " + join_table + ": " + str(old_data[0]) + " - " + str(eid))
                    sql = "DELETE FROM plafond.`" + join_table + "` WHERE " + info["primary_key"] + " = %s AND " + key_ref_table + " = %s"
                    self.cur.execute(sql, (old_data[0], eid))
                    changed = True
            
            for (nid, ntype) in new_conns:
                if (nid, ntype) not in existing_conns:
                    print("Add connection: " + str((old_data[0], nid, ntype)))
                    if orig_col:
                        sql = "INSERT INTO plafond.`" + join_table + "` (" + info["primary_key"] + ", " + key_ref_table + ", " + type_field + ", " + orig_col + ") VALUES (%s, %s, %s, %s)"
                        self.cur.execute(sql, (old_data[0], nid, ntype, "+".join(new_conns_origs[(nid, ntype)])))
                    else:
                        sql = "INSERT INTO plafond.`" + join_table + "` (" + info["primary_key"] + ", " + key_ref_table + ", " + type_field + ") VALUES (%s, %s, %s)"
                        self.cur.execute(sql, (old_data[0], nid, ntype))
                    existing_conns.append((nid, ntype))
                    changed = True
                    
        return changed
    
    def create_new_entry (self, row, info):
        eid = row[self.id_field]
        
        import_keys = info["import_columns"].keys()
        columns = list(import_keys) + list(info["auto_columns"].keys())
        used_fields = []
        
        for ikey in import_keys:
            key_import = info["import_columns"][ikey]
            (new_val, _) = self.get_field_data(row, ikey, key_import, eid, info)
            used_fields.append(new_val)
            
        #TODO lists, connections
    
        sql = "INSERT INTO " + info["name"] + " (source_id," + ",".join(map(lambda x: "`" + x + "`", columns)) + ") VALUES(%s" + (",%s" * len(columns)) + ")"
        fields = [eid] + used_fields + self.get_auto_values(info, columns, used_fields)
        print(fields)
        
        self.cur.execute(sql, fields)
        new_id = self.cur.lastrowid
        self.id_mapping[row[self.type_field]][eid] = new_id
        self.id_handled(info["name"], new_id)
        
    def get_auto_values (self, info, columns, values):
        res = []
        
        for val in info["auto_columns"].values():
            if val[0] == "CONST":
                res.append(val[1])
            elif val[0] == "FUNC":
                fun = getattr(self, val[1])
                data = dict(zip(columns, values))
                res.append(fun(data))
            else:
                raise Exception("Invalid auto column type: " + val[0])
        
        return res
        
        
    def update_statistics (self, otype, key_import, db_field):
        if type(key_import) == list:
            ifields = [key_import[0]] if type(key_import[0]) == str else key_import[0]
        else:
            ifields = [key_import]
            
        for ifield in ifields:
            if not ifield in self.statistics[otype]["fields"]:
                self.statistics[otype]["fields"][ifield] = {
                    "db_fields": [],
                    "count" : 0
                }
            
            if db_field not in self.statistics[otype]["fields"][ifield]["db_fields"]:
                self.statistics[otype]["fields"][ifield]["db_fields"].append(db_field)

    def fill_id_mapping (self, type_name):
        self.id_mapping[type_name] = {}
        
        info = self.object_table_mapping[type_name]
        sql = "SELECT " + info["primary_key"] + ", source_id FROM plafond.`" + info["name"] + "` WHERE source = '" + self.dbname + "'"
        self.cur.execute(sql)
        
        
        for (eid, did) in self.cur.fetchall():
            self.id_mapping[type_name][did] = eid
            
    def get_info_for_table (self, table):
        for ename in self.object_table_mapping:
            if self.object_table_mapping[ename]["name"] == table:
                return self.object_table_mapping[ename]
        
    @not_inferred
    def get_first_name (self, full_name, dbname, table, field):
        return self.handle_name(full_name, dbname, table, field)[0]

    @not_inferred
    def get_last_name (self, full_name, dbname, table, field):
        return self.handle_name(full_name, dbname, table, field)[1]

    @cached
    def handle_name (self, full_name, dbname, table, field):
        if full_name == None:
            return (None,None)
        
        matchObject = re.match("^([^,]+), ([^,]+)$", full_name)
        if matchObject:
            return (matchObject[2], matchObject[1])
        
        return (None,None)
    
    def get_id_person_unique (self, data):
        
        qidFound = False
        res = None
        if data["wikidata_id"]:
            sql = "SELECT id_person_unique FROM a_persons_unique WHERE wikidata_id = %s"
            self.cur.execute(sql, data["wikidata_id"])
            
            res = self.cur.fetchone()
        
        if res == None:
            sql = "SELECT id_person_unique FROM a_persons_unique WHERE full_name = %s"
            self.cur.execute(sql, data["full_name"])
            
            res = self.cur.fetchone()
        else:
            qidFound = True
            
        if res == None:
            sql = "INSERT INTO a_persons_unique (full_name, first_name, last_name, wikidata_id) VALUES (%s, %s, %s, %s)"
            self.cur.execute(sql, (data["full_name"], data["first_name"], data["last_name"], data["wikidata_id"]))
            self.conn.commit()
            return self.cur.lastrowid
        else:
            if not qidFound:
                sql = "UPDATE a_persons_unique SET wikidata_id = %s WHERE id_person_unique = %s"
                self.cur.execute(sql, (data["wikidata_id"], res[0]))
            self.conn.commit()
            return res[0]

