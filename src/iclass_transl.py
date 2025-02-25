from src.db_connection import conn_3310
import urllib.parse
import urllib.request
import json
import time

if __name__ == "__main__":
	conn = conn_3310()
	
	with conn.cursor() as cur:
		cur.execute("SELECT iconclass_id FROM iconclasses WHERE NOT tsearch")
		
		for row in cur.fetchall():
			icid = row[0]
			url = "https://iconclass.org/" + urllib.parse.quote(icid) + ".json"

			try:
				f = urllib.request.urlopen(url)
				json_str = f.read()
				data = json.loads(json_str)
				if data == None:
					raise Exception("Non-valid json: " + str(json_str) + " for iconclass " + icid)
				
				if not data:
					print("ID not valid: " + icid)
					continue


				name_de = ""
				name_fr = ""
				if "de" in data["txt"]:
					name_de = data["txt"]["de"]
				if "fr" in data["txt"]:
					name_fr = data["txt"]["fr"]
					
				sql = "UPDATE iconclasses SET tsearch = 1, description_de = %s, description_fr = %s WHERE iconclass_id = %s"
				cur.execute(sql, (name_de, name_fr, icid))
				conn.commit()
				
				print("Updated " + icid)
				time.sleep(5)
			except urllib.error.HTTPError as err:
				raise Exception(err)
		
		