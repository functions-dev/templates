# Welcome to Blog Function in Go!

This template serves as an example of how to use [Hugo](https://gohugo.io/)
package as a static file generator for your website. It uses instanced Function
in go for the deployment. All the hugo content can be found in the `hugo/`
directory.

## How to use
The root directory will contain your standard Function with one addition -
`hugo/` directory.
This will contain all the hugo files needed. You will need to familiarize
yourself with [Hugo](https://gohugo.io/) in order to use it.

You can develop in a live server where changes happen instanteniously with hugo.
You can do this via command:

```bash
hugo server
```

Note: Look at different flag options in order to build all files, including
drafts etc. (`hugo server -D`) for example.


### Deploy your Function
Once you make your changes in the hugo files you will need to build static
files. You can achieve this via `hugo build` with target destination of `dist`
or whatever directory you choose in your `function.go`. You can do this via
the
following:

```bash
hugo build --destination ../dist
```

Now you can simply `func run` or `func deploy` with the host builder to either
expose your Function locally or on your cluster respectively.

Example commands:
```bash
func run --builder=host
```

```bash
func deploy --builder=host
```

#### Convenient Makefile
A Makefile exists for your convenience! It has 2 simple targets - `build` and
`clean`. Once you've edited all hugo files to your liking, use `make build` to
generate the static files in the `dist` directory -- this takes care of the hugo
build step covered previously. The `clean` target is for cleaning out your files
from the `dist` directory in case you would need it.

### Cleanup
Use `make clean` once you want to get rid of all the generated files to have a
clean Functions root directory.

## GLHF!
- Found a mistake in the templates?
- Created a new project with Functions?

Share it with us on
[CNCF Slack](https://cloud-native.slack.com/archives/C04LKEZUXEE)!
