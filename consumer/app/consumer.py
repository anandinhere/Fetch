import json
import time
import datetime
import os
from collections import Counter
from kafka.admin import KafkaAdminClient, NewTopic
from confluent_kafka import Consumer, Producer, KafkaError
from prometheus_client import generate_latest, REGISTRY, start_http_server, Gauge


# Kafka configuration
BROKER = "kafka:9092"
INPUT_TOPIC = "user-login"
OUTPUT_TOPIC = "user_login_analytics"
GROUP_ID = "consumer-group-1"
DEVICE_TYPE_COUNTER = Gauge('device_type_count', 'Device type count', ['device_type', 'topic'])
LOCALE_COUNTER = Gauge('locale_count', 'Locale count', ['locale', 'topic'])
TOTAL_COUNTER = Gauge('total_count', 'Total count', ['record_type', 'topic'])


# function to configure the Kafka consumer
def create_consumer():
    return Consumer({
        'bootstrap.servers': BROKER,
        'group.id': GROUP_ID,
        'auto.offset.reset': 'earliest'
    })

# function to configure the Kafka producer
def create_producer():
    return Producer({'bootstrap.servers': BROKER})

# Main function
def main():
    consumer = create_consumer()
    producer = create_producer()
    consumer.subscribe([INPUT_TOPIC])
    # Create an AdminClient to manage topics
    bootstrap_servers = os.environ.get('BOOTSTRAP_SERVERS', BROKER)
    analytics_topic = os.environ.get('KAFKA_TOPIC_ANALYTICS', 'user_login_analytics')
    admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)

    # Check if the 'user_login_analytics' topic exists
    topic_exists = analytics_topic in admin_client.list_topics()

    # Create the 'user_login_analytics' topic if it doesn't exist
    if not topic_exists:
        new_topic = NewTopic(name=analytics_topic, num_partitions=1, replication_factor=1)
        try:
            admin_client.create_topics(new_topics=[new_topic], validate_only=False)
        except KafkaError:
            pass

    print(f"Consuming messages from topic: {INPUT_TOPIC}")
    start_time = time.time()
    data_batch = []
    try:
        while True:
            polled_msg = consumer.poll(1.0)  # Poll for messages

            if polled_msg is None:
                continue
            if polled_msg.error():
                if polled_msg.error().code() == KafkaError._PARTITION_EOF:
                    continue  # End of partition event
                else:
                    print("Consumer error:", polled_msg.error())
                    continue


            msg = json.loads(polled_msg.value().decode('utf-8'))
            data_batch.append(msg)


            if not data_batch:
                continue
            data_batch.append(msg)
            # Process data every 20 seconds
            if time.time() - start_time >= 20:

                # Processing time
                processing_time = datetime.datetime.utcnow().isoformat()

                # Aggregations
                device_type_counter = Counter(record.get("device_type", "unknown") for record in data_batch)
                locale_counter = Counter(record["locale"] for record in data_batch)
                total_count = len(data_batch)

                # compute aggregation records
                device_type_aggregations = [
                    {"processing_time": processing_time, "record_type": "device_type", "count": count, "device_type": device_type}
                    for device_type, count in device_type_counter.items()
                ]

                locale_aggregations = [
                    {"processing_time": processing_time, "record_type": "locale", "count": count, "locale": locale}
                    for locale, count in locale_counter.items()
                ]

                total_aggregation = {
                    "processing_time": processing_time, "record_type": "total", "count": total_count
                }

                # combine all aggregations
                all_aggregations = device_type_aggregations + locale_aggregations + [total_aggregation]

                print(json.dumps(all_aggregations, indent=4))

                if all_aggregations:
                    for aggregation in all_aggregations:
                        # Produce each aggregation record to the output topic as a separate message
                        if aggregation['record_type'] == 'device_type':
                            DEVICE_TYPE_COUNTER.labels(device_type=aggregation['device_type'], topic=analytics_topic).set(aggregation['count'])
                        if aggregation['record_type'] == 'locale':
                            LOCALE_COUNTER.labels(locale=aggregation['locale'], topic=analytics_topic).set(aggregation['count'])
                        if aggregation['record_type'] == 'total':
                            TOTAL_COUNTER.labels(record_type='total', topic=analytics_topic).set(aggregation['count'])
                        producer.produce(
                            analytics_topic,
                            key="aggregations",
                            value=json.dumps(aggregation)  # Send each aggregation record individually
                        )

                # Send metrics to Prometheus
                generate_latest(REGISTRY)
                producer.flush()  # Ensure all messages are sent


                # Reset timer and batch
                start_time = time.time()
                data_batch = []


    except KeyboardInterrupt:
        print("\nShutting down...")
    finally:
        consumer.close()

if __name__ == "__main__":
    start_http_server(9997)
    main()
