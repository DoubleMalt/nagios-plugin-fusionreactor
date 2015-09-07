#!/bin/sh

# Run smoke tests targeting a local FusionReactor

../check_fusionreactor.py -H 127.0.0.1 -P 8088 -s fusionreactor -p test -f SerializedMetrics/MemoryProbe/Free

