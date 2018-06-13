#!/usr/bin/env python
from __future__ import print_function
import requests
import sys
import argparse
import os.path
from io import StringIO
from lxml import etree
import random
import time

# Range of time to wait between requests
START_RANGE = 1 
END_RANGE = 2

# cis post endpoint
URL = "https://egov.uscis.gov/casestatus/mycasestatus.do"
LOGIN_URL = "https://egov.uscis.gov/casestatus/login.do"

# construct the argument parse and parse the arguments
ap = argparse.ArgumentParser()
ap.add_argument("-i", "--infile", default="receipts.txt", help="name of input file")
ap.add_argument("-o", "--outfile", default="receipts_and_status.txt", help="name of output file")
ap.add_argument("-u", "--username", default="", help="login username")
ap.add_argument("-p", "--password", default="", help="login password")
args = vars(ap.parse_args())

# make sure input file exists
fname = args["infile"]
if (not os.path.isfile(fname)):
    print("File {} does not exist. Check the file or specify another using the -f parameter.".format(fname))
    sys.exit()

# read case numbers into list
with open(fname) as f:
    content = f.readlines()
    numbers = [x.strip() for x in content]

# Use a session so cookies are captured and reused
with requests.Session() as session:

    # Login to the system first
    login_data = {
        "userNameRules": "userNameRequired",
        "changeLocale": "",
        "username": args["username"],
        "password": args["password"]
    }
    
    resp = session.post(URL, data=login_data)
    if resp.status_code != 200:
        print("Login failed with status code {}, exiting...".format(resp.status_code))
        sys.exit(1)

    # Now process the data
    stop_count = len(numbers) - 1

    lookedup = {}
    for i, number in enumerate(numbers):

        resp = session.get(URL + "?appReceiptNum={}".format(number))
        root = etree.parse(StringIO(resp.text), etree.HTMLParser())
		
        # Look for an error message
        error = root.xpath('//div[@id="formErrorMessages"]/h4/text()')
        if len(error) > 0 and error[0].startswith("Validation Error(s)"):
            message = "Not found or other error"
            details = ""
            row = "{}|{}|{}".format(number, message, details)
            with open(args["outfile"], 'a') as outfile:
                outfile.write(row)
        else:

            text = root.xpath("/html/body/div[2]/form/div/div[1]/div/div/div[2]/div[3]/h1/text()")
            text_p = root.xpath("/html/body/div[2]/form/div/div[1]/div/div/div[2]/div[3]/p//text()")
            try:
                message = text[0]
                details = ''.join(text_p)
            except IndexError:
                message = 'Not found or other error'
                details = ""

            if number in lookedup:
                print("{} is already in the dictionary.".format(number))
                row = "{}|already in dictionary|".format(number)
                with open(args["outfile"], 'a') as outfile:
                    outfile.write(row)
            else:
                row = "{}|{}|{}".format(number, message, details)
                with open(args["outfile"], 'a') as outfile:
                    outfile.write(row)

        x = i + 1
        y = stop_count + 1
        percent = round((x / y) * 100)
        seconds = (y - x) * (((END_RANGE - START_RANGE) / 2) + START_RANGE)
        m, s = divmod(seconds, 60)
        h, m = divmod(m, 60)

        if h > 0:
            est = "{:.0f} hour{}".format(h, "s" if h != 1 else "")
            if m > 0:
                est += ", {:.0f} minute{}".format(m, "s" if m != 1 else "")
        elif m > 0:
            est = "{:.0f} minute{}".format(m, "s" if m != 1 else "")
        else:
            est = "{:.0f} second{}".format(s, "s" if s != 1 else "")
        print("{}% completed - at line {} of {}. Estimated {} remaining".format(percent, x, y, est))

        # Wait a random amount of time, don't wait if last item in list
        if i < stop_count:
            time_range = random.randrange(START_RANGE, END_RANGE)
            print("Waiting {0:.2f} seconds before querying again...".format(time_range))
            time.sleep(time_range)
