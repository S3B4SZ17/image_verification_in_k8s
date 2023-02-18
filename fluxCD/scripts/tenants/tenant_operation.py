#!/usr/bin/env python3
import logging, argparse, os, shutil, yaml, git, sys
from jinja2 import Environment, FileSystemLoader
from kubernetes import client, config
from kubernetes.client import CoreV1Api
from kubernetes.client import V1Namespace
import subprocess

gh_repo = git.Repo('.', search_parent_directories=True)
git_repo_path = gh_repo.working_tree_dir

tenant_path = "tenants/base/"
cluster_path = "tenants/overlays/clusters/"
full_path_to_tenant = os.path.join(git_repo_path, tenant_path)
cluster_overlay_path = os.path.join(git_repo_path, cluster_path)
template_dir = "scripts/tenants/templates"
full_path_template_dir = os.path.join(git_repo_path, template_dir)

parser = argparse.ArgumentParser(prog="flux_tenant")

subparcer = parser.add_subparsers(dest="command")

install = subparcer.add_parser('install', help="install help")
install.add_argument("-t", "--tenant_name", required=True)
install.add_argument("-n", "--namespace", default="default", required=True)
install.add_argument("-g", "--gh_url", required=True, help="string argument is the GitHub URL of the repo in SSH format")
install.add_argument("-b", "--gh_branch", required=True, help="Checkout branch")
install.add_argument("-e", "--env_type", default="global", choices=["tools", "apps", "global"], help="The type of cluster to install the tenant: apps, tools or global that is the default")

remove = subparcer.add_parser('remove', help="remove help")
remove.add_argument("-t", "--tenant_name", required=True)
remove.add_argument("-n", "--namespace")
remove.add_argument("-e", "--env_type", default="global", choices=["tools", "apps", "global"], help="The type of cluster to install the tenant: apps, tools or global that is the default")

deploy_keys = subparcer.add_parser('deploy_keys', help="deploy_keys help")
deploy_keys.add_argument("-g", "--gh_url", required=True, help="string argument is the GitHub URL of the repo in SSH format")
deploy_keys.add_argument("-t", "--tenant_name", required=True)
deploy_keys.add_argument("-n", "--namespace", default="default", required=True)

args = parser.parse_args()

clusters: list[dict] = []
clusters_list: list = []
repo_info: dict = {}
current_cluster: str = "" 

def get_clusters_env_matrix(env: str) -> list[dict]:
    '''
    Returns a list of dictionaries by env.
    '''
    
    c1 = {'name': 'eks-apps-uw2-na-sbx', 'type': 'sbx', 'env': 'apps'}
    c2 = {'name': 'eks-apps-ue1-na-prod', 'type': 'prod', 'env': 'apps'}
    c3 = {'name': 'eks-apps-uw2-na-dev', 'type': 'dev', 'env': 'apps'}
    c4 = {'name': 'eks-apps-uw2-na-prod', 'type': 'prod', 'env': 'apps'}
    c5 = {'name': 'eks-tools-uw2-na-admin', 'type': 'admin', 'env': 'tools'}
    c6 = {'name': 'eks-tools-uw2-na-dev-01', 'type': 'dev', 'env': 'tools'}
    c7 = {'name': 'eks-tools-uw2-na-prod-01', 'type': 'prod', 'env': 'tools'}
    c8 = {'name': 'eks-vault-uw2-na-admin', 'type': 'admin', 'env': 'tools'}
    c9 = {'name': 'eks-apps-uw2-na-stg', 'type': 'stg', 'env': 'apps'}
    c10 = {'name': 'eks-tools-uw2-na-stg', 'type': 'stg', 'env': 'tools'}
    clusters = [c1, c2, c3, c4, c5, c6, c7, c8, c9, c10]
    
    list_clusters = []
    if env != "global":
        for cluster in clusters:
            for (k, v) in cluster.items():
                if v == env:
                    list_clusters.append(cluster)
        return list_clusters
    else:
        return clusters

def set_kubeconfig() -> CoreV1Api:
    '''
    Configure the Kubernetes cluster context.
    '''
    global current_cluster
    suffix_cluster_name = ":cluster/"
    contexts, active_context = config.list_kube_config_contexts()
    if not contexts:
        logging.error("Cannot find any kubeconfig contexts.")
        return

    contexts = [context['name'] for context in contexts]
    active_index = contexts.index(active_context['name'])
    raw_context = active_context['context']['cluster']
    current_cluster = raw_context.split(suffix_cluster_name)[-1]
    k_client = client.CoreV1Api(
        api_client=config.new_client_from_config(context=contexts[active_index]))
    return k_client

