# Usage: python register-script.py <Course Code 1> [Course Code 2] [Course Code 3] ...
# Format Course Codes like so: "IPD-515-001" or "MEAM-101-001". It should be LETTERS-3NUMBERS-3NUMBERS


USER_PENNKEY = "fill in here (dont delete the quotation marks)"
USER_PASSWORD = "fill in here (dont delete the quotation marks)"
GMAIL_ADDRESS = "fill in here (dont delete the quotation marks)"
GMAIL_PASSWORD = "fill in here (dont delete the quotation marks)"


############ NO MORE SETUP BELOW NEEDED ############

import requests, re, json, smtplib, sys, random
import traceback
from bs4 import BeautifulSoup
from email.MIMEMultipart import MIMEMultipart
from email.MIMEText import MIMEText
from time import strftime, sleep

downtime_waittime = 300
interval_waittime = 30

do_debug = True
file_out = 'output.html'

# Logfile params
do_log = True
logfile = 'log.txt'

# PennKey data
PIT_link = "https://medley06.isc-seo.upenn.edu/pennInTouch/jsp/fast2.do?1=2&access=student&bhcp=1"
PIT_login_data = {
  "login" : USER_PENNKEY,
  "password" : USER_PASSWORD,
  "required" : "UPENN.EDU,UPENN.EDU-PORTAL",
  "ref" : "https://pennintouch.apps.upenn.edu/pennInTouch/jsp/fast2.do?1=2&access=student&bhcp=1",
  "service" : "cosign-isc-seo-portal_prodng-0"
}

# Email data
my_email = GMAIL_ADDRESS
to_email = GMAIL_ADDRESS
my_pass = GMAIL_PASSWORD


server_suspected_down = False
server_down = False

def log(string):
	if do_log:
		with open(logfile, "a") as f:
			f.write(strftime("%Y-%m-%d %H:%M:%S") + "; " + string + "\n");

def file_output(txt):
	with open(file_out, "w") as f:
		f.write(str(txt));

def debug(string):
	if do_debug:
		print string

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

# If script is broken, it's likely these AJAX codes
# Every time PennInTouch changes something on their interface, the hardcoded values in this function need to change
# To resolve, use TamperData w/ Firefox to see what AJAX codes are being sent as you click each button
# Cross-reference those codes w/ the HTML/JS on the page
# Use http://jsonviewer.stack.hu/ to find the relevant indeces within the fastResponseJsTemp variable
def extractAJAXCodes(txt):
	debug("Getting codes")
	codes = dict()
	try:
		soup = BeautifulSoup(txt, "lxml")
		fullvar = soup.findAll(text=re.compile(r'.*fastResponseJsTemp.*'))[0]
		abc = "{" + fullvar.split("{", 1)[1].split(";", 1)[0]
		nospace = ''.join(abc.split())
		varjson = json.loads(nospace)

		keyvalues = varjson["FastResponseJs"]['ajaxElements']['AjaxMapEntry']
		for kv in keyvalues:
			if "theValue" in kv:
				value = kv["theValue"]
				if "screenElementId" in value:
					# Primary subject button
					if value["screenElementId"] == "subjectPrimary" and 'subject' not in codes:
						codes['subject'] = value['ajaxId']
					elif value["screenElementId"] == "courseNumberPrimary" and 'course' not in codes:
						codes['course'] = value['ajaxId']
					elif value["screenElementId"] == "sectionNumberPrimary" and 'section' not in codes:
						codes['section'] = value['ajaxId']
		codes['request'] = keyvalues[46]["theValue"]['ajaxId']
		codes['requestGET'] = keyvalues[46]["theKey"]['$']

		keyvalues = varjson["FastResponseJs"]['namesToClear']['AjaxMapEntry']
		#codes['requestBlank'] = keyvalues[51]["theKey"]['$'].split("_")[1]
		codes['requestBlank'] = keyvalues[52]["theKey"]['$'].split("_")[1]
		#codes['cancel'] = keyvalues[52]["theKey"]['$']
		codes['cancel'] = keyvalues[53]["theKey"]['$']
		return codes
	except:
		debug("Issues with server...")
		return None

# sends an AJAX POST request to PIT
def sendAJAXRequest(session, post_data):
	post_url = "https://pennintouch.apps.upenn.edu/pennInTouch/jsp/fast2.do?fastWebService=ajax"
	return session.post(post_url, data = post_data, allow_redirects=True, timeout=10)

