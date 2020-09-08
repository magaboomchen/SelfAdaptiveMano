#!/usr/bin/python
# -*- coding: UTF-8 -*-

from ruamel import yaml
from genSwitchConf import SwitchConf

def ls(obj):
    print("\n".join([x for x in dir(obj) if x[0] != "_"]))

if __name__ == "__main__":
    yaml = yaml.YAML()
    yaml.register_class(SwitchConf)

    with open("./switch.yaml") as f:
        content = yaml.load(f)
        # ls(content)
        for item in content.itervalues():
            print(item)