# Services management

The deployment defines multiple service (or application), each being a
collection of kubernetes manifests located in `src/<service>/`.

## Structure

- `external/`: third party resources
- `src/`: deployable manifests
- secrets are encrypted with sops+age and persisted in `src/secrets/`

Each service is structured as follows (supported tools are `ytt` and `helm`):

```text
├── external
│  └── <tool>
│     └── <service>/... # <- third party templates
└── src
   └── <service>
      ├── additional-manifest.yaml # <- custom manifests for this deployment
      ├── kustomization.yaml # <- kustomization file to select resources
      └── <tool>
         ├── out/... # <- rendered manifests
         └── values.yaml # <- values used for templating
```

## Templating

[ytt](https://carvel.dev/ytt) is the preferred rendering engine, but helm is
also supported as many upstream templates are distributed with
[helm](https://helm.sh).

When running `just render`, we attempt to render each service with helm and then
with ytt and save the rendered manifests in the repository.

## Deployment

When deploying with `just deploy`, deployment is done with kustomize
(`kubectl -k`). This means that the `src` and each of its subdirectories contain
a `kustomization.yaml` file which determine what manifests are included in the
deployment.

For example, running `just deploy src/` will recursively parse
`src/kustomization.yaml` and the `kustomization.yaml` from each resources
declared in that file. This allows to simply exclude services or manifests by
commenting them out of `kustomization.yaml`.

## Updating a service

Here is the typical workflow to re-deploy a service that has been updated
upstream.

1. Update the external manifest templates. This will update the `vendir` lock
   file and fetch the latest templates into `external/<tool>/<service>`.

```bash
just external::refresh
```

2. Render the manifests with the new templates.

```bash
just render
```

> [!NOTE]
> This may fail if the new templates broke compatibility with existing values,
> in which case you will need to update your values in
> `src/<service>/<tool>/values.yaml`. Also watch out in case the upstream added
> new template files, as you may need to include them in the service
> `kustomization.yaml`.

3. Deploy the updated manifests.

```bash
just deploy src/<service>
```

> [!IMPORTANT]
> In some cases, you may want to manually delete resources related to the
> service. You can achieve that with `just delete src/<service>` or use
> `kubectl delete` to delete specific resoruces.

## Adding custom manifests

Custom manifests (e.g. additional volumes) can be added inside `src/<service>/`,
but they need to be added as a resource in `kustomization.yaml` file in the same
directory.
