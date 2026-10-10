import json
t=open("template.html",encoding="utf-8").read()
d=open("data.json",encoding="utf-8").read()
assert "</script" not in d
open("index.html","w",encoding="utf-8").write(t.replace("__DATA__",d))
print("index.html KB:", len(t.replace("__DATA__",d))//1024)
