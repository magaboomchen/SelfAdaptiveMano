\ Model nfvDPPP[0,b]
\ LP format - for model browsing. Use MPS format to capture full model detail.
Minimize
  50 flow[1,2,1] + 10 flow[1,2,3] + 10 flow[1,3,2] + 10 flow[0,1,2]
   + 10 flow[1,3,1] + 10 flow[0,3,1] + 10 flow[0,2,3] + 10 flow[1,1,3]
   + 10 flow[0,3,2] + 10 flow[0,1,3] + 50 flow[0,2,1] + 10 flow[1,1,2]
   - 100 Constant
Subject To
 srcNode[1]: flow[0,1,2] - flow[0,3,1] + flow[0,1,3] - flow[0,2,1]
   + deploy[0,1] = 1
 srcNode[2]: - flow[0,1,2] + flow[0,2,3] - flow[0,3,2] + flow[0,2,1]
   + deploy[0,2] = 0
 srcNode[3]: flow[0,3,1] - flow[0,2,3] + flow[0,3,2] - flow[0,1,3]
   + deploy[0,3] = 0
 middleNode[1,1]: - flow[1,2,1] - flow[1,3,1] + flow[1,1,3] + flow[1,1,2]
   - deploy[0,1] + deploy[1,1] = 0
 middleNode[2,1]: flow[1,2,1] + flow[1,2,3] - flow[1,3,2] - flow[1,1,2]
   + deploy[1,2] - deploy[0,2] = 0
 middleNode[3,1]: - flow[1,2,3] + flow[1,3,2] + flow[1,3,1] - flow[1,1,3]
   + deploy[1,3] - deploy[0,3] = 0
 dstNode[1]: deploy[1,1] = 1
 vnfUnSplittable[0]: deploy[0,1] + deploy[0,3] + deploy[0,2] = 1
 vnfDeployable[0,3]: deploy[0,3] + deploy[0,2] = 1
 linkCapacity[1,2]: flow[0,1,2] + flow[1,1,2] <= 100
 linkCapacity[3,2]: flow[1,3,2] + flow[0,3,2] <= 100
 linkCapacity[1,3]: flow[1,1,3] + flow[0,1,3] <= 100
 linkCapacity[2,3]: flow[1,2,3] + flow[0,2,3] <= 100
 linkCapacity[3,1]: flow[1,3,1] + flow[0,3,1] <= 100
 linkCapacity[2,1]: flow[1,2,1] + flow[0,2,1] <= 100
 nodeCapacity[1]: deploy[0,1] <= 10
 nodeCapacity[2]: deploy[0,2] <= 20
 nodeCapacity[3]: deploy[0,3] <= 10
 e2eLatency: 3.33333e-09 flow[1,2,1] + 3.33333e-09 flow[1,2,3]
   + 3.33333e-09 flow[1,3,2] + 3.33333e-09 flow[0,1,2]
   + 3.33333e-09 flow[1,3,1] + 3.33333e-09 flow[0,3,1]
   + 3.33333e-09 flow[0,2,3] + 3.33333e-09 flow[1,1,3]
   + 3.33333e-09 flow[0,3,2] + 3.33333e-09 flow[0,1,3]
   + 3.33333e-09 flow[0,2,1] + 3.33333e-09 flow[1,1,2] + 1.25 deploy[0,1]
   + 1.25 deploy[0,3] + 1.25 deploy[0,2] <= 35
Bounds
 Constant = 1
Binaries
 flow[1,2,1] flow[1,2,3] flow[1,3,2] flow[0,1,2] flow[1,3,1] flow[0,3,1]
 flow[0,2,3] flow[1,1,3] flow[0,3,2] flow[0,1,3] flow[0,2,1] flow[1,1,2]
 deploy[0,1] deploy[1,2] deploy[1,3] deploy[1,1] deploy[0,3] deploy[0,2]
End
