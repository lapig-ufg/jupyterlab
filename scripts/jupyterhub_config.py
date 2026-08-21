import json
import os
import dockerspawner
from oauthenticator.generic import GenericOAuthenticator

# --- CARREGAMENTO DE USUÁRIOS E PERMISSÕES ---
USERS_FILE = os.environ.get('USERS_JSON_PATH', '/srv/jupyterhub/users.json')

with open(USERS_FILE) as f:
    docker_config = json.load(f)

allowed_users = set(docker_config.keys())
admin_users = set([u for u, cfg in docker_config.items() if cfg.get('admin')])

# Configuração Padrão do Container de Usuário
docker_default = {
    "image": os.environ.get('DOCKER_NOTEBOOK_IMAGE', 'lapig/jupterlab:v3.0.7'),
    "mem_limit": os.environ.get('DOCKER_MEM_LIMIT', '4G'),
    "cpu_limit": int(os.environ.get('DOCKER_CPU_LIMIT', 1)),
    "network_name": os.environ.get('DOCKER_NETWORK_NAME', 'web_lapig'),
    "volumes": {
        "/home/aurilio/Desktop/jupyterhub/local_tests/jupyterhub/users/{username}": "/work",
        "/home/aurilio/Desktop/jupyterhub/local_tests/jupyterhub/users/{username}/.ssh": "/home/jovyan/.ssh",
        "/home/aurilio/Desktop/jupyterhub/local_tests/jupyterhub/shared": "/work/shared"
    }
}

def user_docker_config(spawner):
    with open(USERS_FILE) as f:
        _docker_config = json.load(f)
    
    username = spawner.user.name
    user_config = _docker_config.get(username, {})
    
    spawner.notebook_dir = "/work"
    spawner.image = user_config.get('image', docker_default['image'])
    spawner.network_name = user_config.get('network_name', docker_default['network_name'])
    spawner.mem_limit = user_config.get('mem_limit', docker_default['mem_limit'])
    spawner.cpu_limit = user_config.get('cpu_limit', docker_default['cpu_limit'])
    
    volumes = docker_default['volumes']
    user_volumes = user_config.get('volumes', {})
    spawner.volumes = {**volumes, **user_volumes} if isinstance(user_volumes, dict) else volumes


# --- REDE E SSL DO JUPYTERHUB ---
c.JupyterHub.bind_url = os.environ.get('JUPYTERHUB_BIND_URL', 'http://0.0.0.0:443')

c.JupyterHub.hub_ip = '0.0.0.0'
c.JupyterHub.hub_connect_ip = os.environ.get('HUB_CONNECT_IP', 'jupyterhub')


# --- AUTENTICAÇÃO KEYCLOAK (OAUTHENTICATOR) ---
c.JupyterHub.authenticator_class = GenericOAuthenticator

c.GenericOAuthenticator.client_id = os.environ.get('OAUTH_CLIENT_ID')
c.GenericOAuthenticator.client_secret = os.environ.get('OAUTH_CLIENT_SECRET')
c.GenericOAuthenticator.authorize_url = os.environ.get('OAUTH_AUTHORIZE_URL')
c.GenericOAuthenticator.token_url = os.environ.get('OAUTH_TOKEN_URL')
c.GenericOAuthenticator.oauth_callback_url = os.environ.get('OAUTH_CALLBACK_URL')

c.GenericOAuthenticator.userdata_from_id_token = True
c.GenericOAuthenticator.username_claim = 'preferred_username'
c.GenericOAuthenticator.scope = ['openid', 'profile', 'email', 'groups']
c.GenericOAuthenticator.claim_groups_key = 'groups'
c.GenericOAuthenticator.auth_state_groups_key = 'groups'
c.GenericOAuthenticator.manage_groups = True
c.GenericOAuthenticator.allowed_groups = {'data_science', '/data_science'}

c.GenericOAuthenticator.allowed_users = allowed_users
c.Authenticator.admin_users = admin_users


# --- SPAWNER (DOCKER) ---
c.JupyterHub.spawner_class = dockerspawner.DockerSpawner
c.Spawner.pre_spawn_hook = user_docker_config

c.DockerSpawner.network_name = docker_default['network_name']
c.DockerSpawner.use_internal_ip = True
c.DockerSpawner.pull_policy = 'ifnotpresent'
c.DockerSpawner.remove = False  # Altere para True em produção
c.DockerSpawner.debug = True

c.Spawner.start_timeout = int(os.environ.get('SPAWNER_START_TIMEOUT', 300))
c.Spawner.http_timeout = int(os.environ.get('SPAWNER_HTTP_TIMEOUT', 300))