# 开发建议

simulator的开发可能会用到/sam/base，/sam/measurement/dcnInfoBaseMaintainer以及sam/orchestration/algorithms/base/performanceModel中的很多类。
开发时请复用这些类。
增加新功能时请继承这些类然后再开发新功能。
