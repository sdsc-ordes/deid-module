# deid-module

This repository defines helm chart to deploy a text de-identification module based on [Microsoft Presidio](https://github.com/microsoft/presidio) to deploy on a kubernetes cluster.
It is meant to be used as an HTTP API.

## Goal

The helm chart in this repository adapts the upstream presidio helm chart with the following goals:

- easily override yaml configs with custom values
- default support for multi-lingual texts (en/it/fr/de)

## Usage

The docker images and helm chart are published directly in the github container registry of this repository.
It can be installed with:

```shell
helm install --create-namespace presidio oci://ghcr.io/sdsc-ordes/deid-module-chart/deid-presidio
```

The chart does not declare any ingress, as its meant to be used by other services within the cluster.
If you want to experiment with it, create a port-forward:

```shell
kubectl port-forward svc/presidio-deid-presidio-analyzer 8080:80
```

The REST API documentation of Microsoft Presidio is available [here](https://microsoft.github.io/presidio/api-docs/api-docs.html) (or [here](https://web.archive.org/web/20230313231442/https://microsoft.github.io/presidio/api-docs/api-docs.html) via the Internet Archive's Wayback Machine])

## Configuration

You may configure the installation by providing a custom values.yaml file.

```shell
helm install -f custom-values.yaml --create-namespace presidio oci://ghcr.io/sdsc-ordes/deid-module-chart/deid-presidio
```

Note that the presidio configuration files are exposed through configMaps.
The values `analyzerConfigMapName` `defaultConfigMapName` and `recognizersConfigMapName` can be used to point to the name of an existing configMap.
You may look at [`configmap-default-recognizers.yaml`](./src/chart/templates/configmap-default-recognizers.yaml) for an example on how to write your own configmap.

## Development

> ![NOTE]
> The following requires nix to be installed in the system ([install nix](https://docs.determinate.systems/))

The repository contains a nix flake with all the tooling needed to develop and deploy the charts.
If direnv and nix are installed on the system, just run `direnv allow` in the repository to activate the development shell whenever you `cd` into it.

> [!NOTE]
> Alternatively, you can enter the devshell manually with
> `nix develop ./tools/nix#default --accept-flake-config --command zsh`

Additionally, a justfile contains recipes to work with the manifests. Typs `just` to list available recipes (`just` is included in the nix flake).
