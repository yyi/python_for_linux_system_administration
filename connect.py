#!/usr/bin/python
# connect.py: connect to the MySQL server

import mysql.connector
import sys

try:
    conn = mysql.connector.connect(database="mcb",
                                   host="master",
                                   user="mcb",
                                   password="mcb123")
    print (sys.path)
    print("Connected")
except:
    print("Cannot connect to server")
else:
    conn.close()
    print("Disconnected")

try:
#@ _FRAG_
  conn_params = {
    "database": "mcb",
    "host": "master",
    "user": "mcb",
    "password": "mcb123",
    "charset": "utf8",
  }
#@ _FRAG_
  conn = mysql.connector.connect(**conn_params)
  print("Connected")
  cursor = conn.cursor()
  cursor.execute('''
               INSERT INTO profile (name,birth,color,foods,cats)
               VALUES(%s,%s,%s,%s,%s)
               ''', ("De'Mont", "1973-01-12", None, None, 2))
  cursor.close()
  conn.commit()
  cursor = conn.cursor()
  cursor.execute("SELECT id, name, cats FROM profile WHERE cats = %s", (2,))
  for (id, name, cats) in cursor:
    print("id: %s, name: %s, cats: %s" % (id, name, cats))
  cursor.close()

  cursor = conn.cursor()
  cursor.execute("SELECT name, birth, foods FROM profile")
  for record in cursor:
    record = list(record)  # convert nonmutable tuple to mutable list
    for i, value in enumerate(record):
        if value is None:  # is the column value NULL?
            record[i] = "NULL"
    print("name: %s, birth: %s, foods: %s" % (record[0], record[1], record[2]))
  cursor.close()
except mysql.connector.errors as e:
  print("Cannot connect to server")
  print("Error code: %s" % e.errno)
  print("Error message: %s" % e.msg)
  print("Error SQLSTATE: %s" % e.sqlstate)
else:
  conn.close()
  print("Disconnected")
