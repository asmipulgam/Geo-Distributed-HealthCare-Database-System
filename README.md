# Geo-Distributed Health Records Database System

A geo-distributed healthcare database system designed to provide highly available, fault-tolerant, and low-latency access to patient health records across multiple regions.

The system uses **MongoDB**, **CockroachDB**, **SQL**, and **Docker** to support distributed storage, replication, consistency management, and containerized deployment. It is designed for healthcare workloads where availability, reliability, and secure multi-region access are critical.

## Overview

Healthcare applications require fast and reliable access to patient records, even during regional outages or high-traffic periods. This project implements a geo-distributed database architecture that combines the flexibility of MongoDB with the strong consistency and distributed SQL capabilities of CockroachDB.

The system was architected to support:

- Multi-region access to patient health records
- High data availability and fault tolerance
- Replicated database clusters across regions
- Optimized SQL schemas for healthcare metadata
- Reduced cross-region read latency
- Improved query throughput under distributed load

## Key Highlights

- Achieved **99% data availability** through replicated multi-region database deployment
- Reduced **cross-region read latency by 30%**
- Increased **query throughput by 25%** under high distributed load
- Implemented replication and consistency mechanisms across MongoDB and CockroachDB clusters
- Containerized the full system using Docker for easier deployment and testing
- Designed optimized SQL schemas for patient, provider, visit, and record metadata

## Tech Stack

| Technology | Purpose |
|---|---|
| MongoDB | Document storage for flexible health record data |
| CockroachDB | Distributed SQL database for transactional metadata |
| SQL | Schema design, indexing, and query optimization |
| Docker | Containerized deployment and cluster orchestration |
| Docker Compose | Local multi-service environment setup |

## System Architecture

The system uses a hybrid database architecture:

```text
                        +----------------------+
                        |   Healthcare Client  |
                        +----------+-----------+
                                   |
                                   v
                        +----------------------+
                        |   Application/API    |
                        +----------+-----------+
                                   |
              +--------------------+--------------------+
              |                                         |
              v                                         v
+-----------------------------+         +-----------------------------+
|        CockroachDB           |         |          MongoDB             |
| Distributed SQL Cluster      |         | Distributed Document Store   |
+-----------------------------+         +-----------------------------+
| Patient metadata             |         | Clinical notes               |
| Provider records             |         | Lab results                  |
| Appointments                 |         | Medical history documents    |
| Access logs                  |         | Unstructured health records  |
+-----------------------------+         +-----------------------------+
              |                                         |
              v                                         v
      Multi-region replication                  Replica sets / shards
