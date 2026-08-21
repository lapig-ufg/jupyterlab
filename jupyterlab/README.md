# LAPIG JupyterLab — Imagem de Ambiente Geoespacial

Este documento cobre a imagem Docker de **ambiente de trabalho** distribuída a cada usuário do [LAPIG JupyterHub](../README.md) — não o Hub em si, mas o container individual onde cada pesquisador efetivamente roda notebooks. Publicada como `lapig/jupterlab` (grafia sem "y", ver nota abaixo).

Para o funcionamento geral da plataforma (autenticação, DockerSpawner, fluxo de novos usuários), veja o [README principal](../README.md).

**Mantenedor:** Jairo Matos da Rocha ([devjairomr@gmail.com](mailto:devjairomr@gmail.com)) — via `LABEL maintainer` no `Dockerfile`.

---

## Sumário

- [O que é esta imagem](#o-que-é-esta-imagem)
- [Arquitetura multi-stage](#arquitetura-multi-stage)
- [Conteúdo da imagem](#conteúdo-da-imagem)
- [Pacotes R via `install.R`](#pacotes-r-via-installr)
- [Build e publicação](#build-e-publicação)
- [Debugando o build](#debugando-o-build)
- [Manutenção e pontos de atenção](#manutenção-e-pontos-de-atenção)

---

## O que é esta imagem

Toda vez que um usuário faz login no JupyterHub, o `DockerSpawner` instancia um container novo a partir desta imagem — é o "posto de trabalho" de cada pesquisador, com um ambiente completo de Ciência de Dados e Geoprocessamento pré-instalado: Python, R, QGIS, GDAL e dezenas de bibliotecas geoespaciais, prontas para uso sem que o usuário precise instalar nada manualmente.

> ⚠️ **Grafia da tag**: a imagem é publicada no Docker Hub como `lapig/jupterlab` — **sem o "y"** de "Jupyter". É intencional, mantida por compatibilidade com as tags já publicadas. Use exatamente essa grafia em todo comando `docker build` / `docker pull` / `docker push`.

Ela **não** deve ser confundida com a imagem do próprio JupyterHub (`lapig/geojupyterhub`, definida em `docker/Dockerfile.hub`), que é o orquestrador — um único container que gerencia o login e decide quando instanciar containers desta imagem aqui. Uma é o motor, a outra é o posto de trabalho que o motor distribui a cada usuário.

| | Esta imagem (`jupterlab`) | Imagem do Hub (`geojupyterhub`) |
|---|---|---|
| **Dockerfile** | `jupyterlab/docker/Dockerfile` | `docker/Dockerfile.hub` |
| **Base** | `quay.io/jupyter/datascience-notebook` (multi-stage) | `quay.io/jupyterhub/jupyterhub:5.3.0` |
| **Quem roda** | Um container por usuário logado, criado sob demanda | Um único container: o serviço `jupyterhub` do compose |
| **Onde é referenciada** | `DOCKER_NOTEBOOK_IMAGE` no `.env`, consumida pelo DockerSpawner | `image:` no `docker-compose.yml` |

---

## Arquitetura multi-stage

O `Dockerfile` é dividido em três estágios, nessa ordem de build:

```
system-base ──▶ r-builder ──▶ (estágio final, sem nome)
```

| Estágio | O que faz | Por que é um estágio separado |
|---|---|---|
| **`system-base`** | Copia binários de outras imagens (`uv`, Java 11, Node 20) via `COPY --from`; instala dezenas de pacotes de sistema via `apt-get` (GDAL, GEOS, PROJ, libs de compilação, QGIS, Google Cloud CLI, fontes) | Camada mais estável — muda raramente, então fica no topo pra maximizar cache. Praticamente "cacheia para sempre", como diz o comentário original do Dockerfile. |
| **`r-builder`** | Herda de `system-base`. Instala o grosso dos pacotes R via `mamba` (conda-forge) — `sf`, `terra`, `tidyverse`, `mlr`, entre dezenas de outros — e depois roda `install.R` para os pacotes que o conda não cobre bem | Build de R é **lento**. Isolar num estágio próprio significa que essa camada só é reconstruída quando o `install.R` ou a lista de pacotes conda mudam — alterações no estágio final (Python) não a invalidam. |
| **Estágio final** | Herda de `r-builder` (não de `system-base` diretamente — ver nota crítica abaixo). Instala pacotes Python via `uv pip` e `pip`, extensões do JupyterLab 4, temas, formatadores, e roda o build de produção do Lab (`jupyter lab build`) | Camada que muda com mais frequência (é aqui que a maioria dos ajustes de "preciso de mais uma lib Python" acontece). |

> ⚠️ **Por que o estágio final herda de `r-builder` e não de `system-base`**: o próprio Dockerfile marca isso como "CORREÇÃO CRÍTICA" em comentário. Herdar diretamente de `system-base` perderia as bibliotecas `.so` instaladas pelo conda no estágio `r-builder` — o estágio final **precisa** dessas dependências de sistema do R mesmo trabalhando majoritariamente com Python, porque parte do ecossistema geoespacial (`rpy2`-like bridges, algumas libs nativas) depende delas em runtime.

### Logging de verificação entre estágios

O Dockerfile intercala `RUN echo "===...==="` + `python -c "import jupyterlab; print(...)"` em vários pontos (após cada estágio, após o pin de versão, após os pacotes `uv`, após `geobr`, após o build final). Isso não é decoração — é uma técnica deliberada para diagnosticar builds quebrados: se a versão do JupyterLab mudar inesperadamente entre um log e outro (por exemplo, uma dependência transitiva forçando um downgrade), o log de build aponta exatamente **em qual RUN** isso aconteceu, sem precisar de bisect manual. Ao investigar um build com problema, procure por esses blocos `====` no output do `docker build` para localizar em qual etapa a versão divergiu do esperado.

### Pin explícito do JupyterLab

```dockerfile
RUN pip install --no-cache-dir 'jupyterlab>=4.0,<5.0'
```

O comentário no Dockerfile marca isso como **crítico**: sem esse pin, alguma dependência instalada depois (via `uv pip` ou `pip`) pode arrastar um downgrade silencioso para JupyterLab 3.x. O pin é reforçado logo depois com outro bloco de log de verificação.

---

## Conteúdo da imagem

Um resumo do que a imagem final oferece (a lista completa de pacotes está no próprio `Dockerfile` — não duplicada aqui para evitar que este documento fique desatualizado a cada ajuste de dependência):

- **Geoespacial (Python)**: `geopandas`, `rasterio`, `shapely`, `fiona`, `pyproj`, `rioxarray`, `xarray`, `geemap`/`leafmap` (Google Earth Engine), `pystac-client`, `rio-cogeo`, `geocube`, `pysal`, `momepy`, `movingpandas`, entre outros
- **Geoespacial (R)**: `sf`, `terra`, `stars`, `lidR`, `rnaturalearth`, além dos pacotes Bioconductor instalados via `install.R` (ver seção dedicada abaixo)
- **Dados em escala**: `dask`/`distributed`, `duckdb`, `pyarrow`, `polars`, integração com BigQuery e Google Cloud Storage
- **QGIS**: `python3-qgis` instalado a nível de sistema no estágio `system-base`
- **Extensões JupyterLab 4**: LSP (`jupyterlab-lsp` + `python-lsp-server`), colaboração em tempo real (`jupyter-collaboration`), spellchecker, execute-time, `nbdime` (diff de notebooks), temas (`theme-darcula`, `catppuccin-jupyterlab`)
- **Formatadores**: `black`, `isort`, `autopep8`, `jupyterlab-code-formatter`

---

## Pacotes R via `install.R`

Além dos pacotes R instalados via `mamba` no estágio `r-builder`, um segundo grupo — pacotes sem build conda estável, ou que dependem do **Bioconductor** — é instalado por `jupyterlab/docker/script/install.R`, copiado para dentro do build (`COPY script/install.R /tmp/install.R`) e executado com `Rscript`:

```r
# 1. Configuração de Mirror
options(repos = c(CRAN = "https://cran.r-project.org"))

# 2. Instalar primeiro o BiocManager e definir a versão correta para o R 4.5
if (!requireNamespace("BiocManager", quietly = TRUE)) {
    install.packages("BiocManager")
}
# Força a versão 3.22 compatível com R 4.5
BiocManager::install(version = '3.22', ask = FALSE, update = TRUE)

# 3. Lista de pacotes do CRAN (removendo os que falharam antes)
cran_packages <- c(
    'gamlss',
    'gamlss.dist',
    'gamlss.add',
    'gamlss.lasso',
    'rminer',
    'MachineShop',
    'resample',
    'gbm',
    'RPostgres',
    'RPostgreSQL'
)

install.packages(cran_packages, dependencies = TRUE)

# 4. Instalar pacotes que dependem do Bioconductor ou que costumam dar erro
# spsurvey e rpostgis muitas vezes precisam de bibliotecas BioC
BiocManager::install(c('spsurvey', 'rpostgis'), ask = FALSE)
```

### O que cada bloco faz

1. **Mirror CRAN** — fixa o repositório oficial, evitando depender de um mirror regional que pode estar desatualizado ou fora do ar.
2. **BiocManager + versão do Bioconductor** — o Bioconductor não segue o mesmo versionamento do R; cada versão do R é compatível com uma faixa específica de versões do Bioconductor. `version = '3.22'` é a versão compatível com **R 4.5** (a versão herdada da imagem base `datascience-notebook`).
3. **Pacotes CRAN "diretos"** — `gamlss` e sua família (modelos de regressão para forma, locação e escala), pacotes de machine learning (`rminer`, `MachineShop`, `gbm`), e drivers PostgreSQL (`RPostgres`, `RPostgreSQL`) para conectar a bancos geoespaciais (PostGIS). O comentário "removendo os que falharam antes" indica que essa lista já é resultado de iteração — pacotes que quebravam o build foram tirados daqui.
4. **Pacotes Bioconductor** — `spsurvey` (amostragem espacial) e `rpostgis` (bridge R↔PostGIS), que tipicamente dependem de bibliotecas do próprio Bioconductor para instalar corretamente.

> ⚠️ **Acoplamento de versão R ↔ Bioconductor**: se a imagem base (`BASE_CONTAINER`) for atualizada para uma versão diferente do R, a versão `3.22` do Bioconductor **precisa ser revisada** antes do próximo build. Instalar a versão errada do BiocManager tende a falhar de forma pouco óbvia — ou instala pacotes tecnicamente incompatíveis com o R em uso, o que só aparece como erro em runtime, dentro do notebook do usuário, bem depois do build ter "passado". Confira a [matriz de compatibilidade oficial do Bioconductor](https://bioconductor.org/about/release-announcements/) antes de mudar a versão do R base.
>
> **Adicionando um pacote novo**: teste o build isoladamente (rodando só o `install.R` contra um container já buildado, por exemplo) antes de assumir que ele vai compilar de primeira dentro do estágio `r-builder` completo — que é lento e caro de re-rodar do zero a cada tentativa.

---

## Build e publicação

Na maior parte do tempo você **não precisa buildar esta imagem** — normalmente já existe uma versão publicada no Docker Hub, e o DockerSpawner simplesmente a puxa via `DOCKER_NOTEBOOK_IMAGE` no `.env` do Hub. Builde do zero apenas quando estiver alterando o `Dockerfile` ou o `install.R`.

> ⚠️ **Lembre sempre de trocar o número da versão** (a tag `vX.Y.Z`) antes de buildar e publicar. Sobrescrever uma tag já em uso pode quebrar sessões de usuários que estejam com containers já rodando contra a imagem antiga — ou, pior, containers novos que sobem durante a janela de push podem acabar com uma imagem parcialmente publicada.

Os comandos abaixo assumem que você está **dentro** de `jupyterlab/docker/` — o contexto de build é `.`, e o `Dockerfile` faz `COPY script/install.R`, que só resolve corretamente a partir dessa pasta:

```bash
cd jupyterlab/docker/

docker build -t lapig/jupterlab:v3.0.8 .

docker login

docker push lapig/jupterlab:v3.0.8
```

Depois de publicar, atualize `DOCKER_NOTEBOOK_IMAGE` no `.env` do repositório principal para a nova tag, e reinicie o Hub (`docker compose restart jupyterhub`) para que novos logins já usem a versão nova. Sessões já ativas continuam na imagem antiga até o usuário reiniciar o próprio servidor Jupyter.

Para conferir se uma tag existe no Docker Hub sem baixá-la:

```bash
docker manifest inspect lapig/jupterlab:v3.0.8
```

---

## Debugando o build

Este build é longo (compilação de R, extensões do Lab, dezenas de pacotes Python) e tem vários pontos de falha plausíveis. Alguns atalhos:

- **Build falhou no `jupyter lab build`?** O Dockerfile já captura isso automaticamente — em caso de erro, ele imprime as últimas 250 linhas do log de debug do Jupyter (`/tmp/jupyterlab-debug-*.log`) antes de propagar a falha. Procure esse bloco `JUPYTER BUILD ERROR LOG` no output.
- **Versão do JupyterLab mudou sem explicação?** Procure os blocos `RUN echo "===...==="` no log do `docker build` (ver [Logging de verificação entre estágios](#logging-de-verificação-entre-estágios) acima) para isolar exatamente em qual `RUN` a versão divergiu.
- **`BUILD_INFO.txt`**: todo container final tem um `/home/jovyan/BUILD_INFO.txt` gerado no build, com as versões exatas de JupyterLab, Python, R, Node, Java, uv e a data do build. O `ENTRYPOINT` (`startup.sh`) imprime esse arquivo no início de toda sessão — é a forma mais rápida de confirmar, já dentro de um container de usuário, qual build está rodando.

---

## Manutenção e pontos de atenção

- **Nunca herdar o estágio final direto de `system-base`** — perde as libs `.so` do conda instaladas em `r-builder` (ver nota na seção de arquitetura).
- **Revisar a versão do Bioconductor a cada troca da imagem base** (`BASE_CONTAINER` / versão do R) — ver aviso na seção de pacotes R.
- **O pin `jupyterlab>=4.0,<5.0` é intencional** — não remover sem entender por que ele foi adicionado (downgrade silencioso via dependência transitiva).
- **`ipyvue`/`ipyvuetify`**: o Dockerfile desinstala deliberadamente a versão via `pip` e reinstala via `mamba` — a versão `pip` vem sem as dependências npm empacotadas e fica quebrada. Se precisar tocar nessas libs, mantenha esse padrão (mamba, não pip).
- **`cache bust`**: o comentário `# Build de produção (cache bust: 2024-11-28-008)` acima do `jupyter lab build` é um marcador manual — se precisar forçar a invalidação de cache dessa camada especificamente (sem mudar nenhum pacote), incremente esse identificador.