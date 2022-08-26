# Regulator Function
Auto scaling for SFC
Auto recovery for SFCI
Auto recovery for SFC

# Dashboard
## Initial
### Manual SFC
If user set the SFC to manual state, dashboard needs to set SFC's STATE to STATE_MANUAL to regulator by REQUEST_TYPE_UPDATE_SFC_STATE.
Regulator will handle this state update request.

### Auto SFC
Do nothing


## Running
### Manual -> Auto
set SFC's STATE to STATE_ACTIVE to regulator by REQUEST_TYPE_UPDATE_SFC_STATE.

### Auto -> Manual
Same to Initial's manual SFC case.

## Change scaling and recovery
Send request to regulator to change scaling and recovery mode


## Delete SFCI and SFC
Must send cmd to regulator.