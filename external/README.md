# External assets

This directory holds external files managed by vendir.
The lockfile pins the external releases.

The repos subdirectory holds external git repositories.
The patches subdirectory mirrors the structure of repos and allows patching upstream repos with custom code.

## Adding a patch.

Create patch in local clone:

```
cd external/repos/presidio
git checkout -b fix
# edit files
git commit -am "change app config"
git format-patch -1 HEAD
```

Apply patch from the repository root:

```
git -C external/repos/<repo> apply external/patches/<repo>/file.patch
```

All patches can be (re-)applied at once with `just external::patch`.
