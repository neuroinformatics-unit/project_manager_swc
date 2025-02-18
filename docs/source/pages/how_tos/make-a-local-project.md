# How to Make a Local Project

**datashuttle** can be used to create and validate
[NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/latest/index.html) projects,
as well as transfer data. If you want to quickly create or validate a project's folders,
but not transfer data, you can make a local-only project and immediately get started.

::::{tab-set}

:::{tab-item} Graphical Interface
:sync: gui

Selecting `Make New Project` will take you to the project set up screen.

Enter the name of your project, the path to your project folder and
select `No connection (local only)` (note that the central-path options
are now disabled).

```{image} /_static/screenshots/how-to-make-local-project-configs-dark.png
   :align: center
   :class: only-dark
   :width: 900px
```
```{image} /_static/screenshots/how-to-make-local-project-configs-light.png
   :align: center
   :class: only-light
   :width: 900px
```
<br>

:::

:::{tab-item} Python API
:sync: python

First, import **datashuttle** and set up a project with the ``project_name``.
If a project already exists, this should match the project folder name (i.e. the level above ``rawdata``).


```python

from datashuttle import DataShuttle

project = DataShuttle("my_project_name")

```

Next, give **datashuttle** the path to the project folder (this can,
but doesn't have to, include the ``project_name``)

```python

project.make_config_file(
    local_path=r"C:\MyUsername\my_data\my_project_name"
)

```

The project is now ready for use, and in future can be instantiated only
with the line ``project = DataShuttle("my_project_name")`` (i.e. you will not
have to set the `local_path` again).

If you wish to change the project settings at a later time, use ``project.update_config_file()``.

For example, it is possible to immediately validate the project:

```python
project.validate_project("rawdata", error_or_warn="warn")
```

Setting ``error_or_warn`` will display all validation issues, otherwise
it will error on the first one encountered.

New project folders can also be created in the local folder:

```python
project.create_folders("rawdata", "sub-001", "ses-001_@DATE@", datatype=["ephys", "behav"])
```

see  [Create Folders](how-to-create-folders)  for more details.

:::
::::

:::{note}

When in local-only mode, some functionality of **datashuttle** is lost.

It will not be possible to:
- transfer data, which requires passing configs related to a centrally-stored project.
- Any method that exposes a ``local_only`` argument will always set this to ``True``.
For example, validation will only ever be performed on the local project.

See [](make-a-full-project_target) for more information on setting up for data transfer.
:::
