import sys
import socket
#  Create Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

portNumber = int(sys.argv[1])
address = socket.gethostname()
serverAddress = ("", portNumber)

try:
    sock.bind(serverAddress)
except:
    print "Error: could not bind to address and or port"
    exit(1)

sock.listen(5)  # Listen for handshake

DATASIZE = 256

def address_parser(address_text):  # method for parsing addresses
    if not address_text.startswith("<") or not address_text.endswith(">"):
        return address_text, 11
    else:
        address_text = address_text.replace("<", "")
        address_text = address_text.replace(">", "")  # Remove angle brackets
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


# return address and status
MAILFROMSTATE = 1
# State 1 is processing A MAIL FROM
# State 2 is process RCPT TO or awaiting DATA
RCPTTOSTATE = 2
# State 3 is receiving email text
DATASTATE = 3
# State 4 is processing the email
MESSAGEPROCESSTATE = 4
# State 10 is 500 error state
# State 11 is 501 error state
# State 12 is 503 error state

ERRORSTATE = 13

LISTENSTATE = 5
HELOWAITING = 6
state = LISTENSTATE
while True:
    if state == LISTENSTATE:  # Waiting for connection
        (connection, client_address) = sock.accept()
        message = "220 " + serverAddress[0]
        connection.sendall(message)  # Send 220 message to client
        state = HELOWAITING
        continue
    if state == HELOWAITING:
        data = connection.recv(DATASIZE)
        if not data.startswith("HELO ") and not data.startswith("HELO\t"):
            state = ERRORSTATE
            print data
            errorMessage = "Invalid HELO message"
            continue
        else:
            heloMessage = data.split("HELO")[1].strip()
            connection.sendall("250 " + heloMessage + " pleased to meet you\n")  # Echo 250 ACK with HELO message
            state = MAILFROMSTATE
            continue


    if state == MAILFROMSTATE:
        from_address = ""
        rcpt_list = []  # list for all rcpt's
        text_input = connection.recv(DATASIZE)
        if text_input.startswith("RCPT") or text_input.startswith("DATA"):
            state = 12
            continue
        elif not text_input.startswith("MAIL"):
            state = 10
            continue
        else:
            mail_parts = text_input.split(None, 1)  # Parses white space
            if len(mail_parts) != 2:
                state = 10  # error state
                continue
            else:
                add = ""
                if mail_parts[0] != "MAIL" or not mail_parts[1].startswith("FROM:"):
                    state = 10
                    continue
                else:
                    if len(mail_parts[1]) > 5:
                        add = mail_parts[1].split(":")[1].strip()
                    else:
                        state = 10  # return error state
                    status = address_parser(add)
                    if status[1] != 0:
                        state = status[1]
                        continue
                    else:
                        # print text_input
                        connection.sendall("250 OK\n")
                        state = RCPTTOSTATE
                        from_address = status[0]
                        continue


    if state == RCPTTOSTATE:

        text_input = connection.recv(DATASIZE)

        if text_input.startswith("DATA"):
            if text_input.strip() != "DATA":
                state = 10
                continue
            if len(rcpt_list) < 1:
                state = 12  # bad sequence error
                continue
            else:
                #print "DATA"
                connection.sendall("354 Start mail input; end with <CRLF>.<CRLF>\n")
                state = DATASTATE
                email_text = []  # body of the message
                continue
        if not text_input.startswith("RCPT"):

            state = 10
            continue
        # at this point, we have most likely received a valid RCPT command
        command_parts = text_input.split(None, 1)  # split on whitespace
        if len(command_parts) != 2:
            state = 10
            continue
        if command_parts[0] != "RCPT" or not command_parts[1].startswith("TO:"):
            state = 10
            continue
        # parse the address
        if len(command_parts[1]) > 3:
            recipient_address = command_parts[1].split(":")[1].strip()
        else:
            state = 10  # return error state
            continue
        status = address_parser(recipient_address)
        if status[1] != 0:  # if an error is thrown, check which error
            state = status[1]
            continue
        else:
            rcpt_list.append(status[0])  # add rcpt to list
            #print text_input
            connection.sendall("250 OK\n")
            continue

    if state == DATASTATE:

        text_input = connection.recv(DATASIZE)


        textLines = text_input.split("\n")
        for text in textLines:
            if text.rstrip() != ".":
                email_text.append(text)
            else:
                state = MESSAGEPROCESSTATE
                connection.sendall("250 OK\n")

    if state == MESSAGEPROCESSTATE:  # Appending to file process
        for recipient in rcpt_list:
            domainName = recipient.split("@")[1].strip()  # obtain domain name from address
            file_name = "forward/" + domainName
            f = open(file_name, 'a+')
            for i in range(len(email_text)):
                bodyline = email_text[i]
                if i == 1 and len(bodyline.strip()) < 1:
                    continue
                if i + 1 == len(email_text):
                    f.write(bodyline)
                else:
                    f.write(bodyline + "\n")
            f.close()  # close file(s)
        connection.close()
        state = LISTENSTATE

    if state == 10:
        #print text_input
        connection.sendall("500 Syntax error: command unrecognized")
        connection.close()
        state = LISTENSTATE
    if state == 11:
        #print text_input
        connection.sendall("501 Syntax error in parameters or arguments")
        connection.close()
        state = LISTENSTATE
    if state == 12:  # DATA command before RCPT TO
        #print text_input
        connection.sendall("503 Bad sequence of commands")
        connection.close()
        state = LISTENSTATE
    if state == ERRORSTATE:
        print errorMessage
        connection.close()
        state = LISTENSTATE

