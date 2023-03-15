from __future__ import division

from mail_aru import start_mail,end_mail
import paramiko
import xiv_capacity_Collect,v7000_capacity_Collect,subprocess,isilon_capacity_collect 
import MySQLdb, datetime, smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from email.MIMEBase import MIMEBase
from email.MIMEImage import MIMEImage
from datetime import datetime,timedelta
from storage_decrypt import decryption

devices_row_order= [('cpv7k1clst1','V7000','etc') , ('cpv7k2clst1','V7000','etc'), ('CPV7KU1FIL','V7000-unified','etc') , ('cpev7kgen3','V7000-Flash','etc') , ('cpxiv1','xiv','etc'),('cpxiv2','xiv','etc'), ('CPISICLST01','Isilon','etc'),
                         ('csv7k1clst1','V7000','sdc'), ('csv7ku1fclst1','V7000-unified','sdc'),('csev7kgen3','V7000-Flash','sdc'),('csxiv1','xiv','sdc'),('csxiv2','xiv','sdc'), ('CSISICLST01','Isilon','sdc')]

today=datetime.today()
date=today.strftime("%Y-%m-%d")
last_week_date=today + timedelta(days=-7)
if today.month == last_week_date.month:
    week = "%s(%s-%s)"%(today.strftime("%b"),last_week_date.strftime("%d"),today.strftime("%d")  )
else:
    week = "%s-%s"%(last_week_date.strftime("%b %d"),today.strftime("%b %d") )

Two_Weeks_cap={}

dbh = MySQLdb.connect(host='localhost', user='cmdb',passwd='Cmdb@2015', db='storapp')
cursor = dbh.cursor()
device_capacity = {} 


def mail(html_data):
    fromaddr = "CONA-SAA@capgemini.com"
    toaddr = ["rli@conaservices.com","greg.flores@capgemini.com",
              "vipin.joganpalli@capgemini.com","kiran.urs@capgemini.com"]
    ccaddr = ["ravichandir.thirugnana@capgemini.com","conastorage.nar@capgemini.com"]
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = ",".join(toaddr)
    msg['cc']=",".join(ccaddr)
    msg['Subject'] = "CONA_Weekly_Storage_Capacity_Trend_Report_{}".format(datetime.now().strftime("%d-%B-%Y"))
    paths=["/SAA/plots/All_etc.png","/SAA/plots/All_sdc.png","/SAA/plots/etc_imag1.png" ,"/SAA/plots/etc_imag2.png", 
           "/SAA/plots/sdc_imag1.png", "/SAA/plots/sdc_imag2.png"]
    images=['<image1>','<image2>','<image3>','<image4>','<image5>','<image6>']
    for path,img in zip(paths,images):
        fp = open(path, 'rb')
        msgImage = MIMEImage(fp.read())
        fp.close()
        msgImage.add_header('Content-ID', img )
        msg.attach(msgImage)
    msg.attach(MIMEText(html_data, 'html'))
    server = smtplib.SMTP('161.162.144.164')
    toaddrs=toaddr+ccaddr
    text = msg.as_string()
    #print("Sending Mail..........\n")
    server.sendmail(fromaddr, toaddrs, text)
    #server.sendmail(fromaddr, ["pkandreg@capgemini.com"], text)
    #print("Mail Sent Successfully..........\n")
    server.quit()

def update_db(dc, device_type,device_name,used_cap, virtual_cap):
    cursor.execute("REPLACE INTO weekly_capacity_details"
                    "(date,week,Datacenter, DeviceType, device_name, used_cap, virtual_cap)"
                    "VALUES('{0}','{1}','{2}','{3}','{4}','{5}','{6}' )".format(
                    date, week, dc, device_type,device_name,used_cap, virtual_cap))


def retrieve_data():
    for device,_,loc in devices_row_order:
        cursor.execute("SELECT used_cap,virtual_cap FROM weekly_capacity_details WHERE device_name ='{}'  ORDER BY date DESC limit 2".format(device))
        Two_Weeks_cap[device] =cursor.fetchall()


