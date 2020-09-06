# VNFI

Each VNFI has two PMDPort to connect.

One is for direction 0, another is for direction 1.


# API 

## vdev name
To get vdev name of a VNF, please use the API provided as follow:
```
class SIBMaintainer:
    def getVdev(self,VNFIID,directionID)
        # VNFID: uuid of a VNFI
        # directionID: 0 or 1, denotes direction of a VNF
```
