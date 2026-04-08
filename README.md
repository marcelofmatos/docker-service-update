# Docker Manager API

![Python](https://img.shields.io/badge/python-3.9-blue?logo=python&logoColor=white)
![Flask](https://img.shields.io/badge/flask-2.x-lightgrey?logo=flask)
![Docker](https://img.shields.io/badge/docker-swarm-2496ED?logo=docker&logoColor=white)
![GitLab CI](https://img.shields.io/badge/gitlab--ci-enabled-FC6D26?logo=gitlab&logoColor=white)
![GitHub Actions](https://img.shields.io/badge/github--actions-enabled-2088FF?logo=githubactions&logoColor=white)
![GHCR](https://img.shields.io/badge/registry-ghcr.io-181717?logo=github&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

API HTTP leve que atua como webhook de deploy para atualizar serviços no **Docker Swarm** automaticamente. Recebe o nome de uma imagem e força o re-deploy de todos os serviços que a utilizam.

---

## Sumario

- [Problema que resolve](#problema-que-resolve)
- [Como funciona](#como-funciona)
- [Pré-requisitos](#pré-requisitos)
- [Rodando localmente](#rodando-localmente)
- [Uso da API](#uso-da-api)
- [Integração com GitHub Actions](#integração-com-github-actions)
- [Integração com GitLab CI/CD](#integração-com-gitlab-cicd)
- [Variáveis de ambiente](#variáveis-de-ambiente)
- [Deploy no Docker Swarm](#deploy-no-docker-swarm)
- [Contribuindo](#contribuindo)

---

## Problema que resolve

Em ambientes com Docker Swarm, quando uma nova versão de uma imagem é publicada no registry, os serviços não são atualizados automaticamente. Esta API age como um webhook: o pipeline de CI/CD notifica a API com o nome da imagem, e ela identifica e força o update de todos os serviços Swarm que usam aquela imagem.

---

## Como funciona

```
CI/CD Pipeline → POST /update_services → Docker Manager API → docker service update --force
```

1. O pipeline constrói e publica a imagem no registry (GHCR ou GitLab Registry)
2. O pipeline chama o webhook (esta API) com o nome da imagem
3. A API lista todos os serviços do Swarm e filtra os que usam aquela imagem
4. Cada serviço encontrado é atualizado com `force_update=True`

---

## Pré-requisitos

- Python 3.9+
- Docker Engine com Swarm ativo (para uso em produção)
- Acesso ao socket do Docker (`/var/run/docker.sock`)

---

## Rodando localmente

**Com Python:**

```bash
pip install -r requirements.txt
python app.py
```

**Com Docker (imagem local):**

```bash
docker build -t docker-manager-api .
docker run -p 80:80 -v /var/run/docker.sock:/var/run/docker.sock docker-manager-api
```

**Com a imagem publicada no GHCR:**

```bash
docker run -p 80:80 -v /var/run/docker.sock:/var/run/docker.sock \
  ghcr.io/seu-org/docker-manager-api:latest
```

> A API ficará disponível em `http://localhost:80`.

---

## Uso da API

### `POST /update_services`

Atualiza todos os serviços Swarm que utilizam a imagem informada.

**Request:**

```http
POST /update_services
Content-Type: application/json

{
  "image_name": "registry.example.com/meu-projeto/meu-servico:main"
}
```

**Resposta de sucesso (`200`):**

```json
{
  "message": "Services updated successfully",
  "updated_services": ["meu-servico_web", "meu-servico_worker"]
}
```

**Resposta de erro (`400`):**

```json
{
  "error": "image_name is required"
}
```

**Resposta de erro (`500`):**

```json
{
  "error": "descrição do erro"
}
```

**Exemplo com curl:**

```bash
curl -X POST http://localhost:80/update_services \
  -H "Content-Type: application/json" \
  -d '{"image_name": "ghcr.io/seu-org/meu-servico:main"}'
```

---

## Integração com GitHub Actions

O projeto usa três workflows configurados em `.github/workflows/`:

### `docker-image.yml` — Build contínuo por branch

Disparado em push nos branches `homolog` e `prod`, e em releases publicadas. Constrói a imagem, publica no GHCR com a tag do branch, e chama o webhook de deploy.

```
ghcr.io/<org>/<repo>:homolog
ghcr.io/<org>/<repo>:prod
```

### `release-and-build.yml` — Release semântica

Disparado manualmente via `workflow_dispatch`. Cria uma release no GitHub com versionamento semântico (patch/minor/major) e publica a imagem com múltiplas tags:

```
ghcr.io/<org>/<repo>:1.2.3   # versão completa
ghcr.io/<org>/<repo>:1.2     # minor (pega últimos patches)
ghcr.io/<org>/<repo>:1       # major (pega últimos minor.patch)
ghcr.io/<org>/<repo>:latest  # sempre o mais recente
```

### `docker-set-tag.yml` — Associação manual de tags

Workflow manual para apontar uma docker tag para uma release tag existente. Útil para promover uma imagem de `homolog` para `prod` sem rebuild.

---

Configure os seguintes secrets no GitHub (Settings → Secrets and variables → Actions):

| Secret                   | Descrição                                              |
|--------------------------|--------------------------------------------------------|
| `WEBHOOK_DEPLOY_MAIN`    | URL da API para deploy no ambiente de produção         |
| `WEBHOOK_DEPLOY_HOMOLOG` | URL da API para deploy no ambiente de homologação      |

**Exemplo de chamada gerada pelo pipeline:**

```bash
curl --silent --fail -X POST "$WEBHOOK_DEPLOY_MAIN" \
  -H "Content-Type: application/json" \
  -d '{"image_name": "ghcr.io/seu-org/docker-manager-api:1.2.3"}'
```

## Integração com GitLab CI/CD

O arquivo `.gitlab-ci.yml` está configurado para:

1. **Build:** construir e publicar a imagem no GitLab Container Registry
2. **Update:** chamar o webhook de deploy conforme o branch (`main` ou `homolog`)

Configure as seguintes variáveis no GitLab CI (Settings → CI/CD → Variables):

| Variável                 | Descrição                                              |
|--------------------------|--------------------------------------------------------|
| `WEBHOOK_DEPLOY_MAIN`    | URL da API para deploy no ambiente de produção (`main`) |
| `WEBHOOK_DEPLOY_HOMOLOG` | URL da API para deploy no ambiente de homologação      |

**Exemplo de chamada gerada pelo pipeline:**

```bash
curl --silent --fail -X POST "$WEBHOOK_DEPLOY_MAIN" \
  -H "Content-Type: application/json" \
  -d '{"image_name": "registry.gitlab.com/org/projeto:main"}'
```

---

## Variáveis de ambiente

A API não requer variáveis de ambiente próprias. O acesso ao Docker é feito via socket Unix montado no container.

| Requisito                        | Descrição                                      |
|----------------------------------|------------------------------------------------|
| `/var/run/docker.sock` montado   | Necessário para controlar o Docker Swarm       |
| Permissão de manager no Swarm    | O host deve ser um nó manager do Swarm         |

---

## Deploy no Docker Swarm

Exemplo de stack para subir a API como serviço no Swarm:

```yaml
version: "3.8"

services:
  docker-manager-api:
    image: ghcr.io/seu-org/docker-manager-api:latest
    ports:
      - "80:80"
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock
    deploy:
      placement:
        constraints:
          - node.role == manager
```

> O constraint `node.role == manager` é obrigatório para que a API possa gerenciar serviços do Swarm.

---

## Contribuindo

1. Faça um fork do repositório
2. Crie uma branch para sua feature: `git checkout -b feature/minha-feature`
3. Commit suas mudanças: `git commit -m 'feat: minha feature'`
4. Faça push para a branch: `git push origin feature/minha-feature`
5. Abra um Merge Request

---

*Feito com Flask + Docker SDK for Python*
