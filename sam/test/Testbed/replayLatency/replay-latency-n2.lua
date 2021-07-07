--- Replay a pcap file.

local mg      = require "moongen"
local device  = require "device"
local memory  = require "memory"
local log     = require "log"
local pcap    = require "pcap"
local limiter = require "software-ratecontrol"
local tst     = require "timestamping"
local stats   = require "stats"
local hist    = require "histogram"
local arp     = require "proto.arp"
local timer   = require "timer"
local log     = require "log"

local PKT_SIZE	= 64
local DST_MAC	= "cc:37:ab:a0:a8:41"
local ARP_SRC_MAC = "90:e2:ba:b1:4d:0e"
local SRC_PORT		= 1234
local DST_PORT		= 319

-- local ended = 0
function configure(parser)
	parser:argument("dev", "Device to use."):args(1):convert(tonumber)
	parser:argument("file", "File to replay."):args(1)
	parser:argument("flownum", "Device to use."):args(1):convert(tonumber)
	parser:option("-r --rate-multiplier", "Speed up or slow down replay, 1 = use intervals from file, default = replay as fast as possible"):default(0):convert(tonumber):target("rateMultiplier")
	parser:option("-s --buffer-flush-time", "Time to wait before stopping MoonGen after enqueuing all packets. Increase for pcaps with a very low rate."):default(1):convert(tonumber):target("bufferFlushTime")
	parser:flag("-l --loop", "Repeat pcap file.")
	parser:option("-t --hist", "Filename of the latency histogram."):default("histogram.csv")
	parser:option("-f --flow", "Filename of the realtime flow."):default("flow.csv")
	parser:option("--srcip", "source IP"):default("1.1.1.2"):target("srcip")
	parser:option("--dstip", "destination IP base"):default("3.3.3.2"):target("dstip")
	local args = parser:parse()
	return args
end

function master(args)
	local dev = device.config{port = args.dev, rxQueues = 2, txQueues = 2}
	device.waitForLinks()
	local rateLimiter
	if args.rateMultiplier > 0 then
		rateLimiter = limiter:new(dev:getTxQueue(0), "custom")
	end
    replayer = mg.startTask("replay", dev:getTxQueue(0), dev:getRxQueue(0), args.file, args.loop, rateLimiter, args.rateMultiplier, args.bufferFlushTime, args.flow)
	mg.startTask("timerSlave", dev:getTxQueue(1), dev:getRxQueue(1), 84, args.flownum, args.hist, parseIPAddress(args.srcip), parseIPAddress(args.dstip))
	stats.startStatsTask{dev}
	replayer:wait()
	mg:stop()
	mg.waitForTasks()
end

function replay(queue, rxq, file, loop, rateLimiter, multiplier, sleepTime, flowf)
	-- local mem = memory.createMemPool(function(buf)
	-- 	buf:getArpPacket():fill{
	-- 		ethDst = "00:00:00:00:00:02",
	-- 		ethSrc = ARP_SRC_MAC,
	-- 		arpOperation = arp.OP_REPLY,
	-- 		pktLength = 60,
	-- 		arpHardwareDst = "00:00:00:00:00:00",
	-- 		arpHardwareSrc = ARP_SRC_MAC,
	-- 		arpProtoSrc = "1.1.1.2",
	-- 		arpProtoDst = "1.1.1.1",
	-- 	}
	-- end)
	-- local txBufs = mem:bufArray(1)
	-- txBufs:alloc(60)
	-- queue:sendN(txBufs, 1)
	local mempool = memory:createMemPool(4096)
	local bufs = mempool:bufArray()
	local pcapFile = pcap:newReader(file)
	local prev = 0
	local linkSpeed = queue.dev:getLinkStatus().speed
    local rxCtr = stats:newDevRxCounter(rxq, "plain")
	local startTime = os.clock()
	local flowfile = io.open(flowf, "w")
	local outputcnt = 1
	local tmpcnt = 1
	-- io.output(flowfile)
	while mg.running() do
		-- tmpcnt = tmpcnt + 1
        local n = pcapFile:read(bufs)
		if loop and n == 0 then 
			prev = 0
			pcapFile = pcap:newReader(file)
			pcapFile:reset()
			n = pcapFile:read(bufs)
		end
		if n > 0 then
			if rateLimiter ~= nil then
				if prev == 0 then
					prev = bufs.array[0].udata64
				end
				for i = 1, n  do
                    local buf = bufs[i]
					-- ts is in microseconds
					local ts = buf.udata64
					if prev > ts then
						ts = prev
					end
					local delay = ts - prev
					delay = tonumber(delay * 10^3) / multiplier -- nanoseconds
					delay = delay / (8000 / linkSpeed) -- delay in bytes
					buf:setDelay(delay)
					prev = ts
				end
			end
		else
			if not loop then
                -- print("break while")
                -- ended = 1
				break
			end
		end
		if rateLimiter and n > 0 then
			rateLimiter:sendN(bufs, n)
		else
			queue:sendN(bufs, n)
		end
		rxCtr:update()
		if os.clock() > startTime + outputcnt * 0.01 then
			outputcnt = outputcnt + 1
			local p, b = rxCtr:getThroughput()
			flowfile:write(os.clock())
			flowfile:write(',')
			flowfile:write(os.time())
			flowfile:write(',')
			flowfile:write(p)
			flowfile:write(',')
			flowfile:write(b)
			flowfile:write('\n')
		end
	end
	flowfile:close()
	log:info("Enqueued all packets, waiting for %d seconds for queues to flush", sleepTime)
	mg.sleepMillisIdle(sleepTime * 1000)
end

local function fillUdpPacket(buf, len)
	buf:getUdpPacket():fill{
		ethSrc = queue,
		ethDst = DST_MAC,
		ip4Src = SRC_IP,
		ip4Dst = DST_IP,
		udpSrc = SRC_PORT,
		udpDst = DST_PORT,
		pktLength = len
	}
end

function timerSlave(txQueue, rxQueue, size, flows, histfile, srcip, dstip)
	print(histfile)
	-- doArp()
	if size < 84 then
		log:warn("Packet size %d is smaller than minimum timestamp size 84. Timestamped packets will be larger than load packets.", size)
		size = 84
	end
	local timestamper = tst:newUdpTimestamper(txQueue, rxQueue)
	mg.sleepMillis(1000) -- ensure that the load task is running
	local counter = 0
	local rateLimit = timer:new(0.01)
	-- local baseIP = parseIPAddress(SRC_IP_BASE)
	local tcnt = 0
	local flowfile = io.open(histfile, "w")
	while mg.running() do
		lat, cnt = timestamper:measureLatency(size, function(buf)
			fillUdpPacket(buf, size)
			local pkt = buf:getUdpPacket()
			pkt.ip4.src:set(srcip)
			pkt.ip4.dst:set(dstip + counter)
			counter = incAndWrap(counter, flows)
		end, 15)
		flowfile:write(os.clock())
		flowfile:write(',')
		flowfile:write(os.time())
		flowfile:write(',')
		flowfile:write(cnt)
		flowfile:write(',')
		if lat == nil then
			flowfile:write('-1')
		else
			flowfile:write(lat)
		end
		flowfile:write('\n')
		rateLimit:wait()
		rateLimit:reset()
	end
	-- print the latency stats after all the other stuff
	mg.sleepMillis(300)
	flowfile:close()
end

