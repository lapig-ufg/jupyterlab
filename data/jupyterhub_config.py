from oauthenticator.generic import GenericOAuthenticator
import json


docker_default = {
        "image": "lapig/jupterlab:v3.0.3",
        "mem_limit": "4G",
        "cpu_limit": 1,
        "network_name": "web_lapig",
        "volumes": {
            "/data/jupyterhub/users/{username}": "/work",
            "/data/jupyterhub/users/{username}/.ssh": "/home/jovyan/.ssh",
            "/data/jupyterhub/shared": "/work/shared"
        }
    }

# Carregar a configuração do DockerSpawner do arquivo JSON uma vez
with open('/srv/jupyterhub/users.json') as f:
    docker_config = json.load(f)
    
allowed_users = set(docker_config.keys()) 
admin_users = set([username for username, user_config in docker_config.items() if user_config.get('admin')])  

# Função para aplicar as configurações de limite com base no usuário
def user_docker_config(spawner):
    with open('/srv/jupyterhub/users.json') as f:
        _docker_config = json.load(f)
    # Obtém o nome do usuário
    username = spawner.user.name
    user_config = _docker_config[username]
    # Aplica as configurações padrão do DockerSpawner
    spawner.notebook_dir = "/work"

    # Configurações específicas por usuário, se existirem
    spawner.image = user_config.get('image', docker_default['image'])
    spawner.network_name = user_config.get('network_name', docker_default['network_name'])
    spawner.mem_limit = user_config.get('mem_limit', docker_default['mem_limit'])
    spawner.cpu_limit = user_config.get('cpu_limit', docker_default['cpu_limit'])
    
    # Obtém os volumes padrão
    volumes = docker_default['volumes']

    # Verifica se as configurações do usuário para volumes são um dicionário
    user_volumes = user_config.get('volumes', {})

    # Combina os volumes padrão com os volumes do usuário
    if isinstance(user_volumes, dict):
        spawner.volumes = {**volumes, **user_volumes}
    else:
        spawner.volumes = volumes


        

c.JupyterHub.spawner_class = 'dockerspawner.DockerSpawner'
c.JupyterHub.hub_ip = '0.0.0.0'
c.JupyterHub.hub_connect_url = 'http://jupyterhub:8081/hub/api'

c.JupyterHub.ssl_cert = '/ssl/certe.crt'
c.JupyterHub.ssl_key = '/ssl/key.key'
c.JupyterHub.port = 443  # ou outra porta segura de sua escolha
c.JupyterHub.bind_url = 'https://0.0.0.0:443'

# Configuração do DockerSpawner
c.DockerSpawner.remove_containers = True
c.DockerSpawner.debug = True
# Aplica os limites de recursos por usuário com base no JSON
c.Spawner.pre_spawn_hook = user_docker_config


c.JupyterHub.authenticator_class = GenericOAuthenticator

c.GenericOAuthenticator.client_id = 'jupyterhub'
c.GenericOAuthenticator.client_secret = 'P4Lr753jaDVBiBag6ROQN4tndmOiNZBA'
c.GenericOAuthenticator.oauth_callback_url = 'https://sci.lapig.iesa.ufg.br/hub/oauth_callback'
c.GenericOAuthenticator.authorize_url = 'https://auth.lapig.iesa.ufg.br/realms/lapig/protocol/openid-connect/auth'
c.GenericOAuthenticator.token_url = 'https://auth.lapig.iesa.ufg.br/realms/lapig/protocol/openid-connect/token'
c.GenericOAuthenticator.userdata_url = 'https://auth.lapig.iesa.ufg.br/realms/lapig/protocol/openid-connect/userinfo'
c.GenericOAuthenticator.scope = ['openid', 'profile', 'email']
c.GenericOAuthenticator.username_key = 'preferred_username'
c.GenericOAuthenticator.auth_state_groups_key ='groups'
c.GenericOAuthenticator.manage_groups = True
c.GenericOAuthenticator.allowed_groups = {'data_science'}
c.GenericOAuthenticator.allowed_users = allowed_users
c.Authenticator.admin_users = admin_users