def create_namesapce(namespace: str):
    '''
    Creates a namespace based on the parameter passed if not exists.
    '''
    k_client = set_kubeconfig()
    try:
        namespaces = k_client.list_namespace(_request_timeout=3)
    except Exception as e:
        logging.exception("Exception occurred")
        sys.exit(1)
    if not any(ns.metadata.name == namespace for ns in namespaces.items):
        logging.info("Creating namespace %s", namespace)
        k_client.create_namespace(V1Namespace(metadata=dict(name=namespace)))
        logging.info("Namesapce: %s created!", namespace)
    else:
        logging.info("Using existing namespace %s", namespace)

def parse_gh_url(git_repo: str) -> dict:
    '''
    Get the GH repo URL in ssh format and returns a dict with the OWNER and REPO_NAME
    '''
    # ssh://git@github.com/zuora-zcloud/app_test_flux.git
    logging.info(f"Getting the owner and name of the GH repo ...")
    git_repo = git_repo.replace('ssh://git@github.com/', '')
    git_repo = git_repo.replace('.git', '')
    info = git_repo.split('/')
    repo_info=dict(owner=info[0], repo_name=info[1])
    logging.info(f"Repo info = {repo_info}")
    return repo_info

def check_git_repo_exists(git_repo: str) -> bool:
    '''
    Checks if the GH repo passed as arg exists and follows the <REPO_NAME>-infra naming convention.
    '''
    logging.info(f"Checking if repo already exists in GitHub and has the proper naming convention ...")
    infra_sufix = "-infra"
    
    if not repo_info['repo_name'].endswith(infra_sufix):
        logging.exception(f"The repository name should follow the standard of <REPO_NAME>{infra_sufix}")
        sys.exit(1)
    
    gh_search_repo = ['gh', 'repo', 'list', repo_info['owner'], '--json', 'name', '-q', '.[] | select(.name==\"' + repo_info['repo_name'] + '\")']
    tenant_gh_auth_yaml: str = args.tenant_name + '-auth.yaml'
    try:
        repo_exists = subprocess.run(gh_search_repo, stdout=subprocess.PIPE, text=True)
        if repo_exists.returncode != 0 or repo_exists.stdout == '':
            logging.exception(f"The GitHub repository provided ({git_repo}) does not exist. Please create it first")
            sys.exit(1)
        logging.info(f"Repository {repo_exists.stdout} exists")
        return tenant_gh_auth_yaml
    except Exception as e:
        logging.exception("Exception occurred")
        sys.exit(1)

def create_vars_dict() -> dict:
    content=dict(tenant_name=args.tenant_name, tenant_namespace=args.namespace, gh_url=args.gh_url, gh_branch=args.gh_branch)
    return content

def format_tempalte_manifests():
    '''
    Formating tenant manifest templaes.
    '''
    content = create_vars_dict()
    # Jinja block
    file_loader = FileSystemLoader(full_path_template_dir)  # Load template directory
    environment = Environment(loader=file_loader)  # Use environment from file_loader
    for template_file in environment.list_templates():
        template = environment.get_template(name=template_file)  # Get template from templates
        output_from_parsed_template = template.render(content)

        template_file = template_file.replace('.j2', '')
        # to save the results
        with open(full_path_to_tenant + '/' + template_file, "w") as fh:
            fh.write(output_from_parsed_template)
    
    create_kustomization_file(full_path_to_tenant)

def create_tenant_dir(tenant: str):
    '''
    Creates the tenant directory on the base layer.
    '''
    global tenant_path, full_path_to_tenant
    tenant_path += tenant
    full_path_to_tenant = os.path.join(git_repo_path, tenant_path)

    if not os.path.isdir(full_path_to_tenant):
        logging.info("Creating %s path of tenant", full_path_to_tenant)
        os.makedirs(full_path_to_tenant)
    else:
        logging.info("%s path of tenant already exists.", full_path_to_tenant)

