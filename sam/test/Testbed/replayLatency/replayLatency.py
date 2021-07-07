import os
import sys
import getopt

argv = sys.argv
print(argv)
try:
    opts, args = getopt.getopt(argv[1:], 'i:m:c:d:f:r:s:l:', ["ifile=", "mac=", "src=", "dst=", "flow=", "rate=", "sfile=", "lfile="])
except getopt.GetoptError:
    print('args err')
    sys.exit(2)
print(opts)
print(args)

for opt, arg in opts:
    if opt == '-i':
        inputfile = arg
    elif opt == '-m':
        MAC_address = arg
    elif opt == '-c':
        src_IP = arg
    elif opt == '-d':
        dst_IP = arg
    elif opt == '-f':
        flownum = arg
    elif opt == '-r':
        replay_rate = arg
    elif opt == '-s':
        size_output = arg
    elif opt == '-l':
        latency_output = arg

f1 = './f1'
f2 = './f2'
os.system('./pcapRewrite/pcapRewrite -f ' + inputfile + ' -w ' + f1 + ' -dstipmap ' + dst_IP + ' -srcipmap ' + src_IP + ' -flowcnt ' + flownum)
os.system('tcprewrite --enet-dmac=' + MAC_address + ' -i ' + f1 + ' -o ' + f2)
os.system('sudo ~/MoonGen/build/MoonGen ./replay-latency-n2.lua 0 ' + f2 + ' ' + flownum + ' -r ' + replay_rate + ' -f ' + size_output + ' -t ' + latency_output + ' -l')
os.system('rm ./f1')
os.system('rm ./f2')
