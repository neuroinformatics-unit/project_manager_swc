(how-to-create-folders)=
# How to Create Folders

**datashuttle** automates project folder creation and validation
according to the [NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/).

Before starting with folder creation, we'll briefly introduce the
[NeuroBlueprint specification](https://neuroblueprint.neuroinformatics.dev/latest/specification.html).

An example [NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/) project:

```{image} /_static/NeuroBlueprint_project_tree_dark.png
   :align: center
   :class: only-dark
   :width: 650px
```
```{image} /_static/NeuroBlueprint_project_tree_light.png
   :align: center
   :class: only-light
   :width: 650px
```
<br>

Some key features:

* The `rawdata` top-level-folder contains acquired data. Following acquisition
this data is never edited.

* The `derivatives` top-level folder contains all processing and analysis outputs. There are
no fixed requirements on its organisation.

* Subject and session folders are formatted as key-value pairs.

* Only the `sub-` and `ses-` key-value pairs are required (additional pairs are optional).

* Each session contains datatype folders, in which acquired data is stored.

Now, let's get started with folder creation!

## Creating project folders

The project-name folder is located at the **local path**
specified when [setting up the project](make-a-full-project_target).

We will now create subject, session and
datatype folders within a `rawdata` top-level folder.


We will create datatype folders `behav` and `funcimg`
within a `ses-001_<todays_date>` for both a `sub-001` and `sub-002`.

The below example uses the `@DATE@` convenience tag to automate
creation of today's date. See the
[convenience tags](create-folders-convenience-tags).
section for more information on these tags.


::::{tab-set}

:::{tab-item} Graphical Interface
:sync: gui

Folders are created in the `Create` tab on the `Project Manager` page.

```{image} /_static/screenshots/how-to-create-folders-example-dark.png
   :align: center
   :class: only-dark
   :width: 900px
```
```{image} /_static/screenshots/how-to-create-folders-example-light.png
   :align: center
   :class: only-light
   :width: 900px
```
<br>


We can enter the subject and session names into the input boxes,
and select datatype folders to create. Clicking `Create Folders`
will create the folders within the project.

A number of useful shortcuts to streamline this process are described below.

### `Create` shortcuts

The `Create` tab has a lot of useful shortcuts.

First, **double-clicking subject or session input boxes** will suggest
the next subject or session to create, based on the local project.
If a [Name Template](how-to-use-name-templates) is set, the
suggested name  will also include the template.

Holding `CTRL` while clicking will enter the `sub-`
or `ses-` prefix only.

Next, the **Directory Tree** has a number of useful shortcuts. These are
activated by hovering the mouse of a file or folder and pressing
one of the below key combinations
(you may need to click the `Directory Tree` first):

Fill an input
: `CTRL+F` will fill the subject or session input with the name
of the folder (prefixed with `sub-` or `ses-`) that is hovered over.

Append to an input
: `CTRL+A` is similar to 'fill' above, but will instead append the name
to those already in the input. This allows creation of multiple
subjects or sessions at once.

Open folder in system filebrowser
: `CTRL+O` will open a folder in the system filebrowser.

Copy the full filepath.
: `CTRL+Q` will copy the entire filepath of the file or
folder.


### `Create` Settings

Click the `Settings` button on the `Create` tab to set
the top-level folder, and bypass validation.

```{image} /_static/screenshots/how-to-create-folders-settings-dark.png
   :align: center
   :class: only-dark
   :width: 500px
```
```{image} /_static/screenshots/how-to-create-folders-settings-light.png
   :align: center
   :class: only-light
   :width: 500px
```
<br>

Top level folder
: This dropdown box will set whether folders are created in the
`rawdata` or `derivatives` top-level folder.

Bypass validation
: This setting will allow folder creation even if the names
are not valid (i.e. they break with
[NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/)).

This screen is also used to validate and autofill with
[Name Templates](how-to-use-name-templates).

:::

:::{tab-item} Python API
:sync: python

The `create_folders()` method is used for folder creation.

We simply need to provide the subject, session and datatypes to create:

```python
from datashuttle import DataShuttle

project = DataShuttle("my_first_project")

created_folders = project.create_folders(
    top_level_folder="rawdata",
    sub_names=["sub-001", "002"],
    ses_names="ses-001_@DATE@",
    datatype=["behav", "funcimg"]
)
```

The method outputs `created_folders`, which contains the
`Path`s to created datatype folders. See the below section for
details on the `@DATE@` and other convenience tags.

By default, an error will be raised if the folder names break
with [Neuroblueprint](https://neuroblueprint.neuroinformatics.dev/)
and folders will not be created.
The `bypass_validation` argument can be used to bypass this feature.

:::
::::


(create-folders-convenience-tags)=
## Convenience Tags

There are four convenience tags that can be used in subject or session
names when creating folders.

They automate the inclusion of:

Today's Date
: The `@DATE@` tag will include today's date in the format `YYYYMMDD`. \
    *e.g.* If today's date is 16th May 2024, the name `"ses-001_@DATE@"` will
create the folder `ses-001_date-20241605`.

Current Time
: The `@TIME@` tag will include the current time in the format `HHMMSS`. \
    *e.g.* If the current time is `15:10:05` (i.e. 10 minutes and 5 seconds past 3 p.m.),
the name `"ses-001_@TIME@"` will create the folder `ses-001_time-151005`.

Current Datetime
: The `@DATETIME@` tag will add the
[ISO8601](https://en.wikipedia.org/wiki/ISO_8601)-formatted datetime. \
    *e.g.* If the date and time are as above, the name `"ses-001_@DATETIME@"` will
create the folder `ses-001_datetime-20241605T151005`.

A Range of Folders
: The`@TO@` tag creates a range of subject or session numbers. \
    *e.g.* `"sub-001@TO@003"` would create subject folders `sub-001`, `sub-002`, `sub-003`.
