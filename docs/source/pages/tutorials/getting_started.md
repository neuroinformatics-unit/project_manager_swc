(tutorial-getting-started)=

# Getting Started

This tutorial will give a full introduction to starting
a neuroscience project with **datashuttle**.

We will highlight  **datashuttle**'s key features by creating
a 'mock' experiment, standardised to the
[NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/) style.


```{image} /_static/tutorial-1-example-file-tree-dark.png
   :align: center
   :class: only-dark
   :width: 550px
```
```{image} /_static/tutorial-1-example-file-tree-light.png
   :align: center
   :class: only-light
   :width: 550px
```
<br>

We will upload data to a central data storage machine,
as you would do at the end of a real acquisition session.

Finally we will download data from the central
storage to a local machine, as you would do during analysis.

## Installing **datashuttle**

The first step is to install **datashuttle** by following the instructions
on the [How to Install](how-to-install) page.


::::{tab-set}

:::{tab-item} Graphical Interface
:sync: gui

Entering `datashuttle launch` after installation
will launch the application in your terminal:

```{image} /_static/screenshots/tutorial-1-landing-screen-dark.png
   :align: center
   :class: only-dark
   :width: 700px
```
```{image} /_static/screenshots/tutorial-1-landing-screen-light.png
   :align: center
   :class: only-light
   :width: 700px
```

:::
:::{tab-item} Python API
:sync: python

We can check **datashuttle** has installed correctly by
by importing it into Python without error:

```python
from datashuttle import DataShuttle
```

:::
::::

## Make a new project

The first thing to do when using **datashuttle** on a new machine is
to set up your project.

We need to set the:

1) project name
2) location of the project our local machine (where the acquired data will be saved).
3) location of the project on the central data storage (where we will upload the acquired data).

**datashuttle** supports connecting to the central storage machine
either as a mounted drive or through SHH. \
See [How to Make a New Project](make-a-full-project_target)
for detailed instructions for
connecting a mounted drive or by using SSH.

In this walkthrough, we will set our central storage as a
folder on our local machine for simplicity.

::::{tab-set}
:::{tab-item} Graphical Interface
:sync: gui

Click `Make New Project` and you
will be taken to the project setup page.

```{image} /_static/screenshots/tutorial-1-make-screen-dark.png
   :align: center
   :class: only-dark
   :width: 900px
```
```{image} /_static/screenshots/tutorial-1-make-screen-light.png
   :align: center
   :class: only-light
   :width: 900px
```
<br>

We'll call our project `my_first_project` and can type this into
the first input box on the page:

```{image} /_static/screenshots/tutorial-1-make-project-name-dark.png
   :align: center
   :class: only-dark
   :width: 400px
```
```{image} /_static/screenshots/tutorial-1-make-project-name-light.png
   :align: center
   :class: only-light
   :width: 400px
```
<br>

Next we need to specify the **local path**, the location on our machine where
acquired data will be saved. Choose any directory that is
convenient.

In this example we will add the folder `"local"`
to the end of the filepath for clarity:

```{image} /_static/screenshots/tutorial-1-make-local-path-dark.png
   :align: center
   :class: only-dark
   :width: 400px
```
```{image} /_static/screenshots/tutorial-1-make-local-path-light.png
   :align: center
   :class: only-light
   :width: 400px
```
<br>

The filepath can be typed into the input, copied in with `CTRL+V`
or selected from a directory tree using the `Select` button.

Finally, we need to  select the **central path**. Usually this would be
a path to a mounted central storage drive or relative to the server path
if connecting via SSH.

In this tutorial, we will set this next to the local path for convenience.

1) Copy the contents of the _local path_ input by clicking it, hovering over it and pressing `CTRL+Q` to copy.
2) Paste it into the _central path_ input with `CTRL+V` and change "local" to "central".

```{image} /_static/screenshots/tutorial-1-make-central-path-dark.png
   :align: center
   :class: only-dark
   :width: 400px
```
```{image} /_static/screenshots/tutorial-1-make-central-path-light.png
   :align: center
   :class: only-light
   :width: 400px
```
<br>

