##****************************************************************************
##***********************Author: Foivos Michelinakis**************************
##**( michelinakis.foivos@gmail.com  ///   foivos.michelinakis@imdea.org   )**
##work done as part of the class "Platforms for network communities" 2012-2013
##***************University: "Universidad Carlos III de Madrid"**************
##****************************************************************************


import httplib
from bs4 import BeautifulSoup
import urllib
import urllib2
import string
import random
import json
import sys

class student():
  
    def __init__(self, AA,):
        self.cookie=""
        emailprefix = "testemail"
        emailserverprefix = "testserveremail"
        nameprefix = "testname"
        surnameprefix = "testsurname"
        self.AA = AA
        self.email = emailprefix + str(self.AA) + "%40" + emailserverprefix + str(self.AA) + ".com" #name of the instance
        self.name = nameprefix + str(self.AA) + " " + surnameprefix + str(self.AA) #email of the instance
        print "new user created"
        print "name " + self.name
        print "email " +self.email
        print ""

    def Register(self):
        #Register page
        global conn
        conn = httplib.HTTPConnection("localhost:" + str(sys.argv[1]))
        path = "/_ah/login?action=Login&continue=http%3A%2F%2Flocalhost%3A8082%2Fregister&email=" + self.email + "&admin=False"
        conn.request("GET", path)
        r1 = conn.getresponse()
        self.cookie = r1.getheader("set-cookie")
        
        #Register page 2, you give a name
        conn.request("GET", "/register", None, {"Cookie" : self.cookie})
        r1 = conn.getresponse()
        
        text = r1.read()
        if (int(r1.status) == 200):
            soup = BeautifulSoup(text)
            
            
            for link in soup.find_all('input'):
                if (link.get('name') == "xsrf_token"):
                    token = link.get('value')
         
            
            # last part of Register process (a page about forums)
            params = urllib.urlencode({'xsrf_token': token, 'form01': self.name})
            conn.request("POST", "/register", params , {"Cookie" : self.cookie})
            
            r1 = conn.getresponse()
            text = r1.read()
        print self.name + " has been Registered!"
    
    def ShowClasses(self):
        #the page where all the classes are. Since it does not populate the datastore, this method is virtuallu useless
        conn.request("GET", "/course", None, {"Cookie" : self.cookie})
        r1 = conn.getresponse()
        text = r1.read()

    def PreAss(self):
        #preasses class
        
        #***************************WARNING****************************************************

        #you can not submit the answers right away. You have to first browse the assesment page
        #in order to get the xsrf token and then vistit the submit page, including in the answer the token
        
        conn.request("GET", "/assessment?name=Pre", None, {"Cookie" : self.cookie})
        r1 = conn.getresponse()
        text = r1.read()
        temp = text[text.find("assessmentXsrfToken =")+22:]
        temp = temp[:temp.find(";")]
        xsrfToken = temp[1:-1]
        #print "Pre ass page"
        
        #question0
        answer0 = random.randrange(0,5)
        if answer0 == 2:
            correct0 = "true"
        else:
            correct0 = "false"
        #question1
        answer1 = random.randrange(0,3)
        if answer1 == 0:
            correct1 = "true"
        else:
            correct1 = "false"
        #question2
        answer2 = "sunris"
        answer2a = random.choice(string.ascii_letters)
        answer2 = answer2 + answer2a
        if answer2 == "sunrise":
            correct2 = "true"
        else:
            correct2 = "false"
        #question3
        answer3 = "354+65"
        answer3a = str(random.randrange(0,10))
        answer3 = answer3 + answer3a
        if answer3a == "1":
            correct3 = "true"
        else:
            correct3 = "false"
        score = 0
        if correct0 == "true":
            score = score + 1
        if correct1 == "true":
            score = score + 1
        if correct2 == "true":
            score = score + 1
        if correct3 == "true":
            score = score + 1
        score = str(25 * score) + str(".00")
        userInput = []
        userInput.append({"index":0,"type":"choices","value":answer0,"correct":correct0})
        userInput.append({"index":1,"type":"choices","value":answer1,"correct":correct1})
        userInput.append({"index":2,"type":"string","value":answer2,"correct":correct2})
        userInput.append({"index":3,"type":"regex","value":answer3,"correct":correct3})
            
        params = urllib.urlencode({"assessment_type":"Pre","score":score,"answers":json.dumps(userInput),'xsrf_token': xsrfToken})
        conn.request("POST", "/answer", params , {"Cookie" : self.cookie})
        #print "pre ans page"
        r1 = conn.getresponse()
        text = r1.read()
        print self.name + " has completed Pre ass! The score is" + str(score)

    def MidAss(self):
        #mid asses class
        
        #***************************WARNING****************************************************

        #you can not submit the answers right away. You have to first browse the assesment page
        #in order to get the xsrf token and then vistit the submit page, including in the answer the token
        
        
        
        conn.request("GET", "/assessment?name=Mid", None, {"Cookie" : self.cookie})
        r1 = conn.getresponse()
        text = r1.read()
        temp = text[text.find("assessmentXsrfToken =")+22:]
        temp = temp[:temp.find(";")]
        xsrfToken = temp[1:-1]
        #print "Mid ass page"

        #question0
        answer0 = random.randrange(0,5)
        if answer0 == 0:
            correct0 = "true"
        else:
            correct0 = "false"
        #question1
        answer1 = random.randrange(0,3)
        if answer1 == 1:
            correct1 = "true"
        else:
            correct1 = "false"
        #question2
        answer2 = "-kenne"
        answer2a = random.choice(string.ascii_letters)
        answer2 = answer2 + answer2a
        if answer2 == "-kennel":
            correct2 = "true"
        else:
            correct2 = "false"
        #question3
        answer3 = "define: brindl"
        answer3a = random.choice(string.ascii_letters)
        answer3 = answer3 + answer3a
        if answer3a == "define: brindle":
            correct3 = "true"
        else:
            correct3 = "false"
        #question4
        answer4 = random.randrange(0,5)
        if answer4 == 3:
            correct4 = "true"
        else:
            correct4 = "false"
        score = 0
        if correct0 == "true":
            score = score + 1
        if correct1 == "true":
            score = score + 1
        if correct2 == "true":
            score = score + 1
        if correct3 == "true":
            score = score + 1
        if correct4 == "true":
            score = score + 1
        score = str(20 * score) + str(".00")
        userInput = []
        userInput.append({"index":0,"type":"choices","value":answer0,"correct":correct0})
        userInput.append({"index":1,"type":"choices","value":answer1,"correct":correct1})
        userInput.append({"index":2,"type":"string","value":answer2,"correct":correct2})
        userInput.append({"index":3,"type":"regex","value":answer3,"correct":correct3})
        userInput.append({"index":4,"type":"choices","value":answer4,"correct":correct4})
            
        params = urllib.urlencode({"assessment_type":"Mid","score":score,"answers":json.dumps(userInput),'xsrf_token': xsrfToken})
        conn.request("POST", "/answer", params , {"Cookie" : self.cookie})
        #print "Mid ans page"
        r1 = conn.getresponse()
        text = r1.read()
        print self.name + " has completed Mid ass! The score is" + str(score)

    def FinAss(self):
              
         #Fin asses class
        
        #***************************WARNING****************************************************

        #you can not submit the answers right away. You have to first browse the assesment page
        #in order to get the xsrf token and then vistit the submit page, including in the answer the token
        
        
        conn.request("GET", "/assessment?name=Fin", None, {"Cookie" : self.cookie})
        r1 = conn.getresponse()

        text = r1.read()
        temp = text[text.find("assessmentXsrfToken =")+22:]
        temp = temp[:temp.find(";")]
        xsrfToken = temp[1:-1]
        #print "Fin ass page"
        
        #question0
        answer0 = random.randrange(0,5)
        if answer0 == 2:
            correct0 = "true"
        else:
            correct0 = "false"
        #question1
        answer1 = random.randrange(0,5)
        if answer1 == 3:
            correct1 = "true"
        else:
            correct1 = "false"
        #question2
        answer2 = random.randrange(0,5)
        if answer2 == 1:
            correct2 = "true"
        else:
            correct2 = "false"
        
        
        #question3
        answer3 = "existe um re"
        answer3a = random.choice(string.ascii_letters)
        answer3 = answer3 + answer3a + "?"
        if answer3 == "existe um rest?":
            correct3 = "true"
        else:
            correct3 = "false"
        
        #question4
        answer4 = "existe um re"
        answer4a = random.choice(string.ascii_letters)
        answer4 = answer4 + answer4a + "?"
        if answer4 == "existe um rest?":
            correct4 = "true"
        else:
            correct4 = "false"
        
        
        #question5
        answer5 = "7."
        answer5a = str(random.randrange(0,10))
        answer5 = answer5 + answer5a
        if answer5 == "7.9":
            correct5 = "true"
        else:
            correct5 = "false"
        
        #question6
        answer6 = random.randrange(0,5)
        if answer6 == 0:
            correct6 = "true"
        else:
            correct6 = "false"
        
        
        
        score = 0
        if correct0 == "true":
            score = score + 1
        if correct1 == "true":
            score = score + 1
        if correct2 == "true":
            score = score + 1
        if correct3 == "true":
            score = score + 1
        if correct4 == "true":
            score = score + 1
        if correct5 == "true":
            score = score + 1
        if correct6 == "true":
            score = score + 1
        score = str(14.29 * score)
        userInput = []
        userInput.append({"index":0,"type":"choices","value":answer0,"correct":correct0})
        userInput.append({"index":1,"type":"choices","value":answer1,"correct":correct1})
        userInput.append({"index":2,"type":"choices","value":answer2,"correct":correct2})
        userInput.append({"index":3,"type":"string","value":answer3,"correct":correct3})
        userInput.append({"index":4,"type":"regex","value":answer4,"correct":correct4})
        userInput.append({"index":5,"type":"numeric","value":float(answer5),"correct":correct5})
        userInput.append({"index":6,"type":"choices","value":answer6,"correct":correct6})
            
        params = urllib.urlencode({"assessment_type":"Fin","score":score,"answers":json.dumps(userInput),'xsrf_token': xsrfToken})
        conn.request("POST", "/answer", params , {"Cookie" : self.cookie})
        #print "Fin ans page"
        r1 = conn.getresponse()
        text = r1.read()
        print self.name + " has completed Fin ass! The score is" + str(score)

    def YoutubeEvents(self,unit,lesson):
            
        #**************************************************************************
        #***********************generate random youtube events.********************
        #**************************************************************************


        #Warning!! Do not submit the answers right away. first visit the page of the video, in order
        #to get the video Id and then send the answers to the server.
        subdirectory = "/unit?unit=" + str(unit) + "&lesson=" + str(lesson)
        conn.request("GET", subdirectory, None, {"Cookie" : self.cookie})
        r1 = conn.getresponse()
        temp = r1.read()
        temp = temp[temp.find("<div id=\"videoid\" class=")+23:]
        temp = temp[:temp.find("/>")]
        VideoID = temp[1:-1]
        VideoDuration = 400
        numOfEvents = random.randrange(0,10)
        if (numOfEvents > 0):
            params = urllib.urlencode({"video":VideoID,"event":"started"})
            conn.request("POST", "/youtubeevent", params , {"Cookie" : self.cookie})
            r1 = conn.getresponse()
        for i in range(1,numOfEvents):
            timeStart = 0
            timeEnd = 0
            typeOfEvent = random.randrange(1,4)
            if (typeOfEvent == 1):
                typeOfEvent = "forward"
                timeStart = random.random() * VideoDuration * 0.8
                timeEnd = timeStart + random.random() * (VideoDuration - timeStart)
                params = urllib.urlencode({"video":VideoID,"event":typeOfEvent,"info":json.dumps([{"timeStart":timeStart,"timeEnd":timeEnd}])})
                print "forward event"
                conn.request("POST", "/youtubeevent", params , {"Cookie" : self.cookie})
                r1 = conn.getresponse()
            if (typeOfEvent == 2):
                typeOfEvent = "rewind"
                timeStart = random.random() * VideoDuration
                timeEnd =  random.random() * (VideoDuration - timeStart)
                params = urllib.urlencode({"video":VideoID,"event":typeOfEvent,"info":json.dumps([{"timeStart":timeStart,"timeEnd":timeEnd}]) })
                print "rewind event"
                conn.request("POST", "/youtubeevent", params , {"Cookie" : self.cookie})
                r1 = conn.getresponse()
            if (typeOfEvent == 3):
                typeOfEvent = "pause"
                time = random.random() * VideoDuration
                params = urllib.urlencode({"video":VideoID,"event":typeOfEvent,"info":json.dumps([{"time":time}]) })
                conn.request("POST", "/youtubeevent", params , {"Cookie" : self.cookie})
                print "pause event"
                r1 = conn.getresponse()
        if (numOfEvents > 0 and random.randrange(1,4) > 2):
            params = urllib.urlencode({"video":VideoID,"event":"ended"})
            conn.request("POST", "/youtubeevent", params , {"Cookie" : self.cookie})
            r1 = conn.getresponse()
        print self.name + " has generated " + str(numOfEvents) + " Youtube events for unit " + str(unit) + " and lesson " + str(lesson)

    def Login(self):
        #Login page
        global conn
        conn = httplib.HTTPConnection("localhost:" + str(sys.argv[1]))
        path = "http://localhost:" + str(sys.argv[1]) + "/_ah/login?email=" + self.email + "&action=Login&continue=http%3A%2F%2Flocalhost%3A8083%2Fpreview"
        conn.request("GET", path)
        r1 = conn.getresponse()
        self.cookie = r1.getheader("set-cookie")
        print self.name + " has logged in! "

    def Logout(self):
        #Logout page
        
        path = "http://localhost:" + str(sys.argv[1]) + "/_ah/login?continue=http%3A//localhost%3A8083/course&action=Logout"
        conn.request("GET", path, None , {"Cookie" : self.cookie})
        r1 = conn.getresponse()
        self.cookie = ""
        print self.name + " has logged out! "




#write your code below this line
#example program (see documentation for more information)

students = []
for i in range(2222221,2222225):
    students.append(student(i))
for StudentElement in students:
    StudentElement.Register()
    StudentElement.PreAss()
    StudentElement.MidAss()
    StudentElement.FinAss()
    for le in range(1,7):
        StudentElement.YoutubeEvents(1,le)
    for le in range(1,6):
        StudentElement.YoutubeEvents(2,le)
    for le in range(1,6):
        StudentElement.YoutubeEvents(3,le)
    for le in range(1,6):
        StudentElement.YoutubeEvents(4,le)
    for le in range(1,6):
        StudentElement.YoutubeEvents(5,le)
    for le in range(1,4):
        StudentElement.YoutubeEvents(6,le)
    
    StudentElement.Logout()
