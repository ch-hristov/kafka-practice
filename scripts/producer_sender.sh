kafka-console-producer --topic partition_demo \ 
--bootstrap-server localhost:9092 \
--property parse.key=true \
--property key.separator=: