#Importing the necessary modules
import sys
from create_user_ip_file import ip_file_valid
from create_user_ip_reach import ip_reach
from th_core_create_ssh import ssh_connection
from create_user_createthread import create_threads

#Saving the list of IP addresses in ip.txt to a variable
ip_list = ip_file_valid()

#Verifying the reachability of each IP address in the list
try:
    ip_reach(ip_list)
except KeyboardInterrupt:
    print("\n\n* Program aborted by user. Exiting...\n")
    sys.exit()

#Calling threads creation function for one or multiple SSH connections
create_threads(ip_list, ssh_connection)

#End of program