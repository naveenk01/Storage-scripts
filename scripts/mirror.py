from mail_aru import start_mail,end_mail

aru_start,aru_t1=start_mail("NACONA_STR_20199345_MirrorScript")


import storage_decrypt,os,MySQLdb, pandas as pd
from sql_query import *
from email.message import Message
import smtplib,subprocess
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

#vol_list -s -t name,mirrored,sg_name,master_name cg=MirrCG_PNV 

columns=['SourceLun','SourceWWN','DestLun','DestWWN','CG']

dbh = MySQLdb.connect(host='localhost',user='cmdb',passwd='Cmdb@2015',db='storapp')
cursor = dbh.cursor()
cursor.execute('select * from xiv_mirror_volumes')
dbMirrorVolumes = list(cursor.fetchall())
dbMirrorVolumes = pd.DataFrame(dbMirrorVolumes, columns=columns)
dbGrouped_Mirrorluns = dbMirrorVolumes.groupby('CG')

#Filter All CGs from CPXIV1
username,password = storage_decrypt.decryption('10.244.144.172')
response = os.system("/root/IBM_Storage_Extended_CLI/xcli -m 10.244.144.172 -u {} -p {} cg_list -s -t name,mirrored > /SAA/XIV/Mirror_script/cg_list.txt".format(username,password) )
f=open("/SAA/XIV/Mirror_script/cg_list.txt",'r')

Mirrorcgs=[]
f.readline()

for line in f:

    cg = line.split(",")
    cgi, mirrored = cg[0].strip('"'), cg[1].strip('"\n')
    print(cgi, mirrored)
    if mirrored=="yes": #Mirrored
        Mirrorcgs.append(cgi)

#print(Mirrorcgs)


output=''
for cg in Mirrorcgs:
    print(cg)
    print("/root/IBM_Storage_Extended_CLI/xcli -m 10.244.144.172 -u {} -p {} vol_list -t name,wwn,mirrored,master_name -s cg={} > /SAA/XIV/Mirror_script/cg_luns.txt".format(username, password, cg))

    os.system("/root/IBM_Storage_Extended_CLI/xcli -m 10.244.144.172 -u {} -p {} vol_list -t name,wwn,mirrored,master_name -s cg='{}' > /SAA/XIV/Mirror_script/cg_luns.txt".format(username, password, cg))
    f=open("/SAA/XIV/Mirror_script/cg_luns.txt",'r')
    f.readline()
    cgluns=[]

    #Filter Mirrorluns from array for cg
    for lun in f:
        lun=lun.split(',')
        print lun
        name,wwn,mirrored,master_name = lun[0].strip('"'), lun[1].strip('"'),lun[2].strip('"') , lun[3].strip('"\n')
        if mirrored =='yes' and master_name == '':
            cgluns.append(name)

 #   print(cgluns)  
    try:  
        dbluns = list(dbGrouped_Mirrorluns.get_group(cg)['SourceLun'])
    except:
        dbluns=[]

    VolumesNotInlatest=[]

    for lun in dbluns:
        if lun in cgluns:
            cgluns.remove(lun)
        else:
            VolumesNotInlatest.append(lun)
    
    VolumesNotIndb = cgluns
    if VolumesNotInlatest:print('Notinlatetst {}'.format(VolumesNotInlatest))
    if VolumesNotIndb:print('Notindb {}'.format(VolumesNotIndb))
    for volume in VolumesNotInlatest:
        os.system("/root/IBM_Storage_Extended_CLI/xcli -m 10.244.144.172 -u {} -p {} vol_list -s -t name,wwn,mirrored,cg_name vol={} > /SAA/XIV/Mirror_script/volume_data.txt  ".format(username, password,volume))
        f = open('/SAA/XIV/Mirror_script/volume_data.txt','r')
        line = f.readline()
        line = line.strip('"\n')
        if line.strip() == 'No volumes match the given criteria':
            print("looks like volume {} has been reclaimed from the database, Hence removing it from database ".format(volume))
            print(delete_query('SourceLun',volume))
            wwn = dbMirrorVolumes.loc[dbMirrorVolumes.SourceLun == volume].SourceWWN.values[0]
            lis= [volume, wwn, 'Volume is recalimed and removed from database' ,' ' ]
            output+= "<tr><td>" +"</td><td>".join(lis) + "</td></tr>"
            continue
        line = f.readline()
        name,wwn,mirrored,cg_name = line.split(',')
        name,wwn,mirrored,cg_name = name.strip('"'),wwn.strip('"'),mirrored.strip('"'),cg_name.strip('"\n')
