# image_verification_in_k8s

POC of Concept of image signature and verification in Kubernetes clusters

## FluxCD

Fork this repository on your personal GitHub account and export your GitHub access token, username and repo name:

```sh
export GITHUB_TOKEN=<your-token>
export GITHUB_USER=<your-username>
export GITHUB_REPO=<repository-name>
```

Verify that your cluster satisfies the prerequisites with:

```sh
flux check --pre
```

Set the kubectl context to your staging cluster and bootstrap Flux:

```sh
flux bootstrap github \
    --context=arn:aws:eks:us-east-1:809870132669:cluster/demo-eks \
    --owner=${GITHUB_USER} \
    --repository=${GITHUB_REPO} \
    --branch=main \
    --personal \
    --path=clusters/dev/demo-eks
```
