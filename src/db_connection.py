import pymysql
import os

#A file "login" with the following structure is needed:
# first line: user
# second line: password

def get_login_data ():
    with open(os.path.dirname(os.path.realpath(__file__)) + "/login") as file:
        data = map(lambda x: x[:-1] if x[-1] == "\n" else x, file.readlines())
        return list(data)

def conn_3310 (db = "plafond", **user_data):

    ldata = get_login_data()
    
    if "user" in user_data:
        ldata[0] = user_data["user"]
        
    if "passwd" in user_data:
        ldata[1] = user_data["passwd"] 
    
    # host = "localhost"
    # port = 3311
    # ldata[0] = "root"
    # ldata[1] = ""
    
    host = "gwi-sql.gwi.uni-muenchen.de"
    port = 3309
    
    return pymysql.connect(host= host, port=port, db=db, user=ldata[0], passwd=ldata[1], charset='utf8', ssl={"stub": 0})
