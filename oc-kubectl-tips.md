# Misc `oc` and `kubectl` tips and tricks

### JSONPath
```
oc get is -n openshift -o jsonpath='{.items[*].spec.tags[?(@.from.kind == "DockerImage")].from.name}'
```
