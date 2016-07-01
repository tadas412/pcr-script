import os, smtplib
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from time import strftime

# Email data
my_email = "from email"
to_email = "to email"
my_pass = "password"
logfile = 'log.txt'

def sendEmail(subject, message):
	msg = MIMEMultipart()
	msg['From'] = my_email
	msg['To'] = to_email
	msg['Subject'] = subject
	body = message
	msg.attach(MIMEText(body, 'plain'))

	server = smtplib.SMTP('smtp.gmail.com', 587)
	server.starttls()
	server.login(my_email, my_pass)

	text = msg.as_string()
	server.sendmail(my_email, to_email, text)
	server.quit()

def main():
	with open(logfile, 'rU') as f:
		content = f.read()
	sendEmail("Logfile for PIT Script", content)
	os.remove(logfile)

if __name__ == "__main__": 
	main()