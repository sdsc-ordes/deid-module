# Services management

The deployment is packaged as a single Helm chart located in `src/chart/`.
It bundles the upstream Presidio services (analyzer, anonymizer) together with
the custom services developed in this repository (surrogate).

## Structure

- `src/chart/`: the Helm chart deployed to the cluster
  - `Chart.yaml`: chart metadata
  - `values.yaml`: default values (overridable at install time)
  - `templates/`: kubernetes manifest templates
  - `conf/`: default Presidio configuration files (exposed as ConfigMaps)
  - `data/`: bundled example data (e.g. the example surrogate map)
- `src/modules/`: source code for the custom services built in this repo
  - `surrogate/`: the surrogate-generation FastAPI service (see its `README.md`)
- `external/`: third-party resources fetched and pinned with
  [vendir](https://carvel.dev/vendir) (the upstream Presidio repo), plus local
  patches in `external/patches/`
- `tools/`: the nix flake and the `just` recipe modules

## Templating

The chart is rendered with [helm](https://helm.sh). Running `just render`
templates the chart with the values in `src/chart/values.yaml` and writes the
rendered manifests under `build/`:

```bash
just render
```

This is equivalent to `helm template dev src/chart -f src/chart/values.yaml
--output-dir build` followed by formatting.

## Deployment

`just deploy` installs (or upgrades) the chart on the cluster with
`helm upgrade --install`:

```bash
just deploy
```

By default this deploys `src/chart` as release `dev` into the `ml-clin-deid`
namespace. You can point it at another chart directory by passing it as an
argument (`just deploy <dir>`).

To configure the installation, override values from `src/chart/values.yaml`
(see the root `README.md` for the published-chart workflow with a custom
`values.yaml`).

## Updating an external dependency

The upstream Presidio sources are vendored under `external/repos/` and pinned in
`external/vendir.lock.yml`. The typical workflow to refresh them is:

1. Update the external sources to their latest version. This updates the lock
   file and fetches the sources into `external/repos/`.

```bash
just external::refresh
```

2. (Optional) Re-apply the local patches in `external/patches/`.

```bash
just external::patch
```

> [!NOTE]
> An upstream update may break compatibility with the current chart values or
> patches. Watch for failures when re-applying patches and adjust them or the
> chart accordingly.

3. Render and deploy the updated chart.

```bash
just render
just deploy
```
