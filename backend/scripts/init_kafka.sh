#!/bin/bash
# BTC 自动交易系统 - Kafka Topic 初始化

KAFKA_HOST=${KAFKA_HOST:-localhost:9092}

echo "初始化 Kafka Topics..."

# 市场数据 Topic
kafka-topics.sh --bootstrap-server $KAFKA_HOST --create --if-not-exists \
    --topic market.bars \
    --partitions 3 \
    --replication-factor 1

kafka-topics.sh --bootstrap-server $KAFKA_HOST --create --if-not-exists \
    --topic market.funding \
    --partitions 1 \
    --replication-factor 1

kafka-topics.sh --bootstrap-server $KAFKA_HOST --create --if-not-exists \
    --topic market.liquidations \
    --partitions 1 \
    --replication-factor 1

# 交易 Topic
kafka-topics.sh --bootstrap-server $KAFKA_HOST --create --if-not-exists \
    --topic trading.claims \
    --partitions 3 \
    --replication-factor 1

kafka-topics.sh --bootstrap-server $KAFKA_HOST --create --if-not-exists \
    --topic trading.orders \
    --partitions 3 \
    --replication-factor 1

kafka-topics.sh --bootstrap-server $KAFKA_HOST --create --if-not-exists \
    --topic trading.executions \
    --partitions 3 \
    --replication-factor 1

# 风控 Topic
kafka-topics.sh --bootstrap-server $KAFKA_HOST --create --if-not-exists \
    --topic risk.events \
    --partitions 1 \
    --replication-factor 1

kafka-topics.sh --bootstrap-server $KAFKA_HOST --create --if-not-exists \
    --topic risk.alerts \
    --partitions 1 \
    --replication-factor 1

# 状态 Topic
kafka-topics.sh --bootstrap-server $KAFKA_HOST --create --if-not-exists \
    --topic state.transitions \
    --partitions 1 \
    --replication-factor 1

echo "Kafka Topics 初始化完成"
kafka-topics.sh --bootstrap-server $KAFKA_HOST --list
