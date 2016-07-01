# pitscript

Set up both scripts' global variables (passwords, etc) before running

logfilemanager.py...

Sends email containing text of defined logfile to defined email
Usage: python logfilemanager.py

pennintouchv3.py...

If it finds any of the courses listed, sends an email to defined globals
Usage: python pennintouchv3.py <Primary Course Code> <Secondary Code 1> [Secondary Code 2] [Secondary Code 3] ...


cron.txt example:

*/10 * * * * python /home/ec2-user/pennintouchv3.py IPD 515
0 */6 * * * python /home/ec2-user/logfilemanager.py

first one is every 10 minutes
second one is every 6 hours on the 0th minute

to run:

crontab cron.txt

crontab -l to list
crontab -r to stop

