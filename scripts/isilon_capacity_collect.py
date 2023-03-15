import paramiko, MySQLdb, datetime, sys, storage_decrypt,re


def ipfetch():
    dbh = MySQLdb.connect(host='localhost',user='cmdb',passwd='Cmdb@2015',db='storapp')
    cursor = dbh.cursor()
    ip, arrays, dc = [], [], []
    cursor.execute("select distinct mgmt_ip,array,dc from storage where client='CONA' and model = 'Isilon'")
    numrows = int(cursor.rowcount)
    for x in range(0,numrows):
        row = cursor.fetchone()
        ip.append(row[0])
        arrays.append(row[1])
        dc.append(row[2])
    cursor.close()
    return ip,arrays, dc


class Isilon:
    def __init__(self, ip ,user, pwd, dc,device_name):
        self.date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.dbh = MySQLdb.connect(host='localhost', user='cmdb',passwd='Cmdb@2015', db='storapp')
        self.dc = dc
        self.device_name=device_name
        self.allocated_capacity=0
        self.Total_capacity, self.Used_capacity=0,0
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(ip, port=22, username=user, password=pwd)

    def cap_conv(self, cap):
        if cap == '-':
            return 0
        elif cap.endswith('G'):
            cap = float(cap[:-1])/1024
        elif cap.endswith('T'):
            cap = float(cap[:-1])
        else:
            sys.exit("Capacity other than TB, GB exists !! Program exits")
        return round(float(cap), 2)
    
    def TotalCapacity(self):
        stdin,stdout,stderr=self.ssh.exec_command("isi status|grep -i size")
        capacity=stdout.readline()
        print "Total"
        capacity=re.findall('[\d.]+',capacity)[1]
        print capacity
        self.Total_Capacity=float(capacity)
    
    def UsedCapacity(self):
        stdin,stdout,stderr=self.ssh.exec_command("isi status|grep -i used")
        capacity=stdout.readline()
        print capacity
        capacity=re.findall('[\d.]+[GT]',capacity)[0]
        capacity=self.cap_conv(capacity)
        self.Used_Capacity=capacity        

    def AllocatedCapacity(self):
        stdin,stdout,stderr=self.ssh.exec_command("isi quota quotas list")
        data=stdout.readlines()
        data=data[2:-2]
        if not data:
            self.allocated_capacity=0
        allocated_Shares_Cap=[]
        for quota in data:
            share_cap=quota.split()[4]
            allocated_Shares_Cap.append(self.cap_conv(share_cap))

        self.allocated_capacity= sum(allocated_Shares_Cap)
        if self.device_name=='CSISICLST01':
            cursor=self.dbh.cursor()
            cursor.execute("SELECT total_vdisk from isilon_systemcap WHERE date='{}'"
                            "and device_name='CPISICLST01'".format(self.date))
            self.allocated_capacity=cursor.fetchone()[0]
    def update_db(self):
        cursor = self.dbh.cursor()
        cursor.execute("REPLACE INTO isilon_systemcap (date,dc, device_name, total_mdiskcap, total_usedcap,used_percent, "
                       "total_vdisk,allocated_percent,total_freecap) VALUES('{0}','{1}','{2}','{3}','{4}','{5}',"
                       "'{6}','{7}','{8}')".format(
                self.date,self.dc, self.device_name, self.Total_Capacity, self.Used_Capacity, round((self.Used_Capacity/self.Total_Capacity)*100,2),self.allocated_capacity,round((self.allocated_capacity/self.Total_Capacity)*100,2),self.Total_Capacity-self.Used_Capacity))
        self.dbh.commit()
        cursor.close()

    def ssh_close(self):
        self.ssh.close()


def main():
    Isilon_ips, Isilon_arrays, datacenter = ipfetch()
    
    for ip, array, dc in zip(Isilon_ips, Isilon_arrays, datacenter):
        try:
	    user, pwd = storage_decrypt.decryption(ip)
            dev = Isilon(ip, user, pwd, dc,array)
            print array
            print ip
	    dev.TotalCapacity()
            dev.AllocatedCapacity()
            dev.UsedCapacity()
            dev.update_db()
	    dev.ssh_close()
        except paramiko.ssh_exception.AuthenticationException as err:
            print((ip + str(err)))
            continue
        except Exception as err:
            print(ip+str(err))
            continue
if __name__ == '__main__':
    main()

