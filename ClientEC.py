import sys
import socket
import base64


DATASIZE = 256
MAILFROMSTATE = 1
RCPTSTATE = 2
DATASTATE = 3
SENDMAILSTATE = 4
QUIT = 5
HELOACK = 7
EMAILGENSTATE = 8
OPENSOCKET = 9


serverName = sys.argv[1]
portNumber = int(sys.argv[2])

content = []   # create an empty array to be put entire forward file into to parse
state = EMAILGENSTATE

def address_parser(address_text):  # method for parsing addresses

    if True:
        address_parts = address_text.split("@")

        if len(address_parts) != 2:
            return address_text, 11
        local_part = address_parts[0]  # local-part
        domain = address_parts[1]  # domain

        if local_part.endswith(" ") or local_part.endswith("\t"):
            return address_text, 11
        if domain.startswith(" ") or domain.startswith("\t"):
            return address_text, 11
        if len(local_part.strip()) < 1:
            return address_text, 11
        if domain.endswith(" ") or domain.endswith("\t"):
            return address_text, 11
        if len(domain.strip()) < 1:
            return address_text, 11
        invalid_chars = ["<", ">", "(", ")", "[", "]", "\\", ".", ",", ";", ":", " ", "@", "\""]
        if local_part[0] in invalid_chars:
            return address_text, 11

        if any(char in invalid_chars for char in local_part):
            return address_text, 11

        domain_parts = domain.split(".")

        for domain_part in domain_parts:
            if len(domain_part) < 2 or not domain_part[0].isalpha() or not domain_part.isalnum():
                return address_text, 11
        return address_text, 0  # returns valid address

def prompt(message):
    if len(message) > 1:
        print message
    try:
        text_input = raw_input()
        return text_input
    except EOFError:
        sys.exit(0)  # exit program with end-of-line (ctrl+D)

