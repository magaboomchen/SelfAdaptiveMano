define(
	$RATE  2000Bps,
    $QUEUE_CAPACITY 1000,
);

in0 :: FromDPDKDevice(0, N_QUEUES 1, MODE none, NUMA true);
out0 :: ToDPDKDevice(0, N_QUEUES 1);
in1 :: FromDPDKDevice(1, N_QUEUES 1, MODE none, NUMA true);
out1 ::ToDPDKDevice(1, N_QUEUES 1);
rl_direction0 :: BandwidthRatedUnqueue(RATE $RATE, BURST_BYTES 5000)
rl_direction1 :: BandwidthRatedUnqueue(RATE $RATE, BURST_BYTES 5000)

in0 -> Queue(CAPACITY $QUEUE_CAPACITY) -> rl_direction0;
in1 -> Queue(CAPACITY $QUEUE_CAPACITY) -> rl_direction1;

rl_direction0 -> out1;
rl_direction1 -> out0;
//rl_direction0 -> Print() -> EtherMirror() -> out0;
//rl_direction1 -> Print() -> EtherMirror() -> out1;