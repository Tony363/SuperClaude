# Real-Time Chat Application Architecture

**Version:** 1.0
**Author:** System Architect
**Date:** 2026-01-11
**Status:** Proposed

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Requirements Analysis](#requirements-analysis)
3. [Architecture Overview](#architecture-overview)
4. [Component Design](#component-design)
5. [Data Flow](#data-flow)
6. [Technology Stack](#technology-stack)
7. [Data Models](#data-models)
8. [Scalability Strategy](#scalability-strategy)
9. [Security Architecture](#security-architecture)
10. [Deployment Architecture](#deployment-architecture)
11. [Architecture Decision Records](#architecture-decision-records)

---

## 1. Executive Summary

This document presents a scalable, event-driven microservices architecture for a real-time chat application capable of supporting millions of concurrent users. The design prioritizes:

- **Sub-100ms message delivery** for real-time experience
- **Horizontal scalability** to handle millions of concurrent connections
- **High availability** (99.9%+ uptime)
- **Data consistency** with eventual consistency model
- **Security** with end-to-end encryption support

---

## 2. Requirements Analysis

### Functional Requirements

| Requirement | Priority | Description |
|-------------|----------|-------------|
| Real-time messaging | P0 | Instant message delivery between users |
| Message persistence | P0 | Store and retrieve chat history |
| User presence | P0 | Online/offline/typing indicators |
| Group chat | P0 | Multi-participant conversations |
| Media sharing | P1 | Images, files, videos |
| Push notifications | P1 | Offline message delivery |
| Read receipts | P1 | Message delivery/read confirmations |
| Search | P2 | Full-text message search |
| Reactions | P2 | Emoji reactions to messages |

### Non-Functional Requirements

| Attribute | Target | Rationale |
|-----------|--------|-----------|
| Latency | <100ms p99 | Real-time user experience |
| Throughput | 1M+ messages/sec | High-volume support |
| Concurrent connections | 10M+ | Scale for growth |
| Availability | 99.9% | ~8.7 hours downtime/year |
| Message durability | 99.999% | No message loss |
| Recovery time | <30 seconds | Fast failover |

### Constraints

- Multi-region deployment for global users
- GDPR/CCPA compliance for data handling
- Mobile-first with offline support
- Cost-effective infrastructure

---

## 3. Architecture Overview

### Architectural Pattern: Event-Driven Microservices

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                    │
├─────────────────────────────────────────────────────────────────────────────┤
│   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   ┌─────────────┐   │
│   │   Web App   │   │  iOS App    │   │ Android App │   │  Desktop    │   │
│   │  (React)    │   │  (Swift)    │   │  (Kotlin)   │   │  (Electron) │   │
│   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   └──────┬──────┘   │
│          │                 │                 │                 │           │
│          └─────────────────┴────────┬────────┴─────────────────┘           │
│                                     │                                       │
│                              WebSocket/HTTP                                 │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼───────────────────────────────────────┐
│                           EDGE/GATEWAY LAYER                                 │
├─────────────────────────────────────┼───────────────────────────────────────┤
│   ┌─────────────────────────────────┴───────────────────────────────────┐   │
│   │                        CDN (CloudFlare)                              │   │
│   │              Static assets, DDoS protection, Edge caching            │   │
│   └─────────────────────────────────┬───────────────────────────────────┘   │
│                                     │                                       │
│   ┌─────────────────────────────────┴───────────────────────────────────┐   │
│   │                     Load Balancer (L4/L7)                            │   │
│   │         Connection routing, SSL termination, Health checks           │   │
│   └─────────────────────────────────┬───────────────────────────────────┘   │
│                                     │                                       │
│   ┌─────────────────────────────────┴───────────────────────────────────┐   │
│   │                   API Gateway (Kong/AWS API GW)                      │   │
│   │     Rate limiting, Authentication, Request routing, Monitoring       │   │
│   └─────────────────────────────────┬───────────────────────────────────┘   │
└─────────────────────────────────────┼───────────────────────────────────────┘
                                      │
┌─────────────────────────────────────┼───────────────────────────────────────┐
│                           CONNECTION LAYER                                   │
├─────────────────────────────────────┼───────────────────────────────────────┤
│   ┌─────────────────────────────────┴───────────────────────────────────┐   │
│   │                    WebSocket Gateway Service                         │   │
│   │                                                                      │   │
│   │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │   │
│   │   │  WS-1   │ │  WS-2   │ │  WS-3   │ │  WS-4   │ │  WS-N   │      │   │
│   │   │ 50K     │ │ 50K     │ │ 50K     │ │ 50K     │ │ 50K     │      │   │
│   │   │ conns   │ │ conns   │ │ conns   │ │ conns   │ │ conns   │      │   │
│   │   └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘ └────┬────┘      │   │
│   │        └───────────┴───────────┼───────────┴───────────┘            │   │
│   └────────────────────────────────┼────────────────────────────────────┘   │
└────────────────────────────────────┼────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                          MESSAGE BROKER LAYER                                │
├────────────────────────────────────┼────────────────────────────────────────┤
│   ┌────────────────────────────────┴────────────────────────────────────┐   │
│   │                     Apache Kafka Cluster                             │   │
│   │                                                                      │   │
│   │   Topics:                                                            │   │
│   │   ├── chat.messages.{room_id}   (Partitioned by room)               │   │
│   │   ├── chat.presence             (User online/offline events)        │   │
│   │   ├── chat.notifications        (Push notification events)          │   │
│   │   ├── chat.typing               (Typing indicator events)           │   │
│   │   └── chat.receipts             (Read/delivery receipts)            │   │
│   │                                                                      │   │
│   └─────────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                           MICROSERVICES LAYER                                │
├────────────────────────────────────┴────────────────────────────────────────┤
│                                                                              │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│   │   Message   │ │   User      │ │  Presence   │ │   Room      │          │
│   │   Service   │ │   Service   │ │   Service   │ │   Service   │          │
│   │             │ │             │ │             │ │             │          │
│   │ - Send msg  │ │ - Auth      │ │ - Online/   │ │ - Create    │          │
│   │ - History   │ │ - Profile   │ │   Offline   │ │ - Join/Leave│          │
│   │ - Search    │ │ - Settings  │ │ - Typing    │ │ - Members   │          │
│   │ - Reactions │ │ - Contacts  │ │ - Last seen │ │ - Permissions│         │
│   └──────┬──────┘ └──────┬──────┘ └──────┬──────┘ └──────┬──────┘          │
│          │               │               │               │                  │
│   ┌──────┴───────────────┴───────────────┴───────────────┴──────┐          │
│   │                                                              │          │
│   ┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐          │
│   │Notification │ │   Media     │ │   Search    │ │  Analytics  │          │
│   │   Service   │ │   Service   │ │   Service   │ │   Service   │          │
│   │             │ │             │ │             │ │             │          │
│   │ - Push      │ │ - Upload    │ │ - Index     │ │ - Events    │          │
│   │ - Email     │ │ - Process   │ │ - Query     │ │ - Metrics   │          │
│   │ - SMS       │ │ - CDN       │ │ - Filters   │ │ - Reports   │          │
│   └─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘          │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
                                     │
┌────────────────────────────────────┼────────────────────────────────────────┐
│                             DATA LAYER                                       │
├────────────────────────────────────┴────────────────────────────────────────┤
│                                                                              │
│   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐       │
│   │   Redis Cluster  │   │  Cassandra/ScyllaDB │   │   PostgreSQL     │       │
│   │                  │   │                  │   │                  │       │
│   │ - Session cache  │   │ - Messages       │   │ - Users          │       │
│   │ - Presence       │   │ - Chat history   │   │ - Rooms          │       │
│   │ - Rate limits    │   │ - Attachments    │   │ - Permissions    │       │
│   │ - Pub/Sub        │   │   metadata       │   │ - Settings       │       │
│   │ - Connection map │   │                  │   │                  │       │
│   └──────────────────┘   └──────────────────┘   └──────────────────┘       │
│                                                                              │
│   ┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐       │
│   │  Elasticsearch   │   │    S3/MinIO      │   │   TimescaleDB    │       │
│   │                  │   │                  │   │                  │       │
│   │ - Message search │   │ - Media files    │   │ - Metrics        │       │
│   │ - User search    │   │ - Attachments    │   │ - Analytics      │       │
│   │ - Full-text      │   │ - Backups        │   │ - Time-series    │       │
│   └──────────────────┘   └──────────────────┘   └──────────────────┘       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. Component Design

### 4.1 WebSocket Gateway Service

**Purpose:** Manage persistent WebSocket connections and route messages.

**Responsibilities:**
- Maintain 50,000+ connections per instance
- Authenticate connections via JWT
- Route messages to appropriate Kafka topics
- Handle connection lifecycle (connect, disconnect, reconnect)
- Implement heartbeat/ping-pong for connection health

**Key Design Decisions:**
- Stateless design (connection state in Redis)
- Horizontal scaling based on connection count
- Graceful connection draining during deployments

```typescript
// WebSocket Gateway - Core Connection Handler
interface WebSocketConnection {
  connectionId: string;
  userId: string;
  deviceId: string;
  serverId: string;
  connectedAt: Date;
  lastHeartbeat: Date;
  subscribedRooms: string[];
}

class WebSocketGateway {
  private connections: Map<string, WebSocket>;
  private redis: RedisCluster;
  private kafka: KafkaProducer;

  async handleConnection(ws: WebSocket, token: string): Promise<void> {
    const user = await this.validateToken(token);
    const connectionId = generateUUID();

    // Register connection in Redis for cross-server routing
    await this.redis.hset(`connections:${user.id}`, {
      [connectionId]: {
        serverId: this.serverId,
        deviceId: user.deviceId,
        connectedAt: Date.now()
      }
    });

    // Subscribe to user's rooms
    const rooms = await this.getRoomsForUser(user.id);
    await this.subscribeToRooms(connectionId, rooms);

    // Publish presence event
    await this.kafka.send('chat.presence', {
      userId: user.id,
      status: 'online',
      timestamp: Date.now()
    });
  }

  async routeMessage(message: IncomingMessage): Promise<void> {
    const topic = `chat.messages.${message.roomId}`;
    await this.kafka.send(topic, {
      messageId: generateUUID(),
      roomId: message.roomId,
      senderId: message.userId,
      content: message.content,
      timestamp: Date.now(),
      type: message.type
    });
  }
}
```

### 4.2 Message Service

**Purpose:** Handle message processing, storage, and retrieval.

**Responsibilities:**
- Process messages from Kafka
- Persist to Cassandra/ScyllaDB
- Index in Elasticsearch
- Handle reactions and edits
- Manage message lifecycle (TTL, deletion)

```typescript
// Message Service - Core Processing
interface Message {
  messageId: string;
  roomId: string;
  senderId: string;
  content: string;
  contentType: 'text' | 'image' | 'file' | 'system';
  metadata?: Record<string, any>;
  replyTo?: string;
  reactions: Map<string, string[]>;
  createdAt: Date;
  editedAt?: Date;
  deletedAt?: Date;
}

class MessageService {
  private cassandra: CassandraClient;
  private elasticsearch: ElasticsearchClient;
  private kafka: KafkaConsumer;

  async processMessage(event: KafkaMessage): Promise<void> {
    const message = parseMessage(event);

    // Store in Cassandra (optimized for time-series writes)
    await this.cassandra.execute(
      `INSERT INTO messages (room_id, message_id, sender_id, content,
       content_type, created_at) VALUES (?, ?, ?, ?, ?, ?)`,
      [message.roomId, message.messageId, message.senderId,
       message.content, message.contentType, message.createdAt]
    );

    // Index for search (async, eventual consistency OK)
    await this.elasticsearch.index({
      index: 'messages',
      id: message.messageId,
      body: {
        roomId: message.roomId,
        senderId: message.senderId,
        content: message.content,
        createdAt: message.createdAt
      }
    });

    // Publish delivery receipt
    await this.publishReceipt(message, 'delivered');
  }

  async getHistory(roomId: string, before?: Date, limit = 50): Promise<Message[]> {
    const query = before
      ? `SELECT * FROM messages WHERE room_id = ? AND created_at < ?
         ORDER BY created_at DESC LIMIT ?`
      : `SELECT * FROM messages WHERE room_id = ?
         ORDER BY created_at DESC LIMIT ?`;

    return this.cassandra.execute(query,
      before ? [roomId, before, limit] : [roomId, limit]);
  }
}
```

### 4.3 Presence Service

**Purpose:** Track user online/offline status and typing indicators.

**Responsibilities:**
- Maintain real-time presence state
- Handle typing indicators with TTL
- Publish presence changes to subscribers
- Aggregate presence across devices

```typescript
// Presence Service
interface UserPresence {
  userId: string;
  status: 'online' | 'away' | 'offline';
  lastSeen: Date;
  devices: DevicePresence[];
  customStatus?: string;
}

class PresenceService {
  private redis: RedisCluster;
  private kafka: KafkaProducer;

  async updatePresence(userId: string, status: string): Promise<void> {
    const key = `presence:${userId}`;
    const presence = {
      status,
      lastSeen: Date.now(),
      updatedAt: Date.now()
    };

    // Set with TTL (auto-expire if no heartbeat)
    await this.redis.setex(key, 300, JSON.stringify(presence));

    // Publish to subscribers
    await this.kafka.send('chat.presence', {
      userId,
      status,
      timestamp: Date.now()
    });
  }

  async setTyping(userId: string, roomId: string): Promise<void> {
    const key = `typing:${roomId}:${userId}`;
    // Typing indicator expires after 3 seconds
    await this.redis.setex(key, 3, '1');

    await this.kafka.send('chat.typing', {
      userId,
      roomId,
      isTyping: true,
      timestamp: Date.now()
    });
  }

  async getPresenceBatch(userIds: string[]): Promise<UserPresence[]> {
    const pipeline = this.redis.pipeline();
    userIds.forEach(id => pipeline.get(`presence:${id}`));
    const results = await pipeline.exec();

    return userIds.map((id, i) => ({
      userId: id,
      ...JSON.parse(results[i] || '{"status":"offline"}')
    }));
  }
}
```

### 4.4 Room Service

**Purpose:** Manage chat rooms, memberships, and permissions.

```typescript
// Room Service
interface Room {
  roomId: string;
  type: 'direct' | 'group' | 'channel';
  name?: string;
  description?: string;
  avatar?: string;
  createdBy: string;
  createdAt: Date;
  settings: RoomSettings;
}

interface RoomMember {
  userId: string;
  roomId: string;
  role: 'owner' | 'admin' | 'member';
  joinedAt: Date;
  lastReadAt: Date;
  notifications: 'all' | 'mentions' | 'none';
}

class RoomService {
  private postgres: PostgresClient;
  private redis: RedisCluster;

  async createRoom(input: CreateRoomInput): Promise<Room> {
    return this.postgres.transaction(async (tx) => {
      // Create room
      const room = await tx.query(
        `INSERT INTO rooms (room_id, type, name, created_by, created_at)
         VALUES ($1, $2, $3, $4, $5) RETURNING *`,
        [generateUUID(), input.type, input.name, input.createdBy, new Date()]
      );

      // Add creator as owner
      await tx.query(
        `INSERT INTO room_members (user_id, room_id, role, joined_at)
         VALUES ($1, $2, 'owner', $3)`,
        [input.createdBy, room.roomId, new Date()]
      );

      // Add other members
      for (const memberId of input.memberIds || []) {
        await tx.query(
          `INSERT INTO room_members (user_id, room_id, role, joined_at)
           VALUES ($1, $2, 'member', $3)`,
          [memberId, room.roomId, new Date()]
        );
      }

      // Cache room members for fast lookup
      await this.redis.sadd(
        `room:${room.roomId}:members`,
        [input.createdBy, ...(input.memberIds || [])]
      );

      return room;
    });
  }

  async getRoomMembers(roomId: string): Promise<string[]> {
    // Try cache first
    const cached = await this.redis.smembers(`room:${roomId}:members`);
    if (cached.length > 0) return cached;

    // Fallback to database
    const result = await this.postgres.query(
      'SELECT user_id FROM room_members WHERE room_id = $1',
      [roomId]
    );

    const memberIds = result.rows.map(r => r.user_id);
    await this.redis.sadd(`room:${roomId}:members`, memberIds);
    return memberIds;
  }
}
```

### 4.5 Notification Service

**Purpose:** Handle push notifications for offline users.

```typescript
// Notification Service
class NotificationService {
  private firebase: FirebaseAdmin;
  private apns: APNSClient;
  private kafka: KafkaConsumer;

  async processNotification(event: KafkaMessage): Promise<void> {
    const notification = parseNotification(event);

    // Get user's device tokens
    const devices = await this.getDeviceTokens(notification.userId);

    // Filter out devices with active WebSocket connections
    const offlineDevices = await this.filterOfflineDevices(devices);

    if (offlineDevices.length === 0) return;

    // Send platform-specific notifications
    const androidDevices = offlineDevices.filter(d => d.platform === 'android');
    const iosDevices = offlineDevices.filter(d => d.platform === 'ios');

    await Promise.all([
      this.sendFCM(androidDevices, notification),
      this.sendAPNS(iosDevices, notification)
    ]);
  }

  private async sendFCM(devices: Device[], notification: Notification) {
    if (devices.length === 0) return;

    await this.firebase.messaging().sendEachForMulticast({
      tokens: devices.map(d => d.token),
      notification: {
        title: notification.title,
        body: notification.body
      },
      data: {
        roomId: notification.roomId,
        messageId: notification.messageId,
        type: notification.type
      },
      android: {
        priority: 'high',
        ttl: 86400000 // 24 hours
      }
    });
  }
}
```

---

## 5. Data Flow

### 5.1 Message Send Flow

```
┌──────────┐     ┌─────────────┐     ┌─────────┐     ┌─────────────┐
│  Client  │────▶│  WebSocket  │────▶│  Kafka  │────▶│   Message   │
│          │     │   Gateway   │     │         │     │   Service   │
└──────────┘     └─────────────┘     └─────────┘     └──────┬──────┘
                                                            │
                 ┌──────────────────────────────────────────┘
                 ▼
    ┌────────────────────────────────────────────────────────────┐
    │                                                            │
    ▼                        ▼                       ▼           ▼
┌─────────┐           ┌───────────┐           ┌─────────┐  ┌─────────┐
│Cassandra│           │Elasticsearch│          │  Redis  │  │  Kafka  │
│ (Store) │           │  (Index)   │           │(Delivery│  │(Fanout) │
│         │           │            │           │ Receipt)│  │         │
└─────────┘           └───────────┘           └─────────┘  └────┬────┘
                                                                 │
    ┌────────────────────────────────────────────────────────────┘
    │
    ▼
┌─────────────┐     ┌──────────┐
│  WebSocket  │────▶│ Recipients│
│   Gateway   │     │ (Clients) │
└─────────────┘     └──────────┘
```

**Sequence:**
1. Client sends message via WebSocket
2. Gateway validates, adds metadata, publishes to Kafka
3. Message Service consumes, stores in Cassandra
4. Elasticsearch indexes for search (async)
5. Delivery receipts published to Kafka
6. Gateway fans out to all room members' connections
7. Offline users receive push notifications

### 5.2 Presence Update Flow

```
┌──────────┐     ┌─────────────┐     ┌─────────┐     ┌─────────────┐
│  Client  │────▶│  WebSocket  │────▶│  Redis  │     │  Presence   │
│ (Connect)│     │   Gateway   │     │ (Cache) │     │   Service   │
└──────────┘     └─────────────┘     └────┬────┘     └──────┬──────┘
                                          │                 │
                                          └────────┬────────┘
                                                   │
                                                   ▼
                                             ┌─────────┐
                                             │  Kafka  │
                                             │(Presence│
                                             │  Topic) │
                                             └────┬────┘
                                                  │
                        ┌─────────────────────────┼─────────────────────────┐
                        ▼                         ▼                         ▼
                 ┌─────────────┐           ┌─────────────┐           ┌─────────┐
                 │  WebSocket  │           │  WebSocket  │           │  Other  │
                 │  Gateway 1  │           │  Gateway 2  │           │Services │
                 └──────┬──────┘           └──────┬──────┘           └─────────┘
                        │                         │
                        ▼                         ▼
                 ┌──────────┐             ┌──────────┐
                 │ Contacts │             │ Contacts │
                 │(Subscribed│            │(Subscribed│
                 │  Users)   │            │  Users)   │
                 └──────────┘             └──────────┘
```

### 5.3 Connection Routing (Cross-Server)

```
┌─────────────────────────────────────────────────────────────────┐
│                     Connection Registry (Redis)                  │
│                                                                 │
│  user:123 → {                                                   │
│    conn_abc: { server: "ws-1", device: "mobile" }              │
│    conn_def: { server: "ws-3", device: "desktop" }             │
│  }                                                              │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
   ┌─────────┐           ┌─────────┐          ┌─────────┐
   │  WS-1   │           │  WS-2   │          │  WS-3   │
   │ 50K     │           │ 50K     │          │ 50K     │
   │ conns   │           │ conns   │          │ conns   │
   └────┬────┘           └─────────┘          └────┬────┘
        │                                          │
        ▼                                          ▼
   ┌─────────┐                                ┌─────────┐
   │User 123 │                                │User 123 │
   │(Mobile) │                                │(Desktop)│
   └─────────┘                                └─────────┘
```

---

## 6. Technology Stack

### 6.1 Technology Selection Matrix

| Layer | Technology | Alternatives Considered | Selection Rationale |
|-------|------------|------------------------|---------------------|
| **Gateway** | Node.js + ws | Go, Rust, Erlang | High concurrency, ecosystem, team expertise |
| **Services** | Go | Node.js, Java, Rust | Performance, simplicity, great for microservices |
| **Message Broker** | Apache Kafka | RabbitMQ, Redis Streams, Pulsar | Durability, ordering, replay capability |
| **Cache** | Redis Cluster | Memcached, Hazelcast | Rich data structures, pub/sub, clustering |
| **Messages DB** | ScyllaDB | Cassandra, DynamoDB, MongoDB | High write throughput, time-series optimized |
| **Metadata DB** | PostgreSQL | MySQL, CockroachDB | ACID, complex queries, mature ecosystem |
| **Search** | Elasticsearch | Meilisearch, Typesense, OpenSearch | Full-text, scalable, battle-tested |
| **Object Storage** | S3/MinIO | GCS, Azure Blob | Cost-effective, CDN integration |
| **Container** | Kubernetes | ECS, Docker Swarm | Orchestration, scaling, ecosystem |
| **Monitoring** | Prometheus + Grafana | Datadog, New Relic | Cost, flexibility, open-source |

### 6.2 Detailed Stack

```yaml
# Infrastructure
container_orchestration: Kubernetes (EKS/GKE)
service_mesh: Istio (optional, for advanced traffic management)
ingress: NGINX Ingress Controller
ssl: Let's Encrypt / AWS ACM
dns: Route53 / CloudFlare

# Application Layer
websocket_gateway:
  runtime: Node.js 20 LTS
  framework: Fastify + ws
  language: TypeScript

microservices:
  runtime: Go 1.22+
  framework: Chi / Gin
  grpc: buf.build for service-to-service

# Data Layer
message_broker:
  primary: Apache Kafka 3.x
  partitions_strategy: By room_id (ordering guarantee)
  retention: 7 days (configurable)

cache:
  primary: Redis 7.x Cluster
  mode: Cluster (6+ nodes)
  persistence: RDB + AOF

message_storage:
  primary: ScyllaDB
  replication_factor: 3
  consistency: LOCAL_QUORUM

metadata_storage:
  primary: PostgreSQL 16
  connection_pool: PgBouncer
  high_availability: Patroni

search:
  primary: Elasticsearch 8.x
  shards: Dynamic based on data volume

object_storage:
  primary: AWS S3 / MinIO
  cdn: CloudFront / CloudFlare

# Observability
metrics: Prometheus + Grafana
logging: Loki + Promtail
tracing: Jaeger / Tempo
alerting: Alertmanager + PagerDuty
```

---

## 7. Data Models

### 7.1 PostgreSQL Schema (Metadata)

```sql
-- Users table
CREATE TABLE users (
    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username VARCHAR(50) UNIQUE NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    display_name VARCHAR(100),
    avatar_url TEXT,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);

-- Rooms table
CREATE TABLE rooms (
    room_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type VARCHAR(20) NOT NULL CHECK (type IN ('direct', 'group', 'channel')),
    name VARCHAR(100),
    description TEXT,
    avatar_url TEXT,
    created_by UUID REFERENCES users(user_id),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    settings JSONB DEFAULT '{}'::jsonb
);

CREATE INDEX idx_rooms_type ON rooms(type);
CREATE INDEX idx_rooms_created_by ON rooms(created_by);

-- Room members
CREATE TABLE room_members (
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    room_id UUID REFERENCES rooms(room_id) ON DELETE CASCADE,
    role VARCHAR(20) DEFAULT 'member' CHECK (role IN ('owner', 'admin', 'member')),
    joined_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_read_at TIMESTAMP WITH TIME ZONE,
    notification_preference VARCHAR(20) DEFAULT 'all',
    PRIMARY KEY (user_id, room_id)
);

CREATE INDEX idx_room_members_room ON room_members(room_id);
CREATE INDEX idx_room_members_user ON room_members(user_id);

-- Device tokens for push notifications
CREATE TABLE device_tokens (
    token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
    device_id VARCHAR(255) NOT NULL,
    platform VARCHAR(20) NOT NULL CHECK (platform IN ('ios', 'android', 'web')),
    token TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    last_used_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE (user_id, device_id)
);

CREATE INDEX idx_device_tokens_user ON device_tokens(user_id);
```

### 7.2 ScyllaDB Schema (Messages)

```cql
-- Keyspace
CREATE KEYSPACE chat WITH replication = {
    'class': 'NetworkTopologyStrategy',
    'us-east-1': 3,
    'eu-west-1': 3
};

-- Messages table (optimized for time-series reads)
CREATE TABLE chat.messages (
    room_id UUID,
    bucket TEXT,  -- YYYY-MM-DD for time bucketing
    message_id TIMEUUID,
    sender_id UUID,
    content TEXT,
    content_type TEXT,
    metadata MAP<TEXT, TEXT>,
    reply_to UUID,
    created_at TIMESTAMP,
    edited_at TIMESTAMP,
    deleted BOOLEAN,
    PRIMARY KEY ((room_id, bucket), message_id)
) WITH CLUSTERING ORDER BY (message_id DESC)
  AND compaction = {'class': 'TimeWindowCompactionStrategy',
                    'compaction_window_size': 1,
                    'compaction_window_unit': 'DAYS'}
  AND default_time_to_live = 31536000;  -- 1 year TTL

-- Message reactions
CREATE TABLE chat.message_reactions (
    room_id UUID,
    message_id TIMEUUID,
    user_id UUID,
    reaction TEXT,
    created_at TIMESTAMP,
    PRIMARY KEY ((room_id, message_id), user_id, reaction)
);

-- Read receipts (last read position per user per room)
CREATE TABLE chat.read_receipts (
    room_id UUID,
    user_id UUID,
    last_read_message_id TIMEUUID,
    read_at TIMESTAMP,
    PRIMARY KEY (room_id, user_id)
);
```

### 7.3 Redis Data Structures

```redis
# Connection registry
HSET connections:{user_id} {connection_id} '{"server":"ws-1","device":"mobile","connected_at":1234567890}'

# Presence
SETEX presence:{user_id} 300 '{"status":"online","last_seen":1234567890}'

# Typing indicators (auto-expire in 3 seconds)
SETEX typing:{room_id}:{user_id} 3 "1"

# Room members (fast lookup)
SADD room:{room_id}:members {user_id_1} {user_id_2} {user_id_3}

# User's rooms (for quick room list)
SADD user:{user_id}:rooms {room_id_1} {room_id_2}

# Rate limiting
SETEX ratelimit:{user_id}:messages 60 {count}

# Session data
HSET session:{session_id} user_id {user_id} expires_at {timestamp}
```

---

## 8. Scalability Strategy

### 8.1 Horizontal Scaling Triggers

| Component | Metric | Scale-Up Threshold | Scale-Down Threshold |
|-----------|--------|-------------------|---------------------|
| WebSocket Gateway | Connections/Instance | >40,000 | <20,000 |
| Message Service | CPU Utilization | >70% | <30% |
| Kafka | Partition Lag | >10,000 | N/A |
| Redis | Memory Usage | >70% | <40% |
| ScyllaDB | Storage/Node | >70% | N/A |

### 8.2 Scaling Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Auto-Scaling Configuration                    │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  WebSocket Gateway:                                             │
│  ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ┌─────┐ ... ┌─────┐          │
│  │WS-1 │ │WS-2 │ │WS-3 │ │WS-4 │ │WS-5 │     │WS-N │          │
│  │50K  │ │50K  │ │50K  │ │50K  │ │50K  │     │50K  │          │
│  └─────┘ └─────┘ └─────┘ └─────┘ └─────┘     └─────┘          │
│                                                                 │
│  Min: 3 instances | Max: 200 instances | Scale: +2/-1          │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Message Service:                                               │
│  ┌─────┐ ┌─────┐ ┌─────┐ ... ┌─────┐                          │
│  │MS-1 │ │MS-2 │ │MS-3 │     │MS-N │                          │
│  └─────┘ └─────┘ └─────┘     └─────┘                          │
│                                                                 │
│  Min: 2 instances | Max: 50 instances | Scale: CPU-based       │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  Kafka Cluster:                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Broker 1  │  Broker 2  │  Broker 3  │ ... │ Broker N   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Partitions: Scale by adding partitions (not removable)        │
│  Brokers: Add for storage/throughput                           │
│                                                                 │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ScyllaDB Cluster:                                              │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  Node 1   │  Node 2   │  Node 3   │ ... │  Node N      │   │
│  │  (Shard)  │  (Shard)  │  (Shard)  │     │  (Shard)     │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  Scale: Add nodes, data auto-rebalances                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### 8.3 Partitioning Strategy

**Kafka Topics:**
- `chat.messages.{room_id}` - Partition by room_id hash
  - Ensures message ordering within a room
  - Allows parallel processing across rooms
- `chat.presence` - Partition by user_id hash
- `chat.notifications` - Partition by user_id hash

**ScyllaDB:**
- Partition key: `(room_id, bucket)`
- Bucket = date (YYYY-MM-DD) for time-based data distribution
- Prevents hot partitions for high-traffic rooms

### 8.4 Connection Draining

```yaml
# Kubernetes deployment with graceful shutdown
apiVersion: apps/v1
kind: Deployment
metadata:
  name: websocket-gateway
spec:
  replicas: 10
  strategy:
    type: RollingUpdate
    rollingUpdate:
      maxUnavailable: 1
      maxSurge: 2
  template:
    spec:
      terminationGracePeriodSeconds: 300  # 5 minutes for connection drain
      containers:
      - name: ws-gateway
        lifecycle:
          preStop:
            exec:
              command: ["/bin/sh", "-c", "sleep 10 && /app/drain-connections"]
```

---

## 9. Security Architecture

### 9.1 Authentication Flow

```
┌──────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Client  │────▶│  API Gateway│────▶│    Auth     │────▶│    User     │
│          │     │             │     │   Service   │     │   Service   │
└──────────┘     └─────────────┘     └──────┬──────┘     └─────────────┘
                                            │
                                            ▼
                                     ┌─────────────┐
                                     │    JWT      │
                                     │   Token     │
                                     │ (15min exp) │
                                     └─────────────┘
                                            │
     ┌──────────────────────────────────────┘
     │
     ▼
┌──────────┐     ┌─────────────┐
│  Client  │────▶│  WebSocket  │  (JWT in connection handshake)
│          │     │   Gateway   │
└──────────┘     └─────────────┘
```

### 9.2 Security Layers

| Layer | Mechanism | Implementation |
|-------|-----------|----------------|
| **Transport** | TLS 1.3 | All connections encrypted |
| **Authentication** | JWT + Refresh | Short-lived access tokens |
| **Authorization** | RBAC | Room-level permissions |
| **Rate Limiting** | Token bucket | Per-user, per-endpoint limits |
| **Input Validation** | Schema validation | All inputs sanitized |
| **E2E Encryption** | Signal Protocol | Optional client-side encryption |

### 9.3 Rate Limiting

```go
// Rate limiter configuration
type RateLimits struct {
    MessagesPerMinute   int // 60
    RoomsPerHour        int // 10
    ConnectionsPerUser  int // 5
    FileUploadsPerHour  int // 20
}

func (s *RateLimiter) CheckLimit(ctx context.Context, userID, action string) error {
    key := fmt.Sprintf("ratelimit:%s:%s", userID, action)

    count, err := s.redis.Incr(ctx, key).Result()
    if err != nil {
        return err
    }

    if count == 1 {
        s.redis.Expire(ctx, key, time.Minute)
    }

    limit := s.limits[action]
    if count > int64(limit) {
        return ErrRateLimitExceeded
    }

    return nil
}
```

---

## 10. Deployment Architecture

### 10.1 Multi-Region Setup

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Global Load Balancer                            │
│                           (GeoDNS / Anycast)                                │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │
        ┌─────────────────────────────┼─────────────────────────────┐
        │                             │                             │
        ▼                             ▼                             ▼
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│   US-EAST-1       │     │   EU-WEST-1       │     │   AP-SOUTHEAST-1  │
│                   │     │                   │     │                   │
│ ┌───────────────┐ │     │ ┌───────────────┐ │     │ ┌───────────────┐ │
│ │  Kubernetes   │ │     │ │  Kubernetes   │ │     │ │  Kubernetes   │ │
│ │   Cluster     │ │     │ │   Cluster     │ │     │ │   Cluster     │ │
│ │               │ │     │ │               │ │     │ │               │ │
│ │ - WS Gateway  │ │     │ │ - WS Gateway  │ │     │ │ - WS Gateway  │ │
│ │ - Services    │ │     │ │ - Services    │ │     │ │ - Services    │ │
│ └───────────────┘ │     │ └───────────────┘ │     │ └───────────────┘ │
│                   │     │                   │     │                   │
│ ┌───────────────┐ │     │ ┌───────────────┐ │     │ ┌───────────────┐ │
│ │    Kafka      │◀├─────├─┤    Kafka      │◀├─────├─┤    Kafka      │ │
│ │   (Primary)   │ │     │ │  (MirrorMaker)│ │     │ │  (MirrorMaker)│ │
│ └───────────────┘ │     │ └───────────────┘ │     │ └───────────────┘ │
│                   │     │                   │     │                   │
│ ┌───────────────┐ │     │ ┌───────────────┐ │     │ ┌───────────────┐ │
│ │   ScyllaDB    │◀├─────├─┤   ScyllaDB    │◀├─────├─┤   ScyllaDB    │ │
│ │   (DC: US)    │ │     │ │   (DC: EU)    │ │     │ │   (DC: APAC)  │ │
│ └───────────────┘ │     │ └───────────────┘ │     │ └───────────────┘ │
│                   │     │                   │     │                   │
│ ┌───────────────┐ │     │ ┌───────────────┐ │     │ ┌───────────────┐ │
│ │ Redis Cluster │ │     │ │ Redis Cluster │ │     │ │ Redis Cluster │ │
│ │  (Regional)   │ │     │ │  (Regional)   │ │     │ │  (Regional)   │ │
│ └───────────────┘ │     │ └───────────────┘ │     │ └───────────────┘ │
└───────────────────┘     └───────────────────┘     └───────────────────┘
```

### 10.2 CI/CD Pipeline

```yaml
# GitHub Actions workflow
name: Deploy Chat Services
on:
  push:
    branches: [main]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Tests
        run: make test
      - name: Run Security Scan
        run: make security-scan

  build:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - name: Build Docker Images
        run: make docker-build
      - name: Push to Registry
        run: make docker-push

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    steps:
      - name: Deploy to Staging
        run: kubectl apply -f k8s/staging/

  deploy-production:
    needs: deploy-staging
    runs-on: ubuntu-latest
    environment: production
    steps:
      - name: Canary Deploy (10%)
        run: kubectl apply -f k8s/production/canary/
      - name: Validate Canary
        run: ./scripts/validate-canary.sh
      - name: Full Rollout
        run: kubectl apply -f k8s/production/
```

---

## 11. Architecture Decision Records

### ADR-001: WebSocket vs HTTP Long Polling

**Status:** Accepted
**Date:** 2026-01-11

**Context:**
Need to choose a transport protocol for real-time message delivery.

**Decision:**
Use WebSocket as primary transport with HTTP long-polling fallback.

**Rationale:**
- WebSocket provides true bidirectional communication
- Lower latency than polling (no HTTP overhead per message)
- Efficient for high-frequency updates (presence, typing)
- Long-polling fallback for restrictive networks

**Consequences:**
- (+) Sub-100ms message delivery
- (+) Efficient connection utilization
- (-) Requires sticky sessions or connection registry
- (-) More complex load balancing

---

### ADR-002: Apache Kafka for Message Broker

**Status:** Accepted
**Date:** 2026-01-11

**Context:**
Need a message broker for decoupling services and ensuring message delivery.

**Decision:**
Use Apache Kafka as the primary message broker.

**Alternatives Considered:**
- RabbitMQ: Better for complex routing, but weaker durability
- Redis Streams: Simpler, but limited replay capability
- Pulsar: Similar features, but smaller ecosystem

**Rationale:**
- Durable message storage with configurable retention
- Excellent partition-based ordering
- High throughput (millions of messages/sec)
- Message replay for recovery scenarios
- Mature ecosystem and tooling

**Consequences:**
- (+) Guaranteed message ordering per partition
- (+) Replay capability for debugging/recovery
- (+) High throughput and scalability
- (-) Operational complexity (ZooKeeper/KRaft)
- (-) Learning curve for team

---

### ADR-003: ScyllaDB for Message Storage

**Status:** Accepted
**Date:** 2026-01-11

**Context:**
Need a database optimized for high write throughput and time-series queries.

**Decision:**
Use ScyllaDB for message storage.

**Alternatives Considered:**
- Cassandra: Similar model but lower performance
- DynamoDB: Managed but vendor lock-in
- MongoDB: Flexible but consistency challenges at scale

**Rationale:**
- 10x performance improvement over Cassandra
- Compatible with Cassandra drivers and CQL
- Excellent for time-series data patterns
- Automatic sharding and replication
- Multi-datacenter support

**Consequences:**
- (+) High write throughput for messages
- (+) Efficient time-range queries for history
- (+) Horizontal scaling with auto-sharding
- (-) Eventually consistent (trade-off accepted)
- (-) Limited complex query support

---

### ADR-004: Event-Driven Architecture

**Status:** Accepted
**Date:** 2026-01-11

**Context:**
Need to design inter-service communication for scalability and loose coupling.

**Decision:**
Adopt event-driven architecture with Kafka as the event backbone.

**Rationale:**
- Services communicate via events, not direct calls
- Enables independent scaling and deployment
- Natural fit for real-time systems
- Supports event sourcing patterns
- Improves fault isolation

**Consequences:**
- (+) Loose coupling between services
- (+) Easy to add new consumers
- (+) Built-in audit trail via event log
- (-) Eventual consistency complexity
- (-) Debugging distributed flows harder

---

### ADR-005: Regional Deployment with Global Users

**Status:** Accepted
**Date:** 2026-01-11

**Context:**
Need to support users globally with acceptable latency.

**Decision:**
Deploy regional clusters with cross-region data replication.

**Architecture:**
- User connects to nearest region (GeoDNS)
- Messages stored in user's home region
- Cross-region chat uses message forwarding
- ScyllaDB multi-DC replication for redundancy

**Rationale:**
- Minimizes latency for majority of users
- Data sovereignty compliance (GDPR)
- Fault tolerance across regions
- Cost optimization (egress costs)

**Consequences:**
- (+) Low latency for regional users
- (+) High availability across regions
- (+) Compliance with data regulations
- (-) Cross-region chat has higher latency
- (-) Complex operational model

---

## Appendix A: Capacity Planning

### Sizing Estimates (1M DAU)

| Metric | Value | Calculation |
|--------|-------|-------------|
| Peak concurrent users | 100,000 | 10% of DAU |
| Messages/day | 50M | 50 msgs/user/day |
| Peak messages/sec | 5,000 | 3x average, peak hours |
| Storage/year | 5 TB | 100 bytes avg * 50M * 365 |
| WebSocket servers | 20 | 100K / 50K per server |

### Infrastructure Costs (Monthly Estimate)

| Component | Specification | Monthly Cost |
|-----------|--------------|--------------|
| EKS Cluster | 20 x m6i.xlarge | $2,400 |
| Kafka (MSK) | 6 x kafka.m5.2xlarge | $3,600 |
| ScyllaDB | 6 x i3.2xlarge | $4,800 |
| PostgreSQL (RDS) | db.r6g.xlarge Multi-AZ | $800 |
| Redis (ElastiCache) | 6 x r6g.large | $1,200 |
| S3 + CloudFront | 10 TB storage + CDN | $500 |
| **Total** | | **~$13,300/month** |

---

## Appendix B: API Contracts

### WebSocket Protocol

```typescript
// Client → Server
interface ClientMessage {
  type: 'message' | 'typing' | 'presence' | 'read';
  payload: MessagePayload | TypingPayload | PresencePayload | ReadPayload;
  requestId?: string;  // For request-response correlation
}

interface MessagePayload {
  roomId: string;
  content: string;
  contentType: 'text' | 'image' | 'file';
  replyTo?: string;
  metadata?: Record<string, any>;
}

// Server → Client
interface ServerMessage {
  type: 'message' | 'typing' | 'presence' | 'receipt' | 'error' | 'ack';
  payload: any;
  requestId?: string;
}
```

### REST API Endpoints

```yaml
# User Service
POST   /api/v1/auth/register
POST   /api/v1/auth/login
POST   /api/v1/auth/refresh
GET    /api/v1/users/me
PATCH  /api/v1/users/me

# Room Service
GET    /api/v1/rooms
POST   /api/v1/rooms
GET    /api/v1/rooms/{roomId}
PATCH  /api/v1/rooms/{roomId}
DELETE /api/v1/rooms/{roomId}
GET    /api/v1/rooms/{roomId}/members
POST   /api/v1/rooms/{roomId}/members
DELETE /api/v1/rooms/{roomId}/members/{userId}

# Message Service
GET    /api/v1/rooms/{roomId}/messages
GET    /api/v1/rooms/{roomId}/messages/{messageId}
DELETE /api/v1/rooms/{roomId}/messages/{messageId}
POST   /api/v1/rooms/{roomId}/messages/{messageId}/reactions

# Search Service
GET    /api/v1/search/messages?q={query}&roomId={roomId}
```

---

*Document generated by System Architect persona*
*SuperClaude v7.0.0*
