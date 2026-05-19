# External assets

This directory holds external files managed by vendir.
The lockfile pins the external releases.

The repos subdirectory holds external git repositories.
The patches subdirectory mirrors the structure of repos and allows patching upstream repos with custom code.

## Adding a patch.

Create patch in local clone:

```
cd external/presidio
git checkout -b fix
# edit files
git commit -am "change app config"
git format-patch -1 HEAD
```

Apply patch from outside repo using docker context

```
git -C external/repos/root-dir apply external/patch/repo/file.patch
```
