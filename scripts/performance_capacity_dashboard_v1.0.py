# -*- coding: ascii -*-
from mail_aru import start_mail,end_mail

aru_start,aru_t1=start_mail("NACONA_STR_20199342_Capacity_performance_dashboard")


import v7000_capacity_Collect 
import xiv_capacity_Collect
import isilon_capacity_collect
import CONA_performance_collect_V7000
import CONA_performance_collect_xiv
import MySQLdb, datetime, paramiko, smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email import encoders
from email.MIMEImage import MIMEImage
import switch_decrypt

## To add a new V7000 or XIV device to the report please add the details to the inventory database and also make an entry of it in the below lists
## To add a new brocade switch to the report please add the details to the inventory database
v7000_device_name = ['cpv7k1clst1','CPV7KU1FIL','csv7ku1fclst1','csv7k1clst1']
xiv_device_names = ['cpxiv1','cpxiv2','csxiv1','csxiv2']


def ipfetch():
    dbh = MySQLdb.connect(host='localhost',user='cmdb',passwd='Cmdb@2015',db='storapp')
    cursor = dbh.cursor()
    ip, arrays, dc = [], [], []
    cursor.execute("select distinct mgmt_ip,switch from switch where client='CONA' and (family = 'Brocade' or family= 'brocade')");
    numrows = int(cursor.rowcount)
    for x in range(0,numrows):
        row = cursor.fetchone()
        ip.append(row[0])
        arrays.append(row[1])
    cursor.close()
    return ip,arrays


def mail(html_data):
    fromaddr = "CONA-SAA@capgemini.com"
    toaddr = "conastorage.nar@capgemini.com"
    ccaddr = "harikrishna.maddineni@capgemini.com"
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['cc']=ccaddr
    msg['Subject'] = "CONA-Capacity & Performance Dashboard {}".format( datetime.datetime.now().strftime("%d-%m-%Y"))
    msg.attach(MIMEText(html_data, 'html'))
    # This example assumes the image is in the current directory
    fp = open('/SAA/V7000/V7000_Capacity_Performance_Dashboard/logo.jpg', 'rb')
    msgImage = MIMEImage(fp.read())
    fp.close()
    # Define the image's ID as referenced above
    msgImage.add_header('Content-ID', '<image1>')
    msg.attach(msgImage)
    server = smtplib.SMTP('161.162.144.164')
    text = msg.as_string()
    toaddrs = [toaddr] + [ccaddr]
    print("Sending Mail..........\n")
    server.sendmail(fromaddr, toaddrs, text)
    print("Mail Sent Successfully..........\n")
    server.quit()


def html_writing(header, Table_title):
    Data = """<table border ="2" solid black ><tr> <th bgcolor = "powderblue";text-align:center colspan={0}>{1}</th></tr>""".format(
        len(header), Table_title)
    for head in header:
        Data += '<th bgcolor = "powderblue";text-align:center>{0}</th>'.format(head)
    return Data


class Brocade:
    def __init__(self, ip, user, pwd):
        # pass
        # self.ip = ip
        # self.user = user
        # self.pwd = pwd
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        self.ssh.connect(ip, port=22, username=user, password=pwd)

    def html_table(self, data_list):
        data = ''
        data += "<tr><td rowspan = {0}>{1}</td><td rowspan = {0}>{2}</td>".format(len(data_list), self.switchname, self.uptime)
        if len(data_list) > 0:
            for val in range(0, len(data_list)):
                    for val1 in range(0, len(data_list[val])):
                        data += "<td>{0}</td>".format(data_list[val][val1])
                    data += "</tr>"
        else:
            data += "<td colspan = 20>No errors</td>"
        return data


    def html_table1(self, data_list):
        data = ''
#        data += "<tr><td rowspan = {0}>{1}</td><td rowspan = {0}>{2}</td>".format(len(data_list), self.switchname, self.uptime)
        if len(data_list) > 0:
    	    data += "<tr><td rowspan = {0}>{1}</td><td rowspan = {0}>{2}</td>".format(len(data_list), self.switchname, self.uptime)

            for val in range(0, len(data_list)):
                    for val1 in range(0, len(data_list[val])):
			if val1>2 and 'k' in data_list[val][val1]:
                            data += "<td bgcolor=red>{0}</td>".format(data_list[val][val1])
			elif val1>2 and int(data_list[val][val1])>=15:
                            data += "<td bgcolor=red>{0}</td>".format(data_list[val][val1])
                    	else:
                            data += "<td>{0}</td>".format(data_list[val][val1])
                    data += "</tr>"
        return data

    def switch_name(self):
        self.stdin, self.stdout, self.stderr = self.ssh.exec_command("switchname")
        for line in self.stdout.readlines():
            self.switchname = line.strip()
        print(self.switchname)
        return self.switchname

    def switch_uptime(self):
        self.stdin, self.stdout, self.stderr = self.ssh.exec_command("uptime")
        for line in self.stdout.readlines():
            uptime = line.strip()
        print(uptime)
        self.uptime = " ".join(uptime.split()[2:4])
        print(self.uptime)
        return self.uptime

    def porterr_show(self):
        porterr_data = []
	threshold_data = []
        self.stdin, self.stdout, self.stderr = self.ssh.exec_command("porterrshow")
        for line in self.stdout.readlines():
            if ":" in line:
                line = line.split()
		#print "LINE:",line
                line[0] = line[0].split(":")[0]
                if not all(v == '0' for v in line[3::]):
		    		                        
