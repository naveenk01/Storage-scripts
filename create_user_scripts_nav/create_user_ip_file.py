import os.path
import sys
def ip_file_valid():
    ip_list_valid =[]
    ip_file = input("\n# Enter IP file path and name (e.g. D:\MyApps\myfile.txt): ")
    if os.path.isfile(ip_file) == True:
        print("\n* IP file is valid :)\n")
    else:
        print("\n* File {} does not exist :( Please check and try again.\n".format(ip_file))
        sys.exit()
    selected_ip_file = open(ip_file, 'r')
    selected_ip_file.seek(0)
    ip_list = selected_ip_file.readlines()
    selected_ip_file.close()
    for ip in ip_list:
        ip = ip.rstrip("\n")
        ip_list_valid.append(ip)
    #print(ip_list_valid)
    return ip_list_valid