#!/bin/bash
# Script para criar pastas de usuários a partir de um arquivo JSON

JSON_FILE="/home/aurilio/Desktop/jupyterhub/data/users.json"
BASE_DIR="/home/aurilio/Desktop/jupyterhub/local_tests/jupyterhub/users"
USER_ID=1000
GROUP_ID=1000

# Verificar se o arquivo JSON existe
if [ ! -f "$JSON_FILE" ]; then
    echo "Erro: Arquivo $JSON_FILE não encontrado!"
    exit 1
fi

# Verificar se jq está instalado
if ! command -v jq &> /dev/null; then
    echo "Erro: jq não está instalado. Instale com: sudo apt-get install jq"
    exit 1
fi

# Criar diretório base se não existir
mkdir -p "$BASE_DIR"

# Ler usuários do JSON e criar/verificar pastas
echo "Processando pastas para os usuários em $BASE_DIR..."
echo ""

jq -r 'keys[]' "$JSON_FILE" | while read USERNAME; do
    # Substituir pontos por -2e e underscores por -5f no nome da pasta
    FOLDER_NAME="${USERNAME//./-2e}"
    FOLDER_NAME="${FOLDER_NAME//_/-5f}"
    USER_DIR="$BASE_DIR/$FOLDER_NAME"
    
    # Verificar se a pasta existe
    if [ -d "$USER_DIR" ]; then
        # Pasta existe - verificar ownership
        CURRENT_UID=$(stat -c '%u' "$USER_DIR")
        CURRENT_GID=$(stat -c '%g' "$USER_DIR")
        
        if [ "$CURRENT_UID" != "$USER_ID" ] || [ "$CURRENT_GID" != "$GROUP_ID" ]; then
            # Ownership diferente - corrigir
            chown $USER_ID:$GROUP_ID "$USER_DIR"
            echo "⚠ Pasta existente - ownership corrigido: $USER_DIR"
            echo "  - Usuário: $USERNAME → Pasta: $FOLDER_NAME"
            echo "  - Owner anterior: $CURRENT_UID:$CURRENT_GID → novo: $USER_ID:$GROUP_ID"
        else
            # Ownership já está correto
            echo "✓ Pasta existente - ownership correto: $USER_DIR ($USER_ID:$GROUP_ID)"
            if [ "$USERNAME" != "$FOLDER_NAME" ]; then
                echo "  - Usuário: $USERNAME → Pasta: $FOLDER_NAME"
            fi
        fi
    else
        # Pasta não existe - criar
        mkdir -p "$USER_DIR"
        chown $USER_ID:$GROUP_ID "$USER_DIR"
        chmod 755 "$USER_DIR"
        echo "✓ Pasta criada: $USER_DIR (Owner: $USER_ID:$GROUP_ID)"
        if [ "$USERNAME" != "$FOLDER_NAME" ]; then
            echo "  - Usuário: $USERNAME → Pasta: $FOLDER_NAME"
        fi
    fi
    echo ""
done

echo "Processo concluído!"
echo ""
echo "Verificando estrutura criada:"
ls -la "$BASE_DIR" | head -20