# pass in AJAX response to section code POST request, get grade type argument
def getGradeTypePrimary(txt):
	varjson = json.loads(txt)
	if isinstance(varjson['AjaxResponse']['formFieldValues']['AjaxMapEntry'], dict):
		return ""
	return varjson['AjaxResponse']['formFieldValues']['AjaxMapEntry'][0]['theValue']['string']

# pass in AJAX response to section code POST request, get CU argument
def getCreditUnitPrimary(txt):
	varjson = json.loads(txt)
	if isinstance(varjson['AjaxResponse']['formFieldValues']['AjaxMapEntry'], dict):
		return varjson['AjaxResponse']['formFieldValues']['AjaxMapEntry']['theValue']['string']
	return varjson['AjaxResponse']['formFieldValues']['AjaxMapEntry'][1]['theValue']['string']

# pass in HTML of register courses page, get back the number of courses currently registered
def getNumCourses(content):
	try:
		soup = BeautifulSoup(content, "lxml")
		enrollment_table = soup.find(id="enrollments")
		debug("returning num courses")
		return len(enrollment_table.find_all("tr", { "class" : "draggable"}))
	except:
		return None

# given an AJAX response after a course code POST, tells you if the course is available
def isCodeAvailable(content, code):
	try:
		finalobj = json.loads(content)
		courselist = finalobj['AjaxResponse']['optionValues']['AjaxMapEntry'][0]['theValue']['AjaxOptionValue']
		for e in courselist:
			value = e['value']
			if str(value).isdigit():
				if int(value) == int(code):
					return True
		return False
	except:
		return None

def serverError():
	global server_down, server_suspected_down
	log("Server error!")
	debug("Server error!")
	if server_suspected_down:
		log("Sleeping for server error...")
		server_down = True
		r = random.randint(int(downtime_waittime - downtime_waittime * .1), int(downtime_waittime + downtime_waittime * .1))
		debug("Server down. Waiting " + str(r) + "s")
		sleep(r)
	else:
		server_suspected_down = True

