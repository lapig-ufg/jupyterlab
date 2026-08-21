# LAPIG JupyterHub — Plataforma de Ciência de Dados Geoespacial

Infraestrutura multiusuário de JupyterHub voltada para Ciência de Dados e Geoprocessamento, mantida pelo LAPIG/UFG. Integra **JupyterHub**, **DockerSpawner**, **Keycloak (SSO)**, **Traefik** e monitoramento via **Glances**, sobre uma arquitetura **Docker-out-of-Docker (DooD)**.

Cada usuário autenticado recebe um container isolado com um ambiente completo de geoprocessamento (Python + R + QGIS + GDAL), provisionado dinamicamente no login e destruído ao encerrar a sessão.

---

## Sumário

- [Arquitetura](#arquitetura)
- [Duas imagens Docker, dois propósitos](#duas-imagens-docker-dois-propósitos)
- [Estrutura do repositório](#estrutura-do-repositório)
- [Pré-requisitos](#pré-requisitos)
- [Configuração do ambiente](#configuração-do-ambiente)
- [Subindo o ambiente](#subindo-o-ambiente)
- [Fluxo de inclusão de novos usuários](#fluxo-de-inclusão-de-novos-usuários)
- [Verificação de capacidade (`check.py`)](#verificação-de-capacidade-checkpy)
- [Operação e troubleshooting](#operação-e-troubleshooting)
- [Segurança](#segurança)

---

## Arquitetura

O núcleo da infraestrutura é o modelo **DooD (Docker-out-of-Docker)**: o container do JupyterHub monta o socket do Docker do host (`/var/run/docker.sock`), o que permite ao `DockerSpawner` criar e gerenciar containers de usuário diretamente no host — como containers **irmãos**, não aninhados.

```
┌──────────────────────────────────────────────────────────────────────────┐
│                              HOST (servidor)                             │
│                                                                            │
│   ┌───────────┐      ┌────────────────┐      ┌─────────────────────┐    │
│   │  Traefik  │─────▶│   JupyterHub   │─────▶│    Keycloak (SSO)    │    │
│   │  (proxy)  │      │  (orquestrador)│      │  OAuth2 / grupo      │    │
│   └───────────┘      └───────┬────────┘      │  data_science        │    │
│                               │                └─────────────────────┘    │
│                 /var/run/docker.sock                                     │
│                               ▼                                          │
│                    ┌─────────────────────┐                               │
│                    │    DockerSpawner    │                               │
│                    └──────────┬──────────┘                               │
│                               │ cria dinamicamente, um por login          │
│              ┌────────────────┼────────────────┐                         │
│              ▼                ▼                ▼                         │
│      ┌──────────────┐ ┌──────────────┐ ┌──────────────┐                  │
│      │  Container   │ │  Container   │ │  Container   │                  │
│      │  usuário A   │ │  usuário B   │ │  usuário C   │                  │
│      │ (geojupyter- │ │ (geojupyter- │ │ (geojupyter- │                  │
│      │  lab image)  │ │  lab image)  │ │  lab image)  │                  │
│      └──────────────┘ └──────────────┘ └──────────────┘                  │
│                                                                            │
│   ┌────────────────────────────────────────────────────────────────┐    │
│   │  Glances — monitoramento (pid: host, socket Docker :ro)         │    │
│   └────────────────────────────────────────────────────────────────┘    │
└──────────────────────────────────────────────────────────────────────────┘
```

### Componentes

| Componente | Papel |
|---|---|
| **Traefik** | Proxy reverso externo; roteia requisições HTTPS até o container do Hub via labels Docker. Não faz parte deste repositório — é uma dependência externa que precisa estar rodando na mesma rede Docker. |
| **JupyterHub** | Orquestrador central. Autentica via Keycloak, consulta `users.json` para autorização e limites, e delega ao DockerSpawner a criação do container de cada usuário. |
| **Keycloak (SSO)** | Provedor de identidade via OAuth2 (`GenericOAuthenticator`). Acesso é restrito a contas pertencentes ao grupo `data_science`. |
| **DockerSpawner** | Plugin do JupyterHub responsável por instanciar, no host, um container por usuário logado, usando a imagem de ambiente definida em `.env`. |
| **Glances** | Dashboard web de monitoramento de recursos do host (CPU, memória, containers). Roda com `pid: host` e acesso somente-leitura ao socket Docker. |

---

## Duas imagens Docker, dois propósitos

Este projeto builda **duas imagens distintas**, cada uma com um Dockerfile próprio — não confundir uma com a outra:

| | `docker/Dockerfile.hub` | `jupyterlab/docker/Dockerfile` |
|---|---|---|
| **O que builda** | A imagem do **próprio JupyterHub** (o orquestrador) | A imagem de **ambiente de trabalho** entregue a cada usuário |
| **Base** | `quay.io/jupyterhub/jupyterhub:5.3.0` | `quay.io/jupyter/datascience-notebook` (multi-stage) |
| **Quem "roda" essa imagem** | Um único container: o serviço `jupyterhub` do compose | Um container por usuário logado, criado sob demanda pelo DockerSpawner |
| **Onde é referenciada** | `image: lapig/geojupyterhub:v1` no `docker-compose.yml` | `DOCKER_NOTEBOOK_IMAGE` no `.env`, consumida pelo DockerSpawner |

Em outras palavras: uma imagem é o **motor** (Hub), a outra é o **posto de trabalho** (Lab) que o motor distribui a cada usuário.

> ⚠️ A tag Docker da imagem de ambiente é publicada como `lapig/jupterlab` (sem o "y" de "Jupyter") — grafia intencional, mantida por compatibilidade com as tags já publicadas no Docker Hub.

A imagem de ambiente do usuário é build multi-stage e tem documentação própria — arquitetura dos estágios, pacotes R via `install.R`, fluxo de build/publish e troubleshooting: **[`jupyterlab/README.md`](jupyterlab/README.md)**.

---

## Estrutura do repositório

```
jupyterhub/
├── data/
│   └── users.json              # Fonte de configuração: quotas de CPU/RAM por usuário
├── docker/
│   ├── docker-compose.yml      # Orquestração: jupyterhub + glances + rede externa
│   └── Dockerfile.hub          # Imagem do orquestrador JupyterHub
├── jupyterlab/
│   └── docker/
│       ├── Dockerfile          # Imagem de ambiente (Python + R + Geo) entregue a cada usuário
│       └── script/
│           └── install.R       # Pacotes R instalados no build multi-stage
├── local_tests/                # Pasta de testes locais/experimentais
├── scripts/
│   ├── check.py                # Valida quotas de data/users.json contra capacidade do host
│   ├── generate_ufolder.sh     # Cria e ajusta permissão do diretório físico de cada usuário
│   └── jupyterhub_config.py    # Configuração do Hub: OAuth, DockerSpawner, autorização
├── var/
│   ├── db/
│   │   ├── jupyterhub_cookie_secret
│   │   ├── jupyterhub.sqlite   # Banco de estado interno do Hub (sessões, spawns)
│   │   └── users.json          # Cópia operacional consumida em runtime pelo Hub
│   └── run/
│       └── jupyterhub-proxy.pid
├── .env                        # Variáveis de ambiente (não versionado)
├── .env.example                # Template de referência para o .env
├── .python-version
├── pyproject.toml              # Dependências do tooling Python do repositório, via uv
└── README.md
```

> **`data/users.json` vs. `var/db/users.json`** — são dois arquivos com o mesmo nome e propósitos diferentes. `data/users.json` é a **fonte de configuração**, editada manualmente (ou por script) para cadastrar quotas de um novo usuário. `var/db/users.json` é a **cópia operacional**, montada dentro do container em `/srv/jupyterhub/` e é o que o Hub efetivamente lê em runtime. Ao adicionar ou alterar um usuário, o arquivo de origem é sempre `data/users.json` — ver [Fluxo de inclusão de novos usuários](#fluxo-de-inclusão-de-novos-usuários).

> **`local_tests/`** é uma pasta de testes locais e não faz parte do fluxo de deploy documentado aqui.

---

## Pré-requisitos

- Docker Engine + Docker Compose v2
- Uma rede Docker externa já criada (ver `docker-compose.yml` — a rede é declarada como `external: true`, então precisa existir **antes** do `docker compose up`):
  ```bash
  docker network create <sua-rede-docker>
  ```
- Traefik já rodando nessa mesma rede, configurado para resolver o `certresolver` referenciado nas labels (`le`, no exemplo — normalmente Let's Encrypt)
- Um realm Keycloak configurado com client OAuth2 e o grupo `data_science`
- [`uv`](https://docs.astral.sh/uv/) instalado, caso vá trabalhar no tooling Python do repositório (`pyproject.toml` / `.python-version`)

---

## Configuração do ambiente

Copie o template e preencha com os valores do seu ambiente:

```bash
cp .env.example .env
```

Variáveis esperadas em `.env` (nomes de referência — confira `.env.example` para a lista exata do seu setup):

```env
# OAuth2 / Keycloak
OAUTH_CLIENT_ID=jupyterhub
OAUTH_CLIENT_SECRET=<gerado_no_keycloak>
OAUTH_CALLBACK_URL=https://sci2.lapig.iesa.ufg.br/hub/oauth_callback
OAUTH_AUTHORIZE_URL=https://<seu-keycloak>/realms/<realm>/protocol/openid-connect/auth
OAUTH_TOKEN_URL=https://<seu-keycloak>/realms/<realm>/protocol/openid-connect/token

# Infraestrutura Docker
DOCKER_NETWORK_NAME=<sua-rede-docker>
DOCKER_NOTEBOOK_IMAGE=lapig/jupterlab:v3.0.8
SPAWNER_START_TIMEOUT=300
SPAWNER_HTTP_TIMEOUT=300
```

> ⚠️ **Nunca commite o `.env` preenchido.** O `OAUTH_CLIENT_SECRET` é uma credencial sensível — se ela vazar (inclusive comentada em algum arquivo versionado), rotacione-a no Keycloak imediatamente.

---

## Subindo o ambiente

Na maior parte do tempo, **você não precisa buildar as imagens localmente** — ambas costumam já ter uma versão publicada no Docker Hub, e o `docker compose up` (ou o próprio DockerSpawner) simplesmente puxa a tag configurada. Buildar do zero só é necessário quando alguma das imagens for alterada — ver [Publicando uma nova versão de imagem](#publicando-uma-nova-versão-de-imagem) mais abaixo.

### Uso normal — subir a infraestrutura

```bash
cd docker/
docker compose up -d
```

Isso puxa (ou reaproveita, se já local) as imagens configuradas em `docker-compose.yml` (`lapig/geojupyterhub:v1`) e `.env` (`DOCKER_NOTEBOOK_IMAGE`), e inicializa os serviços `jupyterhub` e `glances` na rede externa. O Hub é iniciado com:

```bash
jupyterhub -f /srv/jupyterhub/scripts/jupyterhub_config.py
```

O uso explícito de `-f` garante que o Hub carregue a configuração deste repositório (mapeada via volume de `../scripts`) em vez de cair em um `jupyterhub_config.py` genérico ou falhar ao procurar o arquivo no diretório padrão.

**Verificar status:**

```bash
docker compose ps
docker logs -f jupyterhub
```

---

### Publicando uma nova versão de imagem

Use este fluxo sempre que alterar o `Dockerfile.hub` do Hub. Para a imagem de ambiente do usuário (`jupterlab`), veja o fluxo de build/publish dedicado em [`jupyterlab/README.md`](jupyterlab/README.md#build-e-publicação).

> ⚠️ **Lembre sempre de trocar o número da versão** (a tag `vX.Y.Z`) antes de buildar e publicar — sobrescrever uma tag já em uso pode quebrar sessões de usuários que ainda estão referenciando a imagem antiga.

**Imagem do JupyterHub (orquestrador)** — a partir de `docker/` (onde fica `Dockerfile.hub`):

```bash
cd docker/

docker build -t lapig/geojupyterhub:v1 . -f Dockerfile.hub

docker login

docker push lapig/geojupyterhub:v1
```

Depois de publicar, atualize o campo `image:` do serviço `jupyterhub` em `docker-compose.yml` para a nova tag, e rode `docker compose up -d` novamente para aplicar.

---

## Fluxo de inclusão de novos usuários

| Passo | Local | Ação |
|---|---|---|
| **1. Credenciais** | Keycloak | Cadastrar o usuário e associá-lo ao grupo `data_science`. |
| **2. Quota** | `data/users.json` | Adicionar a entrada do usuário com limites de `mem_limit` / `cpu_limit`. |
| **3. Capacidade** | `scripts/check.py` | Rodar o script para confirmar que a soma das quotas não excede a capacidade do host (ver seção abaixo). |
| **4. Diretório** | Terminal (host) | Executar `scripts/generate_ufolder.sh` para criar a pasta física do usuário e ajustar a posse para UID/GID `1000:1000` (`jovyan`, usuário padrão dentro do container). |
| **5. Recarga** | Terminal (host) | Executar `docker compose restart jupyterhub` para que o Hub releia `allowed_users`. |
| **6. Login** | Navegador | O usuário acessa a URL pública, autentica via SSO e o `DockerSpawner` instancia seu container. |

### Sanitização de nomes de usuário

`generate_ufolder.sh` converte caracteres incompatíveis com rotas HTTP/sistema de arquivos do JupyterHub, seguindo o padrão de codificação hexadecimal ASCII do próprio Hub:

- `.` → `-2e` (ex.: `joao.silva` → `joao-2esilva`)
- `_` → `-5f` (ex.: `joao_silva` → `joao-5fsilva`)

---

## Verificação de capacidade (`check.py`)

Antes de aprovar a quota de um novo usuário, `scripts/check.py` soma os `cpu_limit` e `mem_limit` de todas as entradas em `users.json` e compara contra a capacidade total configurada no próprio script (constantes `cpu_count` e `recomendado_men`, em núcleos e GB respectivamente).

```bash
cd scripts/
python check.py
```

Saída esperada:

```
cpu OK
mem OK
```

Se alguma quota exceder o total disponível, o script imprime o excedente:

```
mem não OK
 Total 140
 recomendado 125
 excedeu 15
```

> Os valores de `cpu_count` e `recomendado_men` estão hardcoded no topo do script — ajuste-os para refletir a capacidade real do servidor onde o Hub está implantado antes de usar o script como gate de aprovação de novos usuários.

---

## Operação e troubleshooting

**Logs do Hub em tempo real:**
```bash
docker logs -f jupyterhub
```

**Logs do container de um usuário específico** (nome sanitizado conforme a tabela de escaping acima):
```bash
docker logs jupyter-nome-2edouser
```

**Verificar se uma tag da imagem de ambiente existe no Docker Hub sem baixá-la:**
```bash
docker manifest inspect lapig/jupterlab:v3.0.8
```

**Monitoramento de recursos do host:** acesse `http://<IP_do_servidor>:9011` (porta mapeada para o Glances no `docker-compose.yml`).

---

## Segurança

- O socket Docker (`/var/run/docker.sock`) é montado **com permissão de escrita** no container do JupyterHub — necessário para o DockerSpawner criar containers, mas isso equivale, na prática, a acesso root ao host. Trate a configuração do Hub (`scripts/jupyterhub_config.py`) com o mesmo rigor de um script rodando como root.
- O Glances monta o mesmo socket em modo **somente-leitura** (`:ro`) — não reduza esse escopo sem necessidade.
- `data/users.json` é montado no container do Hub como **somente-leitura** (`:ro`) — alterações de quota devem sempre passar pelo arquivo de origem no host, nunca por edição direta dentro do container.
- Segredos (`OAUTH_CLIENT_SECRET` e outros) vivem exclusivamente em `.env`, que **não deve ser versionado**. Confirme que `.env` está no `.gitignore` e nunca cole seu conteúdo em issues, PRs ou logs compartilhados.