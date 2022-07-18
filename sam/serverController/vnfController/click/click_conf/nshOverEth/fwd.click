in0 :: FromDPDKDevice(0, PROMISC true, N_QUEUES 1, MODE none);
out0 :: ToDPDKDevice(0, N_QUEUES 1);
in1 :: FromDPDKDevice(1, PROMISC true, N_QUEUES 1, MODE none);
out1 ::ToDPDKDevice(1, N_QUEUES 1);
in0 -> out1;
in1 -> out0;
// in0 -> Print() -> EtherMirror() -> out0;
// in1 -> Print() -> EtherMirror() -> out1;