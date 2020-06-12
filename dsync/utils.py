





class DSyncMixin:
    def __iter__(self):
        for v in self.values:
            yield v, getattr(self, v)

    def get_type(self):
        return self.__tablename__

    def get_keys(self):
        return {pk.name: getattr(self, pk.name) for pk in self.__table__.primary_key}

    def get_attrs(self):
        return {attr: getattr(self, attr) for attr in self.attributes}





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
