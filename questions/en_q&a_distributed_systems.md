# Distributed Systems Interview Questions: Split Brain, Quorum, Consistency Trade-offs

## 📚 Table of Contents
- [Split Brain](#split-brain)
- [Quorum](#quorum)
- [Consistency Trade-offs](#consistency-trade-offs)
- [Practical Scenarios](#practical-scenarios)
- [References](#references)

---

## Split Brain

### Q1: What is "split brain" in distributed systems?
**Answer:** Split brain occurs when a network partition causes a cluster to divide into two or more isolated groups, each believing it is the authoritative leader. This can lead to conflicting writes, data corruption, or dual leaders.

**Example:** In a 3-node PostgreSQL cluster with synchronous replication, a network failure isolates Node A from Nodes B+C. Both sides may accept writes, creating divergent data states.

**Prevention:** 
- Use quorum-based leader election (e.g., Raft, Paxos)
- Implement fencing tokens or STONITH ("Shoot The Other Node In The Head")
- Configure minimum cluster size for writes (`minimum_master_nodes` in Elasticsearch)

**Source:** [Designing Data-Intensive Applications, Kleppmann, Ch. 8](https://dataintensive.net)

---

### Q2: How do you detect and recover from a split brain scenario?
**Answer:** 
- **Detection:** Use heartbeat timeouts, consensus protocols (Raft/Paxos), or external watchers (e.g., ZooKeeper, etcd).
- **Recovery:** 
  1. Elect a single leader via quorum vote
  2. Discard or reconcile conflicting writes from the minority partition
  3. Resync the healed node from the authoritative source

**Example:** etcd uses Raft consensus: a node must receive votes from a majority (`N/2+1`) to become leader. If a partition loses quorum, it steps down to follower.

**Source:** [Raft Paper, Ongaro & Ousterhout 2014](https://raft.github.io/raft.pdf)

---

### Q3: What is the role of `minimum_master_nodes` in Elasticsearch, and how does it prevent split brain?
**Answer:** `minimum_master_nodes` (now `discovery.zen.minimum_master_nodes`) sets the minimum number of master-eligible nodes required to form a cluster. It prevents two separate clusters from forming during a partition by ensuring only a majority can elect a master.

**Formula:** `minimum_master_nodes = (N / 2) + 1` where N = total master-eligible nodes.

**Example:** For 3 master nodes, set to `2`. If the network splits 2|1, only the side with 2 nodes can elect a master; the single node remains passive.

**Source:** [Elasticsearch Docs: Split Brain](https://www.elastic.co/guide/en/elasticsearch/reference/current/modules-discovery.html#split-brain)

---

## Quorum

### Q4: Explain quorum in the context of distributed consensus. How do you calculate read/write quorums?
**Answer:** Quorum is the minimum number of nodes that must agree on an operation for it to be considered committed. In a system with `N` replicas:

- **Write quorum (W):** Number of nodes that must acknowledge a write
- **Read quorum (R):** Number of nodes that must respond to a read

**Strong consistency rule:** `R + W > N` ensures that every read sees the latest write.

**Example:** Cassandra with `N=3`, `W=2`, `R=2`:
- Write succeeds after 2 replicas confirm
- Read queries 2 replicas and returns the most recent value
- Guarantees consistency even if 1 node fails

**Source:** [Amazon Dynamo Paper, 2007](https://www.allthingsdistributed.com/files/amazon-dynamo-sosp2007.pdf)

---

### Q5: What trade-offs exist when tuning quorum parameters (R, W, N)?
**Answer:**

| Configuration | Consistency | Availability | Latency | Use Case |
| :--- | :--- | :--- | :--- | :--- |
| `R=1, W=N` | Strong | Low (writes slow) | High writes | Financial ledgers |
| `R=N, W=1` | Strong | Low (reads slow) | High reads | Audit logs |
| `R+W ≤ N` | Eventual | High | Low | Social feeds, caching |
| `R+W > N` | Strong | Medium | Balanced | User profiles, inventory |

**Example:** A shopping cart might use `R=1, W=1` for speed (eventual consistency), while payment processing uses `R=2, W=2` on `N=3` for strong consistency.

**Source:** [PACELC Theorem, Daniel Abadi](https://dbmsmusings.blogspot.com/2010/04/problems-with-cap-and-yahoos-little.html)

---

### Q6: How does Raft use quorum for leader election and log replication?
**Answer:** 
- **Leader election:** A candidate requests votes; wins if it receives votes from a majority (`N/2+1`).
- **Log replication:** Leader appends entries to followers; commit occurs when a majority has persisted the entry.

**Example:** In a 5-node Raft cluster:
- Election requires 3 votes
- A log entry is committed after 3 nodes acknowledge
- If leader fails, a new election starts with quorum voting

**Source:** [Raft Interactive Tutorial](https://raft.github.io)

---

## Consistency Trade-offs

### Q7: Explain the CAP theorem. Why can't a distributed system guarantee all three properties simultaneously?
**Answer:** CAP states that during a **network partition (P)**, a system must choose between:
- **Consistency (C):** All nodes see the same data at the same time
- **Availability (A):** Every request receives a response (without guarantee of latest data)

You cannot have all three because a partition isolates nodes; to maintain consistency, you must reject requests (sacrifice availability); to stay available, you may serve stale data (sacrifice consistency).

**Example:** 
- **CP system:** etcd, ZooKeeper — reject writes during partition to preserve consistency
- **AP system:** Cassandra, DynamoDB — accept writes on all partitions, reconcile later

**Source:** [CAP Theorem, Brewer 2000; Gilbert & Lynch 2002](https://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.12.3417&rep=rep1&type=pdf)

---

### Q8: What is PACELC, and how does it extend CAP?
**Answer:** PACELC adds a second trade-off: **Else (E)**, when there is **no partition**, the system chooses between **Latency (L)** and **Consistency (C)**.

**Formula:** 
- **If Partition (P)** → choose Availability (A) or Consistency (C)
- **Else (E)** → choose Latency (L) or Consistency (C)

**Examples:**
- **DynamoDB (PA/EL):** During partition, stays available; otherwise, favors low latency over strong consistency (unless configured otherwise)
- **MongoDB (PC/EC):** During partition, favors consistency; otherwise, can tune for latency or consistency per operation

**Source:** [PACELC, Daniel Abadi](https://dbmsmusings.blogspot.com/2010/04/problems-with-cap-and-yahoos-little.html)

---

### Q9: When would you choose eventual consistency over strong consistency? Give a real-world example.
**Answer:** Choose eventual consistency when:
- Temporary staleness is acceptable
- High availability and low latency are critical
- Conflicts can be resolved automatically or by users

**Example:** Social media "like" counts. If a user sees 100 likes instead of 102 for a few seconds, it's acceptable. The system prioritizes fast writes and global availability over immediate consistency.

**Conflict resolution:** Use vector clocks, last-write-wins (LWW), or CRDTs.

**Source:** [Designing Data-Intensive Applications, Ch. 5](https://dataintensive.net)

---

### Q10: How do you handle write conflicts in an eventually consistent system?
**Answer:** Common strategies:
1. **Last-Write-Wins (LWW):** Use timestamps or version vectors; simplest but can lose data
2. **Vector Clocks:** Track causal relationships; detect and merge conflicts
3. **CRDTs (Conflict-Free Replicated Data Types):** Mathematically guaranteed convergence (e.g., G-Counter, OR-Set)
4. **Application-level merge:** Prompt user or use business logic (e.g., "merge shopping carts")

**Example:** Riak uses vector clocks to track concurrent updates; the client receives all conflicting versions and resolves them.

**Source:** [CRDTs: Shapiro et al., 2011](https://hal.inria.fr/inria-00609399/document)

---

## Practical Scenarios

### Scenario 1: Designing a Global Inventory System
**Problem:** You're building an e-commerce inventory system spanning 3 regions. During a network partition between US and EU, both sides receive orders for the last item.

**Questions:**
1. Would you choose CP or AP? Why?
2. How would you prevent overselling?
3. What quorum settings would you use?

**Sample Answer:**
- Choose **CP** for inventory to avoid overselling (consistency > availability)
- Use **distributed locking** or **reservation tokens** with quorum `W=2, R=2, N=3`
- Implement **idempotent order processing** and **compensation logic** for failed transactions

**Reference:** [Saga Pattern, Microservices.io](https://microservices.io/patterns/data/saga.html)

---

### Scenario 2: Multi-Region User Profile Service
**Problem:** User profiles must be readable globally with low latency, but updates can tolerate slight delay.

**Questions:**
1. What consistency model fits best?
2. How would you handle concurrent updates from different regions?
3. What replication strategy would you use?

**Sample Answer:**
- Use **eventual consistency** with **read-your-writes** guarantee for the user's own session
- Apply **LWW or CRDTs** for merging profile fields (e.g., merge preference lists)
- Use **asynchronous multi-master replication** with conflict resolution at the application layer

**Reference:** [Google Spanner: External Consistency](https://research.google/pubs/pub39966/)

---

## 📊 Quick Reference: Consistency Models

| Model | Guarantee | Latency | Use Case |
| :--- | :--- | :--- | :--- |
| **Strong** | Linearizable; all reads see latest write | High | Payments, inventory |
| **Sequential** | Operations ordered per client | Medium | Chat apps, collaborative editing |
| **Causal** | Causally related ops ordered; concurrent may vary | Low-Medium | Social feeds, comments |
| **Eventual** | All replicas converge if no new updates | Low | Analytics, caching, metrics |

---

## 💡 Interview Tips

- **Clarify assumptions:** Ask about partition frequency, data criticality, and latency SLOs before recommending a model.
- **Use real examples:** Reference systems you've worked with (e.g., "In our Kafka setup, we used...").
- **Discuss trade-offs explicitly:** Show you understand there's no free lunch—every choice has costs.
- **Mention observability:** "We monitored split-brain risk via etcd metrics and set up alerts for quorum loss."

---

## References

1. Brewer, E. (2000). *CAP Theorem*. PODC Keynote. [Link](https://www.infoq.com/articles/cap-twelve-years-later-how-the-rules-have-changed)
2. Gilbert, S., & Lynch, N. (2002). *Brewer's Conjecture and the Feasibility of Consistent, Available, Partition-Tolerant Web Services*. ACM SIGACT News.
3. Ongaro, D., & Ousterhout, J. (2014). *In Search of an Understandable Consensus Algorithm (Raft)*. USENIX ATC.
4. DeCandia, G., et al. (2007). *Dynamo: Amazon's Highly Available Key-value Store*. SOSP.
5. Kleppmann, M. (2017). *Designing Data-Intensive Applications*. O'Reilly. [Website](https://dataintensive.net)
6. Abadi, D. (2012). *Consistency Tradeoffs in Modern Distributed Database System Design*. IEEE Computer.
7. Shapiro, M., et al. (2011). *Conflict-Free Replicated Data Types (CRDTs)*. INRIA Research Report.
8. etcd Documentation: [Clustering and Fault Tolerance](https://etcd.io/docs/latest/learning/design-cluster/)
9. Consul Documentation: [Consensus Protocol](https://developer.hashicorp.com/consul/docs/internals/consensus)
10. MongoDB Manual: [Replication and Consistency](https://www.mongodb.com/docs/manual/replication/)

---

## ✅ Self-Check Questions

- [ ] Can I explain split brain in <30 seconds with a concrete example?
- [ ] Can I calculate quorum values for a given N, R, W and justify the choice?
- [ ] Can I articulate when to sacrifice consistency vs. availability for a given business requirement?
- [ ] Can I name at least two real systems that exemplify CP and AP choices?
- [ ] Can I describe one conflict resolution strategy beyond "last-write-wins"?

*Use this list to guide your preparation. Practice answering aloud with a timer!*
