import MySQLdb as db
conn = db.connect(host="localhost", db="mysql", user='root', passwd='yangyi', unix_socket='/var/run/mysqld/mysqld.sock')
cur = conn.cursor()
sql = "select 1"
cur.execute(sql)
rows =  cur.fetchall()
print rows
