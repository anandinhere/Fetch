import os
import json
import time
import uuid
import random
from confluent_kafka import Producer
from kafka.admin import KafkaAdminClient, NewTopic

bootstrap_servers = os.environ.get('BOOTSTRAP_SERVERS', 'localhost:9092')
topic = os.environ.get('KAFKA_TOPIC', 'user-login')

# Create a Kafka producer configuration
producer_config = {
    'bootstrap.servers': bootstrap_servers,
}

# Create a Kafka producer instance
producer = Producer(producer_config)

# Function to generate a random message
def generate_random_message():
    user_id = str(uuid.uuid4())
    app_version = '2.3.0'
    # Occasionally omit the device_type field (e.g., 5% of the time)
    if random.random() <= 0.05:
        device_type = None
    else:
        device_type = random.choice(['android', 'iOS'])
    ip = '.'.join(map(str, (random.randint(0, 255) for _ in range(4))))
    locale = random.choice(['AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
                            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
                            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
                            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
                            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY'])
    device_id = str(uuid.uuid4())
    timestamp = int(time.time())

    message = {
        "user_id": user_id,
        "app_version": app_version,
        "ip": ip,
        "locale": locale,
        "device_id": device_id,
        "timestamp": timestamp
    }

    # Add the device_type field if it's not None
    if device_type is not None:
        message["device_type"] = device_type

    return json.dumps(message)

# Create an AdminClient to manage topics
admin_client = KafkaAdminClient(bootstrap_servers=bootstrap_servers)

# Check if the 'user-login' topic exists
topic_exists = topic in admin_client.list_topics()

# Create the 'user-login' topic if it doesn't exist
if not topic_exists:
    new_topic = NewTopic(name=topic, num_partitions=1, replication_factor=1)
    try:
        admin_client.create_topics(new_topics=[new_topic], validate_only=False)
    except TopicAlreadyExistsError:
        pass

# Produce random messages to Kafka
try:
    while True:
        message = generate_random_message()
        producer.produce(topic, key=str(uuid.uuid4()), value=message)
        producer.flush()
        print(f"Produced message: {message}")
        time.sleep(0.5)

except KeyboardInterrupt:
    pass

# Close the Kafka producer
producer.flush(30)
producer.close()