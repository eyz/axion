# Neo4j Setup for Axion Graph Tool

The `@[Graph]` tool uses Neo4j as its backend for storing and querying question dependency graphs. Neo4j provides a beautiful built-in graph visualizer that lets you watch the discussion tree grow in real-time.

## Quick Start with Docker (Recommended)

### 1. Start Neo4j Container

```bash
docker run -d \
  --name neo4j-axion \
  -p 7687:7687 \
  -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/axion \
  neo4j:latest
```

### 2. Verify Connection

```bash
# Check container is running
docker ps | grep neo4j-axion

# View logs
docker logs neo4j-axion
```

### 3. Configure Axion

Add to your `.env` file:

```bash
# Neo4j connection (optional - these are the defaults)
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=axion
```

### 4. Access Neo4j Browser

Open http://localhost:7474 in your browser:
- **Username**: `neo4j`
- **Password**: `axion`

## Viewing the Graph

### Real-Time Visualization

As specialists create questions and vote during the discussion, the graph populates in real-time. Open Neo4j Browser and run:

```cypher
// Show all questions and answers
MATCH (n)
WHERE n:Question OR n:Answer
RETURN n
```

### Colored by State

```cypher
// Show nodes colored by state (open=green, closed=red)
MATCH (n)
WHERE n:Question OR n:Answer
RETURN n,
       CASE n.state
         WHEN 'open' THEN 'green'
         WHEN 'closed' THEN 'red'
         ELSE 'gray'
       END as color
```

### Full Dependency Tree

```cypher
// Show questions, answers, and their relationships
MATCH path = (q:Question)<-[:ANSWERS]-(a:Answer)<-[:DEPENDS_ON]-(subq:Question)
RETURN path
UNION
MATCH path = (q:Question)<-[:ANSWERS]-(a:Answer)
WHERE NOT exists( (a)<-[:DEPENDS_ON]-() )
RETURN path
```

### Voting Details

```cypher
// Show who voted on each node
MATCH (n)
WHERE n:Question OR n:Answer
RETURN n.id as node,
       n.text as text,
       n.state as state,
       n.upvoters as upvoters,
       n.downvoters as downvoters,
       n.relevance_votes as upvotes,
       n.not_applicable_votes as downvotes
ORDER BY n.created_at
```

### Find High-Vote Questions

```cypher
// Show pending questions sorted by upvotes
MATCH (q:Question)
WHERE q.status = 'pending' AND q.state = 'open'
RETURN q.id as id,
       q.text as question,
       q.relevance_votes as upvotes,
       q.upvoters as upvoted_by,
       q.priority as priority
ORDER BY q.relevance_votes DESC, q.priority
```

### Show Closed Paths

```cypher
// Find all closed branches
MATCH (n)
WHERE (n:Question OR n:Answer) AND n.state = 'closed'
RETURN n.id as node,
       n.text as text,
       n.downvoters as closed_by,
       n.not_applicable_votes as downvotes
```

## Useful Cypher Queries

### Clear All Data

```cypher
// WARNING: Deletes everything
MATCH (n)
DETACH DELETE n
```

### Export Graph State

```cypher
// Get JSON representation of all nodes and relationships
CALL apoc.export.json.all(null, {stream: true})
YIELD data
RETURN data
```

*(Requires APOC plugin)*

### Count Nodes by Type

```cypher
// Statistics
MATCH (q:Question)
WITH count(q) as questions
MATCH (a:Answer)
WITH questions, count(a) as answers
RETURN questions, answers,
       questions + answers as total
```

### Show Vote Timeline

```cypher
// See voting activity over time
MATCH (n)
WHERE n.last_voted_at IS NOT NULL
RETURN n.id as node,
       n.last_vote_comment as comment,
       n.last_voted_at as timestamp
ORDER BY n.last_voted_at DESC
LIMIT 20
```

## Docker Management

### Stop Neo4j

```bash
docker stop neo4j-axion
```

### Start Neo4j

```bash
docker start neo4j-axion
```

### Remove Neo4j (deletes all data)

```bash
docker rm -f neo4j-axion
```

### Persistent Data Volume

To persist data across container restarts:

```bash
docker run -d \
  --name neo4j-axion \
  -p 7687:7687 \
  -p 7474:7474 \
  -e NEO4J_AUTH=neo4j/axion \
  -v $HOME/neo4j/data:/data \
  -v $HOME/neo4j/logs:/logs \
  neo4j:latest
```

## Troubleshooting

### Connection Refused

If Axion can't connect to Neo4j:

1. Check Neo4j is running: `docker ps | grep neo4j`
2. Check logs: `docker logs neo4j-axion`
3. Try connecting with Neo4j Browser: http://localhost:7474
4. Verify ports 7687 and 7474 aren't in use: `lsof -i :7687`

### Graph Tool Shows "Neo4j not available"

1. Check `.env` has correct connection details
2. Verify Neo4j container is running
3. Test connection manually:

```bash
python3 << EOF
from neo4j import GraphDatabase
driver = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", "axion"))
with driver.session() as session:
    result = session.run("RETURN 1")
    print("✓ Connected:", result.single()[0])
driver.close()
EOF
```

### Port Already in Use

If ports 7687 or 7474 are taken:

```bash
# Use different ports
docker run -d \
  --name neo4j-axion \
  -p 7688:7687 \
  -p 7475:7474 \
  -e NEO4J_AUTH=neo4j/axion \
  neo4j:latest

# Update .env
NEO4J_URI=bolt://localhost:7688
```

## Advanced: Native Installation

If you prefer not to use Docker:

### macOS (Homebrew)

```bash
brew install neo4j
neo4j-admin set-initial-password axion
neo4j start
```

### Ubuntu/Debian

```bash
wget -O - https://debian.neo4j.com/neotechnology.gpg.key | sudo apt-key add -
echo 'deb https://debian.neo4j.com stable latest' | sudo tee /etc/apt/sources.list.d/neo4j.list
sudo apt update
sudo apt install neo4j
sudo neo4j-admin set-initial-password axion
sudo systemctl start neo4j
```

### Windows

Download from https://neo4j.com/download/ and follow installer instructions.

## Neo4j Browser Tips

### Keyboard Shortcuts

- `Ctrl + Enter`: Execute query
- `Ctrl + Up/Down`: Navigate command history
- `Esc`: Clear editor
- `:clear`: Clear visualization

### Visualization Controls

- **Mouse wheel**: Zoom
- **Click + drag**: Pan
- **Click node**: Select and show properties
- **Double-click node**: Expand relationships
- **Right-click**: Context menu

### Useful Commands

```cypher
:help         // Show help
:play start   // Interactive tutorial
:style        // Customize visualization
:schema       // Show database schema
```

## Performance Tuning

For large graphs (100+ nodes):

```bash
# Increase heap size (add to docker run)
-e NEO4J_dbms_memory_heap_initial__size=1G \
-e NEO4J_dbms_memory_heap_max__size=2G
```

## Security

**For production**, change the default password:

```cypher
// In Neo4j Browser
ALTER CURRENT USER SET PASSWORD FROM 'axion' TO 'secure_password_here';
```

Then update `.env`:

```bash
NEO4J_PASSWORD=secure_password_here
```

---

## Resources

- **Neo4j Documentation**: https://neo4j.com/docs/
- **Cypher Query Language**: https://neo4j.com/docs/cypher-manual/current/
- **Neo4j Browser Guide**: https://neo4j.com/docs/browser-manual/current/
- **Python Driver**: https://neo4j.com/docs/api/python-driver/current/

