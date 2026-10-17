"""Remove caminhos locais/usuario de arquivos texto antes de publicar. Uso: python sanitize.py <pasta> <usuario>"""
import os, re, sys
root, user = sys.argv[1], sys.argv[2]
# C:\Users\<user>\... ou C:\\Users\\<user> (JSON) ou /c/Users/<user>, inclusive nome curto 8.3
pat = re.compile(r"[A-Za-z]:(?:\\{1,2}|/)Users(?:\\{1,2}|/)(?:" + re.escape(user) + r"|[A-Z0-9]{1,6}~\d(?:\.[A-Z0-9]{1,3})?)|/c/Users/" + re.escape(user), re.I)
n = 0
for d, _, files in os.walk(root):
    if ".git" in d.split(os.sep):
        continue
    for f in files:
        p = os.path.join(d, f)
        try:
            s = open(p, encoding="utf-8").read()
        except (UnicodeDecodeError, OSError):
            continue
        t = pat.sub("<USER_DIR>", s).replace(user, "<user>")
        if t != s:
            open(p, "w", encoding="utf-8", newline="").write(t); n += 1
print("arquivos sanitizados:", n)