You can now click `Save` to set up the project.

Once the project is created, the `Go to Project Screen` button
will appear. Click to move on to the `Create Project` page.

:::
:::{tab-item} Python API
:sync: python

First, we must initialise the `DataShuttle` object
with our chosen `project_name`.

We will call our project `"my_first_project"`:

```python
from datashuttle import DataShuttle

project = DataShuttle("my_first_project")
```

Next, we will use the `make_config_file()` method set the
configurations ('configs') for our project.


First, we need to specify the `local_path` as the location on our machine
where the projact (and acquired data) will be located.

Next, we set the `central_path` to the project location on the central storage machine.

In this tutorial, we will set this next to the `local_path` for convenience.

Finally, we  will set the `connection_method` to `"local_filesystem"`
as we are not using SSH in this example.

```python
project.make_config_file(
    local_path=r"C:\Users\Joe\data\local\my_first_project",
    central_path=r"C:\Users\Joe\data\central\my_first_project",
    connection_method="local_filesystem",
)
```

If you want to change any config in the future, use the `update_config_file()` method

```python
project.update_config_file(
    local_path=r"C:\a\new\path"
)
```

We are now ready to create our standardised project folders.
:::
::::
## Creating folders

Let's imagine today is our first day of data collection,
and we are acquiring  behaviour (`behav`) and electrophysiology (`ephys`) data.

We will create standardised subject, session and datatype folders
in which to store the acquired data.

::::{tab-set}
:::{tab-item} Graphical Interface
:sync: gui

We will create standardised project folders using the `Create` tab.

```{image} /_static/screenshots/tutorial-1-create-screen-dark.png
   :align: center
   :class: only-dark
   :width: 900px
```
```{image} /_static/screenshots/tutorial-1-create-screen-light.png
   :align: center
   :class: only-light
   :width: 900px
```
<br>

