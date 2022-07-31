rm -rf $SDE/build/p4-build/p4nf_sam
mkdir -p $SDE/build/p4-build/p4nf_sam
cd $SDE/build/p4-build/p4nf_sam
$SDE/pkgsrc/p4-build/configure                  \
    P4_PATH=/root/p4nfsam/p4nf_sam.p4           \
    P4_NAME=p4nf_sam                            \
    P4_PREFIX=p4nf_sam                          \
    P4_VERSION=p4-16                            \
    P4_ARCHITECTURE=tna                         \
    P4FLAGS="--verbose 2 --create-graphs -g"    \
    --with-tofino                               \
    --prefix=$SDE_INSTALL
make
make install
