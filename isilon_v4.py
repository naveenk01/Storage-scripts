import paramiko
import os.path
import time
import sys
import re
import threading
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# SMTP Server Configuration
smtp_server = "10.127.80.70" # Replace with your SMTP server
smtp_port = 25 # Use the appropriate port, e.g., 25, 587, etc.
#smtp_user = "your_email@yourdomain.com" # Your email address
#smtp_password = "your_password" # Your email password

# Email configuration
from_address = "CTC-HCLStorage@cantire.com" # Sender email address
to_address = "CTC-HCLStorage@cantire.com" # Recipient email address
subject = "Isilon Webui & papi services "

# Hardcoded file paths
user_file = "C:/Users/naveen.gowda/Python/create_user_scripts_nav/create_user_user_file.txt"
cmd_file = "C:/Users/naveen.gowda/Python/create_user_scripts_nav/svc_command.txt"

# Verifying files (as per your original script)
if not os.path.isfile(user_file):
    print(f"\n* File {user_file} does not exist. Exiting...\n")
    sys.exit()

if not os.path.isfile(cmd_file):
    print(f"\n* File {cmd_file} does not exist. Exiting...\n")
    sys.exit()

# List of IP addresses
ipaddresses = ['10.126.82.135', '10.18.253.136']

# Thread-safe log storage
output_logs = []
print_lock = threading.Lock()

def ssh_connection(ip):
    global cmd_file, user_file
    try:
        with open(user_file, 'r') as selected_user_file:
            line = selected_user_file.readline().strip()
            if ',' in line:
                username, password = line.split(',')[0].strip(), line.split(',')[1].strip()
            else:
                with print_lock:
                    output_logs.append(f"<p><strong>{ip}:</strong> Error - Invalid format in user file.</p>")
                return

        # Establish SSH connection
        session = paramiko.SSHClient()
        session.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        session.connect(ip, username=username, password=password)
        connection = session.invoke_shell()

        # Send commands
        with open(cmd_file, 'r') as selected_cmd_file:
            for line_count, each_line in enumerate(selected_cmd_file.readlines(), start=1):
                connection.send(each_line + '\n')
                time.sleep(120 if line_count % 2 == 0 else 2)

        # Get command output
        router_output = connection.recv(65535).decode("utf-8")
        
        with print_lock:
            # Log formatted output for each IP
            output_logs.append(f"<h3>Device {ip} Output</h3><pre>{router_output}</pre>")
            if re.search("% Invalid input", router_output):
                output_logs.append(f"<p style='color:red;'><strong>{ip}:</strong> IOS syntax error detected.</p>")
            else:
                output_logs.append(f"<p style='color:green;'><strong>{ip}:</strong> Execution successful.</p>")

        session.close()

    except paramiko.AuthenticationException:
        with print_lock:
            output_logs.append(f"<p><strong>{ip}:</strong> Authentication failed. Please check credentials.</p>")

threads = [threading.Thread(target=ssh_connection, args=(ip,)) for ip in ipaddresses]
for thread in threads:
    thread.start()
for thread in threads:
    thread.join()

# HTML email content
html_content = f"""
<html>
<head>
    <style>
        body {{
            font-family: Arial, sans-serif;
            line-height: 1.6;
        }}
        h2 {{
            color: #2e6c80;
        }}
        p {{
            font-size: 14px;
        }}
        pre {{
            background-color: #f4f4f4;
            padding: 10px;
            border: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <h2>Service restart Summary</h2>
    {''.join(output_logs)}
</body>
</html>
"""

# Send the email
def send_email(html_content):
    # Set up the email message
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address

    # Attach HTML content
    part = MIMEText(html_content, "html")
    msg.attach(part)

    # Connect to SMTP server and send email
    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            #server.login(smtp_user, smtp_password)
            server.sendmail(from_address, to_address, msg.as_string())
        print("Email sent successfully.")
    except Exception as e:
        print(f"Failed to send email: {e}")

# Call the function to send the email
send_email(html_content)
print("All SSH connections and email notification complete.")