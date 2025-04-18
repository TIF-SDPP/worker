# import pika
# import json
# import hashlib
# import random
# import requests
# import time

# # New hash function
# def enhanced_hash(data):
#     hash_val = 0
#     for byte in data.encode('utf-8'):
#         hash_val = (hash_val * 31 + byte) % (2**32)
#         hash_val ^= (hash_val << 13) | (hash_val >> 19)  # Additional bit rotation
#         hash_val = (hash_val * 17) % (2**32)  # Additional multiplication with a new constant
#         hash_val = ((hash_val << 5) | (hash_val >> 27)) & 0xFFFFFFFF  # Final bitwise operation
#     return hash_val

# def post_result(data):
#     url = "http://localhost:8080/solved_task"
#     try:
#         response = requests.post(url, json=data)
#         print("Post response:", response.text)
#     except requests.exceptions.RequestException as e:
#         print("Failed to send POST request:", e)

# def on_message_received(ch, method, properties, body):
#     data = json.loads(body)
#     print(f"Message {data} received")
   
#     found = False
#     start_time = time.time()
    
#     print("Starting mining process")
#     while not found:
#         random_number = str(random.randint(0, data['random_num_max']))
#         combined_data = f"{random_number}{data['base_string_chain']}{data['blockchain_content']}"
#         calculated_hash = format(enhanced_hash(combined_data), '08x')
#         if calculated_hash.startswith(data['prefix']):
#             found = True
#             print (f"found true ; value: {calculated_hash}")
#             processing_time = time.time() - start_time
            
#             data["processing_time"] = processing_time
#             data["hash"] = calculated_hash
#             data["number"] = random_number
            
#             post_result(data)
#     ch.basic_ack(delivery_tag=method.delivery_tag)
#     print(f"Result found and posted for block ID {data['id']} in {processing_time:.2f} seconds")

# def main():
#     connection = pika.BlockingConnection(
#         pika.ConnectionParameters(host='localhost', port=5672, credentials=pika.PlainCredentials('rabbitmq', 'rabbitmq'))
#     )
#     channel = connection.channel()
#     channel.exchange_declare(exchange='block_challenge', exchange_type='topic', durable=True)
#     result = channel.queue_declare('', exclusive=True)
#     queue_name = result.method.queue
#     channel.queue_bind(exchange='block_challenge', queue=queue_name, routing_key='blocks')
#     channel.basic_consume(queue=queue_name, on_message_callback=on_message_received, auto_ack=False)
#     print('Waiting for messages. To exit press CTRL+C')
#     try:
#         channel.start_consuming()
#     except KeyboardInterrupt:
#         print("Consumption stopped by user.")
#         connection.close()
#         print("Connection closed.")

# if __name__ == '__main__':
#     main()

import pika
import json
import random
import requests
import time
import numpy as np
import socket

try:
    import cupy as cp
    cuda_available = True
    worker_type= "worker_gpu"
    print(" ----------- ")
    print(" GPU WORKER ")
    print(" ----------- ")
except Exception as e:
    print(f"GPU no disponible: {e}")
    cuda_available = False
    worker_type= "worker_cpu"
    print(" ----------- ")
    print(" CPU WORKER ")
    print(" ----------- ")


# New hash function adapted for GPU/CPU
# def enhanced_hash_gpu_cpu(data):
#     if cuda_available:
#         # Asegúrate de manejar correctamente los strings para la GPU
#         data_bytes = cp.asarray(bytearray(data.encode('utf-8')), dtype=cp.uint8)
#         hash_val = cp.zeros(1, dtype=cp.uint32)

#     else:
#         data_bytes = np.frombuffer(data.encode('utf-8'), dtype=np.uint8)
#         hash_val = np.array([0], dtype=np.uint32)
    
#     for byte in data_bytes:
#         hash_val = (hash_val * 31 + byte) % (2**32)
#         hash_val ^= (hash_val << 13) | (hash_val >> 19)
#         hash_val = (hash_val * 17) % (2**32)
#         hash_val = ((hash_val << 5) | (hash_val >> 27)) & 0xFFFFFFFF
    
#     return format(int(hash_val), '08x')

# Longitud máxima esperada de los datos (ajústala según el tamaño promedio de tus strings)
MAX_LENGTH = 256  

hash_kernel = cp.ElementwiseKernel(
    'raw uint8 data, int32 length, uint32 seed', 'uint32 hash_val',
    '''
    hash_val = seed;
    for (int i = 0; i < length; i++) {
        hash_val = (hash_val * 31 + data[i]) % 4294967296;
        hash_val ^= (hash_val << 13) | (hash_val >> 19);
        hash_val = (hash_val * 17) % 4294967296;
        hash_val = ((hash_val << 5) | (hash_val >> 27)) & 0xFFFFFFFF;
    }
    ''',
    'hash_kernel'
)

