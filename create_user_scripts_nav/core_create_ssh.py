import paramiko
import os.path
import time
import sys
import re
cmd_file = input("\n# Enter commands file path and name (e.g. D:\MyApps\myfile.txt): ")
if os.path.isfile(cmd_file) == True:
    print("\n* Command file is valid :)\n")
else:
    print("\n* File {} does not exist :( Please check and try again.\n".format(cmd_file))
    sys.exit()
    #Creating SSH CONNECTION
ipaddresses=['10.18.252.90']
def ssh_connection(ip):
    global cmd_file
    try:
    #Logging into device
        session = paramiko.SSHClient()
        session.set_missing_host_key_policy(paramiko.AutoAddPolicy())       
        session.connect(ip, username = 'navineeth', password = 'Welcome@123')
        connection = session.invoke_shell()	
 
        selected_cmd_file = open(cmd_file, 'r')
            
        #Starting from the beginning of the file
        selected_cmd_file.seek(0)
        
        #Writing each line in the file to the device
        for each_line in selected_cmd_file.readlines():
            connection.send(each_line + '\n')
            time.sleep(2)
       
        
        #Closing the command file
        selected_cmd_file.close()
        
        #Checking command output for IOS syntax errors
        router_output = connection.recv(65535)
        
        
        if re.search(b"% Invalid input", router_output):
            print("* There was at least one IOS syntax error on device {} :(".format(ip))
            
        else:
            print("\nDONE for device {} :)\n".format(ip))
            
        #Test for reading command output
       
        print(str(router_output) + "\n")
        x = str(router_output)
        y = list(x)
        print(x)
        print(y)
        with open(r'C:\Users\naveen.gowda\sales.txt', 'w') as fp:
            fp.write("\n".join(str(item) for item in x))
            print('Done')
      
        
        #Closing the connection
        session.close()
     
    except paramiko.AuthenticationException:
        print("* Invalid username or password :( \n* Please check the username/password file or the device configuration.")
        print("* Closing program... Bye!")
for ip in ipaddresses:
    ssh_connection(ip)