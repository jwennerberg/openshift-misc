import os.path
import re
from bitmath import parse_string_unsafe, GiB, MiB
from openshift import client,config
from kubernetes import config, client as kubeclient
from kubernetes.client.rest import ApiException
from pprint import pprint
from flask import Flask, render_template
application = Flask(__name__)

SERVICE_TOKEN_FILENAME = "/var/run/secrets/kubernetes.io/serviceaccount/token"

if os.path.isfile(SERVICE_TOKEN_FILENAME):
    config.load_incluster_config()
else:
    config.load_kube_config()


def to_bytes(value):
    return parse_string_unsafe(value).to_Byte().bytes

def to_mib(value):
    return MiB(bytes=to_bytes(value))

def to_gib(value):
    b = parse_string_unsafe(value).to_Byte().bytes
    return GiB(bytes=b)

def to_millicores(value):
    try:
        unit = re.split('([a-zA-Z]+)',value)
    except TypeError:
        return None
    if len(unit) > 1:
        return int(unit[0])
    else:
        return int(unit[0]) * 1000

def to_cores(value):
    unit = re.split('([a-zA-Z]+)',value)
    if len(unit) > 1:
        return float(unit[0]) / 1000
    else:
        return int(unit[0])

def get_namespace_label(namespace, label_name):
    label = None
    if namespace.metadata.labels:
        label = namespace.metadata.labels.get(label_name)
    return label


@application.route('/')
def home():
    return "SEBShift Inventory\n"


@application.route('/namespaces')
def namespace():
    api = kubeclient.CoreV1Api()
    try:
        namespacelist = api.list_namespace()
        quotalist = api.list_resource_quota_for_all_namespaces()
    except ApiException as e:
        return "Exception when calling CoreV1Api: %s\n" % e

    quotas = { q.metadata.namespace: {'cpu': q.status.hard.get('requests.cpu'),
              'memory': q.status.hard.get('requests.memory')} for q in quotalist.items }

    total_cpu = 0
    total_mem = 0
    data = []
    for n in namespacelist.items:
        cpu_cores = None
        memory_gib = None
        if quotas.get(n.metadata.name):
            quota_cpu = to_cores(quotas[n.metadata.name].get('cpu'))
            quota_mem = to_gib(quotas[n.metadata.name].get('memory'))
            total_cpu += quota_cpu
            total_mem += quota_mem

        data.append({'namespace': n.metadata.name,
                        'quota_cpu': quota_cpu, 'quota_memory': quota_mem,
                        'appid': get_namespace_label(n, 'application-id'),
                        'router': get_namespace_label(n, 'router')})
    return render_template('namespace.html', nslist=data, total_cpu=total_cpu,
                            total_mem=total_mem)


@application.route('/namespace/<namespace>/podresources')
