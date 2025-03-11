#!/bin/bash

# Script para aplicar el deployment de Worker CPU en Kubernetes

# Aplicar el archivo de configuración de Kubernetes
kubectl apply -f ./deploy-worker.yaml

# Aplicar el archivo de configuración de Kubernetes
kubectl apply -f ./service-worker.yaml