while True:
    if state == OPENSOCKET:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        serverAddress = (serverName, portNumber)
        try:
            sock.connect(serverAddress)
        except:
            print "Error : Could not connect to socket"
            exit(1)
        data = sock.recv(DATASIZE)
        print data
        if not data.startswith("220 ") and not data.startswith("220\t"):  # serverACK
            state = QUIT
            continue
        else:
            sock.send("HELO " + socket.gethostname() + "\n")
            state = HELOACK
            continue

    if state == EMAILGENSTATE:
        while True:
            text_input = prompt("From:")
            result = address_parser(text_input)
            if result[1] == 0:
                content.append("MAIL FROM: <" + text_input + ">\n")  # first line, From: address
                break
            else:
                print "Invalid Address, please re-enter"
        while True:
            text_input = prompt("To:")
            rcptcount = 0
            addressList = text_input.split(",")
            valid = True
            for i in range(len(addressList)):
                address = addressList[i].strip()
                addressList[i] = address
                result = address_parser(address)
                rcptcount += 1
                if not result[1] == 0:
                    valid = False
                    break
            if not valid:
                print "Invalid Address(s), please re-enter"
            else:
                break
        for address in addressList:
            content.append("RCPT TO: <" + address + ">\n")
        text_input = prompt("Subject:")
        content.append("Subject: " + text_input + "\n")

        text_input = prompt("Message:")

        while not text_input == ".":
            content.append(text_input)
            text_input = prompt("")
        text_input = prompt("Attachment:").strip()
        attachmentText = []
        if len(text_input) > 1:
            filename = text_input
            attachmentText.append("INSERT FROM:\n")
            #attachmentText.append("INSERT SUBJECT")
            attachmentText.append("INSERT TO:")
            attachmentText.append("MIME-Version: 1.0\n")
            attachmentText.append(
                "Content-Type: multipart/mixed;\n boundary=\"------------A1FCDEE154E03D875E5D6779\"\n\n")
            attachmentText.append("--------------A1FCDEE154E03D875E5D6779\n")
            attachmentText.append("Content-Type: text/plain; charset=\"ISO-8859-1\"\n")
            attachmentText.append("Content-Transfer-Encoding: quoted-printable\n")
            attachmentText.append("INSERT MESSAGE HERE\n")
            attachmentText.append("--------------A1FCDEE154E03D875E5D6779\n")
            attachmentText.append("Content-Type: image/jpeg;\n name=\"" + filename + "\"\n")
            attachmentText.append("Content-Disposition: inline;\n filename=\"" + filename + "\"\n")
            attachmentText.append("Content-Transfer-Encoding: base64\n")
            #attachmentText.append("INSERT IMAGE HERE\n")
            attachmentText.append("string\n")
            attachmentText.append("--------------A1FCDEE154E03D875E5D6779--\n")
            attachmentText.append(".\n")

        state = OPENSOCKET

    if state == HELOACK:
        data = sock.recv(DATASIZE)
        print data
        if not data.startswith("250 ") and not data.startswith("250\t"):
            state = QUIT
            continue
        else:
            state = MAILFROMSTATE
            continue
    if state == MAILFROMSTATE:
        contentIndex = 0
        sock.sendall(content[contentIndex])
        text_input = sock.recv(DATASIZE)
        if len(text_input.split()) >= 1 and text_input.split()[0] == "250" and text_input.startswith("250"):
            print text_input  # mail from 250ok
            state = RCPTSTATE
            contentIndex += 1
            continue
        else:
            state = QUIT
            continue
    if state == RCPTSTATE:
        while content[contentIndex].startswith("RCPT"):
            sock.sendall(content[contentIndex])
            text_input = sock.recv(DATASIZE)
            print text_input  # rcpt to 250ok
            if len(text_input.split()) >= 1 and text_input.split()[0] == "250" and text_input.startswith("250"):
                contentIndex += 1
            else:
                state = QUIT
                continue
        state = DATASTATE
        continue

    if state == DATASTATE:  # parsing DATA aka begin mail body
        sock.sendall("DATA\n")
        text_input = sock.recv(DATASIZE)
        print text_input  # 354 ok
        if len(text_input.split()) >= 1 and text_input.split()[0] == "354" and text_input.startswith("354"):
            state = SENDMAILSTATE
            continue
        else:
            state = QUIT
            continue
    if state == SENDMAILSTATE:
        contentIndex = 0
        attachmentIndex = 0
        while attachmentIndex < len(attachmentText):
            aText = attachmentText[attachmentIndex]
            if not aText.startswith("INSERT"):
                sock.sendall(aText)
                print aText
            else:
                if aText.startswith("INSERT FROM:"):
                    contentIndex = 0
                    fromAddress = content[contentIndex].split(":")[1].strip()
                    sock.sendall("From: " + fromAddress + "\n")
                    print "From: " + fromAddress
                    contentIndex += 1
                if aText.startswith("INSERT TO:"):
                    contentIndex = 1
                    while content[contentIndex].startswith("RCPT"):
                        toAddress = content[contentIndex].split(":")[1].strip()
                        sock.sendall("To: " + toAddress + "\n")
                        print "To: " + toAddress
                        contentIndex += 1
                if aText.startswith("INSERT SUBJECT"):
                    contentIndex = rcptcount + 1
                    sock.sendall(content[contentIndex] + "\n")  # Subject line
                    print content[contentIndex]
                    contentIndex += 1
                elif aText.startswith("INSERT MESSAGE"):
                    sock.sendall("\n")
                    contentIndex = rcptcount + 2
                    while contentIndex < len(content):
                        sock.sendall(content[contentIndex] + "\n")
                        print content[contentIndex]
                        contentIndex += 1
                elif aText.startswith("INSERT IMAGE"):
                    with open(filename, 'rb') as imagefile:
                        encodedstring = base64.b64encode(imagefile.read())
                    sock.sendall("\n")
                    sock.sendall(encodedstring + "\n")
                    sock.sendall("\n")
            attachmentIndex += 1

        text_input = sock.recv(DATASIZE)
        if len(text_input.split()) >= 1 and text_input.split()[0] == "250" and text_input.startswith("250"):
            print text_input
            state = QUIT
        else:
            state = QUIT
            print text_input
    if state == QUIT:  # SMTP Quit
        #print >> sys.stderr, text_input
        sock.sendall("QUIT")
        sock.close()
        break