# porterr_data.append((line[0].split(":")[0], line[1], line[2], line[4], line[10], line[11],line[12],line[13]))
                    porterr_data.append(line)
		    
		    t_list=0
		    for each in line[3::]:
			if 'k' in each:		   
 			    t_list+=1
			elif int(each)>=15:
			    t_list+=1

		    if t_list>0:
		        threshold_data.append(line)			    
                else:
                    pass
                    continue

        data = self.html_table(porterr_data)
	data1 = self.html_table1(threshold_data)
        return data,data1

    def ssh_close(self):
        self.ssh.close()


class DataBase:
    def __init__(self):
        self.date = datetime.datetime.now().strftime("%Y-%m-%d")
        self.dbh = MySQLdb.connect(host='localhost', user='cmdb',passwd= 'Cmdb@2015', db='storapp')
        self.html_data = """<html><style type="text/css">
                                        <style>
                                        th { border:1px solid black; }
                                        tr { border:1px solid black; }
                                        td { border:0.5px solid black;}
                                        table{ text-align:center; border:1px solid black;  width:50%;}
                                        img{ display: inline-block;}
                                        </style>
                                        <body>
                                        <h1 style="color:#e51b1b;"><img src="cid:image1" hspace="20" alt="CONA" WIDTH = 75 HEIGHT = 40> Capacity & Performance Dashboard</h1>"""

    def html_end(self):
        return """</table><br><table border ="2" solid black ><tr><th 
        colspan=2>Note:</th></tr><tr><th>Criteria</th><th>Color</th></tr><tr><td>70-80%</td><td 
        bgcolor=yellow></td></tr><tr><td>>80%</td><td bgcolor=red></td></tr></table></html> """

    def html_writing(self, header, Table_title):
        Data = """<table border ="2" solid black ><tr> <th bgcolor = "powderblue";text-align:center colspan={0}>{1}</th><tr>""".format(
            len(header), Table_title)
        for head in header:
            Data += '<th bgcolor = "powderblue";text-align:center>{0}</th>'.format(head)
        return Data

    def html_table(self, data_list, colors):
        data = '<tr>'
        # data += "<tr><td rowspan = {0}>{1}</td>".format(len(data_list), dc)
        for val in range(0, len(data_list)):
            for val1 in range(0, len(data_list[val])):
                if val1 in colors:
                    if data_list[val][val1] > 70 and data_list[val][val1] < 80:
                        data += "<td bgcolor=yellow>{0}</td>".format(data_list[val][val1])
                    elif data_list[val][val1] >= 80:
                        data += "<td bgcolor=red>{0}</td>".format(data_list[val][val1])
                    else:
                        data += "<td>{0}</td>".format(data_list[val][val1])
                else:
                    data += "<td>{0}</td>".format(data_list[val][val1])
            data += "</tr>"
        return data

    def v7000_dashboard(self):
        data = ''
        labels = ["Device Name", "Throughput(Mbps)", "IOPs", "Read Latency(ms)", "Write Latency(ms)","Total Vdisk Capacity(TB)","Total mdisk Capacity(TB)", "Total Used Capacity(TB)", "Total Free Capacity(TB)", "Used %", "Allocated %"]
        data_list =[]
        for device in v7000_device_name:
            print(device)
            cursor = self.dbh.cursor()
            cursor.execute("SELECT distinct v7000_perf.device_name,v7000_perf.throughput,v7000_perf.iops,v7000_perf.read_latency,v7000_perf.write_latency,v7000_systemcap.total_vdisk, v7000_systemcap.total_mdiskcap, v7000_systemcap.total_usedcap,v7000_systemcap.total_freecap, v7000_systemcap.used_percent, v7000_systemcap.allocated_percent from `v7000_perf` INNER JOIN v7000_systemcap on v7000_systemcap.device_name=v7000_perf.device_name  and v7000_systemcap.date=v7000_perf.date WHERE v7000_systemcap.device_name ='{0}' and v7000_systemcap.date = '{1}'".format(device, self.date));
            for i in range(int(cursor.rowcount)):
                row = cursor.fetchone()
                data_list.append(row)
                # print(row)
        print(data_list)
        data += self.html_table(data_list, colors= [9])
        self.html_data += self.html_writing(header = labels, Table_title="V7000 Storage Capacity & Performance Dashboard")+data+"</table><br>"

    def xiv_dashboard(self):
        data = ''
        labels = ["Device Name", "IOPs", "Throughput (Mbps)",  "Latency (ms)", "Hard Size(TB)", "Hard Used(TB)", "Hard Free Capacity(TB)", "Hard used %", "Soft Size(TB)", "Soft Used(TB)", "Soft Free Capacity(TB)", "Soft used %","Allocated %"]
        for device in xiv_device_names:
            data_list =[]
            cursor = self.dbh.cursor()
            cursor.execute("SELECT distinct xiv_perf.device_name,xiv_perf.iops,xiv_perf.throughput,xiv_perf.latency, xiv_syscap.hard_size, xiv_syscap.hard_used,xiv_syscap.hard_available,xiv_syscap.hard_used_percent,xiv_syscap.soft_size,xiv_syscap.soft_used,xiv_syscap.soft_available,xiv_syscap.soft_used_percent,xiv_syscap.allocated_percent FROM xiv_perf INNER JOIN xiv_syscap on xiv_syscap.device_name=xiv_perf.device_name and xiv_syscap.date=xiv_perf.date WHERE xiv_syscap.device_name='{0}' and xiv_syscap.date='{1}'".format(device, self.date));
            for i in range(int(cursor.rowcount)):
                row = cursor.fetchone()
                data_list.append(row)
            data += self.html_table(data_list, colors=[7, 11])
        self.html_data += self.html_writing(header=labels, Table_title="XIV Storage Capacity & Performance Dashboard")+data+"</table><br>"

    def isilon_dashboard(self):
        Datacenter=["ETC-PROD","SDC-DR"]
        labels=["Datacenter","Name", "UsedCapacity", "Used%", "TotalCapacity","AllocatedCapacity","Allocated%"]
        data=''
        for dc in Datacenter:
            data_list = []
            cursor = self.dbh.cursor()
            print(
                "SELECT DISTINCT device_name,total_usedcap,used_percent,total_mdiskcap,"
                "total_vdisk,allocated_percent  from"
                "isilon_systemcap where date ='{0}' and dc = '{1}'".format(self.date, dc))

            cursor.execute(
                "SELECT DISTINCT device_name,total_usedcap,used_percent,total_mdiskcap,"
                "total_vdisk,allocated_percent  from"
                " isilon_systemcap where date ='{0}' and dc = '{1}'".format(self.date, dc))

            data += "<tr><td rowspan = {0}>{1}</td>".format(int(cursor.rowcount), dc)
            for i in range(int(cursor.rowcount)):
                row=cursor.fetchone()
                for column_number, value in enumerate(row):
                    if column_number in [2,5]:
                        if 70<value<80:
                            data += "<td bgcolor=yellow>{0}</td>".format(value)
                        elif value>80:
                            data += "<td bgcolor=red>{0}</td>".format(value)
                        else:
                            data += "<td>{0}</td>".format(value)
                    else:
                        data += "<td>{0}</td>".format(value)
            data+="</tr>"
        self.html_data += self.html_writing(header=labels, Table_title="Isilon Dashboard") + data + "</table><br>"


