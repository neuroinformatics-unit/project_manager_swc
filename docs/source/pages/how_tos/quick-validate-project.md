(quick-validate-projects)=

# How to Quickly Validate an Existing Project

:::{note}
Currently validation is only available through the Python API.
:::

The function [](datashuttle.quick_validate_project) can be used to quickly validate a project fully conforms
to the[NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/latest/index.html) standard. This does not require setting up
a full ``datashuttle`` project, only the filepath to the project.

For example, if you have an existing project
at ``/mydrive/path/to/project/project_name``
you can validate with:

```python
from datashuttle import quick_validate_project

quick_validate_project(
    project_path="/mydrive/path/to/project/project_name",
    display_mode="error",
)

```

In this case, `display_mode=error` will result in an error
on the first encountered validation issue. Otherwise `"warn"` will show
a python warning for all detected issues, while `"print"`
will print directly to console.

By default, both `"rawdata"` and `"derivatives"` folders will
be checked (assuming they exist). Otherwise, one can be specified
with the a `top_level_folder` argument.

See [](datashuttle.quick_validate_project)  for a full list
of arguments.
