# Usage Guide: System Topology Engine

Welcome to the comprehensive runtime and engineering usage guide for the **System Topology Engine** (`bandesh/system-topology-engine`). This document walks you through the entire end-to-end lifecycle of declaring, validating, rendering, and automating your architecture graphs.

---

## Step 1: Installation and Verification

Get the engine running on your local machine or build runner.

### Universal Install Script
```bash
# Download and install the latest binary to /usr/local/bin
curl -sSL [https://raw.githubusercontent.com/bandesh/system-topology-engine/main/install.sh](https://raw.githubusercontent.com/bandesh/system-topology-engine/main/install.sh) | sh

Alternative Methods
Go Package Manager: go install github.com/bandesh/system-topology-engine/cmd/ste@latest

Docker Container: docker pull ghcr.io/bandesh/system-topology-engine:latest

Verify that the CLI utility is correctly configured in your system path:

**## Step 2: Defining Your System Topology (topology.yaml)**
The engine processes architecture as code. System layouts are declared using three structural primitives: Layers, Nodes, and Edges.
Create a foundational definition file named topology.yaml:

YAML
version: "v1alpha"
metadata:
  name: "core-banking-mesh"
  environment: "production"
  owner: "platform-engineering"

# 1. Layers: Establish logical isolation and sequence tiers
layers:
  - name: edge
    level: 10
    description: "Public-facing ingress and routing"
  - name: services
    level: 20
    description: "Internal microservices mesh"
  - name: datastore
    level: 30
    description: "Stateful persistence systems"

# 2. Nodes: Define individual computational or managed units
nodes:
  - id: api-gateway
    layer: edge
    type: load_balancer
    metadata:
      technology: "Envoy"

  - id: auth-service
    layer: services
    type: microservice
    metadata:
      runtime: "Go"

  - id: payment-worker
    layer: services
    type: microservice
    metadata:
      runtime: "NodeJS"

  - id: ledger-db
    layer: datastore
    type: database
    metadata:
      engine: "PostgreSQL"

# 3. Edges: Map explicit directional communication paths
edges:
  - from: api-gateway
    to: auth-service
    protocol: HTTPS
    port: 443

  - from: api-gateway
    to: payment-worker
    protocol: gRPC
    port: 50051

  - from: payment-worker
    to: ledger-db
    protocol: PostgreSQL
    port: 5432


**## Step 3: Running Structural Validation**
Once defined, pass your layout through the compiling state-machine to inspect structural anomalies, orphaned network fragments, or syntax violations.

ste validate -f topology.yaml
ste validate -f topology.yaml --strict

✔ [SUCCESS] Topology file "topology.yaml" parsed cleanly.
✔ [SUCCESS] 0 architectural faults, 0 structural warnings.

**## Step 4: Compiling and Rendering Visual GraphsTransform your raw structured declarations into human-readable visual layouts**.
The system native renderer maps directed layers automatically.Generate an Interactive HTML CanvasBashste render -f topology.yaml --format html --output ./dist/architecture_map.html
Generate Vector Diagrams for DocumentationBash# Export standard SVG map
ste render -f topology.yaml --format svg --output ./docs/images/topology.svg

# Export raw Graphviz DOT notations
ste render -f topology.yaml --format dot --output ./graph.dot

**## Step 5: Enforcing Custom Compliance Policies**
To prevent architectural drift, you can inject constraint validation rules directly inside your configuration layout or load separate governance manifests.Append a policies runtime block to your topology.yaml file:YAMLpolicies:
  # Enforce unidirectional traffic flows down the layer stacks
  isolation:
    - name: "secure-datastore-ingress"
      target_layer: "datastore"
      allowed_ingress_from: ["services"]
      deny_all_other: true

  # Block dangerous infrastructure structural anomalies
  cycles:
    allow_circular_dependencies: false

  # Enforce transport-layer compliance standards
  protocols:
    enforce_secure_only: true
    allowed_list: ["HTTPS", "gRPC", "PostgreSQL", "TLS"]
Test compliance violations by creating an illegal upstream edge (e.g., configuring ledger-db to communicate directly back up to api-gateway):Bashste validate -f topology.yaml
Plaintext ✖ [POLICY VIOLATION]: "secure-datastore-ingress" breached.
   Resource Node 'ledger-db' [Layer: datastore] cannot initiate downstream or outbound calls to 'api-gateway' [Layer: edge].
   Validation Failed. Code: 1

**##Step 6: Executing Topological Blast-Radius Analytics**
The engine features advanced graph traversal metrics to discover high-risk infrastructure single points of failure (SPOF).Bashste analyze -f topology.yaml --metric blast-radius
System Impact FormulasWhen calculating the cascading impact rating of a target node instance, the internal graph logic computes full downstream dependency reachability matrices. The systemic weight metric leverages the following sequence:$$B_r(n) = \sum_{i \in D(n)} w(i)$$Where $D(n)$ indicates the entire mathematical subset of all operational nodes reachable downstream from resource $n$, and $w(i)$ maps directly to the unique criticality factor configured within that element's target layer stack.Step 7: Automating inside CI/CD PipelinesIntegrate topology verification checks directly into your trunk-based integration runs using standard shell execution gates.GitHub Actions Integration ExampleYAMLname: Architecture Linting
on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  topology-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout Code Base
        uses: actions/checkout@v4

      - name: Setup System Topology Engine
        run: curl -sSL [https://raw.githubusercontent.com/bandesh/system-topology-engine/main/install.sh](https://raw.githubusercontent.com/bandesh/system-topology-engine/main/install.sh) | sh

      - name: Assert Architectural Constraints
        run: ste validate -f ./infra/topology.yaml --strict
Standard CLI Return Code ReferenceThe engine sets predictive exit codes allowing you to orchestrate distinct pipeline recovery logic hooks:Exit CodeStructural ConditionMeaning0Clean RunSchema passes validations and policy requirements perfectly.1Syntax/Parse ErrorFile format schema broken or missing critical definitions.2Policy ViolationGraph structure explicitly broke a defined isolation policy rule.3Cyclic FaultA circular structural dependency loop was discovered in your design.
