# ASAP Protocol: Sprint Plan

> Desenvolvimento incremental com entregas a cada sprint.

---

## Visão Geral

| Sprint | Foco | Entregável Demonstrável | Duração |
|--------|------|-------------------------|---------|
| **0** | Setup | Projeto rodando, CI verde | 0.5 dia |
| **1** | Models | Schemas JSON exportados | 1.5 dias |
| **2** | State | Task state machine funcionando | 1 dia |
| **3** | Transport | Agente respondendo via HTTP | 1.5 dias |
| **4** | E2E | Dois agentes dialogando | 1 dia |
| **5** | Polish | Package publicável | 1 dia |

**Total**: ~6.5 dias

---

## Sprint 0: Project Setup

**Objetivo**: Fundação do projeto com tooling e CI.

### Tarefas

- [x] Criar repositório no GitHub com nome asap-protocol
- [x] Criar estrutura de diretórios
- [x] Configurar `pyproject.toml` (Poetry/PDM)
- [x] Setup pytest + pytest-asyncio
- [x] Configurar ruff (linting) + black (formatting)
- [x] GitHub Actions: lint + test
- [x] README básico com badge de CI (ou atualizar o README existente)
- [x] Primeiro commit e push (criando o repo) pedindo confirmação ao usuário.

### Definição de Pronto
✅ Repositório criado e disponível no GitHub
✅ `pytest` roda sem erros (mesmo sem testes ainda)
✅ CI passa com status verde

### Estrutura Inicial

```
asap-protocol/
├── src/asap/
│   └── __init__.py          # version only
├── tests/
│   └── __init__.py
├── pyproject.toml
├── README.md
└── .github/workflows/ci.yml
```

---

## Sprint 1: Core Models

**Objetivo**: Todos os modelos Pydantic com JSON Schema export.

### Fase 1A: Entities (0.5 dia)

- [x] `models/base.py` - BaseModel com configurações comuns
- [x] `models/ids.py` - ULID generation helpers
- [x] `models/entities.py`:
  - [x] `Agent`
  - [x] `Manifest`
  - [x] `Conversation`
  - [x] `Task`
  - [x] `Message`
  - [x] `Artifact`
  - [x] `StateSnapshot`
- [x] Testes unitários para cada entity

### Fase 1B: Parts (0.5 dia)

- [x] `models/parts.py`:
  - [x] `TextPart`
  - [x] `DataPart`
  - [x] `FilePart`
  - [x] `ResourcePart`
  - [x] `TemplatePart`
  - [x] `Part` (união discriminada)
- [x] Testes de serialização/deserialização

### Fase 1C: Payloads + Envelope (0.5 dia)

- [x] `models/payloads.py`:
  - [x] `TaskRequest`, `TaskResponse`, `TaskUpdate`, `TaskCancel`
  - [x] `MessageSend`, `StateQuery`, `StateRestore`, `ArtifactNotify`
  - [x] `McpToolCall`, `McpToolResult`, `McpResourceFetch`, `McpResourceData`
  - [x] `Payload` (união discriminada por `payload_type`)
- [x] `models/envelope.py`:
  - [x] `Envelope` com auto-gen de id, timestamp
- [x] Testes de envelope creation

### Definição de Pronto
✅ `from asap.models import Envelope, TaskRequest` funciona
✅ `schemas/` contém JSON Schemas gerados
✅ 100% dos modelos têm testes

---

## Sprint 2: State Machine

**Objetivo**: Gerenciamento de estado de Task funcional.

### Tarefas

- [x] `state/machine.py`:
  - [x] Enum `TaskStatus` com todos os estados
  - [x] Dict `VALID_TRANSITIONS`
  - [x] Função `can_transition(from, to) -> bool`
  - [x] Função `transition(task, new_status) -> Task` (com validação)
  - [x] Exception `InvalidTransitionError`
- [x] `state/snapshot.py`:
  - [x] Classe `SnapshotStore` (interface)
  - [x] Implementação `InMemorySnapshotStore`
  - [x] Métodos: `save(snapshot)`, `get(task_id, version?)`, `list_versions(task_id)`
