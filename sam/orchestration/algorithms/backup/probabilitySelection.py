#!/usr/bin/python
# -*- coding: UTF-8 -*-

import numpy as np


values = ('A', 'B', 'C', 'D')
weights = (0.58, 0.17, 0.223, 0.1109)

# values = []
# weights = []
# dic = {}

# for index in range(1, 2000):
#     # values.append(str(index))
#     values.append(index)
#     dic[index] = str(index)
#     weights.append(index)

# values = tuple(values)
# weights = tuple(weights)
# # print values
# # print weights

norm = tuple([float(i)/sum(weights) for i in weights])

# print ''.join(np.random.choice(values, size=1, replace=True, p=norm))
index = np.random.choice(values, size=1, replace=True, p=norm)[0]

print(index)
# print dic[index]
