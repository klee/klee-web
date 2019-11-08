# Adding Examples to Klee Web

There are two ways to add Example files to Klee Web.
These ways work differently and achieve different results.

## Adding Examples from the Control Panel

The easiest way to add, edit or remove examples is from the built-in control
panel at `klee.doc.ic.ac.uk/manage` (or `192.168.33.10/manage` if run locally).

Login as an admin user and click on "Manage Examples". Here you can add new
example project; add, edit and remove new files and the relative configurations.

### Important Note

All the operations executed on the example files will be saved in the internal
database, however they will be lost should the VM be shut down and rebuilt.
In order to make the changes permanent, it's necessary to edit the source files
as explained below.

## Adding Examples from the Source Files

Adding, editing or removing examples from the source file is itself very
simple too. Here are the steps to follow.

- ### Editing an Example

  To edit an existing example, simply edit the .c source files you find in
  `src/klee_web/frontend/fixtures/Examples/`.

- ### Adding an Example

  To add a new example, add the .c source files for the example inside
  `src/klee_web/frontend/fixtures/Examples/`. Then, update the `fixtures.json`
  file with the exact name of the example file you have added and its running
  configuration parameters. Ensure the JSON file remains syntactically valid.

- ### Removing an Example

  Similarly, to remove an new example, remove the .c source files for the Example
  folder `src/klee_web/frontend/fixtures/Examples/` and update the `fixtures.json`
  accordingly. Ensure the JSON file remains syntactically valid.

- ### Adding a new Example Project

  You may have noticed that there are two example projects, "Examples" and
  "Tutorials". If you want to add a new example project, create a folder
  containing the .c source files inside `src/klee_web/frontend/fixtures/`.
  Then update the `fixtures.json` accordingly, ensure that the JSON file remains
  syntactically valid and that the name of the project in the JSON file matches
  the name of the folder you have created.
  Finally, edit the migration file `0002` under
  `src/klee_web/frontend/migrations/` with an extra call to

```python
add_fixtures(apps, fixtures, "Your Project Name")
```

### Applying the Changes

At these point, your changes are permanent and will be applied the next time
the VM is shut down and rebuilt. However, if you want to manually apply the
changes you have made without rebuilding the VM, follow these steps.

1. Log into the Control Panel.
2. Remove the existing example projects.
3. From inside the VM run the command

```bash
cd /titb/src/klee_web && source /src/worker/env/bin/activate
```

4. Run the following command

```bash
./manage.py migrate --fake frontend zero
```

5. Finally run the migrations with

```bash
./manage.py migrate
```

Refresh the page and you should see your changes applied. If you encounter any
errors, then these are probably due to invalid JSON inside `fixtures.json` or
mismatched file names. Check for these and try again.
