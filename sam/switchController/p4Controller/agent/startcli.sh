export PYTHON_VER=2.7
export SDE_INSTALL=/home/yyl/bf-sde-9.1.0/install
export PYTHONPATH=$SDE_INSTALL/lib/python$PYTHON_VER/site-packages/p4testutils:$SDE_INSTALL/lib/python$PYTHON_VER/site-packages/tofinopd/:$SDE_INSTALL/lib/python$PYTHON_VER/site-packages/tofino:$SDE_INSTALL/lib/python$PYTHON_VER/site-packages/:$PYTHONPATH
echo SDE_INSTALL = $SDE_INSTALL
echo PYTHON_VER = $PYTHON_VER
echo PYTHONPATH = $PYTHONPATH
python p4cli.py
