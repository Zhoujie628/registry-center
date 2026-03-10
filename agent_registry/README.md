# 🤖 Agent Registry Service

A **RESTful API service** for centrally managing AI agent cards in a distributed system. Enables seamless registration, retrieval, and semantic matching of agents based on natural language task descriptions.

> ✅ Built with **FastAPI**, **Pydantic**, **Uvicorn**, and **Python 3.10+**  
> 🌐 Designed for **microservices**, **multi-agent systems**, and **AI orchestration platforms**  
> 📦 Ready for **Docker**, **CI/CD**, and **cloud deployment**

---

## 📌 Features

- ✅ **Register** new AI agent cards with schema validation
- ✅ **Retrieve** agents by task description using semantic matching
- ✅ **Centralized management** of agent metadata (name, description, capabilities, etc.)
- ✅ **Health check endpoint** (`/health`) for monitoring and Kubernetes integration
- ✅ **Full OpenAPI/Swagger docs** at `/docs`
- ✅ **Robust logging** with structured output
- ✅ **Extensible design** – easy to integrate with LLM-based matching, auth, audit logs, etc.

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/your-username/agent-registry-service.git
cd agent_registry-service
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Run the service

```shell
uvicorn agent_registry_server:app --host 0.0.0.0 --port 5000
```

### 4. Access the API

- 📄 **Swagger UI** → [http://localhost:5000/docs](http://localhost:5000/docs)
- 📄 **Redoc** → [http://localhost:5000/redoc](http://localhost:5000/redoc)
- 🧪 **Health Check** → `GET http://localhost:5000/health`
- 📥 **Register an agent** → `POST http://localhost:5000/rest/a2a-t/v1/agent-register`
- 🔍 **Retrieve agents** → `GET http://localhost:5000/rest/a2a-t/v1/retrieve-agents?task=write+blog+post`

---

## 🛠️ API Reference

### POST `/rest/a2a-t/v1/agent-register`

Register a new AI agent card.

#### Request Body (JSON)
```json
{
  "name": "blog-writer-agent",
  "description": "An AI agent specialized in writing high-quality blog posts.",
  "capability": ["writing", "research", "editing"],
  "provider": {
    "organization": "Acme AI Labs",
    "version": "1.0.0"
  },
  "llm_config": {
    "model": "qwen3-32b",
    "temperature": 0.7
  }
}
```

#### Response
```json
true
```

---

### GET `/rest/a2a-t/v1/retrieve-agents`

Retrieve agent cards based on a natural language task description.

#### Query Parameters

| Parameter | Type | Required | Description |
|----------|------|----------|-------------|
| `task` | string | ❌ | Natural language task description (e.g., `"write a blog post about AI trends"`). If omitted, returns all agents. |

#### Response
```json
[
  {
    "name": "blog-writer-agent",
    "description": "An AI agent specialized in writing high-quality blog posts.",
    "capability": ["writing", "research", "editing"],
    ...
  }
]
```

---

## 🐳 Docker Support

Build and run with Docker:

```bash
# Build image
docker build -t agent_registry-service:latest .

# Run container
docker run -p 5000:5000 agent_registry-service:latest
```

> ✅ Image is built from `Dockerfile` (see below)

---

## 📄 License

This project is licensed under the **MIT License** – see the [LICENSE](LICENSE) file for details.

---

## 📬 Contributing

We welcome contributions! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) guide for details on how to submit pull requests, report bugs, or suggest new features.

---

## 📚 Acknowledgements

This project was inspired by:
- [FastAPI](https://fastapi.tiangolo.com/)
- [OpenAPI Specification](https://swagger.io/specification/)
- [LLM Agent Orchestration Patterns](https://www.anthropic.com/)

---

## 🔄 Roadmap

- [ ] Add **JWT-based authentication** for agent registration
- [ ] Implement **LLM-powered semantic matching** for `retrieve-agents`
- [ ] Add **audit logging** and **versioning** of agent cards
- [ ] Support **gRPC** alongside REST
- [ ] Publish **Docker image** to Docker Hub
- [ ] Add **CI/CD pipeline** (GitHub Actions)

---

## 📞 Contact

Have questions? Want to collaborate?

👉 Reach out at: **contact@acme-ai-labs.com**

---

> 🌟 **Built with ❤️ for the future of AI agents.**  
> 🔗 **Check out our ecosystem: [acme-ai-labs.com](https://acme-ai-labs.com)**
```