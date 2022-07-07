#!/usr/bin/python
# -*- coding: UTF-8 -*-

from ruamel import yaml
from sam.ryu.conf.genSwitchConfLogicalTwoTier import SwitchConf


def ls(obj):
    print("\n".join([x for x in dir(obj) if x[0] != "_"]))

if __name__ == "__main__":
    yaml = yaml.YAML()
    yaml.register_class(SwitchConf)

    with open("./switch.yaml") as f:
        content = yaml.load(f)
        # ls(content)
        for key, item in content.items():
            print(item)