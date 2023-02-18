# Create tenant

## Pre-requisites

You need to have installed `flux, kustomize, gh` CLI packages.

## Configure the gh CLI

You will need to first have a PAT token for your GitHub account, refer to the [documentation](https://docs.github.com/en/enterprise-server@3.4/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token#creating-a-personal-access-token) to create one. Then set the `GITHUB_TOKEN` env var for your current shell.
`export GITHUB_TOKEN=$(cat ../GH_tokens/fluxcd)`
**Note: You should configure SSO for that token for the GitHub organizations you are part of**

## Install the tenant

Make sure you are connected to the correct EKS cluster and have the proper kubeconfig and context ($KUBECONFIG). After cloning this repo you can locally run the script and add a tenant:
`python3 scripts/tenants/tenant_operation.py install -t test-tenant -n test-tenant -g ssh://git@github.com/zuora-zcloud/app_test_flux.git -b main`

Run `python3 scripts/tenants/tenant_operation.py install -h` to see the complete list of options, the above arguments are all required for the installation. For the `-g/--gh_url` argument is the GitHub URL in SSH format.

```bash
usage: flux_tenant install [-h] -t TENANT_NAME -n NAMESPACE -g GH_URL -b GH_BRANCH [-e {tools,apps,global}]

options:
  -h, --help            show this help message and exit
  -t TENANT_NAME, --tenant_name TENANT_NAME
  -n NAMESPACE, --namespace NAMESPACE
  -g GH_URL, --gh_url GH_URL
                        string argument is the GitHub URL of the repo in SSH format
  -b GH_BRANCH, --gh_branch GH_BRANCH
                        Checkout branch
  -e {tools,apps,global}, --env_type {tools,apps,global}
                        The type of cluster to install the tenant: apps, tools or global that is the default
```

`kubectl apply -k tenants/overlays/clusters/eks-tools-uw2-na-dev-01/`

### Workflow

Link to the ["Create Flux tenant"](https://github.com/zuora-zcloud-admin/kubernetes-fleet/actions/workflows/create-tenant.yaml) workflow. You will need to fill up the inputs as follows:

* **tenant_name**: Name of the new tenant
* **namespace**: Namespace of the new tenant
* **gh_url**: GitHub URL in SSH format for the tenant
* **gh_branch**: Git branch of your repo app
* **cluster_name**: The cluster name where the deploy ssh keys (k8s secret) will be created for the **gh_url**
* **cluster_region**: The cluster's region
* **envs**: The cluster environment type to install the tenant. i.e if apps selected, it
  will create the reference overlays in all the apps clusters. If global is selected will be applied to both apps and tools clusters.
* **save_tenant_to_gh**: Specify if you want to automatically commit the changes to the **deployment_branch**. If not selected the new tenant manifests won't be saved. Will be like a dry run.
* **deployment_branch**: New repo branch to commit the changes and add the new tenant

Important things to consider that the workflow will perform:

* The creation of the tenant will run per cluster based on the **cluster_name** option. Even though new manifests will be created for the flux base tenant and kustomization overlays in the different paths of the repo, the first run of the automation will also connect to the cluster, deploy the SSH keys for the **gh_url** repo you specified and create a K8s secret in the **namespace**.
* The result of the workflow will be a new **deployment_branch** in the repo that will contain a commit with the new tenant configuration if you select the **save_tenant_to_gh** option. Then you can check out the branch review that tenant is configured as expected and then submit a PR.
* Once the tenant manifests are committed to the new branch you can go ahead and run the ["Deploy tenant keys"](https://github.com/zuora-zcloud-admin/kubernetes-fleet/actions/workflows/deploy-tenant-keys.yaml) workflow against the different clusters (currently it will only work in `eks-tools-uw2-na-dev-01`. We are working in the [ESG-716](https://zuora.atlassian.net/browse/ESG-716) ticket to have it in all envs). This workflow will create the necessary K8s secret with the SSH keys Flux needs to authenticate to your **gh_url** repo where your code is. Flux needs those keys to pull the changes and start the reconciliation.

## Remove a tenant

Locally run the following command and change the values for your own tenant:
`python3 scripts/tenants/tenant_operation.py remove -t test-tenant`

The `--namespace` parameter is optional, pass it if you also want to remove the namespace of the tenant, be careful!

## Add deploy keys to the GitHub repo

For flux to authenticate and fetch your GitRepository it needs a set of deploy keys, currently, the `flux create secret git` command creates a K8s secret with the deploy keys in it. The install `tenants/tenant_operation.py install` will automatically deploy a set of keys in the `-g ssh://git@github.com/zuora-zcloud/github-runners.git` if it does not exist already. You can also run the command
`python3 scripts/tenants/tenant_operation.py deploy_keys -t test-tenant -g ssh://git@github.com/zuora-zcloud/github-runners.git -n test-tenant`. This script is dependent on the `gh` cli tool.

## Running the script through the Create Flux tenants workflow

Currently, we do not recommend running the script through the `Create Flux tenants` workflow. Is there but it needs to update for complete automation.

## Integrating current tenants

Please refer to the `test-tenant` that is already provisioned and check its manifests. Take a look at the `scripts/tenants/templates` dir since it has the templates that the script is using for creating the YAML mainfests.

### GitHub Repo structure

In the mayority of cases we prefer having the application package in helm charts but if you just have the manifest files consider checking the [app\_test\_flux](https://github.com/zuora-zcloud/app_test_flux) test app and see its structure for the deployments. You will need to have the `deployments` dir and its separation based on the environment type. In that path is where you will have the YAML manifests for your app, any deployment, helmRelease, ImageRepository, ...

```bash
lt
 .
├──  deployment.yaml
├──  deployments
│   ├──  admin
│   │   └──  eks-tools-uw2-na-admin
│   ├──  dev
│   │   └──  eks-tools-uw2-na-dev-01
│   │       └──  deployment.yaml
│   └──  prod
├──  job-creds-helper.yaml
├──  nexus-credentials.yaml
├──  nexus-self-signed-cert.yaml
├──  README.md
└──  src
    ├──  app
    │   ├──  application.go
    │   └──  url_mapping.go
    ├──  bin
    │   └──  app_test_flux.out
    ├──  cmds
    │   └──  root.go
    ├──  config
    │   └──  config.go
    ├──  config.yaml
    ├──  controllers
    │   └──  ping.go
    ├──  Dockerfile
    ├──  go.mod
    ├──  go.sum
    ├──  main.go
    ├──  Makefile
    ├──  management
    │   └──  logs.go
    └──  outputs.log
```

This is necessary because the kustomization yaml patch that is in the `tenants/overlays/clusters/<cluster_name>` is referencing a remote target (the github repo), and that is the path kustomize will search to apply the manifests.

## Deploy SSH keys for tenant

Every `GitRepository` configuration for a tenant depends on a set of SSH keys for  that Flux will use for authentication. If you just want to deploy those keys to the repo and create the K8s in the specified tenant you can run the following script:

```sh
python3 scripts/tenants/tenant_operation.py deploy_keys -h
usage: flux_tenant deploy_keys [-h] -g GH_URL -t TENANT_NAME -n NAMESPACE

options:
  -h, --help            show this help message and exit
  -g GH_URL, --gh_url GH_URL
                        string argument is the GitHub URL of the repo in SSH format
  -t TENANT_NAME, --tenant_name TENANT_NAME
  -n NAMESPACE, --namespace NAMESPACE
```

## Applying the manifests

Once the manifests are created you can apply them by running `kubectl apply -k tenants/overlays/clusters/<YOUR_CLUSTER_NAME>/` or running `kubectl apply -f <FILE_PATH>`.
