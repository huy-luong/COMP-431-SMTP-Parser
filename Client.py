import sys
import socket


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
            addressList = text_input.split(",")
            valid = True
            for i in range(len(addressList)):
                address = addressList[i].strip()
                addressList[i] = address
                result = address_parser(address)
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
        content.append("Subject: " + text_input)

        text_input = prompt("Message:")
        content.append(text_input)
        while not text_input == ".":
            text_input = prompt("")
            content.append(text_input)
        state = OPENSOCKET

    if state == HELOACK:
        data = sock.recv(DATASIZE)
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
        if len(text_input.split()) >= 1 and text_input.split()[0] == "354" and text_input.startswith("354"):
            state = SENDMAILSTATE
            continue
        else:
            state = QUIT
            continue
    if state == SENDMAILSTATE:
        contentIndex = 0

        while content[contentIndex].startswith("RCPT") or content[contentIndex].startswith("MAIL FROM:"):
            Address = content[contentIndex].split(":")[1].strip()
            if content[contentIndex].startswith("MAIL FROM:"):
                sock.sendall("From: " + Address + "\n")
                contentIndex += 1
            else:
                sock.sendall("To: " + Address + "\n")
                contentIndex += 1
        sock.sendall(content[contentIndex] + "\n")  # Subject line
        contentIndex += 1
        sock.sendall("\n")
        while contentIndex < len(content):
            sock.sendall(content[contentIndex] + "\n")
            contentIndex += 1
        text_input = sock.recv(DATASIZE)
        if len(text_input.split()) >= 1 and text_input.split()[0] == "250" and text_input.startswith("250"):
            state = QUIT
        else:
            state = QUIT
    if state == QUIT:  # SMTP Quit
        #print >> sys.stderr, text_input
        sock.sendall("QUIT")
        sock.close()
        break