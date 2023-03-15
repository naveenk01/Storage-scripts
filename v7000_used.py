import paramiko
import os.path
import time
import sys
import re
import csv
import pandas as pd
volume_file = input("\n# Enter commands file path and name (e.g. D:\MyApps\myfile.txt): ")
if os.path.isfile(volume_file) == True:
    print("\n* volume file is valid :)\n")
else:
    print("\n* File {} does not exist :( Please check and try again.\n".format(volume_file))
    sys.exit()
    #Creating SSH CONNECTION
ipaddresses=['10.126.81.100']
def ssh_connection(ip):
    global cmd_file
    try:
    #Logging into device
        session = paramiko.SSHClient()
        session.set_missing_host_key_policy(paramiko.AutoAddPolicy())       
        session.connect(ip, username = 'navineeth', password = 'Welcome@123')
        connection = session.invoke_shell() 
 
        selected_cmd_file = open(volume_file, 'r')
            
        #Starting from the beginning of the file
        selected_cmd_file.seek(0)
        
        #Writing each line in the file to the device
        for each_line in selected_cmd_file.readlines():
            connection.send("lsvdisk" +" "+ each_line + '\n')
            time.sleep(4)
       
        
        #Closing the command file
        selected_cmd_file.close()
        
        #Checking command output for IOS syntax errors
        router_output = connection.recv(65535)
        
        
        if re.search(b"% Invalid input", router_output):
            print("* There was at least one IOS syntax error on device {} :(".format(ip))
            
        else:
            print("\nDONE for device {} :)\n".format(ip))

        
        x = router_output.decode("utf-8")

        y = re.findall("used_capacity(\s)+(.+?)(\s)", x)
        new_lst = [z[1] for z in y]
        evens = new_lst[0::2]
        evens = pd.DataFrame(evens)
        print(evens)
        evens.to_csv("nav.csv", index = False)
 
      
        #Closing the connection
        session.close()
     
    except paramiko.AuthenticationException:
        print("* Invalid username or password :( \n* Please check the username/password file or the device configuration.")
        print("* Closing program... Bye!")
for ip in ipaddresses:
    ssh_connection(ip)