#        print(name,wwn,mirrored,cg_name,sep='\n')

        if cg_name == '' and mirrored =='no':
            command = "DELETE FROM xiv_mirror_volumes WHERE SourceLun={}".format(repr(name))
            lis= [volume, wwn, "volume is  neither in mirroring nor in CG {},If removed from mirroring permanently update the same in  SAA database".format(cg) ,command]
            output+= "<tr><td>" +"</td><td>".join(lis) + "</td></tr>"
            print('Volume: {} WWN: {} - Is not in mirroring and not in consistency group {}'.format(volume,wwn,cg))

        elif cg_name == '' and mirrored == 'yes':
            command = "UPDATE xiv_mirror_volumes SET ConsistencyGroup=' ' WHERE SourceLun={}".format(repr(name))
            lis= [volume, wwn, "Mirror Volume is out of <strong> {0} </strong> CG, If removed from {0} Permanently update the record in database".format(cg.upper()),command]
            output+= "<tr><td>" +"</td><td>".join(lis) + "</td></tr>"            
            print('Volume: {} WWN: {} - Out of consistency group {}'.format(volume,wwn,cg))
        else:
            command = "DELETE FROM xiv_mirror_volumes WHERE SourceLun={}".format(repr(name))
            lis= [volume, wwn, "in CG {} but not in Mirroring anymore ,".format(cg_name),command]
            output+= "<tr><td>" +"</td><td>".join(lis) + "</td></tr>"              
            print('Volume: {} WWN: {} - belongs to {} Is not in mirroring anymore'.format(volume,wwn,cg))

    for volume in VolumesNotIndb:
        row = dbMirrorVolumes.loc[dbMirrorVolumes.SourceLun == volume]

        if not row.empty:
            wwn = dbMirrorVolumes.loc[dbMirrorVolumes.SourceLun == volume].SourceWWN.values[0]

            # Assuming recently moved to cg
            dbcg = dbMirrorVolumes.loc[dbMirrorVolumes.SourceLun == volume].CG.values[0]
            if dbcg == '':
                print("Volume {} as per Database doesn't belong to consistency group {}, Updating the database".format(volume,cg))
                print(update_query('ConsistencyGroup',cg,'SourceLun',volume))
                lis= [volume, wwn, "Earlier this volume was not part of CG {0} as per database,its currently in CG {0}, Hence updated the database".format(cg),'']
                output+= "<tr><td>" +"</td><td>".join(lis) + "</td></tr>"              
            else:
                print("Volume: {} - As per Database it belongs to consistency group {} As per latest data it belongs to {},Please Update the database".format(volume,dbcg,cg))
                command = "UPDATE xiv_mirror_volumes SET ConsistencyGroup={} WHERE SourceLun={}".format(repr(cg), repr(volume))
                lis= [volume, wwn, "Change to CG {} if required".format(cg),command]
                output+= "<tr><td>" +"</td><td>".join(lis) + "</td></tr>"  
        else:
            #name, wwn and cg from cpxiv1
            os.system("/root/IBM_Storage_Extended_CLI/xcli -m 10.244.144.172 -u {} -p {} vol_list -s -t name,wwn,cg_name vol={} > /SAA/XIV/Mirror_script/volume_data.txt".format(username,password,volume))
            f= open("/SAA/XIV/Mirror_script/volume_data.txt",'r')
            f.readline()
            line = f.readline().split(',')
            name,wwn,cg_name = line[0].strip('"'),line[1].strip('"'),line[2].strip('"\n')
            os.system("/root/IBM_Storage_Extended_CLI/xcli -m 10.244.144.172 -u {} -p {} mirror_list -t remote_peer_name vol={} > /SAA/XIV/Mirror_script/volume_data.txt".format(username,password,volume))
            f= open("/SAA/XIV/Mirror_script/volume_data.txt",'r')
            f.readline()
            line = f.readline()
            remote = line.strip('"\n')            
            #peername, wwn from csxiv1
            os.system("/root/IBM_Storage_Extended_CLI/xcli -m 10.244.144.192 -u {} -p {} vol_list -t wwn vol={} > /SAA/XIV/Mirror_script/volume_data.txt".format(username,password,remote))
            f= open("/SAA/XIV/Mirror_script/volume_data.txt",'r')
            f.readline()
            line = f.readline()
            remotewwn = line.strip('"\n')             
            #adding it to database
            print('Inserting the new volume to database')
            if not cg_name:
                cg_name = ''
           # command = ''
            print(insert_query(name,wwn,remote,remotewwn,cg_name))
            lis= [volume, wwn, "New Volume is added in mirroring CG, Hence updated same in SAA database",'']
            output+= "<tr><td>" +"</td><td>".join(lis) + "</td></tr>"

cursor.execute("SELECT SourceLun,SourceWWN FROM xiv_mirror_volumes WHERE Consistencygroup='' ")

db_standalone=[]
db_standalone = list(cursor.fetchall())
db_standalone = [(line[0] , line[1] )for line in db_standalone]
print(db_standalone)

print(len(db_standalone))
#os.system(" /root/IBM_Storage_Extended_CLI/xcli -m 10.244.144.172 -u {} -p {} vol_list  -s -t name,wwn,mirrored,cg_name >/SAA/XIV/Mirror_script/vol_list.txt".format(username, password) )
#f=open("/SAA/XIV/Mirror_script/vol_list.txt" ,'r' )
#f.readline()
latest_standalone=[]