Following the [NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/)
style we will  call the first subject `sub-001`. Additional key-value pairs
could be included if desired (see the
[NeuroBlueprint specification](https://neuroblueprint.neuroinformatics.dev/latest/specification.html)
for details).

In the session name we will include today's date as an extra key-value pair.
Our first session will be `ses-001_date-<todays_date>`.

We could start by typing `sub-001` into the subject input box, but
it is more convenient to simply double-left-click it. This will suggest
the next subject number based on the current subjects in the project:

```{image} /_static/screenshots/tutorial-1-create-subject-dark.png
   :align: center
   :class: only-dark
   :width: 400px
```
```{image} /_static/screenshots/tutorial-1-create-subject-light.png
   :align: center
   :class: only-light
   :width: 400px
```
<br>

```{note}
The subject and session folder input boxes have live validation.
This will flag any
[NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/)
errors with a red border. Hover over the input box with the mouse
to see the nature of the error.
```

Next, we can input the session name. Double-left-click on the session
input to automatically fill with `ses-001`. We can then add
today's date with the `@DATE@` convenience tag:

```{image} /_static/screenshots/tutorial-1-create-session-dark.png
   :align: center
   :class: only-dark
   :width: 400px
```
```{image} /_static/screenshots/tutorial-1-create-session-light.png
   :align: center
   :class: only-light
   :width: 400px
```
<br>

Today's date will be automatically added when the session folder is created.

The datatype folders to create can be set with the `Datatype(s)` checkboxes.
Uncheck the `funcimg` and `anat` datatype boxes to ensure
we only create `behav` and `ephys` folders.

```{image} /_static/screenshots/tutorial-1-create-datatype-dark.png
   :align: center
   :class: only-dark
   :width: 400px
```
```{image} /_static/screenshots/tutorial-1-create-datatype-light.png
   :align: center
   :class: only-light
   :width: 400px
```
<br>

Finally, click `Create Folders` to create the project folders.
:::
:::{tab-item} Python API
:sync: python
We will create project folders with the `create_folders()` method.

Following the [NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/)
style we will  call the first subject `sub-001`. Additional key-value pairs
could be included if desired (see the
[NeuroBlueprint specification](https://neuroblueprint.neuroinformatics.dev/latest/specification.html)
for details).

In the session name we will include today's date as an extra key-value pair.
Our first session will be `ses-001_date-<todays_date>`.

Finally, we will tell **datashuttle** to create `behav` and `ephys` datatype
folders only:

```python
project.create_folders(
    top_level_folder="rawdata",
    sub_names="sub-001",
    ses_names="ses-001_@DATE@",
    datatype=["behav", "ephys"]
)
```

Navigate to the `local_path` in your system filebrowser to see the created folders.

```{note}
The names of the folders to be created are validated on the fly against
[NeuroBlueprint](https://neuroblueprint.neuroinformatics.dev/latest/specification.html).
An error will be raised if names break with the specification and
the folders will not be created.
```

Two useful methods to automate folder creation are `get_next_sub()` and
`get_next_ses()`. These can be used to automatically get the next subject
and session names in a project.

To get the next subject  in this project (`sub-002`) and the next
session for that subject (`ses-001`) we can run:

```python
next_sub = project.get_next_sub("rawdata", local_only=True)                # returns "sub-001"
next_ses = project.get_next_ses("rawdata", sub=next_sub, local_only=True)  # returns "ses-001"

project.create_folders(
    "rawdata",
    next_sub,
    f"{next_ses}_@DATE@",
    datatype=["behav", "ephys"]
)
```

The `local_only` argument restricts the search for the next subject and session
to the local project folder only. Set this to `False` to consider subjects
and sessions in  the central storage.

:::
::::

This was a quick overview of creating folders—see
and [How to use Create Folder Tags](how-to-create-folders) for full details
including additional customisation with [Name Templates](how-to-use-name-templates).

## Exploring folders

In our imagined experiment, we will now want to save data from
acquisition software into our newly created, standardised folders.
**datashuttle** provides some quick methods to pass the created
folder paths to acquisition software.

::::{tab-set}
:::{tab-item} Graphical Interface
:sync: gui

When folders are created the `Directory Tree` on the left-hand side
will update to display the new folders:

```{image} /_static/screenshots/tutorial-1-explore-folders-dark.png
   :align: center
   :class: only-dark
   :width: 400px
```
```{image} /_static/screenshots/tutorial-1-explore-folders-light.png
   :align: center
   :class: only-light
   :width: 400px
```
<br>

By hovering over a folder with the mouse we can quickly
copy the full path to the folder by pressing `CTRL+Q)`
(you may need to click the `Directory Tree` first).

Alternatively, pressing `CTRL+O` will open the folder in your file browser.

Hover the mouse over the `DirectoryTree` for a tooltip indicating all possible shortcuts.

```{admonition} Creating mock data for the tutorial

To continue with our experiment we will need to create 'mock'
acquired data to transfer to central storage. These will
take the form of simple text files with their extensions changed.

You can download these files from
[this link](https://gin.g-node.org/joe-ziminski/datashuttle/src/master/docs/tutorial-mock-data-files),
by right-clicking each file and selecting "Download (or) Save Link As...".
Alternatively you can create them in your favourite text editor.

Next, hover over the `behav` folder the `Directory Tree` with your
mouse and and press `CTRL+O` to open the folder in your file browser.
Move the mock behavioural data file (`sub-001_ses-001_camera-top.mp4`)
into the `behav` datatype folder.

Next, repeat this for the `ephys` datatype by moving the remaining
electrophysiology files to the `ephys` folder.

Finally, hover the mouse over the `Directory Tree` and press `CTRL+R` to refresh.

```

:::
:::{tab-item} Python API
:sync: python

`create_folders()` returns the full filepaths of created datatype folders.

These can be used in acquisition scripts to save data to these folders:

```python
folder_path_dict = project.create_folders(
    top_level_folder="rawdata",
    sub_names=["sub-001"],
    ses_names=["ses-001_@DATE@"],
    datatype=["behav", "ephys"]

)

print([path_ for path_ in folder_path_dict["behav"]])
# ["C:\Users\Joe\data\local\my_first_project\sub-001\ses-001_16052024\behav"]
```


```{admonition} Creating mock data for the tutorial

To continue with our experiment we will need to create 'mock'
acquired data to transfer to central storage. These will
take the form of simple text files with their extensions changed.

You can download these files from
[this link](https://gin.g-node.org/joe-ziminski/datashuttle/src/master/docs/tutorial-mock-data-files),
by right-clicking each file and selecting "Download (or) Save Link As...".
Alternatively you can create them in your favourite text editor.

Move the mock behavioural data file (`sub-001_ses-001_camera-top.mp4`)
into the `behav` datatype folder and the remaining
electrophysiology files to the `ephys` folder.

```
:::
::::

## Uploading to central storage

We have now 'acquired' `behav` and `ephys` data onto our local machine.
The next step is to upload it to central data storage.

In this walkthrough we set the central storage on our
local machine for convenience. Typically,  this would be an external
central storage machine connected as a mounted drive or through SSH.

```{warning}
The **overwrite existing files** setting is very important.
It takes on the options **never**, **always** or **if source newer**.

See the [transfer options](transfer-options) section for full details.
```

::::{tab-set}
:::{tab-item} Graphical Interface
:sync: gui

Switch to the `Transfer` tab.  On the left we again
see a `Directory Tree` displaying the local version of the project:

```{image} /_static/screenshots/tutorial-1-transfer-screen-upload-dark.png
   :align: center
   :class: only-dark
   :width: 900px
```
```{image} /_static/screenshots/tutorial-1-transfer-screen-upload-light.png
   :align: center
   :class: only-light
   :width: 900px
```
<br>

The first page on the `Transfer` tab allows us to upload the entire project,
both the `rawdata` and `derivatives`—see the
[NeuroBlueprint specification](https://neuroblueprint.neuroinformatics.dev/latest/specification.html)
for details.

We only have acquired data in the `rawdata` folder.
We can simply click `Transfer` to upload everything to central storage.

The data from local will now appear in the "central" folder
(an easy way to navigate to the folder to check
is to go to the `Config` tab and press `CTRL+O` on the **central path** input box).

See the  [How to Transfer Data](how-to-transfer-data) page for full details
on transfer options, as well as `Top Level Folder` and `Custom` transfers.

Next, we will use `Custom` transfers to move only a subset of the dataset.

:::
:::{tab-item} Python API
:sync: python

`upload_entire_project()` is a high level method that uploads all files
in the project.
This includes both the `rawdata` and `derivatives` top-level folders—see the
[NeuroBlueprint specification](https://neuroblueprint.neuroinformatics.dev/latest/specification.html)
for details.

As we only have a `rawdata` folder we can simply run:

```python
project.upload_entire_project()
```

All files will be uploaded from the local version of the project to central storage.

Navigating to the `central_path` in your systems file browser, the newly transferred data
will have appeared.

Other methods (e.g. `upload_rawdata()` and `upload_custom()`) provide customisable
transfers (and every `upload` method has an equivalent `download` method).

See the  [How to Transfer Data](how-to-transfer-data) page for full details
on transfer methods and [arguments](transfer-options).

Next, we will use `Custom` transfers to move only a subset of the dataset.

:::
::::

## Downloading from central storage

Next let's imagine we are now using an analysis machine on which
there is no data. We want to download a subset of data central storage
data for further processing.

In this example we will download the behavioural data only from the first session.

In practice **datashuttle**'s custom data transfers work well when there
are many subjects and sessions. For example, we may want to download
only the behavioural 'test' sessions from a specific range of subjects.

```{admonition} Replicating a fresh machine for the tutorial
To replicate starting on a new local machine, delete the `rawdata` folder
from your **local path**.

We will next download data from the **central path** to our now-empty local project.

In practice when setting up **datashuttle** on a new machine, you would
again [make a new project](make-a-full-project_target).
```

We will look at a small subset of possible
options here—see [How to make Custom Transfers](making-custom-transfers) for all possibilities.

::::{tab-set}
:::{tab-item} Graphical Interface
:sync: gui

The `Custom` transfer screen has options for selecting specific combinations
of subjects, sessions and datatypes.

```{image} /_static/screenshots/tutorial-1-transfer-screen-custom-dark.png
   :align: center
   :class: only-dark
   :width: 600px
```
```{image} /_static/screenshots/tutorial-1-transfer-screen-custom-light.png
   :align: center
   :class: only-light
   :width: 600px
```
<br>

In the subject input, we can simply type `all` (in this case, we only have one subject anyway).

```{image} /_static/screenshots/tutorial-1-transfer-screen-custom-subjects-dark.png
   :align: center
   :class: only-dark
   :width: 400px
```
```{image} /_static/screenshots/tutorial-1-transfer-screen-custom-subjects-light.png
   :align: center
   :class: only-light
   :width: 400px
```
<br>

Next, let's specify what session to download. We can use the
[wildcard tag](transfer-the-wildcard-tag)
to avoid typing the exact date—`ses-001_@*@`:

```{image} /_static/screenshots/tutorial-1-transfer-screen-custom-sessions-dark.png
   :align: center
   :class: only-dark
   :width: 400px
```
```{image} /_static/screenshots/tutorial-1-transfer-screen-custom-sessions-light.png
   :align: center
   :class: only-light
   :width: 400px
```
<br>

This is useful if you want to download many sessions, all with different dates.

Then, select only the `behav` datatype from the datatype checkboxes.

```{image} /_static/screenshots/tutorial-1-transfer-screen-custom-datatypes-dark.png
   :align: center
   :class: only-dark
   :width: 400px
```
```{image} /_static/screenshots/tutorial-1-transfer-screen-custom-datatypes-light.png
   :align: center
   :class: only-light
   :width: 400px
```
<br>

Finally, we can select `Download` from the upload / download switch,
and click `Transfer`.

```{image} /_static/screenshots/tutorial-1-transfer-screen-custom-switch-dark.png
   :align: center
   :class: only-dark
   :width: 580px
```
```{image} /_static/screenshots/tutorial-1-transfer-screen-custom-switch-light.png
   :align: center
   :class: only-light
   :width: 580px
```
<br>

The transfer will complete, and the custom selection
of files will now be available in the **local path**.

:::
:::{tab-item} Python API
:sync: python

We will use the `download_custom()` method (the download equivalent method of
the `upload_custom()`).

Convenience tags can be used to make downloading subsets of data easier:

```python
project.download_custom(
    top_level_folder="rawdata",
    sub_names="all",
    ses_names="ses-001_@*@",
    datatype="behav"
)
```

The `"all"` keyword will upload every subject in the project (in this case,
we only have one subject anyway).

The `@*@` [wildcard tag](transfer-the-wildcard-tag) can be used to match
any part of a subject or session name—in this case we use it to avoid
typing out the date. This is also useful if you want to download many
sessions, all with different dates.


Finally, we chose to download only the `behav` data for the session.
:::
::::

```{note}
Detailed information on data transfers can be found in the `Logs`.
Visit [How to Read the Logs](how-to-read-the-logs) for more information.
```

The transfer will complete, and the custom selection
of files will now be available in the **local path**.

## Summary

That final transfer marks the end of our **datashuttle** tutorial!

Now you can:

1) set up a new project
2) upload your acquired data to a central storage machine
3) download subsets of data for analysis

We are always keen to improve **datashuttle**, so please don't hesitate
to get in contact with any
[Issues](https://github.com/neuroinformatics-unit/datashuttle)
or drop in to our
[Zulip Chat](https://neuroinformatics.zulipchat.com/#narrow/stream/405999-DataShuttle)
with any questions or feedback.

Have a great day!
