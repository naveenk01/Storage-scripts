import datetime, MySQLdb, paramiko,storage_decrypt

def ipfetch():
    dbh = MySQLdb.connect(host='localhost',user='cmdb',passwd='Cmdb@2015',db='storapp')
    cursor = dbh.cursor()
    ip, arrays, dc = [], [], []
    cursor.execute("select distinct mgmt_ip,array,dc from storage where client='CONA' and (model = 'V7000' or model= 'V7000 Unified')");
    numrows = int(cursor.rowcount)
    for x in range(0,numrows):
        row = cursor.fetchone()
        ip.append(row[0])
        arrays.append(row[1])
        dc.append(row[2])
    cursor.close()
    return ip,arrays, dc

class V7000:

    def __init__(self, ip, user, pwd, device, dc):
        self.date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.dbh = MySQLdb.connect(host='localhost', user='cmdb', passwd='Cmdb@2015',db='storapp')
        self.device_name = device
        self.dc = dc
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(ip, port=22, username=user, password=pwd)

    def performance(self):
        self.stdin, self.stdout, self.stderr = self.ssh.exec_command("lssystemstats")
        lssystem_stats = self.stdout.readlines()
        for line in lssystem_stats:
            if "stat_name" not  in line:
                if "vdisk_mb" in line:
                    throughput = line.split()[1]
                    print("Throughput = {0}".format(line.split()[1]))
                elif "vdisk_io" in line:
                    iops = line.split()[1]
                    print("IOPS = {0}".format(line.split()[1]))
                elif "vdisk_r_ms" in line:
                    read_latency = line.split()[1]
                    print("Read Latency = {0}".format(line.split()[1]))
                elif "vdisk_w_ms" in line:
                    write_latency = line.split()[1]
                    print("Write Latency = {0}".format(line.split()[1]))
        cursor = self.dbh.cursor()
        cursor.execute(
            "REPLACE INTO v7000_perf (date, dc, device_name, throughput, iops,read_latency, "
            "write_latency) VALUES('{0}','{1}','{2}','{3}','{4}','{5}',"'{6}'
            ")".format(
                self.date, self.dc, self.device_name, throughput, iops, read_latency, write_latency))
        self.dbh.commit()
        cursor.close()
        print("{0} system Performance details loaded into Database!!".format(self.device_name))
    def ssh_close(self):
        self.ssh.close() 


def main():
    V7000_ips, V7000_arrays, datacenter = ipfetch()
    for ip, array, dc in zip (V7000_ips, V7000_arrays, datacenter):
#        print ip
	try:
	        user, pwd = storage_decrypt.decryption(ip)
        	dev1 = V7000(ip, user, pwd,array, dc)
	        dev1.performance()
	        dev1.ssh_close()
	except paramiko.ssh_exception.AuthenticationException as err:
       # except Exception as err:
            print((ip + str(err)))
            continue
        except Exception as err:
	    print(ip+str(err))
            continue

if __name__ == '__main__':
	main()