#Mirrorcgs = ['PNV_DR_112718', 'MirrCG_PNA_PNS' , 'saa_test','MirrCG_PNV','DRCG_capcrd001_etc','DRCG_capecd001_etc','DRCG_caphrd001_etc']
out = subprocess.Popen(['/root/IBM_Storage_Extended_CLI/xcli', '-m', '10.244.144.172', '-u', username, '-p', password,'vol_list','-s','-t','name,wwn,mirrored,cg_name' ],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
line = out.stdout.readline()
for line in out.stdout:
    line=line.split(',')
#    print(line)
    sn,sw,mirrored,cg_name = line[0].strip('"'),line[1].strip('"'), line[2].strip('"') , line[3].strip('"\n')
    if mirrored == 'yes' and cg_name not in Mirrorcgs:
        latest_standalone.append((sn,sw))
print(latest_standalone)

print(len(latest_standalone))

standalonenotinarray =[]
standalonenotindb =[]

for volume in db_standalone:
    if volume not in latest_standalone:
        standalonenotinarray.append(volume)

print(standalonenotinarray)


for volume in standalonenotinarray:
    out = subprocess.Popen(['/root/IBM_Storage_Extended_CLI/xcli', '-m', '10.244.144.172', '-u', username, '-p',password,'vol_list','vol={}'.format(volume[0]),'-s','-t','mirrored,cg_name' ],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    line=out.stdout.readline().strip("\n")
    print(line)
    print(type(line))
    print(line=="No volumes match the given criteria")
    if "No volumes match the given criteria" in line:
        print("Volume has been reclaimed, removing it from database")
        #print("Removed from Mirroring, Need to delete from database")
            #command= "DELETE FROM xiv_mirror_volumes WHERE Sourcelun={}".format(volume[0])
        headers=[volume[0],volume[1],"Removed from Mirroring, Need to delete from database",'']
        output+="<tr><td>"+"</td><td>".join(headers)+"</td></tr>"
        delete_query('Sourcelun',volume[0])

    else:
        print(line)
        line=out.stdout.readline()
        print(line)
        mirrored, cg_name = line.split(',')[0],line.split(',')[1].strip("\n")
        if mirrored.strip('"')=='no':
            print("Removed from Mirroring, Need to delete from database")
            command= "DELETE FROM xiv_mirror_volumes WHERE Sourcelun={}".format(volume[0])
            headers=[volume[0],volume[1],"Removed from Mirroring, Need to delete from database",command]
            output+="<tr><td>"+"</td><td>".join(headers)+"</td></tr>"

for volume in latest_standalone:
     if volume not in db_standalone:
         standalonenotindb.append(volume)


print(standalonenotindb)

for volume in standalonenotindb:
    Sourcelun,SourceWWN=volume[0],volume[1]
    out = subprocess.Popen(['/root/IBM_Storage_Extended_CLI/xcli', '-m', '10.244.144.172', '-u',username, '-p', password,'mirror_list','-s','-t','remote_peer_name' ],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    remote = out.stdout.readline()
    remote = out.stdout.readline().strip('"\n')           
    out = subprocess.Popen(['/root/IBM_Storage_Extended_CLI/xcli', '-m', '10.244.160.172', '-u',username, '-p', password,'vol_list','vol={}'.format(remote),'-s','-t','wwn' ],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    remotewwn = out.stdout.readline()
    remotewwn = out.stdout.readline().strip('"\n')
    print(insert_query(Sourcelun,volume[1],remote,remotewwn,''))
    
    print('Inserting the new volume to database') 
    print(volume[0] , volume[1],remote,remotewwn)   
    #command= "DELETE FROM xiv_mirror_volumes WHERE Sourcelun={}".format(volume[0])
    headers=[volume[0],volume[1],"Inserted into database",""]
    output+="<tr><td>"+"</td><td>".join(headers)+"</td></tr>"










def mail(html_data):    
    fromaddr = "CONA_SAA@capgemini.com" #CONA-SAA ADMIN
    toaddr="conastorage.nar@capgemini.com" #conastorage.nar@capgemini.com
    ccaddr="prasanna.kandregula@capgemini.com" 
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['cc']=ccaddr
    msg['Subject'] = "CONA XIV Mirror lun Mismatch Alert"
    msg.attach(MIMEText(html_data,'html'))
    toaddrs=[toaddr]+[ccaddr]
    server = smtplib.SMTP('161.162.144.164') #cona SMTP
    text = msg.as_string()
    print "Sending Mail..........\n"
    server.sendmail(fromaddr,toaddrs,text)
    print "Mail Sent Successfully..........\n"
    server.quit()

htmli=''
htmli+='<html><body>'
htmli+='<p>Hi Team</p>'
htmli+="<p>Below are the lun Mismatches from XIV as per standard data</p>"
htmli+='<table border=1 style="border-collapse: collapse; border : 1px solid black;">'
headers= ['VolumeName','WWN', 'Status', 'Command to update in SAA database' ]
htmli+='<tr bgcolor="lightblue" align="left"><th> {}  </th></tr>'.format('</th><th>'.join(headers))
htmli+=output
htmli+='</table></body></html>'
if output:mail( htmli)
end_mail("NACONA_STR_20199345_MirrorScript","successful",aru_start,aru_t1)