def checkClasses(classes):
	global interval_waittime, downtime_waittime, PIT_link, server_down, server_suspected_down
	debug("Checking for classes.")
	Initial_link = "https://weblogin.pennkey.upenn.edu/login?factors=UPENN.EDU,UPENN.EDU-PORTAL&cosign-isc-seo-portal_prodng-0&https://pennintouch.apps.upenn.edu/pennInTouch/jsp/fast2.do?1=2&access=student&bhcp=1"

	while len(classes) > 0:
		debug("Starting outer loop")
		s = requests.Session()
		s.headers['User-Agent'] = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.11; rv:40.0) Gecko/20100101 Firefox/40.0"
		try:
			r = s.get(Initial_link, timeout=10) # Goes to the PennKey login page
			r = s.post("https://weblogin.pennkey.upenn.edu/login", data = PIT_login_data, allow_redirects = True, timeout=10) # Logs in, grabs cookie
			r = s.get(PIT_link, timeout=10) # Goes to the main PIT page
			r = s.get("https://pennintouch.apps.upenn.edu/pennInTouch/jsp/fast2.do?1=2&access=student&bhcp=1&bhab=1&bhqs=1", timeout=10) # Goes again (simulate redirect)
		except:
			serverError()
			continue

		debug("Initial parse")
		soup = BeautifulSoup(r.text, "lxml")
		try:
			page_code = soup.body.findAll(text="Register for courses")[0].parent.parent.get('id').split("_")[0]
		except:
			serverError()
			continue

		debug("Clicking 'Register for Courses'")
		r = s.get("https://pennintouch.apps.upenn.edu/pennInTouch/jsp/fast2.do?fastButtonId=" + page_code, timeout=10) # Clicks "Register for Courses" button

		while len(classes) > 0:
			log("Running a check")
			debug("Starting inner loop")
			codes = extractAJAXCodes(r.text) # grabs the AJAX codes we need to send the right POST requests (i.e. click the buttons)
			if codes == None:
				serverError()
				break
			else:
				server_down = False
				server_suspected_down = False
			numCourses = getNumCourses(r.content)
			#debug("CODES:") ###
			#debug(codes) ###

			# fire off all the posts
			for subjectCode in classes.keys():
				debug("Checking if " + subjectCode + " is available.")
				ajax_data = {
					"fastAjaxId": codes['subject'],
					"subjectPrimary": subjectCode
				}
				
				debug("Clicking subject")
				try:
					r = sendAJAXRequest(s, ajax_data) # Subject
				except:
					serverError()
					break
			
				for courseCode in classes[subjectCode].keys():
					debug("Checking if " + subjectCode + " " + courseCode + " is available.")
					if isCodeAvailable(r.content, courseCode):
						ajax_data = {
							"fastAjaxId": codes['course'],
							"subjectPrimary": subjectCode,
							"courseNumberPrimary": courseCode,

						}

						debug("Clicking course")
						try:
							r = sendAJAXRequest(s, ajax_data) # Course
						except:
							serverError()
							break
						to_delete = []
						for sectionCode in classes[subjectCode][courseCode]:
							debug("Checking if " + subjectCode + " " + courseCode + " " + sectionCode + " is available.")
							if isCodeAvailable(r.content, sectionCode):
								ajax_data = {
									"fastAjaxId": codes['section'],
									"subjectPrimary": subjectCode,
									"courseNumberPrimary": courseCode,
									"sectionNumberPrimary": sectionCode
								}
								debug("Clicking section")
								try:
									r = sendAJAXRequest(s, ajax_data) # Section
								except:
									serverError()
									break

								gradeTypeCode = getGradeTypePrimary(r.text)
								creditUnitCode = getCreditUnitPrimary(r.text)

								ajax_data = {
									"fastAjaxId": codes['request'],
									"subjectPrimary": subjectCode,
									"courseNumberPrimary": courseCode,
									"sectionNumberPrimary": sectionCode,
									"gradeTypePrimary":gradeTypeCode, 
									"creditUnitPrimary":creditUnitCode, 
									codes['requestBlank']:""
								}

								#debug(ajax_data) ###
								debug("Clicking request")
								try:
									r = sendAJAXRequest(s, ajax_data) # Request
									r = s.get("https://pennintouch.apps.upenn.edu/pennInTouch/jsp/fast2.do?fastButtonId=" + codes['requestGET'], timeout=10) # Grabs the GET response
									codes = extractAJAXCodes(r.text)
								except:
									serverError()
									break
								txt = ""
								if (getNumCourses(r.content) > numCourses):
									txt = "Successful registration: " + subjectCode + " " + courseCode + " " + sectionCode
									log(txt)
									debug("Successful registration")
								else:
									txt = "Unsuccessful registration: " + subjectCode + " " + courseCode + " " + sectionCode
									log(txt)
									debug("Failed registration")
								#file_output(r.content) ###
								sendEmail(txt, r.content)
								debug("Removing " + subjectCode + " " + courseCode + " " + sectionCode + " from classes.")
								to_delete.append(sectionCode)
							else:
								debug("Section code not available!")
						for val in to_delete: # deletes registered courses from the list
							classes[subjectCode][courseCode].remove(val)
							if len(classes[subjectCode][courseCode]) == 0:
								del classes[subjectCode][courseCode]
								if len(classes[subjectCode]) == 0:
									del classes[subjectCode]
					else:
						debug("Course code not available!")
			r = random.randint(int(interval_waittime - interval_waittime * .1), int(interval_waittime + interval_waittime * .1))
			debug("Just checked. Waiting " + str(r) + "s")
			sleep(r)
			debug("Clicking cancel")
			try:
				r = s.get("https://pennintouch.apps.upenn.edu/pennInTouch/jsp/fast2.do?fastButtonId=" + codes['cancel'], timeout=10) # Clicks cancel button
			except:
				serverError()
				break

def get_classes(args):
	classes = dict()
	for arg in args:
		codes = arg.split('-')
		primaryCode = codes[0].upper()
		secondaryCode = codes[1]
		tertiaryCode = codes[2]
		if primaryCode not in classes:
			classes[primaryCode] = dict()
		if secondaryCode not in classes[primaryCode]:
			classes[primaryCode][secondaryCode] = []
		classes[primaryCode][secondaryCode].append(tertiaryCode)
	return classes


def main():		
	classes = dict()
	try:
		if len(sys.argv) < 2:
			print "Bad command line arguments"
			print "Usage: python register-script.py <Course Code 1> [Course Code 2] [Course Code 3] ..."
			print "Format Course Codes like so: IPD-515-001 or MEAM-101-001. It should be LETTERS-3NUMBERS-3NUMBERS"
			sys.exit()
		classes = get_classes(sys.argv[1:]) # passing course codes
		print classes
		checkClasses(classes)
	except:
		tb_txt = traceback.format_exc()
		print "ERROR. " + tb_txt
		log("SOMETHING WENT WRONG! " + tb_txt + "\n")

if __name__ == "__main__": 
	main()



	