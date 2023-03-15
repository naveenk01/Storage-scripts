#Checking commands file
#Prompting user for input - COMMANDS FILE
cmd_file = input("\n# Enter commands file path and name (e.g. D:\\MyApps\\myfile.txt): ")
 
#Verifying the validity of the COMMANDS FILE
if os.path.isfile(cmd_file) == True:
    print("\n* Command file is valid :) Sending command(s) to device(s)...\n")
 
else:
    print("\n* File {} does not exist :( Please check and try again.\n".format(cmd_file))
    sys.exit()