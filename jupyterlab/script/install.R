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