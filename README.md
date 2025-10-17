# Ingestion =================
the rq module (Redis Queue) to handle background tasks.
the redis module to connect to a Redis server.
redis_conn = redis.Redis(host="localhost", port=6379, db=0):
    - default Redis connection parameters. Where db=0,means default redis database.
the **rq.Queue class to create a queue for background tasks.**
    - The queue is named "ingestion_queue" and uses the redis_conn connection.
    - q = Queue("ingestion_queue", connection=redis_conn)

**Purpose: This queue will hold jobs (tasks) that you want to process in the background, such as ingesting URLs**




# Worker =================
soup.get_text() pulls out all the visible text from the HTML, ignoring tags.

### Chunking(text, chunkSize, overlap)
- This function splits the cleaned text into smaller chunks for processing.
- So each new chunk starts 200 characters before the previous chunk ends.

Example:
| Chunk Number | Character Range    |
|--------------|-------------------|
| Chunk 1      | 0 → 1000          |
| Chunk 2      | 800 → 1800        |
| Chunk 3      | 1600 → 2600       |
| …            | …                 |

### Embeddings
- A numerical representation of text that captures its semantic meaning.
- Converts text into vectors (list) of numbers.
- Used for similarity search: Compares numerical vectors to find related content, instead of comparing raw text.

similarity score between two text chunks is calculated using cosine similarity.

A = Embedding vector of text chunk 1
B = Embedding vector of query

Cosine Similarity = (A · B) / (||A|| ||B||)

Where:
- A · B is the dot product of vectors A and B.
- ||A|| and ||B|| are the magnitudes (lengths) of vectors A and B.

### Storing in ChromaDB
- ChromaDB is a vector database optimized for storing and querying embeddings.
- Each chunk of text along with its embedding and metadata is stored as a record in ChromaDB.

*if there is not error, then the Metadata.status is updated to "completed".*

***if any error occurs during processing, the Metadata.status is updated to "failed", and the error is also added in the SQLite metadata (URLs Table) for debugging.***

API Documentation=================

## POST(ingest/url) --> This endpoint allows users to submit a URL for ingestion. The URL is stored in the database with a status of "pending", and a background job is enqueued to process the URL.

### *Input Parameters:*
- **url (string): The URL to be ingested.**

```curl
curl -X 'POST' \
  'http://127.0.0.1:8000/ingest/url' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "url": "https://shashwatjain.me"
}'
```
Output: with **Status Code 202**
```json
{
  "message": "URL submitted successfully",
  "url_id": 4,
  "job_id": "19446a81-692b-4f0c-9ee6-f0de4d713690",
  "status": "pending"
}
```

