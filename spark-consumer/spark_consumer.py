from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, lit
from pyspark.sql.types import StructType, StructField, DoubleType, LongType, StringType

# Initialize Spark session
spark = SparkSession.builder \
    .appName("KafkaConsumer") \
    .config("spark.cassandra.connection.host", "cassandra") \
    .config("spark.cassandra.connection.port", "9042") \
    .config("spark.cassandra.auth.username", "cassandra") \
    .config("spark.cassandra.auth.password", "cassandra") \
    .getOrCreate()

# Kafka server and topic
kafka_bootstrap_servers = "kafka:9092"
topic = "electrical_read"

# Schema for the JSON message based on the producer
schema = StructType([
    StructField("time", LongType(), True),
    StructField("global_active_power", DoubleType(), True),
    StructField("global_reactive_power", DoubleType(), True),
    StructField("voltage", DoubleType(), True),
    StructField("global_intensity", DoubleType(), True),
    StructField("sub_metering_1", DoubleType(), True),
    StructField("sub_metering_2", DoubleType(), True),
    StructField("sub_metering_3", DoubleType(), True)
])

# Read data from Kafka topic
kafka_df = spark.readStream \
    .format("kafka") \
    .option("kafka.bootstrap.servers", kafka_bootstrap_servers) \
    .option("subscribe", topic) \
    .load()

# Parse the Kafka 'value' (which is the JSON message) into a structured format
parsed_df = kafka_df.select(
    from_json(col("value").cast("string"), schema).alias("data")
).select("data.*")

parsed_df_with_id = parsed_df.withColumn("sensor_id", lit(1))

# Write the results to the console for testing
# query = parsed_df.writeStream \
#     .outputMode("append") \
#     .format("console") \
#     .start()

query = parsed_df_with_id.writeStream \
    .format("org.apache.spark.sql.cassandra") \
    .option("checkpointLocation", "/tmp/spark/checkpoint") \
    .option("keyspace", "electrical") \
    .option("table", "sensor_data") \
    .outputMode("append") \
    .start()

# Await termination
query.awaitTermination()
