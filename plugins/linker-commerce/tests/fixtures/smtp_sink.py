"""One test-owned loopback SMTP sink; accepts only the documented fake login."""

import base64
import json
import socketserver
import sys
from pathlib import Path


class Handler(socketserver.StreamRequestHandler):
    def reply(self, line: str) -> None:
        self.wfile.write((line + "\r\n").encode())
        self.wfile.flush()

    def handle(self) -> None:
        self.reply("220 localhost test sink")
        authenticated = False
        recipients: list[str] = []
        while line := self.rfile.readline():
            command = line.decode().strip()
            verb = command.split(" ", 1)[0].upper()
            if verb in {"EHLO", "HELO"}:
                self.reply("250-localhost")
                self.reply("250 AUTH LOGIN")
            elif verb == "AUTH":
                self.reply("334 VXNlcm5hbWU6")
                user = base64.b64decode(self.rfile.readline().strip()).decode()
                self.reply("334 UGFzc3dvcmQ6")
                password = base64.b64decode(self.rfile.readline().strip()).decode()
                authenticated = (
                    user == "sales@sunriverinverter.com" and password == sys.argv[2]
                )
                self.reply(
                    "235 authenticated"
                    if authenticated
                    else "535 authentication failed: wrong-test-password"
                )
            elif verb == "MAIL":
                recipients = []
                self.reply("250 ok" if authenticated else "530 authenticate first")
            elif verb == "RCPT":
                recipients.append(command)
                self.reply("250 ok")
            elif verb == "DATA":
                self.reply("354 end with dot")
                data = []
                while (chunk := self.rfile.readline()) != b".\r\n":
                    if not chunk:
                        return
                    data.append(chunk.decode())
                with Path(sys.argv[1]).open("a") as capture:
                    capture.write(
                        json.dumps({"recipients": recipients, "message": "".join(data)})
                        + "\n"
                    )
                self.reply("250 accepted")
            elif verb == "QUIT":
                self.reply("221 bye")
                return
            elif verb in {"RSET", "NOOP"}:
                self.reply("250 ok")
            else:
                self.reply("502 unsupported")


with socketserver.TCPServer(("127.0.0.1", 0), Handler) as server:
    print(server.server_address[1], flush=True)
    server.serve_forever()
