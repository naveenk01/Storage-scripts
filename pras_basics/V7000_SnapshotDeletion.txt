from mail_aru import start_mail,end_mail

aru_start,aru_t1=start_mail("NACONA_STR_20199348_Expired_Snapshot_deletion")

import  sys, os, paramiko, time, copy,MySQLdb
from expiredSnap import expired,confirmation_rename
from v7k_checks import *
from email.message import Message
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

ip, username,password = sys.argv[1],sys.argv[2],sys.argv[3]

arrays={'10.244.160.90':'Csv7k1' , '10.244.144.110':'cpv7k1' , '10.244.144.119':'cpv7k2' }

# Connection to the ip and filtering expired snapshots from mappings
ssh=paramiko.SSHClient() 
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
ssh.connect(str(ip),username=username,password=password)
stdin,stdout,stderr=ssh.exec_command("lsfcmap -nohdr -delim :")
data=stdout.readlines()
snapshots = extractSnapshots(data)
CopySnapshots = copy.copy(snapshots)

output=''
snapshots_mapped=[]

td_styling= """style='border:solid black 1px;padding:3px;border-bottom: 2px solid #e542f4;-webkit-border-radius: 5px; -moz-border-radius: 5px; border-radius: 5px'"""

#checking host mappings for all snapshots
for snapshot in snapshots:
    mappings= snapshots[snapshot][0]
    snapshot_mapped,snapshot_output=False,""
    for mapping in mappings:
        vol_mapped,vol_output = host_mappings(mapping.target,ssh)
        if vol_mapped:
            snapshot_mapped=True
            snapshot_output+='<div>'+vol_output.strip(',')+'</div>'
    if snapshot_output: output+="<tr bgcolor='#ed3d5a'><td {}><p><strong>{}</strong> has host mappings.</p> {}</td></tr>".format(td_styling,snapshot,snapshot_output)
    if snapshot_mapped:
        snapshots_mapped.append(snapshot)
        del CopySnapshots[snapshot]    

#printing all expired snapshots on terminal
snapshots = copy.copy(CopySnapshots)
if snapshots:print(bcolors.HEADER+"Below are the snapshots which will be deleted")
print("Total Expired snapshots: %d"%len(snapshots))
print(bcolors.OKBLUE)
for snapshot in snapshots:
    print(snapshot)
print(bcolors.ENDC)

#waits for 6 seconds before initiating deletion
if snapshots:
    time.sleep(6)

Notpermitted =[]
#Stopping snapshot
for snapshot in snapshots:
    standalone = snapshots[snapshot][1]
    permission_granted = confirmation_rename(snapshot,standalone,ssh=ssh,array='V7000')
    if not permission_granted:
        output+="<tr bgcolor='#96ceea'><td {}><strong>{}</strong> snapshot is not deleted since user has not premitted to delete.</td></tr>".format(td_styling,snapshot)
        del CopySnapshots[snapshot]
        continue
    stop_fcmapping(snapshot,ssh,standalone=standalone)
snapshots=copy.copy(CopySnapshots)        

if not snapshots_mapped and not snapshots:
    print(bcolors.HEADER+bcolors.BOLD+"No Expired snapshots in the array" +bcolors.ENDC)
    output+="<tr><td>No Expired Snapshots in the array</td></tr>"

if snapshots:time.sleep(10)

count=0
while CopySnapshots and count<=2:
    for snapshot in snapshots:
        for mapping in snapshots[snapshot][0]:
            if mapping_stopped(mapping.name,ssh) and volume_offline(mapping.target,ssh) and delete_volume(mapping.target,ssh):
                CopySnapshots[snapshot][0].remove(mapping)
#        print CopySnapshots[snapshot]
        if (not CopySnapshots[snapshot][0]) and (snapshots[snapshot][1] or  delete_cg(snapshot,ssh)):
            output+="<tr><td bgcolor='#5cd682' {}><strong>{}</strong> deleted</td></tr>".format(td_styling,snapshot)
            print(bcolors.OKGREEN+"{}  snapshot deleted".format(snapshot)+bcolors.ENDC)
            del CopySnapshots[snapshot]

    snapshots = copy.copy(CopySnapshots)
    count+=1

if snapshots:
    print("Below snapshots are not deleted")
    for s in snapshots:
        print(s)
        output+="<tr bgcolor='#e0862c'><td {}>{} has not been deleted</td></tr>".format(td_styling,s)

def mail(html_data):
    fromaddr = "CONA_SAA@capgemini.com" #CONA-SAA ADMIN
    toaddr="conastorage.nar@capgemini.com"
    ccaddr="prasanna.kandregula@capgemini.com"
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['cc']=ccaddr
    global arrays
    global ip
    array= arrays[ip]
    msg['Subject'] = "Expired Snapshots deletion - {}".format(array)
    msg.attach(MIMEText(html_data,'html'))
    toaddrs=[toaddr]+[ccaddr]
    server = smtplib.SMTP('161.162.144.164') #cona SMTP
    text = msg.as_string()
    print "Sending Mail..........\n"
    server.sendmail(fromaddr,toaddrs,text)
    print "Mail Sent Successfully..........\n"
    server.quit()

mail_header = """<html><body style="font-size: 14px;font-family: Arial">
	<p>Hi Team,</p>
	<p> Below is the expired Snapshot Deletion Status</p>
	<table border=1 width="700" style="border : 2px solid black; -moz-border-radius: 5px;-webkit-border-radius: 5px; font-size: 14px;font-family: Arial">"""

end='</table></body></html>'

ssh.close()                        
#db.close()
mail(mail_header+output+end)


end_mail("NACONA_STR_20199348_Expired_Snapshot_deletion","successful",aru_start,aru_t1)
