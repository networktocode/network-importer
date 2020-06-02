def print_to_yaml(obj, i=0):
    if isinstance(obj, list):
        for item in obj:
            print_to_yaml(item)

    attrs = obj.get_attrs()
    s = " "
    print(f"{s*i}{obj}:")
    i += 2
    for k, v in attrs.items():
        print(f"{s*i}{k}: {v}")

    for child_type in obj.childs:
        print(f"{s*i}{child_type}:")
        for child in getattr(obj, child_type):
            child_i = i + 2
            print_to_yaml(child, child_i)
