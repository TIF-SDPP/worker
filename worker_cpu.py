import pika
import json
import hashlib
import random
import requests
import time
import socket
import numpy as np
from dotenv import load_dotenv
import os

load_dotenv()
POOL_MANAGER_HOST = os.getenv("POOL_MANAGER_HOST")
COORDINADOR_HOST = os.getenv("COORDINADOR_HOST")
RABBITMQ_HOST = os.getenv("RABBITMQ_HOST")

def calcular_sha256(data):

    data_bytes = np.frombuffer(data.encode('utf-8'), dtype=np.uint8)
    hash_val = np.array([0], dtype=np.uint32)
    
    for byte in data_bytes:
        hash_val = (hash_val * 31 + byte) & 0xFFFFFFFF
        hash_val ^= (hash_val << 13) | (hash_val >> 19)
        hash_val = (hash_val * 17) & 0xFFFFFFFF
        hash_val = ((hash_val << 5) | (hash_val >> 27)) & 0xFFFFFFFF
    
    return format(int(hash_val), '08x')

def post_result(data):
    url = f"{COORDINADOR_HOST}/solved_task"
    try:
        response = requests.post(url, json=data)
        print("Post response:", response.text)
    except requests.exceptions.RequestException as e:
        print("Failed to send POST request:", e)

def keep_alive():
    url = f"{POOL_MANAGER_HOST}/keep_alive"
    print(url)
    worker_id = socket.gethostname()  # Usa el nombre del host como identificador único
    is_user = False  # Cambia a True si este worker está local

    while True:  
        try:
            data = {"worker_id": worker_id, "worker_user": str(is_user).lower(),"worker_type": "worker_cpu"}  
            print(data)
            response = requests.post(url, json=data)  
            print("Post response:", response.text)
        except requests.exceptions.RequestException as e:
                print("Failed to send POST request:", e)
        
        time.sleep(10)  # Enviar cada 10 segundos

def on_message_received(ch, method, properties, body):
    data = json.loads(body)
    print(f"Message {data} received")
   
    encontrado = False
    start_time = time.time()
    
    print("Starting mining process")
    while not encontrado:
        numero_aleatorio =str(random.randint(data['random_start'], data['random_end']))
        hash_calculado = calcular_sha256(numero_aleatorio + data['base_string_chain'] + data['blockchain_content'])
        if hash_calculado.startswith(data['prefix']):
            encontrado = True
            processing_time=time.time() - start_time
            
            result_data = {
                "id": data["id"],
                "hash": hash_calculado,
                "number": numero_aleatorio,
                "base_string_chain": data['base_string_chain'],
                "blockchain_content": data['blockchain_content'],
                "timestamp": processing_time,
                "worker_type": "worker_cpu",
                "transactions": data['transactions']
            }

            print(result_data)
            
            # Enviar resultado a Coordinador
            post_result(result_data)

    ch.basic_ack(delivery_tag=method.delivery_tag)
    print(f"Result found and posted for block ID {data['id']} in {processing_time:.2f} seconds")

def connect_rabbitmq():
    while True:
        try:
            connection = pika.BlockingConnection(pika.ConnectionParameters(host=RABBITMQ_HOST, port=5672, credentials=pika.PlainCredentials('guest', 'guest')))
            return connection
        except pika.exceptions.AMQPConnectionError:
            print("Fallo en la conexión, reintentando en 5 segundos...")
            time.sleep(5)



def main():
    connection = connect_rabbitmq()
    channel = connection.channel()
    channel.queue_declare(queue='workers_queue', durable=True)
    # Enlazar la cola al exchange con un binding key (ejemplo: "challenge.#")
    channel.queue_bind(exchange='workers_queue', queue='workers_queue', routing_key='hash_task')
    channel.basic_consume(queue='workers_queue', on_message_callback=on_message_received, auto_ack=False)
    print('Waiting for messages. To exit press CTRL+C')
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("Consumption stopped by user.")
        connection.close()
        print("Connection closed.")

# Run the process_packages method in a separate thread
import threading
process_packages_thread = threading.Thread(target=keep_alive, daemon=True)
process_packages_thread.start()

if __name__ == '__main__':
    main()
