import MySQLdb, datetime, subprocess, storage_decrypt


def ipfetch():
    dbh = MySQLdb.connect(host='localhost', user='cmdb', passwd='Cmdb@2015', db='storapp')
    cursor = dbh.cursor()
    ip, arrays, dc = [], [], []
    cursor.execute(
        "select distinct mgmt_ip,array,dc from storage where client='CONA' and (model = 'XIV' or model= 'XIV-G3')");
    numrows = int(cursor.rowcount)
    for x in range(0, numrows):
        row = cursor.fetchone()
        ip.append(row[0])
        arrays.append(row[1])
        dc.append(row[2])
    cursor.close()
    return ip, arrays, dc


class xiv():
    def __init__(self, xiv_ip, xiv_user, xiv_pwd, device_name, dc):
        self.dividend = 1000
        self.xiv_ip, self.xiv_user, self.xiv_pwd = xiv_ip, xiv_user, xiv_pwd
        self.device_name = device_name
        self.dc = dc
        self.date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.dbh = MySQLdb.connect(host='localhost', user='cmdb', passwd='Cmdb@2015', db='storapp')
        self.total_soft_used, self.total_hard_used = 0, 0

    def xiv_pool(self):
        pool_name, soft_size, snap_size, soft_used, soft_used_percent, soft_available, hard_size, hard_vols, hard_snaps, vol_used_percent, hard_used, hard_used_percent, hard_available,pools_hard = [], [], [], [], [], [], [], [], [], [], [], [], [],[]
        out = subprocess.Popen(
            ['/root/IBM_Storage_Extended_CLI/xcli', '-m', self.xiv_ip, '-u', self.xiv_user, '-p', self.xiv_pwd,
             'pool_list'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in out.stdout:
            # print(line)
            if "Name" not in line:
                line = line.split()
                pool_name.append(line[0])
		#print self.xiv_ip
                soft_size_cap = round(float(line[1]) / self.dividend, 2)
                snap_size_cap = round(float(line[3]) / self.dividend, 2)
                pool_hard = round(float(line[3]) / self.dividend, 2)
                soft_used_cap = round((float(line[3]) + float(line[2])) / self.dividend, 2)
                hard_vols_cap = round(float(line[6]) / self.dividend, 2)
                hard_size_cap = round(float(line[5]) / self.dividend, 2)
                hard_snaps_cap = round(float(line[8]) / self.dividend, 2)
                hard_used_cap = hard_vols_cap + hard_snaps_cap

                soft_size.append(soft_size_cap)
                snap_size.append(snap_size_cap)
                soft_used.append(soft_used_cap)
                pools_hard.append(pool_hard)
                soft_used_percent.append(round((soft_used_cap / soft_size_cap) * 100, 2))
                soft_available.append(round(float(line[4]) / self.dividend, 2))
                hard_size.append(hard_size_cap)
                hard_vols.append(hard_vols_cap)
                hard_snaps.append(hard_snaps_cap)
                vol_used_percent.append(round(hard_vols_cap / (hard_size_cap - snap_size_cap) * 100, 2))
                hard_used.append(hard_used_cap)
                hard_used_percent.append(round((hard_used_cap / hard_size_cap) * 100, 2))
                hard_available.append(round(hard_size_cap - hard_used_cap, 2))
        self.total_hard_used = round(sum(hard_used), 2)
        self.total_soft_used = round(sum(soft_used), 2)
        cursor = self.dbh.cursor()
        print(pools_hard)
        for val in range(len(pool_name)):
            print(pool_name[val])
            cursor.execute(
                "REPLACE INTO xiv_pool (date,device_name,pool_name, soft_size, snap_size, soft_used, "
                "soft_used_percent, soft_available, hard_size, hard_vols,hard_snaps,vol_used_percent,hard_used,"
                "hard_used_percent,hard_available) VALUES('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}','{8}',"
                "'{9}','{10}','{11}','{12}','{13}','{14}')".format(
                    self.date, self.device_name, pool_name[val], soft_size[val], snap_size[val], soft_used[val],
                    soft_used_percent[val], soft_available[val], hard_size[val], hard_vols[val], hard_snaps[val],
                    vol_used_percent[val], hard_used[val], hard_used_percent[val], hard_available[val]))
            self.dbh.commit()
        cursor.close()

    def xiv_system_cap(self):
        out = subprocess.Popen(
            ['/root/IBM_Storage_Extended_CLI/xcli', '-m', self.xiv_ip, '-u', self.xiv_user, '-p', self.xiv_pwd,
             'system_capacity_list'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        for line in out.stdout:
#            print(line)
            if "Soft" not in line:
                line = line.split()
                soft_size = float(line[0].strip()) / 1000
                hard_size = float(line[1].strip()) / 1000
        # self.total_hard_used
        # self.total_soft_used
        hardused_percent = round((self.total_hard_used / hard_size) * 100, 2)
        softused_percent = round((self.total_soft_used / soft_size) * 100, 2)
        hard_available = round((hard_size - self.total_hard_used), 2)
        soft_available = round((soft_size - self.total_soft_used), 2)
        allocated_percent = round((self.total_soft_used / hard_size), 2) * 100
        perf_resv = round(((hard_size / 100) * 10), 2)
        available_space = soft_available - perf_resv
        cursor = self.dbh.cursor()
        cursor.execute(
            "REPLACE INTO xiv_syscap (date, dc, device_name, hard_size,hard_used,hard_used_percent,"
            "hard_available, soft_size, soft_used, soft_used_percent, soft_available,allocated_percent,perf_resv,"
            "available_space) VALUES('{0}','{1}','{2}','{3}','{4}','{5}','{6}','{7}','{8}','{9}','{10}','{11}',"
            "'{12}','{13}')".format(
                self.date, self.dc, self.device_name, hard_size, self.total_hard_used, hardused_percent, hard_available,
                soft_size, self.total_soft_used, softused_percent, soft_available, allocated_percent, perf_resv,
                available_space))
        self.dbh.commit()
        cursor.close()


def main():
    xiv_ips, xiv_arrays, datacenter = ipfetch()
    for ip, array, dc in zip(xiv_ips, xiv_arrays, datacenter):
        try:
	        user, pwd = storage_decrypt.decryption(ip)
        	xiv1 = xiv(ip, user, pwd, array, dc)
	        xiv1.xiv_pool()
                print "done pool" 
        	xiv1.xiv_system_cap()
                print(ip+": Capacity Details Loaded into Database!")
	except Exception as err:
		print(ip+str(err))


if __name__ == '__main__':
	main()
