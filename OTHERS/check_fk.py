import pymysql
conn = pymysql.connect(host='localhost', user='root', password='', database='mtsms')
cur = conn.cursor()
cur.execute("SHOW CREATE TABLE school_fees")
for row in cur:
    print(row)
