#!/bin/bash
#
# Requirement: must be executed on admin node

set -ex

# preparation: deleting pool if they exist
sudo ceph osd pool delete mig_test_rpl_pool mig_test_rpl_pool --yes-i-really-really-mean-it
sudo ceph osd pool delete new_ec_pool new_ec_pool --yes-i-really-really-mean-it
# create replicated pool
sudo ceph osd pool create mig_test_rpl_pool 16 16 replicated
sudo ceph osd pool application enable mig_test_rpl_pool rbd
# add obj into the pool
for i in 1 2 3 4 5
do 
  file_name=/tmp/random_${i}.txt
  openssl rand -out /tmp/random_1.txt -base64 1000000 
  sudo rados -p mig_test_rpl_pool put object_${i} $file_name
  sudo ceph osd map mig_test_rpl_pool object_${i}
done
sudo rados -p mig_test_rpl_pool ls|grep object
# create new EC pool
sudo ceph osd pool create new_ec_pool 16 16 erasure default
sudo ceph osd pool application enable new_ec_pool rbd
# setup cache tier 
sudo ceph osd tier add new_ec_pool mig_test_rpl_pool --force-nonempty
sudo ceph osd tier cache-mode mig_test_rpl_pool forward --yes-i-really-mean-it
# Force the cache pool to move all objects to the new pool
sudo rados -p mig_test_rpl_pool cache-flush-evict-all
# Switch all clients to the new pool
sudo ceph osd tier set-overlay new_ec_pool mig_test_rpl_pool
# verify all objects are in the new EC pool
sudo rados -p mig_test_rpl_pool ls|grep object || echo "Pool empty: OK"
sudo rados -p new_ec_pool ls|grep object
# remove the overlay and the old cache pool 'testpool'
sudo ceph osd tier remove-overlay new_ec_pool
sudo ceph osd tier remove new_ec_pool mig_test_rpl_pool

echo "Result: OK"

set +ex
