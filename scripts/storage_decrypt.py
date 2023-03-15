from Crypto.Cipher import AES
import base64
import os
import MySQLdb
import sys
def decryption(ip):
        try:
                dbh = MySQLdb.connect(host='localhost',user='cmdb',passwd='Cmdb@2015',db='storapp')
                cursor=dbh.cursor()
                cursor.execute("SELECT user,pass from storage where mgmt_ip = (%s)",ip );
                numrows = int(cursor.rowcount)
                row = cursor.fetchone()
                (user,password) = row
                dbh.commit()
                dbh.close()
                PADDING = '{'
                DecodeAES = lambda c, e: c.decrypt(base64.b64decode(e)).rstrip(PADDING)
                encryption = password
                key = 'T!gErTe@m$2017@B'
                cipher = AES.new(key)
                decoded = DecodeAES(cipher, encryption)
	        print user,decoded
                return user ,decoded
        except Exception as err:
                print("Encryption" +str(err))
#ip=sys.argv[1]
#decryption(ip)
