#!/usr/bin/env python
import sys
import subprocess
import logging
from argparse import ArgumentParser

p = ArgumentParser()

group = p.add_mutually_exclusive_group()
group.add_argument("-f", "--file", action="store", metavar="FILE",
                   help="File with list of images to import")
group.add_argument("-i", "--image", action="store", metavar="IMAGE",
                   help=("Image to import. "
                         "Must use pattern: <registry>/<repo>/<image>"))
p.add_argument("-t", "--tags", action="store", metavar="TAGS",
               help=("Optional list of tags to import. "
                     "Defaults to all tags"))
p.add_argument("-n", "--namespace", action="store", metavar="NAMESPACE",
               help=("Import image to a specific namespace. "
                     "Defaults to the repository name of the source image"))
p.add_argument("--disable-scheduled-imports", dest="scheduled",
               action="store_false", help="Disable scheduled imports")
p.add_argument("--disable-pullthrough", dest="pullthrough",
               action="store_false", help="Disable pullthrough")
p.add_argument("--dry-run", action="store_true", default=False,
               help="Enable dry-run. Only print commands")
args = p.parse_args()

loglevel = logging.DEBUG if args.dry_run else logging.INFO
logging.basicConfig(format="%(asctime)s %(levelname)s: %(message)s",
                    level=loglevel)

############################################################


def call_oc(cmd):
    if args.dry_run:
        logging.debug("DRY-RUN: " + cmd)
    else:
        return subprocess.call(cmd, shell=True)


def create_project(name):
    if call_oc("oc get project %s >/dev/null 2>&1" % name) != 0:
        call_oc("oc new-project %s" % name)
        call_oc("oc policy add-role-to-user system:image-puller \
                system:anonymous -n %s" % name)
        call_oc("oc policy add-role-to-group registry-viewer \
                system:authenticated -n %s" % name)


def is_tag_scheduled(isname, tag, namespace):
    cmd = """
oc get istag %s:%s -o jsonpath='{.tag.importPolicy.scheduled}' \
-n %s 2>/dev/null | grep -q ^true$""" % (isname, tag, namespace)
    if call_oc(cmd) == 0:
        return True
    return False


def get_all_scheduled_tags():
    cmd = '''
oc get istag --all-namespaces \
-o jsonpath=\'{range .items[*]}{.metadata.namespace}/{.metadata.name},\
{.tag.importPolicy.scheduled}{"\\n"}{end}\' | grep ,true$ |cut -f1 -d,'''
    if args.dry_run:
        logging.debug("DRY-RUN: " + cmd)
        return []
    try:
        output = subprocess.check_output(cmd, shell=True)
        return [i for i in output.strip().split('\n')]
    except subprocess.CalledProcessError as e:
        logging.error(e.outout)
        return []


def get_import_opts(tag=None, pullthrough=True, scheduled=True, confirm=True):
    opts = []
    if confirm:
        opts.append("--confirm")
    if pullthrough:
        opts.append("--reference-policy=local")
    if scheduled:
        opts.append("--scheduled")
    if tag is None:
        opts.append("--all")
    return " ".join(opts)


def oc_import_image(name, image_reference, namespace, tag=None,
                    pullthrough=True, scheduled=True):
    image = "%s:%s" % (name, tag) if tag else name
    opts = get_import_opts(tag, pullthrough, scheduled)

    logging.info("Importing image %s from %s" % (image, image_reference))
    logging.debug("Importing image %s with options '%s'" % (image, opts))
    return call_oc("""
oc import-image %s --from=%s %s -n %s >/dev/null""" % (image, image_reference,
                                                       opts, namespace))


def import_by_tags(name, image_ref, tags, namespace, scheduled_tags=None,
                   pullthrough=True, scheduled=True):
    for tag in tags:
        istag = "%s/%s:%s" % (namespace, name, tag)
        if ((scheduled_tags and istag not in scheduled_tags)
                or not is_tag_scheduled(name, tag, namespace)):
            return oc_import_image(name, image_ref, namespace, tag=tag,
                                   pullthrough=pullthrough,
                                   scheduled=scheduled)
        else:
            logging.info("""
Image tag %s:%s is already configured for scheduled updates""" % (name, tag))


def import_all_tags(name, image_ref, namespace, pullthrough=True,
                    scheduled=True):
    return oc_import_image(name, image_ref, namespace,
                           pullthrough=pullthrough, scheduled=scheduled)


def get_images():
    if args.file:
        try:
            images = [i.strip() for i in open(args.file, 'r')]
        except IOError as e:
            logging.error("cannot open %s. message: %s" % (args.file, e))
            sys.exit(2)
    elif args.image:
        images = []
        images.append(args.image)
    else:
        p.print_help()
        sys.exit(1)
    return images


def main():
    if args.tags:
        tags = set(args.tags.split(','))
        if args.scheduled and len(tags) > 2:
            scheduled_tags = get_all_scheduled_tags()
        else:
            scheduled_tags = None

    for image in get_images():
        image_info = image.split('/')
        name = image_info[-1]

        if args.namespace:
            namespace = args.namespace
        else:
            namespace = image_info[-2]

        create_project(namespace)
        if args.tags:
            import_by_tags(name, image, tags, namespace,
                           scheduled_tags=scheduled_tags,
                           pullthrough=args.pullthrough,
                           scheduled=args.scheduled)
        else:
            import_all_tags(name, image, namespace,
                            pullthrough=args.pullthrough,
                            scheduled=args.scheduled)


if __name__ == '__main__':
    main()
