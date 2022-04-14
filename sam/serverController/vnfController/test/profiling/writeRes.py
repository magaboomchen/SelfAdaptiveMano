#!/usr/bin/python
# -*- coding: UTF-8 -*-

from scapy.all import *

from sam.base.pickleIO import PickleIO


if __name__ == "__main__":
    res = {1: [0.9639389514923096, 0.9336371421813965, 0.96846604347229, 0.9292600154876709, 0.896324872970581, 0.9120371341705322, 0.9341111183166504, 0.9637320041656494, 0.9502091407775879, 0.8983759880065918], 2: [3.3288469314575195, 3.5926082134246826, 3.6981561183929443, 3.4267871379852295, 3.5308778285980225, 3.187424898147583, 3.879565954208374, 3.2648000717163086, 3.2232320308685303, 3.542279005050659], 3: [6.352987051010132, 5.993587970733643, 6.065644979476929, 6.722554922103882, 5.026257038116455, 5.99581503868103, 5.841332912445068, 5.766046047210693, 5.314692974090576, 5.782176971435547], 4: [9.1181800365448, 9.293316125869751, 8.644914865493774, 8.456264019012451, 8.45764684677124, 8.640156030654907, 8.291127920150757, 8.80950403213501, 7.424252986907959, 9.05554485321045], 5: [11.223237037658691, 11.150158882141113, 11.144773006439209, 11.099907875061035, 11.402402877807617, 10.70628309249878, 10.1233651638031, 10.229053020477295, 12.040539979934692, 10.702425003051758]}

    pIO = PickleIO()
    pIO.writePickleFile("./deployTimeRes.pickle", res)