def remove_tenant(tenant: str):
    '''
    We remove the tenant directory and the reference to it from the overlays clusters.
    '''
    global tenant_path, full_path_to_tenant, cluster_path, cluster_overlay_path, clusters, clusters_list
    clusters = get_clusters_env_matrix(args.env_type)
    clusters_list = [ sub['name'] for sub in clusters ]
    tenant_path += tenant
    full_path_to_tenant = os.path.join(git_repo_path, tenant_path)
    
    tenant_patch_f_name = args.tenant_name + '-patch.yaml'
    resource_path = "../../../base/" + args.tenant_name

    if os.path.isdir(full_path_to_tenant):
        logging.info("Removing %s dir ...", full_path_to_tenant)
        shutil.rmtree(full_path_to_tenant)
    else:
        logging.info("%s dir does not exists", full_path_to_tenant)

    for cluster in clusters_list:
        cluster_overlay_path = os.path.join(git_repo_path, cluster_path + cluster)
        if os.path.exists(cluster_overlay_path + '/' + args.tenant_name + '-patch.yaml'):
            logging.info(f"Removing {cluster_overlay_path + '/' + args.tenant_name + '-patch.yaml'} file ...")
            os.remove(cluster_overlay_path + '/' + args.tenant_name + '-patch.yaml')
        else:
            logging.info(f"{cluster_overlay_path + '/' + args.tenant_name + '-patch.yaml'} file does not exists")

        logging.info(f"Updating {cluster_overlay_path + '/kustomization.yaml'} file ...")
        with open(cluster_overlay_path + '/kustomization.yaml', 'r', encoding='utf8') as file:
            try:
                kustomization = yaml.safe_load(file)
            except Exception as exc:
                print(exc)
        
        if resource_path in kustomization['resources']:
            kustomization['resources'].remove(resource_path)
        
        if tenant_patch_f_name in kustomization['patchesStrategicMerge']:
            kustomization['patchesStrategicMerge'].remove(tenant_patch_f_name)

        with open(cluster_overlay_path + '/kustomization.yaml', 'w') as file:
            kustomization = yaml.dump(kustomization, file)
    
    logging.info("Tenant %s removed!", args.tenant_name)

def create_git_repo_secret(git_repo: str) -> str:
    '''
    Creates a secret using SSH authentication for the Git source, this uses deploy keys and not actual ssh keys.
    @git_repo = SSH format 
    '''
    flux_git_auth = ['flux', 'create', 'secret','git', args.tenant_name + '-auth', '--url=' + git_repo, '-n', args.namespace, '--export']
    tenant_gh_auth_yaml: str = args.tenant_name + '-auth.yaml'
    try:
        with open(tenant_gh_auth_yaml, "w") as outfile:
            subprocess.run(flux_git_auth, stdout=outfile)
        logging.info(f"Secret pub key {tenant_gh_auth_yaml} for GitHub repo created!")
        return tenant_gh_auth_yaml
    except Exception as e:
        logging.exception("Exception occurred")
        sys.exit(1)

def deploy_key_exists(tenant_key: str) -> bool:
    '''
    Check if the key with the arg name already exists in the repo.
    '''
    logging.info(f"Checking if the tenant already has a deploy key added ...")
    gh_deploy_key = ['gh', 'repo', 'deploy-key', 'list', '-R', repo_info['owner'] + '/' + repo_info['repo_name']]

    try:
        keys_list = subprocess.run(gh_deploy_key, stdout=subprocess.PIPE, text=True)
        if keys_list.returncode != 0:
            logging.exception(f"An error occured getting the keys for the {repo_info['owner'] + '/' + repo_info['repo_name']} ")
            return False
        
        if tenant_key in keys_list.stdout:
            logging.warning(f"Deploy key {tenant_key} already present in the repo.")
            return True
        return False
    except Exception as e:
        logging.exception("Exception occurred")
        sys.exit(1)

def save_gh_pub_key(git_repo: str):
    '''
    Add a deploy key to a GitHub repository.
    '''
    global repo_info
    repo_info = parse_gh_url(args.gh_url)
    deploy_key_name = args.tenant_name + '-key-' + current_cluster

    if not deploy_key_exists(deploy_key_name):
        pub_key_file: str = deploy_key_name + '-key.pub'
        tenant_gh_auth_yaml = create_git_repo_secret(git_repo)
        gh_get_key = ['yq', 'eval', '.stringData."identity.pub"', tenant_gh_auth_yaml]
        create_secret = ['kubectl', 'apply', '-f', tenant_gh_auth_yaml]

        # https://cli.github.com/manual/gh_repo_deploy-key_add
        gh_deploy_key = ['gh', 'repo', 'deploy-key', 'add', pub_key_file, '-R', repo_info['owner'] + '/' + repo_info['repo_name'], '-t', deploy_key_name]
        
        logging.info(f"Deploy new key {deploy_key_name} to the {repo_info['owner'] + '/' + repo_info['repo_name']} repo.")

        try:
            logging.info(f"Getting SSH pub key ...")
            with open(pub_key_file, "w") as outfile:
                subprocess.run(gh_get_key, stdout=outfile)
            create_secret_res = subprocess.run(create_secret, stdout=subprocess.PIPE, text=True)

            if create_secret_res.returncode != 0:
                logging.exception(f"Error creating {deploy_key_name} K8s secret.")
                sys.exit(1)

            deploy_key_res = subprocess.run(gh_deploy_key, stdout=subprocess.PIPE, text=True)
            logging.info(f"Creating K8s secret result: {create_secret_res.stdout}")
            logging.info(f"Deploying SSH key result: {deploy_key_res.stdout}")
            logging.info(f"Removing stored cred files ...")
            os.remove(pub_key_file); os.remove(tenant_gh_auth_yaml)
        except Exception as e:
            logging.exception("Exception occurred")
            sys.exit(1)

