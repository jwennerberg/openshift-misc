from __future__ import print_function
import sys
from kubernetes import config, client as kubeclient
from kubernetes.client.rest import ApiException
from pprint import pprint

config.load_kube_config()

api = kubeclient.CoreV1Api()

try:
    quotalist = api.list_resource_quota_for_all_namespaces()
    namespacelist = api.list_namespace()
except ApiException as e:
    print("Exception when calling CoreV1Api: %s\n" % e)
    sys.exit(1)

labels = { n.metadata.name: n.metadata.labels for n in namespacelist.items }

print("%-20s %-6s %s" % ("Namespace","CPU","Memory"))
for q in quotalist.items:
    try:
        appid = labels[q.metadata.namespace]['application-id']
    except:
        appid = None

    if appid and appid != "":
        print("%-20s %-6s %-10s %s" % (q.metadata.namespace,
                q.status.hard['persistentvolumeclaims'],
                q.status.hard['pods'],
                appid))
