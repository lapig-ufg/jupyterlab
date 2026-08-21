import json

cpu_count = 48
recomendado_men = 125

with open('users.json') as f:
    docker_config = json.load(f)

rows = []

def menToInt(x):
    return int(x.replace("G",""))
    
mens_user = []
cpus_user = []
for user in docker_config:
    mem_limit = menToInt(docker_config[user].get('mem_limit','4G'))
    cpus = docker_config[user].get('cpu_limit',1)
    mens_user.append(mem_limit)
    cpus_user.append(int(cpus))


total_cpu = sum(cpus_user)
if total_cpu <= cpu_count:
    print('cpu OK')
else:
    print(f'mem não OK\n Total {total_cpu} \n recomendado {cpu_count} \n excedeu {total_cpu- cpu_count}')


total_men = sum(mens_user)
if total_men <= recomendado_men:
    print('mem OK')
else:
    print(f'mem não OK\n Total {total_men} \n recomendado {recomendado_men} \n excedeu {total_men- recomendado_men}')