def create_kustomization_file(path_to_manifests: str):
    '''
    Creates kustomization file in the tenant base path.
    '''
    create_kustomization = ['kustomize', 'create', '--autodetect']
    # Get the current working directory
    cwd = os.getcwd()
    os.chdir(path_to_manifests)
    try:
        result = subprocess.run(create_kustomization, stdout=subprocess.PIPE, text=True)
        logging.info("Create kustomization file result: %s", result.stdout)
    except Exception as e:
        logging.exception("Exception occurred")
        sys.exit(1)
    os.chdir(cwd)

def create_overlay_kustomization(path_to_manifests: str, base_resources: str):
    '''
    Creates kustomization overlay file.
    '''
    create_kustomization = ['kustomize', 'create', '--resources', base_resources]
    # Get the current working directory
    cwd = os.getcwd()
    os.chdir(path_to_manifests)
    try:
        result = subprocess.run(create_kustomization, stdout=subprocess.PIPE, text=True)
        logging.info("Create kustomization overlay result: %s", result.stdout)
    except Exception as e:
        logging.exception("Exception occurred")
        sys.exit(1)
    os.chdir(cwd)

def update_cluster_overlay():
    '''
    Updates the specified cluster overlay, its kustomization and paths to the base tenant.
    '''
    for cluster in clusters:

        cluster_overlay_path = os.path.join(git_repo_path, cluster_path + cluster.get("name"))
        tenant_patch_f_name = args.tenant_name + '-patch.yaml'
        resource_path = "../../../base/" + args.tenant_name
        tenant_patch = {'apiVersion': 'kustomize.toolkit.fluxcd.io/v1beta2', 'kind': 'Kustomization', 'metadata': {'name': args.tenant_name, 'namespace': args.namespace}, 'spec': {'path': './deployments/' + cluster.get("type") + '/' + cluster.get("name")}}
        
        logging.info("Updating %s overlay", cluster.get("name"))

        if not os.path.isdir(cluster_overlay_path):
            logging.info("Creating %s cluster overlay", cluster_overlay_path)
            os.makedirs(cluster_overlay_path)
        
        with open(cluster_overlay_path + '/' + tenant_patch_f_name, 'w') as file:
            yaml.dump(tenant_patch, file)

        if not os.path.exists(cluster_overlay_path + '/kustomization.yaml'):
            create_overlay_kustomization(cluster_overlay_path, resource_path)
        
        with open(cluster_overlay_path + '/kustomization.yaml', 'r', encoding='utf8') as file:
            try:
                kustomization: dict = yaml.safe_load(file)
            except Exception as exc:
                logging.exception("Exception occurred")
        
        if resource_path not in kustomization['resources']:
            kustomization['resources'].append(resource_path)
        
        if not "patchesStrategicMerge" in kustomization.keys():
            kustomization['patchesStrategicMerge'] = [tenant_patch_f_name]
        
        if tenant_patch_f_name not in kustomization['patchesStrategicMerge']:
            kustomization['patchesStrategicMerge'].append(tenant_patch_f_name)

        with open(cluster_overlay_path + '/kustomization.yaml', 'w') as file:
            kustomization = yaml.dump(kustomization, file)

def install_tenant():
    '''
    Function that will call helpers functions to install the tenant.
    '''
    global repo_info, clusters, clusters_list
    repo_info = parse_gh_url(args.gh_url)
    clusters = get_clusters_env_matrix(args.env_type)
    clusters_list = [ sub['name'] for sub in clusters ]
    create_namesapce(args.namespace)
    check_git_repo_exists(args.gh_url)
    create_tenant_dir(args.tenant_name)
    format_tempalte_manifests()
    save_gh_pub_key(args.gh_url)
    update_cluster_overlay()

def main():
    # Check actions
    logging.basicConfig(format='%(asctime)s-%(process)d-%(levelname)s- %(message)s', level=logging.INFO)
    
    if args.command == "install":
        install_tenant()
    elif args.command == "remove":
        remove_tenant(args.tenant_name)
    elif args.command == "deploy_keys":
        create_namesapce(args.namespace)
        save_gh_pub_key(args.gh_url)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()