```
Status Codes:
- 202 Accepted: The request has been accepted, and enqueued in background for processing, with Metadata.status set to "pending".
- 400 Bad Request: This means that the url is already ingested in SQLite database and is processed with Status being "completed", "failed", or "processing".



## POST(/query/search) --> This endpoint allows users to query the ingested data. It retrieves the most relevant chunks from ChromaDB based on the input query.

```curl
curl -X 'POST' \
  'http://127.0.0.1:8000/query/search' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "query": "What is redis and fast apis? in one 10 words",
  "top_k": 2,
  "min_similarity": 0.5
}'
```

### *Input Parameters:*
- **query (string): The search query.**
- **top_k (integer, optional): The number of top similar chunks to retrieve. Default is 5.**
- **min_similarity (float, optional): The minimum similarity threshold for retrieved chunks. Default is 0.5.**

Output: with **Status Code 200**
```json
{
  "query": "What is redis and fast apis? in one 10 words",
  "retrieved_chunks": [
    {
      "url": "https://en.wikipedia.org/wiki/FastAPI",
      "url_id": 3,
      "chunk_index": 0,
      "total_chunks": 2,
      "content": "FastAPI - Wikipedia Jump to content From Wikipedia, the free encyclopedia Web framework for Python This article has multiple issues. Please help improve it or discuss these issues on the talk page . ( Learn how and when to remove these messages ) This article contains promotional content . Please help improve it by removing promotional language and inappropriate external links , and by adding encyclopedic text written from a neutral point of view . ( February 2022 ) ( Learn how and when to remove this message ) This article relies excessively on references to primary sources . Please improve this article by adding secondary or tertiary sources . Find sources: FastAPI news newspapers books scholar JSTOR ( February 2022 ) ( Learn how and when to remove this message ) ( Learn how and when to remove this message ) FastAPI Developer Sebastián Ramírez Initial release December 5, 2018 ; 6 years ago ( 2018-12-05 ) 1 Stable release 0.116.1 11 July 2025 ; 3 months ago ( 11 July 2025 ) Repository github .com tiangolo fastapi Written in Python Type Web framework License MIT Website fastapi .tiangolo .com FastAPI is a high-performance web framework for building HTTP -based service APIs in Python 3.8. 2 It uses Pydantic and type hints to validate , serialize and deserialize data. FastAPI also automatically generates OpenAPI documentation for APIs built with it. 3 It was first released in 2018. Components edit Pydantic edit Pydantic is a data validation library for Python. While writing code in an IDE , Pydantic provides type hints based on annotations. 4 FastAPI extensively utilizes Pydantic models for data validation, serialization, and automatic API documentation. These models are using standard Python type hints, providing a declarative way to specify the structure and types of data for incoming requests (e.g., HTTP bodies) and outgoing responses. 5 from fastapi import FastAPI from pydantic import BaseModel app FastAPI () class Item ( BaseModel ): name : str price : float is_offer : bool None None app . post ( items ) def create_item ( item : Item ): The item object is already validated and typed return message : Item received , item_name : item . name Starlette edit Starlette is a lightweight ASGI frameworktoolkit, to support async functionality in Python. 6 Uvicorn edit Uvicorn is a minimal low-level serverapplication web server for async frameworks, following the ASGI specification . Technically, it implements a multi-process model with one main process, which is responsible for managing a pool of worker processes and distributing incoming HTTP requests to them. The number of worker processes is pre-configured, but can also be adjusted up or down at runtime. 7 OpenAPI integration edit FastAPI automatically generates OpenAPI documentation for APIs. This documentation includes both Swagger UI and ReDoc , which provide interactive API documentation that you can use to explore and test your endpoints in real time. This is particularly useful for developing, testing, and sharing APIs with other developers or users. Swagger UI is accessible by default at docs and ReDoc at redoc route. 8 Features edit Asynchronous operations edit FastAPIs architecture inherently supports asynchronous programming . This design allows the single-threaded event loop to handle a large number of concurrent requests efficiently, particularly when dealing with IO-bound operations like database queries or external API calls. For reference, see asyncawait pattern . Dependency injection edit FastAPI incorporates a Dependency Injection (DI) system to manage and provide services to HTTP endpoints. This mechanism allows developers to declare components such as database sessions or authentication logic as function parameters. FastAPI automatically resolves these dependencies for each request, injecting the necessary instances. 9 from fastapi import Depends , HTTPException , status from db import DbSession --- Dependency for Database Session --- def get_db (): db DbSession () try : yield db finally : db . close () app . post ( items , status_code status . HTTP_201_CREATED ) def create_item ( name : str , description : str , db : DbSession Depends ( get_db )): new_item Item ( name name , description description ) db . add ( new_item ) db . commit () db . refresh ( new_item ) return message : Item created successfully! , item : new_item app . get ( items item_id ) def read_item ( item_id : int , db : DbSession Depends ( get_db )): item db . query ( Item ) . filter ( Item . id item_id ) . first () if item is None : raise HTTPException ( status_code status . HTTP_404_NOT_FOUND , detail Item not found ) return item WebSockets support edit WebSockets allow full-duplex communication between a client and the server. This capability is fundamental for applications requiring continuous data exchange, such as instant messaging platforms, live data dashboards, or multiplayer online games. FastAPI leverages the underlying Starlette implementation, allowing for efficient management of connections and message handling. 10 You must have websockets package installed from fastapi import WebSocket app . websocket ( ws ) async def websocket_endpoint ( websocket : WebSocket ): await websocket . accept () while True : data await websocket . receive_text () await websocket . send_text ( f Message text was: data ) Background tasks edit FastAPI enables the execution of background tasks after an HTTP response has been sent to the client. This allows the API to immediately respond to user requests while simultaneously processing non-critical or time-consuming operations in the background. Typical applications include sending email notifications, updating caches, or performing data post-processing. 11 import time import shutil from fastapi import BackgroundTasks , UploadFile , File from utils import generate_thumbnail app . post ( upload-image ) async def upload_image ( image : UploadFile File ( ... ), background_tasks : BackgroundTasks ): file_location f uploaded_images image . filename Save uploaded image with open ( image_path , wb ) as f : contents await file . read () f . write ( contents ) Add thumbnail generation as a background task tasks . add_task ( generate_thumbnail , file_location , 200x200",
      "similarity": 0.6216
    },
    {
      "url": "https://en.wikipedia.org/wiki/Redis",
      "url_id": 2,
      "chunk_index": 1,
      "total_chunks": 4,
      "content": "project. 29 In June 2020, Salvatore Sanfilippo stepped down as Redis sole maintainer. Sanfilippo was succeeded by Yossi Gottlieb and Oran Agra. 13 30 In March 2024, Redis Ltd. announced that beginning with version 7.4, the core Redis software would be relicensed under the RSAL and Server Side Public License (SSPL), both of which are source-available and non-free. 31 The Linux Foundation subsequently announced that it would fork the last BSD-licensed version of Redis as Valkey . 32 In May 2025, Redis Ltd. announced that it would change the license again to the AGPL beginning on version 8.0, citing that forks had achieved their goal of creating a level playing field of differentiated products, and that Redis has achieved record growth since the change in license. 7 Sanfilippo returned to Redis in December 2024. 33 Differences from other database systems edit This section needs additional citations for verification . Please help improve this article by adding citations to reliable sources in this section. Unsourced material may be challenged and removed. Find sources: Redis news newspapers books scholar JSTOR ( July 2025 ) ( Learn how and when to remove this message ) Redis is a system that functions as both a data store and a cache . Data is modified and read from the main computer memory while also being persisted to disk in a format optimized for sequential access rather than random access. The formatted data is only reconstructed into memory once the system restarts. Redis uses a data model that differs from relational database management system (RDBMS). Commands specify operations on abstract data types rather than queries to be executed by a database engine . Data is stored in structures designed for direct retrieval. It does not rely on secondary indexes, aggregations, or other features common in traditional RDBMS. The Redis implementation uses the fork system call to duplicate the process holding the data. This allows the parent process to continue serving clients while the child process persists the in-memory data to disk. Features edit Redis maps keys to types of values. Redis supports a number of data types including Strings , JavaScript Object Notation (JSON) documents, Hashes (a collection of fields, each field is a name-value string pair), 34 lists , sets , vector sets, 35 and more. The Redis Query Engine allows users to use Redis as a document database , a vector database , a secondary index, and a search engine. With Redis Query Engine, users can define indexes for hash and JSON documents, and use a rich query language for vector search, full-text search, geospatial queries, and aggregations. 36 Redis PubSub (short for publishsubscribe) is a lightweight messaging capability. Publishers send messages to a channel, and subscribers receive messages from that channel. 37 A Redis transaction allows the execution of a group of commands in a single step. A request sent by another client will never be served during the execution of a transaction. This guarantees that the commands are executed as a single isolated operation. 38 Redis users can also upload and execute Lua scripts on the server. 39 As of May 1, 2025, for all version of Redis starting with 8.0, all data types are included in the same package 40 and available under the Redis Source Available license v2. 41 Previously some data types were separate and therefore available under difference licenses. Persistence edit Redis typically holds the whole dataset in memory. Versions up to 2.4 could be configured to use what they refer to as virtual memory 42 in which some of the dataset is stored on disk, but this feature is deprecated. Persistence in Redis can be achieved through two different methods. First by snapshotting, where the dataset is asynchronously transferred from memory to disk at regular intervals as a binary dump, using the Redis RDB Dump File Format. Alternatively by journaling , where a record of each operation that modifies the dataset is added to an append -only file (AOF) in a background process. Redis can rewrite the append-only file in the background to avoid an indefinite growth of the journal. Journaling was introduced in version 1.1 and is generally considered the safer approach. By default, Redis writes data to a file system at least every 2 seconds, with more or less robust options available if needed. In the case of a complete system failure on default settings, only a few seconds of data would be lost. Replication edit Redis supports masterreplica replication . Data from any Redis server can replicate to any number of replicas. A replica may be a master to another replica. This allows Redis to implement a single-rooted replication tree. Redis replicas can be configured to accept writes, permitting intentional and unintentional inconsistency between instances. The publishsubscribe feature is fully implemented, so a client of a replica may subscribe to a channel and receive a full feed of messages published to the master, anywhere up the replication tree. Replication is useful for read (but not write) scalability or data redundancy. 43 Performance edit When the durability of data is not needed, the in-memory nature of Redis allows it to perform well compared to database systems that write every change to disk before considering a transaction committed. 8 Redis operates as a single process and is single-threaded or double-threaded when it rewrites the AOF (append-only file). 44 Thus, a single Redis instance cannot use parallel execution of tasks such as stored procedures . Clustering edit Redis introduced clustering in April 2015 with the release of version 3.0. 45 The cluster specification implements a subset of Redis commands: all single-key commands are available, multi-key operations (commands related to unions and intersections) are restricted to keys belonging to the same node, and commands related to database selection operations are unavailable. 46 A Redis cluster can scale up to 1,000 nodes, achieve acceptable write safety and to continue operations when some nodes fail. 47 48 Use cases edit Typical use cases of Redis are session caching, full page",
      "similarity": 0.6097
    }
  ],
  "grounded_answer": "Redis: In-memory database, cache. FastAPI: Python web framework for APIs. [https://en.wikipedia.org/wiki/Redis#Chunk_1/4], [https://en.wikipedia.org/wiki/FastAPI#Chunk_1/2]",
  "sources": [
    "https://en.wikipedia.org/wiki/Redis",
    "https://en.wikipedia.org/wiki/FastAPI"
  ]
}
```


# Schema Definitions ================

## Metadata Database:
*Using SQLite*

SQLite Database: metadata.db
┌─────────────────────────────────────────────────────────┐
│ Table: urls                                             │
├──┬────┬──────────────────────────┬──────────┬───────────┤
│id│url │status                    │created_at│updated_at │
├──┼────┼──────────────────────────┼──────────┼───────────┤

## Vector Embedding Database
*Using ChromaDB Locally*

- ChromaDB Collection: "web_content"

web_content:
- id: Unique identifier for each record (auto-generated by ChromaDB).