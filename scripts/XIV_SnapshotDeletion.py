from mail_aru import start_mail,end_mail

aru_start,aru_t1=start_mail("NACONA_STR_20199348_Expired_Snapshot_deletion")


import os, subprocess,sys,time
from expiredSnap import *
from storage_decrypt import decryption
from email.message import Message
import smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText


xiv_ip = sys.argv[1]
xiv_user = sys.argv[2]
xiv_pwd = sys.argv[3]

class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

out = subprocess.Popen(
             ['/root/IBM_Storage_Extended_CLI/xcli', '-m', xiv_ip, '-u',xiv_user, '-p', xiv_pwd,
               'vol_list', '-s', '-t', 'name,creator,sg_name,snapshot_of' ],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
data = out.stdout.readlines()
snapshots = {}


for line in data[1:]:
    name,creator,sg_name,snapshot_of= line.split(',')
    name,creator,sg_name,snapshot_of= name.strip('"'),creator.strip('"'),sg_name.strip('"'),snapshot_of.strip('"\n')
    if creator=='':  # to remove last replicated snapshots
        continue
    elif name.startswith("sra_synced_"):
        continue
    elif sg_name =='' and snapshot_of !='':
        snapshots[name]=([name],True)
    elif sg_name!='' and snapshot_of != '':
        if sg_name in snapshots:
            snapshots[sg_name][0].append(name)
        else:
            snapshots[sg_name]= ([name],False)

expired_snapshots = {}

def vol_mapping(volume):
    out = subprocess.Popen(
        ['/root/IBM_Storage_Extended_CLI/xcli', '-m', xiv_ip, '-u',xiv_user, '-p', xiv_pwd,
        'vol_mapping_list', 'vol={}'.format(volume) ,'-t','host' ],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    data = out.stdout.readlines()
    if data[0].strip('"\n') == 'This volume is not mapped':
        return (False,'')
    hosts=''
    print(volume+' is mapped to hosts')
    for line in data[1:]:
        host = line.strip('"\n')
        hosts+=host+','
        print(host)
    hosts=hosts.strip(',')
    return (True,hosts+'.')

AllSnapshotsMapped = False

output=''
for snapshot in snapshots:
    snapshot_mappings,standalone= snapshots[snapshot]
    mapped_snapshots=False
#    if snapshot.startswith("sra_synced_"):
#        continue
    expired_response= expired(snapshot)
    print(expired_response)
    if expired_response=='Not a valid Expired date format':
        print("{} doesn't have a valid expired date format".format(snapshot))
        expired_response= confirmation_rename(snapshot,standalone,None,'XIV',xiv_ip,xiv_user,xiv_pwd)
    if expired_response is True:
        output_here=''
        print(bcolors.OKBLUE+snapshot+bcolors.ENDC)
        for snapshot_mapping in snapshot_mappings:
            #print(bcolors.OKBLUE+snapshot_mapping+bcolors.ENDC)
            host_mappings,hosts = vol_mapping(snapshot_mapping)
            if host_mappings:
                output_here+="<p>{} mapped to {}</p>".format(snapshot_mapping,hosts)
                mapped_snapshots=True
                AllSnapshotsMapped=True
            else:
                pass
               # print("no mappings for volume {}".format(snapshot_mapping))
        if not mapped_snapshots:
            expired_snapshots[snapshot] = snapshots[snapshot]
        else:
            if standalone:
                output+="<tr bgcolor='#ed3d5a'><td>{}</td></td>".format(output_here)
            else:
                output+="<tr bgcolor='#ed3d5a'><td><p>{} is mapped.</p>{}".format(snapshot,output_here)

if not AllSnapshotsMapped and not expired_snapshots:
    output+="<tr><td>No Expired snapshots in the array</td></tr>" 

print(bcolors.OKBLUE)
for snapshot in expired_snapshots:
    print(snapshot)
print(bcolors.ENDC)

time.sleep(10)

for snapshot in expired_snapshots:
    standalone= expired_snapshots[snapshot][1]
    confirmed=confirmation_rename(snapshot,standalone,None,'XIV',xiv_ip,xiv_user,xiv_pwd)
    if not confirmed:
        print("{} not deleted since it was not confirmed.".format(snapshot))
        output+="<tr bgcolor='#96ceea'><td>{} not deleted since it was not confirmed for deletion</tr></td>".format(snapshot)
        continue
    if confirmed and standalone:
        out = subprocess.Popen(
        ['/root/IBM_Storage_Extended_CLI/xcli', '-m', xiv_ip, '-u',xiv_user, '-p', xiv_pwd,
        'snapshot_delete', 'snapshot={}'.format(snapshot) ],stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    elif confirmed and not standalone:
        out = subprocess.Popen(
        ['/root/IBM_Storage_Extended_CLI/xcli', '-m', xiv_ip, '-u',xiv_user, '-p', xiv_pwd,
        'snap_group_delete', 'snap_group={}'.format(snapshot) ],stdout=subprocess.PIPE, stderr=subprocess.PIPE)             
    output_here,error =out.stdout.readlines(), out.stderr.readlines()
    output_here,error = [line.strip('"\n') for line in output_here if line.strip('"\n')!='' ],[line.strip('"\n') for line in error if line.strip('"\n')!='' ]
    print(error)
    print(output_here)
    if output_here[0]=='Command executed successfully.':
        output+="<tr bgcolor='#51bc5a'><td>{} deleted.</tr></td>".format(snapshot)
    else:
        output+="<tr bgcolor='#a31303'><td>{} not deleted {}</tr></td>".format(snapshot,"\t".join(error))

def mail(html_data):
    fromaddr = "CONA_SAA@capgemini.com" #CONA-SAA ADMIN
    toaddr="conastorage.nar@capgemini.com"
    ccaddr="prasanna.kandregula@capgemini.com"
    msg = MIMEMultipart()
    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['cc']=ccaddr
    #global arrays
    #global ip
    #array= arrays[ip]
    msg['Subject'] = "Expired Snapshots deletion - XIV"#.format(array)
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
	<p> Below is the expired Snapshots Deletion Status</p>
    <table border=1 width="700" style="border : 1px solid black; font-size: 14px;font-family: Arial">"""


end='</table></body></html>'

mail(mail_header+output+end)

end_mail("NACONA_STR_20199348_Expired_Snapshot_deletion","successful",aru_start,aru_t1)