def xiv_pool(ip,username,password):
    out = subprocess.Popen(
            ['/root/IBM_Storage_Extended_CLI/xcli', '-m', ip, '-u', username, '-p',password,
             'pool_list'],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    out.stdout.readline()
    xiv_pools=[]
    for line in out.stdout:
        line=line.split()
        name=line[0]
        pool_hard=round(float(line[5])/1024,2)
        pool_hard_used=round((float(line[6])+float(line[8]))/1024,2)
        allocated_used=round((float(line[2])+float(line[3]))/1024,2)
        ##print "allocated"
        #print allocated_used
        xiv_pools.append((name,pool_hard_used, round((pool_hard_used*100/pool_hard),2),pool_hard,allocated_used,round((allocated_used*100/pool_hard),2)))
    return xiv_pools

def V7000_pool_values(array):
    v7k_pools=[]
    cursor.execute("SELECT pool_name,used_cap, used_percent, capacity,"
                        "virtual_cap,allocated_percent  from v7000_pool where date ='{0}' and device_name = '{1}'".format(date, array))
    return cursor.fetchall()


def isilon_capacity(array):
    cursor.execute("SELECT device_name,total_usedcap,used_percent,total_mdiskcap,"
                        "total_vdisk,allocated_percent  from Isilon_systemcap where date ='{0}' and device_name = '{1}'".format(date, array))
    return [cursor.fetchone()]

def diff(prev,curr):
    if prev<curr:
       return 'increased by {} TB'.format(str(curr-prev))
    elif prev>curr:
       return 'decreased by {} TB'.format(str(prev-curr))
    else:
       return 'No change, It  is constant -%d TB'%curr

def unified_cap(array):
    service_ip ={'CPV7KU1FIL': '10.244.144.135',
                 'csv7ku1fclst1':'10.244.160.101'}
    user,password =decryption(service_ip[array]) 
    cursor.execute("SELECT pool_name,used_cap, used_percent, capacity,"
                        "virtual_cap,allocated_percent  from v7000_pool where date ='{0}' and device_name = '{1}'".format(date, array))   
    pool_values = cursor.fetchall()
    print pool_values
    pool_name= "&".join([pool[0] for pool in pool_values])
    total_capacity=sum([pool[3] for pool in pool_values ])
    allocated_capacity = sum([pool[4] for pool in pool_values])
    ssh=paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(service_ip[array],port=1602,username=user,password=password)
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
    print((pool_name, total_used,  round(((total_used*100)/total_capacity) ,2) , total_capacity,
            allocated_capacity , round(((allocated_capacity*100)/total_capacity) ,2)   ))

    return [(pool_name, total_used,  round(((total_used*100)/total_capacity) ,2) , total_capacity, 
            allocated_capacity , round(((allocated_capacity*100)/total_capacity) ,2)),]



def above_threshold(device,color):
    """returns analyzation of V7000 devices"""

    analysis='<tr><td rowspan=2 style="background-color:{};font-size:14px;font-family:calibri;font-weight:normal;">{}</td>'.format(color,device)
    device_cap = device_capacity[device]
    used_percent = device_cap[0]*100/device_cap[1]
    allocated_percent = device_cap[2]*100/device_cap[1]
    if used_percent >=  70:
        analysis+='<td style="background-color:{2};font-size:12px;font-family:calibri;font-weight:bold">The Actual Used capacity({0} TB) is above threshold 70% ({0}TB/{1}TB)</td></tr>'.format(device_cap[0],round(device_cap[1]),color)
    else:    
        analysis+='<td style="background-color:{2};font-size:12px;font-family:calibri;font-weight:bold">The Actual Used capacity({0} TB) is below threshold 70% ({0}TB/{1}TB)</td></tr>'.format(device_cap[0],round(device_cap[1]),color)
       
    if allocated_percent >= 100:
        analysis+='<td style="background-color:{0};font-size:12px;font-family:calibri;font-weight:bold"> The virtual allocation capacity({2} TB) over the Array MAXIMUM capacity (~{2} TB)</td></tr>'.format(color,device_cap[0],round(device_cap[1]))
    elif allocated_percent == 0:
        analysis += '<td style="background-color:{};font-size:12px;font-family:calibri;font-weight:bold">The Virtual allocation is 0 TB</td></tr>'.format(color)
    else:
        analysis +='<td style="background-color:{};font-size:12px;font-family:calibri;font-weight:bold">The virtual allocation capacity({} TB) is {}% of  Array MAXIMUM capacity (~{} TB)</td></tr>'.format(color,device_cap[2],round(allocated_percent),device_cap[1])
    return analysis
        



def html_format(device_name,capacity_details):
    ##print device_name
    ##print capacity_details
    total_usedcap,used_percent, total_capacity,virtual_cap,allocated_percent=capacity_details
    none='#FFFFFF'
    bg_color1 = none if used_percent<70  else ("red" if used_percent>=80 else "yellow")
    bg_color2 = none if allocated_percent<100  else ("red" if allocated_percent>=150 else "yellow")
    row_array =("<tr><td>{}</td><td>{}</td><td bgcolor={}>{}</td>"
               "<td>{}</td><td>{}</td>"
               "<td bgcolor={}>{}</td>").format(device_name,str(total_usedcap),bg_color1,str(used_percent),  str(total_capacity),str(virtual_cap),bg_color2,str(allocated_percent))
    return row_array


def html_block(devices):
    block="<table cellpadding=12 style='border-collapse: collapse'>"
    for num,device in enumerate(devices):
        color= '#FBFCFC' if num%2 == 0 else '#D7DBDD'
        if device in ['cpv7k1clst1','cpv7k2clst1', 'csv7k1clst1']:
            block+=above_threshold(device,color)
        else:
            block+="<tr style='background-color:{};'><td rowspan=2 style='font-size:14px;font-family:calibri;font-weight:normal;'>{}</td>".format(color,device)
            curr_week, prev_week = Two_Weeks_cap[device]
            block+="<td style='font-size:12px;font-family:calibri;font-weight:bold'>This Week overall used Capacity {}</td></tr>".format(diff(prev_week[0], curr_week[0]))
            block+="<td style='background-color:{};font-size:12px;font-family:calibri;font-weight:bold'>This Week overall allocated Capacity {}</td></tr>".format(color,diff(prev_week[1] ,curr_week[0] )   )
    block+="</table><br>"
    return block

def main():
    import weekly_plots
    xiv_capacity_Collect.main()
    v7000_capacity_Collect.main()
    isilon_capacity_collect.main()
    style="""<html><style type="text/css">
                        <style>
                        .div1 { width: 25px;height: 300px; padding: 20px;border: 1px solid black;}
                        span{font-size:12px;font-family:calibri;font-weight:bold}
                        th { border:1px solid black; }
                        tr { border:1px solid black;text-align:left; }
                        td { border:0.5px solid black;}
                        img{ display: inline-block;}
                        </style>
                        <body>"""

    
    devices_row_order= [('cpv7k1clst1','V7000','etc') , ('cpv7k2clst1','V7000','etc'), ('CPV7KU1FIL','V7000-unified','etc') ,
                        ('cpev7kgen3','V7000-Flash','etc') , ('cpxiv1','xiv','etc'),('cpxiv2','xiv','etc'), ('CPISICLST01','Isilon','etc'),
                         ('csv7k1clst1','V7000','sdc'), ('csv7ku1fclst1','V7000-unified','sdc'),('csev7kgen3','V7000-Flash','sdc'),
                         ('csxiv1','xiv','sdc'),('csxiv2','xiv','sdc'), ('CSISICLST01','Isilon','sdc')]
    
    pool_values={}   
    dc_capacity ={'etc':{'used':0,'total':0,'allocated':0 },'sdc':{'used':0,'total':0,'allocated':0 }}

    pool_table =''
    array_table=''
    dc_table=''
    headers=['Storage Name','Used(TB)', 'Used %', 'Total (TB)', 'Virtual Allocated (TB)','% Allocated']
    cona_capacity_table= "<table><tr><td align='center' bgcolor='#34307B' colspan=6 style='color:whilte;'>CONA Storage Capacity Utilization  Report-{}</td></tr>".format(week)  +  "<tr><td bgcolor='#002b80'>" + "</td><td bgcolor='#002b80'>".join(headers) +"</tr>"
    xiv_total_capacity={'cpxiv1':325.48   , 'cpxiv2': 325.48  , 'csxiv1':325.48    ,'csxiv2':205.22 }
    for (device,device_type,location) in devices_row_order:
        #getting pool values of devices
        if device_type in ['V7000','V7000-Flash']:
            pool_values[device] = V7000_pool_values(device)
        elif device_type == 'V7000-unified':
            pool_values[device]=unified_cap(device)
        elif device_type =='xiv':
            cursor.execute("select mgmt_ip from storage where array='{}'".format(device))
            ip=cursor.fetchone()[0]
            #print ip
            pool_values[device] =xiv_pool(ip,'saauser','Saauser@123')
        else:
            pool_values[device] = isilon_capacity(device)
        #print(pool_values[device])

        #html_format of pool_table
        #print device
        for pool_value in pool_values[device]:
            print pool_value
            pool_table+=html_format(pool_value[0],[pool_value[1],pool_value[2],pool_value[3],pool_value[4],pool_value[5]])

        #sum of pool values to get array capacity
        array_used=round(sum(pool[1] for pool in pool_values[device]),2)
        array_total=round(sum(pool[3] for pool in pool_values[device]),2 )
        array_allocated=round(sum(pool[4] for pool in pool_values[device]),2)
        if device_type=='xiv':
            cursor.execute("select hard_size from xiv_syscap where device_name='{}' and date='{}'".format(device,date))
            array_total=round(cursor.fetchone()[0],2)
        if device =='csxiv2':
            array_total=207.2
        device_capacity[device] = [array_used, array_total,array_allocated]

        #Adding the array capacities to their respective datacenter
        dc_capacity[location]['used']+=array_used
        dc_capacity[location]['total'] +=array_total
        dc_capacity[location]['allocated']+=array_allocated

        # #html_format of array_table
        #print(array_total)
        array_table+=html_format(device.upper(), [array_used, round(array_used*100/array_total ,2) ,array_total, 
                                           array_allocated,round(array_allocated*100/array_total,2)])
        update_db(location,device_type,device,array_used,array_allocated) 
    
    dc_capacity['etc']['total']=1122.65
    dc_capacity['sdc']['total']=1084.92
    dc_table+=html_format('ETC', [dc_capacity['etc']['used'] ,round(dc_capacity['etc']['used']*100/dc_capacity['etc']['total'],2), dc_capacity['etc']['total'], dc_capacity['etc']['allocated'],round(dc_capacity['etc']['allocated']*100/dc_capacity['etc']['total'],2)])
    dc_table+=html_format('SDC',  [dc_capacity['sdc']['used'] ,round(dc_capacity['sdc']['used']*100/dc_capacity['sdc']['total'],2), dc_capacity['sdc']['total'], dc_capacity['sdc']['allocated'],round(dc_capacity['sdc']['allocated']*100/dc_capacity['sdc']['total'],2)] )

    update_db('etc','All','ETC_capacity',dc_capacity['etc']['used'], dc_capacity['etc']['allocated'] )
    update_db('sdc','All','sdc_total_Cap',dc_capacity['sdc']['used'], dc_capacity['sdc']['allocated'] )    

    used_cona_capacity= dc_capacity['etc']['used'] + dc_capacity['sdc']['used']
    allocated_cona_capacity =dc_capacity['etc']['allocated'] +dc_capacity['etc']['allocated']
    total_cona_capacity=dc_capacity['etc']['total'] + dc_capacity['sdc']['total']


    cona_capacity_table += html_format('Capacity=>',[ used_cona_capacity ,round(used_cona_capacity*100/total_cona_capacity,2), 
                             total_cona_capacity, allocated_cona_capacity,round(allocated_cona_capacity*100/total_cona_capacity,2)] )
    dbh.commit()#comment this line  when you dont want to update the database
    
                             
    etc_cap,sdc_cap= weekly_plots.main()
    
    dc_analysis="""<table cellpadding=12  border= 1px solid black style='border-collapse: collapse'><tr><td>
                <h4>ETC</h4>
		<span>1)This Week overall used Capacity {}</span><br>
		<span>2)This Week overall allocated Capacity {}</span><br>
		<h4>SDC</h4>
		<span>1)This Week overall used Capacity {} </span><br>
		<span>2)This Week overall allocated Capacity {}</span><br><br>
		</td></tr></table>""".format(diff(etc_cap['used_cap'][1],etc_cap['used_cap'][0]),diff(etc_cap['virtual_cap'][1],etc_cap['virtual_cap'][0]),
                                    diff(sdc_cap['used_cap'][1],sdc_cap['used_cap'][0]),diff(sdc_cap['virtual_cap'][1],sdc_cap['virtual_cap'][0]))
                                    
    #print dc_analysis

    retrieve_data()
    etc_array_analysis =  html_block([device for device,_,loc in devices_row_order if loc =='etc'])
    sdc_array_analysis =  html_block([device for device,_,loc in devices_row_order if loc =='sdc'])

    #print etc_array_analysis
    #print sdc_array_analysis

    body="""<p>Hi All,
          <br><br>Please find the Weekly Storage Capacity Trending report of ETC and Savvis devices as on {}</p>
          <p style='margin-left:20px;margin-right:60px;background-color:#7A60A0;color:white;font-size:20px;text-align:center;font-family:calibri;'><strong>
          CONA Storage Capacity Weekly Growth Trend Report - {} {}
          <h3 style='text-align:center;margin-left:45px;margin-right:200px;'>Weekly Overall Actual used Vs Allocated Capacity</h3>
          <table border="0" cellpadding=30><tr><td style="border:none;"><img src="cid:image1" hspace="20" alt="CONA" WIDTH = "500" HEIGHT = "300" border="0"></td>
          <td  style="border:none;"><img src="cid:image2" hspace="20" alt="CONA" WIDTH ="500" HEIGHT = "300" border="0"/></td></tr></table>
          {}
          <h3 style='text-align:center;margin-left:45px;margin-right:200px;'>Weekly - ETC Growth</h3>
          <table border="0" cellpadding=25><tr><td  style="border:none;"><img src="cid:image3" hspace="20" alt="CONA" WIDTH = 550 HEIGHT = 350 border="0"/></td><td  style="border:none;">
          <img src="cid:image4" hspace="20" alt="CONA" WIDTH = 550 HEIGHT = 350 border="0"/></td></tr></table>{}
          <h3 style='text-align:center;margin-left:45px;margin-right:200px;'>Weekly - SDC Growth</h3>
          <table  border="0" cellpadding=25><tr><td  style="border:none;"><img src="cid:image5" hspace="100" alt="CONA" WIDTH = 550 HEIGHT = 350  border="0"></td>
          <td  style="border:none;">
          <img src="cid:image6" hspace="20" alt="CONA" WIDTH = 550 HEIGHT = 350 border="0"></td></tr></table>{}""".format(date,today.strftime("%Y") ,week,dc_analysis,etc_array_analysis,sdc_array_analysis)
    print(body)
    mail("""{}{}{}<tr><td bgcolor = " #0000cc";text-align:left colspan=6></td></tr>{}<tr bgcolor=#FFFFFF>
            <td  bgcolor = " #0000cc";text-align:left colspan=6></td></tr>{}<tr bgcolor=#FFFFFF>
            <td  bgcolor = " #0000cc";text-align:left colspan=6></td></tr>{}
            </table><br><br><span><font size="4">Regards,</span><br><span><font size="4">Storage Admin</span>""".format(style,body,cona_capacity_table, dc_table,array_table ,pool_table))
    cursor.close()
    print etc_array_analysis
    print sdc_array_analysis


if __name__ =="__main__":
    aru_start,aru_t1=start_mail("CONA_STR_20199343_CONA_Weekly_Monthly_Capacity_Report")
    main()
    end_mail("NACONA_STR_20199343_CONA_Weekly_Monthly_Capacity_Report","successful",aru_start,aru_t1)
