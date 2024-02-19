import ast

def parse_route(content):
    tmp = ast.literal_eval("[{}]".format(content))
    for i in tmp:
        i["lat"] = float(i["lat"])
        i["lng"] = float(i["lng"])
    return tmp