def enhanced_hash_gpu_parallel(data_list):
    batch_size = len(data_list)

    # Convertir strings a arrays de bytes de tamaño fijo (relleno con ceros si es más corto)
    data_padded = cp.zeros((batch_size, MAX_LENGTH), dtype=cp.uint8)
    lengths = cp.zeros(batch_size, dtype=cp.int32)

    for i, d in enumerate(data_list):
        byte_array = bytearray(d.encode('utf-8'))
        length = min(len(byte_array), MAX_LENGTH)  # Limitar la longitud
        data_padded[i, :length] = cp.asarray(byte_array[:length], dtype=cp.uint8)
        lengths[i] = length

    seeds = cp.arange(batch_size, dtype=cp.uint32)  # Semillas únicas para cada hash

    # Ejecutar el kernel en la GPU
    hash_vals = hash_kernel(data_padded, lengths, seeds)

    return [format(int(h), '08x') for h in hash_vals.get()]  # Convertir a hex y traer a CPU


def keep_alive():
    url = "http://34.73.163.16:8080/keep_alive"
    worker_id = socket.gethostname()  # Usa el nombre del host como identificador único
    is_user = True  # Cambia a True si este worker está local

    while True:  # Bucle infinito
        try:
            data = {"worker_id": worker_id, "worker_user": str(is_user).lower(),"worker_type": "worker_gpu"}  
            response = requests.post(url, json=data)  # Enviar el JSON en el POST
            print("Post response:", response.text)
        except requests.exceptions.RequestException as e:
            print("Failed to send POST request:", e)
        
        time.sleep(10)  # Espera 10 segundos antes de repetir

def post_result(data):
    url = "http://35.196.10.205:8080/solved_task"
    try:
        response = requests.post(url, json=data)
        print("Post response:", response.text)
    except requests.exceptions.RequestException as e:
        print("Failed to send POST request:", e)

# def on_message_received(ch, method, properties, body):
#     data = json.loads(body)
#     print(f"Received subtask: {data['random_start']} - {data['random_end']}")
   
#     found = False
#     start_time = time.time()
    
#     print("Starting mining process")
#     while not found:
#         random_number = str(random.randint(data['random_start'], data['random_end']))
#         combined_data = f"{random_number}{data['base_string_chain']}{data['blockchain_content']}"
#         calculated_hash = enhanced_hash_gpu_cpu(combined_data)
        
#         if calculated_hash.startswith(data['prefix']):
#             found = True
#             processing_time = time.time() - start_time
            
#             result_data = {
#                 "id": data["id"],
#                 "hash": calculated_hash,
#                 "number": random_number,
#                 "base_string_chain": data['base_string_chain'],
#                 "blockchain_content": data['blockchain_content'],
#                 "timestamp": processing_time,
#                 "worker_type": worker_type
#             }
            
#             # Enviar resultado a Coordinador
#             post_result(result_data)

#     ch.basic_ack(delivery_tag=method.delivery_tag)
#     print(f"Result found and posted for block ID {data['id']} in {processing_time:.2f} seconds")

def on_message_received(ch, method, properties, body):
    data = json.loads(body)
    print(f"Received subtask: {data['random_start']} - {data['random_end']}")
   
    found = False
    start_time = time.time()
    
    print("Starting mining process")
    batch_size = 10000  # Prueba 10,000 valores en paralelo

    while not found:
        random_numbers = [str(random.randint(data['random_start'], data['random_end'])) for _ in range(batch_size)]
        combined_data = [f"{rn}{data['base_string_chain']}{data['blockchain_content']}" for rn in random_numbers]
    
        hash_results = enhanced_hash_gpu_parallel(combined_data)

        for rn, h in zip(random_numbers, hash_results):
            if h.startswith(data['prefix']):
                found = True
                processing_time = time.time() - start_time

                result_data = {
                    "id": data["id"],
                    "hash": h,
                    "number": rn,
                    "base_string_chain": data['base_string_chain'],
                    "blockchain_content": data['blockchain_content'],
                    "timestamp": processing_time,
                    "worker_type": worker_type
                }

            post_result(result_data)
            break  # Salimos del loop si encontramos el hash correcto

    ch.basic_ack(delivery_tag=method.delivery_tag)
    print(f"Result found and posted for block ID {data['id']} in {processing_time:.2f} seconds")



def main():
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host='34.148.205.191', port=5672, credentials=pika.PlainCredentials('guest', 'guest'))
    )
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
