import paramiko, MySQLdb, datetime, sys, storage_decrypt


def ipfetch():
    dbh = MySQLdb.connect(host='localhost',user='cmdb',passwd='Cmdb@2015',db='storapp')
    cursor = dbh.cursor()
    ip, arrays, dc = [], [], []
    cursor.execute("select distinct mgmt_ip,array,dc from storage where client='CONA' and (model = 'V7000' or model = 'V7000 Unified')");
    numrows = int(cursor.rowcount)
    for x in range(0,numrows):
        row = cursor.fetchone()
        ip.append(row[0])
        arrays.append(row[1])
        dc.append(row[2])
    cursor.close()
    return ip,arrays, dc


class v7000:
    def __init__(self, ip ,user, pwd, dc,device_name):
        self.date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.dbh = MySQLdb.connect(host='localhost', user='cmdb',passwd='Cmdb@2015', db='storapp')
        self.dc = dc
        self.device_name=device_name
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(ip, port=22, username=user, password=pwd)

    def cap_conv(self, cap):
        print cap
        if cap.endswith('TB'):
            cap = cap[:-2]
        elif cap.endswith('GB'):
            cap = float(cap[:-2])/1024
        elif cap.endswith('MB'):
            cap = float(cap[:-2])/(1024*1024)
        else:
            sys.exit("Capacity other than TB exists !! Program exits")
        return round(float(cap), 2)

    def unified_cap(self):
        print self.device_name
        service_ip ={'CPV7KU1FIL': '10.244.144.135',
                    'csv7ku1fclst1':'10.244.160.101'}
        user,password =storage_decrypt.decryption(service_ip[self.device_name]) 
        ssh=paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        ssh.connect(service_ip[self.device_name],port=1602,username=user,password=password)
        stdin,stdout, stderr=ssh.exec_command('df -h')
        data=stdout.readlines()
        total_used=0
        i=1
        ssh.close()
        while i<len(data):
            used=data[i].split()
            i+=1
            if len(used)<2:
                used=data[i].split()
                i+=1
                used=used[1]
            else:
                used=used[2]
            if used[-1] == 'G':
                total_used+= round(float(used[:-1])/1024,2)
            elif used[-1] == 'T':
                total_used+=round(float(used[:-1]),2)
            else:
                total_used+=0
        return total_used



    def lssystem(self):
        self.stdin, self.stdout, self.stderr = self.ssh.exec_command("lssystem -delim :")
        lssystem_out = self.stdout.readlines()
#        print self.stderr
        for line in lssystem_out:
#            print line
            #if "name:" in line:
             #   self.device_name =line.split(':')[1].strip()
            if "total_mdisk_capacity:" in line:
                total_mdiskcap = float(self.cap_conv(line.split(':')[1].strip()))
            elif "total_used_capacity:" in line:
                total_usedcap = float(self.cap_conv(line.split(':')[1].strip()))
                if self.device_name in ['CPV7KU1FIL','csv7ku1fclst1']:
                    total_usedcap=self.unified_cap()
            elif "total_vdisk_capacity:" in line:
                total_vdisk = float(self.cap_conv(line.split(':')[1].strip()))
            elif "total_free_space:" in line:
                total_freecap = float(self.cap_conv(line.split(':')[1].strip()))
        used_percent = round((total_usedcap/total_mdiskcap)*100, 2)
        allocated_percent = round((total_vdisk/total_mdiskcap) * 100, 2)
        print("System Details")
        print("="*20)
        print("Device Name: {0}\nTotal Mdisk Cap:{1}\nTotal Used Cap:{2}\nUsed(%):{3}\nTotal Vdisk Cap:{4}\nTotal allocated(%):{5}\nTotal Free Cap:{6}".format(self.device_name,total_mdiskcap,total_usedcap, total_vdisk, total_freecap, used_percent, allocated_percent))
        print("="*20)
        cursor = self.dbh.cursor()
        cursor.execute("REPLACE INTO v7000_systemcap (date,dc, device_name, total_mdiskcap, total_usedcap,used_percent, "
                       "total_vdisk,allocated_percent,total_freecap) VALUES('{0}','{1}','{2}','{3}','{4}','{5}',"
                       "'{6}','{7}','{8}')".format(
                self.date,self.dc, self.device_name, total_mdiskcap, total_usedcap,used_percent,total_vdisk,allocated_percent,total_freecap))
        self.dbh.commit()
        cursor.close()
        print("{0} system capacity details loaded into Database!!".format(self.device_name))


    def lsmdiskgrp(self):
       pool_name, capacity, used_cap, used_percent, virtual_cap, allocated_percent, free_cap = [], [], [],[],[],[],[]
       self.stdin, self.stdout, self.stderr = self.ssh.exec_command("lsmdiskgrp -delim :")
       lsmdiskgrp_out = self.stdout.readlines()
       for line in lsmdiskgrp_out:
           if "id" not in line:
               line = line.split(":")
               pool_name.append(line[1])
               capacity.append(self.cap_conv(line[5]))
               used_cap.append(self.cap_conv(line[9]))
               used_percent.append(round((self.cap_conv(line[9])/self.cap_conv(line[5]))*100,2))
               virtual_cap.append(self.cap_conv(line[8]))
               allocated_percent.append(round((self.cap_conv(line[8])/self.cap_conv(line[5]))*100,2))
               free_cap.append(self.cap_conv(line[7]))
       cursor = self.dbh.cursor()
       for pool, cap, used, prct_used, vir_cap, aloc_cap, fcap in zip(pool_name, capacity, used_cap, used_percent, virtual_cap,allocated_percent,free_cap):
           cursor.execute(
           "REPLACE INTO v7000_pool (date, device_name, pool_name,capacity, used_cap, used_percent, virtual_cap, allocated_percent,free_cap) VALUES('{0}','{1}','{2}','{3}','{4}','{5}',"
           "'{6}','{7}','{8}')".format(
               self.date, self.device_name,pool, cap, used, prct_used, vir_cap, aloc_cap, fcap ))
           self.dbh.commit()
       cursor.close()

    def ssh_close(self):
        self.ssh.close()


def main():
    V7000_ips, V7000_arrays, datacenter = ipfetch()
    print V7000_ips
    for ip, array, dc in zip (V7000_ips, V7000_arrays, datacenter):
        #if array != 'csev7kgen3':continue
        try:
                print array
	        user, pwd = storage_decrypt.decryption(ip)
        	dev1 = v7000(ip, user, pwd, dc,array)
	        dev1.lssystem()
	        dev1.lsmdiskgrp()
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