if __name__ == '__main__':
    #v7000_capacity_Collect.main()
    #xiv_capacity_Collect.main()
    #isilon_capacity_collect.main()
    CONA_performance_collect_V7000.main()
    CONA_performance_collect_xiv.main()
    error =[]
    db = DataBase()
    db.v7000_dashboard()
    db.xiv_dashboard()
    db.isilon_dashboard()
    labels = ['Switch Name', 'Uptime', 'Port Index', 'Frames Tx', 'Frames Rx', 'enc-in', 'crc-err',
     'crc-g_eof', 'too-shrt', 'too-long', 'bad-eof', 'enc-out', 'disc-c3', 'link-fail',
     'loss-sync', 'loss-sig', 'frjt', 'fbsy', 'c3timeout-tx', 'c3timeout-rx',
     'pcs err', 'uncor err']
    html_data = html_writing(header=labels, Table_title="Switch Port Utilization and Error Dashboard")
    html_data1=html_writing(header=labels, Table_title="Switch Port Utilization and Error Dashboard")
    ips, switches = ipfetch()
    for ip,switch_name in zip(ips, switches):
        try:
            user, pwd = switch_decrypt.decryption(ip)
            switch = Brocade(ip,user,pwd)
            switchname = switch.switch_name()
            uptime = switch.switch_uptime()
            data,data1 = switch.porterr_show()
            switch.ssh_close()
            html_data += data
	    html_data1 +=data1
        #except paramiko.ssh_exception.AuthenticationException as err:
        except Exception as err:
            error.append((ip + str(err)))
            continue
    html_data += "</table><br>"
    if error:
        mail(db.html_data+ html_data+"<br>".join(error))
    else:
        mail(db.html_data + html_data)
	mail(html_data1)

end_mail("NACONA_STR_20199342_Capacity_performance_dashboard","successful",aru_start,aru_t1)