- [x] Testes da state machine
- [x] Testes do snapshot store

### Definição de Pronto
✅ `task.transition("completed")` funciona ou levanta erro
✅ Snapshots podem ser salvos e restaurados
✅ Testes cobrem todas as transições

---

## Sprint 3: HTTP Transport

**Objetivo**: Servidor FastAPI recebendo mensagens ASAP.

### Fase 3A: Server (1 dia)

- [x] `transport/server.py`:
  - [x] FastAPI app factory
  - [x] Endpoint POST `/asap` recebendo JSON-RPC
  - [x] Handler registry (payload_type → handler)
  - [x] Endpoint GET `/.well-known/asap/manifest.json`
- [x] `transport/handlers.py`:
  - [x] `TaskRequestHandler` base (echo response)
- [x] Testes com TestClient

### Fase 3B: Client (0.5 dia)

- [x] `transport/client.py`:
  - [x] Classe `ASAPClient` (async context manager)
  - [x] Método `send(envelope) -> Envelope`
  - [x] Auto-retry com idempotency_key
- [x] Testes de client (mock server)

### Definição de Pronto
✅ Servidor roda com `uvicorn asap.transport.server:app`
✅ Client consegue enviar TaskRequest e receber TaskResponse
✅ Manifest acessível via curl

---

## Sprint 4: Integração E2E

**Objetivo**: Demonstração funcional com 2 agentes.

### Tarefas

- [x] `src/asap/examples/echo_agent.py`:
  - [x] Agente que retorna input como output
  - [x] Usa ASAPClient para responder
- [x] `src/asap/examples/coordinator.py`:
  - [x] Envia TaskRequest para echo_agent
  - [x] Recebe e imprime TaskResponse
- [x] `src/asap/examples/run_demo.py`:
  - [x] Script que sobe ambos e executa fluxo
- [x] Teste E2E automatizado

### Definição de Pronto
✅ Demo roda: `python -m asap.examples.run_demo`
✅ Output mostra TaskRequest → TaskResponse completo
✅ Trace IDs correlacionados nos logs

---

## Sprint 5: Polish & Package

**Objetivo**: Pronto para publicação.

### Tarefas

- [x] Docstrings em todas as classes públicas
- [x] README completo:
  - [x] Instalação
  - [x] Quick start
  - [x] Exemplos
  - [x] Link para spec
- [x] CHANGELOG.md atualizado
- [x] `pyproject.toml` metadata completa
- [x] CLI básica: `asap --version`
- [x] Publicar em TestPyPI para validação

### Definição de Pronto
✅ `pip install asap-protocol` funciona (TestPyPI)
✅ README permite começar em <5 min
✅ `asap --version` mostra versão correta

---

## Critérios de Transição entre Sprints

| De → Para | Gate |
|-----------|------|
| 0 → 1 | CI verde, estrutura criada |
| 1 → 2 | Todos os models exportam JSON Schema |
| 2 → 3 | State machine tem 100% cobertura |
| 3 → 4 | Server responde a curl com echo |
| 4 → 5 | Demo E2E funciona sem erros |

---

## Dependências entre Tarefas

```mermaid
graph LR
    S0[Sprint 0: Setup] --> S1[Sprint 1: Models]
    S1 --> S2[Sprint 2: State]
    S1 --> S3[Sprint 3: Transport]
    S2 --> S4[Sprint 4: E2E]
    S3 --> S4
    S4 --> S5[Sprint 5: Polish]
```

---

## Riscos e Mitigações

| Risco | Probabilidade | Impacto | Mitigação |
|-------|---------------|---------|-----------|
| Pydantic v2 breaking changes | Baixa | Alto | Pin version, testes |
| JSON-RPC edge cases | Média | Médio | Usar lib `jsonrpcserver` |
| Async complexity | Média | Médio | Exemplos claros, docs |
| Schema drift | Baixa | Alto | Gerar schemas em CI |
